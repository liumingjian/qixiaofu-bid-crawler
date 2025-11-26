# 微信公众号招标信息爬虫系统

自动化获取“取七小服公众号”历史文章，提取招标信息并通过邮件与 Web 管理界面对外提供。系统以 Python + Selenium + Flask 构建，适合部署在企业内部环境中使用。

## ✨ 核心能力

- **公众号后台文章列表获取**：借助 `fakeid + token + Cookie` 调用 `mp.weixin.qq.com/cgi-bin/appmsg`，按关键词/时间窗口筛选招标文章。
- **文章内容爬取**：`core.scraper.WeChatArticleScraper` 支持批量抓取、重试、随机延迟以及进度回调。
- **招标信息提取**：正则驱动的 `BidInfoExtractor` 拆分多项目文本，提取项目名、预算、采购人、获取文件时间等字段并生成唯一 ID。
- **数据管理**：使用 JSON 文件持久化文章与招标信息，完成去重、状态管理与基本统计。
- **通知与界面**：`EmailNotificationService` 发送 HTML 邮件，Flask Web 界面（Bootstrap + 原生 JS）提供招标查询、状态筛选和“一键爬取”。
- **测试保障**：单元测试 + 模拟端到端测试（`tests/test_e2e.py`、`tests/test_performance.py`）覆盖主要流程。

## 🗂️ 仓库结构

```
├── app.py                     # Flask 应用入口 + API
├── core/                      # 业务模块（抓取、提取、通知等）
├── data/                      # JSON 数据与日志目录（运行后生成）
├── docs/                      # PRD、Story、测试/验收报告等文档
├── tests/                     # 单元测试、E2E、性能测试
├── web/                       # 模板与静态资源
├── INSTALL.md / CONFIGURATION.md / TROUBLESHOOTING.md
├── QUICKSTART.md              # 一页式上手指南
└── README.md                  # 当前文档
```

> `wechat_article.json` 为提取模块的示例输入数据，供单元测试与调试使用。

## ⚙️ 环境准备

1. 安装 **Python 3.10+** 与 **Google Chrome**（需配套版本的 ChromeDriver）。
2. 克隆代码并切换到项目目录：
   ```powershell
   git clone <repo-url> webchat-crawer
   cd webchat-crawer
   ```
3. 创建并激活虚拟环境：
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1    # Windows
   # 或 source .venv/bin/activate  # macOS / Linux
   ```
4. 安装依赖：
   ```powershell
   pip install -r requirements.txt
   ```

## 🔧 配置

`config.json` 包含所有运行参数，常用字段：
- `wechat.fakeid` / `token` / `cookie`（公众号后台抓取必填）以及 `max_articles_per_crawl` / `keyword_filters` / `days_limit`
- `email.smtp_*` / `sender_email` / `sender_password` / `recipient_emails`
- `scraper.headless` / `retry_count` / `prompt_on_captcha`
- `paths.data_dir` / `paths.log_dir`

**如何获取 fakeid / token / cookie**
1. 在浏览器登录 https://mp.weixin.qq.com/，进入“内容管理 - 图文消息”页。
2. 地址栏 `...token=xxxxxxxx&lang=zh_CN&f=...` 中的 `token`、`fakeid` 即可复制到配置。
3. 打开开发者工具 (F12) → Network，任意点击一次“图文消息”列表，请求 Headers 中的 `Cookie` 全量复制到 `wechat.cookie`。
4. 保持浏览器在线，定期更新 Cookie 以避免 ret=200003（登录过期）。

详见 [CONFIGURATION.md](CONFIGURATION.md)。建议在生产环境复制一份 `config.local.json` 并在启动脚本中指定。

## 🚀 快速上手

阅读 [QUICKSTART.md](QUICKSTART.md) 获取“一页式”操作指南，其中包含：
- 5 分钟完成安装、配置、测试与启动
- 如何触发一次完整爬取并查看 Web 界面
- 常见命令（启动 Flask、运行端到端测试）

## ✅ 测试

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest tests/                      # 全量测试
python -m pytest tests/test_e2e.py -v        # 端到端流程（模拟）
python -m pytest tests/test_performance.py   # 性能基线（模拟）
```

测试均在临时数据目录运行，不会污染 `data/` 下的真实文件。

## 🧾 日志与数据

- 运行过程中生成 `data/logs/YYYYMMDD.log`，统一格式 `[时间] [级别] [模块] 消息`。
- 文章与招标信息分别持久化到 `data/articles.json` 与 `data/bids.json`；如需初始化环境，可手动清空或备份这些文件。
- Web 和 API 的实时状态可通过 `/api/crawl/status` 查询。

## 📚 文档导航

- [PRD](docs/PRD.md)：产品需求
- [docs/task_list.md](docs/task_list.md)：任务追踪
- [QUICKSTART.md](QUICKSTART.md)：快速上手
- [INSTALL.md](INSTALL.md) / [CONFIGURATION.md](CONFIGURATION.md) / [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [docs/test_report.md](docs/test_report.md) / [docs/acceptance_report.md](docs/acceptance_report.md)

## 💬 支持

如需反馈缺陷或需求，可在 `docs/task_list.md` 记录或通过 issue 追踪。生产部署前请确保已阅读配置与故障排除文档，并完成一次真实数据的人工验收。***
