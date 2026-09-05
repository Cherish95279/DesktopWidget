# DesktopWidget Content Pool Plugin Developer Guide

This document is intended for developers with Python / PyQt6 experience who are new to
this project. It explains how to develop custom plugins for DesktopWidget's content pool,
with a complete step-by-step tutorial.

> Before reading this guide, it is recommended to read `docs/CONTENT_POOL_DEV_GUIDE_EN.md`
> to understand the basic architecture of the content pool (8 slots, the
> collection → storage → rendering data flow, and the content_key concept).

---

## 1. What Is a Content Pool Plugin

DesktopWidget's dial has 8 fixed slots, each of which can display one type of system
information (CPU, weather, network speed, etc.). These built-in information items form
the "content pool."

**Content pool plugins** allow developers to add custom information items without
modifying the main program code. Plugins are imported as ZIP packages and automatically
appear in the settings page dropdowns, where users can assign them to any slot.

Plugins support three display scenarios (consistent with built-in content items):

| Scenario | Method | Description |
|----------|--------|-------------|
| Dial slot | `render_short()` | Short text, 1~2 lines |
| Hover detail | `render_detail()` | Multi-line detail, Free / Pro split |
| Taskbar info bar | `render_taskbar()` | Single compact text line (optional) |

---

## 2. Plugin Package Structure

Plugins are distributed as ZIP files. The extracted directory structure is as follows:

```
sunrise_sunset.zip
├── plugin.json              ← Metadata (required)
├── sunrise_sunset.py        ← Main plugin module (required)
└── translations/            ← Translation files (optional)
    ├── translations_en.ts
    └── translations_ja.ts
```

### 2.1 File Naming Rules

- **plugin.json**: Fixed filename, must be in the plugin root directory or a
  first-level subdirectory
- **Main module .py**: The filename must match the plugin directory name or the `key`.
  For example, if the directory is named `sunrise_sunset`, the main module can be
  `sunrise_sunset.py`
- **Plugin directory name**: Must match the `key` field in `plugin.json`

### 2.2 ZIP Packaging

Package with a first-level subdirectory included:

```bash
# Correct: ZIP contains a sunrise_sunset/ directory
cd plugins_source
zip -r sunrise_sunset.zip sunrise_sunset/

# Wrong: packaged directly in root, no subdirectory
cd sunrise_sunset
zip -r ../sunrise_sunset.zip *    # plugin.json at ZIP root, can be detected but not recommended
```

---

## 3. plugin.json Field Reference

```json
{
    "key": "sunrise_sunset",
    "name": "Sunrise & Sunset",
    "description": "Display today's sunrise and sunset times",
    "version": "1.0.0",
    "author": "YourName",
    "min_app_version": "1.6.0",
    "collect_interval": 300,
    "supports_taskbar": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|:--------:|---------|-------------|
| `key` | str | ✅ | — | Unique content pool identifier; letters, digits, underscores only |
| `name` | str | ❌ | Same as key | Display name, appears in dropdowns |
| `description` | str | ❌ | "" | Short description, appears in plugin management list |
| `version` | str | ❌ | "1.0.0" | Version number |
| `author` | str | ❌ | "" | Author name |
| `min_app_version` | str | ❌ | "" | Minimum supported App version |
| `collect_interval` | int | ❌ | 300 | Data collection interval (seconds), minimum 5 |
| `supports_taskbar` | bool | ❌ | false | Whether to support taskbar info bar display |

> `key` is the primary key throughout the system. Do not change it after release,
> otherwise users' saved slot configurations will become invalid.

---

## 4. ContentPlugin Standard Interface

The main plugin module must define a class that inherits from `ContentPlugin`:

```python
from plugin_manager import ContentPlugin


