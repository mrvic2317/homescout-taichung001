// VicBot Web 前端應用

const API_BASE_URL = window.location.origin + '/api';
let authToken = localStorage.getItem('authToken');
let currentUser = null;

// ========== 工具函數 ==========

function showError(message) {
    alert('錯誤: ' + message);
}

function showSuccess(message) {
    alert('成功: ' + message);
}

async function apiCall(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (authToken) {
        defaultOptions.headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(API_BASE_URL + endpoint, {
        ...defaultOptions,
        ...options,
        headers: { ...defaultOptions.headers, ...options.headers },
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '請求失敗');
    }

    return response.json();
}

// ========== 認證相關 ==========

document.getElementById('login-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const discordId = document.getElementById('discord-id').value;
    const password = document.getElementById('password').value;

    try {
        const data = await apiCall('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ discord_id: parseInt(discordId), password }),
        });

        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);

        // 獲取用戶資訊
        currentUser = await apiCall('/auth/me');

        // 切換到主應用
        document.getElementById('login-page').classList.add('d-none');
        document.getElementById('app-page').classList.remove('d-none');
        document.getElementById('user-info').textContent = `歡迎，${currentUser.username}`;

        // 加載儀表板
        loadDashboard();
    } catch (error) {
        document.getElementById('login-error').textContent = error.message;
        document.getElementById('login-error').classList.remove('d-none');
    }
});

document.getElementById('logout-btn')?.addEventListener('click', () => {
    localStorage.removeItem('authToken');
    authToken = null;
    currentUser = null;
    location.reload();
});

// ========== 頁面切換 ==========

document.querySelectorAll('[data-page]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const page = e.target.closest('[data-page]').getAttribute('data-page');
        showPage(page);
    });
});

function showPage(pageName) {
    // 隱藏所有頁面
    document.querySelectorAll('.content-page').forEach(page => {
        page.classList.add('d-none');
    });

    // 顯示指定頁面
    const targetPage = document.getElementById(pageName + '-page');
    if (targetPage) {
        targetPage.classList.remove('d-none');

        // 加載對應數據
        switch (pageName) {
            case 'dashboard':
                loadDashboard();
                break;
            case 'monitoring':
                loadMonitoring();
                break;
            case 'cases':
                loadCases();
                break;
            case 'clients':
                loadClients();
                break;
            case 'viewings':
                loadViewings();
                break;
        }
    }

    // 更新導航欄激活狀態
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.querySelector(`[data-page="${pageName}"]`)?.classList.add('active');
}

// ========== 儀表板 ==========

async function loadDashboard() {
    try {
        const [monitoring, cases, clients, viewings] = await Promise.all([
            apiCall('/monitoring'),
            apiCall('/cases'),
            apiCall('/clients'),
            apiCall('/viewings?days=7'),
        ]);

        document.getElementById('stat-monitoring').textContent = monitoring.length;
        document.getElementById('stat-cases').textContent = cases.filter(c => c.status === '跟進中').length;
        document.getElementById('stat-clients').textContent = clients.length;
        document.getElementById('stat-viewings').textContent = viewings.length;
    } catch (error) {
        showError(error.message);
    }
}

// ========== 監控管理 ==========

