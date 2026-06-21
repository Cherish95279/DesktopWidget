# 🖥️ DesktopWidget

**桌面小工具** —— 基于 PyQt6 的轻量级桌面组件，集指针时钟、实时天气、性能监控、网速监控于一体。

![预览图](https://raw.githubusercontent.com/Cherish95279/DesktopWidget/main/screenshots/preview.png)

---

## ✨ 主要功能

- 🕐 **指针时钟**：模拟石英钟，秒针平滑转动，支持窗口拉伸
- 🌤️ **实时天气**：基于高德 API，支持自定义 API 地址和密钥，可设置刷新频率
- 📊 **性能监控**：实时显示 CPU / GPU / 内存占用
- 🌐 **网速监控**：实时显示上行 / 下行速度
- 📅 **农历 + 节气**：显示农历日期，自动计算下一个节气及倒计时
- ⚙️ **自定义设置**：可配置 API 地址、密钥、刷新频率，设置界面友好

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
Python 3.12

PyQt6 —— GUI 框架

psutil —— 系统性能监控

requests —— 网络请求

zhdate —— 农历转换

GPUtil —— GPU 监控

PyInstaller —— 打包为独立 exe

pyinstaller -F -w --collect-all requests --collect-all certifi --hidden-import=requests --hidden-import=urllib3 --hidden-import=certifi --hidden-import=charset_normalizer --hidden-import=idna --add-data "bg.png;." --add-data "Hour_Hand.png;." --add-data "Minute_Hand.png;." --add-data "Second_Hand.png;." widget.py

📄 许可证
MIT License

🙏 致谢

本软件得到了<fqk_123456>的大力支持

天气数据由 高德开放平台 提供

农历转换基于 zhdate


---

## 📸 需要准备一张预览图

模板里引用了一张预览图，你需要在本地准备：

1. 把你的桌面小工具界面截图保存为 `preview.png`（建议放在 `screenshots/` 文件夹中）
2. 提交到 GitHub：

```bash
mkdir screenshots
# 把截图放到 screenshots/preview.png
git add screenshots/preview.png
git commit -m "docs: 添加预览截图"
git push

如果你不想用 screenshots/ 文件夹，也可以直接把预览图放在根目录，然后把链接改为：

https://raw.githubusercontent.com/Cherish95279/DesktopWidget/main/preview.png

✅ 使用方式
在 GitHub 仓库页面点击 Add file → Create new file

文件名输入 README.md

复制上面的模板内容粘贴进去

点击 Commit new file