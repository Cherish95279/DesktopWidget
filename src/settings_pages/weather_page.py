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
        self._signal_connected = False
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(8)

        # ---------- API 地址 ----------
        lbl_url = QLabel("API 地址")
        layout.addWidget(lbl_url)

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

        # ---------- API 密钥 ----------
        lbl_key = QLabel("API 密钥")
        layout.addWidget(lbl_key)

        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("请输入 API 密钥")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.textChanged.connect(self.on_key_changed)
        layout.addWidget(self.key_edit)

        # ---------- 状态 + 刷新频率 ----------
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

        # ---------- 说明文字 ----------
        info_label = QLabel(
            '说明：API地址和密钥可在 <a href="https://lbs.amap.com/" style="color: #0366d6; text-decoration: none;">高德API</a> 免费获取，5000次/月'
        )
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; font-size: 12px; font-weight: normal;")
        layout.addWidget(info_label)

        # ---------- 天气显示地区 ----------
        region_label = QLabel("天气显示地区")
        region_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout.addWidget(region_label)

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
            self._refresh_main_window_weather()

    def _refresh_main_window_weather(self):
        """刷新主窗口天气（强制重启天气线程）"""
        main_window = None
        if self.parent_dialog and hasattr(self.parent_dialog, 'parent'):
            main_window = self.parent_dialog.parent()
        if not main_window:
            parent = self.parent()
            if parent and hasattr(parent, 'parent'):
                main_window = parent.parent()
        if main_window and hasattr(main_window, 'start_weather_thread'):
            main_window.start_weather_thread(force_restart=True)
            if hasattr(main_window, 'update'):
                main_window.update()

    # ---------- 加载设置 ----------
    def load_regions(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        province = settings.value("selected_province", "")
        city = settings.value("selected_city", "")
        county = settings.value("selected_county", "")

        # ===== 阻塞信号，避免触发任何回调 =====
        self.province_combo.blockSignals(True)
        self.city_combo.blockSignals(True)
        self.county_combo.blockSignals(True)

        # ---- 1. 恢复省份 ----
        if province:
            idx = self.province_combo.findText(province)
            if idx >= 0:
                self.province_combo.setCurrentIndex(idx)
        else:
            self.province_combo.setCurrentIndex(0)

        # ---- 2. 填充城市列表 ----
        current_province = self.province_combo.currentText()
        self.city_combo.clear()
        self.city_combo.addItem("请选择城市")
        if current_province and current_province != "请选择省份" and current_province in REGIONS:
            cities = list(REGIONS[current_province].get("cities", {}).keys())
            self.city_combo.addItems(cities)

        # ---- 3. 恢复城市 ----
        if city:
            idx_city = self.city_combo.findText(city)
            if idx_city >= 0:
                self.city_combo.setCurrentIndex(idx_city)
        else:
            self.city_combo.setCurrentIndex(0)

        # ---- 4. 填充区县列表 ----
        current_city = self.city_combo.currentText()
        self.county_combo.clear()
        self.county_combo.addItem("请选择区县")
        if current_province and current_province != "请选择省份" and current_city and current_city != "请选择城市":
            if current_province in REGIONS:
                cities_data = REGIONS[current_province].get("cities", {})
                if current_city in cities_data:
                    counties = cities_data[current_city].get("counties", [])
                    self.county_combo.addItems(counties)

        # ---- 5. 恢复区县 ----
        if county:
            idx_county = self.county_combo.findText(county)
            if idx_county >= 0:
                self.county_combo.setCurrentIndex(idx_county)
        else:
            self.county_combo.setCurrentIndex(0)

        # ===== 恢复信号 =====
        self.province_combo.blockSignals(False)
        self.city_combo.blockSignals(False)
        self.county_combo.blockSignals(False)

        # 注意：这里不触发任何 weather refresh

    def _get_main_window(self):
        """获取主窗口实例"""
        if self.parent_dialog and hasattr(self.parent_dialog, 'parent'):
            return self.parent_dialog.parent()
        parent = self.parent()
        if parent and hasattr(parent, 'parent'):
            return parent.parent()
        return None

    def _connect_weather_signal(self):
        """连接主窗口的天气更新信号，实时刷新状态"""
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, 'weather_thread'):
            weather_thread = main_window.weather_thread
            if weather_thread:
                try:
                    weather_thread.data_updated.disconnect(self._on_weather_updated)
                except:
                    pass
                weather_thread.data_updated.connect(self._on_weather_updated)
                self._signal_connected = True

    def _on_weather_updated(self, data):
        """天气数据更新时刷新状态"""
        self.check_status()

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

            # 连接天气更新信号，实时刷新状态
            self._connect_weather_signal()

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