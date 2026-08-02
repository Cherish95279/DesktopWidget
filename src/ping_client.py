# -*- coding: utf-8 -*-
"""
匿名设备统计客户端
用于在程序启动时上报以下信息到手机服务器：
- UUID（匿名设备标识）
- 版本号
- 操作系统版本
- 是否开机自启
- 当前使用的主题
- 天气 API 请求状态（本次启动以来）
- 更新检查结果（本次启动）
"""

import uuid
import platform
import urllib.request
from PyQt6.QtCore import QSettings, QTimer


def get_or_create_uuid():
    """获取或创建匿名设备标识（存储在 QSettings 中）"""
    settings = QSettings("MyDesktopApp", "WeatherSettings")
    device_uuid = settings.value("device_uuid", "")
    if not device_uuid:
        device_uuid = str(uuid.uuid4())
        settings.setValue("device_uuid", device_uuid)
        settings.sync()
    return device_uuid


def get_os_info():
    """获取操作系统信息"""
    system = platform.system()      # Windows / Linux / Darwin
    release = platform.release()    # 10 / 11 / 22.04 等
    return f"{system} {release}"

def get_autostart_status():
    """获取开机自启状态"""
    try:
        from src.autostart import get_autostart_status as _get_status
    except ImportError:
        try:
            from .autostart import get_autostart_status as _get_status
        except ImportError:
            return False
    try:
        return _get_status()
    except Exception:
        return False


def get_current_theme():
    """获取当前主题名称（始终返回简体中文，不受语言影响）"""
    try:
        from .theme_manager import get_theme_manager
        manager = get_theme_manager()
        folder = manager.get_theme_folder()
        theme_map = {
            "default": "默认主题",
            "skins_01": "竹林",
            "skins_02": "赛博风",
        }
        return theme_map.get(folder, folder)
    except Exception:
        return "未知"


def report_launch():
    """
    上报启动事件（同步请求，但会放在单独线程中调用）
    收集所有数据后一次性发送
    """
    try:
        # 基础数据
        uuid_val = get_or_create_uuid()
        from .constants import VERSION
        version = VERSION

        # A1: 操作系统版本
        os_info = get_os_info()

        # A3: 是否开机自启
        autostart = "1" if get_autostart_status() else "0"

        # A4: 当前主题
        theme = get_current_theme()

        # ===== B2: 天气状态（需要通过主窗口获取） =====
        # 这里无法直接获取，由调用方通过参数传入，或通过全局方式获取
        # 我们采用延迟获取方式：在 widget.py 中调用时传入
        # 但为了保持 ping_client 的独立性，设计为在 widget.py 中获取后传入
        # 这里的 report_launch 将被扩展为接受额外参数

        # 构建 URL（不含天气和更新状态，由调用方补充）
        url = (
            f"https://cherish9527.cc.cd/ping"
            f"?uuid={uuid_val}"
            f"&version={version}"
            f"&os={os_info}"
            f"&autostart={autostart}"
            f"&theme={theme}"
        )
        # 发送 GET 请求，超时 3 秒
        print(f"[PING] URL: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "DesktopWidget/1.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            response.read()
    except Exception:
        # 静默失败，不影响主程序
        pass



def get_language():
    """获取当前语言设置"""
    try:
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        return settings.value("language", "") or "auto"
    except Exception:
        return "unknown"


def get_screen_resolution():
    """获取主屏幕分辨率"""
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QScreen
        app = QApplication.instance()
        if app:
            screen = app.primaryScreen()
            if screen:
                size = screen.size()
                return f"{size.width()}x{size.height()}"
    except Exception:
        pass
    return "unknown"


def get_slot_config():
    """获取8个槽位的配置（逗号分隔）"""
    try:
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        slots = []
        for i in range(1, 9):
            key = f"slot_{i}"
            val = settings.value(key, "")
            slots.append(val if val else "empty")
        return ",".join(slots)
    except Exception:
        return "unknown"

def report_launch_full(
    weather_status: str = "idle",
    update_status: str = "idle"
):
    """
    完整上报（包含天气和更新状态）
    由 widget.py 在获取到主窗口实例后调用
    """
    try:
        uuid_val = get_or_create_uuid()
        from .constants import VERSION
        version = VERSION

        os_info = get_os_info()
        autostart = "1" if get_autostart_status() else "0"
        theme = get_current_theme()

        # 对特殊字符进行 URL 编码
        import urllib.parse
        os_encoded = urllib.parse.quote(os_info)
        theme_encoded = urllib.parse.quote(theme)
        lang_encoded = urllib.parse.quote(get_language())
        res_encoded = urllib.parse.quote(get_screen_resolution())
        slot_encoded = urllib.parse.quote(get_slot_config())

        url = (
            f"https://cherish9527.cc.cd/ping"
            f"?uuid={uuid_val}"
            f"&version={version}"
            f"&os={os_encoded}"
            f"&autostart={autostart}"
            f"&theme={theme_encoded}"
            f"&weather={weather_status}"
            f"&update={update_status}"
            f"&lang={lang_encoded}"
            f"&screen={res_encoded}"
            f"&slots={slot_encoded}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "DesktopWidget/1.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            response.read()
    except Exception:
        # 静默失败
        pass


def report_launch_async():
    """异步上报（在 Qt 事件循环中延迟执行，不阻塞 UI）"""
    QTimer.singleShot(100, report_launch)

def start_periodic_report(main_window):
    def _do_report():
        try:
            ws = main_window.get_weather_status() if main_window else "idle"
            us = main_window.get_update_status() if main_window else "idle"
            report_launch_full(ws, us)
        except Exception:
            pass
    timer = QTimer()
    timer.setInterval(30 * 60 * 1000)
    timer.timeout.connect(_do_report)
    timer.start()


