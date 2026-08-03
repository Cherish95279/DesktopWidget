# 📝 Changelog

All notable changes to DesktopWidget are documented in this file.

> Chinese version:
> [CHANGELOG_CN.md](CHANGELOG_CN.md)

---

# 🚀 v1.3.6 (2026-08-03)

## 🏪 Microsoft Store Release

- DesktopWidget is officially released on the Microsoft Store.
- Added an official Microsoft Store distribution channel for easier access to the latest version.
- Supports Microsoft Store update mechanisms, providing a more convenient and reliable installation and update experience.

## 🎨 Interface & Visual Experience Improvements

- Improved pointer rotation effects for smoother animations and a better visual experience.
- Added a new Cyber theme, bringing a futuristic visual style to the desktop widget.
- Added desktop display icon support, improving usability and application recognition.

## ⚙️ Startup & Runtime Improvements

- Optimized Windows startup behavior to improve application launch stability.
- Improved the startup process and reduced potential issues during initialization.

## 🐛 Stability Improvements

- Fixed various minor issues.
- Improved overall application stability and user experience.

---

---

# 🚀 v1.3.3 (2026-07-24)

## 🔔 Notification and Update Reminder Improvements

- Added a more noticeable arrival notification indicator.
- Added a more noticeable update release reminder indicator.
- Both indicators are now displayed as small red and green dots on the system tray icon for quick recognition.

## 🌍 Localization Improvements

- Fixed an issue where weather information and the main interface language could become inconsistent in extremely rare cases.
- Fixed the default language display logic during application startup.
- Improved language initialization and display consistency.

## 🐛 Bug Fixes

- Fixed other minor logic issues.
- Improved overall application stability.

---

---

# 🚀 v1.3.2 (2026-07-22) 

## 🌍 Localization and Region Display Improvements

- Fixed an issue where weather location search results were displayed in only one language.
- Improved weather location display logic to show region names according to the current language setting.
- Chinese names are now displayed by default for Greater China regions without requiring manual language switching.
- Improved consistency across all 8 supported languages.

## 📅 Lunar Calendar and Solar Terms Improvements

- Separated lunar calendar and solar terms into independent display items.
- Lunar calendar and solar terms can now be added separately to the display item pool and freely arranged.

## 🐛 Bug Fixes

- Fixed an issue where weather location names in the main window were displayed using the API default language.
- Fixed other known logic issues and improved overall stability.

---

# 🚀 v1.3.1 (2026-07-20)

## 🌤️ Weather System Improvements

- Added 3 new weather service options.

- Changed the default weather provider from Amap Weather to Open-Meteo.

- Open-Meteo does not require an API Key.
  The service URL is built into the application.

- Added support for:

  - Open-Meteo
  - Weather API
  - QWeather


All supported weather services now provide global weather data.


---

## 🌍 Localization Improvements

- All newly added user-visible text has been translated.

- DesktopWidget now supports 8 languages:

  - Simplified Chinese
  - Traditional Chinese
  - English
  - Japanese
  - Korean
  - German
  - French
  - Spanish


---

## 🌐 Weather Location Search Improvements

Improved the weather location configuration system.

Changes:

- Removed the previous province / city / district selection method.

- Added a unified search box.

The location search system combines:

- Local region database (priority for China regions)
- Online search service (when local matching fails)

Additional improvements:

- Supports multilingual location search.


---

## 🔑 API Configuration Improvements

Added API Key display options:

- Plain text display
- Masked display


Improved service instructions:

- Help text dynamically changes according to the selected weather service.

- Help information follows the current interface language.

- If an API Key is required, users can directly open the registration link from the help text.


---

# 🚀 v1.3.0 (2026-07-10)

## 🌍 Multi-language Expansion

Added:

- French (Français)
- Korean (한국어)


Translation system improvements:

- Rebuilt the localization framework.
- Uses a dual translation system:
  - Built-in dictionary
  - QTranslator


Language switching:

- Requires application restart after changing language.
- All user interface text has been translated.


---

## 🌐 Global Weather Location Search

Removed the previous:

```
Province → City → District/County
```

three-level selection system.


Added:

- Global city search.
- Multilingual input support including Chinese, English and Japanese.


