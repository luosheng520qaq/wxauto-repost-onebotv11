#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信消息转发框架 - AstrBot插件版本
基于wxauto库和OneBotV11协议的完整框架
可以作为独立应用运行，也可以作为AstrBot插件使用
"""

import sys
import time
import signal
import asyncio
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from config_manager import ConfigManager
from wechat_monitor import WeChatMonitor
from web_ui import WebUI
from onebot_converter import OneBotV11Converter
from websocket_client import WebSocketClient
from message_handler import MessageHandler

# AstrBot插件相关导入（如果可用）
try:
    from astrbot.api.star import Context, Star, register
    from astrbot.api import logger
    ASTRBOT_AVAILABLE = True
except ImportError:
    ASTRBOT_AVAILABLE = False
    # 在独立运行模式下，创建一个简单的日志记录器
    class SimpleLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def debug(self, msg): print(f"[DEBUG] {msg}")
    logger = SimpleLogger()

class WxAutoOneBotApp:
    """微信消息转发应用主类"""
    
    def __init__(self):
        """初始化应用"""
        logger.info("初始化微信消息转发框架...")
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 初始化各个组件
        self.wechat_monitor = None
        self.web_ui = None
        self.onebot_converter = None
        self.websocket_client = None
        self.message_handler = None
        
        # 运行状态
        self.is_running = False
        
    def initialize_components(self):
        """初始化所有组件"""
        try:
            logger.info("初始化组件...")
            
            # 初始化OneBotV11转换器
            self.onebot_converter = OneBotV11Converter(self.config_manager)
            
            # 初始化微信监听器
            self.wechat_monitor = WeChatMonitor(self.config_manager)
            
            # 初始化WebSocket客户端
            self.websocket_client = WebSocketClient(self.config_manager, self.onebot_converter)
            
            # 初始化消息处理器
            self.message_handler = MessageHandler(
                self.config_manager,
                self.wechat_monitor,
                self.onebot_converter,
                self.websocket_client
            )
            
            # 初始化Web UI
            self.web_ui = WebUI(
                self.config_manager,
                self.wechat_monitor,
                self.websocket_client,  # onebot_client
                self.websocket_client,
                self.message_handler
            )
            
            # 设置微信监听器的消息回调
            self.wechat_monitor.set_message_callback(self.message_handler.handle_wechat_message)
            
            logger.info("组件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化组件失败: {e}")
            return False
        
    def start(self):
        """启动应用"""
        try:
            logger.info("🚀 启动微信消息转发框架...")
            
            # 初始化组件
            if not self.initialize_components():
                return False
                
            self.is_running = True
            
            # 启动消息处理器
            if self.message_handler:
                self.message_handler.start()
                
            # 启动WebSocket客户端（如果配置了地址）
            ws_url = self.config_manager.get('onebot.ws_url', '')
            if ws_url and self.websocket_client:
                logger.info(f"🔗 启动WebSocket客户端: {ws_url}")
                self.websocket_client.start()
            else:
                logger.warning("⚠️  未配置WebSocket地址，跳过客户端启动")
                
            # 启动微信监听器（如果有监听用户）
            monitored_users = self.config_manager.get('wechat.monitor_users', [])
            if monitored_users and self.wechat_monitor:
                logger.info(f"👂 启动微信监听器，监听用户: {[user.get('nickname') if isinstance(user, dict) else user for user in monitored_users]}")
                self.wechat_monitor.start()
            else:
                logger.warning("⚠️  未配置监听用户，跳过监听器启动")
                
            # 启动Web UI（最后启动，避免输出被覆盖）
            if self.web_ui:
                web_port = self.config_manager.get('webui.port', 10001)
                logger.info(f"🌐 启动Web UI，端口: {web_port}")
                logger.info("📝 注意：Web UI启动后，日志输出可能会被Flask覆盖")
                self.web_ui.start()
                
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动应用失败: {e}")
            return False
            
    def stop(self):
        """停止应用"""
        try:
            logger.info("🛑 停止微信消息转发框架...")
            
            self.is_running = False
            
            # 停止各个组件
            if self.wechat_monitor:
                self.wechat_monitor.stop()
                
            if self.websocket_client:
                self.websocket_client.stop()
                
            if self.message_handler:
                self.message_handler.stop()
                
            if self.web_ui:
                self.web_ui.stop()
            
            logger.info("✅ 应用已停止")
            
        except Exception as e:
            logger.error(f"❌ 停止应用失败: {e}")
            
    def restart_services(self):
        """重启服务（配置更新后）"""
        try:
            logger.info("重启服务...")
            
            # 停止相关服务
            if self.wechat_monitor:
                self.wechat_monitor.stop()
                
            if self.websocket_client:
                self.websocket_client.stop()
                
            time.sleep(2)  # 等待服务完全停止
            
            # 重新启动服务
            ws_url = self.config_manager.get('onebot.ws_url', '')
            if ws_url and self.websocket_client:
                self.websocket_client.start()
                
            monitored_users = self.config_manager.get('wechat.monitor_users', [])
            if monitored_users and self.wechat_monitor:
                self.wechat_monitor.start()
                
            logger.info("服务重启完成")
            
        except Exception as e:
            logger.error(f"重启服务失败: {e}")
            
    def get_status(self):
        """获取应用状态"""
        status = {
            'is_running': self.is_running,
            'wechat_monitor': self.wechat_monitor.get_status() if self.wechat_monitor else None,
            'websocket_client': self.websocket_client.get_status() if self.websocket_client else None,
            'message_handler': self.message_handler.get_status() if self.message_handler else None
        }
        return status
            
    def signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"\n收到信号 {signum}，正在停止应用...")
        self.stop()
        sys.exit(0)

# AstrBot插件类
if ASTRBOT_AVAILABLE:
    @register("wxauto_repost", "AstrBot Team", "微信消息转发框架插件 - 基于wxauto库和OneBotV11协议", "1.1.0", "https://github.com/luosheng520qaq/wxauto-repost-onebotv11")
    class WxAutoRepostPlugin(Star):
        """微信消息转发框架AstrBot插件"""
        
        def __init__(self, context: Context):
            super().__init__(context)
            self.app = None
            logger.info("微信消息转发框架插件已加载")
            
        async def initialize(self):
            """插件初始化"""
            try:
                logger.info("正在初始化微信消息转发框架...")
                self.app = WxAutoOneBotApp()
                
                # 在后台异步启动应用，避免阻塞AstrBot主线程
                def start_app():
                    try:
                        if self.app.start():
                            logger.info("✅ 微信消息转发框架启动成功")
                            logger.info("🌐 访问 http://localhost:10001 进行配置")
                        else:
                            logger.error("❌ 微信消息转发框架启动失败")
                    except Exception as e:
                        logger.error(f"微信消息转发框架启动异常: {e}")
                
                # 使用线程池在后台启动，避免阻塞
                import threading
                start_thread = threading.Thread(target=start_app, daemon=True)
                start_thread.start()
                
                logger.info("微信消息转发框架正在后台启动...")
                    
            except Exception as e:
                logger.error(f"微信消息转发框架初始化失败: {e}")
                
        async def terminate(self):
            """插件卸载时调用"""
            if self.app:
                logger.info("正在停止微信消息转发框架...")
                self.app.stop()
                logger.info("微信消息转发框架已停止")

def main():
    """主函数 - 独立运行模式"""
    logger.info("="*50)
    logger.info("🤖 微信消息转发框架 v1.0")
    logger.info("📱 基于wxauto库和OneBotV11协议")
    if ASTRBOT_AVAILABLE:
        logger.info("🔌 支持AstrBot插件模式")
    logger.info("="*50)
    
    # 创建应用实例
    app = WxAutoOneBotApp()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)
    
    try:
        # 启动应用
        if app.start():
            logger.info("\n✅ 应用启动成功！")
            logger.info("🌐 访问 http://localhost:10001 进行配置")
            logger.info("⏹️  按 Ctrl+C 停止应用")
            logger.info("\n📋 使用说明:")
            logger.info("  1️⃣  在Web界面中配置监听用户昵称")
            logger.info("  2️⃣  配置反向WebSocket地址")
            logger.info("  3️⃣  启动微信监听和WebSocket连接")
            logger.info("  4️⃣  框架将自动转发消息")
            
            # 保持应用运行
            while app.is_running:
                time.sleep(1)
        else:
            logger.error("❌ 应用启动失败")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n⏹️  用户中断，正在停止应用...")
        app.stop()
    except Exception as e:
        logger.error(f"❌ 应用运行异常: {e}")
        app.stop()
        sys.exit(1)

if __name__ == '__main__':
    main()