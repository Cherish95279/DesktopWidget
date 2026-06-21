# 🖥️ DesktopWidget - 珍爱桌面小工具

**珍爱桌面小工具** —— 基于 PyQt6 的轻量级桌面组件，集指针时钟、实时天气、性能监控、网速监控于一体，支持系统托盘。

> 版本：v1.1.4

![预览图](https://raw.githubusercontent.com/Cherish95279/DesktopWidget/main/screenshots/preview1.1.4.png)

> 版本：v1.1.3

![预览图](https://raw.githubusercontent.com/Cherish95279/DesktopWidget/main/screenshots/preview1.1.3.png)


---

## ✨ 主要功能

- 🕐 **指针时钟**：模拟石英钟，秒针平滑转动
- 🌤️ **实时天气**：基于高德 API，支持自定义 API 地址和密钥，可设置刷新频率
- 📊 **性能监控**：实时显示 CPU / GPU / 内存占用
- 🌐 **网速监控**：实时显示上行 / 下行速度
- 📅 **农历 + 节气**：显示农历日期，自动计算下一个节气及倒计时
- ⚙️ **自定义设置**：可配置 API 地址、密钥、刷新频率，设置界面友好
- 🖥️ **系统托盘**：支持最小化到托盘，左键单击显示/隐藏窗口，双击恢复窗口
- 🚫 **任务栏隐藏**：程序启动后不占用任务栏位置

---

## 🚀 快速开始

### 方式一：下载安装包（推荐）

1. 访问 [Releases](https://github.com/Cherish95279/DesktopWidget/releases) 页面
2. 下载最新版本的 `widget-v*.exe`
3. 双击运行，无需安装

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
PyInstaller	打包为独立 exe

📦 打包命令

bash

pyinstaller -F -w -i icons/app.ico --collect-all requests --collect-all certifi --hidden-import=requests --hidden-import=urllib3 --hidden-import=certifi --hidden-import=charset_normalizer --hidden-import=idna --add-data "skins;skins" --add-data "icons;icons" widget.py

📄 许可证
MIT License

🙏 致谢
本软件得到了 fqk_123456 的大力支持

天气数据由 高德开放平台 提供

农历转换基于 zhdate

📸 预览图
https://raw.githubusercontent.com/Cherish95279/DesktopWidget/main/screenshots/preview1.1.4.png

text

---

## ✅ 使用说明

1. 在 GitHub 仓库页面点击 **`Add file`** → **`Create new file`**
2. 文件名输入 `README.md`
3. 将上面的内容复制粘贴进去
4. 点击 **`Commit new file`**

完成后，你的仓库首页就会显示更新后的 README，版本号已同步到 v1.1.4，功能列表也补充了托盘图标、任务栏隐藏等新特性。😊

