#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
负责配置文件的读取、写入和管理
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading

# 尝试导入AstrBot日志记录器
try:
    from astrbot.api import logger
except ImportError:
    # 在独立运行模式下，创建一个简单的日志记录器
    class SimpleLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def debug(self, msg): print(f"[DEBUG] {msg}")
    logger = SimpleLogger()

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = None):
        """初始化配置管理器
        
        Args:
            config_file: 配置文件路径，默认为 config/config.json
        """
        if config_file is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent
            config_dir = project_root / "config"
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / "config.json"
            
        self.config_file = Path(config_file)
        self.config_data = {}
        self._lock = threading.Lock()
        
        # 默认配置
        self.default_config = {
            "webui": {
                "host": "0.0.0.0",
                "port": 10001,
                "debug": False
            },
            "wechat": {
                "enabled": False,
                "monitor_users": [],  # 监听的用户昵称列表
                "check_interval": 1.0,  # 检查消息间隔(秒)
                "auto_reply": False  # 是否自动回复
            },
            "onebot": {
                "enabled": False,
                "ws_url": "ws://localhost:10001/ws",  # 反向WebSocket地址
                "access_token": "",  # 访问令牌
                "reconnect_interval": 5,  # 重连间隔(秒)
                "heartbeat_interval": 30,  # 心跳间隔(秒)
                "self_id": "wxauto_bot"  # 机器人ID
            },
            "message": {
                "max_length": 4096,  # 最大消息长度
                "enable_image": True,  # 启用图片消息
                "enable_file": True,  # 启用文件消息
                "enable_voice": False,  # 启用语音消息
                "image_cache_dir": "cache/images",  # 图片缓存目录
                "file_cache_dir": "cache/files"  # 文件缓存目录
            },
            "logging": {
                "level": "INFO",
                "file": "logs/app.log",
                "max_size": "10MB",
                "backup_count": 5
            }
        }
        
        # 加载配置文件
        self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件
        
        Returns:
            配置字典
        """
        with self._lock:
            try:
                if self.config_file.exists():
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        loaded_config = json.load(f)
                    
                    # 合并默认配置和加载的配置
                    self.config_data = self._merge_config(self.default_config, loaded_config)
                else:
                    # 如果配置文件不存在，使用默认配置
                    self.config_data = self.default_config.copy()
                    self.save_config()
                    
                return self.config_data.copy()
                
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                self.config_data = self.default_config.copy()
                return self.config_data.copy()
                
    def save_config(self) -> bool:
        """保存配置到文件
        
        Returns:
            是否保存成功
        """
        with self._lock:
            try:
                # 确保配置目录存在
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config_data, f, ensure_ascii=False, indent=2)
                    
                return True
                
            except Exception as e:
                logger.error(f"保存配置文件失败: {e}")
                return False
                
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键，如 'wechat.enabled'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any) -> bool:
        """设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
            
        Returns:
            是否设置成功
        """
        with self._lock:
            keys = key.split('.')
            config = self.config_data
            
            try:
                # 导航到最后一级的父级
                for k in keys[:-1]:
                    if k not in config:
                        config[k] = {}
                    config = config[k]
                    
                # 设置值
                config[keys[-1]] = value
                return True
                
            except Exception as e:
                logger.error(f"设置配置值失败: {e}")
                return False
                
    def update(self, updates: Dict[str, Any]) -> bool:
        """批量更新配置
        
        Args:
            updates: 要更新的配置字典
            
        Returns:
            是否更新成功
        """
        with self._lock:
            try:
                self.config_data = self._merge_config(self.config_data, updates)
                return True
            except Exception as e:
                logger.error(f"批量更新配置失败: {e}")
                return False
                
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置
        
        Returns:
            配置字典的副本
        """
        return self.config_data.copy()
        
    def reset_to_default(self) -> bool:
        """重置为默认配置
        
        Returns:
            是否重置成功
        """
        with self._lock:
            try:
                self.config_data = self.default_config.copy()
                return self.save_config()
            except Exception as e:
                logger.error(f"重置配置失败: {e}")
                return False
                
    def add_monitor_user(self, user_data) -> bool:
        """添加监听用户
        
        Args:
            user_data: 用户数据，可以是字符串（昵称）或字典（包含nickname和user_id）
            
        Returns:
            是否添加成功
        """
        monitor_users = self.get('wechat.monitor_users', [])
        
        # 检查是否已存在
        if isinstance(user_data, str):
            # 字符串格式
            if user_data not in monitor_users:
                monitor_users.append(user_data)
                return self.set('wechat.monitor_users', monitor_users)
        else:
            # 字典格式
            nickname = user_data.get('nickname')
            # 检查是否已存在相同昵称的用户
            for user in monitor_users:
                if isinstance(user, dict) and user.get('nickname') == nickname:
                    return True  # 已存在
                elif isinstance(user, str) and user == nickname:
                    return True  # 已存在
            
            monitor_users.append(user_data)
            return self.set('wechat.monitor_users', monitor_users)
        
        return True
        
    def remove_monitor_user(self, username: str) -> bool:
        """移除监听用户
        
        Args:
            username: 用户昵称
            
        Returns:
            是否移除成功
        """
        monitor_users = self.get('wechat.monitor_users', [])
        
        # 查找并移除匹配的用户
        for i, user in enumerate(monitor_users):
            if isinstance(user, str) and user == username:
                monitor_users.pop(i)
                return self.set('wechat.monitor_users', monitor_users)
            elif isinstance(user, dict) and user.get('nickname') == username:
                monitor_users.pop(i)
                return self.set('wechat.monitor_users', monitor_users)
        
        return False  # 未找到匹配的用户
        
    def get_monitor_users(self) -> List:
        """获取监听用户列表
        
        Returns:
            用户列表，可能包含字符串（昵称）或字典（包含nickname和user_id）
        """
        return self.get('wechat.monitor_users', [])
        
    def _merge_config(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """递归合并配置字典
        
        Args:
            base: 基础配置
            updates: 更新配置
            
        Returns:
            合并后的配置
        """
        result = base.copy()
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def validate_config(self) -> List[str]:
        """验证配置的有效性
        
        Returns:
            错误信息列表，空列表表示配置有效
        """
        errors = []
        
        # 验证WebUI配置
        port = self.get('webui.port')
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append("WebUI端口必须是1-65535之间的整数")
            
        # 验证OneBot配置
        if self.get('onebot.enabled'):
            ws_url = self.get('onebot.ws_url')
            if not ws_url or not ws_url.startswith(('ws://', 'wss://')):
                errors.append("OneBot WebSocket地址格式不正确")
                
        # 验证监听用户
        monitor_users = self.get('wechat.monitor_users', [])
        if not isinstance(monitor_users, list):
            errors.append("监听用户列表格式不正确")
            
        return errors