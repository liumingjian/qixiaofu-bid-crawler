# 微信公众号招标信息爬虫系统

一个自动化获取“七小服公众号”历史文章，智能提取招标信息（如预算、采购人、截止时间），并通过邮件和 Web 界面进行通知与管理的工具。

## ✨ 核心功能

*   **自动抓取**: 按关键词（如“招标”、“采购”）和时间范围批量获取公众号文章。
*   **智能提取**: 自动从文章文本中解析项目名称、预算金额、采购人等关键字段。
*   **邮件通知**: 发现新招标信息后自动发送 HTML 邮件通知。
*   **Web 管理**: 提供简洁的网页界面查看历史数据、运行状态和统计信息。
*   **开箱即用**: 支持打包为独立可执行文件，无需安装 Python 环境。

## 🚀 快速开始 (使用二进制文件)

如果您使用的是打包好的程序（如 `qixiaofu-bid-crawler-macos`），请按以下步骤操作：

### 1. 准备配置文件
在程序同级目录下创建一个名为 `custom.yml` 的文件，仅填写需要覆盖的配置项，例如：

```yaml
email:
  recipient_emails:
    - your_email@example.com
scheduler:
  enabled: true
  cron: "0 8 * * *"
```

默认公众号账号（七小服）已经保存在 `db/seed.sql` 中，首次启动会自动写入数据库。如需替换默认账号，请编辑 `db/seed.sql` 并重新启动；后续所有账号都可在 Web 界面「设置 → 数据源管理」中维护。

### 2. 运行程序
在终端中运行程序：

```bash
./qixiaofu-bid-crawler-macos
```

程序启动后，您可以访问 `http://localhost:5000` 查看 Web 界面。

## 🛠️ 编译与打包

如果您希望自己编译二进制文件，请务必在**虚拟环境**中进行，以避免依赖冲突。

1.  **创建并激活虚拟环境**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # macOS / Linux
    # 或 .\.venv\Scripts\Activate.ps1  # Windows
    ```

2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **执行打包**:
    ```bash
    pyinstaller qixiaofu-bid-crawler-macos.spec --clean --noconfirm
    ```

4.  **运行验证**:
    打包完成后，可执行文件位于 `dist/` 目录：
    ```bash
    ./dist/qixiaofu-bid-crawler-macos
    ```

## 💻 源码运行

如果您需要修改代码或在开发环境中运行：

1.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **启动应用**:
    ```bash
    python app.py
    ```

## ⚙️ 进阶配置

除了 `custom.yml`，您还可以通过环境变量或修改 `config.yml` 进行更多配置。

*   **定时任务**: 在配置中设置 `scheduler.enabled: true` 和 `cron` 表达式即可开启自动定时抓取。
*   **抓取策略**: 修改 `wechat.fetch_rule` 可设定只抓取最近 N 天或最新 N 篇文章。
*   **数据库管理**: 在 `config.yml` 中配置 `database.url`（或 `host`/`port`/`name` 等字段）即可将公众号账号与抓取到的文章/招标数据统一保存在数据库中。首启时系统会执行 `db/seed.sql` 将七小服等默认账号写入数据库，其余账号可在 Web 界面“数据源管理”中维护。

详细配置参数请参考 [配置指南](docs/guide/configuration.md)。

## 📂 数据与日志

*   **数据文件**: 启用数据库后，所有文章/招标数据都会写入数据库；仅在开发模式下未提供数据库配置时，才会落到 `data/articles.json` 与 `data/bids.json`。
*   **运行日志**: 详细日志位于 `data/logs/` 目录下。

## ❓ 常见问题

遇到问题？请查看 [故障排除指南](docs/guide/troubleshooting.md)。
