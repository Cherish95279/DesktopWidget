# DesktopWidget Content Pool Developer Guide

This document is intended for developers with Python / PyQt6 experience who are new to
this project. It provides a detailed explanation of the "Content Pool" architecture and
data flow, along with a complete step-by-step tutorial for adding new content items from
scratch.

> Before reading this guide, it is recommended to quickly skim `docs/THEME_DEV_GUIDE.md`
> to understand canvas dimensions and layer concepts, since content pool text is drawn
> on top of the theme dial.

---

## 1. What Is the Content Pool

DesktopWidget's main interface is a 400×297-pixel clock dial. Around the dial there are
**8 fixed slots** (slot_1 ~ slot_8), each of which can display one type of system
information (CPU, weather, network speed, etc.).

**The "Content Pool" is the registry of all selectable information types for these 8 slots.**

Users assign a content type to each slot via 8 dropdown boxes in the Settings → Display
page. The selected content is drawn onto the dial in real time. Hovering the mouse over
a slot pops up a detailed information panel. Additionally, the taskbar info bar has a
streamlined subset of the content pool.

### 1.1 Three Display Scenarios

The same content item may appear in three different display scenarios, each with its own
independent rendering logic:

| Scenario | Location | Render File | Characteristics |
|----------|----------|-------------|-----------------|
| **Dial slots** | 8 fixed coordinates around the dial | `src/main_window_parts/painter.py` | Short text, limited space |
| **Hover detail** | Floating panel on mouse hover | `src/widgets/detail_popup.py` | Multi-line detail, Free / Pro split |
| **Taskbar info bar** | Windows taskbar notification area | `src/taskbar_widget.py` | Single compact text line |

> These three scenarios have **independent** rendering logic. When adding a new content
> item, each must be adapted individually — otherwise you will get "selectable in settings
> but not displayed" or "hover shows no detail" issues.

---

## 2. Architecture Overview and Data Flow

The content pool data flow is divided into three stages — **collection → storage →
rendering** — spanning 6 files. The diagram below shows the complete path of a content
item (using `cpu` as an example) from system data to final display:

```
 ┌─────────────────────────────────────────────────────────────────────┐
 │                      Data Collection Stage                           │
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
 │  └── Initialize all data attributes: self.cpu = 0, self.gpu = 0,... │
 └──────────────────────────────┬──────────────────────────────────────┘
                                │
                                │  Data stored as MainWindow instance attrs
                                │  (self.cpu, self.weather, self.disk_usage ...)
                                │
 ┌──────────────────────────────▼──────────────────────────────────────┐
 │                  Persistence & Configuration Stage                   │
 │                                                                     │
 │  QSettings("MyDesktopApp", "WeatherSettings")                       │
 │  ├── slot_1 = "weather"    (content key for dial slot 1)            │
 │  ├── slot_2 = "netspeed"                                           │
 │  ├── ...                                                           │
 │  ├── slot_8 = "disk_total"                                         │
 │  ├── taskbar_display = "netspeed"  (taskbar info bar content key)   │
 │  └── hover_enabled = True   (hover detail toggle)                   │
 │                                                                     │
 │  src/constants.py                                                   │
 │  └── DEFAULT_LAYOUT = { slot_1: "weather", ... }  (first-run default)│
 └──────────────────────────────┬──────────────────────────────────────┘
                                │
                                │  Read config at runtime
                                │
 ┌──────────────────────────────▼──────────────────────────────────────┐
 │                      Rendering & Display Stage                       │
 │                                                                     │
 │  ① Dial render  src/main_window_parts/painter.py  (PaintMixin)      │
 │     paintEvent()                                                    │
 │     ├── Read slot_1~8 content_key from QSettings                    │
 │     ├── Build content_text_map = { "cpu": "CPU 45%", ... }          │
 │     ├── Build multiline_map = { "date": ["2026/09/01", "Mon"], ... }│
 │     └── Draw to dial using slot_position_map coordinates            │
 │                                                                     │
 │  ② Hover detail  src/widgets/detail_popup.py  (DetailPopup)         │
 │     _build_content(content_key)                                     │
 │     ├── if content_key == 'cpu': → ["CPU: 45%", "Cores: ..."]       │
 │     ├── if is_pro: → append Pro-only detail lines                   │
 │     └── paintText() draws line by line                              │
 │                                                                     │
 │  ③ Taskbar    src/taskbar_widget.py  (TaskbarWidget)                │
 │     _get_display_text()                                             │
 │     ├── Read taskbar_display setting                                │
 │     └── if key == 'cpu': return 'CPU 45%'                           │
 └─────────────────────────────────────────────────────────────────────┘
```

### 2.1 MainWindow and the Mixin Architecture

The `MainWindow` class composes multiple Mixins via **multiple inheritance**, with each
Mixin responsible for a group of features:

