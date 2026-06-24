from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
import requests
import certifi


class WeatherPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(5)

        # API 地址
        lbl_url = QLabel("API 地址")
        layout.addWidget(lbl_url)
        url_layout = QHBoxLayout()
        self.url_combo = QComboBox()
        self.url_combo.addItems(["高德", "自定义"])
        self.url_combo.currentTextChanged.connect(self.on_provider_changed)
        url_layout.addWidget(self.url_combo)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("请输入 API 地址")
        url_layout.addWidget(self.url_edit)
        layout.addLayout(url_layout)

        # API 密钥
        lbl_key = QLabel("API 密钥")
        layout.addWidget(lbl_key)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("请输入 API 密钥")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_edit)

        # 状态 + 刷新频率
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
        layout.addLayout(status_layout)

        # 保存按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("保存")
        self.save_btn.setFixedWidth(80)
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

        # 说明文字
        info_label = QLabel("说明：API地址和密钥可在高德API免费获取，5000次/月，本程序默认每2小时更新一次天气")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; font-size: 12px; font-weight: normal;")
        layout.addWidget(info_label)

        layout.addStretch()

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

        # ===== 地区变化时清空经纬度缓存 =====
        # 获取当前选择的地区
        province = settings.value("selected_province", "")
        city = settings.value("selected_city", "")
        county = settings.value("selected_county", "")
        if province and city:
            # 地区已保存，清空旧的经纬度缓存，让天气线程重新获取
            settings.remove("cached_lat")
            settings.remove("cached_lng")

        self.check_status()
        QMessageBox.information(self, "提示", "天气设置已保存")

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
        except requests.RequestException:
            self.status_label.setText("状态：❌ 连接失败（网络或服务器错误）")