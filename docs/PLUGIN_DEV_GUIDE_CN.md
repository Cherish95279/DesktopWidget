# DesktopWidget 内容池插件开发指南

本文档面向有 Python / PyQt6 基础、但首次接触本项目的开发者，详细说明如何为
DesktopWidget 的内容池开发自定义插件，并包含一份**从零开发完整插件**的教程。

> 阅读本文档前，建议先阅读 `docs/CONTENT_POOL_DEV_GUIDE_CN.md` 了解内容池的基本
> 架构（8 个槽位、采集→存储→渲染的数据流、content_key 概念）。

---

## 1. 什么是内容池插件

DesktopWidget 的表盘有 8 个固定槽位，每个槽位可以显示一种系统信息（CPU、天气、
网速等）。这些内置的信息项构成了"内容池"。

**内容池插件**允许开发者在不修改主程序代码的情况下，新增自定义信息项。插件以 ZIP
包形式导入，导入后自动出现在设置页面的下拉框中，用户可以将其分配到任意槽位。

插件支持三个显示场景（与内置内容项一致）：

| 场景 | 方法 | 说明 |
|------|------|------|
| 表盘槽位 | `render_short()` | 短文本，1~2 行 |
| 悬停详情 | `render_detail()` | 多行详情，区分 Free / Pro |
| 任务栏信息条 | `render_taskbar()` | 单行紧凑文本（可选） |

---

## 2. 插件包结构

插件以 ZIP 格式分发，解压后的目录结构如下：

```
sunrise_sunset.zip
├── plugin.json              ← 元数据（必须）
├── sunrise_sunset.py        ← 插件主模块（必须）
└── translations/            ← 翻译文件（可选）
    ├── translations_en.ts
    └── translations_ja.ts
```

### 2.1 文件命名规则

- **plugin.json**：文件名固定，必须位于插件根目录或一级子目录
- **主模块 .py**：文件名必须与插件目录名或 `key` 一致。例如目录名为
  `sunrise_sunset`，则主模块可以是 `sunrise_sunset.py`
- **插件目录名**：必须与 `plugin.json` 中的 `key` 字段一致

### 2.2 ZIP 打包方式

打包时需要包含一级子目录，例如：

```bash
# 正确：zip 内含 sunrise_sunset/ 目录
cd plugins_source
zip -r sunrise_sunset.zip sunrise_sunset/

# 错误：直接在根目录打包，没有子目录
cd sunrise_sunset
zip -r ../sunrise_sunset.zip *    # plugin.json 在 zip 根目录，也能识别但不推荐
```

---

## 3. plugin.json 字段说明

```json
{
    "key": "sunrise_sunset",
    "name": "日出日落",
    "description": "显示今日日出日落时间",
    "version": "1.0.0",
    "author": "YourName",
    "min_app_version": "1.6.0",
    "collect_interval": 300,
    "supports_taskbar": true
}
```

| 字段 | 类型 | 必须 | 默认值 | 说明 |
|------|------|:----:|--------|------|
| `key` | str | ✅ | — | 内容池唯一标识，只允许字母、数字、下划线 |
| `name` | str | ❌ | 同 key | 显示名称，出现在下拉框中 |
| `description` | str | ❌ | "" | 简短描述，出现在插件管理列表中 |
| `version` | str | ❌ | "1.0.0" | 版本号 |
| `author` | str | ❌ | "" | 作者名 |
| `min_app_version` | str | ❌ | "" | 最低支持的 App 版本 |
| `collect_interval` | int | ❌ | 300 | 数据采集间隔（秒），最小 5 |
| `supports_taskbar` | bool | ❌ | false | 是否支持任务栏信息条显示 |

> `key` 是贯穿整个系统的主键，一旦发布不要更改，否则用户已保存的槽位配置会失效。

---

## 4. ContentPlugin 标准接口

插件主模块需要定义一个继承 `ContentPlugin` 的类：

