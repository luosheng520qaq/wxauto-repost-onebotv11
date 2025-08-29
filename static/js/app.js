// 全局变量
let currentConfig = {};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
    loadConfig();
    loadMonitorUsers();
    updateStatus();
    
    // 定期更新状态
    setInterval(updateStatus, 5000);
});

// 初始化页面
function initializePage() {
    // 标签页切换
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            // 更新按钮状态
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // 更新内容显示
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === tabName + '-tab') {
                    content.classList.add('active');
                }
            });
        });
    });
    
    // 回车键添加用户
    document.getElementById('new-username').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            addMonitorUser();
        }
    });
    
    document.getElementById('new-userid').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            addMonitorUser();
        }
    });
}

// 加载配置
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const result = await response.json();
        
        if (result.success) {
            currentConfig = result.data;
            updateConfigForm();
            showToast('配置加载成功', 'success');
        } else {
            showToast('加载配置失败: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('加载配置失败: ' + error.message, 'error');
    }
}

// 更新配置表单
function updateConfigForm() {
    // WebUI配置
    document.getElementById('webui-port').value = currentConfig.webui?.port || 10001;
    
    // 微信配置
    document.getElementById('wechat-enabled').checked = currentConfig.wechat?.enabled || false;
    document.getElementById('check-interval').value = currentConfig.wechat?.check_interval || 1.0;
    
    // OneBot配置
    document.getElementById('onebot-enabled').checked = currentConfig.onebot?.enabled || false;
    document.getElementById('ws-url').value = currentConfig.onebot?.ws_url || '';
    document.getElementById('access-token').value = currentConfig.onebot?.access_token || '';
}

