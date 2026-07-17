from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
import requests
import certifi
import json
import re
from ..region_data import REGIONS


# ===== 统一下拉框样式 =====
COMBO_STYLE = """
    QComboBox {
        border: 1px solid #ccc;
        border-radius: 4px;
        background: #f5f5f5;
        color: #333;
        font-size: 12px;
        padding: 0 4px;
        height: 28px;
    }
    QComboBox:hover {
        background: #e6f4ff;
        border: 1px solid #1677ff;
        color: #1677ff;
    }
"""

# ===== 统一输入框样式 =====
LINEEDIT_STYLE = """
    QLineEdit {
        border: 1px solid #ccc;
        border-radius: 4px;
        background: white;
        color: #333;
        font-size: 12px;
        padding: 2px 6px;
        height: 28px;
    }
    QLineEdit:focus {
        border: 1px solid #1677ff;
        background: #fafaff;
    }
"""

# ===== 统一数字输入框样式 =====
SPINBOX_STYLE = """
    QSpinBox {
        border: 1px solid #ccc;
        border-radius: 4px;
        background: white;
        color: #333;
        font-size: 12px;
        padding: 2px 6px;
        height: 28px;
    }
    QSpinBox:focus {
        border: 1px solid #1677ff;
        background: #fafaff;
    }
    QSpinBox::up-button, QSpinBox::down-button {
        width: 16px;
    }
"""


class GeocodingThread(QThread):
    """后台线程：调用 Open-Meteo Geocoding API"""
    result_ready = pyqtSignal(list)
    search_failed = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query.strip()

    def run(self):
        if not self.query or len(self.query) < 2:
            self.search_failed.emit("输入太短")
            return

        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            "name": self.query,
            "language": "zh",
            "count": 10,
            "format": "json"
        }

        try:
            resp = requests.get(url, params=params, timeout=8)
            if resp.status_code != 200:
                self.search_failed.emit(f"HTTP {resp.status_code}")
                return

            data = resp.json()
            results = data.get("results", [])
            if not results:
                self.search_failed.emit("未找到匹配地点")
                return

            formatted_results = []
            for item in results:
                name = item.get("name", "")
                admin1 = item.get("admin1", "")
                country = item.get("country", "")
                parts = [p for p in [name, admin1, country] if p]
                display_text = ", ".join(parts)
                formatted_results.append({
                    "display": display_text,
                    "name": name,
                    "admin1": admin1,
                    "country": country,
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                })

            self.result_ready.emit(formatted_results)

        except requests.exceptions.Timeout:
            self.search_failed.emit("搜索超时")
        except requests.exceptions.ConnectionError:
            self.search_failed.emit("网络连接失败")
        except Exception as e:
            self.search_failed.emit(f"搜索异常: {str(e)}")


