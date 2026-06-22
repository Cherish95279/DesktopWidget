# 🖥️ DesktopWidget - 珍爱桌面小工具

**珍爱桌面小工具** —— 基于 PyQt6 的轻量级桌面组件，集指针时钟、实时天气、性能监控、网速监控于一体，支持系统托盘和自动更新。

> 当前版本：v1.1.8

![预览图](https://raw.githubusercontent.com/Cherish95279/DesktopWidget/main/screenshots/preview1.1.8.png)

---

## ✨ 主要功能

- 🕐 **指针时钟**：模拟石英钟，秒针平滑转动
- 🌤️ **实时天气**：支持高德 API，可自定义 API 地址和密钥，可设置刷新频率
- 📊 **性能监控**：实时显示 CPU / GPU / 内存占用
- 🌐 **网速监控**：实时显示上行 / 下行速度
- 📅 **农历 + 节气**：显示农历日期，自动计算下一个节气及倒计时
- ⚙️ **自定义设置**：可配置 API 地址、密钥、刷新频率，设置界面友好
- 🖥️ **系统托盘**：支持最小化到托盘，左键单击显示/隐藏窗口，双击恢复窗口
- 🔄 **自动更新**：启动时自动检测新版本，支持一键下载安装
- 🚀 **开机自启动**：支持设置开机自动运行
- 🗺️ **地区选择**：支持手动选择省/市/县，天气跟随地区切换

---

## 🚀 快速开始

### 方式一：下载安装包（推荐）

1. 访问 [Releases](https://github.com/Cherish95279/DesktopWidget/releases) 页面
2. 下载最新版本的 `DesktopWidget-v*.exe`
3. 双击运行安装，首次安装后桌面会生成快捷方式
4. 后续双击桌面图标即可启动

### 方式二：从源码运行

```bash
# 克隆仓库
git clone https://github.com/Cherish95279/DesktopWidget.git
cd DesktopWidget

# 安装依赖
pip install PyQt6 psutil requests zhdate GPUtil

# 运行
python widget.py

🛠️ 技术栈
技术	用途
Python 3.12	编程语言
PyQt6	GUI 框架
psutil	系统性能监控
requests	网络请求
zhdate	农历转换
GPUtil	GPU 监控
Inno Setup	安装包制作
PyInstaller	打包为独立 exe
📦 打包命令
bash
pyinstaller -D -w -n DesktopWidget -i icons/app.ico --collect-all requests --collect-all certifi --hidden-import=requests --hidden-import=urllib3 --hidden-import=certifi --hidden-import=charset_normalizer --hidden-import=idna --add-data "skins;skins" --add-data "icons;icons" widget.py
📄 许可证
MIT License

🙏 致谢
本软件得到了 fqk_123456 的大力支持

天气数据由 高德开放平台 提供

农历转换基于 zhdate

📸 预览图
https://raw.githubusercontent.com/Cherish95279/DesktopWidget/main/screenshots/preview1.1.8.png

text

---

## 📤 第二步：提交 README.md 到 GitHub

在项目根目录打开 Git Bash 或终端，执行：

```bash
git add README.md
git commit -m "docs: 更新README到v1.1.8"
git push
📦 第三步：创建 Release 并上传 exe
1. 进入 Releases 页面
打开 https://github.com/Cherish95279/DesktopWidget，点击 Releases。

2. 创建新 Release
点击 Draft a new release。

3. 填写信息
字段	填写内容
Tag version	v1.1.8
Release title	珍爱桌面小工具 v1.1.8
Describe this release	填写更新日志（见下方模板）
4. 上传安装包
在 Attach binaries 区域，将 D:\PythonProjects\DesktopWidget\dist\DesktopWidget-v1.1.8-win64-Cherish-Setup.exe 拖拽进去。

5. 发布
点击 Publish release 按钮。

📋 Release Notes 模板（直接复制）
markdown
## ✨ 新增功能
- **自动更新通道**：程序启动 3 秒后自动检测新版本，支持一键下载安装
- **系统托盘**：支持最小化到托盘，左键单击显示/隐藏窗口，双击恢复窗口
- **开机自启动**：支持设置开机自动运行，默认开启
- **地区选择**：支持手动选择省/市/县，天气跟随地区切换
- **设置对话框重构**：新增常规设置、天气设置、主题、检查更新、关于五个页面
- **检查更新页面**：显示当前版本、最新版本、下载进度，支持一键安装

## 🔧 优化改进
- 版本号升级至 v1.1.8
- 修复更新后程序卡死的问题
- 修复天气地区切换后显示不正确的问题
- 优化打包流程，改用 Inno Setup 制作安装包
- 修复退出程序时误弹托盘提示的问题
- 修复设置对话框初始页面重叠问题
- 修复打包后闪黑框问题

## 📦 下载
请下载 `DesktopWidget-v1.1.8-win64-Cherish-Setup.exe` 并运行安装。
✅ 完成
README.md 已更新

代码已提交到 GitHub

安装包已上传到 Releases

现在用户可以通过 https://github.com/Cherish95279/DesktopWidget/releases 下载 v1.1.8 版本了。😊


