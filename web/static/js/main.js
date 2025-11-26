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

// Configuration management
function loadConfig() {
    fetch('/api/config')
        .then(handleResponse)
        .then((payload) => {
            if (!payload.success) {
                throw new Error(payload.message || '配置加载失败');
            }
            populateConfigForm(payload.data || {});
        })
        .catch((err) => {
            showError(`配置加载失败：${err.message}`);
        });
}

function populateConfigForm(config) {
    // Email
    const email = config.email || {};
    const recipients = email.recipient_emails || [];
    document.getElementById('configRecipients').value = recipients.join('\n');

    // Scheduler
    const scheduler = config.scheduler || {};
    document.getElementById('configSchedulerEnabled').checked = scheduler.enabled || false;
    document.getElementById('configCron').value = scheduler.cron || '';
}

function saveConfig() {
    const config = {
        email: {
            recipient_emails: document.getElementById('configRecipients').value
                .split('\n')
                .map(e => e.trim())
                .filter(e => e.length > 0)
        },
        scheduler: {
            enabled: document.getElementById('configSchedulerEnabled').checked,
            cron: document.getElementById('configCron').value.trim()
        }
    };

    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    })
        .then(handleResponse)
        .then((payload) => {
            if (!payload.success) {
                throw new Error(payload.message || '保存失败');
            }
            showStatus(payload.message || '配置已保存', 'success');
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('configModal'));
            if (modal) modal.hide();
        })
        .catch((err) => {
            showError(`保存失败：${err.message}`);
        });
}

// Load config when modal opens
document.addEventListener('DOMContentLoaded', () => {
    const configModal = document.getElementById('configModal');
    if (configModal) {
        configModal.addEventListener('show.bs.modal', () => {
            loadConfig();
            loadWeChatAccounts(); // Load accounts when config modal opens
        });
    }
});

// WeChat Account Management
function loadWeChatAccounts() {
    fetch('/api/sources/wechat')
        .then(handleResponse)
        .then((payload) => {
            if (!payload.success) {
                throw new Error(payload.message || '加载失败');
            }
            renderWeChatAccounts(payload.data || []);
        })
        .catch((err) => {
            document.getElementById('wechatAccountsTable').innerHTML =
                `<tr><td colspan="5" class="text-center text-danger">加载失败: ${err.message}</td></tr>`;
        });
}

function renderWeChatAccounts(accounts) {
    const tbody = document.getElementById('wechatAccountsTable');
    if (!accounts.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">暂无账号</td></tr>';
        return;
    }

    tbody.innerHTML = accounts.map(account => `
        <tr>
            <td>${account.name || '-'}</td>
            <td><span class="badge ${account.enabled ? 'bg-success' : 'bg-secondary'}">${account.enabled ? '启用' : '禁用'}</span></td>
            <td>${account.page_size || 5}</td>
            <td>${account.days_limit || 7}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editAccount('${account.id}')">编辑</button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteAccount('${account.id}')">删除</button>
            </td>
        </tr>
    `).join('');
}

function showAccountModal(account = null) {
    const modal = new bootstrap.Modal(document.getElementById('accountModal'));
    const title = document.getElementById('accountModalTitle');

    if (account) {
        title.textContent = '编辑公众号';
        document.getElementById('accountId').value = account.id;
        document.getElementById('accountName').value = account.name || '';
        document.getElementById('accountFakeid').value = account.fakeid || '';
        document.getElementById('accountToken').value = account.token || '';
        document.getElementById('accountCookie').value = account.cookie || '';
        document.getElementById('accountPageSize').value = account.page_size || 5;
        document.getElementById('accountDaysLimit').value = account.days_limit || 7;
        document.getElementById('accountEnabled').checked = account.enabled !== false;
    } else {
        title.textContent = '添加公众号';
        document.getElementById('accountId').value = '';
        document.getElementById('accountName').value = '';
        document.getElementById('accountFakeid').value = '';
        document.getElementById('accountToken').value = '';
        document.getElementById('accountCookie').value = '';
        document.getElementById('accountPageSize').value = 5;
        document.getElementById('accountDaysLimit').value = 7;
        document.getElementById('accountEnabled').checked = true;
    }

    modal.show();
}

function editAccount(accountId) {
    fetch('/api/sources/wechat')
        .then(handleResponse)
        .then((payload) => {
            const account = (payload.data || []).find(a => a.id === accountId);
            if (account) {
                showAccountModal(account);
            }
        })
        .catch((err) => showError(`加载账号失败: ${err.message}`));
}

function saveAccount() {
    const accountId = document.getElementById('accountId').value;
    const account = {
        name: document.getElementById('accountName').value.trim(),
        fakeid: document.getElementById('accountFakeid').value.trim(),
        token: document.getElementById('accountToken').value.trim(),
        cookie: document.getElementById('accountCookie').value.trim(),
        page_size: parseInt(document.getElementById('accountPageSize').value) || 5,
        days_limit: parseInt(document.getElementById('accountDaysLimit').value) || 7,
        enabled: document.getElementById('accountEnabled').checked
    };

    if (!account.name) {
        showError('账号名称不能为空');
        return;
    }

    const url = accountId ? `/api/sources/wechat/${accountId}` : '/api/sources/wechat';
    const method = accountId ? 'PUT' : 'POST';

    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(account)
    })
        .then(handleResponse)
        .then((payload) => {
            if (!payload.success) {
                throw new Error(payload.message || '保存失败');
            }
            showStatus('账号已保存', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('accountModal'));
            if (modal) modal.hide();
            loadWeChatAccounts();
        })
        .catch((err) => showError(`保存失败: ${err.message}`));
}

function deleteAccount(accountId) {
    if (!confirm('确定要删除此账号吗？')) {
        return;
    }

    fetch(`/api/sources/wechat/${accountId}`, {
        method: 'DELETE'
    })
        .then(handleResponse)
        .then((payload) => {
            if (!payload.success) {
                throw new Error(payload.message || '删除失败');
            }
            showStatus('账号已删除', 'success');
            loadWeChatAccounts();
        })
        .catch((err) => showError(`删除失败: ${err.message}`));
}