// 保存配置
async function saveConfig() {
    try {
        // 收集表单数据
        const config = {
            webui: {
                ...currentConfig.webui,
                port: parseInt(document.getElementById('webui-port').value)
            },
            wechat: {
                ...currentConfig.wechat,
                enabled: document.getElementById('wechat-enabled').checked,
                check_interval: parseFloat(document.getElementById('check-interval').value)
            },
            onebot: {
                ...currentConfig.onebot,
                enabled: document.getElementById('onebot-enabled').checked,
                ws_url: document.getElementById('ws-url').value.trim(),
                access_token: document.getElementById('access-token').value.trim()
            }
        };
        
        // 验证配置
        const validateResponse = await fetch('/api/config/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const validateResult = await validateResponse.json();
        
        if (!validateResult.success) {
            showToast('配置验证失败: ' + validateResult.error, 'error');
            return;
        }
        
        if (!validateResult.valid) {
            showToast('配置验证失败: ' + validateResult.errors.join(', '), 'error');
            return;
        }
        
        // 保存配置
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentConfig = config;
            showToast('配置保存成功', 'success');
        } else {
            showToast('保存配置失败: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('保存配置失败: ' + error.message, 'error');
    }
}

// 重置配置
async function resetConfig() {
    if (!confirm('确定要重置为默认配置吗？这将清除所有自定义设置。')) {
        return;
    }
    
    try {
        // 这里应该调用重置API，暂时重新加载
        await loadConfig();
        showToast('配置已重置', 'info');
    } catch (error) {
        showToast('重置配置失败: ' + error.message, 'error');
    }
}

// 加载监听用户列表
async function loadMonitorUsers() {
    try {
        const response = await fetch('/api/monitor/users');
        const result = await response.json();
        
        if (result.success) {
            updateUsersList(result.data);
        } else {
            showToast('加载用户列表失败: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('加载用户列表失败: ' + error.message, 'error');
    }
}

// 更新用户列表显示
function updateUsersList(users) {
    const usersList = document.getElementById('monitor-users-list');
    usersList.innerHTML = '';
    
    if (users.length === 0) {
        usersList.innerHTML = '<li style="text-align: center; color: #718096;">暂无监听用户</li>';
        return;
    }
    
    users.forEach(user => {
        const li = document.createElement('li');
        let displayName, removeKey;
        
        // 处理两种格式：字符串和对象
        if (typeof user === 'string') {
            displayName = user;
            removeKey = user;
        } else if (typeof user === 'object' && user.nickname) {
            displayName = `${user.nickname} (QQ: ${user.user_id || 'N/A'})`;
            removeKey = user.nickname;
        } else {
            displayName = JSON.stringify(user);
            removeKey = user.nickname || user;
        }
        
        li.innerHTML = `
            <span><i class="fas fa-user"></i> ${displayName}</span>
            <button class="btn btn-danger" onclick="removeMonitorUser('${removeKey.replace(/'/g, "\'")}')">移除</button>
        `;
        usersList.appendChild(li);
    });
}

// 添加监听用户
async function addMonitorUser() {
    const usernameInput = document.getElementById('new-username');
    const useridInput = document.getElementById('new-userid');
    const nickname = usernameInput.value.trim();
    const user_id = useridInput.value.trim();
    
    if (!nickname) {
        showToast('请输入用户昵称', 'error');
        return;
    }
    
    if (!user_id) {
        showToast('请输入QQ号', 'error');
        return;
    }
    
    // 验证QQ号格式（纯数字）
    if (!/^\d+$/.test(user_id)) {
        showToast('QQ号必须是纯数字', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/monitor/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ nickname, user_id })
        });
        
        const result = await response.json();
        
        if (result.success) {
            usernameInput.value = '';
            useridInput.value = '';
            await loadMonitorUsers();
            showToast(result.message, 'success');
        } else {
            showToast('添加用户失败: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('添加用户失败: ' + error.message, 'error');
    }
}

// 移除监听用户
async function removeMonitorUser(username) {
    if (!confirm(`确定要移除监听用户 "${username}" 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/monitor/users/${encodeURIComponent(username)}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            await loadMonitorUsers();
            showToast(result.message, 'success');
        } else {
            showToast('移除用户失败: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('移除用户失败: ' + error.message, 'error');
    }
}

// 更新系统状态
async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const result = await response.json();
        
        if (result.success) {
            const status = result.data;
            
            // 更新头部状态栏
            updateStatusBar(status);
            
            // 更新状态页面
            updateStatusPage(status);
        }
    } catch (error) {
        console.error('更新状态失败:', error);
    }
}

// 更新状态栏
function updateStatusBar(status) {
    const wechatStatus = document.querySelector('#wechat-status .status-text');
    const onebotStatus = document.querySelector('#onebot-status .status-text');
    
    if (wechatStatus) {
        wechatStatus.textContent = status.wechat.running ? '运行中' : '已停止';
        wechatStatus.style.color = status.wechat.running ? '#48bb78' : '#f56565';
    }
    
    if (onebotStatus) {
        onebotStatus.textContent = status.onebot.connected ? '已连接' : '未连接';
        onebotStatus.style.color = status.onebot.connected ? '#48bb78' : '#f56565';
    }
}

// 更新状态页面
function updateStatusPage(status) {
    // 微信状态
    const wechatRunning = document.getElementById('wechat-running');
    const wechatUsersCount = document.getElementById('wechat-users-count');
    
    if (wechatRunning) {
        wechatRunning.textContent = status.wechat.running ? '运行中' : '已停止';
        wechatRunning.style.color = status.wechat.running ? '#48bb78' : '#f56565';
    }
    
    if (wechatUsersCount) {
        wechatUsersCount.textContent = status.wechat.monitor_users.length;
    }
    
    // OneBot状态
    const onebotConnected = document.getElementById('onebot-connected');
    const onebotUrl = document.getElementById('onebot-url');
    
    if (onebotConnected) {
        onebotConnected.textContent = status.onebot.connected ? '已连接' : '未连接';
        onebotConnected.style.color = status.onebot.connected ? '#48bb78' : '#f56565';
    }
    
    if (onebotUrl) {
        onebotUrl.textContent = status.onebot.ws_url || '未配置';
    }
}

// 控制服务
async function controlService(service, action) {
    try {
        const response = await fetch(`/api/control/${service}/${action}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(result.message, 'success');
            // 延迟更新状态
            setTimeout(updateStatus, 1000);
        } else {
            showToast('操作失败: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('操作失败: ' + error.message, 'error');
    }
}

// 刷新日志
function refreshLogs() {
    showToast('日志刷新功能开发中', 'info');
}

// 清空日志
function clearLogs() {
    if (confirm('确定要清空日志吗？')) {
        document.getElementById('log-content').textContent = '日志已清空';
        showToast('日志已清空', 'info');
    }
}

// 显示消息提示
function showToast(message, type = 'info') {
    const toast = document.getElementById('message-toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    
    // 显示提示
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);
    
    // 3秒后隐藏
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// 工具函数
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatTime(timestamp) {
    return new Date(timestamp).toLocaleString('zh-CN');
}