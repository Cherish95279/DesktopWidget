import sys
import os
import ctypes
import ctypes.util
import socket
import subprocess
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import psutil

from .constants import CENTER_X, CENTER_Y, DEFAULT_LAYOUT
from .utils import get_weather_icon
from .region_data import get_coords_by_name, get_coords_for_city
from .solar_terms import get_next_term_info, translate_term
from .threads import ServerScanner, WeatherThread, NetSpeedThread
from .settings_dialog import SettingsDialog
from .tray_icon import TrayIcon
from .updater import UpdateChecker, is_store_version
from .theme_manager import get_theme_manager
from .i18n.translations import TranslatorManager
from .widgets.notice_bubble import NoticeBubble
from .taskbar_widget import TaskbarWidget

# GPU支持：使用ctypes直接调用NVML
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
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # ===== 开机自启初始化（首次运行默认开启） =====
        try:
            from PyQt6.QtCore import QSettings
            from .autostart import set_autostart, get_autostart_status
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            autostart_on = settings.value("autostart", True, type=bool)
            if autostart_on and not get_autostart_status():
                set_autostart(True)
        except Exception:
            pass
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

        # 任务栏显示窗口（默认隐藏）
        self.taskbar_widget = TaskbarWidget(self, tray_menu=self.tray.menu if self.tray else None)
        taskbar_visible = QSettings("MyDesktopApp", "WeatherSettings").value("taskbar_visible", False, type=bool)
        if taskbar_visible:
            self.taskbar_widget.show()

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
        self.show()

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

    def _check_initial_ping_ready(self):
        """
        检查启动阶段的天气和更新检查是否都已经完成。

        第一次完整上报只允许执行一次。
        """
        if self._initial_ping_sent:
            return

        # --------------------------------------------------------
        # 1. 判断天气是否需要等待
        # --------------------------------------------------------

        settings = QSettings("MyDesktopApp", "WeatherSettings")

        has_weather = False

        for i in range(1, 9):
            key = f"slot_{i}"
            default_val = DEFAULT_LAYOUT.get(key, "empty")
            value = settings.value(key, default_val)

            if value == "weather":
                has_weather = True
                break

        if has_weather:
            weather_status = self.get_weather_status()

            # 天气线程还没有产生第一次结果
            if weather_status == "idle":
                return
        else:
            # 没有天气槽位，不需要等待天气
            weather_status = "not_enabled"

        # --------------------------------------------------------
        # 2. 判断更新检查是否完成
        # --------------------------------------------------------

        update_status = self.get_update_status()

        if update_status in ("idle", "checking"):
            return

        # --------------------------------------------------------
        # 3. 两项都完成
        # --------------------------------------------------------

        self._initial_ping_sent = True

        # 停止启动阶段轮询
        if self._initial_ping_timer.isActive():
            self._initial_ping_timer.stop()

        # 进行第一次完整上报
        try:
            from .ping_client import report_launch_full

            report_launch_full(
                weather_status,
                update_status
            )
        except Exception:
            pass

        # --------------------------------------------------------
        # 4. 第一次上报之后开始30分钟周期上报
        # --------------------------------------------------------

        if not self._ping_timer.isActive():
            self._ping_timer.start(30 * 60 * 1000)

    def _periodic_ping(self):
        """
        每30分钟上报一次当前状态。
        """
        try:
            from .ping_client import report_launch_full

            weather_status = self.get_weather_status()
            update_status = self.get_update_status()

            report_launch_full(
                weather_status,
                update_status
            )

        except Exception:
            pass

    def _read_refresh_rate(self):
        """读取 Windows 当前显示配置刷新率"""
        try:
            import ctypes, struct
            user32 = ctypes.windll.user32
            num_paths = ctypes.c_uint32(0)
            num_modes = ctypes.c_uint32(0)
            ret = user32.GetDisplayConfigBufferSizes(1, ctypes.byref(num_paths), ctypes.byref(num_modes))
            if ret == 0 and num_paths.value > 0:
                path_buf = (ctypes.c_ubyte * (num_paths.value * 72))()
                mode_buf = (ctypes.c_ubyte * (num_modes.value * 96))()
                actual_paths = ctypes.c_uint32(num_paths.value)
                actual_modes = ctypes.c_uint32(num_modes.value)
                ret = user32.QueryDisplayConfig(1, ctypes.byref(actual_paths), path_buf, ctypes.byref(actual_modes), mode_buf, None)
                if ret == 0:
                    for i in range(actual_paths.value):
                        num, den = struct.unpack_from('<II', path_buf, i * 72 + 48)
                        if den > 0 and num > 0:
                            return int(round(num / den))
        except Exception:
            pass
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hdc = user32.GetDC(0)
            refresh = ctypes.windll.gdi32.GetDeviceCaps(hdc, 116)
            user32.ReleaseDC(0, hdc)
            if refresh > 0:
                return refresh
        except Exception:
            pass
        return 60

    def _init_paint(self):
        """初始化屏幕信息。"""
        screen = QApplication.primaryScreen()
        self.refresh_rate = self._read_refresh_rate()
        self.screen_res = (
            f"{screen.size().width()}×{screen.size().height()}"
            if screen else "1920×1080"
        )

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

    # ===== 加载图片（通过主题管理器） =====
    def _load_images(self):
        """通过主题管理器加载当前主题的所有图片"""
        bg_path = self.theme_manager.get_theme_path("bg.png")
        face_path = self.theme_manager.get_theme_path("face.png")
        self.bg = QPixmap(bg_path) if bg_path and os.path.exists(bg_path) else QPixmap()
        self.face = QPixmap(face_path) if face_path and os.path.exists(face_path) else QPixmap()
        hour_path = self.theme_manager.get_theme_path("Hour_Hand.png")
        minute_path = self.theme_manager.get_theme_path("Minute_Hand.png")
        second_path = self.theme_manager.get_theme_path("Second_Hand.png")
        self.hour = QPixmap(hour_path) if hour_path and os.path.exists(hour_path) else QPixmap()
        self.minute = QPixmap(minute_path) if minute_path and os.path.exists(minute_path) else QPixmap()
        self.second = QPixmap(second_path) if second_path and os.path.exists(second_path) else QPixmap()

        # 如果 face 为空，用 bg 替代
        if self.face.isNull():
            self.face = self.bg

        # 检查关键图片是否存在
        if any(p.isNull() for p in [self.bg, self.hour, self.minute, self.second]):
            print(" 部分图片加载失败，请检查主题文件")

    def _apply_hand_pivot(self):
        """根据当前主题设置指针旋转枢轴偏移量"""
        self.hand_px = 199
        self.hand_py = 143

    def reload_images(self):
        """重新加载当前主题的所有图片（主题切换时调用）"""
        self._load_images()
        self._apply_hand_pivot()
        # 强制重建背景缓存
        self._cached_bg = None
        self.update_theme_cache(force=True)
        self.update()
        # 切换主题时立即上报
        from src.ping_client import report_launch_full
        report_launch_full("idle", "theme_switched")

    # ---------- 主题缓存 ----------
    def update_theme_cache(self, force=False):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        theme_opacity = int(settings.value("theme_opacity", 100))
        theme_color = settings.value("theme_color", "#a8c7dc")
        theme_tint_alpha = int(settings.value("theme_tint_alpha", 80))

        if not force and (self._cached_bg is not None and
                          self._cached_theme_color == theme_color and
                          self._cached_theme_opacity == theme_opacity and
                          self._cached_tint_alpha == theme_tint_alpha):
            return

        self._cached_theme_color = theme_color
        self._cached_theme_opacity = theme_opacity
        self._cached_tint_alpha = theme_tint_alpha

        if not self.bg.isNull():
            bg_pixmap = self.bg.copy()
            if not bg_pixmap.isNull():
                color = QColor(theme_color)
                color.setAlpha(theme_tint_alpha)
                temp_painter = QPainter(bg_pixmap)
                temp_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
                temp_painter.fillRect(bg_pixmap.rect(), color)
                temp_painter.end()
                self._cached_bg = bg_pixmap
            else:
                self._cached_bg = self.bg
        else:
            self._cached_bg = QPixmap(400, 297)
            self._cached_bg.fill(QColor(theme_color))

        self.update()

    # ---------- 以下方法保持原样（从原 main_window.py 保留） ----------
    def move_to_top_right(self):
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.right() - self.width() - 100
            y = geometry.top() + 150
            self.move(x, y)

    def _on_bubble_clicked(self):
        self._acknowledge_notice()

    def _acknowledge_notice(self):
        """统一处理公告确认：停止所有闪烁，打开公告窗口"""
        # 停止气泡闪烁
        if hasattr(self, 'notice_bubble') and self.notice_bubble:
            self.notice_bubble.hide_bubble()
        # 停止托盘闪烁
        if hasattr(self, 'tray') and self.tray:
            self.tray._stop_flash()
            self.tray._green_dot_visible = False
            self.tray._notice_opened = True
            QTimer.singleShot(10, lambda: self.tray.setIcon(self.tray._default_icon))
            self.tray._update_tooltip()
        # 打开公告窗口
        self._open_notice_window()

    def _open_notice_window(self):
        from .notice import NoticeWindow, NoticeManager
        if self._notice_window is not None and self._notice_window.isVisible():
            self._notice_window.raise_()
            self._notice_window.activateWindow()
            return
        QTimer.singleShot(200, self._create_notice_window)

    def _create_notice_window(self):
        from .notice import NoticeWindow, NoticeManager
        self._notice_window = NoticeWindow(self)
        self._notice_window.destroyed.connect(self._on_notice_window_destroyed)
        manager = NoticeManager.get_instance()
        current_notice = manager.get_current_notice()
        if current_notice:
            notice_id = current_notice.get("id")
            if notice_id:
                QTimer.singleShot(300, lambda: self._notice_window.select_notice_by_id(
                    notice_id) if self._notice_window else None)
        self._notice_window.show()

    def _on_notice_window_destroyed(self):
        self._notice_window = None

    def open_settings(self, initial_page="general"):
        if self.settings_dialog is not None and self.settings_dialog.isVisible():
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            if hasattr(self.settings_dialog, 'switch_page'):
                page_index = {"general": 0, "display": 1, "weather": 2, "theme": 3, "update": 4, "donation": 5,
                              "about": 6}.get(initial_page, 0)
                self.settings_dialog.switch_page(page_index)
            return
        try:
            dialog = SettingsDialog(self, initial_page=initial_page)
            screen = QApplication.primaryScreen()
            if screen:
                geometry = screen.availableGeometry()
                x = geometry.right() - dialog.width() - 100
                y = geometry.bottom() - dialog.height() - 200
                if y < 0:
                    y = 0
                dialog.move(x, y)
            self.settings_dialog = dialog
            dialog.destroyed.connect(self._on_settings_closed)
            dialog.show()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开设置失败：{str(e)}")

    def _on_settings_closed(self):
        self.settings_dialog = None

    def check_for_updates_auto(self):
        if self.update_checker is not None and self.update_checker.isRunning():
            return

        settings = QSettings("MyDesktopApp", "WeatherSettings")
        channel = settings.value("update_channel", "gitee")
        if channel == "gitee":
            url = "https://gitee.com/api/v5/repos/Cherish95279/DesktopWidget/releases/latest"
            self.update_checker = UpdateChecker(url, use_token=False)
        else:
            self.update_checker = UpdateChecker()
        self.update_check_status = "checking"
        self.update_checker.check_finished.connect(self.on_update_check_finished)
        self.update_checker.start()

    def on_update_check_finished(self, result):
        if "error" in result:
            self.update_check_status = "failed"
            self.has_update = False
            return
        if result.get("has_update", False):
            self.has_update = True
            self.latest_version_info = result
            self.update_check_status = "success"
            # 通知托盘图标闪烁
            if hasattr(self, 'tray') and self.tray:
                self.tray.start_update_flash()
        else:
            self.has_update = False
            self.update_check_status = "no_update"

    def get_latest_version_info(self):
        return self.latest_version_info if self.has_update else None

    def start_loading_animation(self):
        self._loading_weather = True
        self._loading_dots = 0
        if self._loading_timer is None:
            self._loading_timer = QTimer()
            self._loading_timer.timeout.connect(self._update_loading_dots)
            self._loading_timer.start(500)
        self.update()

    def _update_loading_dots(self):
        self._loading_dots = (self._loading_dots + 1) % 4
        self.update()

    def stop_loading_animation(self):
        self._loading_weather = False
        if self._loading_timer is not None:
            self._loading_timer.stop()
            self._loading_timer = None
        self.update()

    def start_weather_thread(self, force_restart=False):
        """智能启动天气线程：根据布局配置和服务类型决定是否启动"""
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.sync()  # 确保读取最新配置

        weather_service = settings.value("weather_service", "open_meteo")
        api_url = settings.value(f"api_url_{weather_service}", "")
        api_key = settings.value(f"api_key_{weather_service}", "")
        refresh_minutes = int(settings.value("refresh_minutes", 120))
        lat = settings.value("selected_latitude", "")
        lng = settings.value("selected_longitude", "")

        print(f"🌤️ start_weather_thread 被调用，weather_service={weather_service}, force_restart={force_restart}")
        print(f"🌤️ lat={lat}, lng={lng}")

        # Open-Meteo: 尝试获取坐标（JSON 反查 > IP 定位）
        if weather_service == "open_meteo":
            if not lat or not lng:
                # 优先从本地 JSON 反查坐标（高德 IP 定位可能已写入城市名）
                city_name = settings.value("selected_city", "") or settings.value("selected_location_display", "")
                coords_from_json = False
                if city_name:
                    coords = get_coords_for_city(city_name) or get_coords_by_name(city_name)
                    if coords:
                        settings.setValue("selected_latitude", str(coords[0]))
                        settings.setValue("selected_longitude", str(coords[1]))
                        settings.setValue("location_source", "json")
                        settings.sync()
                        lat = str(coords[0])
                        lng = str(coords[1])
                        coords_from_json = True
                        print(f"🌐 从本地 JSON 推导坐标成功: {city_name} -> {coords[0]}, {coords[1]}")

                # JSON 反查失败才尝试网络 IP 定位
                if not coords_from_json:
                    ip_attempted = settings.value("_ip_attempted", False, type=bool)
                    if not ip_attempted:
                        from .utils import get_ip_location
                        print("🌐 JSON 无匹配，尝试 IP 自动定位...")
                        new_lat, new_lng, city, ip_isp = get_ip_location()
                        settings.setValue("_ip_attempted", True)
                        if new_lat and new_lng:
                            settings.setValue("_ip_attempted", True)
                            settings.setValue("selected_latitude", str(new_lat))
                            settings.setValue("selected_longitude", str(new_lng))
                            if city:
                                settings.setValue("selected_city", city)
                                settings.setValue("selected_location_display", city)
                            if ip_isp:
                                settings.setValue("ip_isp", ip_isp)
                            settings.setValue("location_source", "ip")
                            settings.sync()
                            lat = str(new_lat)
                            lng = str(new_lng)
                            print(f"🌐 IP 定位成功: {city} ({new_lat}, {new_lng})")
                        else:
                            print("🌐 IP 定位失败，请手动搜索城市")
                            settings.sync()

        # 按服务类型读取 API Key（Open-Meteo 不需要）
        if weather_service != "open_meteo":
            api_key = api_key or settings.value(f"api_key_{weather_service}", "")

        # 判断 API 是否配置完整
        if weather_service == "open_meteo":
            self._api_configured = bool(lat and lng)
        else:
            self._api_configured = bool(api_url and api_key)

        print(f"🌤️ _api_configured={self._api_configured}")

        has_weather = False
        slot_keys = ["slot_1", "slot_2", "slot_3", "slot_4", "slot_5", "slot_6", "slot_7", "slot_8"]
        for key in slot_keys:
            default_val = DEFAULT_LAYOUT.get(key, "empty")
            value = settings.value(key, default_val)
            if value == "weather":
                has_weather = True
                break

        if not has_weather:
            if self.weather_thread is not None:
                print(" 布局中未配置天气，停止天气线程")
                try:
                    self.weather_thread.data_updated.disconnect()
                    self.weather_thread.error_signal.disconnect()
                except Exception as e:
                    print(f" 断开天气线程信号时出错: {e}")
                self.weather_thread.stop()
                self.weather_thread = None
            self.stop_loading_animation()
            return

        if not self._api_configured:
            print(f"🌤️ API 未配置，跳过启动")
            if self.weather_thread is not None:
                try:
                    self.weather_thread.data_updated.disconnect()
                    self.weather_thread.error_signal.disconnect()
                except Exception as e:
                    print(f" 断开天气线程信号时出错: {e}")
                self.weather_thread.stop()
                self.weather_thread = None
            self.stop_loading_animation()
            self.update()
            return

        if self.weather_thread is not None and not force_restart:
            print(f"🌤️ 线程已运行且非强制重启，跳过")
            return

        if self.weather_thread is not None:
            print(" 断开旧天气线程信号并停止...")
            try:
                self.weather_thread.data_updated.disconnect()
                self.weather_thread.error_signal.disconnect()
            except Exception as e:
                print(f" 断开信号时出错: {e}")
            self.weather_thread.stop()
            self.weather_thread = None

        if force_restart or self.weather.get("city") == "--":
            self.start_loading_animation()

        print(" 启动新天气线程...")
        self.weather_thread = WeatherThread(api_url, api_key, refresh_minutes)
        self.weather_thread.data_updated.connect(self.update_weather)
        self.weather_thread.error_signal.connect(self.on_weather_error)
        self.weather_thread.start()
        print(f"🌤️ 线程启动状态: {self.weather_thread is not None}")

    def update_weather(self, data):
        print(f" 主窗口收到天气更新: {data.get('city')} {data.get('weather')} {data.get('temp')}℃")
        self.stop_loading_animation()
        self.weather = data
        self.update()

    def on_weather_error(self, err_msg):
        if not err_msg:  # 空字符串不打印
            return
        print(f" 天气错误: {err_msg}")

    def toggle_taskbar_window(self, visible: bool):
        """托盘右键菜单切换任务栏窗口显隐"""
        if hasattr(self, 'taskbar_widget') and self.taskbar_widget:
            if visible:
                self.taskbar_widget.show()
                self.taskbar_widget.update_position()
            else:
                self.taskbar_widget.hide()

    # ---------- hover detail popup ----------
    def _init_detail_popup(self):
        from .widgets.detail_popup import DetailPopup
        self._detail_popup = DetailPopup(self)
        self.setMouseTracking(True)
        self._last_hover_slot = None
        if hasattr(self, 'notice_bubble') and self.notice_bubble:
            self.notice_bubble.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if hasattr(self, '_detail_popup'):
            self._last_hover_slot = None
            self._detail_popup.start_fade_out(2000)

    def _get_hover_slot(self, pos):
        from PyQt6.QtCore import QSettings
        from .constants import DEFAULT_LAYOUT
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        slot_position_map = {
            "slot_1": (20, 30, 105, 43),
            "slot_2": (20, 86, 85, 43),
            "slot_3": (20, 166, 70, 50),
            "slot_4": (20, 235, 88, 50),
            "slot_5": (280, 30, 94, 43),
            "slot_6": (314, 86, 71, 43),
            "slot_7": (324, 166, 60, 50),
            "slot_8": (273, 245, 97, 52),
        }
        for slot_key in ["slot_1", "slot_2", "slot_3", "slot_4", "slot_5", "slot_6", "slot_7", "slot_8"]:
            if slot_key not in slot_position_map:
                continue
            x, y, w, h = slot_position_map[slot_key]
            rect = QRect(x, y, w, h)
            if rect.contains(pos):
                content_key = settings.value(slot_key, DEFAULT_LAYOUT.get(slot_key, "empty"))
                return (slot_key, content_key, rect)
        return None

    def closeEvent(self, event):
        if self._exiting:
            event.accept()
            return
        if self.tray.isVisible():
            self.hide()
            self.tray.showMessage(
                "珍爱桌面小工具",
                "程序已最小化到系统托盘，双击托盘图标可恢复窗口。",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
            event.ignore()
        else:
            self.shutdown()
            event.accept()

    def shutdown(self):
        """停止后台任务，避免 QApplication 退出时销毁仍在运行的 QThread。"""
        if getattr(self, "_shutdown_complete", False):
            return
        self._shutdown_complete = True

        if self._loading_timer is not None:
            self._loading_timer.stop()
        for timer_name in (
                "clock_timer",
                "perf_timer",
                "_initial_ping_timer",
                "_ping_timer",
        ):
            timer = getattr(self, timer_name, None)
            if timer is not None:
                timer.stop()

        for thread_name in ("weather_thread", "net_thread", "scanner"):
            thread = getattr(self, thread_name, None)
            if thread is not None:
                thread.stop()

        from .notice import NoticeManager
        NoticeManager.get_instance().stop()

    def get_public_ip(self):
        """获取公网 IP，多个备用接口"""
        import requests
        urls = [
            ("https://api.ipify.org?format=json", "json", "ip"),
            ("https://httpbin.org/ip", "json", "origin"),
            ("https://myip.ipip.net", "text", None),
        ]
        for url, fmt, key in urls:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    if fmt == "json":
                        return resp.json().get(key, "")
                    else:
                        # text format: "当前 IP：x.x.x.x  来自于：..."
                        text = resp.text
                        import re
                        m = re.search(r"(\d+\.\d+\.\d+\.\d+)", text)
                        if m:
                            return m.group(1)
            except Exception:
                continue
        return ""

    def _fetch_public_ip(self):
        """后台获取公网 IP"""
        ip = self.get_public_ip()
        if ip:
            self.public_ip = ip

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except (OSError, socket.error):
            return "127.0.0.1"

    def on_speed_update(self, down, up, total_recv=0, total_sent=0):
        self.down_speed = max(0, down)
        self.up_speed = max(0, up)
        self.total_recv = total_recv
        self.total_sent = total_sent
        self.update()


    # ---------- GPU 读取（使用 ctypes 直接调用 NVML） ----------
    def update_perf(self):
        try:
            self.cpu = psutil.cpu_percent()
            self.mem = psutil.virtual_memory().percent

            # GPU 读取
            try:
                # 尝试加载 nvml.dll
                nvml = ctypes.WinDLL(r"C:\Windows\System32\nvml.dll")
            except OSError:
                # 尝试用 find_library 查找
                lib_path = ctypes.util.find_library("nvml")
                if lib_path:
                    try:
                        nvml = ctypes.WinDLL(lib_path)
                    except OSError:
                        nvml = None
                else:
                    nvml = None

            if nvml:
                # 定义函数原型
                nvmlInit = nvml.nvmlInit
                nvmlInit.restype = ctypes.c_int
                nvmlDeviceGetHandleByIndex = nvml.nvmlDeviceGetHandleByIndex
                nvmlDeviceGetHandleByIndex.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)]
                nvmlDeviceGetUtilizationRates = nvml.nvmlDeviceGetUtilizationRates
                nvmlDeviceGetUtilizationRates.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]

                ret = nvmlInit()
                if ret == 0:  # NVML_SUCCESS
                    handle = ctypes.c_void_p()
                    ret = nvmlDeviceGetHandleByIndex(0, ctypes.byref(handle))
                    if ret == 0:
                        util = ctypes.c_uint()
                        ret = nvmlDeviceGetUtilizationRates(handle, ctypes.byref(util))
                        if ret == 0:
                            self.gpu = util.value
                        # GPU memory info
                        try:
                            class nvmlMemory_t(ctypes.Structure):
                                _fields_ = [("total", ctypes.c_ulonglong), ("free", ctypes.c_ulonglong), ("used", ctypes.c_ulonglong)]
                            mem_info = nvmlMemory_t()
                            nvmlDeviceGetMemoryInfo = nvml.nvmlDeviceGetMemoryInfo
                            nvmlDeviceGetMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(nvmlMemory_t)]
                            nvmlDeviceGetMemoryInfo.restype = ctypes.c_int
                            if nvmlDeviceGetMemoryInfo(handle, ctypes.byref(mem_info)) == 0:
                                self.gpu_mem_total = mem_info.total
                                self.gpu_mem_used = mem_info.used
                        except Exception:
                            pass
                        # GPU clock
                        try:
                            nvmlDeviceGetClockInfo = nvml.nvmlDeviceGetClockInfo
                            nvmlDeviceGetClockInfo.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)]
                            nvmlDeviceGetClockInfo.restype = ctypes.c_int
                            clock = ctypes.c_uint()
                            if nvmlDeviceGetClockInfo(handle, 0, ctypes.byref(clock)) == 0:
                                self.gpu_clock = clock.value
                        except Exception:
                            pass
                        # GPU power
                        try:
                            nvmlDeviceGetPowerUsage = nvml.nvmlDeviceGetPowerUsage
                            nvmlDeviceGetPowerUsage.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
                            nvmlDeviceGetPowerUsage.restype = ctypes.c_int
                            power = ctypes.c_uint()
                            if nvmlDeviceGetPowerUsage(handle, ctypes.byref(power)) == 0:
                                self.gpu_power = power.value
                        except Exception:
                            pass
                    else:
                        self.gpu = 0
                else:
                    self.gpu = 0
            else:
                self.gpu = 0

            # ?????
            self._update_disk_usage()
            self._update_uptime()
            self.update()
        except Exception:
            # 出错时 GPU 设为 0
            self.gpu = 0
            self.update()

    def _update_disk_usage(self):
        """?????????????????????0"""
        import psutil
        self.disk_usage = {}
        total_used = 0
        total_all = 0
        for part in psutil.disk_partitions():
            if (not part.opts.startswith("cdrom")
                    and not part.device.startswith("\\\\")
                    and part.fstype not in ("", "udf", "iso9660")):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    if usage.total > 0:
                        letter = part.mountpoint.split(":")[0].rstrip("\\").upper()
                        self.disk_usage[f"disk_{letter}"] = usage.percent
                        total_used += usage.used
                        total_all += usage.total
                except (PermissionError, OSError):
                    pass
        if total_all > 0:
            self.disk_usage["disk_total"] = int(total_used / total_all * 100)
        else:
            self.disk_usage["disk_total"] = 0
        # ???????????????????? self.disk_usage.get(key, 0)

    def _update_uptime(self):
        """计算系统已运行时长"""
        import time
        boot_time = psutil.boot_time()
        self._uptime_seconds = int(time.time() - boot_time)
        total_minutes = self._uptime_seconds // 60
        total_hours = total_minutes // 60
        days = total_hours // 24
        hours = total_hours % 24
        minutes = total_minutes % 60

        rp = self._i18n["run_prefix"]
        mu_min = self._i18n["min_unit"]
        mu_hour = self._i18n["hour_unit"]
        mu_day = self._i18n["day_unit"]
        mu_month = self._i18n["month_unit"]

        if days >= 30:
            months = days // 30
            remaining_days = days % 30
            self.uptime = f"{rp}{months}{mu_month}{remaining_days}{mu_day}"
        elif days >= 1:
            self.uptime = f"{rp}{days}{mu_day}"
        elif total_hours < 3:
            self.uptime = f"{rp}{total_minutes}{mu_min}"
        else:
            if minutes >= 30:
                self.uptime = f"{rp}{hours}.5{mu_hour}"
            else:
                self.uptime = f"{rp}{hours}{mu_hour}"

    def update_clock(self):
        self.now = datetime.now()
        if LUNAR_AVAILABLE:
            try:
                lunar = ZhDate.from_datetime(self.now)
                from lunar_python import Solar as _Solar
                _lunar = _Solar.fromDate(self.now).getLunar()
                self.lunar_text = f"{self._i18n['lunar']} {_lunar.getMonthInChinese()}月{_lunar.getDayInChinese()}"
            except Exception:
                self.lunar_text = self._i18n['lunar_error']
        else:
            self.lunar_text = self._i18n['not_installed']

        current, next_name, days = get_next_term_info(self.now.year, self.now.month, self.now.day)
        if current:
            self.term_display = translate_term(current)
        elif next_name is not None and days is not None:
            trans_name = translate_term(next_name)
            self.term_display = f"{self._i18n['distance']}{trans_name} {days}{self._i18n['day_unit']}"
        else:
            self.term_display = ""
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._cached_bg is not None and not self._cached_bg.isNull():
            if self._cached_theme_opacity is not None:
                mapped_opacity = 0.75 + (self._cached_theme_opacity - 20) * (0.25 / 80)
                painter.setOpacity(mapped_opacity)
            painter.drawPixmap(0, 0, self._cached_bg)
            painter.setOpacity(1.0)

        if self.face is not None and not self.face.isNull():
            painter.drawPixmap(0, 0, self.face)

        cx = CENTER_X
        cy = CENTER_Y
        now = self.now
        self.draw_hand(painter, self.hour, cx, cy, self.hand_px, self.hand_py, (now.hour % 12) * 30 + now.minute * 0.5)
        self.draw_hand(painter, self.minute, cx, cy, self.hand_px, self.hand_py, now.minute * 6 + now.second * 0.1)
        self.draw_hand(painter, self.second, cx, cy, self.hand_px, self.hand_py, now.second * 6)

        # 绘制文字信息
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        font_family = settings.value("font_family", "Microsoft YaHei")
        font_size = int(settings.value("font_size", 10))
        font_color = settings.value("font_color", "#1c344d")
        font = QFont(font_family, font_size)
        painter.setFont(font)
        painter.setPen(QPen(QColor(font_color)))

        slot_values = {}
        slot_keys = ["slot_1", "slot_2", "slot_3", "slot_4", "slot_5", "slot_6", "slot_7", "slot_8"]
        for key in slot_keys:
            default_val = DEFAULT_LAYOUT.get(key, "empty")
            slot_values[key] = settings.value(key, default_val)

        ip_text = f"{self.public_ip or self.local_ip}"

        # ---- 只显示短格式地区名 ----
        selected_county = settings.value("selected_county", "")
        selected_city = settings.value("selected_city", "")
        selected_province = settings.value("selected_province", "")

        if selected_county:
            display_city = selected_county
        elif selected_city:
            display_city = selected_city
        elif selected_province:
            display_city = selected_province
        else:
            display_city = self.weather.get('city', self._i18n['unknown_location'])
            if display_city == "--":
                display_city = self._i18n['unknown_location']

        weather_icon = get_weather_icon(self.weather['weather'])
        weather_text = f"{weather_icon} {self.weather['weather']} {self.weather['temp']}℃"
        netspeed_text = f"↓{self.down_speed:.1f}Mb/s\n↑{self.up_speed:.1f}Mb/s"
        cpu_text = f"CPU{int(self.cpu)}%"
        gpu_text = f"GPU{int(self.gpu)}%"
        resolution_text = f"{self.screen_res}"
        memory_text = f"{self._i18n['memory']}\n{int(self.mem)}%"
        uptime_text = self.uptime
        term_text = self.term_display if self.term_display else ""
        date_text = f"{self.now.strftime('%Y/%m/%d')}\n  {self._i18n['week']}{self._i18n['weekdays'][self.now.weekday()]}"
        lunar_text = self.lunar_text

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
            "empty": "",
        }
        # ???????????? content_text_map
        for dk, dv in self.disk_usage.items():
            if dk == "disk_total":
                content_text_map[dk] = f"{int(dv)}%"
            else:

                letter = dk.replace("disk_", "")
                content_text_map[dk] = f"{letter}: {int(dv)}%"

        multiline_map = {
            "date": [self.now.strftime('%Y/%m/%d'),
                     f"{self._i18n['week']}{self._i18n['weekdays'][self.now.weekday()]}"],
            "netspeed": [f"↓{self.down_speed:.1f}Mb/s", f"↑{self.up_speed:.1f}Mb/s"],
            "memory": [self._i18n['memory'], f"{int(self.mem)}%"],
            "disk_total": [self._i18n['disk_total'], f"{int(self.disk_usage.get('disk_total', 0))}%"],
        }

        slot_position_map = {
            "slot_1": (20, 30, 105, 43),
            "slot_2": (20, 86, 85, 43),
            "slot_3": (20, 166, 70, 50),
            "slot_4": (20, 235, 88, 50),
            "slot_5": (280, 30, 94, 43),
            "slot_6": (314, 86, 71, 43),
            "slot_7": (324, 166, 60, 50),
            "slot_8": (273, 238, 97, 43),
        }

        for slot_key, (x, y, w, h) in slot_position_map.items():
            configured_key = slot_values.get(slot_key, "empty")
            if configured_key == "empty":
                continue
            if configured_key == "weather":
                painter.drawText(x, y, w, h // 2,
                                 Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                 display_city)
                if not self._api_configured:
                    painter.drawText(x, y + h // 2, w, h // 2,
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                     self._i18n['set_api'])
                elif self._loading_weather:
                    dots_text = "." * self._loading_dots
                    painter.drawText(x, y + h // 2, w, h // 2,
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                     f"⌛ {self._i18n['loading']}{dots_text}")
                else:
                    weather_icon = get_weather_icon(self.weather['weather'])
                    weather_text = f"{weather_icon} {self.weather['weather']} {self.weather['temp']}℃"
                    painter.drawText(x, y + h // 2, w, h // 2,
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                     weather_text)
                continue

            if configured_key in multiline_map:
                lines = multiline_map[configured_key]
                line_height = h // 2
                for idx, line in enumerate(lines):
                    if line:
                        painter.drawText(x, y + idx * line_height, w, line_height,
                                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                         line)
            elif configured_key in content_text_map:
                text = content_text_map[configured_key]
                if text:
                    painter.drawText(x, y, w, h,
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                     text)

    def draw_hand(self, painter, pixmap, cx, cy, px, py, angle):
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(angle)
        painter.drawPixmap(-px, -py, pixmap)
        painter.restore()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = event.globalPosition().toPoint()
        if hasattr(self, '_detail_popup'):
            hover_enabled = QSettings("MyDesktopApp", "WeatherSettings").value("hover_enabled", True, type=bool)
            if hover_enabled:
                pos = event.position().toPoint()
                slot_info = self._get_hover_slot(pos)
                if slot_info:
                    slot_key, content_key, rect = slot_info
                    if self._last_hover_slot != (slot_key, content_key):
                        self._last_hover_slot = (slot_key, content_key)
                        self._detail_popup.stop_fade_out()
                        self._detail_popup.show_for_slot(slot_key, content_key, rect)
                else:
                    if self._last_hover_slot is not None:
                        self._last_hover_slot = None
                        self._detail_popup.start_fade_out(2000)
            else:
                if self._last_hover_slot is not None:
                    self._last_hover_slot = None
                    self._detail_popup.hide()

    def mouseReleaseEvent(self, e):
        self.drag_pos = None
    # ---------- hover detail popup ----------
