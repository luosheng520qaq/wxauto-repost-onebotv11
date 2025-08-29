#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反向WebSocket客户端
负责与后端服务建立WebSocket连接，发送和接收OneBotV11消息
"""

import json
import time
import threading
from typing import Dict, Any, Callable, Optional
import websocket
from queue import Queue, Empty

class WebSocketClient:
    """反向WebSocket客户端"""
    
    def __init__(self, config_manager, onebot_converter):
        """初始化WebSocket客户端
        
        Args:
            config_manager: 配置管理器
            onebot_converter: OneBotV11转换器
        """
        self.config_manager = config_manager
        self.onebot_converter = onebot_converter
        
        # WebSocket连接
        self.ws = None
        self.ws_url = ""
        self.is_connected = False
        self.is_running = False
        
        # 线程管理
        self.connect_thread = None
        self.heartbeat_thread = None
        
        # 消息队列
        self.send_queue = Queue()
        self.receive_queue = Queue()
        
        # 回调函数
        self.on_message_callback = None
        self.on_connect_callback = None
        self.on_disconnect_callback = None
        
        # 重连配置
        self.reconnect_interval = 5  # 重连间隔（秒）
        self.max_reconnect_attempts = 10  # 最大重连次数
        self.reconnect_attempts = 0
        
        # 心跳配置
        self.heartbeat_interval = 30  # 心跳间隔（秒）
        self.last_heartbeat = 0
        
    def set_callbacks(self, on_message: Callable = None, on_connect: Callable = None, on_disconnect: Callable = None):
        """设置回调函数
        
        Args:
            on_message: 收到消息时的回调
            on_connect: 连接成功时的回调
            on_disconnect: 连接断开时的回调
        """
        self.on_message_callback = on_message
        self.on_connect_callback = on_connect
        self.on_disconnect_callback = on_disconnect
        
    def start(self) -> bool:
        """启动WebSocket客户端
        
        Returns:
            是否启动成功
        """
        try:
            # 获取WebSocket地址
            self.ws_url = self.config_manager.get('onebot.ws_url', '')
            if not self.ws_url:
                print("错误: 未配置反向WebSocket地址")
                return False
                
            print(f"启动WebSocket客户端，连接地址: {self.ws_url}")
            
            self.is_running = True
            self.reconnect_attempts = 0
            
            # 启动连接线程
            self.connect_thread = threading.Thread(target=self._connect_loop, daemon=True)
            self.connect_thread.start()
            
            # 启动心跳线程
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()
            
            return True
            
        except Exception as e:
            print(f"启动WebSocket客户端失败: {e}")
            return False
            
    def stop(self):
        """停止WebSocket客户端"""
        print("停止WebSocket客户端")
        
        self.is_running = False
        
        # 关闭WebSocket连接
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None
            
        self.is_connected = False
        
        # 等待线程结束
        if self.connect_thread and self.connect_thread.is_alive():
            self.connect_thread.join(timeout=2)
            
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=2)
            
    def send_message(self, message: Dict[str, Any]) -> bool:
        """发送消息
        
        Args:
            message: 要发送的消息
            
        Returns:
            是否发送成功
        """
        try:
            if not self.is_connected or not self.ws:
                print("WebSocket未连接，消息加入发送队列")
                self.send_queue.put(message)
                return False
                
            # 转换为JSON并发送
            json_data = json.dumps(message, ensure_ascii=False)
            self.ws.send(json_data)
            
            print(f"发送消息: {message.get('post_type', 'unknown')}")
            return True
            
        except Exception as e:
            print(f"发送消息失败: {e}")
            # 将消息加入队列等待重发
            self.send_queue.put(message)
            return False
            
    def send_wechat_message(self, wechat_msg: Dict[str, Any]) -> bool:
        """发送微信消息（自动转换为OneBotV11格式）
        
        Args:
            wechat_msg: 微信消息
            
        Returns:
            是否发送成功
        """
        try:
            # 转换为OneBotV11格式
            onebot_msg = self.onebot_converter.wechat_to_onebot(wechat_msg)
            return self.send_message(onebot_msg)
            
        except Exception as e:
            print(f"❌ 发送微信消息失败: {e}")
            return False
            
    def get_received_message(self) -> Optional[Dict[str, Any]]:
        """获取接收到的消息
        
        Returns:
            接收到的消息，如果没有则返回None
        """
        try:
            return self.receive_queue.get_nowait()
        except Empty:
            return None
            
    def _connect_loop(self):
        """连接循环"""
        while self.is_running:
            try:
                if not self.is_connected:
                    self._connect()
                    
                time.sleep(1)
                
            except Exception as e:
                print(f"连接循环异常: {e}")
                time.sleep(self.reconnect_interval)
                
    def _connect(self):
        """建立WebSocket连接"""
        try:
            print(f"尝试连接WebSocket: {self.ws_url}")
            
            # 准备连接头
            headers = {}
            access_token = self.config_manager.get('onebot.access_token', '')
            if access_token:
                headers['Authorization'] = f'Bearer {access_token}'
                print("已添加access_token认证")
            
            # 添加OneBotV11标准要求的头部信息
            headers['X-Self-ID'] = '10001000'  # 机器人QQ号，可以从配置获取
            headers['X-Client-Role'] = 'Universal'  # 客户端类型：Universal支持API和Event
            
            # 创建WebSocket连接
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                header=headers,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # 启动连接（阻塞）
            self.ws.run_forever()
            
        except Exception as e:
            print(f"WebSocket连接失败: {e}")
            self._handle_reconnect()
            
    def _on_open(self, ws):
        """WebSocket连接打开回调"""
        print("WebSocket连接已建立")
        
        self.is_connected = True
        self.reconnect_attempts = 0
        
        # 发送生命周期事件
        lifecycle_event = self.onebot_converter.create_lifecycle_event("connect")
        self.send_message(lifecycle_event)
        
        # 处理发送队列中的消息
        self._process_send_queue()
        
        # 调用连接回调
        if self.on_connect_callback:
            try:
                self.on_connect_callback()
            except Exception as e:
                print(f"连接回调执行失败: {e}")
                
    def _on_message(self, ws, message):
        """WebSocket消息接收回调"""
        try:
            # 解析JSON消息
            data = json.loads(message)
            print(f"收到消息: {data.get('action', 'unknown')}")
            
            # 将消息加入接收队列
            self.receive_queue.put(data)
            
            # 调用消息回调
            if self.on_message_callback:
                try:
                    self.on_message_callback(data)
                except Exception as e:
                    print(f"消息回调执行失败: {e}")
                    
        except json.JSONDecodeError as e:
            print(f"解析消息JSON失败: {e}")
        except Exception as e:
            print(f"处理接收消息失败: {e}")
            
    def _on_error(self, ws, error):
        """WebSocket错误回调"""
        print(f"WebSocket错误: {error}")
        
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket连接关闭回调"""
        print(f"WebSocket连接已关闭: {close_status_code} - {close_msg}")
        
        self.is_connected = False
        
        # 调用断开连接回调
        if self.on_disconnect_callback:
            try:
                self.on_disconnect_callback()
            except Exception as e:
                print(f"断开连接回调执行失败: {e}")
                
        # 如果还在运行状态，尝试重连
        if self.is_running:
            self._handle_reconnect()
            
    def _handle_reconnect(self):
        """处理重连"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            print(f"达到最大重连次数({self.max_reconnect_attempts})，停止重连")
            return
            
        self.reconnect_attempts += 1
        print(f"准备重连 ({self.reconnect_attempts}/{self.max_reconnect_attempts})，{self.reconnect_interval}秒后重试")
        
        time.sleep(self.reconnect_interval)
        
    def _process_send_queue(self):
        """处理发送队列中的消息"""
        while not self.send_queue.empty():
            try:
                message = self.send_queue.get_nowait()
                self.send_message(message)
            except Empty:
                break
            except Exception as e:
                print(f"处理发送队列消息失败: {e}")
                
    def _heartbeat_loop(self):
        """心跳循环"""
        while self.is_running:
            try:
                current_time = time.time()
                
                # 检查是否需要发送心跳
                if (self.is_connected and 
                    current_time - self.last_heartbeat >= self.heartbeat_interval):
                    
                    # 发送心跳包
                    heartbeat = self.onebot_converter.create_heartbeat()
                    if self.send_message(heartbeat):
                        self.last_heartbeat = current_time
                        
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                print(f"心跳循环异常: {e}")
                time.sleep(5)
                
    def get_status(self) -> Dict[str, Any]:
        """获取客户端状态
        
        Returns:
            状态信息
        """
        return {
            'is_running': self.is_running,
            'is_connected': self.is_connected,
            'ws_url': self.ws_url,
            'reconnect_attempts': self.reconnect_attempts,
            'send_queue_size': self.send_queue.qsize(),
            'receive_queue_size': self.receive_queue.qsize(),
            'last_heartbeat': self.last_heartbeat
        }
        
    def update_config(self):
        """更新配置"""
        try:
            # 获取新的WebSocket地址
            new_ws_url = self.config_manager.get('websocket.reverse_ws_url', '')
            
            # 如果地址发生变化，重新连接
            if new_ws_url != self.ws_url and new_ws_url:
                print(f"WebSocket地址已更新: {self.ws_url} -> {new_ws_url}")
                self.ws_url = new_ws_url
                
                # 重新连接
                if self.is_running:
                    self.stop()
                    time.sleep(1)
                    self.start()
                    
            # 更新心跳间隔
            self.heartbeat_interval = self.config_manager.get('onebot.heartbeat_interval', 30)
            
            # 更新重连配置
            self.reconnect_interval = self.config_manager.get('websocket.reconnect_interval', 5)
            self.max_reconnect_attempts = self.config_manager.get('websocket.max_reconnect_attempts', 10)
            
        except Exception as e:
            print(f"更新WebSocket配置失败: {e}")
            
    def send_api_response(self, echo: str, data: Any = None, retcode: int = 0, status: str = "ok"):
        """发送API响应
        
        Args:
            echo: 请求的echo字段
            data: 响应数据
            retcode: 返回码
            status: 状态
        """
        response = {
            "status": status,
            "retcode": retcode,
            "data": data,
            "echo": echo
        }
        
        self.send_message(response)
        
    def handle_api_request(self, request: Dict[str, Any]) -> bool:
        """处理API请求
        
        Args:
            request: API请求
            
        Returns:
            是否处理成功
        """
        try:
            action = request.get('action', '')
            echo = request.get('echo', '')
            params = request.get('params', {})
            
            print(f"收到API请求: {action}")
            
            # 根据不同的action处理请求
            if action == 'get_login_info':
                # 获取登录信息
                data = {
                    "user_id": self.onebot_converter.self_id,
                    "nickname": "WxAuto Bot"
                }
                self.send_api_response(echo, data)
                
            elif action == 'get_status':
                # 获取状态
                data = {
                    "online": self.is_connected,
                    "good": True
                }
                self.send_api_response(echo, data)
                
            elif action == 'send_private_msg':
                # 发送私聊消息 - 这个需要在消息处理模块中实现
                # 这里只是发送成功响应
                data = {"message_id": int(time.time())}
                self.send_api_response(echo, data)
                
            else:
                # 未知的API请求
                self.send_api_response(echo, None, 1404, "failed")
                
            return True
            
        except Exception as e:
            print(f"处理API请求失败: {e}")
            if 'echo' in locals():
                self.send_api_response(echo, None, 1500, "failed")
            return False