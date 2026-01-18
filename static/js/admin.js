// API Base URL
const API_BASE = window.location.origin;

// State
let authToken = null;
let selectedCompanies = new Set();
let companies = [];
let globalSettings = null;
let isSubmitting = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded - Admin.js initialized');
    
    // Check for existing token
    authToken = localStorage.getItem('authToken');
    if (authToken) {
        showDashboard();
    } else {
        showLogin();
    }

    // Event Listeners
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        console.log('Login form found, attaching submit handler');
        loginForm.addEventListener('submit', handleLogin, { once: false });
        // Prevent any additional submit events
        loginForm.addEventListener('submit', (e) => {
            if (isSubmitting) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
            }
        }, true);
    } else {
        console.error('Login form not found!');
    }
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Pending approvals
    document.getElementById('refreshPendingBtn').addEventListener('click', loadPendingApprovals);
    
    // Add company
    document.getElementById('addCompanyBtn').addEventListener('click', handleAddCompany);
    
    // Bulk operations
    document.getElementById('selectAllCheckbox').addEventListener('change', handleSelectAll);
    document.getElementById('selectAllBtn').addEventListener('click', handleSelectAllBtn);
    document.getElementById('bulkSyncNowBtn').addEventListener('click', () => handleBulkOperation('sync_now'));
    document.getElementById('bulkEnableBtn').addEventListener('click', () => handleBulkOperation('sync_enable'));
    document.getElementById('bulkDisableBtn').addEventListener('click', () => handleBulkOperation('sync_disable'));
    document.getElementById('bulkSettingsBtn').addEventListener('click', showBulkSettingsModal);

    // Settings
    document.getElementById('saveSettingsBtn').addEventListener('click', saveGlobalSettings);
    document.getElementById('refreshLogsBtn').addEventListener('click', loadActivityLogs);

    // Modal
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', closeModals);
    });
    document.getElementById('cancelBulkSettings').addEventListener('click', closeModals);
    document.getElementById('applyBulkSettings').addEventListener('click', applyBulkSettings);
});