class SunriseSunsetPlugin(ContentPlugin):
    """Sunrise & Sunset plugin"""

    def collect(self, context):
        """Data collection, returns dict"""
        # context provides settings, now, etc.
        # Calculate sunrise and sunset times here
        return {
            "sunrise": "06:12",
            "sunset": "18:45",
            "day_length": "12h 33m"
        }

    def render_short(self, data, i18n):
        """Dial slot short text"""
        # Return str for single line, list for multiple lines
        return [f"🌅 {data['sunrise']}", f"🌇 {data['sunset']}"]

    def render_detail(self, data, is_pro, i18n):
        """Hover detail multi-line text"""
        lines = [
            f"Sunrise: {data['sunrise']}",
            f"Sunset: {data['sunset']}",
        ]
        if is_pro:
            lines.append(f"Day length: {data['day_length']}")
        return lines

    def render_taskbar(self, data, i18n):
        """Taskbar text (called when supports_taskbar=True)"""
        return f"🌅{data['sunrise']}"
```

### 4.1 Method Reference

#### collect(context) → dict

Data collection method. Called periodically by PluginManager at the `collect_interval`.

- **context**: `PluginContext` instance, providing:
  - `context.settings` — QSettings instance for reading user config
  - `context.now` — current datetime object
  - `context.get_setting(key, default, type)` — convenient setting reader
- **Returns**: dict, any structure, passed as `data` to render methods
- **Error handling**: Exceptions are caught by PluginManager; 5 consecutive failures
  will auto-disable the plugin

#### render_short(data, i18n) → str | list

Dial slot short text. Space is limited (~60~105px wide, 43~50px tall), recommend no
more than 2 lines.

- **data**: dict returned by `collect()`
- **i18n**: Internationalization text dict (same structure as MainWindow._i18n)
- **Returns**:
  - `str`: single-line text
  - `list[str]`: multi-line text, one element per line

#### render_detail(data, is_pro, i18n) → list[str]

Hover detail. The floating panel that appears when hovering over a slot; ample space
for multiple lines.

- **is_pro**: bool, whether the user is Pro. Recommend providing more detail for Pro.
- **Returns**: `list[str]`, one string per line

#### render_taskbar(data, i18n) → str

Taskbar info bar text. Only called when `supports_taskbar: true`.

- Taskbar height is only 28px; keep text as short as possible
- **Returns**: str, single-line text

### 4.2 i18n Dictionary

The `i18n` parameter is MainWindow's internationalization text dict, containing common
UI text. Plugins can use it for simple internationalization, or handle multi-language
text internally.

Common available keys (depends on current language):
```python
i18n.get("memory", "Memory")    # "Memory" / "内存" / "メモリ" ...
i18n.get("week", "Day")         # "Day" / "星期" ...
```

> If the plugin needs its own translated text, it is recommended to read the current
> language from `context.settings` in `collect()` and include translated text in the
> returned data dict.

---

## 5. PluginContext Reference

`PluginContext` is the sole entry point for plugins to access user configuration and
basic capabilities. Plugins **should not** directly access the MainWindow instance.

```python
def collect(self, context):
    # Read user's language setting
    lang = context.get_setting("language", "en")

    # Read user's selected location (weather-related)
    city = context.get_setting("selected_city", "")

    # Get current time
    now = context.now

    # Directly access QSettings
    all_keys = context.settings.allKeys()

    return {...}
```

### 5.1 Available Settings

Common QSettings keys (organization `MyDesktopApp`, application `WeatherSettings`):

| Key | Type | Description |
|-----|------|-------------|
| `language` | str | Current language code (zh_CN / zh_TW / en / ja / ko / de / fr / es) |
| `selected_province` | str | User-selected province |
| `selected_city` | str | User-selected city |
| `selected_county` | str | User-selected county/district |
| `font_color` | str | Font color (e.g. "#1c344d") |
| `font_family` | str | Font family (e.g. "Microsoft YaHei") |
| `font_size` | int | Font size |
| `hover_enabled` | bool | Whether hover detail is enabled |
| `theme_color` | str | Theme background color |

---

## 6. Developing a Plugin from Scratch: Complete Tutorial

This section demonstrates the complete flow from creation to import using a
**sunrise & sunset** plugin as an example.

### 6.1 Create the Project Directory

```
plugins_source/
└── sunrise_sunset/
    ├── plugin.json
    └── sunrise_sunset.py