```
class MainWindow(PaintMixin,       # Dial drawing        → painter.py
                 PerfMixin,        # Performance data     → perf.py
                 WeatherMixin,     # Weather thread       → weather.py
                 LifecycleMixin,   # Window behavior/hover→ lifecycle.py
                 ServicesMixin,    # Settings/update/notice→ services.py
                 QWidget):
```

This means all Mixin methods and attributes are directly accessible on the `MainWindow`
instance. Content pool-related methods are spread across `PaintMixin`, `PerfMixin`, and
`LifecycleMixin`.

### 2.2 The Two Content Pools

| Property | `content_pool` | `taskbar_pool` |
|----------|----------------|----------------|
| Defined in | `display_page.py` | `display_page.py` |
| Purpose | Dial 8 slots + hover detail | Taskbar info bar |
| Contains `empty` | ✅ Yes (represents an empty slot) | ❌ No (uses `none` for "off") |
| Contains `ip`/`date`/`lunar`/`term`/`resolution` | ✅ Yes | ❌ No (taskbar too small) |
| Rendered by | `painter.py` + `detail_popup.py` | `taskbar_widget.py` |

---

## 3. Core Concepts

### 3.1 content_key

Each content item has a unique string identifier called the **content_key**. It is the
primary key that flows through all layers.

Existing content_keys:

| content_key | Display name | Data source | Dynamic key? |
|-------------|-------------|-------------|:------------:|
| `ip` | IP | `perf.py` → `self.public_ip` / `self.local_ip` | ❌ |
| `weather` | Weather | `weather.py` → `self.weather` dict | ❌ |
| `netspeed` | Network speed | `perf.py` → `self.down_speed` / `self.up_speed` | ❌ |
| `cpu` | CPU | `perf.py` → `self.cpu` | ❌ |
| `gpu` | GPU | `perf.py` → `self.gpu` | ❌ |
| `resolution` | Resolution | `painter.py` → `self.screen_res` | ❌ |
| `memory` | Memory | `perf.py` → `self.mem` | ❌ |
| `date` | Gregorian date | `perf.py` → `self.now` | ❌ |
| `lunar` | Lunar date | `perf.py` → `self.lunar_text` | ❌ |
| `term` | Solar term | `perf.py` → `self.term_display` | ❌ |
| `uptime` | Uptime | `perf.py` → `self.uptime` | ❌ |
| `disk_{letter}` | e.g. `C drive` | `perf.py` → `self.disk_usage["disk_C"]` | ✅ Dynamic |
| `disk_total` | Total disk | `perf.py` → `self.disk_usage["disk_total"]` | ❌ |
| `empty` | Empty | — | ❌ Special |

> **Dynamic keys**: `disk_{letter}` is generated at runtime based on actual disk partitions,
> e.g. `disk_C`, `disk_D`. Code matches them with `content_key.startswith("disk_")`.

### 3.2 Slots and slot_position_map

The dial has 8 slots, each with a fixed rectangular region (x, y, width, height) defined
in `painter.py` and `lifecycle.py`:

```python
slot_position_map = {
    "slot_1": (20,  30,  105, 43),   # Left 1
    "slot_2": (20,  86,   85, 43),   # Left 2
    "slot_3": (20, 166,   70, 50),   # Left 3
    "slot_4": (20, 235,   88, 50),   # Left 4
    "slot_5": (280, 30,   94, 43),   # Right 1
    "slot_6": (314, 86,   71, 43),   # Right 2
    "slot_7": (324, 166,  60, 50),   # Right 3
    "slot_8": (273, 238,  97, 43),   # Right 4
}
```

> ⚠️ There are two copies of `slot_position_map` — one in `painter.py` and one in
> `lifecycle.py`. **Both must be kept in sync.** The one in `painter.py` is for drawing
> text; the one in `lifecycle.py` is for mouse hover detection.

### 3.3 Uniqueness Constraint

The same content_key cannot appear in two slots simultaneously. The settings page
(`display_page.py`) enforces this in `_rebuild_combo_options()`, which **excludes keys
already occupied by other slots** when building dropdown options, ensuring each content
item appears at most once.

### 3.4 Persistence Mechanism

User selections are persisted via PyQt6's `QSettings`, stored in the Windows registry:

```
HKEY_CURRENT_USER\Software\MyDesktopApp\WeatherSettings
  slot_1 = "weather"
  slot_2 = "netspeed"
  ...
  taskbar_display = "netspeed"
  hover_enabled = true
```

The code consistently uses:
```python
settings = QSettings("MyDesktopApp", "WeatherSettings")
```


---

## 4. The Six Layers in Detail

Adding a new content item requires changes to the following files (ordered by data flow).
Each layer's purpose, key code locations, and change points are described below.

### 4.1 Layer 1: Registration — `src/settings_pages/display_page.py`

This is the **entry point** of the content pool. The `DisplayPage` class defines two lists
in `__init__`:

