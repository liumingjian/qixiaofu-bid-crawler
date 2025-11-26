let currentStatus = 'all';
let statusPolling = null;

document.addEventListener('DOMContentLoaded', () => {
    loadBids();
    loadStats();
});

function handleResponse(response) {
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
}

function loadBids(status = 'all') {
    currentStatus = status;
    const container = document.getElementById('bidsContainer');
    container.innerHTML = `
        <div class="text-center text-muted py-4">
            <div class="spinner-border text-primary mb-2" role="status"></div>
            <p class="mb-0">正在加载数据...</p>
        </div>
    `;
    const emptyState = document.getElementById('emptyState');
    emptyState.classList.add('d-none');

    const url = status === 'all' ? '/api/bids' : `/api/bids?status=${status}`;
    fetch(url)
        .then(handleResponse)
        .then((payload) => {
            if (!payload.success) {
                throw new Error(payload.error || '未知错误');
            }
            renderBids(payload.data || []);
        })
        .catch((err) => showError(`加载失败：${err.message}`));
}

function renderBids(bids) {
    const container = document.getElementById('bidsContainer');
    const emptyState = document.getElementById('emptyState');
    if (!bids.length) {
        container.innerHTML = '';
        emptyState.classList.remove('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    container.innerHTML = bids
        .map(
            (bid) => `
        <div class="bid-card">
            <div class="d-flex justify-content-between align-items-start mb-2">
                <div class="bid-title">${bid.project_name || '未命名项目'}</div>
                <span class="status-badge status-${bid.status || 'new'}">${getStatusText(bid.status)}</span>
            </div>
            ${renderField('预算金额', bid.budget)}
            ${renderField('采购人', bid.purchaser)}
            ${renderField('获取文件时间', bid.doc_time)}
            ${bid.project_number ? renderField('项目编号', bid.project_number) : ''}
            ${bid.service_period ? renderField('服务期限', bid.service_period) : ''}
            <div class="mt-3">
                <a href="${bid.source_url || '#'}" target="_blank" class="btn btn-primary btn-sm">查看原文</a>
            </div>
        </div>
    `
        )
        .join('');
}

function renderField(label, value) {
    return `
    <div class="bid-field">
        <span class="field-label">${label}：</span>
        <span class="field-value">${value || '-'}</span>
    </div>`;
}

function filterBids(status, evt) {
    if (evt) {
        evt.preventDefault();
    }
    document.querySelectorAll('#statusTabs .nav-link').forEach((link) => link.classList.remove('active'));
    if (evt?.target) {
        evt.target.classList.add('active');
    }
    loadBids(status);
}

function getStatusText(status) {
    switch (status) {
        case 'new':
            return '新发现';
        case 'notified':
            return '已通知';
        case 'archived':
            return '已归档';
        default:
            return '未知';
    }
}

function startCrawl() {
    const button = document.getElementById('crawlBtn');
    const buttonText = document.getElementById('crawlBtnText');
    button.disabled = true;
    buttonText.textContent = '正在爬取...';
    showStatus('正在启动爬取任务...');

    fetch('/api/crawl/start', { method: 'POST' })
        .then(handleResponse)
        .then((payload) => {
            if (!payload.success) {
                throw new Error(payload.message || '任务启动失败');
            }
            showStatus('爬取任务已启动');
            beginStatusPolling();
        })
        .catch((err) => {
            showError(err.message);
            button.disabled = false;
            buttonText.textContent = '开始爬取';
        });
}

function beginStatusPolling() {
    if (statusPolling) {
        clearInterval(statusPolling);
    }
    statusPolling = setInterval(() => {
        fetch('/api/crawl/status')
            .then(handleResponse)
            .then((payload) => {
                if (!payload.success) {
                    throw new Error(payload.error || '状态查询失败');
                }
                const data = payload.data || {};
                const message = data.message || '执行中...';
                showStatus(message, data.last_error ? 'danger' : 'info');
                if (!data.is_running) {
                    clearInterval(statusPolling);
                    statusPolling = null;
                    document.getElementById('crawlBtn').disabled = false;
                    document.getElementById('crawlBtnText').textContent = '开始爬取';
                    loadBids(currentStatus);
                    loadStats();
                }
            })
            .catch((err) => {
                clearInterval(statusPolling);
                statusPolling = null;
                showError(`状态查询失败：${err.message}`);
            });
    }, 2000);
}

function loadStats() {
    fetch('/api/stats')
        .then(handleResponse)
        .then((payload) => {
            if (!payload.success) {
                throw new Error(payload.error || '统计数据获取失败');
            }
            renderStats(payload.data || {});
        })
        .catch(() => {
            // 忽略统计错误，避免打扰用户
        });
}

function renderStats(stats) {
    document.getElementById('statTotalBids').textContent = stats.total_bids ?? 0;
    document.getElementById('statNewBids').textContent = stats.new_bids ?? 0;
    document.getElementById('statTotalArticles').textContent = stats.total_articles ?? 0;
    document.getElementById('statNotifiedBids').textContent = stats.notified_bids ?? 0;
}

function showStatus(message, level = 'info') {
    const statusBar = document.getElementById('statusBar');
    const statusMessage = document.getElementById('statusMessage');
    statusBar.classList.remove('d-none', 'alert-info', 'alert-danger');
    statusBar.classList.add(level === 'danger' ? 'alert-danger' : 'alert-info');
    statusMessage.textContent = message;
}

function showError(message) {
    showStatus(message, 'danger');
}
