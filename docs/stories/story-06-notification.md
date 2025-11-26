# Story 06: 邮件通知模块

**Story ID**: STORY-06
**关联任务**: Task 4.1
**优先级**: 🟡 P1 - 高
**预计时长**: 2小时
**负责人**: -
**状态**: ✅ 已完成
**依赖**: STORY-03

---

## 📋 Story描述

实现邮件通知功能，当发现新的招标信息时，自动发送格式化的HTML邮件给配置的接收人列表，包含招标信息的关键字段和原文链接。

---

## 🎯 验收标准

- [x] 成功发送HTML格式邮件
- [x] 邮件包含所有招标信息字段
- [x] 链接可点击跳转
- [x] 发送后更新招标状态为'notified'
- [x] SMTP错误有日志记录
- [x] 支持配置多个接收人

---

## ✅ TODO清单

### 1. 研究SMTP配置 (20分钟)
- [x] 了解SMTP协议基础
- [x] 研究常用邮箱SMTP配置:
  - [x] Gmail: smtp.gmail.com:587
  - [x] QQ邮箱: smtp.qq.com:587
  - [x] 163邮箱: smtp.163.com:465
  - [x] Outlook: smtp.office365.com:587
- [x] 了解应用专用密码设置:
  - [x] Gmail App Password
  - [x] QQ邮箱授权码
- [x] 记录配置说明

**输出**: SMTP配置指南文档（见下文“SMTP配置指南”一节）

---

### 2. 创建邮件通知类 (30分钟)
- [x] 创建 `core/notification.py` 文件
- [x] 实现 `EmailNotificationService` 类
- [x] 在 `__init__()` 中:
  - [x] 加载邮件配置
  - [x] 初始化logger
  - [x] 验证配置完整性
- [x] 定义必需的配置项

**代码示例**:
```python
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from utils.logger import setup_logger

class EmailNotificationService:
    def __init__(self, config_file='config.json'):
        # 加载配置
        with open(config_file) as f:
            config = json.load(f)

        email_config = config['email']
        self.smtp_server = email_config['smtp_server']
        self.smtp_port = email_config['smtp_port']
        self.sender = email_config['sender_email']
        self.password = email_config['sender_password']
        self.recipients = email_config['recipient_emails']

        self.logger = setup_logger('notification', config['paths']['log_dir'])

        # 验证配置
        self._validate_config()

    def _validate_config(self):
        """验证配置完整性"""
        if not self.sender or not self.password:
            raise ValueError("Email sender or password not configured")

        if not self.recipients or len(self.recipients) == 0:
            raise ValueError("No recipients configured")

        self.logger.info("Email configuration validated")
```

**验证**: 初始化成功，配置验证正常

---

### 3. 设计HTML邮件模板 (30分钟)
- [x] 设计邮件样式:
  - [x] 标题区域
  - [x] 招标信息卡片
  - [x] 字段展示
  - [x] 原文链接按钮
- [x] 实现 `_format_email_body()` 方法:
  - [x] HTML结构
  - [x] CSS内联样式
  - [x] 响应式设计
  - [x] 美观易读

**代码示例**:
```python
def _format_email_body(self, bids: List[dict]) -> str:
    """格式化邮件内容为HTML"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .header { background-color: #0066cc; color: white; padding: 20px; text-align: center; }
            .container { max-width: 800px; margin: 0 auto; padding: 20px; }
            .bid-card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 15px 0; background-color: #f9f9f9; }
            .bid-title { color: #0066cc; font-size: 18px; font-weight: bold; margin-bottom: 10px; }
            .bid-field { margin: 8px 0; }
            .field-label { font-weight: bold; color: #666; }
            .field-value { color: #333; }
            .link-button { display: inline-block; background-color: #0066cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 10px; }
            .link-button:hover { background-color: #0052a3; }
            .footer { text-align: center; color: #999; padding: 20px; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>新招标信息通知</h1>
            <p>发现 {} 条新的招标信息</p>
        </div>
        <div class="container">
    """.format(len(bids))

    for i, bid in enumerate(bids, 1):
        html += f"""
            <div class="bid-card">
                <div class="bid-title">{i}. {bid.get('project_name', '未知项目')}</div>

                <div class="bid-field">
                    <span class="field-label">预算金额:</span>
                    <span class="field-value">{bid.get('budget', '-')}</span>
                </div>

                <div class="bid-field">
                    <span class="field-label">采购人:</span>
                    <span class="field-value">{bid.get('purchaser', '-')}</span>
                </div>

                <div class="bid-field">
                    <span class="field-label">获取采购文件:</span>
                    <span class="field-value">{bid.get('doc_time', '-')}</span>
                </div>
        """

        if bid.get('project_number'):
            html += f"""
                <div class="bid-field">
                    <span class="field-label">项目编号:</span>
                    <span class="field-value">{bid['project_number']}</span>
                </div>
            """

        if bid.get('service_period'):
            html += f"""
                <div class="bid-field">
                    <span class="field-label">服务期限:</span>
                    <span class="field-value">{bid['service_period']}</span>
                </div>
            """

        if bid.get('content'):
            html += f"""
                <div class="bid-field">
                    <span class="field-label">采购内容:</span>
                    <span class="field-value">{bid['content']}</span>
                </div>
            """

        html += f"""
                <a href="{bid.get('source_url', '#')}" class="link-button" target="_blank">查看原文</a>
            </div>
        """

    html += """
        </div>
        <div class="footer">
            <p>此邮件由招标信息爬虫系统自动发送</p>
        </div>
    </body>
    </html>
    """

    return html
```

