# 安装说明

## 系统要求

- Windows 操作系统
- Python 3.8+
- 微信PC版（已登录）

## 依赖安装

```bash
pip install -r requirements.txt
```

## 独立应用模式安装

1. 克隆或下载项目到本地
2. 安装依赖包
3. 运行 `python main.py` 启动应用
4. 访问 http://localhost:10001 进行配置

## AstrBot插件模式安装

### 方法一：通过AstrBot插件管理器（推荐）

1. 在AstrBot管理界面中，进入插件管理
2. 搜索「微信消息转发框架」或「wxauto_repost」
3. 点击安装并启用插件
4. 插件启动后访问 http://localhost:10001 进行配置

### 方法二：手动安装

1. 将整个项目文件夹复制到AstrBot的插件目录：
   ```
   AstrBot安装目录/plugins/wxauto_repost/
   ```

2. 确保插件目录结构如下：
   ```
   plugins/
   └── wxauto_repost/
       ├── main.py          # 插件入口文件
       ├── metadata.yaml    # 插件元数据
       ├── requirements.txt # 依赖列表
       ├── config/         # 配置目录
       ├── src/            # 源代码目录
       └── ...
   ```

3. 重启AstrBot或在插件管理界面中刷新插件列表

4. 启用「微信消息转发框架」插件

## 配置说明

### 首次使用配置

1. 确保微信PC版已登录且窗口可见
2. 访问Web配置界面：http://localhost:10001
3. 在「微信配置」中添加要监听的用户昵称
4. 在「WebSocket配置」中设置后端服务地址
5. 启用相应的功能模块
6. 点击「启动服务」开始消息转发

### 配置文件位置

- 独立模式：`config/config.json`
- 插件模式：`plugins/wxauto_repost/config/config.json`

## 常见问题

### Q: 提示"未找到微信窗口"
A: 请确保微信PC版已启动并登录，且窗口未被最小化或遮挡

### Q: WebSocket连接失败
A: 检查后端服务是否正常运行，确认WebSocket地址配置正确

### Q: 插件无法加载
A: 检查AstrBot版本是否满足要求（>=3.0.0），确认插件文件完整

### Q: 消息发送失败
A: 确认目标用户昵称正确，检查微信是否有该联系人

## 技术支持

如遇到问题，请提供以下信息：
- 操作系统版本
- Python版本
- AstrBot版本（如使用插件模式）
- 错误日志信息
- 配置文件内容（隐私信息请脱敏）