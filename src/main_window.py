import sys
import os
import subprocess
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from .threads import ServerScanner, NetSpeedThread
from .tray_icon import TrayIcon
from .updater import is_store_version
from .theme_manager import get_theme_manager
from .i18n.translations import TranslatorManager
from .widgets.notice_bubble import NoticeBubble
from .taskbar_widget import TaskbarWidget
from .main_window_parts.painter import PaintMixin
from .main_window_parts.perf import PerfMixin
from .main_window_parts.weather import WeatherMixin
from .main_window_parts.lifecycle import LifecycleMixin
from .main_window_parts.services import ServicesMixin

_GPU_AVAILABLE = True  # 假设存在，加载失败时置0

try:
    from zhdate import ZhDate

    LUNAR_AVAILABLE = True
except ImportError:
    LUNAR_AVAILABLE = False

# ===== 打包后强制隐藏所有子进程窗口 =====
if sys.platform == 'win32' and getattr(sys, 'frozen', False):
    _original_popen = subprocess.Popen


    def _popen_no_window(*args, **kwargs):
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = kwargs.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
        return _original_popen(*args, **kwargs)


    subprocess.Popen = _popen_no_window


# ---------- 主窗口 ----------
class MainWindow(PaintMixin, PerfMixin, WeatherMixin, LifecycleMixin, ServicesMixin, QWidget):
    def __init__(self):
        super().__init__()

        # ===== 开机自启初始化（首次运行默认开启） =====
        # 延后到事件循环启动后执行：MSIX 首次启动需 request_enable_async 同步等待
        # WinRT 异步，在 __init__ 里执行会阻塞主线程，赶在任务栏窗口嵌入完成前
        # 打乱 SetParent/SetWindowPos 时序，导致信息条落点错位（仅首次启动复现）。
        QTimer.singleShot(1000, self._init_autostart)
        TranslatorManager().init_translator(QApplication.instance())
        TranslatorManager().on_language_changed(self._on_language_changed)
        self._init_i18n()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnBottomHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._exiting = False
        self.settings_dialog = None
        self._notice_window = None

        # ===== 新增：显式初始化更新检查状态（确保存在） =====
        self.update_check_status = "idle"

        # ===== 匿名统计上报 =====
        self._initial_ping_sent = False

        # 等待天气和更新检查完成后进行第一次完整上报
        self._initial_ping_timer = QTimer(self)
        self._initial_ping_timer.timeout.connect(self._check_initial_ping_ready)
        self._initial_ping_timer.start(1000)

        # 第一次完整上报完成后，每30分钟上报一次
        self._ping_timer = QTimer(self)
        self._ping_timer.timeout.connect(self._periodic_ping)

        # 主题管理器
        self.theme_manager = get_theme_manager()

        # ===== 加载图片（通过主题管理器） =====
        self._load_images()
        self.hand_px = 199
        self.hand_py = 143
        self._apply_hand_pivot()

        # ===== 缓存处理后的背景图 =====
        self._cached_bg = None
        self._cached_theme_color = None
        self._cached_theme_opacity = None
        self._cached_tint_alpha = None

        self.setFixedSize(400, 297)
        self.drag_pos = None

        # 数据
        self.cpu = 0
        self.gpu = 0
        self.gpu_mem_used = 0
        self.gpu_mem_total = 0
        self.gpu_clock = 0
        self.gpu_power = 0
        self.mem = 0
        self.local_ip = self.get_local_ip()
        self.public_ip = ""
        self.server_ip = "扫描中..."
        self.weather = {"city": "--", "weather": "--", "temp": "--", "wind": ""}

        self.disk_usage = {}
        self.uptime = ""
        self._uptime_seconds = 0
        self.down_speed = 0.0
        self.up_speed = 0.0
        self.total_recv = 0
        self.total_sent = 0
        self.refresh_rate = 0
        self.now = datetime.now()
        self.lunar_text = ""
        self.term_display = ""

        # 加载状态
        self._loading_weather = False
        self._loading_dots = 0
        self._loading_timer = None

        # API 配置状态
        self._api_configured = True

        # 绘制相关
        self._init_paint()

        # 天气线程
        self.weather_thread = None
        self.start_weather_thread()

        # 定时器
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(50)

        self.perf_timer = QTimer()
        self.perf_timer.timeout.connect(self.update_perf)
        self.perf_timer.start(5000)

        self.net_thread = NetSpeedThread()
        self.net_thread.speed_updated.connect(self.on_speed_update)
        self.net_thread.start()

        self.scanner = ServerScanner()
        self.scanner.ip_found.connect(lambda ip: setattr(self, 'server_ip', ip))
        self.scanner.start()

        # MSIX 版检测：如果是商店版，强制设置更新渠道为 store
        if is_store_version():
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            settings.setValue("update_channel", "store")
            settings.sync()

        # 延迟获取公网 IP
        QTimer.singleShot(2000, self._fetch_public_ip)

        self.tray = TrayIcon(self)
        self.tray.show()
        # hover detail popup
        self._init_detail_popup()

        # 公告气泡
        self.notice_bubble = NoticeBubble(self)
        self.notice_bubble.move(
            self.width() - self.notice_bubble.width() - 15,
            self.height() - self.notice_bubble.height() - 1
        )
        self.notice_bubble.set_on_click(self._on_bubble_clicked)
        self.notice_bubble.raise_()

        # 任务栏显示窗口（显示状态由 tray_icon._load_taskbar_visible 统一控制）
        self.taskbar_widget = TaskbarWidget(self, tray_menu=self.tray.menu if self.tray else None)
        # taskbar_widget 创建后再恢复显示状态（时序依赖）
        if self.tray:
            self.tray._load_taskbar_visible()

        # 自动更新
        self.update_checker = None
        self.has_update = False
        self.latest_version_info = {}
        QTimer.singleShot(3000, self.check_for_updates_auto)
        # 每4小时自动检查一次更新
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self.check_for_updates_auto)
        self._update_timer.start(4 * 60 * 60 * 1000)

        # 应用主题缓存
        self.update_theme_cache()

        self.update_perf()
        self.update_clock()
        self.move_to_top_right()
        if getattr(self.tray, "_main_window_visible", True):
            self.show()

        # 延迟修复桌面快捷方式（MSIX 版本更新后路径失效问题）
        QTimer.singleShot(2000, self._fix_shortcut)

    def _fix_shortcut(self):
        """检测并修复桌面快捷方式（MSIX 版本更新后路径失效问题）。"""
        try:
            from .shortcut_fixer import fix_desktop_shortcut
            fix_desktop_shortcut()
        except Exception:
            pass

    def _init_autostart(self):
        """开机自启初始化（延迟执行，避免阻塞任务栏嵌入）。"""
        try:
            from .autostart import set_autostart, get_autostart_detail
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            autostart_on = settings.value("autostart", True, type=bool)
            detail = get_autostart_detail()
            # 仅在“应用还能控制”且当前未开启时尝试开启，
            # DisabledByUser 时 request_enable_async 不会再弹提示，跳过避免空跑
            if autostart_on and detail["available"] and not detail["enabled"] and not detail["blocked_by_user"]:
                set_autostart(True)
                detail = get_autostart_detail()
            # 同步缓存到系统真实状态，避免 QSettings 与系统脱节
            if detail["available"]:
                settings.setValue("autostart", detail["enabled"])
                settings.sync()
        except Exception:
            pass

    # ===== 新增：获取天气状态（供 ping_client 调用） =====
    def get_weather_status(self) -> str:
        """返回本次启动以来的天气请求状态"""
        if self.weather_thread is not None:
            return getattr(self.weather_thread, "last_status", "idle")
        return "idle"

    # ===== 新增：获取更新检查状态（供 ping_client 调用） =====
    def get_update_status(self) -> str:
        """返回本次启动的更新检查状态"""
        return getattr(self, "update_check_status", "idle")

    def _on_language_changed(self, lang_code):
        """语言切换回调，重新计算翻译并刷新界面"""
        self._refresh_i18n()
        # 重新扫描主题（刷新主题显示名）
        self.theme_manager.rescan_themes()
        # 重建设置对话框（如果打开着）
        if self.settings_dialog is not None:
            try:
                self.settings_dialog.rebuild_all_pages()
            except Exception:
                pass
        self.tray._refresh_menu()
        if self._notice_window is not None and self._notice_window.isVisible():
            try:
                self._notice_window.retranslate_ui()
            except Exception:
                pass
        if hasattr(self, 'taskbar_widget') and self.taskbar_widget:
            self.taskbar_widget.retranslate_ui()
        self.update()

    def _init_i18n(self):
        """预计算所有 paintEvent 中使用的翻译字符串"""
        t = TranslatorManager().translate
        self._i18n = {
            "unknown_location": t("MainWindow", "未知地区"),
            "memory": t("MainWindow", "内存"),
            "set_api": t("MainWindow", "设置API"),
            "loading": t("MainWindow", "加载中"),
            "weekdays": [t("MainWindow", d) for d in ["一", "二", "三", "四", "五", "六", "日"]],
            "week": t("MainWindow", "星期"),
            "lunar": t("MainWindow", "农历"),
            "lunar_error": t("MainWindow", "农历错误"),
            "not_installed": t("MainWindow", "未安装"),
            "distance": t("MainWindow", "距"),
            "days_until": t("MainWindow", "离"),
            "days_left": t("MainWindow", "还有"),
            "day_unit": t("MainWindow", "天"),
            "disk_total": t("MainWindow", "磁盘总计"),
            "run_prefix": t("MainWindow", "运行"),
            "min_unit": t("MainWindow", "分钟"),
            "hour_unit": t("MainWindow", "小时"),
            "month_unit": t("MainWindow", "月"),
        }

    def _refresh_i18n(self):
        """重新计算翻译字符串（语言切换时调用）"""
        t = TranslatorManager().translate
        self._i18n["unknown_location"] = t("MainWindow", "未知地区")
        self._i18n["memory"] = t("MainWindow", "内存")
        self._i18n["set_api"] = t("MainWindow", "设置API")
        self._i18n["loading"] = t("MainWindow", "加载中")
        self._i18n["weekdays"] = [t("MainWindow", d) for d in ["一", "二", "三", "四", "五", "六", "日"]]
        self._i18n["week"] = t("MainWindow", "星期")
        self._i18n["lunar"] = t("MainWindow", "农历")
        self._i18n["lunar_error"] = t("MainWindow", "农历错误")
        self._i18n["not_installed"] = t("MainWindow", "未安装")
        self._i18n["distance"] = t("MainWindow", "距")
        self._i18n["days_until"] = t("MainWindow", "离")
        self._i18n["days_left"] = t("MainWindow", "还有")
        self._i18n["day_unit"] = t("MainWindow", "天")
        self._i18n["disk_total"] = t("MainWindow", "磁盘总计")
        self._i18n["run_prefix"] = t("MainWindow", "运行")
        self._i18n["min_unit"] = t("MainWindow", "分钟")
        self._i18n["hour_unit"] = t("MainWindow", "小时")
        self._i18n["month_unit"] = t("MainWindow", "月")

    # ---------- hover detail popup ----------
    # ---------- GPU 读取（使用 ctypes 直接调用 NVML） ----------
    # ---------- hover detail popup ----------
