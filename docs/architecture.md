# 系统实现与技术说明

本文帮助开发者快速理解七小服公众号招标信息爬虫的端到端实现流程、关键模块以及可扩展点。阅读顺序与实际运行路径一致，结合 `README.md` / `CONFIGURATION.md` 可以覆盖部署与调试需求。

## 技术栈与整体架构

- **语言 & 框架**：Python 3.10+，Selenium（ChromeDriver）、Flask、BeautifulSoup、pytest。
- **运行形态**：单体应用，Flask 提供 Web UI 与 API，并负责触发后台爬虫；Selenium 驱动 Chrome 浏览器完成公众号页面的模拟访问。
- **数据持久化**：JSON 文件（`data/articles.json`、`data/bids.json`）+ 日志文件夹（`data/logs/`），通过 `storage.FileStorage` 封装备份、防损坏逻辑。
- **外部依赖**：微信公众号后台接口（`appmsg`）、文章正文页面、SMTP 服务。

```
┌────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│ Flask  │ -> │ CrawlRunner   │ -> │ Selenium    │ -> │ 正文内容 &  │
│  UI/API│    │ (业务流程编排)│    │ Fetcher/Scr.│    │ 招标文本     │
└────────┘    └──────────────┘    └─────────────┘    └─────────────┘
      │                                         │
      ▼                                         ▼
┌─────────────┐    ┌─────────────┐    ┌──────────────────┐
│ DataManager │ <- │ BidExtractor │ <- │ EmailNotification │
└─────────────┘    └─────────────┘    └──────────────────┘
```

## 端到端流程

| 阶段 | 说明 | 关键模块 / 文件 |
| --- | --- | --- |
| 1. 文章列表获取 | `SougouWeChatFetcher`（新版实现）调用 `mp.weixin.qq.com/cgi-bin/appmsg` 接口，使用 `fakeid/token/Cookie` 获取文章列表，并按关键词/时间过滤招标文章。 | `core/article_fetcher.py` |
| 2. 新文章筛选 | 使用 `DataManager.is_article_crawled` 对比 `articles.json`，仅保留未处理 URL。 | `core/data_manager.py` |
| 3. 正文抓取 | `WeChatArticleScraper` 批量访问文章页，等待 `#js_content` 渲染、滚动加载，再由 `parse_html` 提取标题、作者、正文、图片等。 | `core/scraper.py` |
| 4. 招标信息提取 | 通过 `BidInfoExtractor` 的正则模板拆分多项目文本，提取项目名、预算等字段并构造 `BidInfo`。 | `core/bid_extractor.py` |
| 5. 数据持久化 | `DataManager.save_bids/save_article` 负责去重、写入及统计更新，底层采用 `FileStorage` 进行备份与回滚。 | `core/data_manager.py`、`storage/file_storage.py` |
| 6. 通知 | `EmailNotificationService` 组装 HTML 邮件并发送，成功后调用 `update_bid_status` 标记为 `notified`。 | `core/notification.py` |
| 7. Web 展示 | Flask API (`/api/bids`/`/api/stats`/`/api/crawl/*`) 为前端提供查询和控制能力，`web/static/js/main.js` 负责轮询任务状态、渲染卡片。 | `app.py`、`web/` |

`CrawlRunner` 将上述阶段串联，通过 `CrawlController` 在后台线程中运行，并暴露运行状态给 Web 层。

## 关键模块拆解

### 1. SougouWeChatFetcher

- 目标：直接调用公众号后台接口（`mp.weixin.qq.com/cgi-bin/appmsg`）获取历史文章列表。
- 技术要点：
  - 依赖人工登录后台获得 `fakeid`、`token` 和完整 Cookie，Fetcher 使用 `requests.Session` 携带这些凭据发起请求。
  - 支持 `page_size` 分页、重试机制、`request_interval_range` 随机等待以及 rate limit（ret=200013）退避。
  - 通过 `fetch_rule` 在配置中自定义“最近 N 天”或“最新 M 篇”，内部自动切换 `days_limit` / `max_articles` 并结合 `keyword_filters` 预筛选招标文章。
  - `_normalize_article` 将接口返回的 `create_time` 转为 ISO8601 时间戳，统一供后续持久化与 UI 展示。

### 2. WeChatArticleScraper

- 功能：根据文章 URL 抓取正文，支持批量、重试与进度回调。
- 细节：
  - `scrape_articles_batch` 在每篇文章间调用 `_scrape_with_retry`，遇到 `content_text` 为空则按配置重试，并在日志中记录成功率。
  - `scroll_page` 模拟逐屏滚动加载，确保延迟渲染的图片/文字进入 DOM。
  - `parse_html` 输出结构化信息（标题、作者、发布时间、全文文本、HTML、段落列表、图片列表等），供后续提取与存档。

### 3. BidInfoExtractor

