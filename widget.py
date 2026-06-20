import sys
import os
import subprocess

# ===== 打包后强制隐藏所有子进程窗口 =====
if sys.platform == 'win32' and getattr(sys, 'frozen', False):
    _original_popen = subprocess.Popen
    def _popen_no_window(*args, **kwargs):
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = kwargs.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
        return _original_popen(*args, **kwargs)
    subprocess.Popen = _popen_no_window

# ---------- 其余导入 ----------
import socket
import math
from datetime import datetime, timedelta
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import psutil
import requests
import certifi
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from zhdate import ZhDate
    LUNAR_AVAILABLE = True
except ImportError:
    LUNAR_AVAILABLE = False

try:
    import GPUtil
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False

# ---------- 资源路径 ----------
def resource_path(rel_path):
    try:
        base = sys._MEIPASS
    except:
        base = os.path.abspath(".")
    return os.path.join(base, rel_path)

# ---------- 天气图标 ----------
def get_weather_icon(weather_str):
    mapping = {
        "晴": "☀️",
        "多云": "⛅",
        "阴": "☁️",
        "小雨": "🌦️",
        "中雨": "🌧️",
        "大雨": "🌧️",
        "雷阵雨": "⛈️",
        "小雪": "🌨️",
        "中雪": "❄️",
        "大雪": "❄️",
        "雾": "🌫️",
        "霾": "🌫️",
        "大风": "💨",
    }
    first = weather_str.split('转')[0] if '转' in weather_str else weather_str
    return mapping.get(first, "🌡️")

# ---------- 节气数据 ----------
TERM_DATA = {
    2026: [
        (1, 5, "小寒"), (1, 20, "大寒"), (2, 4, "立春"), (2, 19, "雨水"),
        (3, 6, "惊蛰"), (3, 21, "春分"), (4, 5, "清明"), (4, 20, "谷雨"),
        (5, 5, "立夏"), (5, 21, "小满"), (6, 5, "芒种"), (6, 21, "夏至"),
        (7, 7, "小暑"), (7, 22, "大暑"), (8, 7, "立秋"), (8, 23, "处暑"),
        (9, 7, "白露"), (9, 23, "秋分"), (10, 8, "寒露"), (10, 23, "霜降"),
        (11, 7, "立冬"), (11, 22, "小雪"), (12, 7, "大雪"), (12, 22, "冬至")
    ],
    2027: [
        (1, 5, "小寒"), (1, 20, "大寒"), (2, 4, "立春"), (2, 19, "雨水"),
        (3, 6, "惊蛰"), (3, 21, "春分"), (4, 5, "清明"), (4, 20, "谷雨"),
        (5, 6, "立夏"), (5, 21, "小满"), (6, 6, "芒种"), (6, 21, "夏至"),
        (7, 7, "小暑"), (7, 23, "大暑"), (8, 7, "立秋"), (8, 23, "处暑"),
        (9, 8, "白露"), (9, 23, "秋分"), (10, 8, "寒露"), (10, 24, "霜降"),
        (11, 7, "立冬"), (11, 22, "小雪"), (12, 7, "大雪"), (12, 22, "冬至")
    ],
    2028: [
        (1, 6, "小寒"), (1, 21, "大寒"), (2, 4, "立春"), (2, 19, "雨水"),
        (3, 5, "惊蛰"), (3, 20, "春分"), (4, 4, "清明"), (4, 20, "谷雨"),
        (5, 5, "立夏"), (5, 21, "小满"), (6, 5, "芒种"), (6, 21, "夏至"),
        (7, 7, "小暑"), (7, 22, "大暑"), (8, 7, "立秋"), (8, 22, "处暑"),
        (9, 7, "白露"), (9, 22, "秋分"), (10, 8, "寒露"), (10, 23, "霜降"),
        (11, 7, "立冬"), (11, 22, "小雪"), (12, 7, "大雪"), (12, 21, "冬至")
    ],
    2029: [
        (1, 5, "小寒"), (1, 20, "大寒"), (2, 4, "立春"), (2, 19, "雨水"),
        (3, 5, "惊蛰"), (3, 20, "春分"), (4, 4, "清明"), (4, 20, "谷雨"),
        (5, 5, "立夏"), (5, 21, "小满"), (6, 5, "芒种"), (6, 21, "夏至"),
        (7, 7, "小暑"), (7, 22, "大暑"), (8, 7, "立秋"), (8, 23, "处暑"),
        (9, 7, "白露"), (9, 23, "秋分"), (10, 8, "寒露"), (10, 23, "霜降"),
        (11, 7, "立冬"), (11, 22, "小雪"), (12, 7, "大雪"), (12, 21, "冬至")
    ]
}

