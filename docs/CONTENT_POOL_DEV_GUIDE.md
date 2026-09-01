# DesktopWidget 内容池开发指南

本文档面向有 Python / PyQt6 基础、但首次接触本项目的协作开发者，详细说明"内容池"
（Content Pool）的架构设计与数据流，并提供一份**从零添加新内容项**的完整分步教程。

> 阅读本文档前，建议先快速浏览 `docs/THEME_DEV_GUIDE.md` 了解画布尺寸与图层概念，
> 因为内容池的文字信息最终绘制在主题表盘的上层。

---

## 1. 什么是内容池

DesktopWidget 的主界面是一个 400×297 像素的时钟表盘，表盘四周有 **8 个固定槽位**
（slot_1 ~ slot_8），每个槽位可以显示一种系统信息（CPU、天气、网速等）。

**"内容池"就是这 8 个槽位可选的所有信息类型的注册表。**

用户在「设置 → 显示」页面中，通过 8 个下拉框为每个槽位选择一种内容；选中的内容会
实时绘制到表盘上。鼠标悬停在某个槽位上时，还会弹出一个详细信息面板。此外，任务栏
信息条也有一个精简版的内容池子集。

### 1.1 三个显示场景

同一个内容项可能出现在三个不同的显示场景中，每个场景的渲染逻辑是独立的：

| 场景 | 位置 | 渲染文件 | 特点 |
|------|------|----------|------|
| **表盘槽位** | 表盘四周 8 个固定坐标 | `src/main_window_parts/painter.py` | 短文本，空间有限 |
| **悬停详情** | 鼠标悬停时弹出的浮动面板 | `src/widgets/detail_popup.py` | 多行详情，区分 Free / Pro |
| **任务栏信息条** | Windows 任务栏通知区域 | `src/taskbar_widget.py` | 单条紧凑文本 |

> 这三个场景的渲染逻辑**各自独立**，新增内容项时需要逐一适配，否则会出现"设置里能选
> 但显示不出来"或"悬停没详情"的残缺状态。

---

## 2. 架构总览与数据流

内容池的数据流分为 **采集 → 存储 → 渲染** 三个阶段，涉及 6 个文件。下图展示了一个
内容项（以 `cpu` 为例）从系统数据到最终显示的完整路径：

```
 ┌─────────────────────────────────────────────────────────────────────┐
 │                        数据采集阶段                                  │
 │                                                                     │
 │  src/main_window_parts/perf.py  (PerfMixin)                         │
 │  ├── update_perf()        → self.cpu = psutil.cpu_percent()         │
 │  ├── update_clock()       → self.now / self.lunar_text / ...        │
 │  ├── on_speed_update()    → self.down_speed / self.up_speed         │
 │  └── _update_disk_usage() → self.disk_usage = {...}                 │
 │                                                                     │
 │  src/main_window_parts/weather.py (WeatherMixin)                    │
 │  └── start_weather_thread() → self.weather = {city, temp, ...}      │
 │                                                                     │
 │  src/main_window.py  (MainWindow.__init__)                          │
 │  └── 初始化所有数据属性: self.cpu = 0, self.gpu = 0, ...             │
 └──────────────────────────────┬──────────────────────────────────────┘
                                │
                                │  数据存储为 MainWindow 实例属性
                                │  (self.cpu, self.weather, self.disk_usage ...)
                                │
 ┌──────────────────────────────▼──────────────────────────────────────┐
 │                        持久化与配置阶段                               │
 │                                                                     │
 │  QSettings("MyDesktopApp", "WeatherSettings")                       │
 │  ├── slot_1 = "weather"    (表盘槽位 1 的内容 key)                    │
 │  ├── slot_2 = "netspeed"                                          │
 │  ├── ...                                                           │
 │  ├── slot_8 = "disk_total"                                        │
 │  ├── taskbar_display = "netspeed"  (任务栏信息条内容 key)            │
 │  └── hover_enabled = True   (悬停详情开关)                          │
 │                                                                     │
 │  src/constants.py                                                   │
 │  └── DEFAULT_LAYOUT = { slot_1: "weather", ... }  (首次安装默认值)   │
 └──────────────────────────────┬──────────────────────────────────────┘
                                │
                                │  运行时读取配置
                                │
 ┌──────────────────────────────▼──────────────────────────────────────┐
 │                        渲染显示阶段                                   │
 │                                                                     │
 │  ① 表盘渲染  src/main_window_parts/painter.py  (PaintMixin)         │
 │     paintEvent()                                                    │
 │     ├── 从 QSettings 读取 slot_1~8 的 content_key                    │
 │     ├── 构建 content_text_map = { "cpu": "CPU 45%", ... }           │
 │     ├── 构建 multiline_map = { "date": ["2026/09/01", "周一"], ... } │
 │     └── 按 slot_position_map 坐标绘制到表盘                          │
 │                                                                     │
 │  ② 悬停详情  src/widgets/detail_popup.py  (DetailPopup)             │
 │     _build_content(content_key)                                     │
 │     ├── if content_key == 'cpu': → ["CPU 使用率：45%", "核心/线程:.."] │
 │     ├── if is_pro: → 追加 Pro 专属详情行                              │
 │     └── paintText() 逐行绘制                                        │
 │                                                                     │
 │  ③ 任务栏    src/taskbar_widget.py  (TaskbarWidget)                 │
 │     _get_display_text()                                             │
 │     ├── 读 taskbar_display 设置                                     │
 │     └── if key == 'cpu': return 'CPU 45%'                           │
 └─────────────────────────────────────────────────────────────────────┘
```

### 2.1 MainWindow 与 Mixin 架构