- 核心逻辑：
  - `_split_projects` 通过 `(?P<index>\d+)\s*项目名称` 匹配拆分含多项目的文章内容。
  - `_build_pattern` 为各字段动态生成“当前标签到下一个标签”范围的正则，避免跨字段串联。
  - `_validate_required_fields` 要求预算含“元”等硬性特征，过滤误识别文本。
  - `_generate_id` 利用 `project_name + purchaser` 的 MD5 生成稳定 ID，后续用于去重与状态更新。

### 4. DataManager & FileStorage

- `DataManager`：管理工作目录、文件路径、去重、状态统计以及 `articles.json`/`bids.json` 的读写。
- `FileStorage`：负责 JSON 读写的一致性保障——写入前创建时间戳备份、写入失败自动回滚、检测到 JSON 损坏时转移至 `.corrupt` 文件。
- `get_stats` 为仪表盘提供总量、新增、已通知、已归档等指标。

### 5. EmailNotificationService

- 初始化时校验 SMTP 配置并创建日志目录，支持 465（SSL）与 587（STARTTLS）。
- `_format_email_body` 输出响应式 HTML 卡片，将预算、采购人等字段突出展示，并附带原文链接。
- `send_bid_notification` 在发送成功后调用 `DataManager.update_bid_status(...,"notified")`，防止重复通知。

### 6. Flask Web 层

- `create_app` 负责依赖注入，默认实例化数据、抓取、提取、通知组件，并将 `CrawlController`/调度器注入应用配置。
- API：
  - `POST /api/crawl/start`：触发后台线程执行 `CrawlRunner.run`。
  - `GET /api/crawl/status`：轮询爬取状态与错误信息。
  - `GET /api/bids`：按状态过滤招标数据。
  - `GET /api/stats`：返回累计统计。
- 前端使用原生 Fetch + Bootstrap，`web/static/js/main.js` 处理轮询、渲染与错误提示。

### 7. 测试矩阵

- `tests/test_*.py` 覆盖抓取器、提取器、存储、通知以及 Flask API，使用 `pytest` 及依赖注入模拟浏览器/SMTP。
- `tests/test_e2e.py` 构建端到端模拟流程（Mock Selenium + SMTP），验证 `CrawlRunner` 协同逻辑。
- `tests/test_performance.py` 通过伪造数据评估提取器/存储的性能基线。
- `tests/test_scheduler.py` 验证调度器在间隔模式下触发任务及跳过运行中的逻辑。

## 数据与状态

- `data/articles.json`：记录已爬文章的 URL、标题、发布时间、摘要、是否含招标以及招标数量；用于去重与统计。
- `data/bids.json`：存储招标字段、来源信息、状态（`new`/`notified`/`archived`）及时间戳。
- `data/logs/YYYYMMDD.log`：`setup_logger` 将 console + file 双写，方便排查 Selenium/SMTP 运行问题。
- 邮件内容与 Web UI 都来自同一份结构化数据，保证展示一致性。

## 配置要点

- `wechat` 段控制抓取策略（如 `fetch_rule`、`keyword_filters`），账号凭据保存在数据库 `wechat_accounts` 表，可通过 `db/seed.sql` 或 Web 界面维护；`custom.yml` 可继续覆盖其他参数。
- `scraper.*` 影响 Selenium 行为：`headless`、`wait_time`、`retry_count/delay`、`random_delay_range`。
- `email.*` 需提供完整的 SMTP 凭据；`send_test_email()` 可在部署时验证。
- `paths.data_dir/log_dir` 可重定向到共享存储或 Docker 卷，便于多实例读取。
- `scheduler.*` 决定是否自动按 `cron` 表达式或 `interval_minutes` 触发抓取。

### 8. 自动调度器

- `core.scheduler.CrawlScheduler` 常驻后台线程，根据配置计算下一次触发时间。
- 支持 `cron` 表达式（兼容旧的 `daily_time` 字段）或 `interval_minutes` 循环模式，可自由切换。
- 若当前有任务执行，则记录并跳过下一次计划，防止并发重复爬取。

## 扩展与二次开发建议

1. **调度与自动化**：可在外部通过 cron/Systemd 直接运行 Flask CLI 或编写独立脚本调用 `CrawlRunner.run`，借助现有组件即可复用业务逻辑。
2. **持久化升级**：若需要多用户并发或高级查询，可将 `DataManager` 替换为数据库实现（保留 `get_all_bids/save_bids` 等接口）。
3. **更多通知渠道**：依照 `EmailNotificationService` 的接口编写新的通知类（如企业微信 Webhook），并在 `create_app` 中注入。
4. **反爬策略**：在高频运行场景，可扩展代理池、分布式浏览器或自定义登录流程；`driver_factory` 允许注入远程 WebDriver。

> 阅读顺序建议：1) `QUICKSTART.md` 完成环境搭建；2) 本文掌握实现细节；3) 根据需求查阅 `CONFIGURATION.md` 与 `TROUBLESHOOTING.md`。
