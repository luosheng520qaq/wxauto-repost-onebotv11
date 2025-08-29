#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web UI模块
提供Web界面进行配置管理和状态监控
"""

import json
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
import os

class WebUI:
    """Web用户界面"""
    
    def __init__(self, config_manager, wechat_monitor=None, onebot_client=None, websocket_client=None, message_handler=None):
        """初始化WebUI
        
        Args:
            config_manager: 配置管理器
            wechat_monitor: 微信监听器
            onebot_client: OneBot客户端
            websocket_client: WebSocket客户端
            message_handler: 消息处理器
        """
        self.config_manager = config_manager
        self.wechat_monitor = wechat_monitor
        self.onebot_client = onebot_client
        self.websocket_client = websocket_client
        self.message_handler = message_handler
        
        # 创建Flask应用
        self.app = Flask(__name__, 
                        template_folder=self._get_template_dir(),
                        static_folder=self._get_static_dir())
        CORS(self.app)
        
        # 设置路由
        self._setup_routes()
        
        self.running = False
        
    def _get_template_dir(self):
        """获取模板目录"""
        # 模板目录在src/templates
        template_dir = Path(__file__).parent / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        return str(template_dir)
        
    def _get_static_dir(self):
        """获取静态文件目录"""
        project_root = Path(__file__).parent.parent
        static_dir = project_root / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        return str(static_dir)
        
    def _setup_routes(self):
        """设置路由"""
        
        @self.app.route('/')
        def index():
            """主页"""
            return render_template('index.html')
            
        @self.app.route('/api/config', methods=['GET'])
        def get_config():
            """获取配置"""
            try:
                config = self.config_manager.get_all()
                return jsonify({
                    'success': True,
                    'data': config
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
                
        @self.app.route('/api/config', methods=['POST'])
        def update_config():
            """更新配置"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': '无效的JSON数据'
                    }), 400
                    
                # 更新配置
                success = self.config_manager.update(data)
                if success:
                    # 保存配置
                    self.config_manager.save_config()
                    return jsonify({
                        'success': True,
                        'message': '配置更新成功'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': '配置更新失败'
                    }), 500
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
                
        @self.app.route('/api/config/validate', methods=['POST'])
        def validate_config():
            """验证配置"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': '无效的JSON数据'
                    }), 400
                    
                # 临时更新配置进行验证
                old_config = self.config_manager.get_all()
                self.config_manager.update(data)
                
                # 验证配置
                errors = self.config_manager.validate_config()
                
                # 恢复原配置
                self.config_manager.config_data = old_config
                
                return jsonify({
                    'success': True,
                    'valid': len(errors) == 0,
                    'errors': errors
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
                
        @self.app.route('/api/monitor/users', methods=['GET'])
        def get_monitor_users():
            """获取监听用户列表"""
            try:
                users = self.config_manager.get_monitor_users()
                return jsonify({
                    'success': True,
                    'data': users
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
                
        @self.app.route('/api/monitor/users', methods=['POST'])
        def add_monitor_user():
            """添加监听用户"""
            try:
                data = request.get_json()
                
                # 支持新格式（nickname + user_id）和旧格式（username）
                if 'nickname' in data and 'user_id' in data:
                    # 新格式：包含昵称和用户ID的映射
                    nickname = data.get('nickname', '').strip()
                    user_id = data.get('user_id', '').strip()
                    
                    if not nickname:
                        return jsonify({
                            'success': False,
                            'error': '昵称不能为空'
                        }), 400
                        
                    if not user_id:
                        return jsonify({
                            'success': False,
                            'error': '用户ID不能为空'
                        }), 400
                    
                    user_data = {
                        'nickname': nickname,
                        'user_id': user_id
                    }
                    success = self.config_manager.add_monitor_user(user_data)
                    display_name = f'{nickname} (QQ: {user_id})'
                else:
                    # 旧格式：仅用户名
                    username = data.get('username', '').strip()
                    
                    if not username:
                        return jsonify({
                            'success': False,
                            'error': '用户名不能为空'
                        }), 400
                        
                    success = self.config_manager.add_monitor_user(username)
                    display_name = username
                
                if success:
                    self.config_manager.save_config()
                    return jsonify({
                        'success': True,
                        'message': f'已添加监听用户: {display_name}'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': '添加用户失败'
                    }), 500
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
                
        @self.app.route('/api/monitor/users/<username>', methods=['DELETE'])
        def remove_monitor_user(username):
            """移除监听用户"""
            try:
                success = self.config_manager.remove_monitor_user(username)
                if success:
                    self.config_manager.save_config()
                    return jsonify({
                        'success': True,
                        'message': f'已移除监听用户: {username}'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': '移除用户失败'
                    }), 500
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
                
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """获取系统状态"""
            try:
                status = {
                    'wechat': {
                        'enabled': self.config_manager.get('wechat.enabled', False),
                        'running': self.wechat_monitor.running if self.wechat_monitor else False,
                        'monitor_users': self.config_manager.get_monitor_users()
                    },
                    'onebot': {
                        'enabled': self.config_manager.get('onebot.enabled', False),
                        'connected': self.websocket_client.is_connected if self.websocket_client else False,
                        'ws_url': self.config_manager.get('onebot.ws_url', '')
                    },
                    'webui': {
                        'running': self.running,
                        'port': self.config_manager.get('webui.port', 10001)
                    }
                }
                
                return jsonify({
                    'success': True,
                    'data': status
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
                
        @self.app.route('/api/control/<service>/<action>', methods=['POST'])
        def control_service(service, action):
            """控制服务"""
            try:
                if service == 'wechat' and self.wechat_monitor:
                    if action == 'start':
                        result = self.wechat_monitor.start()
                        message = '微信监听已启动' if result else '微信监听启动失败'
                    elif action == 'stop':
                        result = self.wechat_monitor.stop()
                        message = '微信监听已停止' if result else '微信监听停止失败'
                    else:
                        return jsonify({
                            'success': False,
                            'error': '无效的操作'
                        }), 400
                        
                elif service == 'onebot' and self.onebot_client:
                    if action == 'start':
                        result = self.onebot_client.start()
                        message = 'OneBot客户端已启动' if result else 'OneBot客户端启动失败'
                    elif action == 'stop':
                        result = self.onebot_client.stop()
                        message = 'OneBot客户端已停止' if result else 'OneBot客户端停止失败'
                    else:
                        return jsonify({
                            'success': False,
                            'error': '无效的操作'
                        }), 400
                else:
                    return jsonify({
                        'success': False,
                        'error': '无效的服务'
                    }), 400
                    
                return jsonify({
                    'success': result,
                    'message': message
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
                
    def run(self):
        """启动Web服务器"""
        if self.running:
            return
            
        self.running = True
        
        # 创建静态文件
        self._create_static_files()
        
        host = self.config_manager.get('webui.host', '0.0.0.0')
        port = self.config_manager.get('webui.port', 10001)
        debug = self.config_manager.get('webui.debug', False)
        
        try:
            self.app.run(host=host, port=port, debug=debug, threaded=True)
        except Exception as e:
            print(f"Web服务器启动失败: {e}")
            self.running = False
            
    def start(self):
        """启动Web UI服务"""
        try:
            port = self.config_manager.get('webui.port', 10001)
            print(f"启动Web UI服务，端口: {port}")
            # 在单独的线程中启动Flask应用，避免阻塞主线程
            self.web_thread = threading.Thread(target=self.run, daemon=True)
            self.web_thread.start()
        except Exception as e:
            print(f"Web UI启动失败: {e}")
            raise
            
    def stop(self):
        """停止Web服务器"""
        self.running = False
        print("Web UI服务停止")
        
    def _create_static_files(self):
        """创建静态文件"""
        # 创建HTML模板
        self._create_html_template()
        
        # 创建CSS文件
        self._create_css_files()
        
        # 创建JavaScript文件
        self._create_js_files()
        
    def _create_html_template(self):
        """创建HTML模板 - 现在使用独立的模板文件"""
        # HTML模板已移动到 templates/index.html
        # 不再需要动态创建HTML文件
        pass
            
    def _create_css_files(self):
        """创建CSS文件"""
        css_dir = Path(self._get_static_dir()) / "css"
        css_dir.mkdir(exist_ok=True)
        
        css_content = '''/* 基础样式 */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    color: #333;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

/* 头部样式 */
header {
    background: rgba(255, 255, 255, 0.95);
    border-radius: 15px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    backdrop-filter: blur(10px);
}

header h1 {
    color: #4a5568;
    margin-bottom: 15px;
    font-size: 2rem;
}

.status-bar {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
}

.status-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 15px;
    background: #f7fafc;
    border-radius: 8px;
    border-left: 4px solid #4299e1;
}

.status-item i {
    color: #4299e1;
}

.status-text {
    font-weight: 600;
}

/* 标签页样式 */
.tabs {
    display: flex;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 10px;
    padding: 5px;
    margin-bottom: 20px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.tab-button {
    flex: 1;
    padding: 12px 20px;
    border: none;
    background: transparent;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: 500;
}

.tab-button:hover {
    background: rgba(66, 153, 225, 0.1);
}

.tab-button.active {
    background: #4299e1;
    color: white;
    box-shadow: 0 2px 8px rgba(66, 153, 225, 0.3);
}

/* 主内容区域 */
main {
    background: rgba(255, 255, 255, 0.95);
    border-radius: 15px;
    padding: 30px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    backdrop-filter: blur(10px);
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
}

/* 配置组样式 */
.config-group {
    margin-bottom: 30px;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 10px;
    border-left: 4px solid #4299e1;
}

.config-group h3 {
    color: #2d3748;
    margin-bottom: 15px;
    font-size: 1.2rem;
}

.form-group {
    margin-bottom: 15px;
}

.form-group label {
    display: block;
    margin-bottom: 5px;
    font-weight: 500;
    color: #4a5568;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group input[type="password"] {
    width: 100%;
    padding: 10px 15px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    font-size: 14px;
    transition: border-color 0.3s ease;
}

.form-group input:focus {
    outline: none;
    border-color: #4299e1;
    box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
}

.form-group input[type="checkbox"] {
    margin-right: 8px;
    transform: scale(1.2);
}

.input-group {
    display: flex;
    gap: 10px;
}

.input-group input {
    flex: 1;
}

/* 按钮样式 */
.btn {
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.3s ease;
    text-decoration: none;
    display: inline-block;
}

.btn-primary {
    background: #4299e1;
    color: white;
}

.btn-primary:hover {
    background: #3182ce;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(66, 153, 225, 0.3);
}

.btn-secondary {
    background: #718096;
    color: white;
}

.btn-secondary:hover {
    background: #4a5568;
    transform: translateY(-2px);
}

.btn-success {
    background: #48bb78;
    color: white;
}

.btn-success:hover {
    background: #38a169;
    transform: translateY(-2px);
}

.btn-danger {
    background: #f56565;
    color: white;
}

.btn-danger:hover {
    background: #e53e3e;
    transform: translateY(-2px);
}

.button-group {
    display: flex;
    gap: 10px;
    margin-top: 20px;
    flex-wrap: wrap;
}

/* 用户列表样式 */
.user-list {
    margin-top: 20px;
}

#monitor-users-list {
    list-style: none;
    padding: 0;
}

#monitor-users-list li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 15px;
    margin-bottom: 8px;
    background: white;
    border-radius: 8px;
    border-left: 4px solid #48bb78;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* 状态卡片样式 */
.status-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
}

.status-card {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 20px;
    border-left: 4px solid #4299e1;
}

.status-card h3 {
    color: #2d3748;
    margin-bottom: 15px;
}

.status-info p {
    margin-bottom: 8px;
    color: #4a5568;
}

.control-buttons {
    margin-top: 15px;
    display: flex;
    gap: 10px;
}

/* 日志样式 */
.log-container {
    background: #1a202c;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    max-height: 400px;
    overflow-y: auto;
}

#log-content {
    color: #e2e8f0;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.4;
    white-space: pre-wrap;
}

/* 消息提示样式 */
.toast {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    border-radius: 8px;
    color: white;
    font-weight: 500;
    z-index: 1000;
    transform: translateX(400px);
    transition: transform 0.3s ease;
}

.toast.show {
    transform: translateX(0);
}

.toast.success {
    background: #48bb78;
}

.toast.error {
    background: #f56565;
}

.toast.info {
    background: #4299e1;
}

/* 响应式设计 */
@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
    
    .tabs {
        flex-direction: column;
    }
    
    .status-bar {
        flex-direction: column;
    }
    
    .button-group {
        flex-direction: column;
    }
    
    .input-group {
        flex-direction: column;
    }
    
    .control-buttons {
        flex-direction: column;
    }
}

/* 动画效果 */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.tab-content.active {
    animation: fadeIn 0.3s ease;
}

/* 加载状态 */
.loading {
    opacity: 0.6;
    pointer-events: none;
}

.loading::after {
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    width: 20px;
    height: 20px;
    margin: -10px 0 0 -10px;
    border: 2px solid #4299e1;
    border-top: 2px solid transparent;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}'''
        
        css_file = css_dir / "style.css"
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(css_content)
            
    def _create_js_files(self):
        """创建JavaScript文件"""
        js_dir = Path(self._get_static_dir()) / "js"
        js_dir.mkdir(exist_ok=True)
        
        js_content = '''// 全局变量
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
            <button class="btn btn-danger" onclick="removeMonitorUser('${removeKey.replace(/'/g, "\\'")}')">移除</button>
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
    if (!/^\\d+$/.test(user_id)) {
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
}'''
        
        js_file = js_dir / "app.js"
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write(js_content)