`MainWindow` 类通过**多重继承**组合了多个 Mixin，每个 Mixin 负责一组功能：

```
class MainWindow(PaintMixin,       # 表盘绘制        → painter.py
                 PerfMixin,        # 性能数据采集     → perf.py
                 WeatherMixin,     # 天气线程         → weather.py
                 LifecycleMixin,   # 窗口行为/悬停    → lifecycle.py
                 ServicesMixin,    # 设置/更新/公告   → services.py
                 QWidget):
```

这意味着 `MainWindow` 实例上可以直接访问所有 Mixin 的方法和属性。内容池相关的方法
分布在 `PaintMixin`、`PerfMixin` 和 `LifecycleMixin` 中。

### 2.2 两个内容池的区别

| 属性 | `content_pool` | `taskbar_pool` |
|------|----------------|----------------|
| 定义位置 | `display_page.py` | `display_page.py` |
| 用途 | 表盘 8 槽位 + 悬停详情 | 任务栏信息条 |
| 是否含 `empty` | ✅ 是（表示空槽位） | ❌ 否（用 `none` 表示不显示） |
| 是否含 `ip`/`date`/`lunar`/`term`/`resolution` | ✅ 是 | ❌ 否（任务栏空间太小） |
| 渲染文件 | `painter.py` + `detail_popup.py` | `taskbar_widget.py` |

---

## 3. 核心概念

### 3.1 content_key

每个内容项有一个唯一的字符串标识符，称为 **content_key**。它是贯穿所有层的主键。

现有 content_key 一览：

| content_key | 显示名称 | 数据来源 | 是否含动态 key |
|-------------|----------|----------|:--------------:|
| `ip` | IP | `perf.py` → `self.public_ip` / `self.local_ip` | ❌ |
| `weather` | 天气 | `weather.py` → `self.weather` dict | ❌ |
| `netspeed` | 网速 | `perf.py` → `self.down_speed` / `self.up_speed` | ❌ |
| `cpu` | CPU | `perf.py` → `self.cpu` | ❌ |
| `gpu` | GPU | `perf.py` → `self.gpu` | ❌ |
| `resolution` | 分辨率 | `painter.py` → `self.screen_res` | ❌ |
| `memory` | 内存 | `perf.py` → `self.mem` | ❌ |
| `date` | 公历 | `perf.py` → `self.now` | ❌ |
| `lunar` | 农历 | `perf.py` → `self.lunar_text` | ❌ |
| `term` | 节气 | `perf.py` → `self.term_display` | ❌ |
| `uptime` | 运行时间 | `perf.py` → `self.uptime` | ❌ |
| `disk_{盘符}` | 如 `C盘` | `perf.py` → `self.disk_usage["disk_C"]` | ✅ 动态 |
| `disk_total` | 磁盘总计 | `perf.py` → `self.disk_usage["disk_total"]` | ❌ |
| `empty` | 空 | — | ❌ 特殊 |

> **动态 key**：`disk_{盘符}` 是运行时根据实际磁盘分区动态生成的，如 `disk_C`、
> `disk_D`。代码中通过 `content_key.startswith("disk_")` 来匹配。

### 3.2 slot 与 slot_position_map

表盘有 8 个槽位，每个槽位有一个固定的矩形区域（x, y, width, height），定义在
`painter.py` 和 `lifecycle.py` 中：

```python
slot_position_map = {
    "slot_1": (20,  30,  105, 43),   # 左一
    "slot_2": (20,  86,   85, 43),   # 左二
    "slot_3": (20, 166,   70, 50),   # 左三
    "slot_4": (20, 235,   88, 50),   # 左四
    "slot_5": (280, 30,   94, 43),   # 右一
    "slot_6": (314, 86,   71, 43),   # 右二
    "slot_7": (324, 166,  60, 50),   # 右三
    "slot_8": (273, 238,  97, 43),   # 右四
}
```

> ⚠️ `painter.py` 和 `lifecycle.py` 中各有一份 `slot_position_map`，**两份必须保持
> 一致**。`painter.py` 的用于绘制文字，`lifecycle.py` 的用于鼠标悬停检测。

### 3.3 唯一性约束

同一个 content_key 不能同时出现在两个槽位中。设置页面（`display_page.py`）的
`_rebuild_combo_options()` 方法会在构建下拉选项时**排除已被其他槽位占用的 key**，
确保每个内容项最多出现一次。

### 3.4 持久化机制

用户的选择通过 PyQt6 的 `QSettings` 持久化，存储在 Windows 注册表中：

```
HKEY_CURRENT_USER\Software\MyDesktopApp\WeatherSettings
  slot_1 = "weather"
  slot_2 = "netspeed"
  ...
  taskbar_display = "netspeed"
  hover_enabled = true
```

代码中统一使用：
```python
settings = QSettings("MyDesktopApp", "WeatherSettings")
```


---

## 4. 六层详解

新增一个内容项需要改动以下文件（按数据流顺序排列）。每层的作用、关键代码位置和
改动要点如下：

### 4.1 第一层：注册定义 — `src/settings_pages/display_page.py`

这是内容池的**入口**。`DisplayPage` 类在 `__init__` 中定义了两个列表：

