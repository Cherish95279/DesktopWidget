# -*- coding: utf-8 -*-
"""
DesktopWidget 匿名设备统计客户端

新版统计上报字段：

- uuid
- version
- distribution
- os
- autostart
- theme
- weather
- update
- lang
- screen
- hover
- slots
- uptime

共 13 个字段。

国家/地区由服务器根据请求 IP 判断。
活跃时间由服务器根据请求时间判断。
"""

import string
import urllib.parse
import urllib.request
import uuid
import platform
import time
import ctypes

from PyQt6.QtCore import QSettings


# ============================================================
# 程序启动时间
# ============================================================

_PROCESS_START_TIME = time.monotonic()


# ============================================================
# UUID
# ============================================================

def get_or_create_uuid():
    """获取或创建匿名设备标识"""

    settings = QSettings(
        "MyDesktopApp",
        "WeatherSettings"
    )

    device_uuid = settings.value(
        "device_uuid",
        ""
    )

    if not device_uuid:
        device_uuid = str(uuid.uuid4())

        settings.setValue(
            "device_uuid",
            device_uuid
        )

        settings.sync()

    return device_uuid


# ============================================================
# 发行渠道
# ============================================================

def get_distribution():
    """
    判断当前程序是 Microsoft Store 版还是 EXE 安装版。

    Windows AppModel：
    - Store/MSIX：当前进程属于 Package
    - 普通 EXE：ERROR_NO_PACKAGE
    """

    try:
        kernel32 = ctypes.windll.kernel32

        ERROR_NO_PACKAGE = 15700

        length = ctypes.c_uint32(0)

        result = kernel32.GetCurrentPackageFullName(
            ctypes.byref(length),
            None
        )

        if result != ERROR_NO_PACKAGE:
            return "store"

    except Exception:
        pass

    return "exe"


# ============================================================
# 操作系统
# ============================================================

def get_os_info():
    """获取 Windows 操作系统版本"""

    try:
        system = platform.system()
        release = platform.release()

        return f"{system} {release}"

    except Exception:
        return "unknown"


# ============================================================
# 开机自启
# ============================================================

def get_autostart_status():
    """获取开机自启状态"""

    try:
        from src.autostart import (
            get_autostart_status as _get_status
        )

    except ImportError:

        try:
            from .autostart import (
                get_autostart_status as _get_status
            )

        except ImportError:
            return False

    try:
        return _get_status()

    except Exception:
        return False


# ============================================================
# 当前主题
# ============================================================

def get_current_theme():
    """
    获取当前主题。

    统计统一使用中文名称。
    """

    try:
        from .theme_manager import get_theme_manager

        manager = get_theme_manager()

        folder = manager.get_theme_folder()

        theme_map = {
            "default": "默认主题",
            "skins_01": "竹林",
            "skins_02": "赛博风",
        }

        return theme_map.get(
            folder,
            folder
        )

    except Exception:
        return "未知"


# ============================================================
# 当前语言
# ============================================================

def get_language():
    """
    获取当前界面语言。

    无论当前界面使用什么语言，
    上报统一使用中文名称。
    """

    try:
        settings = QSettings(
            "MyDesktopApp",
            "WeatherSettings"
        )

        lang_code = settings.value(
            "language",
            ""
        )

        if not lang_code:

            from .i18n.translations import (
                TranslatorManager
            )

            lang_code = (
                TranslatorManager()
                .current_language()
            )

        lang_map = {
            "zh_CN": "简体中文",
            "zh_TW": "繁体中文",
            "en": "英语",
            "ja": "日语",
            "ko": "韩语",
            "es": "西班牙语",
            "fr": "法语",
            "de": "德语",
        }

        return lang_map.get(
            lang_code,
            "未知"
        )

    except Exception:
        return "未知"


# ============================================================
# 屏幕分辨率
# ============================================================

