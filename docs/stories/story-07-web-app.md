# Story 07: Web管理界面

**Story ID**: STORY-07
**关联任务**: Task 4.2
**优先级**: 🟡 P1 - 高
**预计时长**: 5小时
**负责人**: -
**状态**: ✅ 已完成
**依赖**: STORY-02, STORY-03, STORY-04, STORY-05, STORY-06

---

## 📋 Story描述

开发Flask Web应用和前端界面，提供招标信息展示、爬取控制、系统设置等功能，实现完整的用户交互体验。

---

## 🎯 验收标准

- [x] API `/api/bids` 正常返回数据
- [x] API `/api/crawl/start` 能触发爬取任务
- [x] 页面能展示招标信息列表
- [x] 标签页切换(全部/新发现/已通知)正常
- [x] "开始爬取"按钮功能正常
- [x] 响应式布局，支持移动端
- [x] 页面加载时间 ≤ 2秒

---

## ✅ TODO清单

### 1. 创建Flask应用 (30分钟)
- [x] 创建 `app.py` 文件
- [x] 初始化Flask应用
- [x] 配置静态文件和模板目录
- [x] 加载系统配置
- [x] 初始化各模块实例:
  - [x] DataManager
  - [x] WeChatArticleScraper
  - [x] BidInfoExtractor
  - [x] EmailNotificationService
  - [x] SougouWeChatFetcher
- [x] 设置日志
- [x] 添加基础路由(首页)