```python
# Dial content pool (includes empty)
self.content_pool = [
    ("ip", self.tr("IP")),
    ("weather", self.tr("Weather")),
    ("netspeed", self.tr("Net Speed")),
    ("cpu", self.tr("CPU")),
    ("gpu", self.tr("GPU")),
    ("resolution", self.tr("Resolution")),
    ("memory", self.tr("Memory")),
    ("date", self.tr("Date")),
    ("lunar", self.tr("Lunar")),
    ("term", self.tr("Solar Term")),
    ("uptime", self.tr("Uptime")),
]
# ... dynamically detect disk partitions, then append disk_{letter} ...
self.content_pool.append(("disk_total", self.tr("Total Disk")))
self.content_pool.append(("empty", self.tr("Empty")))

# Taskbar content pool (streamlined, no empty / ip / date etc.)
self.taskbar_pool = [
    ("netspeed", self.tr("Net Speed")),
    ("weather", self.tr("Weather")),
    ("cpu", self.tr("CPU")),
    ("gpu", self.tr("GPU")),
    ("memory", self.tr("Memory")),
    ("uptime", self.tr("Uptime")),
]
# ... append dynamic disk letters + disk_total ...
```

**List format**: Each element is a `(content_key, display_name)` tuple. The display name
is wrapped in `self.tr()` for internationalization.

**Key methods**:

| Method | Purpose |
|--------|---------|
| `_rebuild_combo_options()` | Generates selectable lists for each dropdown based on current slot occupancy (excludes occupied keys) |
| `_apply_layout_to_ui()` | Syncs `layout_data` to dropdown current selections |
| `_on_combo_changed()` | Callback when user switches a dropdown; updates `layout_data` and saves to QSettings |
| `_apply_changes()` | Writes `layout_data` to QSettings and triggers main window repaint |
| `load_layout_settings()` | Loads saved layout from QSettings on startup, with dedup validation |

**Change point**: When adding a new content item, add `("your_key", self.tr("Name"))` to
the `content_pool` list. If it should also appear in the taskbar, add it to `taskbar_pool`
as well.

### 4.2 Layer 2: Default Layout — `src/constants.py`

The `DEFAULT_LAYOUT` dictionary defines the default content for all 8 slots on first
install:

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

> New content items typically **do not** require modifying `DEFAULT_LAYOUT`, unless you want
> the new content to be shown by default. Changing the default layout affects all
> first-install users.

### 4.3 Layer 3: Data Collection — `src/main_window_parts/perf.py` + `src/main_window.py`

Data collection is handled by `PerfMixin` (`perf.py`), with results stored as `MainWindow`
instance attributes.

**Data attribute initialization** (in `main_window.py` `__init__`):

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

**Collection timers** (in `main_window.py` `__init__`):

```python
self.clock_timer = QTimer()
self.clock_timer.timeout.connect(self.update_clock)     # every 50ms
self.clock_timer.start(50)

self.perf_timer = QTimer()
self.perf_timer.timeout.connect(self.update_perf)       # every 5s
self.perf_timer.start(5000)

self.net_thread = NetSpeedThread()                      # independent network speed thread
self.net_thread.speed_updated.connect(self.on_speed_update)
self.net_thread.start()
```

**Collection methods** (`perf.py`):

| Method | Collects | Refresh rate | Stored attributes |
|--------|----------|--------------|-------------------|
| `update_perf()` | CPU / GPU / memory / disk / uptime | 5 seconds | `self.cpu`, `self.gpu`, `self.mem`, `self.disk_usage`, `self.uptime` |
| `update_clock()` | Time / lunar / solar term | 50ms | `self.now`, `self.lunar_text`, `self.term_display` |
| `on_speed_update()` | Network speed | Thread callback | `self.down_speed`, `self.up_speed`, `self.total_recv`, `self.total_sent` |
| `_fetch_public_ip()` | Public IP | 2s after startup | `self.public_ip` |
| `get_local_ip()` | Local IP | At startup | `self.local_ip` |

> **When adding a new content item**: If the new content requires system data, initialize
> the corresponding attribute in `main_window.py`'s `__init__`, and populate the data in
> a collection method in `perf.py`. If the collection frequency differs from existing
> timers, you may need to create a new QTimer.

### 4.4 Layer 4: Dial Rendering — `src/main_window_parts/painter.py`

`PaintMixin`'s `paintEvent()` is the core of dial rendering. Key steps for rendering text
information:

**Step 1: Read slot configuration**

```python
slot_values = {}
slot_keys = ["slot_1", "slot_2", ..., "slot_8"]
for key in slot_keys:
    default_val = DEFAULT_LAYOUT.get(key, "empty")
    slot_values[key] = settings.value(key, default_val)
```

**Step 2: Build text mapping**

For each content_key, generate a short text string and store it in `content_text_map`:

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

# Dynamically add disk entries
for dk, dv in self.disk_usage.items():
    if dk == "disk_total":
        content_text_map[dk] = f"{int(dv)}%"
    else:
        letter = dk.replace("disk_", "")
        content_text_map[dk] = f"{letter}: {int(dv)}%"