```

### 6.2 Write plugin.json

```json
{
    "key": "sunrise_sunset",
    "name": "Sunrise & Sunset",
    "description": "Display today's sunrise and sunset times",
    "version": "1.0.0",
    "author": "DesktopWidget Team",
    "collect_interval": 3600,
    "supports_taskbar": true
}
```

> Collection interval is set to 3600 seconds (1 hour), since sunrise/sunset times
> barely change within a day.

### 6.3 Write sunrise_sunset.py

```python
# -*- coding: utf-8 -*-
"""Sunrise & Sunset plugin - Display today's sunrise and sunset times"""

import math
from datetime import datetime, timedelta
from plugin_manager import ContentPlugin


class SunriseSunsetPlugin(ContentPlugin):
    """Sunrise & Sunset plugin"""

    def collect(self, context):
        """Calculate today's sunrise and sunset times"""
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
            "day_length": f"{hours}h {minutes}m",
            "date": now.strftime("%Y/%m/%d"),
        }

    def render_short(self, data, i18n):
        """Dial display: two lines"""
        return [f"🌅 {data['sunrise']}", f"🌇 {data['sunset']}"]

    def render_detail(self, data, is_pro, i18n):
        """Hover detail"""
        lines = [
            f"Date: {data['date']}",
            f"Sunrise: {data['sunrise']}",
            f"Sunset: {data['sunset']}",
        ]
        if is_pro:
            lines.append(f"Day length: {data['day_length']}")
        return lines

    def render_taskbar(self, data, i18n):
        """Taskbar: single line"""
        return f"🌅{data['sunrise']} 🌇{data['sunset']}"

    # ---------- Internal methods ----------

    def _get_location(self, context):
        """Get coordinates from user settings, default to Beijing"""
        # Can look up coordinates based on user's selected city
        # Using default value here; actual development can integrate region data
        return 39.9042, 116.4074  # Beijing

    def _calc_sunrise_sunset(self, year, month, day, lat, lon):
        """Simplified sunrise/sunset calculation (based on astronomical formulas)"""
        n = datetime(year, month, day).timetuple().tm_yday

        # Solar declination
        decl = 23.45 * math.sin(math.radians(360 * (284 + n) / 365))

        # Hour angle
        lat_rad = math.radians(lat)
        decl_rad = math.radians(decl)
        cos_omega = -math.tan(lat_rad) * math.tan(decl_rad)

        # Polar day/night handling
        if cos_omega > 1:
            return None, None  # Polar night
        if cos_omega < -1:
            return None, None  # Polar day

        omega = math.degrees(math.acos(cos_omega))

        # Sunrise/sunset time (UTC, approximate)
        sunrise_utc = 12 - omega / 15 - lon / 15
        sunset_utc = 12 + omega / 15 - lon / 15

        # Convert to local time (UTC+8)
        tz_offset = 8
        sunrise_hour = (sunrise_utc + tz_offset) % 24
        sunset_hour = (sunset_utc + tz_offset) % 24

        sunrise = self._hour_to_datetime(year, month, day, sunrise_hour)
        sunset = self._hour_to_datetime(year, month, day, sunset_hour)

        return sunrise, sunset

    def _hour_to_datetime(self, year, month, day, hour_float):
        """Convert hour float to datetime"""
        h = int(hour_float)
        m = int((hour_float - h) * 60)
        s = int(((hour_float - h) * 60 - m) * 60)
        return datetime(year, month, day, h, m, s)
```

### 6.4 Package the ZIP

```bash
cd plugins_source
zip -r sunrise_sunset.zip sunrise_sunset/
```

The ZIP internal structure should be:
```
sunrise_sunset.zip
└── sunrise_sunset/
    ├── plugin.json
    └── sunrise_sunset.py