**代码示例**:
```python
from flask import Flask, render_template, jsonify, request
import json
import threading
from core.data_manager import DataManager
from core.scraper import WeChatArticleScraper
from core.bid_extractor import BidInfoExtractor
from core.notification import EmailNotificationService
from core.article_fetcher import SougouWeChatFetcher
from utils.logger import setup_logger

app = Flask(__name__,
           template_folder='web/templates',
           static_folder='web/static')

# 加载配置
with open('config.json') as f:
    config = json.load(f)

# 初始化模块
data_manager = DataManager()
scraper = WeChatArticleScraper()
extractor = BidInfoExtractor()
notifier = EmailNotificationService()
fetcher = SougouWeChatFetcher()

logger = setup_logger('web_app', config['paths']['log_dir'])

# 爬取任务状态
crawl_status = {
    'is_running': False,
    'progress': 0,
    'total': 0,
    'message': ''
}

@app.route('/')
def index():
    """招标信息列表页"""
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**验证**: Flask应用启动成功

---

### 2. 实现API路由 (60分钟)
- [x] 在 `app.py` 中实现REST API
- [x] 实现 `GET /api/bids` - 获取招标信息列表:
  - [x] 支持status查询参数
  - [x] 返回JSON格式
- [x] 实现 `POST /api/crawl/start` - 启动爬取任务:
  - [x] 检查是否已有任务在运行
  - [x] 创建后台线程执行爬取
  - [x] 返回任务状态
- [x] 实现 `GET /api/crawl/status` - 查询爬取进度:
  - [x] 返回当前进度和状态
- [x] 实现 `GET /api/stats` - 获取统计信息:
  - [x] 返回文章数、招标数等统计
- [x] 添加错误处理

**代码示例**:
```python
@app.route('/api/bids')
def get_bids():
    """获取招标信息API"""
    try:
        status = request.args.get('status')
        bids = data_manager.get_all_bids(status)

        logger.info(f"API /api/bids called, returned {len(bids)} bids")
        return jsonify({
            'success': True,
            'data': bids,
            'count': len(bids)
        })

    except Exception as e:
        logger.error(f"API error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/crawl/start', methods=['POST'])
def start_crawl():
    """启动爬取任务"""
    global crawl_status

    if crawl_status['is_running']:
        return jsonify({
            'success': False,
            'message': '爬取任务已在运行中'
        })

    # 启动后台线程
    thread = threading.Thread(target=crawl_task)
    thread.daemon = True
    thread.start()

    logger.info("Crawl task started")
    return jsonify({
        'success': True,
        'message': '爬取任务已启动'
    })

@app.route('/api/crawl/status')
def get_crawl_status():
    """获取爬取状态"""
    return jsonify({
        'success': True,
        'data': crawl_status
    })

@app.route('/api/stats')
def get_stats():
    """获取统计信息"""
    try:
        stats = data_manager.get_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"Stats API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

**验证**: API调用正常返回数据

---

### 3. 实现爬取任务 (45分钟)
- [x] 实现 `CrawlRunner`/`CrawlController` 协调爬取:
  - [x] 更新任务状态
  - [x] 获取文章列表
  - [x] 过滤已爬取文章
  - [x] 批量爬取文章
  - [x] 提取招标信息
  - [x] 保存数据
  - [x] 发送邮件通知
  - [x] 错误处理
- [x] 实现进度更新
- [x] 添加详细日志

**代码示例**:
```python
def crawl_task():
    """爬取任务主流程"""
    global crawl_status

    try:
        # 初始化状态
        crawl_status['is_running'] = True
        crawl_status['progress'] = 0
        crawl_status['message'] = '正在获取文章列表...'
        logger.info("=== Crawl Task Started ===")

        # 1. 获取文章列表
        logger.info("Step 1: Fetching article list")
        article_list = fetcher.fetch_article_list(
            max_articles=config['wechat']['max_articles_per_crawl']
        )
        logger.info(f"Found {len(article_list)} articles")

        if not article_list:
            crawl_status['message'] = '未获取到文章列表'
            return

        # 2. 过滤已爬取
        new_articles = [a for a in article_list
                       if not data_manager.is_article_crawled(a['url'])]
        logger.info(f"New articles: {len(new_articles)}")

        crawl_status['total'] = len(new_articles)
        crawl_status['message'] = f'开始爬取 {len(new_articles)} 篇新文章...'

        if len(new_articles) == 0:
            crawl_status['message'] = '没有新文章需要爬取'
            return

        # 3. 批量爬取文章
        logger.info("Step 2: Crawling articles")

        def progress_callback(index, total, article_data):
            crawl_status['progress'] = index
            crawl_status['message'] = f'正在爬取: {article_data.get("title", "")[:30]}...'

        articles_data = scraper.scrape_articles_batch(
            [a['url'] for a in new_articles],
            callback=progress_callback
        )
        logger.info(f"Crawled {len(articles_data)} articles")

        # 4. 提取招标信息
        logger.info("Step 3: Extracting bid information")
        crawl_status['message'] = '正在提取招标信息...'

        all_new_bids = []
        for article_data in articles_data:
            # 提取招标
            bids = extractor.extract_from_text(
                article_data['content_text'],
                article_data
            )

            # 保存招标(去重)
            new_bids = data_manager.save_bids(bids)
            all_new_bids.extend(new_bids)

            # 保存文章
            data_manager.save_article(article_data)

        logger.info(f"Extracted {len(all_new_bids)} new bids")

        # 5. 发送通知
        if all_new_bids:
            logger.info("Step 4: Sending notification")
            crawl_status['message'] = '正在发送邮件通知...'

            notifier.send_bid_notification(all_new_bids, data_manager)
            logger.info("Notification sent")

        # 完成
        crawl_status['message'] = f'爬取完成! 发现 {len(all_new_bids)} 条新招标信息'
        logger.info("=== Crawl Task Completed ===")

    except Exception as e:
        crawl_status['message'] = f'爬取失败: {str(e)}'
        logger.error(f"Crawl task failed: {e}", exc_info=True)

    finally:
        crawl_status['is_running'] = False
```

**验证**: 爬取任务完整流程正常

---

### 4. 创建HTML模板 (90分钟)
- [x] 创建 `web/templates/base.html` - 基础模板:
  - [x] HTML结构
  - [x] 引入Bootstrap CSS
  - [x] 引入自定义CSS
  - [x] 引入JavaScript
- [x] 创建 `web/templates/index.html` - 招标信息列表页:
  - [x] 导航栏
  - [x] 标签页(全部/新发现/已通知)
  - [x] 招标信息卡片列表
  - [x] 加载动画
  - [x] 空状态提示

**base.html代码示例**:
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}招标信息管理系统{% endblock %}</title>

    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- Custom CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">

    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">招标信息爬虫系统</a>
            <button class="btn btn-light" id="crawlBtn" onclick="startCrawl()">
                <span id="crawlBtnText">开始爬取</span>
            </button>
        </div>
    </nav>

    <!-- Content -->
    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>

    <!-- Custom JS -->
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

