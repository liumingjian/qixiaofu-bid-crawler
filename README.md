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
在程序同级目录下创建一个名为 `custom.json` 的文件，填入您的微信公众号参数和接收邮箱：

```json
{
  "wechat": {
    "fakeid": "您的公众号fakeid",
    "token": "您的token",
    "cookie": "您的完整cookie"
  },
  "email": {
    "recipient_emails": ["your_email@example.com"]
  }
}
```

> **如何获取微信参数？**
> 1. 登录 [微信公众平台](https://mp.weixin.qq.com/)。
> 2. 进入“图文消息”页面，URL 中的 `fakeid` 和 `token` 即为所需参数。
> 3. 按 F12 打开开发者工具，刷新页面，在 Network 面板找到任意请求，复制其 `Cookie`。

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

除了 `custom.json`，您还可以通过环境变量或修改 `config.json` 进行更多配置。

*   **定时任务**: 在配置中设置 `scheduler.enabled: true` 和 `cron` 表达式即可开启自动定时抓取。
*   **抓取策略**: 修改 `wechat.fetch_rule` 可设定只抓取最近 N 天或最新 N 篇文章。

## 📂 数据与日志

*   **数据文件**: 抓取的文章和招标信息保存在 `data/articles.json` 和 `data/bids.json`。
*   **运行日志**: 详细日志位于 `data/logs/` 目录下。