class WeatherPage(QWidget):
    region_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self._updating = False
        self._signal_connected = False
        self._loading = False
        self._search_timer = None
        self._geocoding_thread = None
        self._selected_lat = None
        self._selected_lng = None
        self._selected_display = None
        self._block_search = False  # 防止程序设置文本时触发搜索

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(8)

        # ---------- API 地址 ----------
        lbl_url = QLabel(self.tr("API 地址"))
        layout.addWidget(lbl_url)

        url_layout = QHBoxLayout()
        self.url_combo = QComboBox()
        self.url_combo.setFixedHeight(28)
        self.url_combo.setStyleSheet(COMBO_STYLE)
        self.url_combo.addItems([self.tr("高德"), self.tr("自定义")])
        self.url_combo.currentTextChanged.connect(self.on_provider_changed)
        url_layout.addWidget(self.url_combo)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(self.tr("请输入 API 地址"))
        self.url_edit.setStyleSheet(LINEEDIT_STYLE)
        self.url_edit.setFixedHeight(28)
        self.url_edit.textChanged.connect(self.on_url_changed)
        url_layout.addWidget(self.url_edit)
        layout.addLayout(url_layout)

        # ---------- API 密钥 ----------
        lbl_key = QLabel(self.tr("API 密钥"))
        layout.addWidget(lbl_key)

        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText(self.tr("请输入 API 密钥"))
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setStyleSheet(LINEEDIT_STYLE)
        self.key_edit.setFixedHeight(28)
        self.key_edit.textChanged.connect(self.on_key_changed)
        layout.addWidget(self.key_edit)

        # ---------- 状态 + 刷新频率 ----------
        status_freq_layout = QHBoxLayout()
        self.status_label = QLabel(self.tr("状态：未配置"))
        status_freq_layout.addWidget(self.status_label)
        status_freq_layout.addStretch()

        freq_label1 = QLabel(self.tr("每"))
        status_freq_layout.addWidget(freq_label1)

        self.freq_spin = QSpinBox()
        self.freq_spin.setRange(1, 1440)
        self.freq_spin.setSuffix(self.tr(" 分钟"))
        self.freq_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.freq_spin.setStyleSheet(SPINBOX_STYLE)
        self.freq_spin.setFixedHeight(28)
        self.freq_spin.setFixedWidth(90)
        self.freq_spin.valueChanged.connect(self.on_freq_changed)
        status_freq_layout.addWidget(self.freq_spin)

        freq_label2 = QLabel(self.tr("刷新天气"))
        status_freq_layout.addWidget(freq_label2)

        layout.addLayout(status_freq_layout)

        # ---------- 说明文字 ----------
        info_label = QLabel(
            self.tr(
                "说明：API地址和密钥可在 ") + '<a href="https://lbs.amap.com/" style="color: #0366d6; text-decoration: none;">' + self.tr(
                "高德API") + '</a> ' + self.tr("免费获取，5000次/月")
        )
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; font-size: 12px; font-weight: normal;")
        layout.addWidget(info_label)

        # ---------- 天气显示地区 ----------
        region_label = QLabel(self.tr("天气显示地区"))
        region_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout.addWidget(region_label)

        # 搜索框布局（搜索框 + 状态标签）
        search_layout = QHBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("输入城市名称（如 北京、New York）"))
        self.search_edit.setStyleSheet(LINEEDIT_STYLE)
        self.search_edit.setFixedHeight(28)
        self.search_edit.setMinimumWidth(250)
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.search_edit.returnPressed.connect(self._on_search_triggered)
        search_layout.addWidget(self.search_edit)

        self.search_status_label = QLabel("")
        self.search_status_label.setStyleSheet("font-size: 11px; color: #999;")
        search_layout.addWidget(self.search_status_label)

        search_layout.addStretch()
        layout.addLayout(search_layout)

        # 搜索结果列表
        self.result_list = QListWidget()
        self.result_list.setFixedHeight(100)
        self.result_list.setStyleSheet("""
            QListWidget {
                background: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
                padding: 2px;
            }
            QListWidget::item {
                padding: 2px 6px;
            }
            QListWidget::item:hover {
                background: #e6f4ff;
            }
            QListWidget::item:selected {
                background: #d0e4ff;
                color: #1677ff;
            }
        """)
        self.result_list.itemClicked.connect(self._on_result_selected)
        self.result_list.hide()
        layout.addWidget(self.result_list)

        # 当前选中地区显示（只读）
        self.current_location_label = QLabel(self.tr("当前地区：未选择"))
        self.current_location_label.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(self.current_location_label)

        layout.addStretch()

    # ---------- 本地搜索 ----------
    def _contains_chinese(self, text: str) -> bool:
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def _search_local_regions(self, query: str) -> list:
        results = []
        query_lower = query.lower()
        for province, province_data in REGIONS.items():
            if query_lower in province.lower():
                results.append({
                    "display": province,
                    "name": province,
                    "admin1": "",
                    "country": "中国",
                    "latitude": None,
                    "longitude": None,
                    "type": "province"
                })
            cities = province_data.get("cities", {})
            for city, city_data in cities.items():
                if query_lower in city.lower():
                    results.append({
                        "display": f"{city}, {province}",
                        "name": city,
                        "admin1": province,
                        "country": "中国",
                        "latitude": None,
                        "longitude": None,
                        "type": "city"
                    })
                counties = city_data.get("counties", [])
                for county in counties:
                    if query_lower in county.lower():
                        results.append({
                            "display": f"{county}, {city}, {province}",
                            "name": county,
                            "admin1": city,
                            "country": "中国",
                            "latitude": None,
                            "longitude": None,
                            "type": "county"
                        })
        seen = set()
        unique_results = []
        for r in results:
            key = r["display"]
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        type_order = {"county": 0, "city": 1, "province": 2}
        unique_results.sort(key=lambda x: type_order.get(x.get("type", "province"), 2))
        return unique_results[:10]

    # ---------- 搜索相关 ----------
    def _on_search_text_changed(self, text):
        # 如果正在程序主动设置文本，跳过所有操作
        if self._block_search:
            return

        if self._search_timer is not None:
            self._search_timer.stop()
            self._search_timer = None

        if len(text.strip()) < 2:
            self.result_list.clear()
            self.result_list.hide()
            self.search_status_label.setText("")
            return

        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search_triggered)
        self._search_timer.start(500)

    def _on_search_triggered(self):
        query = self.search_edit.text().strip()
        if len(query) < 2:
            return

        # 重置标志，确保用户输入触发的搜索正常工作
        self._block_search = False

        self.search_status_label.setText(self.tr("搜索中..."))
        self.result_list.clear()
        self.result_list.hide()

        if self._geocoding_thread is not None and self._geocoding_thread.isRunning():
            self._geocoding_thread.quit()
            self._geocoding_thread.wait()
            self._geocoding_thread = None

        if self._contains_chinese(query):
            local_results = self._search_local_regions(query)
            if local_results:
                self._display_local_results(local_results)
                return

        self._geocoding_thread = GeocodingThread(query)
        self._geocoding_thread.result_ready.connect(self._on_search_result)
        self._geocoding_thread.search_failed.connect(self._on_search_failed)
        self._geocoding_thread.start()

    def _display_local_results(self, results):
        self.search_status_label.setText("")
        self.result_list.clear()

        if self._geocoding_thread is not None and self._geocoding_thread.isRunning():
            self._geocoding_thread.quit()
            self._geocoding_thread.wait()
            self._geocoding_thread = None

        self._search_results = results

        for item in results:
            self.result_list.addItem(item["display"])

        self.result_list.show()

        if len(results) > 1:
            self.search_status_label.setText(f"✅ {self.tr('已找到')} {len(results)} {self.tr('个结果')}")
        else:
            self.result_list.setCurrentRow(0)
            self._on_result_selected(self.result_list.item(0))

    def _on_search_result(self, results):
        self.result_list.clear()
        self.search_status_label.setText("")

        if not results:
            self.search_status_label.setText("❌ " + self.tr("未找到匹配地点"))
            return

        self._search_results = results

        for item in results:
            self.result_list.addItem(item["display"])

        self.result_list.show()

        if len(results) == 1:
            self.result_list.setCurrentRow(0)
            self._on_result_selected(self.result_list.item(0))
        else:
            self.search_status_label.setText(f"✅ {self.tr('已找到')} {len(results)} {self.tr('个结果')}")

    def _on_search_failed(self, err_msg):
        self.search_status_label.setText(f"❌ {err_msg}")
        self.result_list.clear()
        self.result_list.hide()

    def _on_result_selected(self, item):
        if not hasattr(self, '_search_results'):
            return

        index = self.result_list.row(item)
        if index < 0 or index >= len(self._search_results):
            return

        result = self._search_results[index]
        self._selected_display = result["display"]
        self._selected_lat = result.get("latitude")
        self._selected_lng = result.get("longitude")

        settings = QSettings("MyDesktopApp", "WeatherSettings")
        if result.get("type") in ["county", "city"]:
            settings.setValue("selected_city", result["name"])
            if result.get("type") == "county":
                settings.setValue("selected_county", result["name"])
                settings.setValue("selected_province", result.get("admin1", ""))
            else:
                settings.setValue("selected_county", "")
                settings.setValue("selected_province", result.get("admin1", ""))
        else:
            settings.setValue("selected_city", result["name"])
            settings.setValue("selected_province", result["name"])
            settings.setValue("selected_county", "")

        settings.setValue("selected_location_display", self._selected_display)
        if self._selected_lat is not None and self._selected_lng is not None:
            settings.setValue("selected_latitude", self._selected_lat)
            settings.setValue("selected_longitude", self._selected_lng)
        else:
            settings.remove("selected_latitude")
            settings.remove("selected_longitude")
        settings.sync()

        # 程序主动设置搜索框文本，阻止触发搜索
        self._block_search = True
        self.search_edit.setText(self._selected_display)
        self._block_search = False

        self.current_location_label.setText(f"{self.tr('当前地区')}：{self._selected_display}")

        self.search_status_label.setText("✅ " + self.tr("已选择"))
        self.result_list.hide()

        self.region_changed.emit()
        self._refresh_main_window_weather()

    # ---------- API 相关 ----------
    def on_provider_changed(self, text):
        if self._loading:
            return
        if text == "高德":
            self.url_edit.setText("https://restapi.amap.com")
            self.url_edit.setReadOnly(True)
        else:
            self.url_edit.clear()
            self.url_edit.setReadOnly(False)
        self.save_api_settings()

    def on_url_changed(self, text):
        if not self._updating and not self._loading:
            self.save_api_settings()

    def on_key_changed(self, text):
        if not self._updating and not self._loading:
            self.save_api_settings()

    def on_freq_changed(self, value):
        if not self._updating and not self._loading:
            self.save_api_settings()

    def save_api_settings(self):
        if self._loading:
            return
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("api_url", self.url_edit.text().strip())
        settings.setValue("api_key", self.key_edit.text().strip())
        settings.setValue("refresh_minutes", self.freq_spin.value())
        self.check_status()

    def save_region_and_refresh(self):
        if self._loading:
            return
        if self._selected_display:
            self.region_changed.emit()
            self._refresh_main_window_weather()

    def _refresh_main_window_weather(self):
        if self._loading:
            return
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
        location_display = settings.value("selected_location_display", "")
        lat = settings.value("selected_latitude", "")
        lng = settings.value("selected_longitude", "")

        if location_display and lat and lng:
            self._selected_display = location_display
            self._selected_lat = float(lat)
            self._selected_lng = float(lng)
            self._block_search = True
            self.search_edit.setText(location_display)
            self._block_search = False
            self.current_location_label.setText(f"{self.tr('当前地区')}：{location_display}")
        else:
            province = settings.value("selected_province", "")
            city = settings.value("selected_city", "")
            county = settings.value("selected_county", "")
            if county:
                display = f"{county}, {city}, {province}"
            elif city:
                display = f"{city}, {province}"
            elif province:
                display = province
            else:
                display = ""
            if display:
                self._block_search = True
                self.search_edit.setText(display)
                self._block_search = False
                self.current_location_label.setText(f"{self.tr('当前地区')}：{display}")
            else:
                self.search_edit.clear()
                self.current_location_label.setText(self.tr("当前地区：未选择"))

    def _get_main_window(self):
        if self.parent_dialog and hasattr(self.parent_dialog, 'parent'):
            return self.parent_dialog.parent()
        parent = self.parent()
        if parent and hasattr(parent, 'parent'):
            return parent.parent()
        return None

    def _connect_weather_signal(self):
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
        self.check_status()

    def load_settings(self):
        self._updating = True
        self._loading = True
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
            self._connect_weather_signal()

        finally:
            self._loading = False
            self._updating = False

    def check_status(self):
        if self._loading:
            return
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        if not url or not key:
            self.status_label.setText(self.tr("状态") + "：❌ " + self.tr("未填写完整"))
            return
        try:
            test_url = f"{url}/v3/ip?key={key}"
            resp = requests.get(test_url, timeout=3, verify=certifi.where())
            if resp.status_code == 200 and resp.json().get('status') == '1':
                self.status_label.setText(self.tr("状态") + "：✅ " + self.tr("已连接"))
            else:
                self.status_label.setText(self.tr("状态") + "：❌ " + self.tr("连接失败（请检查地址和密钥）"))
        except requests.RequestException:
            self.status_label.setText(self.tr("状态") + "：❌ " + self.tr("连接失败（网络或服务器错误）"))