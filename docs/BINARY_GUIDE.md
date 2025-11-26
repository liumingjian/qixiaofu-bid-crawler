# 二进制打包与运行指南

目录结构已支持通过 PyInstaller 打包。以下步骤帮助你在不同操作系统迅速构建并运行独立可执行文件。

## 1. 准备环境

1. 安装 **Python 3.10+** 与对应的 pip。
2. 安装依赖（若尚未安装）：
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows 使用 .\.venv\Scripts\activate
   pip install -r requirements.txt
   pip install pyinstaller
   ```

## 2. 配置文件

- 内置默认配置无需额外文件；实际部署时只需准备 `custom.json`，填写业务变化项，例如：
  ```json
  {
    "wechat": {
      "fetch_rule": { "mode": "recent_days", "value": 7 }
    },
    "email": {
      "recipient_emails": ["ops@example.com"]
    },
    "scheduler": {
      "enabled": true,
      "cron": "0 7 * * *",
      "timezone": "Asia/Shanghai"
    }
  }
  ```
- `custom.json` **不会**被打包入可执行文件，运行时放在可执行文件同目录即可覆盖配置。若不想暴露该文件，可在启动命令前设置 `QIXIAOFU_CONFIG_JSON='{"wechat": {...}}'` 或指向私有路径 `QIXIAOFU_CONFIG_PATH=/path/secure_config.json`。

## 3. 打包

执行脚本会自动检测操作系统并生成对应二进制：
```bash
python scripts/package.py
```
输出位于 `dist/` 下，例如：
- `dist/qixiaofu-bid-crawler-windows.exe`
- `dist/qixiaofu-bid-crawler-macos`
- `dist/qixiaofu-bid-crawler-linux`

脚本默认打包 `web/templates`、`web/static` 以及 `config.json`。如需附带其他资源，可在 `scripts/package.py` 中追加 `--add-data`。

## 4. 部署 & 运行

1. 将二进制文件复制到目标服务器。
2. 将 `custom.json`、ChromeDriver（若需）以及 `web/` 所需资源放置在同一目录/相对路径。
3. 启动：
   ```bash
   chmod +x qixiaofu-bid-crawler-macos   # Linux/macOS
   ./qixiaofu-bid-crawler-macos
   # Windows 直接双击或在命令行运行
   ```
4. 浏览器访问 `http://<server>:5000` 管理界面，或依托配置好的 scheduler 自动运行。

## 5. 调度示例

在 `custom.json` 的 `scheduler` 段配置以下任一规则：

| 场景 | 配置 |
|------|------|
| 每天 07:00 运行 | `"cron": "0 7 * * *"` |
| 每隔 2 小时运行 | `"cron": "0 */2 * * *"` |
| 每周一 09:30 运行 | `"cron": "30 9 * * 1"` |
| 每隔 5 天 08:00 运行 | `"cron": "0 8 */5 * *"` |
| 每 90 分钟运行 | `"interval_minutes": 90`（可与 `cron` 二选一） |

## 6. 常见问题

- **custom.json 没生效？** 确保文件与可执行文件同目录，且内容为合法 JSON。
- **打包后模板丢失？** 检查 `scripts/package.py` 中 `--add-data` 是否覆盖 `web/templates`、`web/static`。
- **缺少 ChromeDriver/浏览器？** 打包不包含第三方浏览器，请在目标机上安装对应版本并确保 PATH 可访问。

完成以上步骤，即可在任何支持的操作系统上使用独立可执行文件运行招标信息爬虫。***
