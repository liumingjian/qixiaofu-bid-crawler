/**
 * Main application logic
 * Handles UI interactions, API calls, and state management.
 */

// --- Global State ---
let currentBids = [];
let statusPolling = null;

// --- API Helpers ---

async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const payload = await response.json();
        return payload;
    } catch (error) {
        showToast(`请求失败: ${error.message}`, 'error');
        throw error;
    }
}

// --- Dashboard Functions ---

async function loadDashboardStats() {
    try {
        const payload = await apiCall('/api/stats');
        if (payload.success) {
            const stats = payload.data;
            updateText('todayBids', stats.new_bids || 0);
            updateText('totalBids', stats.total_bids || 0);
            updateText('activeSources', stats.active_sources || 0); // Need backend support
            // Update active sources count manually if backend doesn't support
            if (stats.active_sources === undefined) {
                 fetch('/api/sources/wechat').then(r=>r.json()).then(d => {
                     const active = (d.data || []).filter(a => a.enabled).length;
                     updateText('activeSources', active);
                 });
            }
        }
        
        // Load recent bids for dashboard
        loadRecentBids();
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

async function loadRecentBids() {
    const tbody = document.getElementById('recentBidsTableBody');
    if (!tbody) return;

    try {
        const payload = await apiCall('/api/bids?limit=5'); // Need backend support for limit
        // Fallback if limit not supported: slice client side
        let bids = payload.data || [];
        // Sort by doc_time desc (assuming backend doesn't) - actually backend might, but let's ensure
        bids = bids.slice(0, 5);

        if (bids.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center text-secondary">暂无数据</td></tr>';
            return;
        }

        tbody.innerHTML = bids.map(bid => `
            <tr onclick="openDrawer('${bid.id}')">
                <td>
                    <div style="font-weight: 500;">${truncate(bid.project_name, 20)}</div>
                    <div style="font-size: 12px; color: var(--text-tertiary);">${bid.purchaser || '未知采购人'}</div>
                </td>
                <td style="color: var(--warning-color); font-weight: 500;">${bid.budget || '-'}</td>
                <td>${renderStatusBadge(bid.status)}</td>
            </tr>
        `).join('');
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-danger">加载失败</td></tr>';
    }
}

// --- Bidding Hall Functions ---

async function loadBids() {
    const tbody = document.getElementById('bidsTableBody');
    const emptyState = document.getElementById('emptyState');
    const loadingState = document.getElementById('loadingState');
    if (!tbody) return;

    tbody.innerHTML = '';
    if (loadingState) loadingState.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';

    try {
        const statusFilter = document.getElementById('statusFilter').value;
        const searchInput = document.getElementById('searchInput').value.toLowerCase();
        
        let url = '/api/bids';
        if (statusFilter !== 'all') {
            url += `?status=${statusFilter}`;
        }
        
        const payload = await apiCall(url);
        let bids = payload.data || [];

        // Client-side search filtering (since backend search isn't fully implemented yet)
        if (searchInput) {
            bids = bids.filter(bid => 
                (bid.project_name && bid.project_name.toLowerCase().includes(searchInput)) ||
                (bid.purchaser && bid.purchaser.toLowerCase().includes(searchInput))
            );
        }

        if (loadingState) loadingState.style.display = 'none';

        if (bids.length === 0) {
            if (emptyState) emptyState.style.display = 'block';
            return;
        }

        tbody.innerHTML = bids.map(bid => `
            <tr onclick="openDrawer('${bid.id}')">
                <td style="font-size: 13px; color: var(--text-secondary);">${bid.doc_time || '-'}</td>
                <td>
                    <div style="font-weight: 500; color: var(--primary-color);">${bid.project_name}</div>
                </td>
                <td style="color: var(--warning-color); font-weight: 600;">${bid.budget || '-'}</td>
                <td>${bid.purchaser || '-'}</td>
                <td>${renderStatusBadge(bid.status)}</td>
                <td>
                     <button class="btn-secondary" style="height: 28px; padding: 0 8px; font-size: 12px;" onclick="event.stopPropagation(); window.open('${bid.source_url}', '_blank')">
                        <i class="bi bi-box-arrow-up-right"></i>
                    </button>
                </td>
            </tr>
        `).join('');
        
        // Save to global for drawer access
        currentBids = bids;

    } catch (error) {
        if (loadingState) loadingState.style.display = 'none';
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">加载失败: ${error.message}</td></tr>`;
    }
}

// --- Drawer Functions ---

function openDrawer(bidId) {
    const drawer = document.getElementById('detailDrawer');
    const content = document.getElementById('drawerContent');
    const drawerTitle = document.getElementById('drawerTitle');
    
    // Find bid data
    // If not in currentBids (e.g. from dashboard), fetch it or find it
    // For simplicity, we assume we might need to fetch single bid if not found,
    // but for now let's rely on current list or a simple fetch if needed.
    // Since we don't have get-by-id API, we iterate.
    let bid = currentBids.find(b => b.id === bidId);
    
    // If not found in current list (dashboard case), we might need to fetch all or find a way.
    // For MVP dashboard, we probably should store the small list in a separate variable or merge.
    // Let's make dashboard store its bids in currentBids too for now? No, that messes up Hall.
    // Let's just fetch all for now or show loading.
    
    if (!bid) {
        // Fallback: This is a bit inefficient but works for MVP without ID endpoint
        // Or we could attach data to the row.
        // Let's just fetch all for now or show loading.
        content.innerHTML = '<div class="loading-spinner"></div>';
        drawer.classList.add('open');
        
        // Quick fix: Fetch all bids to find the one.
        apiCall('/api/bids').then(payload => {
            bid = (payload.data || []).find(b => b.id === bidId);
            if (bid) renderDrawerContent(bid);
            else content.innerHTML = '<div class="text-danger">未找到数据</div>';
        });
        return;
    }

    renderDrawerContent(bid);
    drawer.classList.add('open');
}

function renderDrawerContent(bid) {
    const content = document.getElementById('drawerContent');
    content.innerHTML = `
        <div style="margin-bottom: var(--spacing-6);">
            <div style="font-size: 18px; font-weight: 600; margin-bottom: var(--spacing-4); line-height: 1.4;">${bid.project_name}</div>
            <div style="display: flex; gap: var(--spacing-2);">
                ${renderStatusBadge(bid.status)}
                <span class="badge badge-neutral">${bid.source_title ? '公众号' : '未知来源'}</span>
            </div>
        </div>

        <div class="card" style="margin-bottom: var(--spacing-6); background: var(--bg-secondary); border: none;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-4);">
                <div>
                    <div style="font-size: 12px; color: var(--text-secondary);">预算金额</div>
                    <div style="font-size: 16px; font-weight: 600; color: var(--warning-color);">${bid.budget || '-'}</div>
                </div>
                <div>
                    <div style="font-size: 12px; color: var(--text-secondary);">发布时间</div>
                    <div style="font-size: 16px;">${bid.doc_time || '-'}</div>
                </div>
                <div style="grid-column: span 2;">
                    <div style="font-size: 12px; color: var(--text-secondary);">采购人</div>
                    <div style="font-size: 16px;">${bid.purchaser || '-'}</div>
                </div>
            </div>
        </div>

        <div style="margin-bottom: var(--spacing-6);">
            <h4 style="font-size: 14px; font-weight: 600; margin-bottom: var(--spacing-2);">详细内容</h4>
            <div style="background: var(--bg-tertiary); padding: var(--spacing-4); border-radius: var(--radius-sm); white-space: pre-wrap; font-size: 13px; line-height: 1.6; color: var(--text-primary);">${bid.content || '无详细内容'}</div>
        </div>
        
         <div style="margin-bottom: var(--spacing-6);">
            <h4 style="font-size: 14px; font-weight: 600; margin-bottom: var(--spacing-2);">原文信息</h4>
             <div style="font-size: 13px; margin-bottom: 4px;">来源文章: ${bid.source_title || '-'}</div>
            <a href="${bid.source_url}" target="_blank" class="btn-primary" style="width: 100%;">
                <i class="bi bi-box-arrow-up-right" style="margin-right: 8px;"></i> 查看原文
            </a>
        </div>
    `;
}

function closeDrawer() {
    document.getElementById('detailDrawer').classList.remove('open');
}

// --- Settings Functions ---

let globalKeywords = [];

async function loadConfig() {
    try {
        const payload = await apiCall('/api/config');
        if (payload.success) {
            const config = payload.data;
            // Email
            const recipients = (config.email && config.email.recipient_emails) || [];
            document.getElementById('configRecipients').value = recipients.join('\n');
            // Scheduler
            const scheduler = config.scheduler || {};
            document.getElementById('configSchedulerEnabled').checked = scheduler.enabled || false;
            document.getElementById('configCron').value = scheduler.cron || '';
            
            // Filter
            const wechat = config.wechat || {};
            document.getElementById('configDaysLimit').value = wechat.days_limit || 7;
            document.getElementById('configKeywordLogic').value = wechat.filter_keyword_logic || 'OR';
            
            // Handle global keywords
            // Check legacy keyword_filters first if filter_keywords missing
            globalKeywords = wechat.filter_keywords || wechat.keyword_filters || [];
            renderKeywords('keywordsContainer', globalKeywords, (newKw) => {
                globalKeywords = newKw;
            });
        }
    } catch (error) {
        console.error(error);
    }
}

// Init global keyword input
document.addEventListener('DOMContentLoaded', () => {
    initKeywordInput('newKeywordInput', 'keywordsContainer', () => globalKeywords, (nk) => globalKeywords = nk);
});

async function saveConfig() {
    const recipients = document.getElementById('configRecipients').value.trim().split('\n').filter(r => r.trim());
    const schedulerEnabled = document.getElementById('configSchedulerEnabled').checked;
    const cron = document.getElementById('configCron').value.trim();
    
    // Filter
    const daysLimit = parseInt(document.getElementById('configDaysLimit').value) || 0;
    const keywordLogic = document.getElementById('configKeywordLogic').value;

    const config = {
        email: { recipient_emails: recipients },
        scheduler: { enabled: schedulerEnabled, cron: cron },
        wechat: {
            days_limit: daysLimit,
            filter_keyword_logic: keywordLogic,
            keyword_filters: globalKeywords, // backward compat
            filter_keywords: globalKeywords  // new standard
        }
    };

    try {
        const payload = await fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        }).then(r => r.json());

        if (payload.success) {
            showToast('配置已保存', 'success');
        } else {
            showToast(payload.message, 'error');
        }
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}

// --- Sources Management ---
let accountKeywords = [];

async function loadWeChatAccounts() {
    try {
        const response = await fetch('/api/sources/wechat');
        if (!response.ok) {
            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }
            throw new Error('Failed to load accounts');
        }

        const result = await response.json();
        const accounts = result.data || [];

        const tbody = document.getElementById('wechatAccountsTable');
        if (!tbody) return;

        if (accounts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-secondary); padding: var(--spacing-8);">暂无公众号数据，请联系管理员在配置文件中添加</td></tr>';
            return;
        }

        // Store accounts globally for edit
        window.wechatAccounts = accounts;

        tbody.innerHTML = accounts.map((account, index) => `
            <tr>
                <td>${escapeHtml(account.name)}</td>
                <td>
                    <span class="badge ${account.enabled ? 'badge-success' : 'badge-secondary'}">
                        ${account.enabled ? '启用' : '禁用'}
                    </span>
                </td>
                <td>${account.article_limit || '-'}</td>
                <td>
                    <button class="btn-sm btn-primary" onclick="editAccountById(${index})">
                        <i class="bi bi-sliders"></i> 配置规则
                    </button>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Load accounts error:', error);
        showToast('加载公众号列表失败', 'error');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function editAccountById(index) {
    const account = window.wechatAccounts[index];
    if (account) {
        editAccount(account);
    }
}

function closeAccountModal() {
    document.getElementById('accountModal').style.display = 'none';
}

function showAccountModal() {
    document.getElementById('accountModal').style.display = 'block';
    // Clear form
    document.getElementById('accountId').value = '';
    document.getElementById('accountName').value = '';
    document.getElementById('accountFakeid').value = '';
    document.getElementById('accountToken').value = '';
    document.getElementById('accountCookie').value = '';
    document.getElementById('accountPageSize').value = 5;
    document.getElementById('accountDaysLimit').value = 7;
    document.getElementById('accountEnabled').checked = true;
    document.getElementById('accountModalTitle').textContent = '添加公众号';

    // Clear account keywords
    accountKeywords = [];
    document.getElementById('accountKeywordLogic').value = 'OR';
    renderKeywords('accountKeywordsContainer', accountKeywords, (nk) => accountKeywords = nk);
}

// Init account keyword input
document.addEventListener('DOMContentLoaded', () => {
    initKeywordInput('accountKeywordInput', 'accountKeywordsContainer', () => accountKeywords, (nk) => accountKeywords = nk);
});

function editAccount(account) {
    document.getElementById('accountModal').style.display = 'block';
    document.getElementById('accountModalTitle').textContent = `配置过滤规则 - ${account.name}`;
    document.getElementById('accountId').value = account.id;
    document.getElementById('accountName').value = account.name || '';
    document.getElementById('accountFakeid').value = account.fakeid || '';
    document.getElementById('accountToken').value = account.token || '';
    document.getElementById('accountCookie').value = account.cookie || '';
    document.getElementById('accountPageSize').value = account.page_size || 5;
    document.getElementById('accountArticleLimit').value = account.article_limit !== undefined ? account.article_limit : 10;
    document.getElementById('accountEnabled').checked = account.enabled !== false;

    // Account filters
    document.getElementById('accountKeywordLogic').value = account.filter_keyword_logic || 'OR';
    accountKeywords = account.filter_keywords || [];
    renderKeywords('accountKeywordsContainer', accountKeywords, (nk) => accountKeywords = nk);
}

async function saveAccount() {
    const id = document.getElementById('accountId').value;
    const data = {
        name: document.getElementById('accountName').value,
        fakeid: document.getElementById('accountFakeid').value,
        token: document.getElementById('accountToken').value,
        cookie: document.getElementById('accountCookie').value,
        page_size: parseInt(document.getElementById('accountPageSize').value),
        article_limit: parseInt(document.getElementById('accountArticleLimit').value),
        enabled: document.getElementById('accountEnabled').checked,
        // Filter fields
        filter_keywords: accountKeywords,
        filter_keyword_logic: document.getElementById('accountKeywordLogic').value
    };

    if (!data.name) {
        showToast('请输入账号名称', 'error');
        return;
    }

    try {
        const url = id ? `/api/sources/wechat/${id}` : '/api/sources/wechat';
        const method = id ? 'PUT' : 'POST';
        
        await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        }).then(async r => {
            const res = await r.json();
            if(!res.success) throw new Error(res.message);
        });

        showToast('保存成功', 'success');
        closeAccountModal();
        loadWeChatAccounts();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// --- Tag Input Helpers ---

function initKeywordInput(inputId, containerId, getKeywords, setKeywords) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const val = input.value.trim();
            if (val) {
                const current = getKeywords();
                if (!current.includes(val)) {
                    const next = [...current, val];
                    setKeywords(next);
                    renderKeywords(containerId, next, setKeywords);
                }
                input.value = '';
            }
        }
    });
}

function renderKeywords(containerId, keywords, setKeywords) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = keywords.map((kw, index) => `
        <div class="badge badge-info" style="font-size: 13px; display: flex; align-items: center; gap: 4px; padding: 6px 10px;">
            ${kw}
            <i class="bi bi-x" style="cursor: pointer; font-size: 16px;" data-index="${index}"></i>
        </div>
    `).join('');
    
    // Bind remove events
    container.querySelectorAll('.bi-x').forEach(icon => {
        icon.addEventListener('click', (e) => {
            const idx = parseInt(e.target.dataset.index);
            const current = keywords.filter((_, i) => i !== idx);
            setKeywords(current);
            renderKeywords(containerId, current, setKeywords);
        });
    });
}


async function resetSystemData() {
    if (!confirm('确定要清空所有历史数据吗？此操作不可恢复！')) {
        return;
    }
    
    // Double confirmation
    if (!confirm('再次确认：这将删除所有已爬取的文章和招标记录。继续吗？')) {
        return;
    }

    try {
        const payload = await apiCall('/api/admin/reset', { method: 'POST' });
        if (payload.success) {
            showToast('数据已清空', 'success');
        } else {
            showToast(payload.message, 'error');
        }
    } catch (error) {
        showToast('操作失败: ' + error.message, 'error');
    }
}

// --- Crawl Control ---

async function startCrawl() {
    const btn = document.getElementById('crawlBtn');
    const btnText = document.getElementById('crawlBtnText');
    
    if (btn.disabled) return;
    
    btn.disabled = true;
    btnText.textContent = '准备中...';
    
    try {
        const payload = await apiCall('/api/crawl/start', { method: 'POST' });
        if (payload.success) {
            showToast('爬取任务已启动', 'success');
            pollStatus();
        } else {
            showToast(payload.message, 'error');
            btn.disabled = false;
            btnText.textContent = '立即抓取';
        }
    } catch (error) {
        btn.disabled = false;
        btnText.textContent = '立即抓取';
    }
}

function pollStatus() {
    if (statusPolling) clearInterval(statusPolling);
    
    const btn = document.getElementById('crawlBtn');
    const btnText = document.getElementById('crawlBtnText');

    statusPolling = setInterval(async () => {
        try {
            const payload = await apiCall('/api/crawl/status');
            const status = payload.data;
            
            if (status.is_running) {
                btn.disabled = true;
                btnText.textContent = status.message || '运行中...';
            } else {
                clearInterval(statusPolling);
                statusPolling = null;
                btn.disabled = false;
                btnText.textContent = '立即抓取';
                showToast('爬取任务完成', 'success');
                // Refresh data if on relevant pages
                loadBids(); 
                loadDashboardStats();
            }
        } catch (error) {
            clearInterval(statusPolling);
            statusPolling = null;
            btn.disabled = false;
            btnText.textContent = '立即抓取';
        }
    }, 2000);
}

// --- Utils ---

function updateText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function renderStatusBadge(status) {
    const map = {
        'new': { text: '新发现', class: 'badge-success' },
        'notified': { text: '已通知', class: 'badge-info' },
        'archived': { text: '已归档', class: 'badge-neutral' }
    };
    const s = map[status] || { text: status, class: 'badge-neutral' };
    return `<span class="badge ${s.class}">${s.text}</span>`;
}

function truncate(str, len) {
    if (!str) return '';
    return str.length > len ? str.substring(0, len) + '...' : str;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    const color = type === 'error' ? 'var(--danger-color)' : type === 'success' ? 'var(--success-color)' : 'var(--primary-color)';
    const bg = type === 'error' ? '#fef2f2' : type === 'success' ? '#ecfdf5' : '#eff6ff';
    
    toast.style.cssText = `
        background: ${bg};
        color: var(--text-primary);
        padding: 12px 24px;
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-lg);
        margin-bottom: 12px;
        border-left: 4px solid ${color};
        display: flex;
        align-items: center;
        animation: slideIn 0.3s ease;
        min-width: 300px;
    `;
    
    toast.innerHTML = `
        <i class="bi ${type === 'error' ? 'bi-exclamation-circle' : 'bi-check-circle'}" style="color: ${color}; margin-right: 8px;"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add animations styles if not present
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);