def get_next_term_info(year, month, day):
    all_terms = []
    for y, terms in TERM_DATA.items():
        for m, d, name in terms:
            all_terms.append((y, m, d, name))
    all_terms.sort(key=lambda x: (x[0], x[1], x[2]))
    cur_date = datetime(year, month, day)
    cur_ymd = (year, month, day)
    future_terms = []
    for y, m, d, name in all_terms:
        if (y, m, d) >= cur_ymd:
            future_terms.append((y, m, d, name))
    if not future_terms:
        next_year = year + 1
        if next_year in TERM_DATA:
            first_term = TERM_DATA[next_year][0]
            next_date = datetime(next_year, first_term[0], first_term[1])
            days = (next_date - cur_date).days
            return (None, first_term[2], days)
        else:
            return (None, None, None)
    y0, m0, d0, name0 = future_terms[0]
    if (y0, m0, d0) == cur_ymd:
        return (name0, None, None)
    else:
        next_date = datetime(y0, m0, d0)
        days = (next_date - cur_date).days
        return (None, name0, days)

# ---------- 扫描 HA 服务器 ----------
class ServerScanner(QThread):
    ip_found = pyqtSignal(str)
    def run(self):
        local_ip = "192.168.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
        except: pass
        subnet = ".".join(local_ip.split('.')[:-1]) + "."
        found = None
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(self.check_port, subnet + str(i)): i for i in range(1, 255)}
            for f in as_completed(futures):
                res = f.result()
                if res:
                    found = res
                    break
        self.ip_found.emit(found if found else "192.168.0.135")
    def check_port(self, ip):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.15)
                if s.connect_ex((ip, 8123)) == 0:
                    return ip
        except: pass
        return None

# ---------- 天气线程 ----------
class WeatherThread(QThread):
    data_updated = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, api_url, api_key, refresh_minutes):
        super().__init__()
        self.api_url = api_url
        self.api_key = api_key
        self.refresh_minutes = max(1, refresh_minutes)

    def run(self):
        while True:
            if not self.api_url or not self.api_key:
                self.error_signal.emit("未配置 API 地址或密钥")
                self.msleep(60000)
                continue
            try:
                ip_url = f"{self.api_url}/v3/ip?key={self.api_key}"
                ip_resp = requests.get(ip_url, timeout=5, verify=certifi.where())
                ip_resp.raise_for_status()
                city_code = ip_resp.json().get('adcode', '110101')

                weather_url = f"{self.api_url}/v3/weather/weatherInfo?key={self.api_key}&city={city_code}&extensions=base"
                w_resp = requests.get(weather_url, timeout=5, verify=certifi.where())
                w_resp.raise_for_status()
                data = w_resp.json()

                if data['status'] == '1' and data['count'] != '0':
                    live = data['lives'][0]
                    self.data_updated.emit({
                        'weather': live['weather'],
                        'temp': live['temperature'],
                        'wind': live['winddirection'] + live['windpower'] + '级'
                    })
                else:
                    self.error_signal.emit(f"API错误: {data.get('info', '未知')}")
            except Exception as e:
                self.error_signal.emit(f"请求异常: {str(e)}")
            self.msleep(self.refresh_minutes * 60 * 1000)

# ---------- 网速监控 ----------
class NetSpeedThread(QThread):
    speed_updated = pyqtSignal(float, float)
    def __init__(self):
        super().__init__()
        self.last_bytes = psutil.net_io_counters()
        self.last_time = datetime.now()

    def run(self):
        while True:
            now = datetime.now()
            current = psutil.net_io_counters()
            dt = (now - self.last_time).total_seconds()
            if dt > 0:
                down = (current.bytes_recv - self.last_bytes.bytes_recv) / dt / 1024 / 1024 * 8
                up = (current.bytes_sent - self.last_bytes.bytes_sent) / dt / 1024 / 1024 * 8
                self.speed_updated.emit(down, up)
            self.last_bytes = current
            self.last_time = now
            self.sleep(1)