```

**Step 3: Build multiline text mapping**

Some content items need to be displayed in two lines, handled separately via `multiline_map`:

```python
multiline_map = {
    "date": [self.now.strftime('%Y/%m/%d'),
             f"{self._i18n['week']}{self._i18n['weekdays'][self.now.weekday()]}"],
    "netspeed": [f"↓{self.down_speed:.1f}Mb/s", f"↑{self.up_speed:.1f}Mb/s"],
    "memory": [self._i18n['memory'], f"{int(self.mem)}%"],
    "disk_total": [self._i18n['disk_total'], f"{int(self.disk_usage.get('disk_total', 0))}%"],
}
```

**Step 4: Draw by slot coordinates**

```python
for slot_key, (x, y, w, h) in slot_position_map.items():
    configured_key = slot_values.get(slot_key, "empty")
    if configured_key == "empty":
        continue
    if configured_key == "weather":
        # weather has special two-line handling (city + weather)
        ...
        continue
    if configured_key in multiline_map:
        # Multiline content drawn line by line
        ...
    elif configured_key in content_text_map:
        # Single-line content
        text = content_text_map[configured_key]
        if text:
            painter.drawText(x, y, w, h, ...)
```

> ⚠️ `weather` has special drawing logic (city name + weather info in two lines) that does
> not use the `content_text_map` / `multiline_map` general path — it is handled separately.

**Change point**: When adding a new content item, add the corresponding entry to
`content_text_map` or `multiline_map`. If the new content needs special multi-line drawing
logic (like weather), add an `if` branch in the drawing loop.

### 4.5 Layer 5: Hover Detail — `src/widgets/detail_popup.py`

`DetailPopup._build_content(content_key)` builds multi-line detail text based on content
type.

**Trigger flow** (`lifecycle.py`):

```
Mouse move → mouseMoveEvent()
  → _get_hover_slot(pos)  determine which slot the mouse is over
  → _detail_popup.show_for_slot(slot_key, content_key, rect)
    → _build_content(content_key)  build list of text lines
    → _render_text(text)           calculate size and trigger repaint
    → paintText()                  draw line by line
```

**`_build_content` structure**:

```python
def _build_content(self, content_key):
    is_pro = is_pro_enabled()
    mw = self._main_window
    lines = []

    if content_key in ('cpu',):
        lines.append(self.tr("CPU: {}%").format(int(mw.cpu)))
        if is_pro:
            # Pro users get extra: frequency, core count, temperature
            ...
    elif content_key in ('gpu',):
        ...
    elif content_key in ('memory', 'mem'):
        ...
    # ... one elif branch per content_key ...
    elif content_key in ('resolution',):
        ...

    return lines
```

**Free / Pro split**: Within each branch, `if is_pro:` appends additional detail lines.
Free users see only basic info; Pro users see full details.

**Change point**: When adding a new content item, add an `elif` branch in
`_build_content` to build the detail line list. It is recommended to implement both Free
and Pro tiers.

### 4.6 Layer 6: Taskbar Rendering — `src/taskbar_widget.py`

`TaskbarWidget._get_display_text()` reads the `taskbar_display` setting and returns the
display text:

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

> This is an **optional layer**. If the new content item does not need taskbar display,
> you can skip this layer (but also skip `taskbar_pool` registration).

**Change point**: When adding taskbar content, add the corresponding `elif` branch in
`_get_display_text()`.


---

## 5. Adding a New Content Item from Scratch: Complete Tutorial

This section demonstrates the complete flow from registration to rendering using a
**battery level** (`battery`) content item as an example. The battery level shows a
percentage on the dial, and on hover displays remaining time and charging status (Pro
users additionally see battery health).

### Tutorial Example: battery (Battery Level)

| Property | Value |
|----------|-------|
| content_key | `battery` |
| Dial display | `Battery 78%` (two lines: label + percentage) |
| Hover detail (Free) | `Battery: 78%` |
| Hover detail (Pro) | Append `Charging: AC Power` / `Time remaining: 2.5 hours` / `Health: 92%` |
| Taskbar | `Bat 78%` |
| Data source | `psutil.sensors_battery()` |
| Collection frequency | 5 seconds (reuse `perf_timer`) |

### File Change Checklist

| # | File | Change | Required? |
|:-:|------|--------|:---------:|
| 1 | `src/settings_pages/display_page.py` | Add `battery` to `content_pool` | ✅ |
| 2 | `src/settings_pages/display_page.py` | Add `battery` to `taskbar_pool` | ⬜ Optional |
| 3 | `src/main_window.py` | Initialize `self.battery` etc. in `__init__` | ✅ |
| 4 | `src/main_window_parts/perf.py` | Collect battery data in `update_perf()` | ✅ |
| 5 | `src/main_window_parts/painter.py` | Add `battery` to `multiline_map` | ✅ |
| 6 | `src/widgets/detail_popup.py` | Add `battery` branch in `_build_content` | ✅ |
| 7 | `src/taskbar_widget.py` | Add `battery` branch in `_get_display_text` | ⬜ Optional |
| 8 | `src/i18n/translations/translations_*.ts` | Add translation entries | ✅ |

---

### Step 1: Register in content_pool — `display_page.py`

Open `src/settings_pages/display_page.py` and add the `battery` item to the
`content_pool` list in `__init__`. Place it after `uptime` and before the dynamic disk
items:

```python
# --- Before ---
self.content_pool = [
    ("ip", self.tr("IP")),
    ("weather", self.tr("Weather")),
    ("netspeed", self.tr("Net Speed")),
    ("cpu", self.tr("CPU")),
    ("gpu", self.tr("GPU")),
    ("resolution", self.tr("Resolution")),
    ("memory", self.tr("Memory")),
    ("date", self.tr("Date")),
    ("lunar", self.tr("Lunar")),
    ("term", self.tr("Solar Term")),
    ("uptime", self.tr("Uptime")),
]