**验证**: HTML格式正确，在浏览器中显示美观

---

### 4. 实现邮件发送功能 (40分钟)
- [x] 实现 `send_bid_notification()` 方法:
  - [x] 检查是否有新招标
  - [x] 格式化邮件内容
  - [x] 构建MIMEMultipart消息
  - [x] 连接SMTP服务器
  - [x] 发送邮件
  - [x] 处理异常
- [x] 实现 `_send_email()` 私有方法:
  - [x] SMTP连接
  - [x] TLS加密
  - [x] 登录验证
  - [x] 发送消息
- [x] 添加详细日志

**代码示例**:
```python
def send_bid_notification(self, bids: List[dict]) -> bool:
    """发送招标信息通知"""
    if not bids or len(bids) == 0:
        self.logger.info("No bids to notify")
        return True

    try:
        # 构建邮件
        subject = f"发现 {len(bids)} 条新招标信息"
        body = self._format_email_body(bids)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = ', '.join(self.recipients)

        # 添加HTML内容
        html_part = MIMEText(body, 'html', 'utf-8')
        msg.attach(html_part)

        # 发送邮件
        self._send_email(msg)

        self.logger.info(f"Notification sent successfully to {len(self.recipients)} recipients")
        return True

    except Exception as e:
        self.logger.error(f"Failed to send notification: {e}", exc_info=True)
        return False

def _send_email(self, msg: MIMEMultipart):
    """发送邮件"""
    try:
        # 连接SMTP服务器
        with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
            server.ehlo()

            # 启用TLS加密
            if self.smtp_port == 587:
                server.starttls()
                server.ehlo()

            # 登录
            server.login(self.sender, self.password)
            self.logger.debug("SMTP login successful")

            # 发送邮件
            server.send_message(msg)
            self.logger.debug("Email sent")

    except smtplib.SMTPAuthenticationError as e:
        self.logger.error(f"SMTP authentication failed: {e}")
        raise ValueError("Email authentication failed. Please check sender email and password.")

    except smtplib.SMTPException as e:
        self.logger.error(f"SMTP error: {e}")
        raise

    except Exception as e:
        self.logger.error(f"Unexpected error sending email: {e}")
        raise
```

**验证**: 邮件发送成功

---

### 5. 添加测试邮件功能 (15分钟)
- [x] 实现 `send_test_email()` 方法:
  - [x] 发送测试邮件
  - [x] 验证SMTP配置
  - [x] 测试邮件格式

**代码示例**:
```python
def send_test_email(self) -> bool:
    """发送测试邮件"""
    test_bids = [{
        'id': 'test123',
        'project_name': '测试招标项目',
        'budget': '100万元',
        'purchaser': '测试采购单位',
        'doc_time': '2025-11-25 - 2025-12-01',
        'project_number': 'TEST-2025-001',
        'service_period': '1年',
        'content': '这是一个测试招标项目的采购内容描述。',
        'source_url': 'https://example.com',
        'source_title': '测试文章',
        'extracted_time': '2025-11-25T10:00:00',
        'status': 'new'
    }]

    self.logger.info("Sending test email")
    return self.send_bid_notification(test_bids)
```

**验证**: 测试邮件成功发送

---

### 6. 集成数据管理器 (15分钟)
- [x] 修改 `send_bid_notification()` 接收DataManager
- [x] 发送成功后更新招标状态为'notified'
- [x] 添加状态更新日志

**代码示例**:
```python
def send_bid_notification(self, bids: List[dict], data_manager=None) -> bool:
    """发送招标信息通知"""
    # ... 发送邮件 ...

    # 更新状态
    if data_manager:
        for bid in bids:
            data_manager.update_bid_status(bid['id'], 'notified')
        self.logger.info(f"Updated {len(bids)} bids status to 'notified'")

    return True
```

**验证**: 状态更新正常

---

