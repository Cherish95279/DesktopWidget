# 🖥️ DesktopWidget - 珍爱桌面小工具

**珍爱桌面小工具** —— 基于 PyQt6 的轻量级桌面组件，集指针时钟、实时天气、性能监控、网速监控于一体，支持系统托盘和自动更新。

> 当前版本：v1.2.0

![预览图](https://raw.githubusercontent.com/Cherish95279/DesktopWidget/main/screenshots/preview1.2.0.png)

---

## ✨ 主要功能

- 🕐 **指针时钟**：模拟石英钟，秒针平滑转动
- 🌤️ **实时天气**：支持高德 API，可自定义 API 地址和密钥，可设置刷新频率
- 📊 **性能监控**：实时显示 CPU / GPU / 内存占用
- 🌐 **网速监控**：实时显示上行 / 下行速度
- 📅 **农历 + 节气**：显示农历日期，自动计算下一个节气及倒计时
- ⚙️ **自定义布局**：8 个信息槽位自由排列，下拉菜单实时生效，无需保存
- 🖥️ **系统托盘**：支持最小化到托盘，左键单击显示/隐藏窗口，双击恢复窗口
- 🔄 **自动更新**：启动时自动检测新版本，支持一键下载安装
- 🚀 **开机自启动**：支持设置开机自动运行
- 🗺️ **地区选择**：支持手动选择省/市/县，天气跟随地区切换
- 🎨 **字体自定义**：支持自定义主窗口字体、字号、文字颜色，实时生效
- 💖 **捐赠支持**：支付宝 / 微信扫码捐赠，感谢您的支持！
- 🔑 **GitHub Token**：支持用户自行填写 Token，提升更新检查频率至 5000 次/小时

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
pip install PyQt6 psutil requests zhdate GPUtil astral

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
astral	日出日落计算
Inno Setup	安装包制作
PyInstaller	打包为独立 exe
📦 一键打包
bash
# 激活虚拟环境
.venv\Scripts\activate

# 执行打包（指定版本号）
python build.py v1.2.0
脚本自动完成：版本号更新 → 旧文件归档 → PyInstaller 打包 → Inno Setup 编译

📄 许可证
MIT License

🙏 致谢
感谢 fqk_123456 的大力支持

天气数据由 高德开放平台 提供

农历转换基于 zhdate

日出日落计算基于 astral

📸 预览图
https://raw.githubusercontent.com/Cherish95279/DesktopWidget/main/screenshots/preview1.2.0.png

📝 更新日志
v1.2.0 (2026-06-24)
重构显示项目布局，8 个信息槽位自由排列

下拉菜单实时生效，取消保存按钮

新增捐赠页面（支付宝 / 微信扫码）

修复 CPU、GPU、分辨率、刷新率显示位置错乱

修复日出日落显示为两行

调整左一/右一高度为两行显示

优化主窗口绘制逻辑，提升显示准确性

v1.1.9
新增日出日落功能

优化天气线程缓存机制

修复已知问题

text

---

## 📌 同时需要做的

1. **准备新预览图**：运行程序，截图主窗口，命名为 `preview1.2.0.png`，放到 `screenshots/` 目录并提交。
2. **提交 README**：
   ```bash
   git add README.md screenshots/preview1.2.0.png
   git commit -m "docs: 更新README到v1.2.0"
   git push