# --- After ---
self.content_pool = [
    ("ip", self.tr("IP")),
    ("weather", self.tr("Weather")),
    ("netspeed", self.tr("Net Speed")),
    ("cpu", self.tr("CPU")),
    ("gpu", self.tr("GPU")),
    ("resolution", self.tr("Resolution")),
    ("memory", self.tr("Memory")),
    ("date", self.tr("Date")),
    ("lunar", self.tr("Lunar")),
    ("term", self.tr("Solar Term")),
    ("uptime", self.tr("Uptime")),
    ("battery", self.tr("Battery")),        # ← new
]
```

> `content_pool` is a list; the order determines the display order in the dropdowns.
> `empty` and `disk_total` are appended dynamically at the end — do not insert them
> manually in the middle.

### Step 2: (Optional) Register in taskbar_pool — `display_page.py`

If the battery should also be selectable in the taskbar info bar, add it to
`taskbar_pool`:

```python
# --- Before ---
self.taskbar_pool = [
    ("netspeed", self.tr("Net Speed")),
    ("weather", self.tr("Weather")),
    ("cpu", self.tr("CPU")),
    ("gpu", self.tr("GPU")),
    ("memory", self.tr("Memory")),
    ("uptime", self.tr("Uptime")),
]

# --- After ---
self.taskbar_pool = [
    ("netspeed", self.tr("Net Speed")),
    ("weather", self.tr("Weather")),
    ("cpu", self.tr("CPU")),
    ("gpu", self.tr("GPU")),
    ("memory", self.tr("Memory")),
    ("uptime", self.tr("Uptime")),
    ("battery", self.tr("Battery")),        # ← new
]
```

### Step 3: Initialize data attributes — `main_window.py`

Open `src/main_window.py` and add battery-related attributes in the data initialization
section of `__init__`. Find the area near `self.disk_usage = {}` and add:

```python
# --- Add near self.uptime = "" ---
self.battery = 0              # Battery percentage
self.battery_plugged = False  # Whether on AC power
self.battery_secsleft = -1    # Seconds left (-2=unlimited, -1=unknown)
```

> All data attributes must be initialized in `__init__`. Otherwise, before the first
> `update_perf()` runs, `paintEvent` may crash due to a missing attribute.

### Step 4: Collect data — `perf.py`

Open `src/main_window_parts/perf.py` and add battery collection logic in the
`update_perf()` method. Add it after the `self._update_disk_usage()` call:

```python
def update_perf(self):
    try:
        self.cpu = psutil.cpu_percent()
        self.mem = psutil.virtual_memory().percent
        # ... existing GPU logic (omitted) ...
        self._update_disk_usage()
        self._update_uptime()
        self._update_battery()        # ← new
        self.update()
    except Exception:
        self.gpu = 0
        self.update()
```

Then add the `_update_battery` method to the `PerfMixin` class (after `_update_uptime`):

```python
def _update_battery(self):
    """Collect battery level, charging status, and remaining time"""
    try:
        bat = psutil.sensors_battery()
        if bat is not None:
            self.battery = int(bat.percent)
            self.battery_plugged = bat.power_plugged
            self.battery_secsleft = bat.secsleft
        else:
            # No battery (desktop), keep defaults
            self.battery = 0
            self.battery_plugged = False
            self.battery_secsleft = -1
    except Exception:
        self.battery = 0
        self.battery_plugged = False
        self.battery_secsleft = -1
```

> Battery collection reuses the 5-second `perf_timer` — no new timer needed.
> `psutil.sensors_battery()` returns `None` on desktops, so a null check is required.

### Step 5: Dial rendering — `painter.py`

Open `src/main_window_parts/painter.py` and make two changes in `paintEvent()`.

**5a. Build battery text**

In the `content_text_map` construction area (near the `uptime_text` variable), add:

```python
uptime_text = self.uptime
# --- new ---
battery_text = f"{int(self.battery)}%"
```

Then add an entry to the `content_text_map` dictionary:

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
    "battery": battery_text,            # ← new
    "empty": "",
}
```

**5b. Add multiline mapping**

Battery level is best displayed in two lines (label + percentage). Add to `multiline_map`:

