from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
import requests
import certifi
from .constants import VERSION

class SettingsDialog(QDialog):
    def __init__(self, parent=None, initial_page="weather"):
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
        # 第一行：天气设置
        btn_weather = QPushButton("天气设置")
        btn_weather.setFixedHeight(40)
        btn_weather.setFlat(True)
        btn_weather.setStyleSheet("""
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
        btn_weather.setCheckable(True)
        btn_weather.setAutoExclusive(True)
        btn_weather.setChecked(True)
        left_layout.addWidget(btn_weather)
        self.cat_buttons.append(btn_weather)

        # 第二行：关于
        btn_about = QPushButton("关于")
        btn_about.setFixedHeight(40)
        btn_about.setFlat(True)
        btn_about.setStyleSheet("""
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
        btn_about.setCheckable(True)
        btn_about.setAutoExclusive(True)
        left_layout.addWidget(btn_about)
        self.cat_buttons.append(btn_about)

        # 其余三行留空（隐藏）
        for i in range(3):
            btn = QPushButton("")
            btn.setFixedHeight(40)
            btn.setFlat(True)
            btn.setVisible(False)
            left_layout.addWidget(btn)
            self.cat_buttons.append(btn)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # ---------- 右侧内容（使用 QStackedWidget） ----------
        self.stacked = QStackedWidget()
        self.stacked.setStyleSheet("background-color: rgba(245, 245, 245, 0.9);")

        # 页面1：天气设置
        page_weather = QWidget()
        weather_layout = QVBoxLayout(page_weather)
        weather_layout.setContentsMargins(15, 20, 15, 15)
        weather_layout.setSpacing(5)

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

        lbl_key = QLabel("API 密钥")
        weather_layout.addWidget(lbl_key)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("请输入 API 密钥")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        weather_layout.addWidget(self.key_edit)

        status_layout = QHBoxLayout()
        self.status_label = QLabel("状态：未配置")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        freq_label1 = QLabel("每")
        status_layout.addWidget(freq_label1)
        self.freq_spin = QSpinBox()
        self.freq_spin.setRange(1, 1440)
        self.freq_spin.setSuffix(" 分钟")
        self.freq_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
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

        spacer = QLabel("")
        spacer.setFixedHeight(10)
        weather_layout.addWidget(spacer)

        info_label = QLabel("说明：API地址和密钥可在高德API免费获取，5000次/月，本程序默认每2小时更新一次天气")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; font-size: 12px; font-weight: normal;")
        weather_layout.addWidget(info_label)

        weather_layout.addStretch()
        self.stacked.addWidget(page_weather)

        # 页面2：关于
        page_about = QWidget()
        about_layout = QVBoxLayout(page_about)
        about_layout.setContentsMargins(15, 20, 15, 15)
        about_layout.setSpacing(10)

        title = QLabel(f"珍爱桌面小工具 {VERSION}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(title)

        author = QLabel("作者：Cherish95279")
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(author)

        thanks = QLabel("致谢：fqk_123456")
        thanks.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(thanks)

        github = QLabel('<a href="https://github.com/Cherish95279/DesktopWidget">GitHub：https://github.com/Cherish95279/DesktopWidget</a>')
        github.setOpenExternalLinks(True)
        github.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(github)

        info = QLabel("基于 PyQt6 开发 | 天气数据由高德地图提供")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        about_layout.addWidget(info)

        about_layout.addStretch()
        self.stacked.addWidget(page_about)

        # ---------- 将 stacked 放入右侧面板 ----------
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.stacked)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        right_layout.addLayout(btn_layout)

        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        right_widget.setStyleSheet("background-color: rgba(245, 245, 245, 0.9);")
        main_layout.addWidget(right_widget)

        # 连接信号
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)
        btn_weather.clicked.connect(lambda: self.switch_page("weather"))
        btn_about.clicked.connect(lambda: self.switch_page("about"))

        # 设置初始页面
        self.switch_page(initial_page)

        # 加载设置
        self.load_settings()

    def switch_page(self, page):
        if page == "weather":
            self.stacked.setCurrentIndex(0)
            self.cat_buttons[0].setChecked(True)
            self.cat_buttons[1].setChecked(False)
        elif page == "about":
            self.stacked.setCurrentIndex(1)
            self.cat_buttons[0].setChecked(False)
            self.cat_buttons[1].setChecked(True)

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