```python
from plugin_manager import ContentPlugin


class SunriseSunsetPlugin(ContentPlugin):
    """日出日落插件"""

    def collect(self, context):
        """数据采集，返回 dict"""
        # context 提供 settings、now 等访问能力
        # 这里计算日出日落时间
        return {
            "sunrise": "06:12",
            "sunset": "18:45",
            "day_length": "12小时33分"
        }

    def render_short(self, data, i18n):
        """表盘槽位短文本"""
        # 返回 str 为单行，返回 list 为多行
        return [f"🌅 {data['sunrise']}", f"🌇 {data['sunset']}"]

    def render_detail(self, data, is_pro, i18n):
        """悬停详情多行文本"""
        lines = [
            f"日出：{data['sunrise']}",
            f"日落：{data['sunset']}",
        ]
        if is_pro:
            lines.append(f"昼长：{data['day_length']}")
        return lines

    def render_taskbar(self, data, i18n):
        """任务栏文本（supports_taskbar=True 时调用）"""
        return f"🌅{data['sunrise']}"
```

### 4.1 方法说明

#### collect(context) → dict

数据采集方法。PluginManager 会按 `collect_interval` 定时调用。

- **context**：`PluginContext` 实例，提供以下能力：
  - `context.settings` — QSettings 实例，读取用户配置
  - `context.now` — 当前 datetime 对象
  - `context.get_setting(key, default, type)` — 便捷读取设置值
- **返回值**：dict，任意结构，会作为 `data` 参数传给 render 方法
- **异常处理**：方法内抛出的异常会被 PluginManager 捕获，连续失败 5 次后插件
  会被自动禁用

#### render_short(data, i18n) → str | list

表盘槽位短文本。空间有限（约 60~105px 宽，43~50px 高），建议不超过 2 行。

- **data**：`collect()` 返回的 dict
- **i18n**：国际化文本字典（与 MainWindow._i18n 相同结构）
- **返回值**：
  - `str`：单行文本
  - `list[str]`：多行文本，每个元素一行

#### render_detail(data, is_pro, i18n) → list[str]

悬停详情。鼠标悬停在槽位上时弹出的浮动面板，空间充裕，可显示多行。

- **is_pro**：bool，是否为 Pro 用户。建议为 Pro 用户提供更多详情
- **返回值**：`list[str]`，每行一个字符串

#### render_taskbar(data, i18n) → str

任务栏信息条文本。仅在 `supports_taskbar: true` 时调用。

- 任务栏高度仅 28px，文本要尽量简短
- **返回值**：str，单行文本

### 4.2 i18n 字典说明

`i18n` 参数是 MainWindow 的国际化文本字典，包含常用界面文本。插件可以用它做
简单的国际化，也可以在插件内部自行处理多语言。

常见可用键（取决于当前语言）：
```python
i18n.get("memory", "内存")    # "内存" / "Memory" / "メモリ" ...
i18n.get("week", "星期")      # "星期" / "Day" ...
```

> 如果插件需要自己的翻译文本，建议在 `collect()` 中根据 `context.settings`
> 读取当前语言，在返回的 data dict 中携带翻译后的文本。

---

## 5. PluginContext 详解

`PluginContext` 是插件访问用户配置和基础能力的唯一入口。插件**不应**直接访问
MainWindow 实例。

```python
def collect(self, context):
    # 读取用户设置的语言
    lang = context.get_setting("language", "zh_CN")

    # 读取用户选择的位置（天气相关）
    city = context.get_setting("selected_city", "")

    # 获取当前时间
    now = context.now

    # 直接访问 QSettings
    all_keys = context.settings.allKeys()

    return {...}
```

### 5.1 可访问的设置项

以下是常用的 QSettings 键（组织名 `MyDesktopApp`，应用名 `WeatherSettings`）：

| 键 | 类型 | 说明 |
|----|------|------|
| `language` | str | 当前语言代码（zh_CN / zh_TW / en / ja / ko / de / fr / es） |
| `selected_province` | str | 用户选择的省份 |
| `selected_city` | str | 用户选择的城市 |
| `selected_county` | str | 用户选择的区县 |
| `font_color` | str | 字体颜色（如 "#1c344d"） |
| `font_family` | str | 字体（如 "Microsoft YaHei"） |
| `font_size` | int | 字号 |
| `hover_enabled` | bool | 悬停详情是否开启 |
| `theme_color` | str | 主题背景颜色 |

---

## 6. 从零开发一个插件：完整教程

本节以**日出日落时间**插件为例，演示从创建到导入的完整流程。

### 6.1 创建项目目录

```
plugins_source/
└── sunrise_sunset/
    ├── plugin.json
    └── sunrise_sunset.py
```

### 6.2 编写 plugin.json

```json
{
    "key": "sunrise_sunset",
    "name": "日出日落",
    "description": "显示今日日出日落时间",
    "version": "1.0.0",
    "author": "DesktopWidget Team",
    "collect_interval": 3600,
    "supports_taskbar": true
}
```