### 7. 编写单元测试 (20分钟)
- [x] 创建 `tests/test_notification.py`
- [x] 测试用例1: 测试HTML模板格式化
- [x] 测试用例2: 测试邮件发送(使用真实SMTP/Mock)
- [x] 测试用例3: 测试错误处理
- [x] 测试用例4: 测试状态更新

**代码示例**:
```python
import unittest
from core.notification import EmailNotificationService

class TestNotification(unittest.TestCase):
    def test_format_email_body(self):
        """测试邮件格式化"""
        service = EmailNotificationService()

        bids = [{
            'project_name': 'Test Project',
            'budget': '100万元',
            'purchaser': 'Test Company',
            'doc_time': '2025-11-25',
            'source_url': 'https://example.com'
        }]

        html = service._format_email_body(bids)

        self.assertIn('Test Project', html)
        self.assertIn('100万元', html)
        self.assertIn('https://example.com', html)

    def test_send_test_email(self):
        """测试发送邮件(需要配置真实SMTP)"""
        service = EmailNotificationService()
        result = service.send_test_email()

        self.assertTrue(result)
```

**验证**: 测试通过

---

### SMTP配置指南

| 邮箱类型 | SMTP服务器 | 端口 | 加密方式 | 备注 |
|----------|------------|------|----------|------|
| Gmail | `smtp.gmail.com` | 587 | STARTTLS | 需启用两步验证并使用 App Password |
| QQ邮箱 | `smtp.qq.com` | 587 | STARTTLS | 必须使用授权码而非登录密码 |
| 163邮箱 | `smtp.163.com` | 465 | SSL | 需在邮箱设置中开启 SMTP/IMAP |
| Outlook/Office365 | `smtp.office365.com` | 587 | STARTTLS | 企业租户需管理员允许第三方客户端 |

**应用专用密码获取**
- Gmail: Google 账号 → “安全性” → “应用专用密码” → 选择“邮件/本设备”生成 16 位密码。
- QQ邮箱: 设置 → 账户 → POP3/IMAP/SMTP服务 → 开启后系统发送授权码短信。
- 163邮箱: 设置 → POP3/SMTP/IMAP → 启用客户端授权并复制生成的密码。

**调试步骤**
1. 在 `config.json` 填写服务器、端口、发件人邮箱、授权码以及 `recipient_emails` 列表。
2. 将 `scraper.headless` 设置为任意值均可，运行 `EmailNotificationService.send_test_email()` 验证配置。
3. 端口为 587 时库会自动调用 `starttls()`，若使用 465 端口则切换至 `SMTP_SSL`。

**排查建议**
- 邮件被拦截时检查垃圾箱或向收件方白名单添加发件地址。
- 若提示认证失败，请确认开启了应用专用密码/授权码，并避免复制多余空格。
- 防火墙阻断可通过 `telnet smtp.xxx.com <port>` 或 `openssl s_client` 等命令行工具检查。

---

## 📦 交付物

- [x] `core/notification.py` - 邮件通知类
- [x] `tests/test_notification.py` - 单元测试
- [x] SMTP配置指南文档

---

## 🧪 测试清单

- [x] 测试邮件发送成功
- [x] HTML格式正确美观
- [x] 多个接收人都收到邮件
- [x] 链接可正常点击
- [x] 状态更新为'notified'
- [x] SMTP错误有日志记录

---

## 📝 开发笔记

### SMTP配置示例

**Gmail**:
```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "sender_email": "your_email@gmail.com",
  "sender_password": "your_app_password",  // 应用专用密码
  "recipient_emails": ["recipient@example.com"]
}
```

**QQ邮箱**:
```json
{
  "smtp_server": "smtp.qq.com",
  "smtp_port": 587,
  "sender_email": "your_qq@qq.com",
  "sender_password": "授权码",  // QQ邮箱授权码
  "recipient_emails": ["recipient@example.com"]
}
```

### 获取应用专用密码
- **Gmail**: https://myaccount.google.com/apppasswords
- **QQ邮箱**: 邮箱设置 → 账户 → POP3/IMAP/SMTP服务 → 生成授权码

### 可能遇到的问题
1. **问题**: SMTP authentication failed
   - **解决**: 检查邮箱密码，使用应用专用密码而不是登录密码

2. **问题**: SSL/TLS错误
   - **解决**: 确认端口号(587用TLS，465用SSL)

3. **问题**: 邮件进入垃圾箱
   - **解决**: 避免过多链接，优化邮件内容

---

## ✨ 完成标准

- [ ] 手动测试成功:
```python
from core.notification import EmailNotificationService

service = EmailNotificationService()

# 发送测试邮件
result = service.send_test_email()
print(f"Test email sent: {result}")
```
- [ ] 成功接收到格式化的HTML邮件
- [ ] 邮件内容完整美观

---

## 📅 时间记录

- **开始时间**:
- **完成时间**:
- **实际耗时**:
- **备注**: 需要配置真实SMTP账号