**index.html代码示例**:
```html
{% extends "base.html" %}

{% block content %}
<!-- Tabs -->
<ul class="nav nav-tabs" id="statusTabs">
    <li class="nav-item">
        <a class="nav-link active" href="#" onclick="filterBids('all')">全部</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" href="#" onclick="filterBids('new')">新发现</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" href="#" onclick="filterBids('notified')">已通知</a>
    </li>
</ul>

<!-- Status Bar -->
<div id="statusBar" class="alert alert-info mt-3" style="display:none;">
    <span id="statusMessage"></span>
</div>

<!-- Bids Container -->
<div id="bidsContainer" class="mt-3">
    <div class="text-center text-muted">
        <div class="spinner-border" role="status">
            <span class="visually-hidden">加载中...</span>
        </div>
        <p>加载中...</p>
    </div>
</div>

<!-- Empty State -->
<div id="emptyState" class="text-center text-muted mt-5" style="display:none;">
    <h4>暂无招标信息</h4>
    <p>点击"开始爬取"获取最新招标信息</p>
</div>
{% endblock %}
```

**验证**: HTML页面显示正常

---

### 5. 创建CSS样式 (30分钟)
- [x] 创建 `web/static/css/style.css`
- [x] 定义卡片样式
- [x] 定义响应式布局
- [x] 定义按钮和标签样式
- [x] 添加动画效果

**style.css代码示例**:
```css
/* 全局样式 */
body {
    font-family: 'Microsoft YaHei', Arial, sans-serif;
    background-color: #f5f5f5;
}

/* 招标卡片 */
.bid-card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    transition: transform 0.2s, box-shadow 0.2s;
}

.bid-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.bid-title {
    color: #0066cc;
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 15px;
}

.bid-field {
    margin: 8px 0;
}

.field-label {
    font-weight: bold;
    color: #666;
    margin-right: 8px;
}

.field-value {
    color: #333;
}

/* 状态标签 */
.status-badge {
    font-size: 12px;
    padding: 4px 8px;
    border-radius: 4px;
}

.status-new {
    background-color: #28a745;
    color: white;
}

.status-notified {
    background-color: #6c757d;
    color: white;
}

/* 响应式 */
@media (max-width: 768px) {
    .bid-card {
        padding: 15px;
    }

    .bid-title {
        font-size: 16px;
    }
}

/* 加载动画 */
.fade-in {
    animation: fadeIn 0.5s;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
```

**验证**: 样式美观，响应式正常

---

### 6. 创建JavaScript交互 (60分钟)
- [x] 创建 `web/static/js/main.js`
- [x] 实现 `loadBids()` - 加载招标列表
- [x] 实现 `filterBids()` - 状态过滤
- [x] 实现 `renderBids()` - 渲染招标卡片
- [x] 实现 `startCrawl()` - 开始爬取
- [x] 实现 `checkCrawlStatus()` - 轮询爬取状态
- [x] 添加错误处理
- [x] 页面加载时自动加载数据