def get_screen_resolution():
    """获取主屏幕分辨率"""

    try:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()

        if app:

            screen = app.primaryScreen()

            if screen:

                size = screen.size()

                return (
                    f"{size.width()}x"
                    f"{size.height()}"
                )

    except Exception:
        pass

    return "unknown"


# ============================================================
# 8 个信息槽位
# ============================================================

def get_slot_config():
    """
    获取 8 个信息槽位配置。

    统计统一使用中文名称。
    """

    try:

        settings = QSettings(
            "MyDesktopApp",
            "WeatherSettings"
        )

        slot_name_map = {

            "ip": "IP",
            "weather": "天气",
            "netspeed": "网速",
            "cpu": "CPU",
            "gpu": "GPU",
            "resolution": "分辨率",
            "refresh_rate": "刷新率",
            "memory": "内存",
            "date": "日期",
            "lunar": "农历",
            "term": "节气",
            "uptime": "运行时间",
            "disk_total": "磁盘总容量",
        }

        # disk_A ~ disk_P
        for letter in string.ascii_uppercase[:16]:

            slot_name_map[
                f"disk_{letter}"
            ] = f"{letter}盘"

        slots = []

        for i in range(1, 9):

            key = f"slot_{i}"

            value = settings.value(
                key,
                ""
            )

            if value and value != "empty":

                display = slot_name_map.get(
                    value,
                    value
                )

                slots.append(display)

            else:
                slots.append("空")

        return ",".join(slots)

    except Exception:
        return "unknown"


# ============================================================
# 悬停显示
# ============================================================

def get_hover_status():
    """获取悬停详细信息开关"""

    try:

        settings = QSettings(
            "MyDesktopApp",
            "WeatherSettings"
        )

        enabled = settings.value(
            "hover_enabled",
            True,
            type=bool
        )

        return "1" if enabled else "0"

    except Exception:
        return "0"


# ============================================================
# 运行时长
# ============================================================

def get_uptime():
    """
    获取本次程序运行时间。

    单位：秒
    """

    try:

        seconds = int(
            time.monotonic()
            - _PROCESS_START_TIME
        )

        return max(seconds, 0)

    except Exception:
        return 0


# ============================================================
# 完整上报
# ============================================================

def report_launch_full(
    weather_status: str = "idle",
    update_status: str = "idle",
):
    """
    完整匿名上报。

    上报时机由 MainWindow 控制。
    """

    try:

        # ----------------------------------------------------
        # 收集数据
        # ----------------------------------------------------

        uuid_val = get_or_create_uuid()

        from .constants import VERSION

        version = VERSION

        distribution = get_distribution()

        os_info = get_os_info()

        autostart = (
            "1"
            if get_autostart_status()
            else "0"
        )

        theme = get_current_theme()

        language = get_language()

        screen_resolution = (
            get_screen_resolution()
        )

        hover = get_hover_status()

        slots = get_slot_config()

        uptime = get_uptime()


        # ----------------------------------------------------
        # 构建参数
        # ----------------------------------------------------

        params = {

            "uuid": uuid_val,

            "version": version,

            "distribution": distribution,

            "os": os_info,

            "autostart": autostart,

            "theme": theme,

            "weather": weather_status,

            "update": update_status,

            "lang": language,

            "screen": screen_resolution,

            "hover": hover,

            "slots": slots,

            "uptime": uptime,
        }


        # ----------------------------------------------------
        # URL 编码
        # ----------------------------------------------------

        query = urllib.parse.urlencode(
            params,
            safe=""
        )


        # ----------------------------------------------------
        # 构建 URL
        # ----------------------------------------------------

        url = (
            "https://cherish9527.cc.cd/ping?"
            + query
        )


        # ----------------------------------------------------
        # 发送请求
        # ----------------------------------------------------

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                    "DesktopWidget/1.0"
            },
        )

        with urllib.request.urlopen(
            req,
            timeout=3
        ) as response:

            response.read()


    except Exception:
        # 统计系统绝不能影响主程序
        pass