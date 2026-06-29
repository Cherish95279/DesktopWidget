import sys
import os
import socket
import subprocess
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import psutil

from .constants import CENTER_X, CENTER_Y, VERSION, DEFAULT_LAYOUT
from .utils import resource_path, get_weather_icon
from .solar_terms import get_next_term_info
from .threads import ServerScanner, WeatherThread, NetSpeedThread
from .settings_dialog import SettingsDialog
from .tray_icon import TrayIcon
from .updater import UpdateChecker
from .theme_manager import get_theme_manager
from .widgets.notice_bubble import NoticeBubble
from .mixins import (
    WindowMixin,
    PaintMixin,
    ThemeMixin,
    WeatherMixin,
    UpdateMixin,
    DialogMixin,
)

try:
    import GPUtil
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False

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
class MainWindow(
    WindowMixin,
    PaintMixin,
    ThemeMixin,
    WeatherMixin,
    UpdateMixin,
    DialogMixin,
    QWidget
):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnBottomHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._exiting = False
        self.settings_dialog = None
        self._notice_window = None

        self.theme_manager = get_theme_manager()

        # 加载图片（通过主题管理器）
        self._load_images()

        # 缓存
        self._cached_bg = None
        self._cached_theme_color = None
        self._cached_theme_opacity = None
        self._cached_tint_alpha = None

        self.setFixedSize(400, 297)
        self.drag_pos = None

        # 数据
        self.cpu = 0
        self.gpu = 0
        self.mem = 0
        self.local_ip = self.get_local_ip()
        self.server_ip = "扫描中..."
        self.weather = {"city": "--", "weather": "--", "temp": "--", "wind": ""}
        self.down_speed = 0.0
        self.up_speed = 0.0
        self.fps = 0
        self.now = datetime.now()
        self.lunar_text = ""
        self.term_display = ""

        self._loading_weather = False
        self._loading_dots = 0
        self._loading_timer = None
        self._api_configured = True

        self._init_paint()

        self.weather_thread = None
        self.start_weather_thread()

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

        self.tray = TrayIcon(self)
        self.tray.show()

        self.notice_bubble = NoticeBubble(self)
        self.notice_bubble.move(
            self.width() - self.notice_bubble.width() - 15,
            self.height() - self.notice_bubble.height() - 1
        )
        self.notice_bubble.set_on_click(self._on_bubble_clicked)
        self.notice_bubble.raise_()

        self.update_checker = None
        self.has_update = False
        self.latest_version_info = {}
        QTimer.singleShot(3000, self.check_for_updates_auto)

        self.update_theme_cache()

        self.update_perf()
        self.update_clock()
        self.move_to_top_right()
        self.show()

    # ===== 加载图片（带调试打印） =====
    def _load_images(self):
        """通过主题管理器加载当前主题的所有图片"""
        print(f"🔄 _load_images() 被调用，当前主题: {self.theme_manager.get_current_theme()}")

        bg_path = self.theme_manager.get_theme_path("bg.png")
        face_path = self.theme_manager.get_theme_path("face.png")
        hour_path = self.theme_manager.get_theme_path("Hour_Hand.png")
        minute_path = self.theme_manager.get_theme_path("Minute_Hand.png")
        second_path = self.theme_manager.get_theme_path("Second_Hand.png")
        dot_path = self.theme_manager.get_theme_path("center_dot.png")

        print(f"  bg_path: {bg_path}")
        print(f"  face_path: {face_path}")
        print(f"  hour_path: {hour_path}")
        print(f"  minute_path: {minute_path}")
        print(f"  second_path: {second_path}")
        print(f"  dot_path: {dot_path}")

        self.bg = QPixmap(bg_path) if bg_path and os.path.exists(bg_path) else QPixmap()
        self.face = QPixmap(face_path) if face_path and os.path.exists(face_path) else QPixmap()
        self.hour = QPixmap(hour_path) if hour_path and os.path.exists(hour_path) else QPixmap()
        self.minute = QPixmap(minute_path) if minute_path and os.path.exists(minute_path) else QPixmap()
        self.second = QPixmap(second_path) if second_path and os.path.exists(second_path) else QPixmap()
        self.center_dot = QPixmap(dot_path) if dot_path and os.path.exists(dot_path) else QPixmap()

        if self.face.isNull():
            self.face = self.bg

        if any(p.isNull() for p in [self.bg, self.hour, self.minute, self.second, self.center_dot]):
            print("⚠️ 部分图片加载失败，请检查主题文件")

        print(f"✅ 图片加载完成，bg: {not self.bg.isNull()}, face: {not self.face.isNull()}")

    # ===== 重新加载图片（主题切换时调用） =====
    def reload_images(self):
        """重新加载当前主题的所有图片（主题切换时调用）"""
        print("🔄 reload_images() 被调用")
        self._load_images()
        self._cached_bg = None
        self.update_theme_cache()
        self.update()
        print("✅ reload_images() 完成")

    # ---------- 以下方法保持不变（省略冗长内容） ----------
    # 为了节省篇幅，这里省略 move_to_top_right、_on_bubble_clicked、
    # open_settings、check_for_updates_auto、start_loading_animation、
    # start_weather_thread、update_weather、closeEvent、get_local_ip、
    # on_speed_update、update_perf、update_clock、update_fps、
    # paintEvent、draw_hand、mousePressEvent、mouseMoveEvent、mouseReleaseEvent
    # 这些方法从你的现有 `main_window.py` 中完整保留即可。
    # 如果你不确定，我可以提供完整版，但当前文件已经很长，所以我只展示修改部分。

    # ===== 以下方法从原 main_window.py 中复制保留 =====

    def move_to_top_right(self):
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.right() - self.width() - 100
            y = geometry.top() + 150
            self.move(x, y)

    def _on_bubble_clicked(self):
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
                QTimer.singleShot(300, lambda: self._notice_window.select_notice_by_id(notice_id) if self._notice_window else None)
        self._notice_window.show()

    def _on_notice_window_destroyed(self):
        self._notice_window = None

    def open_settings(self, initial_page="general"):
        if self.settings_dialog is not None and self.settings_dialog.isVisible():
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            if hasattr(self.settings_dialog, 'switch_page'):
                page_index = {"general": 0, "display": 1, "weather": 2, "theme": 3, "update": 4, "donation": 5, "about": 6}.get(initial_page, 0)
                self.settings_dialog.switch_page(page_index)
            return
        try:
            dialog = SettingsDialog(self, initial_page=initial_page)
            dialog.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
            screen = QApplication.primaryScreen()
            if screen:
                geometry = screen.availableGeometry()
                x = geometry.right() - dialog.width() - 100
                y = geometry.bottom() - dialog.height() - 200
                if y < 0:
                    y = 0
                dialog.move(x, y)
            self.settings_dialog = dialog
            dialog.finished.connect(self._on_settings_closed)
            dialog.show()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开设置失败：{str(e)}")

    def _on_settings_closed(self):
        self.settings_dialog = None

    def check_for_updates_auto(self):
        self.update_checker = UpdateChecker()
        self.update_checker.check_finished.connect(self.on_update_check_finished)
        self.update_checker.start()

    def on_update_check_finished(self, result):
        if result.get("has_update", False):
            self.has_update = True
            self.latest_version_info = result
        else:
            self.has_update = False

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

    def apply_theme(self):
        self.update_theme_cache()

    def start_weather_thread(self, force_restart=False):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        api_url = settings.value("api_url", "")
        api_key = settings.value("api_key", "")
        refresh_minutes = int(settings.value("refresh_minutes", 120))
        self._api_configured = bool(api_url and api_key)

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
                print("🌤️ 布局中未配置天气，停止天气线程")
                try:
                    self.weather_thread.data_updated.disconnect()
                    self.weather_thread.error_signal.disconnect()
                except:
                    pass
                self.weather_thread.stop()
                self.weather_thread = None
            self.stop_loading_animation()
            return

        if not self._api_configured:
            if self.weather_thread is not None:
                try:
                    self.weather_thread.data_updated.disconnect()
                    self.weather_thread.error_signal.disconnect()
                except:
                    pass
                self.weather_thread.stop()
                self.weather_thread = None
            self.stop_loading_animation()
            self.update()
            return

        if self.weather_thread is not None and not force_restart:
            return

        if self.weather_thread is not None:
            print("🔄 断开旧天气线程信号并停止...")
            try:
                self.weather_thread.data_updated.disconnect()
                self.weather_thread.error_signal.disconnect()
            except Exception as e:
                print(f"⚠️ 断开信号时出错: {e}")
            self.weather_thread.stop()
            self.weather_thread = None

        if force_restart or self.weather.get("city") == "--":
            self.start_loading_animation()

        print("🌤️ 启动新天气线程...")
        self.weather_thread = WeatherThread(api_url, api_key, refresh_minutes)
        self.weather_thread.data_updated.connect(self.update_weather)
        self.weather_thread.error_signal.connect(self.on_weather_error)
        self.weather_thread.start()
        print("🌤️ 天气线程已启动")

    def update_weather(self, data):
        print(f"🔔 主窗口收到天气更新: {data.get('city')} {data.get('weather')} {data.get('temp')}℃")
        self.stop_loading_animation()
        self.weather = data
        self.update()

    def on_weather_error(self, err_msg):
        print(f"❌ 天气错误: {err_msg}")

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
            event.accept()

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def on_speed_update(self, down, up):
        self.down_speed = max(0, down)
        self.up_speed = max(0, up)
        self.update()

    def update_perf(self):
        try:
            self.cpu = psutil.cpu_percent()
            self.mem = psutil.virtual_memory().percent
            if getattr(sys, 'frozen', False):
                self.gpu = 0
            else:
                if GPU_AVAILABLE:
                    try:
                        gpus = GPUtil.getGPUs()
                        self.gpu = gpus[0].load * 100 if gpus else 0
                    except Exception:
                        self.gpu = 0
                else:
                    self.gpu = 0
            self.update()
        except Exception:
            pass

    def update_clock(self):
        self.now = datetime.now()
        if LUNAR_AVAILABLE:
            try:
                lunar = ZhDate.from_datetime(self.now)
                self.lunar_text = f"农历{lunar.lunar_month}月{lunar.lunar_day}日"
            except:
                self.lunar_text = "农历错误"
        else:
            self.lunar_text = "未安装"

        current, next_name, days = get_next_term_info(self.now.year, self.now.month, self.now.day)
        if current:
            self.term_display = current
        elif next_name is not None and days is not None:
            self.term_display = f"离{next_name}还有{days}天"
        else:
            self.term_display = ""
        self.update()

    def update_fps(self):
        elapsed = self.last_paint_time.elapsed()
        if elapsed > 0:
            self.fps = int(self.paint_count * 1000 / elapsed)
        else:
            self.fps = 0
        self.paint_count = 0
        self.last_paint_time.restart()
        self.update()

    def paintEvent(self, event):
        self.paint_count += 1
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
        self.draw_hand(painter, self.hour, cx, cy, (now.hour % 12) * 30 + now.minute * 0.5)
        self.draw_hand(painter, self.minute, cx, cy, now.minute * 6 + now.second * 0.1)
        self.draw_hand(painter, self.second, cx, cy, now.second * 6)

        dot_size = 18
        scaled_dot = self.center_dot.scaled(
            dot_size, dot_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        painter.drawPixmap(cx - dot_size // 2, cy - dot_size // 2, scaled_dot)

        # 绘制文字信息（保持不变，此处省略）
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

        ip_text = f"{self.local_ip}"
        selected_city = settings.value("selected_city", "")
        selected_county = settings.value("selected_county", "")
        user_city = selected_county if selected_county else selected_city
        if user_city:
            display_city = user_city
        else:
            display_city = self.weather.get('city', '未知地区')
            if display_city == "--":
                display_city = "未知地区"

        weather_icon = get_weather_icon(self.weather['weather'])
        weather_text = f"{weather_icon} {self.weather['weather']} {self.weather['temp']}℃"
        netspeed_text = f"↓{self.down_speed:.1f}Mb/s\n↑{self.up_speed:.1f}Mb/s"
        cpu_text = f"CPU{int(self.cpu)}%"
        gpu_text = f"GPU{int(self.gpu)}%"
        resolution_text = f"{self.screen_res}"
        refresh_rate_text = f"{self.fps}Hz"
        memory_text = f"内存\n{int(self.mem)}%"
        date_text = f"{self.now.strftime('%Y/%m/%d')}\n  星期{['一','二','三','四','五','六','日'][self.now.weekday()]}"
        lunar_text = f"{self.lunar_text}\n{self.term_display}"

        content_text_map = {
            "ip": ip_text,
            "weather": weather_text,
            "netspeed": netspeed_text,
            "cpu": cpu_text,
            "gpu": gpu_text,
            "resolution": resolution_text,
            "refresh_rate": refresh_rate_text,
            "memory": memory_text,
            "date": date_text,
            "lunar": lunar_text,
            "empty": "",
        }

        multiline_map = {
            "lunar": [self.lunar_text, self.term_display],
            "date": [self.now.strftime('%Y/%m/%d'), f"星期{['一','二','三','四','五','六','日'][self.now.weekday()]}"],
            "netspeed": [f"↓{self.down_speed:.1f}Mb/s", f"↑{self.up_speed:.1f}Mb/s"],
            "memory": ["内存", f"{int(self.mem)}%"],
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
                                     "设置API")
                elif self._loading_weather:
                    dots_text = "." * self._loading_dots
                    painter.drawText(x, y + h // 2, w, h // 2,
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                     f"⌛ 加载中{dots_text}")
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

    def draw_hand(self, painter, pixmap, cx, cy, angle):
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(angle)
        painter.drawPixmap(-pixmap.width()//2, -pixmap.height()//2, pixmap)
        painter.restore()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self.drag_pos:
            self.move(self.pos() + e.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self.drag_pos = None