> 采集间隔设为 3600 秒（1 小时），日出日落时间一天内基本不变。

### 6.3 编写 sunrise_sunset.py

```python
# -*- coding: utf-8 -*-
"""日出日落插件 - 显示今日日出日落时间"""

import math
from datetime import datetime, timedelta
from plugin_manager import ContentPlugin


class SunriseSunsetPlugin(ContentPlugin):
    """日出日落插件"""

    def collect(self, context):
        """计算今日日出日落时间"""
        now = context.now
        lat, lon = self._get_location(context)

        sunrise, sunset = self._calc_sunrise_sunset(
            now.year, now.month, now.day, lat, lon)

        day_length = sunset - sunrise
        hours = int(day_length.total_seconds() // 3600)
        minutes = int((day_length.total_seconds() % 3600) // 60)

        return {
            "sunrise": sunrise.strftime("%H:%M"),
            "sunset": sunset.strftime("%H:%M"),
            "day_length": f"{hours}小时{minutes}分",
            "date": now.strftime("%Y/%m/%d"),
        }

    def render_short(self, data, i18n):
        """表盘显示：两行"""
        return [f"🌅 {data['sunrise']}", f"🌇 {data['sunset']}"]

    def render_detail(self, data, is_pro, i18n):
        """悬停详情"""
        lines = [
            f"日期：{data['date']}",
            f"日出：{data['sunrise']}",
            f"日落：{data['sunset']}",
        ]
        if is_pro:
            lines.append(f"昼长：{data['day_length']}")
        return lines

    def render_taskbar(self, data, i18n):
        """任务栏：单行"""
        return f"🌅{data['sunrise']} 🌇{data['sunset']}"

    # ---------- 内部方法 ----------

    def _get_location(self, context):
        """从用户设置获取经纬度，默认北京"""
        # 可根据用户选择的城市查找经纬度
        # 这里用默认值，实际开发可接入区域数据
        return 39.9042, 116.4074  # 北京

    def _calc_sunrise_sunset(self, year, month, day, lat, lon):
        """简化的日出日落计算（基于天文公式）"""
        n = datetime(year, month, day).timetuple().tm_yday

        # 太阳赤纬
        decl = 23.45 * math.sin(math.radians(360 * (284 + n) / 365))

        # 时角
        lat_rad = math.radians(lat)
        decl_rad = math.radians(decl)
        cos_omega = -math.tan(lat_rad) * math.tan(decl_rad)

        # 极昼/极夜处理
        if cos_omega > 1:
            return None, None  # 极夜
        if cos_omega < -1:
            return None, None  # 极昼

        omega = math.degrees(math.acos(cos_omega))

        # 日出日落时间（UTC，粗略）
        sunrise_utc = 12 - omega / 15 - lon / 15
        sunset_utc = 12 + omega / 15 - lon / 15

        # 转为北京时间（UTC+8）
        tz_offset = 8
        sunrise_hour = (sunrise_utc + tz_offset) % 24
        sunset_hour = (sunset_utc + tz_offset) % 24

        sunrise = self._hour_to_datetime(year, month, day, sunrise_hour)
        sunset = self._hour_to_datetime(year, month, day, sunset_hour)

        return sunrise, sunset

    def _hour_to_datetime(self, year, month, day, hour_float):
        """将小时浮点数转为 datetime"""
        h = int(hour_float)
        m = int((hour_float - h) * 60)
        s = int(((hour_float - h) * 60 - m) * 60)
        return datetime(year, month, day, h, m, s)
```

### 6.4 打包 ZIP

```bash
cd plugins_source
zip -r sunrise_sunset.zip sunrise_sunset/
```

ZIP 内部结构应为：
```
sunrise_sunset.zip
└── sunrise_sunset/
    ├── plugin.json
    └── sunrise_sunset.py
```

### 6.5 导入测试

1. 启动 DesktopWidget
2. 打开「设置 → 显示项目」
3. 点击「管理插件」按钮
4. 在对话框上半部分点击「浏览...」，选择 `sunrise_sunset.zip`
5. 查看校验结果，如果有安全警告请确认用途后继续
6. 点击「导入」
7. 导入成功后，下方列表出现「日出日落」插件
8. 关闭对话框，在 8 个槽位下拉框中选择「日出日落」
9. 确认表盘显示日出日落时间
10. 鼠标悬停确认详情面板
11. 在任务栏下拉框中选择「日出日落」，确认任务栏显示

