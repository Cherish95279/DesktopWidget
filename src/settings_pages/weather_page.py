from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
import requests
import certifi
from ..region_data import REGIONS


class WeatherPage(QWidget):
    region_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self._updating = False
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(8)

        # ---------- 第一排：API 地址（标签） ----------
        lbl_url = QLabel("API 地址")
        layout.addWidget(lbl_url)

        # ---------- 第二排：高德下拉框 + URL 输入框 ----------
        url_layout = QHBoxLayout()
        self.url_combo = QComboBox()
        self.url_combo.addItems(["高德", "自定义"])
        self.url_combo.currentTextChanged.connect(self.on_provider_changed)
        url_layout.addWidget(self.url_combo)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("请输入 API 地址")
        self.url_edit.textChanged.connect(self.on_url_changed)
        url_layout.addWidget(self.url_edit)
        layout.addLayout(url_layout)

        # ---------- 第三排：API 密钥（标签） ----------
        lbl_key = QLabel("API 密钥")
        layout.addWidget(lbl_key)

        # ---------- 第四排：密钥输入框 ----------
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("请输入 API 密钥")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.textChanged.connect(self.on_key_changed)
        layout.addWidget(self.key_edit)

        # ---------- 第五排：状态 + 刷新频率（同一行） ----------
        status_freq_layout = QHBoxLayout()

        self.status_label = QLabel("状态：未配置")
        status_freq_layout.addWidget(self.status_label)

        status_freq_layout.addStretch()

        freq_label1 = QLabel("每")
        status_freq_layout.addWidget(freq_label1)

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
        self.freq_spin.valueChanged.connect(self.on_freq_changed)
        status_freq_layout.addWidget(self.freq_spin)

        freq_label2 = QLabel("刷新天气")
        status_freq_layout.addWidget(freq_label2)

        layout.addLayout(status_freq_layout)

        # ---------- 说明文字（移到天气显示地区上方） ----------
        info_label = QLabel(
            '说明：API地址和密钥可在 <a href="https://lbs.amap.com/" style="color: #0366d6; text-decoration: none;">高德API</a> 免费获取，5000次/月'
        )
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; font-size: 12px; font-weight: normal;")
        layout.addWidget(info_label)

        # ---------- 天气显示地区（标签） ----------
        region_label = QLabel("天气显示地区")
        region_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout.addWidget(region_label)

        # ---------- 三个地区下拉框 ----------
        region_layout = QHBoxLayout()
        self.province_combo = QComboBox()
        self.province_combo.setMinimumWidth(80)
        self.city_combo = QComboBox()
        self.city_combo.setMinimumWidth(80)
        self.county_combo = QComboBox()
        self.county_combo.setMinimumWidth(80)
        region_layout.addWidget(self.province_combo)
        region_layout.addWidget(self.city_combo)
        region_layout.addWidget(self.county_combo)
        region_layout.addStretch()
        layout.addLayout(region_layout)

        layout.addStretch()

        # ---------- 信号连接 ----------
        self.province_combo.currentTextChanged.connect(self.on_province_changed)
        self.city_combo.currentTextChanged.connect(self.on_city_changed)
        self.county_combo.currentTextChanged.connect(self.on_county_changed)

        self.load_regions_data()

    # ---------- 地区数据 ----------
    def load_regions_data(self):
        provinces = list(REGIONS.keys())
        self.province_combo.clear()
        self.province_combo.addItem("请选择省份")
        self.province_combo.addItems(provinces)

    def on_province_changed(self, province):
        self.city_combo.clear()
        self.city_combo.addItem("请选择城市")
        if province and province in REGIONS:
            cities = list(REGIONS[province].get("cities", {}).keys())
            self.city_combo.addItems(cities)
        self.county_combo.clear()
        self.county_combo.addItem("请选择区县")
        self.load_city_if_saved()

    def load_city_if_saved(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        saved_city = settings.value("selected_city", "")
        saved_county = settings.value("selected_county", "")
        if saved_city:
            idx = self.city_combo.findText(saved_city)
            if idx >= 0:
                self.city_combo.setCurrentIndex(idx)
                self.on_city_changed(saved_city)
                if saved_county:
                    idx_c = self.county_combo.findText(saved_county)
                    if idx_c >= 0:
                        self.county_combo.setCurrentIndex(idx_c)

    def on_city_changed(self, city):
        self.county_combo.clear()
        self.county_combo.addItem("请选择区县")
        province = self.province_combo.currentText()
        if province and city and province in REGIONS:
            counties = REGIONS[province].get("cities", {}).get(city, {}).get("counties", [])
            self.county_combo.addItems(counties)
        if city and city != "请选择城市":
            self.save_region_and_refresh()

    def on_county_changed(self, county):
        if county and county != "请选择区县":
            self.save_region_and_refresh()

    # ---------- API 相关 ----------
    def on_provider_changed(self, text):
        if text == "高德":
            self.url_edit.setText("https://restapi.amap.com")
            self.url_edit.setReadOnly(True)
        else:
            self.url_edit.clear()
            self.url_edit.setReadOnly(False)
        self.save_api_settings()

    def on_url_changed(self, text):
        if not self._updating:
            self.save_api_settings()

    def on_key_changed(self, text):
        if not self._updating:
            self.save_api_settings()

    def on_freq_changed(self, value):
        if not self._updating:
            self.save_api_settings()

    # ---------- 保存方法 ----------
    def save_api_settings(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("api_url", self.url_edit.text().strip())
        settings.setValue("api_key", self.key_edit.text().strip())
        settings.setValue("refresh_minutes", self.freq_spin.value())
        self.check_status()

    def save_region_and_refresh(self):
        province = self.province_combo.currentText()
        city = self.city_combo.currentText()
        county = self.county_combo.currentText()

        if province != "请选择省份" and city != "请选择城市":
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            settings.setValue("selected_province", province)
            settings.setValue("selected_city", city)
            if county != "请选择区县":
                settings.setValue("selected_county", county)
            else:
                settings.remove("selected_county")

            settings.remove("cached_lat")
            settings.remove("cached_lng")
            settings.sync()

            self.region_changed.emit()
            parent = self.parent()
            if parent and hasattr(parent, 'parent'):
                main_window = parent.parent()
                if main_window and hasattr(main_window, 'start_weather_thread'):
                    main_window.start_weather_thread()

    # ---------- 加载设置 ----------
    def load_regions(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        province = settings.value("selected_province", "")
        city = settings.value("selected_city", "")
        county = settings.value("selected_county", "")

        if province:
            idx = self.province_combo.findText(province)
            if idx >= 0:
                self.province_combo.setCurrentIndex(idx)
                self.on_province_changed(province)
        if city:
            idx_city = self.city_combo.findText(city)
            if idx_city >= 0:
                self.city_combo.setCurrentIndex(idx_city)
                self.on_city_changed(city)
        if county:
            idx_county = self.county_combo.findText(county)
            if idx_county >= 0:
                self.county_combo.setCurrentIndex(idx_county)

    def load_settings(self):
        self._updating = True
        try:
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

            self.load_regions()
            self.check_status()
        finally:
            self._updating = False

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