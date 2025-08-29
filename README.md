# 微信消息转发到OneBotV11协议框架

基于wxauto库和OneBotV11协议的微信消息转发框架，支持通过WebUI进行配置管理。

**🔌 支持两种使用方式：**
- **独立应用模式**：直接运行使用
- **AstrBot插件模式**：作为AstrBot插件集成使用

## 功能特性

- 🌐 **WebUI配置界面** - 友好的Web界面进行配置操作
- 💾 **本地配置存储** - 所有配置保存到本地文件，支持长期存储
- 👥 **微信消息监听** - 监听指定用户的微信消息
- 🔄 **OneBotV11协议转换** - 将微信消息转换为OneBotV11格式
- 🌐 **反向WebSocket通信** - 通过反向WS与后端服务通信
- 📨 **消息回复处理** - 解析后端回复并发送给微信用户
- 🎯 **多媒体支持** - 支持文字、图片、文件等多种消息类型

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 方式一：独立应用模式

1. 启动程序：
```bash
python main.py
```

2. 打开浏览器访问WebUI界面：
```
http://localhost:10001
```

3. 在WebUI中进行配置：
   - 设置要监听的微信用户昵称
   - 配置反向WebSocket地址
   - 启用相关功能模块

### 方式二：AstrBot插件模式

1. 将整个项目文件夹复制到AstrBot的插件目录中

2. 在AstrBot管理界面中启用「微信消息转发框架」插件

3. 插件启动后，访问WebUI界面进行配置：
```
http://localhost:10001
```
(注意：需要自行在astrbot的webui新建一个消息平台并选择aiocqhttp协议)
4. 配置步骤与独立模式相同

**注意**：
- 插件模式下，框架会在AstrBot启动时自动加载，无需手动运行main.py
- 插件采用非阻塞设计，不会影响AstrBot的正常业务运行
- 所有组件（WebSocket、微信监听、Web UI）都在独立线程中运行

## 配置说明

### 微信配置
- `监听用户昵称`: 要监听消息的微信用户昵称列表
- `启用微信监听`: 是否启用微信消息监听功能

### OneBotV11配置
- `反向WebSocket地址`: 后端服务的WebSocket地址
- `启用OneBot客户端`: 是否启用OneBot协议通信

### WebUI配置
- `端口`: WebUI服务端口，默认10001

## 项目结构

```
wxauto_repost_onebotv11/
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖包列表
├── README.md              # 项目说明
├── config/                # 配置文件目录
│   └── config.json        # 主配置文件
├── src/                   # 源代码目录
│   ├── __init__.py
│   ├── config_manager.py  # 配置管理模块
│   ├── wechat_monitor.py  # 微信监听模块
│   ├── onebot_client.py   # OneBotV11客户端
│   ├── message_handler.py # 消息处理模块
│   └── web_ui.py         # WebUI模块
└── static/               # 静态文件目录
    ├── css/
    ├── js/
    └── templates/
```

## 注意事项

1. 首次使用需要确保微信PC版已登录
2. 建议在稳定的网络环境下使用
3. 配置文件会自动保存，无需手动备份
4. 如遇到问题，请检查日志输出

## 许可证

MIT License