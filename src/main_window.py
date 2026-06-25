import sys
import os
import socket
import subprocess
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import psutil

from .constants import ORIG_W, ORIG_H, CENTER_X, CENTER_Y, VERSION, DEFAULT_LAYOUT
from .utils import resource_path, get_weather_icon
from .solar_terms import get_next_term_info
from .threads import ServerScanner, WeatherThread, NetSpeedThread
from .settings_dialog import SettingsDialog
from .tray_icon import TrayIcon
from .updater import UpdateChecker
from .widgets import NoticeBubble

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
class MainWindow(QWidget):
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

        # 加载图片
        self.bg = QPixmap(resource_path("bg.png"))
        self.hour = QPixmap(resource_path("Hour_Hand.png"))
        self.minute = QPixmap(resource_path("Minute_Hand.png"))
        self.second = QPixmap(resource_path("Second_Hand.png"))
        self.center_dot = QPixmap(resource_path("center_dot.png"))
        if any(p.isNull() for p in [self.bg, self.hour, self.minute, self.second, self.center_dot]):
            sys.exit(1)

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

        screen = QApplication.primaryScreen()
        if screen:
            size = screen.size()
            self.screen_res = f"{size.width()}×{size.height()}"
        else:
            self.screen_res = "1920×1080"

        # FPS 统计
        self.last_paint_time = QElapsedTimer()
        self.last_paint_time.start()
        self.paint_count = 0
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(1000)

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

        self.tray = TrayIcon(self)
        self.tray.show()

        # ---------- 公告气泡 ----------
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

        self.update_perf()
        self.update_clock()
        self.move_to_top_right()
        self.show()

    def move_to_top_right(self):
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.right() - self.width() - 100
            y = geometry.top() + 150
            self.move(x, y)

    def _on_bubble_clicked(self):
        """点击聊天气泡 → 打开公告窗口"""
        self._open_notice_window()

    def _open_notice_window(self):
        """打开公告窗口（延迟创建，避免与闪烁冲突）"""
        from .notice import NoticeWindow, NoticeManager

        if self._notice_window is not None and self._notice_window.isVisible():
            self._notice_window.raise_()
            self._notice_window.activateWindow()
            return

        # 延迟 200ms 创建窗口，避免与闪烁回调冲突
        QTimer.singleShot(200, self._create_notice_window)

    def _create_notice_window(self):
        """实际创建公告窗口"""
        from .notice import NoticeWindow, NoticeManager

        self._notice_window = NoticeWindow(self)
        self._notice_window.destroyed.connect(self._on_notice_window_destroyed)

        manager = NoticeManager.get_instance()
        current_notice = manager.get_current_notice()
        if current_notice:
            notice_id = current_notice.get("id")
            if notice_id:
                # 延迟选中，等待窗口加载完成
                QTimer.singleShot(300, lambda: self._notice_window.select_notice_by_id(
                    notice_id) if self._notice_window else None)

        self._notice_window.show()

    def _on_notice_window_destroyed(self):
        """公告窗口销毁时清理引用"""
        self._notice_window = None

    # ==================== 修改点：设置窗口改为非模态 ====================
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
            # 移除模态设置，变为非模态，使公告窗口和设置窗口互不影响
            # dialog.setWindowModality(Qt.WindowModality.ApplicationModal)  # 已注释

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
            dialog.show()  # 改为非阻塞显示
            # dialog.exec()  # 原阻塞调用已注释
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开设置失败：{str(e)}")
    # ===============================================================

    def _on_settings_closed(self):
        self.settings_dialog = None

    # ---------- 更新检查 ----------
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

    # ---------- 天气线程管理 ----------
    def start_weather_thread(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        api_url = settings.value("api_url", "")
        api_key = settings.value("api_key", "")
        refresh_minutes = int(settings.value("refresh_minutes", 120))

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
                self.weather_thread.stop()
                self.weather_thread = None
            return

        if not api_url or not api_key:
            if self.weather_thread is not None:
                self.weather_thread.stop()
                self.weather_thread = None
            self.on_weather_error("未配置 API 地址或密钥")
            return

        if self.weather_thread is not None:
            return

        self.weather_thread = WeatherThread(api_url, api_key, refresh_minutes)
        self.weather_thread.data_updated.connect(self.update_weather)
        self.weather_thread.error_signal.connect(self.on_weather_error)
        self.weather_thread.start()

    def update_weather(self, data):
        self.weather = data
        self.update()

    def on_weather_error(self, err_msg):
        self.weather = {"city": "⚠️", "weather": "⚠️", "temp": "?", "wind": err_msg[:10] + "..."}
        self.update()

    # ---------- 关闭事件 ----------
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

    # ---------- 辅助 ----------
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

    # ---------- 绘制 ----------
    def paintEvent(self, event):
        self.paint_count += 1

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(255, 255, 255, 1))

        painter.drawPixmap(0, 0, self.bg)

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
        city_text = self.weather.get('city', '--')
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
            "weather": [city_text, weather_text],
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