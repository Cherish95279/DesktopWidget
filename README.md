# 🖥️ DesktopWidget

> [English](README.md) | [简体中文](README_CN.md)

**DesktopWidget** is a lightweight and customizable Windows desktop widget built with PyQt6, focused on real-time system monitoring and desktop information display.

It integrates system performance monitoring, network monitoring, weather information, calendar information, and theme customization into a simple desktop component.

<p align="center">
  <img src="https://img.shields.io/badge/version-v1.3.1-blue" alt="Version"/>
  <img src="https://img.shields.io/badge/Python-3.12+-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/PyQt6-GUI-green" alt="PyQt6"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/🌍-8%20Languages-blue" alt="Languages"/>
  <img src="https://img.shields.io/badge/简体中文-✅-green" alt="Chinese"/>
  <img src="https://img.shields.io/badge/繁體中文-✅-green" alt="Traditional Chinese"/>
  <img src="https://img.shields.io/badge/English-✅-green" alt="English"/>
  <img src="https://img.shields.io/badge/Español-✅-green" alt="Spanish"/>
  <img src="https://img.shields.io/badge/日本語-✅-green" alt="Japanese"/>
  <img src="https://img.shields.io/badge/Deutsch-✅-green" alt="German"/>
  <img src="https://img.shields.io/badge/Français-✅-green" alt="French"/>
  <img src="https://img.shields.io/badge/한국어-✅-green" alt="Korean"/>
</p>

**Current Version: v1.3.1**

![Preview](screenshots/preview.gif)


---

# ✨ Features

## 🖥️ System Monitoring

- Real-time CPU usage monitoring
- GPU usage monitoring
- Memory usage monitoring
- Network upload/download speed monitoring
- Screen refresh rate display
- IP address display


## 🕐 Date & Time Information

- Analog clock with smooth second hand movement
- Gregorian calendar
- Lunar calendar
- 24 Solar Terms calculation
- Next solar term countdown


## 🌤️ Weather Information

- Real-time weather display
- Global city search
- Multiple weather service support
- Custom API configuration
- Adjustable refresh interval


## 🎨 Customization

- Multiple built-in themes
- Default theme and Bamboo theme
- Custom widget layout
- Background color adjustment
- Transparency control
- Font customization
- Real-time setting changes


## ⚙️ System Features

- System tray support
- Start with Windows
- Automatic update checking
- Remote announcement system
- Feedback through GitHub Discussions


---

# 📷 Screenshots

## Main Interface

### Default Theme

![Default Theme](screenshots/main_default.png)


### Bamboo Theme

![Bamboo Theme](screenshots/main_bamboo.png)


## Settings

### General Settings

![General Settings](screenshots/settings_general.png)


### Widget Settings

![Widget Settings](screenshots/settings_widgets.png)


### Theme Settings

![Theme Settings](screenshots/settings_theme.png)


### Weather Settings

![Weather Settings](screenshots/settings_weather.png)


## Other

### System Tray Menu

![Tray Menu](screenshots/tray_menu.png)


### Update Interface

![Update Interface](screenshots/update.png)


---

# 🚀 Getting Started

## Download Release (Recommended)

Download the latest executable version:

| Platform | Download |
| --- | --- |
| GitHub | [Releases](https://github.com/Cherish95279/DesktopWidget/releases) |
| Gitee | [Releases](https://gitee.com/Cherish95279/DesktopWidget/releases) |


## Run From Source

### Requirements

- Windows 10 / Windows 11
- Python 3.12+


### Install Dependencies

```bash
pip install PyQt6 psutil requests zhdate GPUtil Pillow
Run
python widget.py
🛠️ Technology Stack
Technology	Purpose
Python 3.12	Programming language
PyQt6	GUI framework
psutil	System performance monitoring
GPUtil	GPU monitoring
zhdate	Lunar calendar conversion
requests	Network requests
Pillow	Image processing
PyInstaller	Executable packaging
Inno Setup	Installer creation
📦 Build

Activate virtual environment:

.venv\Scripts\activate

Build executable:

python build.py v1.3.1

The build script automatically handles:

Version update
Old file archive
PyInstaller packaging
Inno Setup installer generation
🌍 Language Support

DesktopWidget supports 8 languages:

Language	Code
简体中文	zh_CN
繁體中文	zh_TW
English	en
Español	es
日本語	ja
Deutsch	de
Français	fr
한국어	ko

Language settings are saved through QSettings.

A restart is required after changing the language.

📄 License

MIT License

🙏 Acknowledgements
Weather data provided by weather service providers
Lunar calendar conversion based on zhdate
Thanks to fkp123 for support
📝 Changelog

See:

CHANGELOG.md