async function loadMonitoring() {
    try {
        const rules = await apiCall('/monitoring');
        const listEl = document.getElementById('monitoring-list');

        if (rules.length === 0) {
            listEl.innerHTML = '<p class="text-muted">目前沒有監控條件</p>';
            return;
        }

        listEl.innerHTML = rules.map(rule => `
            <div class="card mb-2">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h5>${rule.area}</h5>
                            <p class="mb-0">
                                價格：${rule.price_min || '不限'} - ${rule.price_max || '不限'} 萬 |
                                坪數：${rule.size_min || '不限'} - ${rule.size_max || '不限'}
                            </p>
                        </div>
                        <button class="btn btn-danger btn-sm" onclick="deleteMonitoring(${rule.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        showError(error.message);
    }
}

document.getElementById('add-monitoring-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        area: formData.get('area'),
        price_min: formData.get('price_min') ? parseInt(formData.get('price_min')) : null,
        price_max: formData.get('price_max') ? parseInt(formData.get('price_max')) : null,
        size_min: formData.get('size_min') ? parseFloat(formData.get('size_min')) : null,
        size_max: formData.get('size_max') ? parseFloat(formData.get('size_max')) : null,
    };

    try {
        await apiCall('/monitoring', {
            method: 'POST',
            body: JSON.stringify(data),
        });

        bootstrap.Modal.getInstance(document.getElementById('addMonitoringModal')).hide();
        e.target.reset();
        loadMonitoring();
        showSuccess('監控條件新增成功');
    } catch (error) {
        showError(error.message);
    }
});

async function deleteMonitoring(id) {
    if (!confirm('確定要刪除此監控條件嗎？')) return;

    try {
        await apiCall(`/monitoring/${id}`, { method: 'DELETE' });
        loadMonitoring();
        showSuccess('監控條件已刪除');
    } catch (error) {
        showError(error.message);
    }
}

// ========== 案件管理 ==========

async function loadCases() {
    try {
        const cases = await apiCall('/cases');
        const listEl = document.getElementById('cases-list');

        if (cases.length === 0) {
            listEl.innerHTML = '<p class="text-muted">目前沒有案件</p>';
            return;
        }

        listEl.innerHTML = cases.map(c => `
            <div class="card mb-2">
                <div class="card-body">
                    <h5>${c.title}</h5>
                    <p class="mb-0">
                        區域：${c.area || '未填寫'} |
                        價格：${c.price || '未填寫'} 萬 |
                        狀態：<span class="badge bg-${c.status === '已成交' ? 'success' : 'primary'}">${c.status}</span>
                    </p>
                    ${c.notes ? `<p class="mt-2 mb-0"><small>${c.notes}</small></p>` : ''}
                </div>
            </div>
        `).join('');
    } catch (error) {
        showError(error.message);
    }
}

document.getElementById('add-case-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        title: formData.get('title'),
        area: formData.get('area') || null,
        price: formData.get('price') ? parseInt(formData.get('price')) : null,
        status: formData.get('status'),
        notes: formData.get('notes') || null,
    };

    try {
        await apiCall('/cases', {
            method: 'POST',
            body: JSON.stringify(data),
        });

        bootstrap.Modal.getInstance(document.getElementById('addCaseModal')).hide();
        e.target.reset();
        loadCases();
        showSuccess('案件新增成功');
    } catch (error) {
        showError(error.message);
    }
});

// ========== 客戶管理 ==========

async function loadClients() {
    try {
        const clients = await apiCall('/clients');
        const listEl = document.getElementById('clients-list');

        if (clients.length === 0) {
            listEl.innerHTML = '<p class="text-muted">目前沒有客戶</p>';
            return;
        }

        listEl.innerHTML = clients.map(client => `
            <div class="card mb-2">
                <div class="card-body">
                    <h5>${client.name}</h5>
                    <p class="mb-0">
                        預算：${client.budget_min || '不限'} - ${client.budget_max || '不限'} 萬 |
                        偏好區域：${client.preferred_areas || '未填寫'}
                    </p>
                    ${client.description ? `<p class="mt-2 mb-0"><small>${client.description}</small></p>` : ''}
                </div>
            </div>
        `).join('');
    } catch (error) {
        showError(error.message);
    }
}

document.getElementById('add-client-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        name: formData.get('name'),
        budget_min: formData.get('budget_min') ? parseInt(formData.get('budget_min')) : null,
        budget_max: formData.get('budget_max') ? parseInt(formData.get('budget_max')) : null,
        preferred_areas: formData.get('preferred_areas') || null,
        description: formData.get('description') || null,
    };

    try {
        await apiCall('/clients', {
            method: 'POST',
            body: JSON.stringify(data),
        });

        bootstrap.Modal.getInstance(document.getElementById('addClientModal')).hide();
        e.target.reset();
        loadClients();
        showSuccess('客戶新增成功');
    } catch (error) {
        showError(error.message);
    }
});

// ========== 看屋排程 ==========

async function loadViewings() {
    try {
        const viewings = await apiCall('/viewings?days=7');
        const listEl = document.getElementById('viewings-list');

        if (viewings.length === 0) {
            listEl.innerHTML = '<p class="text-muted">目前沒有即將到來的看屋排程</p>';
            return;
        }

        listEl.innerHTML = viewings.map(v => {
            const date = new Date(v.scheduled_at);
            return `
                <div class="card mb-2">
                    <div class="card-body">
                        <h5><i class="fas fa-calendar-check"></i> ${date.toLocaleString('zh-TW')}</h5>
                        <p class="mb-0">
                            客戶：${v.client} |
                            物件：${v.property} |
                            業務：${v.agent || '未指派'}
                        </p>
                        ${v.note ? `<p class="mt-2 mb-0"><small>${v.note}</small></p>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        showError(error.message);
    }
}

document.getElementById('add-viewing-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        scheduled_at: new Date(formData.get('scheduled_at')).toISOString(),
        client: formData.get('client'),
        property: formData.get('property'),
        agent: formData.get('agent') || null,
        contact: formData.get('contact') || null,
        note: formData.get('note') || null,
        link: formData.get('link') || null,
    };

    try {
        await apiCall('/viewings', {
            method: 'POST',
            body: JSON.stringify(data),
        });

        bootstrap.Modal.getInstance(document.getElementById('addViewingModal')).hide();
        e.target.reset();
        loadViewings();
        showSuccess('看屋排程已建立');
    } catch (error) {
        showError(error.message);
    }
});

// ========== 房價查詢 ==========

document.getElementById('price-query-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const area = document.getElementById('price-area').value;
    const resultEl = document.getElementById('price-result');

    resultEl.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';

    try {
        const data = await apiCall('/price/query', {
            method: 'POST',
            body: JSON.stringify({ area }),
        });

        let html = `
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h4>${data.area} 房價統計</h4>
                    <p class="mb-0">${data.query_period}</p>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>總交易筆數：</strong>${data.total_transactions} 筆</p>
                            <p><strong>平均總價：</strong>${data.avg_price.toFixed(2)} 萬元</p>
                            <p><strong>平均單價：</strong>${data.avg_unit_price.toFixed(2)} 萬/坪</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>最高總價：</strong>${data.max_price.toFixed(2)} 萬元</p>
                            <p><strong>最低總價：</strong>${data.min_price.toFixed(2)} 萬元</p>
                            <p><strong>建案分組數：</strong>${data.project_groups.length} 個</p>
                        </div>
                    </div>
        `;

        if (data.project_groups.length > 0) {
            html += '<h5 class="mt-3">建案分組</h5>';
            data.project_groups.slice(0, 10).forEach(group => {
                html += `
                    <div class="card mt-2">
                        <div class="card-body">
                            <h6>${group.road_name} ${group.address_range}</h6>
                            <p class="mb-1">成交筆數：${group.transaction_count} 筆</p>
                            <p class="mb-1">平均總價：${group.avg_price.toFixed(2)} 萬元 | 平均單價：${group.avg_unit_price.toFixed(2)} 萬/坪</p>
                            <p class="mb-0"><small>門牌：${group.addresses.slice(0, 5).join('、')}${group.addresses.length > 5 ? '...' : ''}</small></p>
                        </div>
                    </div>
                `;
            });
        }

        html += '</div></div>';
        resultEl.innerHTML = html;
    } catch (error) {
        resultEl.innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
    }
});

// ========== 初始化 ==========

if (authToken) {
    apiCall('/auth/me')
        .then(user => {
            currentUser = user;
            document.getElementById('login-page').classList.add('d-none');
            document.getElementById('app-page').classList.remove('d-none');
            document.getElementById('user-info').textContent = `歡迎，${user.username}`;
            loadDashboard();
        })
        .catch(() => {
            localStorage.removeItem('authToken');
            authToken = null;
        });
}
