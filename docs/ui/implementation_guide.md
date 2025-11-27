# 图腾数安招标信息搜集平台 - 前端实现指南

## 开发顺序概览

1. **Phase 1: 基础架构** - 布局框架、样式系统
2. **Phase 2: 核心页面** - 仪表盘、招标大厅
3. **Phase 3: 管理功能** - 资源管理、系统配置
4. **Phase 4: 优化完善** - 交互优化、响应式适配

---

## Phase 1: 基础架构

### 1.1 创建全局样式文件

**文件**: `web/static/css/design-system.css`

```css
/* 定义所有 CSS 变量（参考 design_system.md） */
:root {
  /* 颜色 */
  --primary-color: #1e40af;
  /* ... 其他变量 */
}

/* 全局重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", ...;
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg-secondary);
}
```

### 1.2 创建新布局模板

**文件**: `web/templates/layout.html`

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}图腾数安招标信息搜集平台{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/design-system.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/components.css') }}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- 侧边栏 -->
    <aside class="sidebar">
        <div class="sidebar-brand">
            <h1>图腾数安</h1>
        </div>
        <nav class="sidebar-nav">
            <a href="/dashboard" class="nav-item">
                <i class="icon-dashboard"></i>
                <span>仪表盘</span>
            </a>
            <a href="/bidding-hall" class="nav-item active">
                <i class="icon-list"></i>
                <span>招标大厅</span>
            </a>
            <a href="/sources" class="nav-item">
                <i class="icon-database"></i>
                <span>资源管理</span>
            </a>
            <a href="/settings" class="nav-item">
                <i class="icon-settings"></i>
                <span>系统配置</span>
            </a>
        </nav>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
        <!-- 顶部栏 -->
        <header class="top-bar">
            <div class="top-bar-left">
                <h2 class="page-title">{% block page_title %}{% endblock %}</h2>
            </div>
            <div class="top-bar-right">
                <button id="crawlBtn" class="btn-primary" onclick="startCrawl()">
                    <span id="crawlBtnText">立即抓取</span>
                </button>
            </div>
        </header>

        <!-- 页面内容 -->
        <div class="content-area">
            {% block content %}{% endblock %}
        </div>
    </main>

    <!-- 详情抽屉（全局，JS控制显示） -->
    <div id="detailDrawer" class="detail-drawer">
        <div class="drawer-overlay" onclick="closeDrawer()"></div>
        <div class="drawer-panel">
            <div class="drawer-header">
                <h3 id="drawerTitle">招标详情</h3>
                <button class="btn-close" onclick="closeDrawer()">×</button>
            </div>
            <div class="drawer-body" id="drawerContent">
                <!-- 动态内容 -->
            </div>
        </div>
    </div>

    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

### 1.3 创建组件样式文件

**文件**: `web/static/css/components.css`

实现：侧边栏、按钮、输入框、卡片、表格、抽屉等组件样式

---

## Phase 2: 核心页面

### 2.1 仪表盘页面

**文件**: `web/templates/dashboard.html`

```html
{% extends "layout.html" %}

{% block page_title %}仪表盘{% endblock %}

{% block content %}
<div class="dashboard-grid">
    <!-- 统计卡片 -->
    <div class="stat-card">
        <div class="stat-label">今日新增招标</div>
        <div class="stat-value" id="todayBids">0</div>
        <div class="stat-trend positive">↑ 12%</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">活跃数据源</div>
        <div class="stat-value" id="activeSources">0</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">系统状态</div>
        <div class="stat-value">
            <span class="status-dot running"></span>
            运行中
        </div>
    </div>

    <!-- 最近活动 -->
    <div class="activity-log">
        <h3>最近活动</h3>
        <div id="activityList">
            <!-- JS 动态加载 -->
        </div>
    </div>
</div>
{% endblock %}
```

**对应 JS**: 添加到 `main.js`，实现 `loadDashboardStats()`、`loadActivityLog()` 函数

### 2.2 招标大厅页面

**文件**: `web/templates/bidding_hall.html`

```html
{% extends "layout.html" %}

{% block page_title %}招标大厅{% endblock %}

{% block content %}
<!-- 过滤栏 -->
<div class="filter-bar">
    <input type="text" id="searchInput" placeholder="搜索项目名称或采购人..." class="search-input">
    <select id="sourceFilter" class="filter-select">
        <option value="all">全部来源</option>
        <!-- JS 动态加载来源列表 -->
    </select>
    <input type="date" id="dateFrom" class="date-input">
    <input type="date" id="dateTo" class="date-input">
</div>

<!-- 状态标签 -->
<div class="status-tabs">
    <button class="tab active" onclick="filterByStatus('all')">全部</button>
    <button class="tab" onclick="filterByStatus('new')">新发现</button>
    <button class="tab" onclick="filterByStatus('notified')">已通知</button>
</div>

<!-- 表格列表 -->
<div class="table-wrapper">
    <table class="bid-table">
        <thead>
            <tr>
                <th width="140">发布时间</th>
                <th>项目名称</th>
                <th width="120">预算金额</th>
                <th width="180">采购人</th>
                <th width="120">来源</th>
            </tr>
        </thead>
        <tbody id="bidsTableBody">
            <!-- JS 动态加载 -->
        </tbody>
    </table>
</div>
{% endblock %}

{% block extra_js %}
<script>
// 渲染表格行
function renderBidRow(bid) {
    return `
        <tr onclick="openBidDetail('${bid.id}')">
            <td>${formatDate(bid.doc_time)}</td>
            <td class="bid-title">${bid.project_name}</td>
            <td class="bid-budget">${bid.budget}</td>
            <td>${bid.purchaser}</td>
            <td><span class="badge source-badge">${bid.source}</span></td>
        </tr>
    `;
}

// 打开详情抽屉
function openBidDetail(bidId) {
    // 获取招标详情数据
    // 填充抽屉内容
    // 显示抽屉
}
</script>
{% endblock %}
```

---

## Phase 3: 管理功能

### 3.1 资源管理页面

**关键功能**:
- 公众号列表展示（表格）
- 添加/编辑公众号（Modal 弹窗）
- **规则编辑器**（关键词、排除词、解析器选择）

**实现步骤**:
1. 创建 `web/templates/sources.html`
2. 实现标签页切换（公众号 / 网站预留）
3. 创建 Modal 组件用于编辑
4. 实现规则编辑器 UI（Tag Input 组件）

### 3.2 系统配置页面

**功能模块**:
- 全局关键词配置
- 邮件通知配置
- 定时任务配置

**文件**: `web/templates/settings.html`

---

## Phase 4: 优化完善

### 4.1 交互优化

- [ ] 添加加载动画（Spinner）
- [ ] 添加表格排序功能
- [ ] 添加分页功能
- [ ] 优化抽屉滑入动画（使用 CSS transform）

### 4.2 响应式适配

- [ ] 调整移动端侧边栏为抽屉式
- [ ] 优化表格在小屏幕的显示（卡片模式）

### 4.3 无障碍优化

- [ ] 添加 ARIA 标签
- [ ] 键盘导航支持
- [ ] 对比度检查

---

## 后端路由调整

### 需要新增的路由

```python
# app.py

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/bidding-hall')
def bidding_hall():
    return render_template('bidding_hall.html')

@app.route('/sources')
def sources():
    return render_template('sources.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

# 默认首页重定向到仪表盘
@app.route('/')
def index():
    return redirect('/dashboard')
```

### 需要更新的 API

确保以下 API 已支持前端需求：
- `GET /api/bids` - 支持分页、排序、过滤参数
- `GET /api/stats` - 返回仪表盘统计数据
- `GET /api/sources/wechat` - 返回公众号列表（含规则）
- `POST /api/sources/wechat` - 创建公众号（含规则验证）
- `PUT /api/sources/wechat/<id>` - 更新公众号规则

---

## 文件结构总览

```
web/
├── static/
│   ├── css/
│   │   ├── design-system.css    # CSS 变量定义
│   │   ├── components.css       # 组件样式
│   │   └── pages.css            # 页面特定样式
│   ├── js/
│   │   ├── main.js              # 主 JS
│   │   ├── drawer.js            # 抽屉组件
│   │   └── filters.js           # 过滤器逻辑
│   └── icons/                   # SVG 图标
└── templates/
    ├── layout.html              # 主布局
    ├── dashboard.html           # 仪表盘
    ├── bidding_hall.html        # 招标大厅
    ├── sources.html             # 资源管理
    └── settings.html            # 系统配置
```

---

## 开发检查清单

### Phase 1
- [ ] 创建 `design-system.css` 并定义所有变量
- [ ] 创建 `layout.html` 主布局
- [ ] 实现侧边栏样式和交互
- [ ] 验证布局在不同屏幕尺寸下正常

### Phase 2
- [ ] 实现仪表盘页面和数据加载
- [ ] 实现招标大厅表格列表
- [ ] 实现详情抽屉组件
- [ ] 测试所有交互流程

### Phase 3
- [ ] 实现资源管理页面
- [ ] 开发规则编辑器组件
- [ ] 实现系统配置页面
- [ ] 后端 API 集成和测试

### Phase 4
- [ ] 性能优化（减少重绘）
- [ ] 响应式适配
- [ ] 浏览器兼容性测试
- [ ] 用户体验微调
