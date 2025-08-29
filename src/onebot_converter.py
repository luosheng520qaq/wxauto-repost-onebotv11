#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OneBotV11消息格式转换器
负责微信消息与OneBotV11协议格式之间的转换
"""

import json
import time
import base64
from typing import Dict, Any, List, Optional
from pathlib import Path
import mimetypes

class OneBotV11Converter:
    """OneBotV11协议消息转换器"""
    
    def __init__(self, config_manager):
        """初始化转换器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.self_id = config_manager.get('onebot.self_id', 'wxauto_bot')
        
    def wechat_to_onebot(self, wechat_msg: Dict[str, Any]) -> Dict[str, Any]:
        """将微信消息转换为OneBotV11格式
        
        Args:
            wechat_msg: 微信消息字典
            
        Returns:
            OneBotV11格式的消息
        """
        try:
            # 基础消息结构
            onebot_msg = {
                "time": wechat_msg.get('timestamp', int(time.time())),
                "self_id": self.self_id,
                "post_type": "message",
                "message_type": "private",  # 默认为私聊
                "sub_type": "friend",
                "message_id": self._generate_message_id(wechat_msg),
                "user_id": wechat_msg.get('user_id', ''),
                "message": [],
                "raw_message": "",
                "font": 0,
                "sender": {
                    "user_id": wechat_msg.get('user_id', ''),
                    "nickname": wechat_msg.get('user_name', ''),
                    "card": "",
                    "sex": "unknown",
                    "age": 0,
                    "area": "",
                    "level": "1",
                    "role": "member",
                    "title": ""
                }
            }
            
            # 根据消息类型转换内容
            msg_type = wechat_msg.get('message_type', 'text')
            
            if msg_type == 'text':
                onebot_msg.update(self._convert_text_message(wechat_msg))
            elif msg_type == 'image':
                onebot_msg.update(self._convert_image_message(wechat_msg))
            elif msg_type == 'file':
                onebot_msg.update(self._convert_file_message(wechat_msg))
            elif msg_type == 'voice':
                onebot_msg.update(self._convert_voice_message(wechat_msg))
            else:
                # 未知类型，当作文本处理
                onebot_msg.update(self._convert_text_message(wechat_msg))
                
            return onebot_msg
            
        except Exception as e:
            print(f"❌ 转换微信消息到OneBotV11格式失败: {e}")
            return self._create_error_message(wechat_msg, str(e))
            
    def onebot_to_wechat(self, onebot_msg: Dict[str, Any]) -> Dict[str, Any]:
        """将OneBotV11消息转换为微信格式
        
        Args:
            onebot_msg: OneBotV11格式的消息
            
        Returns:
            微信格式的消息
        """
        try:
            wechat_msg = {
                'user_id': onebot_msg.get('user_id', ''),
                'content': '',
                'message_type': 'text',
                'timestamp': onebot_msg.get('time', int(time.time()))
            }
            
            # 解析消息内容
            message = onebot_msg.get('message', [])
            if isinstance(message, str):
                # 如果message是字符串，直接作为文本内容
                wechat_msg['content'] = message
            elif isinstance(message, list):
                # 如果message是数组，解析CQ码
                wechat_msg.update(self._parse_onebot_message(message))
            else:
                wechat_msg['content'] = str(message)
                
            return wechat_msg
            
        except Exception as e:
            print(f"❌ 转换OneBotV11消息到微信格式失败: {e}")
            return {
                'user_id': onebot_msg.get('user_id', ''),
                'content': f'[消息解析失败: {e}]',
                'message_type': 'text',
                'timestamp': int(time.time())
            }
            
    def _generate_message_id(self, wechat_msg: Dict[str, Any]) -> int:
        """生成消息ID
        
        Args:
            wechat_msg: 微信消息
            
        Returns:
            消息ID
        """
        # 使用时间戳和用户ID生成唯一ID
        timestamp = wechat_msg.get('timestamp', int(time.time()))
        user_id = wechat_msg.get('user_id', '')
        return hash(f"{timestamp}_{user_id}_{wechat_msg.get('message_id', '')}") & 0x7FFFFFFF
        
    def _convert_text_message(self, wechat_msg: Dict[str, Any]) -> Dict[str, Any]:
        """转换文本消息
        
        Args:
            wechat_msg: 微信消息
            
        Returns:
            OneBotV11消息片段
        """
        content = wechat_msg.get('content', '')
        
        return {
            "message": [
                {
                    "type": "text",
                    "data": {
                        "text": content
                    }
                }
            ],
            "raw_message": content
        }
        
    def _convert_image_message(self, wechat_msg: Dict[str, Any]) -> Dict[str, Any]:
        """转换图片消息
        
        Args:
            wechat_msg: 微信消息
            
        Returns:
            OneBotV11消息片段
        """
        image_path = wechat_msg.get('image_path')
        image_url = wechat_msg.get('image_url')
        
        # 构建图片消息
        image_data = {}
        
        if image_path and Path(image_path).exists():
            # 如果有本地路径，转换为base64
            try:
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    image_data['file'] = f"base64://{image_base64}"
            except Exception as e:
                print(f"读取图片文件失败: {e}")
                image_data['file'] = image_path
        elif image_url:
            image_data['file'] = image_url
        else:
            image_data['file'] = "[图片]"  # 占位符
            
        return {
            "message": [
                {
                    "type": "image",
                    "data": image_data
                }
            ],
            "raw_message": "[CQ:image,file={}]".format(image_data.get('file', ''))
        }
        
    def _convert_file_message(self, wechat_msg: Dict[str, Any]) -> Dict[str, Any]:
        """转换文件消息
        
        Args:
            wechat_msg: 微信消息
            
        Returns:
            OneBotV11消息片段
        """
        file_path = wechat_msg.get('file_path')
        file_name = wechat_msg.get('file_name', 'unknown_file')
        
        # OneBotV11中文件消息可能需要特殊处理
        # 这里先转换为文本消息，包含文件信息
        content = f"[文件: {file_name}]"
        
        if file_path and Path(file_path).exists():
            file_size = Path(file_path).stat().st_size
            content = f"[文件: {file_name}, 大小: {self._format_file_size(file_size)}]"
            
        return {
            "message": [
                {
                    "type": "text",
                    "data": {
                        "text": content
                    }
                }
            ],
            "raw_message": content
        }
        
    def _convert_voice_message(self, wechat_msg: Dict[str, Any]) -> Dict[str, Any]:
        """转换语音消息
        
        Args:
            wechat_msg: 微信消息
            
        Returns:
            OneBotV11消息片段
        """
        voice_path = wechat_msg.get('voice_path')
        
        # 构建语音消息
        voice_data = {}
        
        if voice_path and Path(voice_path).exists():
            try:
                with open(voice_path, 'rb') as f:
                    voice_bytes = f.read()
                    voice_base64 = base64.b64encode(voice_bytes).decode('utf-8')
                    voice_data['file'] = f"base64://{voice_base64}"
            except Exception as e:
                print(f"读取语音文件失败: {e}")
                voice_data['file'] = voice_path
        else:
            voice_data['file'] = "[语音]"  # 占位符
            
        return {
            "message": [
                {
                    "type": "record",
                    "data": voice_data
                }
            ],
            "raw_message": "[CQ:record,file={}]".format(voice_data.get('file', ''))
        }
        
    def _parse_onebot_message(self, message: List[Dict[str, Any]]) -> Dict[str, Any]:
        """解析OneBotV11消息数组
        
        Args:
            message: OneBotV11消息数组
            
        Returns:
            微信消息字典
        """
        result = {
            'content': '',
            'message_type': 'text',
            'files': []  # 存储文件路径
        }
        
        content_parts = []
        
        for segment in message:
            seg_type = segment.get('type', 'text')
            seg_data = segment.get('data', {})
            
            if seg_type == 'text':
                text = seg_data.get('text', '')
                content_parts.append(text)
                
            elif seg_type == 'image':
                image_file = seg_data.get('file', '')
                image_path = self._process_image_file(image_file)
                
                if image_path:
                    result['message_type'] = 'image'
                    result['files'].append(image_path)
                    content_parts.append('[图片]')
                else:
                    content_parts.append('[图片]')
                    
            elif seg_type == 'record':
                voice_file = seg_data.get('file', '')
                voice_path = self._process_voice_file(voice_file)
                
                if voice_path:
                    result['message_type'] = 'voice'
                    result['files'].append(voice_path)
                    content_parts.append('[语音]')
                else:
                    content_parts.append('[语音]')
                    
            elif seg_type == 'at':
                qq = seg_data.get('qq', '')
                content_parts.append(f'@{qq}')
                
            elif seg_type == 'face':
                face_id = seg_data.get('id', '')
                content_parts.append(f'[表情{face_id}]')
                
            else:
                # 其他类型的消息段
                content_parts.append(f'[{seg_type}]')
                
        result['content'] = ''.join(content_parts)
        
        # 如果只有一个文件且没有文本，设置为对应的消息类型
        if len(result['files']) == 1 and not any(part.strip() and not part.startswith('[') for part in content_parts):
            file_path = result['files'][0]
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                result['message_type'] = 'image'
            elif file_path.lower().endswith(('.wav', '.mp3', '.amr', '.silk')):
                result['message_type'] = 'voice'
            else:
                result['message_type'] = 'file'
                
        return result
        
    def _process_image_file(self, file_data: str) -> Optional[str]:
        """处理图片文件
        
        Args:
            file_data: 文件数据（可能是base64、URL或路径）
            
        Returns:
            本地文件路径
        """
        try:
            if file_data.startswith('base64://'):
                # Base64编码的图片
                base64_data = file_data[9:]  # 去掉 'base64://' 前缀
                image_bytes = base64.b64decode(base64_data)
                
                # 保存到缓存目录
                project_root = Path(__file__).parent.parent
                cache_dir = project_root / self.config_manager.get('message.image_cache_dir', 'cache/images')
                cache_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = int(time.time())
                file_path = cache_dir / f"received_image_{timestamp}.jpg"
                
                with open(file_path, 'wb') as f:
                    f.write(image_bytes)
                    
                return str(file_path)
                
            elif file_data.startswith(('http://', 'https://')):
                # URL图片，这里可以下载或直接返回URL
                return file_data
                
            elif Path(file_data).exists():
                # 本地文件路径
                return file_data
                
            return None
            
        except Exception as e:
            print(f"处理图片文件失败: {e}")
            return None
            
    def _process_voice_file(self, file_data: str) -> Optional[str]:
        """处理语音文件
        
        Args:
            file_data: 文件数据
            
        Returns:
            本地文件路径
        """
        try:
            if file_data.startswith('base64://'):
                # Base64编码的语音
                base64_data = file_data[9:]
                voice_bytes = base64.b64decode(base64_data)
                
                # 保存到缓存目录
                project_root = Path(__file__).parent.parent
                cache_dir = project_root / self.config_manager.get('message.file_cache_dir', 'cache/files')
                cache_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = int(time.time())
                file_path = cache_dir / f"received_voice_{timestamp}.wav"
                
                with open(file_path, 'wb') as f:
                    f.write(voice_bytes)
                    
                return str(file_path)
                
            elif Path(file_data).exists():
                return file_data
                
            return None
            
        except Exception as e:
            print(f"处理语音文件失败: {e}")
            return None
            
    def _create_error_message(self, wechat_msg: Dict[str, Any], error: str) -> Dict[str, Any]:
        """创建错误消息
        
        Args:
            wechat_msg: 原始微信消息
            error: 错误信息
            
        Returns:
            错误消息的OneBotV11格式
        """
        return {
            "time": int(time.time()),
            "self_id": self.self_id,
            "post_type": "message",
            "message_type": "private",
            "sub_type": "friend",
            "message_id": int(time.time()),
            "user_id": wechat_msg.get('user_id', ''),
            "message": [
                {
                    "type": "text",
                    "data": {
                        "text": f"[消息转换失败: {error}]"
                    }
                }
            ],
            "raw_message": f"[消息转换失败: {error}]",
            "font": 0,
            "sender": {
                "user_id": wechat_msg.get('user_id', ''),
                "nickname": wechat_msg.get('user_name', ''),
                "card": "",
                "sex": "unknown",
                "age": 0,
                "area": "",
                "level": "1",
                "role": "member",
                "title": ""
            }
        }
        
    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小
        
        Args:
            size_bytes: 文件大小（字节）
            
        Returns:
            格式化的文件大小字符串
        """
        if size_bytes == 0:
            return "0 B"
            
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
            
        return f"{size:.1f} {size_names[i]}"
        
    def create_heartbeat(self) -> Dict[str, Any]:
        """创建心跳包
        
        Returns:
            心跳包数据
        """
        return {
            "time": int(time.time()),
            "self_id": self.self_id,
            "post_type": "meta_event",
            "meta_event_type": "heartbeat",
            "status": {
                "online": True,
                "good": True
            },
            "interval": self.config_manager.get('onebot.heartbeat_interval', 30) * 1000
        }
        
    def create_lifecycle_event(self, sub_type: str = "connect") -> Dict[str, Any]:
        """创建生命周期事件
        
        Args:
            sub_type: 事件子类型 (connect/enable/disable)
            
        Returns:
            生命周期事件数据
        """
        return {
            "time": int(time.time()),
            "self_id": self.self_id,
            "post_type": "meta_event",
            "meta_event_type": "lifecycle",
            "sub_type": sub_type
        }