```

### 6.5 Import and Test

1. Launch DesktopWidget
2. Open Settings → Display
3. Click the "Manage Plugins" button
4. In the upper section of the dialog, click "Browse..." and select `sunrise_sunset.zip`
5. Review the validation results; if there are security warnings, confirm the usage
6. Click "Import"
7. After successful import, "Sunrise & Sunset" appears in the plugin list below
8. Close the dialog and select "Sunrise & Sunset" from one of the 8 slot dropdowns
9. Verify the dial displays sunrise and sunset times
10. Hover the mouse to verify the detail panel
11. Select "Sunrise & Sunset" from the taskbar dropdown to verify taskbar display

---

## 7. Import Validation Flow

When importing a plugin, PluginManager performs the following validations:

1. **Extract ZIP** — Verify it is a valid ZIP file
2. **Find plugin.json** — Search in root directory or first-level subdirectory
3. **Validate JSON format** — Must contain a valid `key` field
4. **Validate key** — Letters, digits, underscores only
5. **Find main module** — directory_name.py or key.py must exist
6. **Static security scan** — Scan for dangerous code patterns (see Section 8)
7. **Module load test** — Try importing the module and check for a ContentPlugin subclass

Only after validation passes and the user clicks "Import" is the plugin copied to the
plugin directory.

---

## 8. Security

### 8.1 Static Scanning

The following dangerous patterns are scanned in the plugin source code during import:

| Pattern | Description |
|---------|-------------|
| `os.system` / `os.popen` | System command execution |
| `subprocess.Popen` / `run` / `call` | Subprocess execution |
| `eval(` / `exec(` | Dynamic code execution |
| `__import__` | Dynamic import |
| `ctypes.CDLL` / `WinDLL` / `windll` | DLL loading |
| `os.remove` / `shutil.rmtree` | File/directory deletion |
| `open(` | File operations |
| `socket.socket` | Raw network communication |

> Detected patterns display a **warning** but **do not block import**.
> For personal-use plugins, the user is responsible.

### 8.2 Error Isolation

- All plugin method calls are wrapped in `try/except`
- Plugin crashes do not affect the main program or other plugins
- After 5 consecutive collection failures, the plugin is **automatically disabled**
- Disabled plugins show empty slots without affecting other slots

### 8.3 Shared Repository Review

If you plan to publish a plugin to the official shared repository, it must undergo
manual review:
- Submit the plugin source code for static scanning and behavior analysis
- Only after review passes will it be published to the repository
- Repository-listed plugins display a ✅ verified badge on import

---

## 9. Plugin Storage Location

Installed plugins are stored in the user data directory:

```
%LOCALAPPDATA%\MyDesktopApp\DesktopWidget\plugins\
    sunrise_sunset\
        plugin.json
        sunrise_sunset.py
    battery_plus\
        plugin.json
        battery_plus.py
```

- Same level as the user themes directory (`skins/`)
- Shared between MSIX Store version and exe version
- Deleting a plugin removes its subdirectory

---

## 10. Appendix

### 10.1 ContentPlugin Method Quick Reference

| Method | When Called | Parameters | Returns | Required |
|--------|-------------|------------|---------|:--------:|
| `collect(context)` | Periodic collection | PluginContext | dict | ✅ |
| `render_short(data, i18n)` | Dial repaint | dict, dict | str or list[str] | ✅ |
| `render_detail(data, is_pro, i18n)` | Mouse hover | dict, bool, dict | list[str] | ✅ |
| `render_taskbar(data, i18n)` | Taskbar refresh | dict, dict | str | ⬜ |

### 10.2 Debugging Tips

- Use `print()` in `collect()` for debug output; it will appear in the console
- If a plugin doesn't display, check the "Manage Plugins" list to see if it exists
  and is enabled
- If a slot is empty, check whether `render_short()` returns an empty string
- If hover shows no detail, check whether `render_detail()` returns an empty list

### 10.3 FAQ

**Q: Can I change the plugin key?**
A: No. The key is the basis for users' saved slot configurations; changing it will
invalidate their saved settings.

**Q: Can plugins use requests to access the network?**
A: Yes. Plugins run in the main process and can import any installed third-party
library. However, network requests should be placed in `collect()` (called
periodically in the background), not in `render_*()` (called frequently).

**Q: Can plugins access the MainWindow instance?**
A: Not directly. Use `PluginContext` to access user configuration and basic
capabilities. If you need more data, declare it in `plugin.json`; future versions
will expand Context capabilities.

**Q: Can one ZIP contain multiple plugins?**
A: No. Each ZIP corresponds to one plugin. Multiple plugins should be packaged and
imported separately.

---

> This document is based on DesktopWidget v1.6.0 source code. For questions, please
> refer to the source code or contact the project maintainer.