```python
# 表盘内容池（含 empty）
self.content_pool = [
    ("ip", self.tr("IP")),
    ("weather", self.tr("天气")),
    ("netspeed", self.tr("网速")),
    ("cpu", self.tr("CPU")),
    ("gpu", self.tr("GPU")),
    ("resolution", self.tr("分辨率")),
    ("memory", self.tr("内存")),
    ("date", self.tr("公历")),
    ("lunar", self.tr("农历")),
    ("term", self.tr("节气")),
    ("uptime", self.tr("运行时间")),
]
# ... 动态检测磁盘盘符后追加 disk_{盘符} ...
self.content_pool.append(("disk_total", self.tr("磁盘总计")))
self.content_pool.append(("empty", self.tr("空")))

# 任务栏内容池（精简版，无 empty / ip / date 等）
self.taskbar_pool = [
    ("netspeed", self.tr("网速")),
    ("weather", self.tr("天气")),
    ("cpu", self.tr("CPU")),
    ("gpu", self.tr("GPU")),
    ("memory", self.tr("内存")),
    ("uptime", self.tr("运行时间")),
]
# ... 追加动态磁盘盘符 + disk_total ...
```

**列表格式**：每个元素是一个 `(content_key, 显示名称)` 元组。显示名称使用 `self.tr()`
包裹以支持国际化。

**关键方法**：

| 方法 | 作用 |
|------|------|
| `_rebuild_combo_options()` | 根据当前各槽位占用情况，为每个下拉框生成可选列表（排除已占用的 key） |
| `_apply_layout_to_ui()` | 将 `layout_data` 同步到下拉框的当前选中项 |
| `_on_combo_changed()` | 用户切换下拉框时的回调，更新 `layout_data` 并保存到 QSettings |
| `_apply_changes()` | 将 `layout_data` 写入 QSettings，并触发主窗口重绘 |
| `load_layout_settings()` | 启动时从 QSettings 加载已保存的布局，含去重校验 |

**改动要点**：新增内容项时，在 `content_pool` 列表中添加 `("your_key", self.tr("名称"))`。
如果也需要在任务栏显示，则在 `taskbar_pool` 中同步添加。

### 4.2 第二层：默认布局 — `src/constants.py`

`DEFAULT_LAYOUT` 字典定义了首次安装时 8 个槽位的默认内容：

```python
DEFAULT_LAYOUT = {
    "slot_1": "weather",
    "slot_2": "netspeed",
    "slot_3": "resolution",
    "slot_4": "date",
    "slot_5": "ip",
    "slot_6": "gpu",
    "slot_7": "memory",
    "slot_8": "disk_total"
}
```

> 新增内容项通常**不需要**修改 `DEFAULT_LAYOUT`，除非你想让新内容成为默认显示项。
> 修改默认布局会影响所有首次安装的用户。

### 4.3 第三层：数据采集 — `src/main_window_parts/perf.py` + `src/main_window.py`

数据采集由 `PerfMixin`（`perf.py`）负责，结果存储为 `MainWindow` 实例属性。

**数据属性初始化**（`main_window.py` 的 `__init__` 中）：

```python
self.cpu = 0
self.gpu = 0
self.gpu_mem_used = 0
self.gpu_mem_total = 0
self.gpu_clock = 0
self.gpu_power = 0
self.mem = 0
self.local_ip = self.get_local_ip()
self.public_ip = ""
self.weather = {"city": "--", "weather": "--", "temp": "--", "wind": ""}
self.disk_usage = {}
self.uptime = ""
self.down_speed = 0.0
self.up_speed = 0.0
self.total_recv = 0
self.total_sent = 0
self.screen_res = "1920×1080"
self.now = datetime.now()
self.lunar_text = ""
self.term_display = ""
```

**采集定时器**（`main_window.py` 的 `__init__` 中）：

```python
self.clock_timer = QTimer()
self.clock_timer.timeout.connect(self.update_clock)     # 每 50ms
self.clock_timer.start(50)

self.perf_timer = QTimer()
self.perf_timer.timeout.connect(self.update_perf)       # 每 5s
self.perf_timer.start(5000)

self.net_thread = NetSpeedThread()                      # 网速独立线程
self.net_thread.speed_updated.connect(self.on_speed_update)
self.net_thread.start()
```

**采集方法**（`perf.py`）：

| 方法 | 采集内容 | 刷新频率 | 存储属性 |
|------|----------|----------|----------|
| `update_perf()` | CPU / GPU / 内存 / 磁盘 / 运行时间 | 5 秒 | `self.cpu`, `self.gpu`, `self.mem`, `self.disk_usage`, `self.uptime` |
| `update_clock()` | 时间 / 农历 / 节气 | 50ms | `self.now`, `self.lunar_text`, `self.term_display` |
| `on_speed_update()` | 网速 | 线程回调 | `self.down_speed`, `self.up_speed`, `self.total_recv`, `self.total_sent` |
| `_fetch_public_ip()` | 公网 IP | 启动延迟 2s | `self.public_ip` |
| `get_local_ip()` | 本机 IP | 启动时 | `self.local_ip` |

> **新增内容项时**：如果新内容需要系统数据，需在 `main_window.py` 的 `__init__` 中
> 初始化对应属性，并在 `perf.py` 的采集方法中填充数据。如果数据采集频率与现有定时器
> 不同，可能需要新建一个 QTimer。

### 4.4 第四层：表盘渲染 — `src/main_window_parts/painter.py`

`PaintMixin` 的 `paintEvent()` 是表盘渲染的核心。渲染文字信息的关键步骤：

**步骤 1：读取槽位配置**

```python
slot_values = {}
slot_keys = ["slot_1", "slot_2", ..., "slot_8"]
for key in slot_keys:
    default_val = DEFAULT_LAYOUT.get(key, "empty")
    slot_values[key] = settings.value(key, default_val)
```

**步骤 2：构建文本映射**

为每个 content_key 生成短文本字符串，存入 `content_text_map`：

