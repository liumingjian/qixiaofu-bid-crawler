# 安装指南

本文档描述如何在新环境中部署“微信公众号招标信息爬虫系统”。

## 1. 环境准备

1. 安装 Python 3.10 及以上版本。
2. 安装 Google Chrome，并确保版本与 ChromeDriver 匹配。
3. 克隆或下载项目源代码：
   ```bash
   git clone <repo-url> webchat-crawer
   cd webchat-crawer
   ```

## 2. 创建虚拟环境

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
source .venv/bin/activate      # macOS/Linux
```

## 3. 安装依赖

```bash
pip install -r requirements.txt
```

如需指定国内镜像，可在命令后追加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`。

## 4. 浏览器驱动

1. 下载与 Chrome 版本一致的 ChromeDriver。
2. 将其放入系统 PATH，或在运行脚本前设置 `webdriver.chrome.driver` 环境变量。

## 5. 配置文件

复制 `config.json` 并填写：

```bash
copy config.json config.local.json  # Windows
```

在 `config.local.json` 中配置公众号名称、爬取数量、SMTP 信息等，详见 `CONFIGURATION.md`。

## 6. 初始化数据目录

```bash
mkdir data
mkdir data/logs
```

首次运行时程序会自动创建 `data/articles.json` 与 `data/bids.json`，无需手动编写。

## 7. 运行测试

```bash
python -m pytest tests/
```

确保所有测试通过后再部署到生产环境。

## 8. 启动应用

```bash
python app.py
```

浏览器访问 `http://localhost:5000` 进行操作。

## 9. 后续部署

- 建议将 `app.py` 通过 Gunicorn + Nginx 或 Windows 服务托管。
- 如需定时执行爬虫，可使用 Windows 任务计划或 Linux cron。

完成上述步骤后，系统即可投入使用。***