Location search system:

### China regions

- Uses local `china_regions.json` database first.


### International regions

- Uses Open-Meteo Geocoding API.

Features:

- Free to use.
- No API Key required.


Weather requests:

- Changed to latitude and longitude based queries.
- Supports weather data for any location worldwide.


Display optimization:

- Weather location display now uses a shorter format.

Example:

```
Yanjin County
```

to reduce occupied space.


---

## 📢 Announcement System Improvements

Added:

- Dual-source announcement checking:
  - GitHub
  - Gitee

Domestic users can receive update announcements without proxy access.


Improved announcement window:

- Removed dates from the left announcement list.
- Only displays announcement titles.
- Simplified interface layout.


Improved timestamp display:

- Increased font size.
- Increased contrast.
- Improved readability.


---

## 🖥️ Settings Window Improvements

Fixed:

- Incorrect minimize button behavior.

Changes:

- Restored the system title bar.
- Removed the custom title bar design to avoid possible crashes.

Improved:

- General settings page layout.
- Language selector alignment with window mode options.


---

## 🐛 Other Fixes

Fixed:

- GPU detection failure after packaging.

Solution:

- Directly call `nvml.dll` through ctypes.


Other improvements:

- Fixed settings window position issues after minimizing.
- Fixed announcement list not refreshing after data updates.
- Removed large amounts of unused imports.
- Replaced bare except statements with specific exception handling.


---

# 🚀 v1.2.8

## 🧹 Code Optimization

Removed the chat feature completely.

Deleted:

- `src/chat_client.py`
- `src/chat_window.py`
- `src/settings_pages/chat_page.py`


Restored the following modules to the non-chat version:

- `main_window.py`
- `settings_dialog.py`
- `tray_icon.py`
- `constants.py`


Other improvements:

- Cleaned unused `__pycache__` files.


Code quality improvements:

- Optimized code with assistance from Cline + DeepSeek.
- Removed unused imports (11 locations).
- Split long functions exceeding 50 lines (11 methods).
- Replaced all bare except statements with specific exception handling.


---

## ⚙️ Settings Window UI Improvements

Added:

- Custom title bar minimize button.


Unified:

- Title bar hover effects.
- Light gray hover feedback.


Updated colors:

Title bar:

```text
#e6f4ff
```

Navigation bar:

```text
#f5f6fa
```


Other changes:

- Disabled maximize button.
- Completely removed maximize functionality.


---

## 🛠️ VSCode Debug Configuration

Added:

- `launch.json` debugging configuration.


Features:

- Press F5 to automatically terminate old processes.
- Automatically restart `widget.py`.


Added:

- `preLaunchTask` for automatic process cleanup.


---

# 🚀 v1.2.7 (2026-07-04)

## 🎨 UI Consistency Improvements

Unified the style of all settings pages:

- Combo boxes
- Input fields
- Buttons
- Sliders


All controls now share a consistent visual style.


---

## 🎨 Theme Control Improvements

Changed theme intensity control:

Before:

- Manual input field.

After:

- Slider control.


Range:

```text
0 ~ 255
```

Values are displayed as percentage mapping.

Improved usability and interaction.


---

## 🎨 Real-time Theme Switching

Added:

- Instant theme switching.

Changes:

- Apply immediately to the main window.
- No restart required.


---

## 🐛 Bug Fixes

Fixed:

- Weather updates being triggered repeatedly when opening the weather settings page.


---

## 🔄 Update System Improvements

Added update source selection:

- Gitee
- GitHub


Default source:

- Gitee


Improves update speed for users in regions where GitHub access is slower.


---

## 📢 Announcement Improvements

Added:

- "View Announcements" button in General Settings.


Users can now:

- Check historical announcements at any time.


---

## 🎨 UI Component Standardization

Unified:

- Input field height.
- Combo box height.
- Button height.

Standard size:

```text
28px
```


Improved:

- Combo box borders.
- Background style.
- Hover effects.

Kept the native system dropdown arrow.


---

## 🧹 Code Cleanup

Removed:

- Redundant weather location selection code.

Weather location management is now handled independently.


---

# 🚀 v1.2.6 (2026-07-03)

## 🎨 Theme System