```python
cpu_text = f"CPU{int(self.cpu)}%"
# ...

content_text_map = {
    "ip": ip_text,
    "weather": weather_text,
    "cpu": cpu_text,
    # ...
    "empty": "",
}

# 动态补充磁盘项
for dk, dv in self.disk_usage.items():
    if dk == "disk_total":
        content_text_map[dk] = f"{int(dv)}%"
    else:
        letter = dk.replace("disk_", "")
        content_text_map[dk] = f"{letter}: {int(dv)}%"
```

**步骤 3：构建多行文本映射**

部分内容项需要分两行显示，使用 `multiline_map` 单独处理：

```python
multiline_map = {
    "date": [self.now.strftime('%Y/%m/%d'),
             f"{self._i18n['week']}{self._i18n['weekdays'][self.now.weekday()]}"],
    "netspeed": [f"↓{self.down_speed:.1f}Mb/s", f"↑{self.up_speed:.1f}Mb/s"],
    "memory": [self._i18n['memory'], f"{int(self.mem)}%"],
    "disk_total": [self._i18n['disk_total'], f"{int(self.disk_usage.get('disk_total', 0))}%"],
}
```

**步骤 4：按槽位坐标绘制**

```python
for slot_key, (x, y, w, h) in slot_position_map.items():
    configured_key = slot_values.get(slot_key, "empty")
    if configured_key == "empty":
        continue
    if configured_key == "weather":
        # weather 有特殊的分行处理（城市 + 天气）
        ...
        continue
    if configured_key in multiline_map:
        # 多行内容逐行绘制
        ...
    elif configured_key in content_text_map:
        # 单行内容
        text = content_text_map[configured_key]
        if text:
            painter.drawText(x, y, w, h, ...)
```

> ⚠️ `weather` 有特殊的绘制逻辑（城市名 + 天气信息分两行），不使用 `content_text_map`
> 和 `multiline_map`，而是单独处理。

**改动要点**：新增内容项时，需在 `content_text_map` 或 `multiline_map` 中添加对应条目。
如果新内容需要特殊的分行绘制逻辑（如 weather），需要在绘制循环中添加 `if` 分支。

### 4.5 第五层：悬停详情 — `src/widgets/detail_popup.py`

`DetailPopup._build_content(content_key)` 方法根据内容类型构建多行详情文本。

**触发流程**（`lifecycle.py`）：

```
鼠标移动 → mouseMoveEvent()
  → _get_hover_slot(pos)  判断鼠标在哪个槽位
  → _detail_popup.show_for_slot(slot_key, content_key, rect)
    → _build_content(content_key)  构建文本行列表
    → _render_text(text)           计算尺寸并触发重绘
    → paintText()                  逐行绘制
```

**`_build_content` 结构**：

```python
def _build_content(self, content_key):
    is_pro = is_pro_enabled()
    mw = self._main_window
    lines = []

    if content_key in ('cpu',):
        lines.append(self.tr("CPU 使用率：{}%").format(int(mw.cpu)))
        if is_pro:
            # Pro 用户额外显示频率、核心数、温度
            ...
    elif content_key in ('gpu',):
        ...
    elif content_key in ('memory', 'mem'):
        ...
    # ... 每种 content_key 一个 elif 分支 ...
    elif content_key in ('resolution',):
        ...

    return lines
```

**Free / Pro 区分**：每个分支内通过 `if is_pro:` 追加更多详情行。Free 用户只看到
基础信息，Pro 用户看到完整详情。

**改动要点**：新增内容项时，在 `_build_content` 中添加一个 `elif` 分支，构建详情行
列表。建议同时实现 Free 和 Pro 两个层级的内容。

### 4.6 第六层：任务栏渲染 — `src/taskbar_widget.py`

`TaskbarWidget._get_display_text()` 读取 `taskbar_display` 设置并返回显示文本：

```python
def _get_display_text(self):
    settings = QSettings('MyDesktopApp', 'WeatherSettings')
    key = settings.value('taskbar_display', 'netspeed')
    mw = self.main_window

    if key == 'netspeed':
        return '↑ {:.1f}MB/s\n↓ {:.1f}MB/s'.format(mw.up_speed, mw.down_speed)
    elif key == 'weather':
        return '{} {}℃'.format(mw.weather.get('weather', '--'), mw.weather.get('temp', '--'))
    elif key == 'cpu':
        return 'CPU {}%'.format(int(mw.cpu))
    # ...
    elif key.startswith('disk_'):
        letter = key.replace('disk_', '')
        val = mw.disk_usage.get(key, 0)
        return '{}: {}%'.format(letter, int(val))
    else:
        return ''
```

> 这是**可选层**。如果新内容项不需要在任务栏显示，可以跳过此层（但也要跳过
> `taskbar_pool` 的注册）。

**改动要点**：新增任务栏内容时，在 `_get_display_text()` 中添加对应的 `elif` 分支。


---

## 5. 从零添加新内容项：完整教程

本节以添加一个**电池电量**（`battery`）内容项为例，演示从注册到渲染的完整流程。
电池电量显示百分比，悬停时显示剩余时间和充电状态（Pro 用户额外显示电池健康度）。

### 教程示例：battery（电池电量）

| 属性 | 值 |
|------|-----|
| content_key | `battery` |
| 表盘显示 | `电池 78%`（两行：标签 + 百分比） |
| 悬停详情（Free） | `电池电量：78%` |
| 悬停详情（Pro） | 追加 `充电状态：交流电` / `剩余时间：2.5 小时` / `电池健康：92%` |
| 任务栏 | `电 78%` |
| 数据来源 | `psutil.sensors_battery()` |
| 采集频率 | 5 秒（复用 `perf_timer`） |

### 改动文件清单

| 序号 | 文件 | 改动内容 | 是否必须 |
|:----:|------|----------|:--------:|
| 1 | `src/settings_pages/display_page.py` | `content_pool` 添加 `battery` | ✅ |
| 2 | `src/settings_pages/display_page.py` | `taskbar_pool` 添加 `battery` | ⬜ 可选 |
| 3 | `src/main_window.py` | `__init__` 初始化 `self.battery` 等属性 | ✅ |
| 4 | `src/main_window_parts/perf.py` | `update_perf()` 采集电池数据 | ✅ |
| 5 | `src/main_window_parts/painter.py` | `multiline_map` 添加 `battery` | ✅ |
| 6 | `src/widgets/detail_popup.py` | `_build_content` 添加 `battery` 分支 | ✅ |
| 7 | `src/taskbar_widget.py` | `_get_display_text` 添加 `battery` 分支 | ⬜ 可选 |
| 8 | `src/i18n/translations/translations_*.ts` | 添加翻译条目 | ✅ |

---

### Step 1：在 content_pool 中注册 — `display_page.py`

打开 `src/settings_pages/display_page.py`，在 `__init__` 方法的 `content_pool` 列表中
添加 `battery` 项。建议放在 `uptime` 之后、动态磁盘项之前：

```python
# --- 修改前 ---
self.content_pool = [
    ("ip", self.tr("IP")),
    ("weather", self.tr("天气")),
    ("netspeed", self.tr("网速")),
    ("cpu", self.tr("CPU")),
    ("gpu", self.tr("GPU")),
    ("resolution", self.tr("分辨率")),
    ("memory", self.tr("内存")),
    ("date", self.tr("公历")),
    ("lunar", self.tr("农历")),
    ("term", self.tr("节气")),
    ("uptime", self.tr("运行时间")),
]

# --- 修改后 ---
self.content_pool = [
    ("ip", self.tr("IP")),
    ("weather", self.tr("天气")),
    ("netspeed", self.tr("网速")),
    ("cpu", self.tr("CPU")),
    ("gpu", self.tr("GPU")),
    ("resolution", self.tr("分辨率")),
    ("memory", self.tr("内存")),
    ("date", self.tr("公历")),
    ("lunar", self.tr("农历")),
    ("term", self.tr("节气")),
    ("uptime", self.tr("运行时间")),
    ("battery", self.tr("电池")),          # ← 新增
]
```

> `content_pool` 是一个列表，顺序决定了下拉框中的显示顺序。`empty` 和 `disk_total`
> 在列表末尾动态追加，不要手动插入到中间。

### Step 2：（可选）在 taskbar_pool 中注册 — `display_page.py`

如果需要在任务栏信息条中也能选择电池，在 `taskbar_pool` 中添加：

```python
# --- 修改前 ---
self.taskbar_pool = [
    ("netspeed", self.tr("网速")),
    ("weather", self.tr("天气")),
    ("cpu", self.tr("CPU")),
    ("gpu", self.tr("GPU")),
    ("memory", self.tr("内存")),
    ("uptime", self.tr("运行时间")),
]

# --- 修改后 ---
self.taskbar_pool = [
    ("netspeed", self.tr("网速")),
    ("weather", self.tr("天气")),
    ("cpu", self.tr("CPU")),
    ("gpu", self.tr("GPU")),
    ("memory", self.tr("内存")),
    ("uptime", self.tr("运行时间")),
    ("battery", self.tr("电池")),          # ← 新增
]
```

### Step 3：初始化数据属性 — `main_window.py`

打开 `src/main_window.py`，在 `__init__` 方法的数据初始化区域添加电池相关属性。
找到 `self.disk_usage = {}` 附近，添加：

```python
# --- 在 self.uptime = "" 附近添加 ---
self.battery = 0              # 电池电量百分比
self.battery_plugged = False  # 是否接通电源
self.battery_secsleft = -1    # 剩余秒数（-2=无限，-1=未知）
```

> 所有数据属性必须在 `__init__` 中初始化，否则在数据采集完成前（首次 `update_perf()`
> 执行前），`paintEvent` 可能因属性不存在而崩溃。

### Step 4：采集数据 — `perf.py`

打开 `src/main_window_parts/perf.py`，在 `update_perf()` 方法中添加电池采集逻辑。
建议在 `self._update_disk_usage()` 调用之后添加：

```python
def update_perf(self):
    try:
        self.cpu = psutil.cpu_percent()
        self.mem = psutil.virtual_memory().percent
        # ... GPU 读取逻辑（已有，省略）...
        self._update_disk_usage()
        self._update_uptime()
        self._update_battery()        # ← 新增
        self.update()
    except Exception:
        self.gpu = 0
        self.update()
```

然后在 `PerfMixin` 类中添加 `_update_battery` 方法（放在 `_update_uptime` 之后）：

```python
def _update_battery(self):
    """采集电池电量、充电状态和剩余时间"""
    try:
        bat = psutil.sensors_battery()
        if bat is not None:
            self.battery = int(bat.percent)
            self.battery_plugged = bat.power_plugged
            self.battery_secsleft = bat.secsleft
        else:
            # 没有电池（台式机），保持默认值
            self.battery = 0
            self.battery_plugged = False
            self.battery_secsleft = -1
    except Exception:
        self.battery = 0
        self.battery_plugged = False
        self.battery_secsleft = -1
```

> 电池采集复用了 5 秒的 `perf_timer`，无需新建定时器。`psutil.sensors_battery()` 在
> 台式机上返回 `None`，因此需要做空值判断。

### Step 5：表盘渲染 — `painter.py`

打开 `src/main_window_parts/painter.py`，在 `paintEvent()` 中做两处修改。

**5a. 构建 battery 文本**

在 `content_text_map` 构建区域（`uptime_text` 变量附近）添加：

```python
uptime_text = self.uptime
# --- 新增 ---
battery_text = f"{int(self.battery)}%"
```

然后在 `content_text_map` 字典中添加条目：

```python
content_text_map = {
    "ip": ip_text,
    "weather": weather_text,
    "netspeed": netspeed_text,
    "cpu": cpu_text,
    "gpu": gpu_text,
    "resolution": resolution_text,
    "memory": memory_text,
    "date": date_text,
    "lunar": lunar_text,
    "term": term_text,
    "uptime": uptime_text,
    "battery": battery_text,            # ← 新增
    "empty": "",
}
```

**5b. 添加多行映射**

电池电量适合两行显示（标签 + 百分比），在 `multiline_map` 中添加：

```python
multiline_map = {
    "date": [...],
    "netspeed": [...],
    "memory": [self._i18n['memory'], f"{int(self.mem)}%"],
    "disk_total": [self._i18n['disk_total'], f"{int(self.disk_usage.get('disk_total', 0))}%"],
    "battery": [self._i18n.get('battery', '电池'), f"{int(self.battery)}%"],  # ← 新增
}
```

> `self._i18n` 是国际化文本字典，需要在 `main_window.py` 的 `_init_i18n()` 中添加
> `battery` 键（见 Step 8 的说明）。如果未添加，用 `self._i18n.get('battery', '电池')`
> 做降级处理。

> **单行 vs 多行**：如果新内容只需一行显示，只需加到 `content_text_map`，无需加到
> `multiline_map`。绘制循环会优先检查 `multiline_map`，其次检查 `content_text_map`。

### Step 6：悬停详情 — `detail_popup.py`

打开 `src/widgets/detail_popup.py`，在 `_build_content()` 方法中添加 `battery` 分支。
建议放在 `uptime` 分支之后、`disk_total` 分支之前：

```python
elif content_key in ('uptime',):
    uptime = getattr(mw, 'uptime', '')
    lines.append(self.tr("已运行：{}").format(uptime))
    if is_pro:
        # ... 已有 Pro 逻辑 ...

# ========== 新增 battery 分支 ==========
elif content_key in ('battery',):
    battery_val = int(getattr(mw, 'battery', 0))
    lines.append(self.tr("电池电量：{}%").format(battery_val))
    if is_pro:
        plugged = getattr(mw, 'battery_plugged', False)
        if plugged:
            lines.append(self.tr("充电状态：交流电"))
        else:
            lines.append(self.tr("充电状态：电池"))
        secsleft = getattr(mw, 'battery_secsleft', -1)
        if secsleft > 0:
            hours = secsleft / 3600
            lines.append(self.tr("剩余时间：{:.1f} 小时").format(hours))
        elif secsleft == -2:
            lines.append(self.tr("剩余时间：无限"))
        # 电池健康度（需要额外采集，此处用占位示例）
        # 如有 WMI 或其他数据源可在此补充
# ========== 新增结束 ==========

elif content_key == 'disk_total':
    ...
```

> `getattr(mw, 'battery', 0)` 使用 `getattr` 而非 `mw.battery` 是防御性编程，避免在
> 数据属性尚未初始化时崩溃。项目现有代码也采用这种模式。

### Step 7：（可选）任务栏渲染 — `taskbar_widget.py`

打开 `src/taskbar_widget.py`，在 `_get_display_text()` 中添加 `battery` 分支：

```python
def _get_display_text(self):
    # ... 已有代码 ...
    elif key == 'uptime':
        return mw.uptime if mw.uptime else ''
    # ========== 新增 ==========
    elif key == 'battery':
        return '电 {}%'.format(int(mw.battery))
    # ========== 新增结束 ==========
    elif key == 'disk_total':
        ...
```

> 任务栏空间非常有限（高度仅 28px），文本要尽量简短。单行文本居中绘制，多行文本
> 会自动调整行距。

### Step 8：i18n 国际化

本项目支持 8 种语言。新增的显示文本需要添加到翻译文件中。

**8a. `_init_i18n` 添加内置文本**（`main_window.py`）

如果新内容用到了 `self._i18n` 字典（如 Step 5b 中的 `battery` 键），需要在
`main_window.py` 的 `_init_i18n()` 方法中添加：

```python
def _init_i18n(self):
    t = TranslatorManager().translate
    self._i18n = {
        # ... 已有键值 ...
        "battery": t('MainWindow', '电池'),    # ← 新增
    }
```

**8b. .ts 翻译文件**

翻译文件位于 `src/i18n/translations/` 目录，格式为 Qt Linguist 的 XML 格式。
每个 `translations_{lang}.ts` 文件需要添加对应条目。

以 `translations_en.ts` 为例，在 `<context>` 块中添加：

```xml
<context>
    <name>DisplayPage</name>
    <message>
        <source>电池</source>
        <translation>Battery</translation>
    </message>
</context>
```

以 `translations_ja.ts` 为例：

```xml
<message>
    <source>电池</source>
    <translation>バッテリー</translation>
</message>
```

同理，`detail_popup.py` 中 `self.tr("电池电量：{}%")` 等文本也需要在 `DetailPopup`
context 下添加翻译条目。

> **翻译 context 规则**：`self.tr("文本")` 的 context 是该代码所在的**类名**。
> 例如 `display_page.py` 中 `DisplayPage` 类内的 `self.tr("电池")` 对应 context 为
> `DisplayPage`；`detail_popup.py` 中 `DetailPopup` 类内的 `self.tr(...)` 对应
> context 为 `DetailPopup`。
>
> `QCoreApplication.translate("Constants", "C盘")` 的 context 则是显式指定的
> `"Constants"`。

> 项目还内置了 Python 字典翻译系统（`translations.py` 中的 `_builtin_translations`），
> 会从 `.ts` 文件加载翻译到内存。修改 `.ts` 文件后无需编译 `.qm` 文件即可生效。


---

## 6. 常见陷阱与注意事项

### 6.1 必须在 `__init__` 中初始化数据属性

`paintEvent()` 在窗口创建后立即执行，此时如果数据属性尚未定义，会导致
`AttributeError` 崩溃。**所有新内容项的数据属性必须在 `MainWindow.__init__` 中
初始化**，即使初始值是 `0` 或空字符串。

```python
# ❌ 错误：忘记初始化
# paintEvent 访问 self.battery 时崩溃

# ✅ 正确：在 __init__ 中初始化
self.battery = 0
```

### 6.2 两份 slot_position_map 必须一致

`painter.py` 和 `lifecycle.py` 各有一份 `slot_position_map`。前者用于绘制文字，
后者用于鼠标悬停检测。如果两者不一致，会导致"文字画在这里，鼠标悬停却检测到另一个
区域"的问题。

> 注意：`lifecycle.py` 中 `slot_8` 的坐标是 `(273, 245, 97, 52)`，而 `painter.py`
> 中是 `(273, 238, 97, 43)`，两者 y 坐标和高度略有差异。这是历史遗留，悬停检测区域
> 比绘制区域略大以提升用户体验。新增槽位时不需要完全一致，但区域中心应对齐。

### 6.3 动态 content_key 的匹配方式

磁盘类内容使用动态 key（`disk_C`、`disk_D`），在渲染和悬停详情中通过
`content_key.startswith("disk_")` 来匹配，而不是逐一列举。如果你的新内容也有动态
key（如多块显卡 `gpu_0`、`gpu_1`），需要采用同样的前缀匹配模式。

### 6.4 weather 的特殊处理

`weather` 在表盘渲染中有独立的绘制分支（城市名 + 天气信息分两行），不走
`content_text_map` / `multiline_map` 的通用路径。如果你的新内容也需要类似的特殊
布局（如带图标的天气），参考 `painter.py` 中 `if configured_key == "weather":` 的
处理方式。

### 6.5 Free / Pro 分层

悬停详情中，Free 用户只看到基础信息，Pro 用户看到完整详情。新增内容项时建议同时
实现两个层级：

```python
lines.append(self.tr("基础信息"))       # Free + Pro 都显示
if is_pro:
    lines.append(self.tr("Pro 专属详情")) # 仅 Pro 显示
```

Pro 检测使用 `from ..utils import is_pro_enabled`。

### 6.6 数据采集频率

现有定时器频率：
- `clock_timer`：50ms（时间、农历、节气）—— 适合需要高频更新的内容
- `perf_timer`：5s（CPU、GPU、内存、磁盘、运行时间）—— 适合一般系统指标
- `NetSpeedThread`：独立线程回调（网速）—— 适合需要实时性但不阻塞 UI 的内容

如果新内容需要不同的采集频率（如每 10 秒采集一次），需要新建 QTimer：

```python
self.battery_timer = QTimer()
self.battery_timer.timeout.connect(self._update_battery)
self.battery_timer.start(10000)   # 10 秒
```

并在 `shutdown()` 方法中停止该定时器。

### 6.7 settings 读写一致性

QSettings 的 key 名称在所有文件中必须完全一致。项目统一使用：
```python
settings = QSettings("MyDesktopApp", "WeatherSettings")
```

不要在其他地方使用不同的组织名/应用名，否则读写的是不同的注册表分支。

### 6.8 `_refresh_draw_cache` 是空操作

`display_page.py` 的 `_apply_changes()` 中调用了 `main_window._refresh_draw_cache()`，
但该方法实际未定义。调用前有 `hasattr` 保护，所以不会报错。实际的界面刷新依赖
`main_window.update()` 触发 `paintEvent` 重绘。新增内容项后无需关心这个方法。

---

## 7. 验证清单

完成所有改动后，按以下步骤验证：

### 7.1 基本功能验证

- [ ] 启动程序，打开「设置 → 显示」页面
- [ ] 确认新内容项出现在 8 个下拉框的可选列表中
- [ ] 在某个空槽位选择新内容项，确认表盘立即显示对应文字
- [ ] 确认选择后其他下拉框中该内容项变为不可选（唯一性约束生效）
- [ ] 鼠标悬停在新内容槽位上，确认弹出详情面板且内容正确
- [ ] （如实现了任务栏）在任务栏下拉框中选择新内容项，确认任务栏显示正确
- [ ] 重启程序，确认上次选择被正确持久化

### 7.2 边界情况验证

- [ ] 将新内容设为某个槽位，再切换为「空」，确认槽位清空且不报错
- [ ] 在台式机（无电池）上测试，确认不崩溃，显示合理默认值
- [ ] 切换语言（如英文 / 日文），确认新内容的显示名称正确翻译
- [ ] 点击「恢复默认」按钮，确认新内容项不影响默认布局恢复

### 7.3 Pro 验证（如实现了 Pro 分层）

- [ ] Free 状态下悬停，确认只显示基础信息
- [ ] Pro 状态下悬停，确认显示完整详情
- [ ] 确认 Pro 提示行可点击且跳转正确

---

## 8. 附录

### 8.1 完整文件索引

| 文件路径 | 职责 | 内容池相关 |
|----------|------|------------|
| `src/constants.py` | 常量定义 | `DEFAULT_LAYOUT` 默认布局 |
| `src/main_window.py` | 主窗口（组合所有 Mixin） | 数据属性初始化、定时器、`_init_i18n` |
| `src/main_window_parts/painter.py` | 表盘绘制 Mixin | `paintEvent()` 文字渲染、`slot_position_map` |
| `src/main_window_parts/perf.py` | 性能采集 Mixin | `update_perf()`、`update_clock()`、`on_speed_update()` |
| `src/main_window_parts/weather.py` | 天气线程 Mixin | 天气数据采集 |
| `src/main_window_parts/lifecycle.py` | 窗口行为 Mixin | `mouseMoveEvent()` 悬停检测、`slot_position_map` |
| `src/main_window_parts/services.py` | 服务 Mixin | 设置对话框、更新检查 |
| `src/settings_pages/display_page.py` | 显示设置页 | `content_pool` / `taskbar_pool` 定义、下拉框逻辑 |
| `src/widgets/detail_popup.py` | 悬停详情面板 | `_build_content()` 内容构建 |
| `src/taskbar_widget.py` | 任务栏信息条 | `_get_display_text()` 渲染 |
| `src/i18n/translations.py` | 翻译系统 | 翻译加载与管理 |
| `src/i18n/translations/translations_*.ts` | 翻译文件 | 8 种语言的翻译条目 |

### 8.2 现有内容项的 content_key 与数据属性对照表

| content_key | MainWindow 属性 | 类型 | 采集方法 |
|-------------|-----------------|------|----------|
| `ip` | `self.public_ip` / `self.local_ip` | `str` | `_fetch_public_ip()` / `get_local_ip()` |
| `weather` | `self.weather` | `dict` | `WeatherThread`（天气线程） |
| `netspeed` | `self.down_speed` / `self.up_speed` | `float` | `on_speed_update()` |
| `cpu` | `self.cpu` | `float` | `update_perf()` |
| `gpu` | `self.gpu` | `float` | `update_perf()` |
| `resolution` | `self.screen_res` | `str` | `_init_paint()` |
| `memory` | `self.mem` | `float` | `update_perf()` |
| `date` | `self.now` | `datetime` | `update_clock()` |
| `lunar` | `self.lunar_text` | `str` | `update_clock()` |
| `term` | `self.term_display` | `str` | `update_clock()` |
| `uptime` | `self.uptime` / `self._uptime_seconds` | `str` / `int` | `update_perf()` → `_update_uptime()` |
| `disk_{盘符}` | `self.disk_usage["disk_C"]` | `float` | `update_perf()` → `_update_disk_usage()` |
| `disk_total` | `self.disk_usage["disk_total"]` | `int` | `update_perf()` → `_update_disk_usage()` |

### 8.3 Pro 专属数据属性一览

以下属性仅在 Pro 模式的悬停详情中使用，Free 模式下不读取：

| 属性 | 类型 | 来源 | 用途 |
|------|------|------|------|
| `self.gpu_mem_total` | `int` | `update_perf()` (NVML) | GPU 显存总量 |
| `self.gpu_mem_used` | `int` | `update_perf()` (NVML) | GPU 显存已用 |
| `self.gpu_clock` | `int` | `update_perf()` (NVML) | GPU 频率 |
| `self.gpu_power` | `int` | `update_perf()` (NVML) | GPU 功耗 |
| `self.total_recv` | `int` | `on_speed_update()` | 累计下载量 |
| `self.total_sent` | `int` | `on_speed_update()` | 累计上传量 |
| `self.server_ip` | `str` | `ServerScanner` | 内网服务器 IP |
| `self.refresh_rate` | `int` | `_init_paint()` | 屏幕刷新率 |

### 8.4 slot_position_map 坐标说明

```
  (0,0) ─────────────────────────────────────── 400
    │                                           │
    │  slot_1(20,30)      slot_5(280,30)       │
    │  slot_2(20,86)      slot_6(314,86)       │
    │  slot_3(20,166)     slot_7(324,166)      │
    │  slot_4(20,235)     slot_8(273,238)      │
    │                                           │
   297 ──────────────────────────────────────── ┘

  坐标格式: (x, y, width, height)
  表盘中心: (201, 144)  →  指针旋转中心
```

左侧 4 个槽位 (slot_1 ~ slot_4) 的 x 坐标为 20，右侧 4 个 (slot_5 ~ slot_8) 的
x 坐标为 273~324。槽位宽高根据可用空间不同而有所变化。

### 8.5 快速改动检查清单

新增一个内容项，最少需要改动以下位置（打勾确认）：

- [ ] `display_page.py` → `content_pool` 列表添加 `("key", self.tr("名称"))`
- [ ] `main_window.py` → `__init__` 初始化数据属性
- [ ] `perf.py` → 采集方法中填充数据
- [ ] `painter.py` → `content_text_map` 或 `multiline_map` 添加渲染条目
- [ ] `detail_popup.py` → `_build_content()` 添加 `elif` 分支
- [ ] `translations_*.ts` → 添加翻译条目

可选改动：
- [ ] `display_page.py` → `taskbar_pool` 添加条目
- [ ] `taskbar_widget.py` → `_get_display_text()` 添加分支
- [ ] `constants.py` → `DEFAULT_LAYOUT` 修改默认值（通常不需要）
- [ ] `main_window.py` → `_init_i18n()` 添加 i18n 键值

---

> 本文档基于 DesktopWidget v1.5.3 代码编写。如有疑问，请参考源码或联系项目维护者。
