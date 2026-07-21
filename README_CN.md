# 🖥️ DesktopWidget（珍爱桌面小工具）

> [English](README.md) | [简体中文](README_CN.md)

**DesktopWidget（珍爱桌面小工具）** 是一个基于 PyQt6 开发的轻量级 Windows 桌面组件，专注于实时系统监控和桌面信息展示。

集成系统性能监控、网络监控、天气信息、日期信息以及主题自定义功能，为桌面提供简洁直观的信息展示。


<p align="center">
  <img src="https://img.shields.io/badge/版本-v1.3.1-blue" alt="Version"/>
  <img src="https://img.shields.io/badge/Python-3.12+-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/PyQt6-GUI-green" alt="PyQt6"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
</p>


<p align="center">
  <img src="https://img.shields.io/badge/🌍-支持8种语言-blue" alt="Languages"/>
  <img src="https://img.shields.io/badge/简体中文-✅-green"/>
  <img src="https://img.shields.io/badge/繁體中文-✅-green"/>
  <img src="https://img.shields.io/badge/English-✅-green"/>
  <img src="https://img.shields.io/badge/Español-✅-green"/>
  <img src="https://img.shields.io/badge/日本語-✅-green"/>
  <img src="https://img.shields.io/badge/Deutsch-✅-green"/>
  <img src="https://img.shields.io/badge/Français-✅-green"/>
  <img src="https://img.shields.io/badge/한국어-✅-green"/>
</p>


**当前版本：v1.3.1**

![预览图](screenshots/preview.gif)


---

# ✨ 主要功能


## 🖥️ 系统监控

- 实时 CPU 占用率监控
- GPU 使用率监控
- 内存占用监控
- 网络上传/下载速度监控
- 屏幕刷新率显示
- IP 地址显示


## 🕐 时间日期信息

- 指针时钟，秒针平滑转动
- 公历日期显示
- 农历日期显示
- 二十四节气计算
- 下一个节气倒计时


## 🌤️ 天气信息

- 实时天气显示
- 全球城市搜索
- 多天气服务支持
- 自定义 API 配置
- 可调整刷新频率


## 🎨 个性化设置

- 多主题支持
- 默认主题与竹林主题
- 信息槽位自由排列
- 背景颜色调整
- 窗口透明度控制
- 字体自定义
- 设置实时生效


## ⚙️ 系统功能

- 系统托盘支持
- 开机自动启动
- 自动更新检测
- 远程公告系统
- GitHub Discussions 反馈渠道


---

# 📷 预览截图


## 主界面


### 默认主题

![默认主题](screenshots/main_default.png)


### 竹林主题

![竹林主题](screenshots/main_bamboo.png)


## 设置界面


### 常规设置

![常规设置](screenshots/settings_general.png)


### 显示项目设置

![显示项目设置](screenshots/settings_widgets.png)


### 主题设置

![主题设置](screenshots/settings_theme.png)


### 天气设置

![天气设置](screenshots/settings_weather.png)


## 其他


### 系统托盘菜单

![托盘菜单](screenshots/tray_menu.png)


### 更新界面

![更新界面](screenshots/update.png)



---

# 🚀 快速开始


## 下载安装包（推荐）


下载最新版本：

| 平台 | 下载地址 |
| --- | --- |
| GitHub | [Releases](https://github.com/Cherish95279/DesktopWidget/releases) |
| Gitee | [Releases](https://gitee.com/Cherish95279/DesktopWidget/releases) |



## 从源码运行


### 环境要求

- Windows 10 / Windows 11
- Python 3.12+


### 安装依赖

```bash
pip install PyQt6 psutil requests zhdate GPUtil Pillow
运行
python widget.py
🛠️ 技术栈
技术	用途
Python 3.12	编程语言
PyQt6	GUI 框架
psutil	系统性能监控
GPUtil	GPU 监控
zhdate	农历转换
requests	网络请求
Pillow	图像处理
PyInstaller	EXE 打包
Inno Setup	安装程序制作
📦 一键打包

激活虚拟环境：

.venv\Scripts\activate

执行：

python build.py v1.3.1

脚本自动完成：

版本号更新
旧文件归档
PyInstaller 打包
Inno Setup 安装程序生成
🌍 多语言支持

DesktopWidget 支持 8 种语言：

语言	代码
简体中文	zh_CN
繁體中文	zh_TW
English	en
Español	es
日本語	ja
Deutsch	de
Français	fr
한국어	ko

语言设置保存在 QSettings 中。

切换语言后需要重启程序生效。

📄 许可证

MIT License

🙏 致谢
天气数据由相关天气服务提供
农历转换基于 zhdate
感谢 fkp123 的支持
📝 更新日志

详见：

CHANGELOG.md