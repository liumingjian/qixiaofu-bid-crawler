# Story 01: 项目环境初始化

**Story ID**: STORY-01
**关联任务**: Task 1.1
**优先级**: 🔴 P0 - 最高
**预计时长**: 0.5小时
**负责人**: -
**状态**: ✅ 已完成

---

## 📋 Story描述

作为开发者，我需要搭建项目的基础架构和开发环境，创建必要的目录结构、配置文件和工具模块，以便后续模块开发。

---

## 🎯 验收标准

- [x] 目录结构创建完整
- [x] 依赖安装成功: `pip install -r requirements.txt`
- [x] config.json包含所有必要配置项且格式正确
- [x] logger工具可正常使用
- [x] README.md更新完整

---

## ✅ TODO清单

### 1. 创建目录结构 (10分钟)
- [x] 创建 `core/` 目录
  - [x] 创建 `core/__init__.py`
- [x] 创建 `storage/` 目录
  - [x] 创建 `storage/__init__.py`
- [x] 创建 `web/` 目录
  - [x] 创建 `web/static/css/` 目录
  - [x] 创建 `web/static/js/` 目录
  - [x] 创建 `web/templates/` 目录
- [x] 创建 `data/` 目录
  - [x] 创建 `data/logs/` 目录
- [x] 创建 `utils/` 目录
  - [x] 创建 `utils/__init__.py`
- [x] 创建 `tests/` 目录
  - [x] 创建 `tests/__init__.py`

**验证**: 运行 `ls -R` 确认所有目录存在

---

### 2. 配置requirements.txt (5分钟)
- [x] 创建 `requirements.txt` 文件
- [x] 添加依赖项:
  - [x] `flask==3.0.0`
  - [x] `selenium==4.16.0`
  - [x] `beautifulsoup4==4.12.2`
  - [x] `webdriver-manager==4.0.1`
  - [x] `requests==2.31.0`
- [x] 测试安装: `pip install -r requirements.txt`

**验证**: 所有包安装成功，无错误

---

### 3. 创建config.json (10分钟)
- [x] 创建 `config.json` 文件
- [x] 添加微信公众号配置:
  ```json
  "wechat": {
    "account_name": "取七小服公众号",
    "max_articles_per_crawl": 50
  }
  ```
- [x] 添加邮件配置:
  ```json
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "",
    "sender_password": "",
    "recipient_emails": []
  }
  ```
- [x] 添加爬虫配置:
  ```json
  "scraper": {
    "headless": true,
    "wait_time": 5,
    "retry_count": 3,
    "retry_delay": 5,
    "random_delay_range": [2, 5]
  }
  ```
- [x] 添加路径配置:
  ```json
  "paths": {
    "data_dir": "data",
    "log_dir": "data/logs"
  }
  ```
- [x] 验证JSON格式: `python -m json.tool config.json`

**验证**: JSON格式正确，可被Python读取

---

### 4. 创建日志工具 (10分钟)
- [x] 创建 `utils/logger.py` 文件
- [x] 实现 `setup_logger()` 函数
  - [x] 支持同时输出到控制台和文件
  - [x] 文件路径从config读取
  - [x] 日志格式: `[时间] [级别] [模块] 消息`
  - [x] 支持日志级别配置(DEBUG/INFO/WARNING/ERROR)
- [x] 创建测试代码验证功能
- [x] 在 `data/logs/` 下生成测试日志文件

**代码示例**:
```python
import logging
import os
from datetime import datetime

def setup_logger(name, log_dir="data/logs", level=logging.INFO):
    """设置日志器"""
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 文件处理器
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # 格式化
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
```

**验证**:
- 日志同时输出到控制台和文件
- 日志格式正确
- 日志文件可读

---

### 5. 初始化数据文件 (5分钟)
- [x] 创建 `data/articles.json`，内容为空数组: `[]`
- [x] 创建 `data/bids.json`，内容为空数组: `[]`
- [x] 验证JSON格式正确

**验证**: 文件可被Python正常读取

---

### 6. 更新README.md (10分钟)
- [x] 添加项目简介
- [x] 添加功能特性列表
- [x] 添加安装步骤:
  - [x] Python版本要求
  - [x] 依赖安装
  - [x] 配置文件设置
- [x] 添加快速开始指南
- [x] 添加目录结构说明
- [x] 添加许可和免责声明

**验证**: README清晰易懂，可指导新用户使用

---

## 📦 交付物

- [x] 完整的目录结构
- [x] `requirements.txt` - Python依赖清单
- [x] `config.json` - 系统配置文件
- [x] `utils/logger.py` - 日志工具模块
- [x] `data/articles.json` - 文章数据文件
- [x] `data/bids.json` - 招标数据文件
- [x] `README.md` - 项目说明文档

---

## 🧪 测试清单

- [x] 所有目录正常创建
- [x] `pip install -r requirements.txt` 成功
- [x] 导入logger模块成功: `from utils.logger import setup_logger`
- [x] 创建logger实例成功: `logger = setup_logger('test')`
- [x] 写入日志成功: `logger.info('Test message')`
- [x] 日志文件生成在 `data/logs/` 目录
- [x] config.json可被读取: `json.load(open('config.json'))`

---

## 📝 开发笔记

### 注意事项
- 确保Python版本 ≥ 3.8
- Windows系统路径使用反斜杠，需要处理
- 日志文件编码设置为UTF-8，避免中文乱码
- config.json不提交敏感信息(邮箱密码等)，创建config.example.json模板

### 可能遇到的问题
1. **问题**: pip安装selenium失败
   - **解决**: 升级pip: `python -m pip install --upgrade pip`

2. **问题**: 日志文件权限错误
   - **解决**: 确保data/logs目录有写权限

3. **问题**: JSON格式错误
   - **解决**: 使用在线JSON验证工具检查

---

## ✨ 完成标准

- [x] 运行 `pip install -r requirements.txt` 无错误
- [x] 运行以下测试代码无错误:
```python
import json
from utils.logger import setup_logger

# 测试配置文件
with open('config.json') as f:
    config = json.load(f)
    print("Config loaded:", config['wechat']['account_name'])

# 测试日志
logger = setup_logger('test')
logger.info('Project setup complete!')
```
- [x] README.md完整可读
- [x] 目录结构符合设计

---

## 📅 时间记录

- **开始时间**: 2025-11-25 21:50
- **完成时间**: 2025-11-25 22:30
- **实际耗时**: 0.7小时
- **备注**: 初版环境与文档均已建立，可直接推进核心模块开发。