# ---------- 设置对话框 ----------
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowSystemMenuHint)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---------- 左侧目录 ----------
        left_panel = QWidget()
        left_panel.setFixedWidth(100)
        left_panel.setStyleSheet("background-color: #f0f0f0;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 20, 0, 20)
        left_layout.setSpacing(0)

        self.cat_buttons = []
        for i in range(5):
            btn = QPushButton()
            btn.setFixedHeight(40)
            btn.setFlat(True)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: center;
                    font-size: 12px;
                    color: #333;
                    border: none;
                    background: transparent;
                }
                QPushButton:hover {
                    background: #e0e0e0;
                }
                QPushButton:checked {
                    background: #d0e4ff;
                }
            """)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            if i == 0:
                btn.setText("天气设置")
                btn.setChecked(True)
            else:
                btn.setText("")
                btn.setVisible(False)
            left_layout.addWidget(btn)
            self.cat_buttons.append(btn)

        self.cat_buttons[0].clicked.connect(lambda: self.switch_page(0))
        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # ---------- 右侧内容 ----------
        self.right_panel = QWidget()
        self.right_panel.setStyleSheet("background-color: rgba(245, 245, 245, 0.9);")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(15, 20, 15, 15)
        right_layout.setSpacing(5)

        self.page_weather = QWidget()
        weather_layout = QVBoxLayout(self.page_weather)
        weather_layout.setContentsMargins(0, 0, 0, 0)
        weather_layout.setSpacing(5)

        # ---- API 地址（下拉选择 + 输入框） ----
        lbl_url = QLabel("API 地址")
        weather_layout.addWidget(lbl_url)
        url_layout = QHBoxLayout()
        self.url_combo = QComboBox()
        self.url_combo.addItems(["高德", "自定义"])
        self.url_combo.currentTextChanged.connect(self.on_provider_changed)
        url_layout.addWidget(self.url_combo)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("请输入 API 地址")
        url_layout.addWidget(self.url_edit)
        weather_layout.addLayout(url_layout)

        # ---- API 密钥 ----
        lbl_key = QLabel("API 密钥")
        weather_layout.addWidget(lbl_key)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("请输入 API 密钥")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        weather_layout.addWidget(self.key_edit)

        # ---- 状态 + 刷新频率 ----
        status_layout = QHBoxLayout()
        self.status_label = QLabel("状态：未配置")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        freq_label1 = QLabel("每")
        status_layout.addWidget(freq_label1)
        self.freq_spin = QSpinBox()
        self.freq_spin.setRange(1, 1440)
        self.freq_spin.setSuffix(" 分钟")
        self.freq_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)  # 去掉箭头
        self.freq_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 2px 4px;
                background: white;
            }
        """)
        status_layout.addWidget(self.freq_spin)
        freq_label2 = QLabel("刷新天气")
        status_layout.addWidget(freq_label2)
        weather_layout.addLayout(status_layout)

        # ---- 空标签作为间距（隔一行效果） ----
        spacer = QLabel("")
        spacer.setFixedHeight(10)
        weather_layout.addWidget(spacer)

        # ---- 说明文字 ----
        info_label = QLabel("说明：API地址和密钥可在高德API免费获取，5000次/月，本程序默认每2小时更新一次天气")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; font-size: 12px; font-weight: normal;")
        weather_layout.addWidget(info_label)

        weather_layout.addStretch()
        right_layout.addWidget(self.page_weather)

        # ---- 底部按钮 ----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        right_layout.addLayout(btn_layout)

        main_layout.addWidget(self.right_panel)

        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)
        self.load_settings()

    def switch_page(self, index):
        pass

    def on_provider_changed(self, text):
        if text == "高德":
            self.url_edit.setText("https://restapi.amap.com")
            self.url_edit.setReadOnly(True)
        else:
            self.url_edit.clear()
            self.url_edit.setReadOnly(False)

    def load_settings(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        url = settings.value("api_url", "")
        key = settings.value("api_key", "")
        freq = int(settings.value("refresh_minutes", 120))
        self.url_edit.setText(url)
        self.key_edit.setText(key)
        self.freq_spin.setValue(freq)
        if url == "https://restapi.amap.com":
            self.url_combo.setCurrentText("高德")
        else:
            self.url_combo.setCurrentText("自定义")
        self.check_status()

    def check_status(self):
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        if not url or not key:
            self.status_label.setText("状态：❌ 未填写完整")
            return
        try:
            test_url = f"{url}/v3/ip?key={key}"
            resp = requests.get(test_url, timeout=3, verify=certifi.where())
            if resp.status_code == 200 and resp.json().get('status') == '1':
                self.status_label.setText("状态：✅ 已连接")
            else:
                self.status_label.setText("状态：❌ 连接失败（请检查地址和密钥）")
        except Exception:
            self.status_label.setText("状态：❌ 连接失败（网络或服务器错误）")

    def save_settings(self):
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        freq = self.freq_spin.value()
        if not url or not key:
            QMessageBox.warning(self, "提示", "请完整填写 API 地址和密钥")
            return
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("api_url", url)
        settings.setValue("api_key", key)
        settings.setValue("refresh_minutes", freq)
        self.accept()

    def reject(self):
        super().reject()

    def closeEvent(self, event):
        self.reject()
        event.accept()

# ---------- 主窗口 ----------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 加载图片
        self.bg_orig = QPixmap(resource_path("bg.png"))
        self.hour_orig = QPixmap(resource_path("Hour_Hand.png"))
        self.minute_orig = QPixmap(resource_path("Minute_Hand.png"))
        self.second_orig = QPixmap(resource_path("Second_Hand.png"))
        if any(p.isNull() for p in [self.bg_orig, self.hour_orig, self.minute_orig, self.second_orig]):
            sys.exit(1)

        self.orig_w, self.orig_h = 400, 297
        self.center_x, self.center_y = 200, 144

        self.resize(400, 297)
        self.drag_pos = None
        self._resizing = False

        # 数据
        self.cpu = 0
        self.gpu = 0
        self.mem = 0
        self.local_ip = self.get_local_ip()
        self.server_ip = "扫描中..."
        self.weather = {"weather": "--", "temp": "--", "wind": ""}
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

        # 缩放缓存
        self.scaled_bg = None
        self.scaled_hour = None
        self.scaled_minute = None
        self.scaled_second = None
        self.current_scale = 0

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
        # Y坐标减数改为 10（下移5像素，原为15）
        self.settings_btn.move(self.width() - self.settings_btn.width() - 15,
                               self.height() - self.settings_btn.height() - 1)
        self.settings_btn.mousePressEvent = self.on_settings_click

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
        # 按下反馈（短暂加深背景）
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
        QTimer.singleShot(50, self.show_menu)

    # ---------- 天气线程管理 ----------
    def start_weather_thread(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        api_url = settings.value("api_url", "")
        api_key = settings.value("api_key", "")
        refresh_minutes = int(settings.value("refresh_minutes", 120))

        if self.weather_thread is not None:
            self.weather_thread.quit()
            self.weather_thread.wait()

        self.weather_thread = WeatherThread(api_url, api_key, refresh_minutes)
        self.weather_thread.data_updated.connect(self.update_weather)
        self.weather_thread.error_signal.connect(self.on_weather_error)
        self.weather_thread.start()

    def on_weather_error(self, err_msg):
        self.weather = {"weather": "⚠️", "temp": "?", "wind": err_msg[:10] + "..."}
        self.update()

    def update_weather(self, data):
        self.weather = data
        self.update()

    # ---------- 菜单 ----------
    def show_menu(self):
        menu = QMenu(self)

        act_settings = QAction("⚙️ 设置", self)
        act_settings.triggered.connect(self.open_settings)
        menu.addAction(act_settings)

        act_theme = QAction("🎨 主题", self)
        act_theme.triggered.connect(lambda: QMessageBox.information(self, "提示", "主题功能开发中..."))
        menu.addAction(act_theme)

        act_update = QAction("🔄 检查更新", self)
        act_update.triggered.connect(lambda: QMessageBox.information(self, "提示", "检查更新功能开发中..."))
        menu.addAction(act_update)

        menu.addSeparator()

        act_exit = QAction("❌ 退出", self)
        act_exit.triggered.connect(self.confirm_exit)
        menu.addAction(act_exit)

        pos = self.settings_btn.mapToGlobal(self.settings_btn.rect().bottomRight())
        menu.exec(pos)

    def open_settings(self):
        try:
            dialog = SettingsDialog(self)
            dialog.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
            dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            dialog.move(
                self.x() + (self.width() - dialog.width()) // 2,
                self.y() + (self.height() - dialog.height()) // 2
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.start_weather_thread()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开设置失败：{str(e)}")

    def confirm_exit(self):
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QApplication.quit()

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

    # ---------- 窗口缩放 ----------
    def resizeEvent(self, event):
        QTimer.singleShot(0, self._apply_aspect_ratio)

    def _apply_aspect_ratio(self):
        if self._resizing:
            return
        self._resizing = True
        try:
            ratio = self.width() / self.height()
            target = self.orig_w / self.orig_h
            if abs(ratio - target) > 0.01:
                if ratio > target:
                    new_w = int(self.height() * target)
                    if abs(self.width() - new_w) > 2:
                        self.resize(new_w, self.height())
                else:
                    new_h = int(self.width() / target)
                    if abs(self.height() - new_h) > 2:
                        self.resize(self.width(), new_h)
            self._update_caches()
            # 同步更新设置按钮位置（Y坐标减数改为10）
            self.settings_btn.move(self.width() - self.settings_btn.width() - 15,
                                   self.height() - self.settings_btn.height() - 1)
        except: pass
        finally:
            self._resizing = False

    def _update_caches(self):
        scale = min(self.width() / self.orig_w, self.height() / self.orig_h)
        if scale <= 0: scale = 0.1
        if abs(scale - self.current_scale) < 0.001:
            return
        self.current_scale = scale
        w, h = self.width(), self.height()
        self.scaled_bg = self.bg_orig.scaled(w, h,
                                             Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation)
        pw, ph = int(self.orig_w * scale), int(self.orig_h * scale)
        self.scaled_hour = self.hour_orig.scaled(pw, ph,
                                                 Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation)
        self.scaled_minute = self.minute_orig.scaled(pw, ph,
                                                     Qt.AspectRatioMode.KeepAspectRatio,
                                                     Qt.TransformationMode.SmoothTransformation)
        self.scaled_second = self.second_orig.scaled(pw, ph,
                                                     Qt.AspectRatioMode.KeepAspectRatio,
                                                     Qt.TransformationMode.SmoothTransformation)

    # ---------- 绘制 ----------
    def paintEvent(self, event):
        self.paint_count += 1
        if self.scaled_bg is None:
            self._update_caches()
        scale = self.current_scale
        if scale <= 0: scale = 0.1

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(255, 255, 255, 1))

        # 背景
        painter.drawPixmap(0, 0, self.scaled_bg)

        # ----- 文字（固定 10 号，#1c344d） -----
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        painter.setPen(QPen(QColor("#1c344d")))

        weather_icon = get_weather_icon(self.weather['weather'])
        weather_text = f"{weather_icon} {self.weather['weather']} {self.weather['temp']}℃"

        items = [
            (20, 30, 105, 15, f"{self.local_ip}", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (280, 30, 94, 15, weather_text, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (20, 86, 85, 43, f"↓{self.down_speed:.1f}Mb/s\n↑{self.up_speed:.1f}Mb/s", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (314, 86, 71, 43, f"CPU{int(self.cpu)}%\nGPU{int(self.gpu)}%", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (20, 166, 70, 50, f"刷新率: {self.fps}\n{self.screen_res}", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (319, 166, 60, 50, f"内存\n{int(self.mem)}%", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (20, 235, 88, 50, f"{self.now.strftime('%Y/%m/%d')}\n  星期{['一','二','三','四','五','六','日'][self.now.weekday()]}", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            (273, 238, 97, 43, f"农历{self.lunar_text}\n{self.term_display}", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
        ]

        for x, y, w, h, text, align in items:
            rx = int(x * scale)
            ry = int(y * scale)
            rw = int(w * scale)
            rh = int(h * scale)
            painter.drawText(rx, ry, rw, rh, align, text)

        # ----- 指针 -----
        cx = int(self.center_x * scale)
        cy = int(self.center_y * scale)
        now = self.now
        self.draw_hand(painter, self.scaled_hour, cx, cy, (now.hour % 12) * 30 + now.minute * 0.5)
        self.draw_hand(painter, self.scaled_minute, cx, cy, now.minute * 6 + now.second * 0.1)
        self.draw_hand(painter, self.scaled_second, cx, cy, now.second * 6)

        # 中心圆点
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
        painter.setPen(Qt.PenStyle.NoPen)
        r = max(1, int(12 * scale))
        painter.drawEllipse(cx - r, cy - r, 2*r, 2*r)

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

# ---------- 入口 ----------
if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        os.environ['PYTHONWARNINGS'] = 'ignore'
        import logging
        logging.getLogger().setLevel(logging.ERROR)

    app = QApplication(sys.argv)
    app.setOrganizationName("MyDesktopApp")
    app.setApplicationName("WeatherSettings")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())