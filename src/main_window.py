import sys
import os
import socket
import subprocess
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import psutil

from .constants import ORIG_W, ORIG_H, CENTER_X, CENTER_Y, VERSION
from .utils import resource_path, get_weather_icon
from .solar_terms import get_next_term_info
from .threads import ServerScanner, WeatherThread, NetSpeedThread
from .settings_dialog import SettingsDialog
from .tray_icon import TrayIcon
from .updater import UpdateChecker

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
        # 窗口标志：无边框、置底、不显示任务栏图标（Tool）
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnBottomHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 标记是否正在退出（用于关闭事件判断）
        self._exiting = False

        # 加载图片
        self.bg = QPixmap(resource_path("bg.png"))
        self.hour = QPixmap(resource_path("Hour_Hand.png"))
        self.minute = QPixmap(resource_path("Minute_Hand.png"))
        self.second = QPixmap(resource_path("Second_Hand.png"))
        self.center_dot = QPixmap(resource_path("center_dot.png"))
        if any(p.isNull() for p in [self.bg, self.hour, self.minute, self.second, self.center_dot]):
            sys.exit(1)

        # 窗口固定大小
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

        # ---------- 托盘图标 ----------
        self.tray = TrayIcon(self)
        self.tray.show()

        # ---------- “设置”文字按钮 ----------
        self.settings_btn = QLabel("设置", self)
        self.settings_btn.setStyleSheet("""
            QLabel {
                background: transparent;
                border-radius: 4px;
                padding: 4px 8px;
                color: #333;
                font-size: 12px;
                font-weight: normal;
            }
            QLabel:hover {
                background: rgba(255,255,255,60);
            }
        """)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.adjustSize()
        self.settings_btn.move(self.width() - self.settings_btn.width() - 15,
                               self.height() - self.settings_btn.height() - 1)
        self.settings_btn.mousePressEvent = self.on_settings_click

        # ---------- 更新检查 ----------
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

    def on_settings_click(self, event):
        self.settings_btn.setStyleSheet("""
            QLabel {
                background: rgba(255,255,255,150);
                border-radius: 4px;
                padding: 4px 8px;
                color: #333;
                font-size: 12px;
                font-weight: normal;
            }
        """)
        QTimer.singleShot(150, lambda: self.settings_btn.setStyleSheet("""
            QLabel {
                background: transparent;
                border-radius: 4px;
                padding: 4px 8px;
                color: #333;
                font-size: 12px;
                font-weight: normal;
            }
            QLabel:hover {
                background: rgba(255,255,255,60);
            }
        """))
        # 直接打开设置对话框，不再弹出菜单
        self.open_settings()

    def open_settings(self, initial_page="weather"):
        try:
            dialog = SettingsDialog(self, initial_page=initial_page)
            dialog.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
            dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            # 定位：距右100px，距下300px
            screen = QApplication.primaryScreen()
            if screen:
                geometry = screen.availableGeometry()
                x = geometry.right() - dialog.width() - 100
                y = geometry.bottom() - dialog.height() - 200
                if y < 0:
                    y = 0
                dialog.move(x, y)
            else:
                dialog.move(
                    self.x() + (self.width() - dialog.width()) // 2,
                    self.y() + (self.height() - dialog.height()) // 2
                )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.start_weather_thread()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开设置失败：{str(e)}")

    def show_message(self, title, text):
        QMessageBox.information(self, title, text)

    def confirm_exit(self):
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._exiting = True
            QApplication.quit()

    # ---------- 更新检查 ----------
    def check_for_updates_auto(self):
        self.update_checker = UpdateChecker()
        self.update_checker.check_finished.connect(self.on_update_check_finished)
        self.update_checker.start()

    def on_update_check_finished(self, result):
        if result.get("has_update", False):
            self.has_update = True
            self.latest_version_info = result
            self.settings_btn.setText("设置 ●")
            # 移除托盘消息
        else:
            self.has_update = False
            if "●" in self.settings_btn.text():
                self.settings_btn.setText("设置")

    def get_latest_version_info(self):
        return self.latest_version_info if self.has_update else None

    # ---------- 天气线程管理 ----------
    def start_weather_thread(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        api_url = settings.value("api_url", "")
        api_key = settings.value("api_key", "")
        refresh_minutes = int(settings.value("refresh_minutes", 120))

        # 停止旧线程（如果存在）
        if self.weather_thread is not None:
            self.weather_thread.stop()
            # 注意：stop 内部已经 wait，这里不再等待

        # 创建并启动新线程
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
                self.lunar_text = f"{lunar.lunar_month}月{lunar.lunar_day}日"
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

        # 1. 背景
        painter.drawPixmap(0, 0, self.bg)

        # 2. 文字
        font = QFont()
        font.setPixelSize(12)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#1c344d")))

        # 天气：第一行地区名，第二行天气图标+天气+温度
        city_text = self.weather.get('city', '--')
        weather_icon = get_weather_icon(self.weather['weather'])
        weather_detail_text = f"{weather_icon} {self.weather['weather']} {self.weather['temp']}℃"

        items = [
            (20, 30, 105, 15, f"{self.local_ip}", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (280, 30, 94, 15, city_text, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (280, 48, 94, 15, weather_detail_text, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (20, 86, 85, 43, f"↓{self.down_speed:.1f}Mb/s\n↑{self.up_speed:.1f}Mb/s", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (314, 86, 71, 43, f"CPU{int(self.cpu)}%\nGPU{int(self.gpu)}%", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (20, 166, 70, 50, f"刷新率: {self.fps}\n{self.screen_res}", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (324, 166, 60, 50, f"内存\n{int(self.mem)}%", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (20, 235, 88, 50, f"{self.now.strftime('%Y/%m/%d')}\n  星期{['一','二','三','四','五','六','日'][self.now.weekday()]}", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (273, 238, 97, 43, f"农历{self.lunar_text}\n{self.term_display}", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
        ]

        for x, y, w, h, text, align in items:
            painter.drawText(x, y, w, h, align, text)

        # 3. 指针
        cx = CENTER_X
        cy = CENTER_Y
        now = self.now

        self.draw_hand(painter, self.hour, cx, cy, (now.hour % 12) * 30 + now.minute * 0.5)
        self.draw_hand(painter, self.minute, cx, cy, now.minute * 6 + now.second * 0.1)
        self.draw_hand(painter, self.second, cx, cy, now.second * 6)

        # 4. 中心圆点
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

    # ---------- 鼠标拖拽 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint()
    def mouseMoveEvent(self, e):
        if self.drag_pos:
            self.move(self.pos() + e.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = e.globalPosition().toPoint()
    def mouseReleaseEvent(self, e):
        self.drag_pos = None