// Authentication
async function handleLogin(e) {
    console.log('handleLogin called');
    e.preventDefault();
    
    // Prevent multiple submissions
    if (isSubmitting) {
        console.log('Already submitting, ignoring duplicate request');
        return;
    }
    
    isSubmitting = true;
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('loginError');
    const submitBtn = e.target.querySelector('button[type="submit"]');
    
    console.log('Login attempt:', { username, passwordLength: password.length });
    
    // Disable button and show loading state
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Logging in...';
    }
    
    // Clear previous errors
    errorDiv.textContent = '';
    errorDiv.classList.remove('show');

    try {
        const response = await fetch(`${API_BASE}/api/v1/admin/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        // Check content type
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            throw new Error('Server error: Invalid response format');
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }

        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);
        
        document.getElementById('adminName').textContent = data.admin.username;
        console.log('Login successful, showing dashboard');
        showDashboard();
    } catch (error) {
        console.error('Login error:', error);
        errorDiv.textContent = error.message || 'Login failed. Please try again.';
        errorDiv.classList.add('show');
    } finally {
        // Re-enable button
        isSubmitting = false;
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Login';
        }
    }
}

function handleLogout() {
    authToken = null;
    localStorage.removeItem('authToken');
    showLogin();
}

function showLogin() {
    document.getElementById('loginScreen').classList.add('active');
    document.getElementById('dashboardScreen').classList.remove('active');
}

function showDashboard() {
    console.log('showDashboard() called');
    const loginScreen = document.getElementById('loginScreen');
    const dashboardScreen = document.getElementById('dashboardScreen');
    
    console.log('loginScreen element:', loginScreen);
    console.log('dashboardScreen element:', dashboardScreen);
    
    if (loginScreen) {
        loginScreen.classList.remove('active');
        console.log('Removed active from loginScreen');
    }
    if (dashboardScreen) {
        dashboardScreen.classList.add('active');
        console.log('Added active to dashboardScreen');
    }
    
    loadPendingApprovals();
    loadCompanies();
    loadGlobalSettings();
    loadActivityLogs();
}

// API Helper
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(authToken && { 'Authorization': `Bearer ${authToken}` }),
        ...options.headers
    };

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers
        });

        if (response.status === 401) {
            handleLogout();
            throw new Error('Session expired. Please login again.');
        }

        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            throw new Error(`Server returned non-JSON response: ${text.substring(0, 100)}`);
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Request failed');
        }

        return response.json();
    } catch (error) {
        if (error.message.includes('JSON')) {
            throw error;
        }
        // Handle network errors
        throw new Error(error.message || 'Network request failed');
    }
}

// Tab Switching
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');

    // Load data if needed
    if (tabName === 'logs') {
        loadActivityLogs();
    } else if (tabName === 'rates') {
        // Rates tab loads via iframe - no additional loading needed
    }
}

// Pending Approvals
async function loadPendingApprovals() {
    const loading = document.getElementById('pendingLoading');
    const error = document.getElementById('pendingError');
    const table = document.getElementById('pendingTable');
    const noPending = document.getElementById('noPending');
    const badge = document.getElementById('pendingCount');

    try {
        loading.style.display = 'block';
        error.classList.remove('show');
        table.style.display = 'none';
        noPending.style.display = 'none';

        const data = await apiRequest('/api/v1/admin/pending-companies');
        const pending = data.pending_companies || [];
        const approved = data.approved_not_connected || [];
        const allPending = [...pending, ...approved];

        loading.style.display = 'none';

        // Update badge count (pending + approved awaiting connection)
        const totalCount = data.total_pending + data.total_approved;
        if (totalCount > 0) {
            badge.textContent = totalCount;
            badge.style.display = 'inline';
        } else {
            badge.style.display = 'none';
        }

        if (allPending.length === 0) {
            noPending.style.display = 'block';
            return;
        }

        renderPendingApprovals(allPending);
        table.style.display = 'table';
    } catch (err) {
        loading.style.display = 'none';
        error.textContent = err.message;
        error.classList.add('show');
    }
}

function renderPendingApprovals(pending) {
    const tbody = document.getElementById('pendingTableBody');
    tbody.innerHTML = pending.map(company => {
        let statusBadge = '';
        let actions = '';
        
        if (company.status === 'pending') {
            statusBadge = '<span class="status-badge status-inactive">Pending Approval</span>';
            actions = `
                <button class="btn btn-success btn-sm" onclick="approveCompany(${company.id}, '${company.business_name}')">
                    ✓ Approve
                </button>
                <button class="btn btn-danger btn-sm" onclick="rejectCompany(${company.id}, '${company.business_name}')">
                    ✗ Reject
                </button>
            `;
        } else if (company.status === 'approved_awaiting_connection') {
            statusBadge = '<span class="status-badge status-active">✓ Approved - Awaiting QB Connection</span>';
            actions = `
                <button class="btn btn-info btn-sm" onclick="copyOAuthLink('${company.oauth_link}', '${company.business_name}')">
                    📋 Copy Link
                </button>
                <button class="btn btn-outline btn-sm" onclick="window.open('mailto:${company.contact_email}?subject=QuickBooks Connection Link&body=Please click this link to connect your QuickBooks: ${company.oauth_link}', '_blank')">
                    ✉ Email Link
                </button>
            `;
        }
        
        return `
            <tr>
                <td><strong>${company.business_name}</strong><br/>${statusBadge}</td>
                <td>${company.contact_name}</td>
                <td>${company.contact_email}</td>
                <td>${company.tax_id || 'N/A'}</td>
                <td>${new Date(company.requested_at).toLocaleString()}</td>
                <td>${actions}</td>
            </tr>
        `;
    }).join('');
}

async function approveCompany(companyId, businessName) {
    if (!confirm(`Approve registration for "${businessName}"?`)) {
        return;
    }

    try {
        const result = await apiRequest(`/api/v1/admin/approve-company/${companyId}`, {
            method: 'POST'
        });

        alert(`✓ ${result.message}\n\nOAuth Connection Link:\n${result.oauth_connection_link}\n\nSend this link to the company to connect their QuickBooks account.`);
        
        // Copy link to clipboard
        navigator.clipboard.writeText(result.oauth_connection_link);
        
        loadPendingApprovals();
        loadCompanies();
    } catch (err) {
        alert(`Failed to approve company: ${err.message}`);
    }
}

async function rejectCompany(companyId, businessName) {
    const reason = prompt(`Reject registration for "${businessName}"?\n\nPlease provide a reason:`);
    
    if (reason === null) {
        return; // User cancelled
    }

    try {
        const result = await apiRequest(`/api/v1/admin/reject-company/${companyId}?reason=${encodeURIComponent(reason)}`, {
            method: 'POST'
        });

        alert(`✗ ${result.message}`);
        
        loadPendingApprovals();
    } catch (err) {
        alert(`Failed to reject company: ${err.message}`);
    }
}

function viewPendingDetails(companyId) {
    // Implementation for viewing full details of pending registration
    alert('View details modal - to be implemented');
}

function copyOAuthLink(link, businessName) {
    navigator.clipboard.writeText(link).then(() => {
        alert(`✓ OAuth link copied to clipboard!\n\nSend this link to ${businessName} to connect their QuickBooks account:\n\n${link}`);
    }).catch(err => {
        alert(`Failed to copy link: ${err.message}\n\nLink: ${link}`);
    });
}

// Companies
async function loadCompanies() {
    const loading = document.getElementById('companiesLoading');
    const error = document.getElementById('companiesError');
    const table = document.getElementById('companiesTable');
    const noCompanies = document.getElementById('noCompanies');

    try {
        loading.style.display = 'block';
        error.classList.remove('show');
        table.style.display = 'none';
        noCompanies.style.display = 'none';

        companies = await apiRequest('/api/v1/admin/companies');

        loading.style.display = 'none';

        if (companies.length === 0) {
            noCompanies.style.display = 'block';
            return;
        }

        renderCompanies();
        table.style.display = 'table';
    } catch (err) {
        loading.style.display = 'none';
        error.textContent = err.message;
        error.classList.add('show');
    }
}

function renderCompanies() {
    const tbody = document.getElementById('companiesTableBody');
    tbody.innerHTML = companies.map(company => `
        <tr>
            <td>
                <input type="checkbox" class="company-checkbox" value="${company.company_id}"
                       ${selectedCompanies.has(company.company_id) ? 'checked' : ''}>
            </td>
            <td>${company.company_name || 'N/A'}</td>
            <td><code>${company.company_id}</code></td>
            <td>
                <span class="status-badge ${company.is_active ? 'status-active' : 'status-inactive'}">
                    ${company.is_active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                <span class="status-badge ${company.sync_enabled ? 'sync-enabled' : 'sync-disabled'}">
                    ${company.sync_enabled ? 'Enabled' : 'Disabled'}
                </span>
            </td>
            <td>${company.last_sync ? new Date(company.last_sync).toLocaleString() : 'Never'}</td>
            <td>
                <span class="status-badge ${company.is_sandbox ? 'env-sandbox' : 'env-production'}">
                    ${company.is_sandbox ? 'Sandbox' : 'Production'}
                </span>
            </td>
            <td>
                <button class="btn btn-outline" onclick="toggleCompanySync('${company.company_id}')">
                    ${company.sync_enabled ? 'Disable' : 'Enable'}
                </button>
                <button class="btn btn-outline" onclick="viewCompanyDetails('${company.company_id}')">
                    Details
                </button>
            </td>
        </tr>
    `).join('');

    // Add checkbox listeners
    document.querySelectorAll('.company-checkbox').forEach(cb => {
        cb.addEventListener('change', handleCompanySelection);
    });

    updateBulkButtons();
}

function handleCompanySelection(e) {
    const companyId = e.target.value;
    if (e.target.checked) {
        selectedCompanies.add(companyId);
    } else {
        selectedCompanies.delete(companyId);
    }
    updateBulkButtons();
}

function handleSelectAll(e) {
    const checkboxes = document.querySelectorAll('.company-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = e.target.checked;
        if (e.target.checked) {
            selectedCompanies.add(cb.value);
        } else {
            selectedCompanies.delete(cb.value);
        }
    });
    updateBulkButtons();
}

function handleSelectAllBtn() {
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    selectAllCheckbox.checked = !selectAllCheckbox.checked;
    handleSelectAll({ target: selectAllCheckbox });
}

function updateBulkButtons() {
    const hasSelection = selectedCompanies.size > 0;
    document.getElementById('bulkSyncNowBtn').disabled = !hasSelection;
    document.getElementById('bulkEnableBtn').disabled = !hasSelection;
    document.getElementById('bulkDisableBtn').disabled = !hasSelection;
    document.getElementById('bulkSettingsBtn').disabled = !hasSelection;
}

async function toggleCompanySync(companyId) {
    try {
        await apiRequest(`/api/v1/admin/companies/${companyId}/toggle-sync`, {
            method: 'PATCH'
        });
        await loadCompanies();
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

async function viewCompanyDetails(companyId) {
    const modal = document.getElementById('companyDetailsModal');
    const content = document.getElementById('companyDetailsContent');
    
    modal.classList.add('active');
    content.innerHTML = '<div class="loading">Loading...</div>';

    try {
        const company = await apiRequest(`/api/v1/admin/companies/${companyId}`);
        const settings = company.sync_settings || {};

        content.innerHTML = `
            <h4>${company.company_name || 'N/A'}</h4>
            <p><strong>Company ID:</strong> ${company.company_id}</p>
            <p><strong>Status:</strong> ${company.is_active ? 'Active' : 'Inactive'}</p>
            <p><strong>Sync Enabled:</strong> ${company.sync_enabled ? 'Yes' : 'No'}</p>
            <p><strong>Last Sync:</strong> ${company.last_sync ? new Date(company.last_sync).toLocaleString() : 'Never'}</p>
            <p><strong>Environment:</strong> ${company.is_sandbox ? 'Sandbox' : 'Production'}</p>
            
            <h4 style="margin-top: 1.5rem;">Sync Settings</h4>
            <p><strong>Custom Schedule:</strong> ${settings.use_custom_schedule ? 'Yes' : 'No'}</p>
            ${settings.schedule_time ? `<p><strong>Schedule Time:</strong> ${settings.schedule_time}</p>` : ''}
            ${settings.timezone ? `<p><strong>Timezone:</strong> ${settings.timezone}</p>` : ''}
            ${settings.enabled_currencies ? `<p><strong>Enabled Currencies:</strong> ${settings.enabled_currencies}</p>` : ''}
            <p><strong>Auto Sync:</strong> ${settings.auto_sync_enabled ? 'Enabled' : 'Disabled'}</p>
            ${settings.notification_email ? `<p><strong>Notification Email:</strong> ${settings.notification_email}</p>` : ''}
        `;
    } catch (err) {
        content.innerHTML = `<p class="error-message show">${err.message}</p>`;
    }
}

// Bulk Operations
async function handleBulkOperation(operation) {
    if (selectedCompanies.size === 0) return;

    const confirmMsg = operation === 'sync_now' 
        ? `Trigger sync for ${selectedCompanies.size} companies?`
        : `${operation.replace('_', ' ')} for ${selectedCompanies.size} companies?`;

    if (!confirm(confirmMsg)) return;

    try {
        const result = await apiRequest('/api/v1/admin/companies/bulk', {
            method: 'POST',
            body: JSON.stringify({
                company_ids: Array.from(selectedCompanies),
                operation: operation
            })
        });

        alert(`Success: ${result.successful}, Failed: ${result.failed}`);
        
        if (result.failed > 0) {
            const failures = result.results.filter(r => !r.success);
            console.log('Failures:', failures);
        }

        await loadCompanies();
        selectedCompanies.clear();
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

function showBulkSettingsModal() {
    document.getElementById('bulkSettingsModal').classList.add('active');
}

async function applyBulkSettings() {
    const form = document.getElementById('bulkSettingsForm');
    const formData = new FormData(form);
    
    const settings = {};
    
    // Collect checked/filled values
    if (document.getElementById('bulkAutoSync').checked) {
        settings.auto_sync_enabled = true;
    }
    if (document.getElementById('bulkUseCustomSchedule').checked) {
        settings.use_custom_schedule = true;
    }
    if (formData.get('schedule_time')) {
        settings.schedule_time = formData.get('schedule_time');
    }
    if (formData.get('timezone')) {
        settings.timezone = formData.get('timezone');
    }
    if (document.getElementById('bulkEnabledCurrencies').value) {
        settings.enabled_currencies = document.getElementById('bulkEnabledCurrencies').value.split(',').map(s => s.trim());
    }
    if (formData.get('notification_email')) {
        settings.notification_email = formData.get('notification_email');
    }
    if (document.getElementById('bulkNotifyOnSync').checked) {
        settings.notify_on_sync = true;
    }

    try {
        const result = await apiRequest('/api/v1/admin/companies/bulk', {
            method: 'POST',
            body: JSON.stringify({
                company_ids: Array.from(selectedCompanies),
                operation: 'update_settings',
                settings: settings
            })
        });

        alert(`Settings applied! Success: ${result.successful}, Failed: ${result.failed}`);
        closeModals();
        await loadCompanies();
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

// Global Settings
async function loadGlobalSettings() {
    const loading = document.getElementById('settingsLoading');
    const error = document.getElementById('settingsError');
    const form = document.getElementById('settingsForm');

    try {
        loading.style.display = 'block';
        error.classList.remove('show');

        globalSettings = await apiRequest('/api/v1/admin/settings/global');

        // Populate form
        document.getElementById('scheduleEnabled').checked = globalSettings.schedule_enabled;
        document.getElementById('scheduleTime').value = globalSettings.schedule_time;
        document.getElementById('timezone').value = globalSettings.timezone;
        document.getElementById('enforceGlobalSchedule').checked = globalSettings.enforce_global_schedule;
        document.getElementById('retryOnFailure').checked = globalSettings.retry_on_failure;
        document.getElementById('maxRetryAttempts').value = globalSettings.max_retry_attempts;
        document.getElementById('retryDelayMinutes').value = globalSettings.retry_delay_minutes;
        document.getElementById('boaTimeout').value = globalSettings.boa_timeout_seconds;
        document.getElementById('boaRetryAttempts').value = globalSettings.boa_retry_attempts;
        document.getElementById('autoRefreshTokens').checked = globalSettings.auto_refresh_tokens;
        document.getElementById('tokenRefreshThreshold').value = globalSettings.token_refresh_threshold_hours;
        document.getElementById('notifyOnSuccess').checked = globalSettings.notify_on_success;
        document.getElementById('notifyOnFailure').checked = globalSettings.notify_on_failure;
        document.getElementById('notificationEmail').value = globalSettings.notification_email || '';

        loading.style.display = 'none';
        form.style.display = 'flex';
    } catch (err) {
        loading.style.display = 'none';
        error.textContent = err.message;
        error.classList.add('show');
    }
}

async function saveGlobalSettings() {
    const success = document.getElementById('settingsSuccess');
    const error = document.getElementById('settingsError');

    try {
        error.classList.remove('show');
        success.classList.remove('show');

        const settings = {
            schedule_enabled: document.getElementById('scheduleEnabled').checked,
            schedule_time: document.getElementById('scheduleTime').value,
            timezone: document.getElementById('timezone').value,
            enforce_global_schedule: document.getElementById('enforceGlobalSchedule').checked,
            retry_on_failure: document.getElementById('retryOnFailure').checked,
            max_retry_attempts: parseInt(document.getElementById('maxRetryAttempts').value),
            retry_delay_minutes: parseInt(document.getElementById('retryDelayMinutes').value),
            boa_timeout_seconds: parseInt(document.getElementById('boaTimeout').value),
            boa_retry_attempts: parseInt(document.getElementById('boaRetryAttempts').value),
            auto_refresh_tokens: document.getElementById('autoRefreshTokens').checked,
            token_refresh_threshold_hours: parseInt(document.getElementById('tokenRefreshThreshold').value),
            notify_on_success: document.getElementById('notifyOnSuccess').checked,
            notify_on_failure: document.getElementById('notifyOnFailure').checked,
            notification_email: document.getElementById('notificationEmail').value || null
        };

        await apiRequest('/api/v1/admin/settings/global', {
            method: 'PATCH',
            body: JSON.stringify(settings)
        });

        success.textContent = 'Settings saved successfully!';
        success.classList.add('show');

        setTimeout(() => success.classList.remove('show'), 3000);
    } catch (err) {
        error.textContent = err.message;
        error.classList.add('show');
    }
}

// Activity Logs
async function loadActivityLogs() {
    const loading = document.getElementById('logsLoading');
    const error = document.getElementById('logsError');
    const table = document.getElementById('logsTable');

    try {
        loading.style.display = 'block';
        error.classList.remove('show');
        table.style.display = 'none';

        const logs = await apiRequest('/api/v1/admin/logs?limit=100');

        const tbody = document.getElementById('logsTableBody');
        tbody.innerHTML = logs.map(log => `
            <tr>
                <td>${new Date(log.created_at).toLocaleString()}</td>
                <td>${log.admin_username}</td>
                <td><code>${log.action}</code></td>
                <td>
                    ${log.target_type ? `${log.target_type}: ${log.target_id}` : 'N/A'}
                </td>
                <td>${log.details || 'N/A'}</td>
                <td>${log.ip_address || 'N/A'}</td>
            </tr>
        `).join('');

        loading.style.display = 'none';
        table.style.display = 'table';
    } catch (err) {
        loading.style.display = 'none';
        error.textContent = err.message;
        error.classList.add('show');
    }
}

// Add New Company
function handleAddCompany() {
    const connectUrl = `${API_BASE}/api/v1/oauth/connect`;
    
    // Show modal with connection instructions
    const modalHtml = `
        <div class="modal active" id="addCompanyModal">
            <div class="modal-content">
                <h3>Connect New QuickBooks Company</h3>
                <p>To add a new company, click the button below to connect to QuickBooks.</p>
                <p><strong>What happens next:</strong></p>
                <ol style="text-align: left; margin: 20px 0;">
                    <li>You'll be redirected to QuickBooks</li>
                    <li>Sign in to the QuickBooks company you want to connect</li>
                    <li>Authorize the BoA Exchange Rate API</li>
                    <li>You'll be redirected back and the company will appear in your dashboard</li>
                </ol>
                <div class="modal-buttons">
                    <button class="btn btn-primary" onclick="window.location.href='${connectUrl}'">
                        Connect to QuickBooks
                    </button>
                    <button class="btn btn-secondary" onclick="closeModals()">Cancel</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// Modal
function closeModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.remove();
    });
}