Added:

- New "Bamboo" theme.


Users can switch themes from:

```
Settings → Theme
```


---

## 🇨🇳 Gitee Update Source

Added:

- Gitee update channel.


Users can switch update sources from:

```
Settings → Check for Updates
```


Provides faster downloads for users in China.


---

## 📢 Announcement System

Added:

- "View Announcements" entry in General Settings.


Allows users to:

- Browse announcement history anytime.


---

## 🎨 Theme Settings Improvements

Improved:

- Theme switching layout.
- Background color settings layout.
- Restore default button style.


---

## 🐛 Performance Improvements

Fixed:

- Weather thread restarting unnecessarily when opening settings.


Optimized:

- Settings page loading logic.
- Reduced unnecessary network requests.


---

# 🚀 v1.2.5

## 🎨 Theme System Release

DesktopWidget officially introduced theme customization starting from v1.2.5.


### Theme Switching

Built-in themes:

- Default Theme
- Bamboo Theme


Features:

- One-click switching.
- Real-time application.


---

### Background Color

Preset options:

- Classic Dark
- Light Theme
- Light Blue Gray


Also supports:

- Custom colors.


---

### Theme Intensity

Added:

- Background color overlay control.


Range:

```text
0 ~ 255
```


Lower values:

- More transparent.
- Original image remains clearer.


Higher values:

- Stronger color overlay.


---

### Window Opacity

Supports:

```text
20% ~ 100%
```


Allows DesktopWidget to better blend with different desktop environments.


---

### Restore Default Settings

Added:

- One-click reset for all theme settings.


Other improvements:

- Theme switching applies instantly.
- No save operation required.


---

# 🚀 v1.2.3 (2026-06-28)

## 🐛 Bug Fixes

- Fixed several known issues.


## 📢 Preview

- Announced that the theme system would be introduced gradually.


---

# 🚀 v1.2.2 (2026-06-26)

## 📦 Installation Experience Improvements

- Fully localized the installer interface into Chinese.

Improved:

- Installation experience for users.


---

## 📢 Announcement Window Improvements

Optimized:

- Announcement display logic.
- Stability.
- User interaction experience.


---

## 🛠️ DevTool Developer Tools

Added an independent backend development tool.

Supports:

- One-click packaging.
- Code pushing.
- Release creation.
- Automatic EXE uploading.


Current workflow:

- GitHub upload: automatic.
- Gitee upload: manual.


---

# 🚀 v1.2.1 (2026-06-25)

## 📢 Announcement System Release

Fully released the announcement system.

Added:

- Remote announcement push.
- Popup notifications.
- Tray icon notifications.


---

## 📚 Announcement History Management

Added:

- Automatic archiving of read announcements.
- Right-click delete support.
- Clear announcement history support.


---

## 🖥️ Window Experience Improvements

Optimized:

- Instant announcement window opening.
- Background data loading without noticeable delay.


Added:

- Tray green dot notification.

When new announcements are available:

- Green dot appears.
- Automatically disappears after reading.


---

## 💬 Feedback Channel

Added:

- GitHub Discussions link in the About page.


Fixed:

- Popup notification and tray indicator not disappearing after reading announcements.


Optimized:

- Announcement window loading speed.


---

# 🚀 v1.2.0 (2026-06-24)

## 📐 Layout System Refactoring

Rebuilt the display item layout system.

Added:

- 8 customizable information slots.
- Free arrangement of displayed items.


Improved:

- Settings changes apply instantly.
- Removed the save button.


---

## 💖 Donation Support

Added:

- Donation page.

Supported:

- Alipay QR Code.
- WeChat Pay QR Code.


---

## 🐛 Bug Fixes

Fixed incorrect display positions for:

- CPU usage.
- GPU usage.
- Resolution.
- Refresh rate.


Improved:

- Left 1 / Right 1 information areas changed to two-line display.
- Main window rendering logic.


---

# 🚀 v1.1.9

## 🌅 Weather Feature Improvements

Added:

- Sunrise and sunset information.


Optimized:

- Weather thread cache mechanism.


Fixed:

- Known issues.


---

If DesktopWidget is useful to you, consider giving the project a Star ⭐ on GitHub to support continued development.