---

## 7. 导入校验流程

导入插件时，PluginManager 会执行以下校验：

1. **解压 ZIP** — 验证是否为有效的 ZIP 文件
2. **查找 plugin.json** — 在根目录或一级子目录中查找
3. **校验 JSON 格式** — 必须包含有效的 `key` 字段
4. **校验 key 合法性** — 只允许字母、数字、下划线
5. **查找主模块** — 目录名.py 或 key.py 必须存在
6. **静态安全扫描** — 扫描危险代码模式（见第 8 节）
7. **模块加载测试** — 尝试 import 模块，检查是否定义了 ContentPlugin 子类

校验通过后点击「导入」才会将插件复制到插件目录。

---

## 8. 安全说明

### 8.1 静态扫描

导入时会扫描插件源码中的以下危险模式：

| 检测项 | 说明 |
|--------|------|
| `os.system` / `os.popen` | 系统命令执行 |
| `subprocess.Popen` / `run` / `call` | 子进程执行 |
| `eval(` / `exec(` | 动态代码执行 |
| `__import__` | 动态导入 |
| `ctypes.CDLL` / `WinDLL` / `windll` | DLL 加载 |
| `os.remove` / `shutil.rmtree` | 文件/目录删除 |
| `open(` | 文件操作 |
| `socket.socket` | 原始网络通信 |

> 检测到危险模式时会显示**警告**，但**不会阻止导入**。
> 个人自用插件由用户自行负责。

### 8.2 错误隔离

- 插件的所有方法调用都包裹在 `try/except` 中
- 插件崩溃不会影响主程序和其他插件
- 连续采集失败 5 次后，插件会被**自动禁用**
- 禁用后槽位显示为空，不影响其他槽位

### 8.3 共享仓库审核

如果你计划将插件发布到官方共享仓库，需要经过人工审核：
- 提交插件源码供静态扫描和行为分析
- 审核通过后才会发布到仓库
- 上架仓库的插件在导入时显示 ✅ 已验证标记

---

## 9. 插件存储位置

插件安装后存放在用户数据目录：

```
%LOCALAPPDATA%\MyDesktopApp\DesktopWidget\plugins\
    sunrise_sunset\
        plugin.json
        sunrise_sunset.py
    battery_plus\
        plugin.json
        battery_plus.py
```

- 与用户主题目录（`skins/`）同级
- MSIX 商店版和 exe 版共用同一目录
- 删除插件即删除对应子目录

---

## 10. 附录

### 10.1 ContentPlugin 方法速查

| 方法 | 调用时机 | 参数 | 返回值 | 必须 |
|------|----------|------|--------|:----:|
| `collect(context)` | 定时采集 | PluginContext | dict | ✅ |
| `render_short(data, i18n)` | 表盘重绘 | dict, dict | str 或 list[str] | ✅ |
| `render_detail(data, is_pro, i18n)` | 鼠标悬停 | dict, bool, dict | list[str] | ✅ |
| `render_taskbar(data, i18n)` | 任务栏刷新 | dict, dict | str | ⬜ |

### 10.2 调试技巧

- 在 `collect()` 中使用 `print()` 输出调试信息，会在控制台显示
- 如果插件不显示，检查「管理插件」列表中插件是否存在、是否被禁用
- 如果槽位为空，检查 `render_short()` 是否返回了空字符串
- 如果悬停无详情，检查 `render_detail()` 是否返回了空列表

### 10.3 常见问题

**Q: 插件 key 能不能改？**
A: 不能。key 是用户保存槽位配置的依据，改了之后用户已保存的配置会失效。

**Q: 插件能用 requests 访问网络吗？**
A: 可以。插件运行在主进程中，可以 import 任何已安装的第三方库。但网络请求应该放在
`collect()` 中（后台定时调用），不要放在 `render_*()` 中（会被频繁调用）。

**Q: 插件能访问 MainWindow 实例吗？**
A: 不能直接访问。通过 `PluginContext` 获取用户配置和基础能力。如果需要更多数据，
建议在 `plugin.json` 中声明，未来版本会扩展 Context 能力。

**Q: 一个 ZIP 能包含多个插件吗？**
A: 不能。每个 ZIP 对应一个插件。多个插件分别打包、分别导入。

---

> 本文档基于 DesktopWidget v1.6.0 代码编写。如有疑问，请参考源码或联系项目维护者。
