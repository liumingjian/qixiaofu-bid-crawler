# Quickstart

用以下步骤在 5 分钟内启动“微信公众号招标信息爬虫系统”。

## 1. 环境准备
- **Python 3.10+**
- **Google Chrome + ChromeDriver**
- Windows PowerShell（示例命令）或任何兼容 shell

## 2. 获取代码并安装依赖
```powershell
git clone <repo-url> webchat-crawer
cd webchat-crawer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. 配置
1. 打开 `config.json`，在 `wechat` 段填写：
   - `account_name`：仅用于日志显示。
   - `fakeid/token/cookie`：登录 https://mp.weixin.qq.com/ 后在“内容管理 - 图文消息”页面获取；`token` 与 `fakeid` 位于地址栏参数，Cookie 需在 Network 面板复制整段字符串。
   - `user_agent`、`max_articles_per_crawl`、`keyword_filters`、`days_limit` 等按照需求调整。
2. 配置 `email.*`（SMTP、发件人、收件人）以便发送通知；`scraper.headless` 首次调试建议设为 `false`，观察浏览器执行情况。
3. 确认 `paths.data_dir`、`paths.log_dir` 存在或可创建；如需区分环境，可复制为 `config.local.json` 并在启动命令中指定。

## 4. 快速验证
```powershell
# 单元测试 + 集成测试（使用模拟数据）
python -m pytest tests/

# 仅运行端到端流程（Fake fetcher+scraper）
python -m pytest tests/test_e2e.py -v
```
如出现 `captcha` 提示，请在浏览器窗口手动完成验证后回到控制台按 Enter。

## 5. 启动 Web 管理界面
```powershell
python app.py
```
访问 `http://localhost:5000`：
1. 点击 **“开始爬取”** 按钮触发后台任务。
2. 通过顶部 Tab 筛选 “全部 / 新发现 / 已通知”。
3. 状态栏显示实时进度，完成后可在卡片上点击 “查看原文”。

## 6. 常用命令
| 目标 | 命令 |
|------|------|
| 重置数据 | 删除 `data/articles.json`、`data/bids.json` |
| 查看日志 | `Get-Content data/logs/YYYYMMDD.log -Tail 30 -Wait` |
| 手动发送测试邮件 | 在 Python REPL 中 `EmailNotificationService().send_test_email()` |
| API 调试 | `curl http://localhost:5000/api/bids?status=new` |

## 7. 下一步
- 阅读 [INSTALL.md](INSTALL.md) 以了解生产部署细节。
- 阅读 [CONFIGURATION.md](CONFIGURATION.md) 并申请正式 SMTP 凭据。
- 使用 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 诊断常见问题。

完成上述步骤后即可在内部环境中稳定运行并二次开发。祝使用顺利！***
