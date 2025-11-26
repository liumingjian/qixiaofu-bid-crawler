# 微信公众号招标信息爬虫系统

自动化获取“取七小服公众号”历史文章，提取招标信息并通过邮件与 Web 管理界面对外提供。系统以 Python + Selenium + Flask 构建，适合部署在企业内部环境中使用。

## ✨ 核心能力

- **公众号后台文章列表获取**：借助 `fakeid + token + Cookie` 调用 `mp.weixin.qq.com/cgi-bin/appmsg`，按关键词/时间窗口筛选招标文章。
- **文章内容爬取**：`core.scraper.WeChatArticleScraper` 支持批量抓取、重试、随机延迟以及进度回调。
- **招标信息提取**：正则驱动的 `BidInfoExtractor` 拆分多项目文本，提取项目名、预算、采购人、获取文件时间等字段并生成唯一 ID。
- **数据管理**：使用 JSON 文件持久化文章与招标信息，完成去重、状态管理与基本统计。
- **通知与界面**：`EmailNotificationService` 发送 HTML 邮件，Flask Web 界面（Bootstrap + 原生 JS）提供招标查询、状态筛选和“一键爬取”。
- **自动调度**：内置可选的每日/间隔调度器，配置一次即可在设定时间自动触发抓取。
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

系统内置了默认配置（`core/default_config.py`），运行时会依次合并：
1. 内置默认值；
2. 可选的 `config.json`（不存在则跳过）；
3. 可选的 `custom.json`（推荐仅写入 fetch_rule / 收件人 / 调度等非敏感信息）；
4. 可选的环境变量 `QIXIAOFU_CONFIG_JSON`（直接提供 JSON 字符串）或 `QIXIAOFU_CONFIG_PATH`（指向私有配置文件）。

常见字段：
- `wechat.fakeid` / `token` / `cookie`（公众号后台抓取必填）以及 `max_articles_per_crawl` / `keyword_filters` / `fetch_rule`
- `email.smtp_*` / `sender_email` / `sender_password` / `recipient_emails`
- `scraper.headless` / `retry_count` / `prompt_on_captcha`
- `scheduler.enabled` / `cron` / `timezone`（或 `interval_minutes`）
- `paths.data_dir` / `paths.log_dir`

**如何获取 fakeid / token / cookie**
1. 在浏览器登录 https://mp.weixin.qq.com/，进入“内容管理 - 图文消息”页。
2. 地址栏 `...token=xxxxxxxx&lang=zh_CN&f=...` 中的 `token`、`fakeid` 即可复制到配置。
3. 打开开发者工具 (F12) → Network，任意点击一次“图文消息”列表，请求 Headers 中的 `Cookie` 全量复制到 `wechat.cookie`。
4. 如需抓取“最近 N 天”或“最新 M 篇”，可在 `custom.json` 的 `wechat.fetch_rule` 中设置 `mode: recent_days/latest_count` 及 `value`，无需修改主配置。
5. `scheduler` 支持标准 crontab 表达式（例如 `"0 7 * * *"` 表示每天 07:00），也可指定 `interval_minutes` 周期执行。
6. 保持浏览器在线，定期更新 Cookie 以避免 ret=200003（登录过期）。

详见 [CONFIGURATION.md](CONFIGURATION.md)。生产部署如需隐藏敏感信息，可在打包前修改 `core/default_config.py` 或以环境变量的形式注入。

示例：通过环境变量注入完整配置
```bash
export QIXIAOFU_CONFIG_JSON='{"wechat":{"fakeid":"xxx","token":"yyy","cookie":"..."}, "email":{"smtp_server":"smtp.xxx.com","sender_email":"bot@xxx.com","sender_password":"****"}}'
./dist/qixiaofu-bid-crawler-linux
```
或指向外部文件：
```bash
export QIXIAOFU_CONFIG_PATH=/opt/secure/config.prod.json
./dist/qixiaofu-bid-crawler-linux
```

### 自动调度

将 `scheduler.enabled` 设为 `true` 即可开启后台调度，可选择：

- `cron`: 标准 crontab 表达式，例如 `"0 7 * * *"` 表示每天 07:00；
- `interval_minutes`: 设置后将忽略 cron，按指定分钟数循环执行；
- `timezone`: 解析 cron 的时区，默认 `Asia/Shanghai`（也兼容旧的 `daily_time` 字段）。

调度器运行在独立线程中，会在任务尚未结束时跳过下一次触发，避免重复爬取。

### custom.json

为避免频繁改动默认 `config.json`（其中包含账号、路径等基础配置），日常使用只需维护 `custom.json` 中的几个字段：

```json
{
  "wechat": {
    "fetch_rule": { "mode": "recent_days", "value": 7 }
  },
  "email": {
    "recipient_emails": ["ops@example.com", "boss@example.com"]
  },
  "scheduler": {
    "enabled": true,
    "cron": "0 7 * * *"
  }
}
```

> `fetch_rule.mode` 可选 `recent_days` / `latest_count`；`value` 为对应的天数或篇数。`email.recipient_emails` 列表决定通知收件人，其他 SMTP 参数留在主配置即可。

常见调度场景：

| 需求 | `cron` 示例 |
|------|-------------|
| 每天 07:00 运行 | `0 7 * * *` |
| 每隔 2 小时运行 | `0 */2 * * *` |
| 每周一 09:30 运行 | `30 9 * * 1` |
| 每 5 天早上 08:00 运行 | `0 8 */5 * *` |

如需按固定间隔循环，可改用 `scheduler.interval_minutes`（例如 `120` 表示每 2 小时一次）。***

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
- [docs/BINARY_GUIDE.md](docs/BINARY_GUIDE.md)：二进制打包与部署

## 💬 支持

如需反馈缺陷或需求，可在 `docs/task_list.md` 记录或通过 issue 追踪。生产部署前请确保已阅读配置与故障排除文档，并完成一次真实数据的人工验收。***
