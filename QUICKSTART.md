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
1. 打开 `config.json`，填写：
   - `wechat.account_name`: 目标公众号名称
   - `email.*`: SMTP 信息与收件人
   - `scraper.headless`: 首次运行建议 `false`，便于通过验证码
2. 确认 `paths.data_dir`、`paths.log_dir` 存在或可创建。
3. 若需区分环境，可复制为 `config.local.json` 并在运行命令中指定。

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