```python
multiline_map = {
    "date": [...],
    "netspeed": [...],
    "memory": [self._i18n['memory'], f"{int(self.mem)}%"],
    "disk_total": [self._i18n['disk_total'], f"{int(self.disk_usage.get('disk_total', 0))}%"],
    "battery": [self._i18n.get('battery', 'Battery'), f"{int(self.battery)}%"],  # ← new
}
```

> `self._i18n` is the internationalization text dictionary. You need to add a `battery` key
> to `_init_i18n()` in `main_window.py` (see Step 8). If not added,
> `self._i18n.get('battery', 'Battery')` provides a fallback.

> **Single-line vs multiline**: If the new content only needs one line, just add it to
> `content_text_map` — no need for `multiline_map`. The drawing loop checks `multiline_map`
> first, then `content_text_map`.

### Step 6: Hover detail — `detail_popup.py`

Open `src/widgets/detail_popup.py` and add a `battery` branch in `_build_content()`.
Place it after the `uptime` branch and before the `disk_total` branch:

```python
elif content_key in ('uptime',):
    uptime = getattr(mw, 'uptime', '')
    lines.append(self.tr("Uptime: {}").format(uptime))
    if is_pro:
        # ... existing Pro logic ...

# ========== New battery branch ==========
elif content_key in ('battery',):
    battery_val = int(getattr(mw, 'battery', 0))
    lines.append(self.tr("Battery: {}%").format(battery_val))
    if is_pro:
        plugged = getattr(mw, 'battery_plugged', False)
        if plugged:
            lines.append(self.tr("Charging: AC Power"))
        else:
            lines.append(self.tr("Charging: Battery"))
        secsleft = getattr(mw, 'battery_secsleft', -1)
        if secsleft > 0:
            hours = secsleft / 3600
            lines.append(self.tr("Time remaining: {:.1f} hours").format(hours))
        elif secsleft == -2:
            lines.append(self.tr("Time remaining: Unlimited"))
        # Battery health (requires additional collection; placeholder example)
        # Add WMI or other data source here if available
# ========== End new branch ==========

elif content_key == 'disk_total':
    ...
```

> `getattr(mw, 'battery', 0)` uses `getattr` instead of `mw.battery` as defensive
> programming to avoid crashes when the attribute is not yet initialized. The existing
> code follows this pattern.

### Step 7: (Optional) Taskbar rendering — `taskbar_widget.py`

Open `src/taskbar_widget.py` and add a `battery` branch in `_get_display_text()`:

```python
def _get_display_text(self):
    # ... existing code ...
    elif key == 'uptime':
        return mw.uptime if mw.uptime else ''
    # ========== new ==========
    elif key == 'battery':
        return 'Bat {}%'.format(int(mw.battery))
    # ========== end new ==========
    elif key == 'disk_total':
        ...
```

> Taskbar space is very limited (height only 28px), so keep text as short as possible.
> Single-line text is centered; multiline text auto-adjusts line spacing.

### Step 8: i18n internationalization

This project supports 8 languages. New display text must be added to the translation files.

**8a. Add built-in text to `_init_i18n`** (`main_window.py`)

If the new content uses the `self._i18n` dictionary (like the `battery` key in Step 5b),
add it to `_init_i18n()` in `main_window.py`:

```python
def _init_i18n(self):
    t = TranslatorManager().translate
    self._i18n = {
        # ... existing keys ...
        "battery": t('MainWindow', 'Battery'),    # ← new
    }
```

**8b. .ts translation files**

Translation files are in `src/i18n/translations/` in Qt Linguist XML format. Each
`translations_{lang}.ts` file needs corresponding entries.

Example for `translations_en.ts`, add within a `<context>` block:

```xml
<context>
    <name>DisplayPage</name>
    <message>
        <source>Battery</source>
        <translation>Battery</translation>
    </message>
</context>
```

Example for `translations_ja.ts`:

```xml
<message>
    <source>Battery</source>
    <translation>バッテリー</translation>
</message>
```

Similarly, `self.tr("Battery: {}%")` etc. in `detail_popup.py` need entries under the
`DetailPopup` context.

> **Translation context rule**: The context for `self.tr("text")` is the **class name**
> where the code resides. For example, `self.tr("Battery")` inside the `DisplayPage` class
> in `display_page.py` has context `DisplayPage`; `self.tr(...)` inside the `DetailPopup`
> class in `detail_popup.py` has context `DetailPopup`.
>
> `QCoreApplication.translate("Constants", "C Drive")` has the explicitly specified context
> `"Constants"`.

> The project also has a built-in Python dictionary translation system
> (`_builtin_translations` in `translations.py`) that loads translations from `.ts` files
> into memory. After modifying `.ts` files, no `.qm` compilation is needed — changes take
> effect immediately.


---

## 6. Common Pitfalls and Notes

### 6.1 Always initialize data attributes in `__init__`

