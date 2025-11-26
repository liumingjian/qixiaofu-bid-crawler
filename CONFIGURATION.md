# 配置说明

项目所有运行参数集中在 `config.json`。以下为各字段含义及示例。

> 配置合并顺序：内置默认 (`core/default_config.py`) → 可选 `config.json` → 可选 `custom.json` → 可选环境变量 (`QIXIAOFU_CONFIG_JSON` 或 `QIXIAOFU_CONFIG_PATH`)。因此在真实部署中可以仅提供 `custom.json`/环境变量，避免暴露完整配置文件。

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
| `account_name` | string | 仅用于日志显示，可与后台账号名称保持一致 |
| `max_articles_per_crawl` | int | 单次最大抓取文章数，建议 30~50 |
| `fakeid` | string | 公众号后台请求标识，可在浏览器地址栏 `fakeid=` 参数中获取 |
| `token` | string | 登录后台后附带的 token，同样来自地址栏 `token=` 参数 |
| `cookie` | string | 登录 `mp.weixin.qq.com` 后的完整 Cookie 字符串，需要定期更新 |
| `user_agent` | string | 发送请求的 UA，默认为桌面 Chrome |
| `page_size` | int | 每次向 `appmsg` 接口请求的条数，默认 5 |
| `days_limit` | int | 仅抓取最近 N 天的文章，设为 0 表示不限制 |
| `keyword_filters` | list | 标题关键词过滤，空数组表示不过滤 |
| `request_interval_range` | [int, int] | 请求间隔的随机范围，单位秒 |
| `request_timeout` | int | 请求超时秒数，默认 10 |
| `retry_count` / `retry_delay` | int | 接口失败重试次数及等待间隔 |
| `rate_limit_wait` | int | 遇到 ret=200013（频率限制）后的等待秒数 |
| `fetch_rule.mode` | string | `recent_days`（按天）或 `latest_count`（按数量） |
| `fetch_rule.value` | int | `mode` 对应参数，例如最近 7 天或最新 50 篇 |

> **提示**：登录 https://mp.weixin.qq.com/ 后打开“内容管理-图文消息”，浏览器地址栏中即可看到 `token` 与 `fakeid`，同时使用开发者工具复制整段请求 Cookie。上述三项缺一不可，且 Cookie 需要在过期后重新获取。

## email

| 字段 | 类型 | 说明 |
|------|------|------|
| `smtp_server` | string | SMTP 服务器，如 `smtp.gmail.com` |
| `smtp_port` | int | 端口（587/TLS 或 465/SSL） |
| `sender_email` | string | 发件邮箱 |
| `sender_password` | string | 邮箱授权码/App Password |
| `recipient_emails` | list | 接收人数组，可配置多个 |
| `timeout` | int (可选) | SMTP 超时（秒），默认 30 |

## scheduler

| 字段 | 类型 | 说明 |
|------|------|------|
| `enabled` | bool | 是否开启自动调度 |
| `cron` | string | 标准 crontab 表达式，例如 `0 7 * * *`（每天 07:00） |
| `daily_time` | string | (可选) 兼容旧配置，自动转换为 cron 表达式 |
| `timezone` | string | 时区名称，默认 `Asia/Shanghai` |
| `interval_minutes` | number/null | 设置后按间隔循环触发，优先级高于 `daily_time` |

调度器在任务运行过程中会自动跳过下一次计划，避免并发。

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
