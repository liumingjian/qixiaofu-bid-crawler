# 配置说明

项目所有运行参数集中在 `config.json`。以下为各字段含义及示例。

## 顶层结构

```json
{
  "wechat": {},
  "email": {},
  "scraper": {},
  "paths": {},
  "logging": {}
}
```

## wechat

| 字段 | 类型 | 说明 |
|------|------|------|
| `account_name` | string | 公众号名称，例如 “取七小服公众号” |
| `max_articles_per_crawl` | int | 单次最大抓取文章数，建议 30~50 |

## email

| 字段 | 类型 | 说明 |
|------|------|------|
| `smtp_server` | string | SMTP 服务器，如 `smtp.gmail.com` |
| `smtp_port` | int | 端口（587/TLS 或 465/SSL） |
| `sender_email` | string | 发件邮箱 |
| `sender_password` | string | 邮箱授权码/App Password |
| `recipient_emails` | list | 接收人数组，可配置多个 |
| `timeout` | int (可选) | SMTP 超时（秒），默认 30 |

## scraper

| 字段 | 类型 | 说明 |
|------|------|------|
| `headless` | bool | 是否启用无头浏览器（首次运行建议 False） |
| `wait_time` | int | 打开文章后等待的秒数 |
| `retry_count` | int | 失败重试次数 |
| `retry_delay` | int | 重试间隔 |
| `random_delay_range` | [int, int] | 随机延迟范围（秒） |
| `prompt_on_captcha` | bool | 检测到验证码时是否暂停等待人工完成 |

## paths

| 字段 | 类型 | 说明 |
|------|------|------|
| `data_dir` | string | 数据文件目录，默认 `data` |
| `log_dir` | string | 日志目录，默认 `data/logs` |

建议在生产环境中将 `data` 指向持久化磁盘，以防容器或服务器重启导致数据丢失。

## logging

| 字段 | 类型 | 说明 |
|------|------|------|
| `level` | string | `DEBUG`/`INFO`/`WARNING` 等日志级别 |

## 多环境配置

可在部署脚本中设置 `CONFIG_PATH` 环境变量，并在 `app.py` 或 CLI 中传入对应路径，以区别测试/生产配置。

## 配置校验

运行 `python - <<'PY' ...` 快速检测：

```python
import json
from pathlib import Path
cfg = json.loads(Path("config.json").read_text(encoding="utf-8"))
assert cfg["wechat"]["account_name"]
assert cfg["email"]["recipient_emails"], "应至少配置一个收件人"
print("配置校验成功")
```

若需要针对不同账号运行，可准备多个配置文件并在启动脚本中选择。***