`paintEvent()` executes immediately after window creation. If data attributes are not yet
defined at that point, it will crash with `AttributeError`. **All data attributes for new
content items must be initialized in `MainWindow.__init__`**, even if the initial value is
`0` or an empty string.

```python
# ❌ Wrong: forgot to initialize
# paintEvent crashes when accessing self.battery

# ✅ Correct: initialize in __init__
self.battery = 0
```

### 6.2 Both copies of slot_position_map must match

`painter.py` and `lifecycle.py` each have a copy of `slot_position_map`. The former is for
drawing text, the latter for mouse hover detection. If they are inconsistent, you get
"text drawn here, but hover detected in a different area" problems.

> Note: In `lifecycle.py`, `slot_8` coordinates are `(273, 245, 97, 52)`, while in
> `painter.py` they are `(273, 238, 97, 43)` — the y coordinate and height differ
> slightly. This is a historical artifact; the hover detection area is slightly larger
> than the drawing area for better UX. New slots do not need to match exactly, but the
> region centers should align.

### 6.3 Dynamic content_key matching

Disk content uses dynamic keys (`disk_C`, `disk_D`), matched in rendering and hover detail
via `content_key.startswith("disk_")` rather than individual enumeration. If your new
content also has dynamic keys (e.g. multiple GPUs `gpu_0`, `gpu_1`), use the same prefix
matching pattern.

### 6.4 Special handling for weather

`weather` has an independent drawing branch in dial rendering (city name + weather info in
two lines) that bypasses the `content_text_map` / `multiline_map` general path. If your
new content needs similar special layout (e.g. weather with icons), refer to the
`if configured_key == "weather":` handling in `painter.py`.

### 6.5 Free / Pro tiering

In hover detail, Free users see only basic info while Pro users see full details. When
adding a new content item, implement both tiers:

```python
lines.append(self.tr("Basic info"))       # shown to Free + Pro
if is_pro:
    lines.append(self.tr("Pro-only detail")) # Pro only
```

Pro detection uses `from ..utils import is_pro_enabled`.

### 6.6 Data collection frequency

Existing timer frequencies:
- `clock_timer`: 50ms (time, lunar, solar term) — suitable for high-frequency updates
- `perf_timer`: 5s (CPU, GPU, memory, disk, uptime) — suitable for general system metrics
- `NetSpeedThread`: independent thread callback (network speed) — suitable for real-time
  data without blocking the UI

If the new content needs a different collection frequency (e.g. every 10 seconds), create
a new QTimer:

```python
self.battery_timer = QTimer()
self.battery_timer.timeout.connect(self._update_battery)
self.battery_timer.start(10000)   # 10 seconds
```

And stop this timer in the `shutdown()` method.

### 6.7 QSettings read/write consistency

QSettings key names must be identical across all files. The project consistently uses:
```python
settings = QSettings("MyDesktopApp", "WeatherSettings")
```

Do not use different organization/application names elsewhere — otherwise you would be
reading/writing a different registry branch.

### 6.8 `_refresh_draw_cache` is a no-op

`display_page.py`'s `_apply_changes()` calls `main_window._refresh_draw_cache()`, but
this method is never actually defined. The call is guarded by `hasattr`, so it does not
error. The actual UI refresh relies on `main_window.update()` triggering a `paintEvent`
repaint. No need to worry about this method when adding new content.

---

## 7. Verification Checklist

After completing all changes, verify using these steps:

### 7.1 Basic functionality

- [ ] Launch the app, open Settings → Display
- [ ] Confirm the new content item appears in the 8 dropdown option lists
- [ ] Select the new content in an empty slot, confirm the dial shows the text immediately
- [ ] Confirm that after selecting, the item becomes unselectable in other dropdowns
      (uniqueness constraint)
- [ ] Hover the mouse over the new content slot, confirm the detail panel pops up with
      correct content
- [ ] (If taskbar implemented) Select the new content in the taskbar dropdown, confirm
      the taskbar displays correctly
- [ ] Restart the app, confirm the last selection is correctly persisted

### 7.2 Edge cases

- [ ] Set the new content in a slot, then switch to "Empty", confirm the slot clears
      without errors
- [ ] Test on a desktop (no battery), confirm no crash and reasonable default values
- [ ] Switch languages (e.g. English / Japanese), confirm the new content display name is
      correctly translated
- [ ] Click "Restore Default" button, confirm the new content does not interfere with
      default layout restoration

### 7.3 Pro verification (if Pro tiering is implemented)

- [ ] Hover in Free mode, confirm only basic info is shown
- [ ] Hover in Pro mode, confirm full details are shown
- [ ] Confirm the Pro prompt line is clickable and redirects correctly

---

## 8. Appendix

### 8.1 Complete File Index