**main.js代码示例**:
```javascript
let currentStatus = 'all';

// 页面加载时
window.onload = function() {
    loadBids();
    loadStats();
};

// 加载招标信息
function loadBids(status = 'all') {
    currentStatus = status;
    const url = status === 'all' ? '/api/bids' : `/api/bids?status=${status}`;

    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                renderBids(data.data);
            } else {
                showError('加载失败: ' + data.error);
            }
        })
        .catch(err => {
            showError('网络错误: ' + err.message);
        });
}

// 渲染招标信息
function renderBids(bids) {
    const container = document.getElementById('bidsContainer');
    const emptyState = document.getElementById('emptyState');

    if (bids.length === 0) {
        container.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';
    container.style.display = 'block';
    container.innerHTML = '';

    bids.forEach(bid => {
        const card = `
            <div class="bid-card fade-in">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="bid-title">${bid.project_name}</div>
                    <span class="status-badge status-${bid.status}">${getStatusText(bid.status)}</span>
                </div>

                <div class="bid-field">
                    <span class="field-label">预算金额:</span>
                    <span class="field-value">${bid.budget}</span>
                </div>

                <div class="bid-field">
                    <span class="field-label">采购人:</span>
                    <span class="field-value">${bid.purchaser}</span>
                </div>

                <div class="bid-field">
                    <span class="field-label">获取文件:</span>
                    <span class="field-value">${bid.doc_time}</span>
                </div>

                ${bid.project_number ? `
                <div class="bid-field">
                    <span class="field-label">项目编号:</span>
                    <span class="field-value">${bid.project_number}</span>
                </div>
                ` : ''}

                <div class="mt-3">
                    <a href="${bid.source_url}" target="_blank" class="btn btn-primary btn-sm">查看原文</a>
                </div>
            </div>
        `;
        container.innerHTML += card;
    });
}

// 状态过滤
function filterBids(status) {
    // 更新标签页样式
    document.querySelectorAll('#statusTabs .nav-link').forEach(link => {
        link.classList.remove('active');
    });
    event.target.classList.add('active');

    // 加载数据
    loadBids(status);
}

// 开始爬取
function startCrawl() {
    const btn = document.getElementById('crawlBtn');
    const btnText = document.getElementById('crawlBtnText');

    btn.disabled = true;
    btnText.textContent = '正在爬取...';

    fetch('/api/crawl/start', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showStatus(data.message);
                // 开始轮询状态
                checkCrawlStatus();
            } else {
                showError(data.message);
                btn.disabled = false;
                btnText.textContent = '开始爬取';
            }
        })
        .catch(err => {
            showError('启动失败: ' + err.message);
            btn.disabled = false;
            btnText.textContent = '开始爬取';
        });
}

// 轮询爬取状态
function checkCrawlStatus() {
    const statusInterval = setInterval(() => {
        fetch('/api/crawl/status')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const status = data.data;
                    showStatus(`${status.message} (${status.progress}/${status.total})`);

                    if (!status.is_running) {
                        clearInterval(statusInterval);
                        document.getElementById('crawlBtn').disabled = false;
                        document.getElementById('crawlBtnText').textContent = '开始爬取';
                        // 重新加载数据
                        loadBids(currentStatus);
                    }
                }
            });
    }, 2000);  // 每2秒轮询一次
}

// 显示状态
function showStatus(message) {
    const statusBar = document.getElementById('statusBar');
    const statusMessage = document.getElementById('statusMessage');

    statusMessage.textContent = message;
    statusBar.style.display = 'block';
    statusBar.className = 'alert alert-info mt-3';
}

// 显示错误
function showError(message) {
    const statusBar = document.getElementById('statusBar');
    const statusMessage = document.getElementById('statusMessage');

    statusMessage.textContent = message;
    statusBar.style.display = 'block';
    statusBar.className = 'alert alert-danger mt-3';
}

// 状态文本
function getStatusText(status) {
    const statusMap = {
        'new': '新发现',
        'notified': '已通知',
        'archived': '已归档'
    };
    return statusMap[status] || status;
}

// 加载统计信息
function loadStats() {
    fetch('/api/stats')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // 可以在页面上显示统计信息
                console.log('Stats:', data.data);
            }
        });
}
```

**验证**: 交互功能正常

---

### 7. 测试Web应用 (30分钟)
- [x] 启动Flask应用
- [x] 测试首页加载
- [x] 测试招标列表显示
- [x] 测试状态过滤
- [x] 测试开始爬取按钮
- [x] 测试移动端响应式
- [x] 测试错误处理
- [x] 性能测试(页面加载时间)

**验证**: 所有功能正常工作

---

## 📦 交付物

- [x] `app.py` - Flask应用主文件（含API路由与任务控制）
- [x] `web/templates/base.html` - 基础模板
- [x] `web/templates/index.html` - 首页模板
- [x] `web/static/css/style.css` - 样式文件
- [x] `web/static/js/main.js` - JavaScript文件

---

## 🧪 测试清单

- [x] Flask应用启动成功
- [x] API返回正确数据
- [x] 页面展示正常
- [x] 标签页切换正常
- [x] 开始爬取功能正常
- [x] 状态轮询正常
- [x] 响应式布局正常
- [x] 页面加载时间 ≤ 2秒

---

## 📝 开发笔记

### 开发顺序
1. 先实现后端API
2. 测试API正常工作
3. 开发HTML模板
4. 添加CSS样式
5. 实现JavaScript交互
6. 集成测试

### 可能遇到的问题
1. **问题**: CORS错误
   - **解决**: 前后端同域名，无需配置CORS

2. **问题**: 静态文件404
   - **解决**: 检查Flask static_folder配置

3. **问题**: 爬取任务阻塞
   - **解决**: 使用后台线程

---

## ✨ 完成标准

- [x] 启动应用: `python app.py`
- [x] 访问: `http://localhost:5000`
- [x] 页面正常显示
- [x] 所有功能正常工作

---

## 📅 时间记录

- **开始时间**:
- **完成时间**:
- **实际耗时**:
- **备注**:
