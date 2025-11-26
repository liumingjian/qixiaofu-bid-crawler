# 故障排除指南

| 问题 | 可能原因 | 解决方案 |
|------|-----------|----------|
| 启动时报 `No module named pytest` | 虚拟环境未安装依赖 | 激活 `.venv` 后执行 `pip install -r requirements.txt` |
| 浏览器窗口一直停在验证码 | 首次访问需人工验证 | 在控制台提示时完成验证码并敲回车，系统会保存 Cookie |
| `selenium.common.exceptions.SessionNotCreatedException` | ChromeDriver 版本与浏览器不匹配 | 下载与 Chrome 版本一致的驱动 |
| `SMTPAuthenticationError` | 邮箱未启用“应用专用密码” | 按照 `CONFIGURATION.md` 设置授权码，勿直接使用登录密码 |
| Web 页面不显示数据 | API 未返回成功 | 打开浏览器 DevTools -> Network 检查 `/api/bids` 响应，查看 `data/logs/` 下日志 |
| “爬取任务已在运行中” | 上一轮任务尚未结束 | 等待状态栏提示完成，或重启服务清空状态 |
| JSON 文件损坏 | 非正常退出导致 | 删除 `data/articles.json`/`data/bids.json` 并从备份恢复，或手动修复 JSON 结构 |

## 常用诊断命令

```bash
tail -f data/logs/YYYYMMDD.log  # 实时查看日志
python -m pytest tests/test_e2e.py -v  # 验证端到端流程
python -m pytest tests/test_performance.py -v  # 快速性能基线
```

## 提升稳定性

- 启用代理或限速以降低被屏蔽概率。
- 定期清理 `data/logs`，防止日志过大。
- 将 `config.json` 置于安全位置并限制权限，避免凭据泄露。

如遇无法定位的问题，请附带日志与配置（脱敏处理）进行反馈。***