| File path | Responsibility | Content pool relation |
|-----------|---------------|----------------------|
| `src/constants.py` | Constants | `DEFAULT_LAYOUT` default layout |
| `src/main_window.py` | Main window (composes all Mixins) | Data attribute init, timers, `_init_i18n` |
| `src/main_window_parts/painter.py` | Dial drawing Mixin | `paintEvent()` text rendering, `slot_position_map` |
| `src/main_window_parts/perf.py` | Performance collection Mixin | `update_perf()`, `update_clock()`, `on_speed_update()` |
| `src/main_window_parts/weather.py` | Weather thread Mixin | Weather data collection |
| `src/main_window_parts/lifecycle.py` | Window behavior Mixin | `mouseMoveEvent()` hover detection, `slot_position_map` |
| `src/main_window_parts/services.py` | Services Mixin | Settings dialog, update check |
| `src/settings_pages/display_page.py` | Display settings page | `content_pool` / `taskbar_pool` definition, dropdown logic |
| `src/widgets/detail_popup.py` | Hover detail panel | `_build_content()` content building |
| `src/taskbar_widget.py` | Taskbar info bar | `_get_display_text()` rendering |
| `src/i18n/translations.py` | Translation system | Translation loading and management |
| `src/i18n/translations/translations_*.ts` | Translation files | Translation entries for 8 languages |

### 8.2 content_key to Data Attribute Reference

| content_key | MainWindow attribute | Type | Collection method |
|-------------|---------------------|------|-------------------|
| `ip` | `self.public_ip` / `self.local_ip` | `str` | `_fetch_public_ip()` / `get_local_ip()` |
| `weather` | `self.weather` | `dict` | `WeatherThread` (weather thread) |
| `netspeed` | `self.down_speed` / `self.up_speed` | `float` | `on_speed_update()` |
| `cpu` | `self.cpu` | `float` | `update_perf()` |
| `gpu` | `self.gpu` | `float` | `update_perf()` |
| `resolution` | `self.screen_res` | `str` | `_init_paint()` |
| `memory` | `self.mem` | `float` | `update_perf()` |
| `date` | `self.now` | `datetime` | `update_clock()` |
| `lunar` | `self.lunar_text` | `str` | `update_clock()` |
| `term` | `self.term_display` | `str` | `update_clock()` |
| `uptime` | `self.uptime` / `self._uptime_seconds` | `str` / `int` | `update_perf()` → `_update_uptime()` |
| `disk_{letter}` | `self.disk_usage["disk_C"]` | `float` | `update_perf()` → `_update_disk_usage()` |
| `disk_total` | `self.disk_usage["disk_total"]` | `int` | `update_perf()` → `_update_disk_usage()` |

### 8.3 Pro-only Data Attributes

The following attributes are only used in Pro-mode hover details; Free mode does not
read them:

| Attribute | Type | Source | Purpose |
|-----------|------|--------|---------|
| `self.gpu_mem_total` | `int` | `update_perf()` (NVML) | GPU total VRAM |
| `self.gpu_mem_used` | `int` | `update_perf()` (NVML) | GPU used VRAM |
| `self.gpu_clock` | `int` | `update_perf()` (NVML) | GPU clock frequency |
| `self.gpu_power` | `int` | `update_perf()` (NVML) | GPU power draw |
| `self.total_recv` | `int` | `on_speed_update()` | Total data received |
| `self.total_sent` | `int` | `on_speed_update()` | Total data sent |
| `self.server_ip` | `str` | `ServerScanner` | LAN server IP |
| `self.refresh_rate` | `int` | `_init_paint()` | Screen refresh rate |

### 8.4 slot_position_map Coordinate Guide

```
  (0,0) ─────────────────────────────────────── 400
    │                                           │
    │  slot_1(20,30)      slot_5(280,30)       │
    │  slot_2(20,86)      slot_6(314,86)       │
    │  slot_3(20,166)     slot_7(324,166)      │
    │  slot_4(20,235)     slot_8(273,238)      │
    │                                           │
   297 ──────────────────────────────────────── ┘

  Format: (x, y, width, height)
  Dial center: (201, 144)  →  hand rotation pivot
```

The left 4 slots (slot_1 ~ slot_4) have x = 20; the right 4 (slot_5 ~ slot_8) have
x = 273~324. Slot width and height vary based on available space.

### 8.5 Quick Change Checklist

To add a new content item, the minimum required changes (check off each):

- [ ] `display_page.py` → add `("key", self.tr("Name"))` to `content_pool` list
- [ ] `main_window.py` → initialize data attributes in `__init__`
- [ ] `perf.py` → populate data in a collection method
- [ ] `painter.py` → add rendering entry to `content_text_map` or `multiline_map`
- [ ] `detail_popup.py` → add `elif` branch in `_build_content()`
- [ ] `translations_*.ts` → add translation entries

Optional changes:
- [ ] `display_page.py` → add entry to `taskbar_pool`
- [ ] `taskbar_widget.py` → add branch in `_get_display_text()`
- [ ] `constants.py` → modify `DEFAULT_LAYOUT` (usually not needed)
- [ ] `main_window.py` → add i18n key to `_init_i18n()`

---

> This document is based on DesktopWidget v1.5.3 source code. For questions, please refer
> to the source code or contact the project maintainer.
