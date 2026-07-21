from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtCore import QCoreApplication
import requests
import certifi
import json
import re
from ..region_data import REGIONS, get_coords_by_name, get_coords_for_city


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
    """后台线程：Open-Meteo Geocoding API + Nominatim 回退"""
    result_ready = pyqtSignal(list)
    search_failed = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query.strip()

    def _search_open_meteo(self):
        """主搜索引擎：Open-Meteo Geocoding"""
        url = "https://geocoding-api.open-meteo.com/v1/search"
        app_lang = QSettings("MyDesktopApp", "WeatherSettings").value("language", "")
        geocoding_lang = app_lang.split("_")[0] if "_" in app_lang else (app_lang or "zh")
        params = {
            "name": self.query,
            "language": geocoding_lang,
            "count": 10,
            "format": "json"
        }
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("results", [])

    def _search_nominatim(self):
        """回退引擎：Nominatim (OpenStreetMap)，对非拉丁脚本支持更好"""
        mirrors = [
            "https://nominatim.openstreetmap.org/search",
            "https://nominatim.openstreetmap.fr/search",
        ]
        app_lang = QSettings("MyDesktopApp", "WeatherSettings").value("language", "en")
        headers = {
            "User-Agent": "DesktopWidget/1.0 (weather app)",
            "Accept-Language": app_lang
        }
        params = {
            "q": self.query,
            "format": "json",
            "limit": 10,
            "addressdetails": 1
        }
        last_error = None
        for mirror_url in mirrors:
            try:
                resp = requests.get(mirror_url, params=params, headers=headers, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        break
            except Exception as e:
                last_error = e
                continue
        else:
            return []
        results = []
        for item in data:
            addr = item.get("address", {})
            name = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or item.get("name", "")
            admin1 = addr.get("state") or addr.get("region") or addr.get("province") or ""
            country = addr.get("country", "")
            parts = [p for p in [name, admin1, country] if p]
            results.append({
                "display": ", ".join(parts),
                "name": name,
                "admin1": admin1,
                "country": country,
                "latitude": float(item.get("lat", 0)),
                "longitude": float(item.get("lon", 0)),
            })
        return results

    def _format_results(self, raw_items):
        """统一格式化搜索结果"""
        formatted = []
        for item in raw_items:
            name = item.get("name", "")
            admin1 = item.get("admin1", "")
            country = item.get("country", "")
            parts = [p for p in [name, admin1, country] if p]
            formatted.append({
                "display": ", ".join(parts),
                "name": name,
                "admin1": admin1,
                "country": country,
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
            })
        return formatted

    def run(self):
        if not self.query or len(self.query) < 2:
            self.search_failed.emit(QCoreApplication.translate("WeatherPage", "输入太短"))
            return

        # 每个搜索引擎独立 try，一个挂了不影响另一个
        om_results = None
        try:
            om_results = self._search_open_meteo()
        except Exception:
            pass

        if om_results:
            formatted = self._format_results(om_results)
            if formatted:
                self.result_ready.emit(formatted)
                return

        # Open-Meteo 无结果或异常 → Nominatim 回退
        nominatim_results = []
        try:
            nominatim_results = self._search_nominatim()
        except Exception:
            pass

        if nominatim_results:
            self.result_ready.emit(nominatim_results)
            return

        self.search_failed.emit(QCoreApplication.translate("WeatherPage", "未找到匹配地点"))


class WeatherPage(QWidget):
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
        self._block_search = False

        # 加载状态动画相关
        self._loading_dots = 0
        self._loading_timer = None
        self._last_weather_received = False
        self._timeout_timer = None  # 120秒超时定时器

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
        self._providers = [
            ("gaode",      QCoreApplication.translate("WeatherPage", "高德")),
            ("open_meteo", QCoreApplication.translate("WeatherPage", "Open-Meteo")),
            ("qweather",   QCoreApplication.translate("WeatherPage", "和风天气")),
            ("weatherapi", QCoreApplication.translate("WeatherPage", "WeatherAPI")),
            ("custom",     QCoreApplication.translate("WeatherPage", "自定义")),
        ]
        for key, label in self._providers:
            self.url_combo.addItem(label, key)
        self.url_combo.currentIndexChanged.connect(self._on_provider_index_changed)
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

        # 密钥显示/隐藏切换（小眼睛）
        self._key_visible = False
        self.eye_btn = QPushButton(self.tr("👁"))
        self.eye_btn.setFixedSize(24, 24)
        self.eye_btn.setStyleSheet("QPushButton { border: none; background: transparent; font-size: 14px; color: #888; } QPushButton:hover { color: #1677ff; }")
        self.eye_btn.setToolTip(self.tr("显示密钥"))
        self.eye_btn.clicked.connect(self._toggle_key_visibility)
        self.eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # 密钥输入框 + 眼睛按钮容器
        key_row = QHBoxLayout()
        key_row.addWidget(self.key_edit)
        key_row.addWidget(self.eye_btn)
        layout.addLayout(key_row)

        # ---------- 状态 + 刷新频率 ----------
        status_freq_layout = QHBoxLayout()
        self.status_label = QLabel(self.tr("状态：加载中..."))
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
        self.info_label = QLabel(self.tr("说明：请选择服务并填写对应信息"))
        self.info_label.setOpenExternalLinks(True)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #555; font-size: 12px; font-weight: normal;")
        layout.addWidget(self.info_label)

        # ---------- 天气显示地区 ----------
        region_label = QLabel(self.tr("天气显示地区"))
        region_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout.addWidget(region_label)

        # 搜索框布局（搜索框 + 状态标签）
        search_layout = QHBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("搜索城市名称"))
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
        """仅中文（排除日文假名/韩文谚文的 CJK 干扰）"""
        if re.search(r'[\u3040-\u30ff\uac00-\ud7af]', text):
            return False
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

        # 为本地搜索结果填充经纬度（用于 Open-Meteo 等需要坐标的服务）
        for r in unique_results[:10]:
            if r["latitude"] is not None and r["longitude"] is not None:
                continue
            name = r.get("name", "")
            if r["type"] == "county":
                coords = get_coords_by_name(name)
                if coords:
                    r["latitude"] = coords[0]
                    r["longitude"] = coords[1]
            elif r["type"] == "city":
                coords = get_coords_for_city(name)
                if coords:
                    r["latitude"] = coords[0]
                    r["longitude"] = coords[1]
            # province 类型暂不填充（范围太大，无意义）

        return unique_results[:10]

    # ---------- 搜索相关 ----------
    def _on_search_text_changed(self, text):
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

        # 标记用户已手动选择城市，后续启动不再调用 IP 定位
        settings.setValue("location_source", "user")
        settings.sync()

        self._block_search = True
        self.search_edit.setText(self._selected_display)
        self._block_search = False

        self.current_location_label.setText(f"{self.tr('当前地区')}：{self._selected_display}")

        self.search_status_label.setText("✅ " + self.tr("已选择"))
        self.result_list.hide()

        # 延迟发射信号，避免在信号处理中触发天气线程重启导致崩溃
        QTimer.singleShot(0, self._safe_region_changed)

    def _safe_region_changed(self):
        """安全地发射区域变更信号（延迟到下一事件循环）"""
        try:
            self.region_changed.emit()
            self._refresh_main_window_weather()
        except Exception:
            pass

    def _toggle_key_visibility(self):
        """切换 API Key 的显示/隐藏状态"""
        self._key_visible = not self._key_visible
        if self._key_visible:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.eye_btn.setText(self.tr("👁"))
            self.eye_btn.setStyleSheet("QPushButton { border: none; background: transparent; font-size: 14px; color: #1677ff; }")
            self.eye_btn.setToolTip(self.tr("隐藏密钥"))
        else:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.eye_btn.setText(self.tr("👁"))
            self.eye_btn.setStyleSheet("QPushButton { border: none; background: transparent; font-size: 14px; color: #888; } QPushButton:hover { color: #1677ff; }")
            self.eye_btn.setToolTip(self.tr("显示密钥"))

    def _update_info_label(self, service_key: str):
        """根据当前选中的服务动态更新说明文字"""
        if service_key == "gaode":
            self.info_label.setText(
                self.tr("说明：填入") +
                '<a href="https://lbs.amap.com/" style="color: #0366d6; text-decoration: none;">' +
                self.tr("高德API Key") +
                '</a>' +
                self.tr("，仅支持中国")
            )
        elif service_key == "open_meteo":
            self.info_label.setText(
                self.tr("说明：无需密钥，支持全球天气")
            )
        elif service_key == "qweather":
            self.info_label.setText(
                self.tr("说明：填入和风") +
                '<a href="https://www.qweather.com/" style="color: #0366d6; text-decoration: none;">' +
                self.tr("Host & API Key") +
                '</a>' +
                self.tr("，查看全球天气")
            )
        elif service_key == "weatherapi":
            self.info_label.setText(
                self.tr("说明：填入") +
                '<a href="https://www.weatherapi.com/" style="color: #0366d6; text-decoration: none;">' +
                self.tr("WeatherAPI Key") +
                '</a>' +
                self.tr("，查看全球天气")
            )
        elif service_key == "custom":
            self.info_label.setText(
                self.tr("说明：填入自定义API地址与Key")
            )
        else:
            self.info_label.setText(
                self.tr("说明：请选择服务并填写对应信息")
            )

    # ---------- API 相关 ----------

    def _start_loading_status(self):
        """启动加载状态动画（正在连接...）"""
        # 如果已经收到过天气，不启动加载动画
        if self._last_weather_received:
            return
        # 先彻底清理之前的定时器
        self._stop_loading_status()
        self._loading_dots = 0
        self._loading_timer = QTimer()
        self._loading_timer.timeout.connect(self._update_loading_status)
        self._loading_timer.start(500)
        self._update_loading_status()
        self._start_timeout_timer()

    def _stop_loading_status(self):
        """停止加载状态动画和超时定时器"""
        if self._loading_timer is not None:
            self._loading_timer.stop()
            self._loading_timer = None
        self._stop_timeout_timer()

    def _update_loading_status(self):
        """更新加载状态文字（三个点循环）"""
        # 如果已经收到过天气，停止更新
        if self._last_weather_received:
            self._stop_loading_status()
            return
        self._loading_dots = (self._loading_dots + 1) % 4
        dots = "." * self._loading_dots
        self.status_label.setText(self.tr("状态") + "：⏳ " + self.tr("正在连接") + dots)

    def _start_timeout_timer(self):
        """启动120秒超时定时器"""
        self._stop_timeout_timer()
        self._timeout_timer = QTimer()
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_connect_timeout)
        self._timeout_timer.start(120000)

    def _stop_timeout_timer(self):
        """停止超时定时器"""
        if self._timeout_timer is not None:
            self._timeout_timer.stop()
            self._timeout_timer = None
            self._timeout_timer = None  # 确保引用被清除

    def _on_connect_timeout(self):
        """120秒超时回调"""
        # 如果已经收到天气，不显示连接超时
        if self._last_weather_received:
            return
        self._stop_loading_status()
        self.status_label.setText(self.tr("状态") + "：❌ " + self.tr("连接超时"))

    def _on_provider_index_changed(self, index):
        if index < 0:
            return

        service_key = self.url_combo.currentData()
        if not service_key:
            return

        service_map = {
            "gaode":      ("https://restapi.amap.com",                        QCoreApplication.translate("WeatherPage", "请输入高德 API Key"),       True),
            "open_meteo": ("https://api.open-meteo.com/v1/forecast",          QCoreApplication.translate("WeatherPage", "无需 API Key（可留空）"),   True),
            "qweather":   ("https://devapi.qweather.com/v7/weather/now",      QCoreApplication.translate("WeatherPage", "请输入和风天气 API Key"),    False),
            "weatherapi": ("https://api.weatherapi.com/v1/current.json",      QCoreApplication.translate("WeatherPage", "请输入 WeatherAPI Key"),     True),
            "custom":     ("",                                                 QCoreApplication.translate("WeatherPage", "请输入 API Key"),            False),
        }

        if service_key in service_map:
            _, key_placeholder, readonly = service_map[service_key]
            self._updating = True
            settings = QSettings("MyDesktopApp", "WeatherSettings")

            # 按服务读取已保存的 URL
            saved_url = settings.value(f"api_url_{service_key}", "")
            if saved_url:
                self.url_edit.setText(saved_url)
            elif service_key == "gaode":
                self.url_edit.setText("https://restapi.amap.com")
            elif service_key == "open_meteo":
                self.url_edit.setText("https://api.open-meteo.com/v1/forecast")
            elif service_key == "weatherapi":
                self.url_edit.setText("https://api.weatherapi.com/v1/current.json")
            else:
                self.url_edit.setText("")

            # qweather: 特殊占位符，其他服务恢复默认
            if service_key == "qweather":
                self.url_edit.setPlaceholderText(
                    QCoreApplication.translate("WeatherPage", "输入你的个人和风Host")
                )
            else:
                self.url_edit.setPlaceholderText(self.tr("请输入 API 地址"))
            self.url_edit.setReadOnly(readonly)
            self.key_edit.setPlaceholderText(key_placeholder)
            # 重置密钥显示状态为隐藏（闭眼）
            self._key_visible = False
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            if hasattr(self, 'eye_btn'):
                self.eye_btn.setStyleSheet("QPushButton { border: none; background: transparent; font-size: 14px; color: #888; } QPushButton:hover { color: #1677ff; }")
                self.eye_btn.setToolTip(self.tr("显示密钥"))
            self._restore_key_for_service(service_key)
            self._updating = False

            # 更新说明文字
            self._update_info_label(service_key)
            # 切换服务时重置天气标志
            self._last_weather_received = False

        if not self._loading:
            self.save_api_settings()
            # ===== 修改点：切换 API 后刷新天气 =====
            self._refresh_main_window_weather()

    def on_url_changed(self, text):
        if not self._updating and not self._loading:
            self.save_api_settings()

    def on_key_changed(self, text):
        if not self._updating and not self._loading:
            self.save_api_settings()

    def on_freq_changed(self, value):
        if not self._updating and not self._loading:
            self.save_api_settings()

    def _restore_key_for_service(self, service_key):
        if not service_key or service_key == "open_meteo":
            self.key_edit.clear()
            return
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        saved_key = settings.value(f"api_key_{service_key}", "")
        self.key_edit.setText(saved_key)

    def save_api_settings(self):
        if self._loading:
            return
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        service_key = self.url_combo.currentData()
        if service_key:
            settings.setValue(f"api_url_{service_key}", self.url_edit.text().strip())
            settings.setValue("weather_service", service_key)
            if service_key != "open_meteo":
                settings.setValue(f"api_key_{service_key}", self.key_edit.text().strip())
        else:
            settings.setValue("api_url", self.url_edit.text().strip())
            settings.setValue("api_key", self.key_edit.text().strip())
            current_url = self.url_edit.text().strip()
            if current_url == "https://restapi.amap.com":
                settings.setValue("weather_service", "gaode")
            elif current_url == "https://api.open-meteo.com/v1/forecast":
                settings.setValue("weather_service", "open_meteo")
            elif "qweather" in current_url.lower() or "qweatherapi" in current_url.lower():
                settings.setValue("weather_service", "qweather")
            elif current_url.startswith("https://api.weatherapi.com"):
                settings.setValue("weather_service", "weatherapi")
            else:
                settings.setValue("weather_service", "custom")

        settings.setValue("refresh_minutes", self.freq_spin.value())
        self.check_status()

    def save_region_and_refresh(self):
        if self._loading:
            return
        if self._selected_display:
            self.region_changed.emit()
            self._refresh_main_window_weather()

    def _refresh_main_window_weather(self):
        """强制刷新主窗口天气线程"""
        if self._loading:
            return

        main_window = None

        # 方法1：通过 parent_dialog._main_window 属性（SettingsDialog 存储的引用）
        if self.parent_dialog and hasattr(self.parent_dialog, '_main_window'):
            main_window = self.parent_dialog._main_window

        # 方法2：通过 parent() 链向上查找
        if not main_window:
            obj = self.parent()
            while obj:
                if obj.__class__.__name__ == "MainWindow":
                    main_window = obj
                    break
                obj = obj.parent()

        # 方法3：通过 parent_dialog 链向上查找
        if not main_window and self.parent_dialog:
            obj = self.parent_dialog
            while obj:
                if obj.__class__.__name__ == "MainWindow":
                    main_window = obj
                    break
                obj = obj.parent()

        # 方法4：遍历顶层窗口（兜底）
        if not main_window:
            for widget in QApplication.topLevelWidgets():
                if widget.__class__.__name__ == "MainWindow":
                    main_window = widget
                    break

        if main_window and hasattr(main_window, 'start_weather_thread'):
            print("🔄 强制刷新天气线程")
            main_window.start_weather_thread(force_restart=True)
            # 重新连接设置页的天气信号（新线程需重新绑定）
            self._connect_weather_signal()
            if hasattr(main_window, 'update'):
                main_window.update()
        else:
            print("⚠️ 未找到主窗口，无法刷新天气")

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
            self.search_status_label.setText("✅ " + self.tr("已选择"))
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
                self.search_status_label.setText("✅ " + self.tr("已选择"))
            else:
                self.search_edit.clear()
                self.current_location_label.setText(self.tr("当前地区：未选择"))

    def _get_main_window(self):
        """???????????"""
        # ??1??? parent_dialog._main_window ??
        if self.parent_dialog and hasattr(self.parent_dialog, '_main_window'):
            return self.parent_dialog._main_window

        # ??2??? parent() ?????
        obj = self.parent()
        while obj:
            if obj.__class__.__name__ == "MainWindow":
                return obj
            obj = obj.parent()

        # ??3??? parent_dialog ?????
        if self.parent_dialog:
            obj = self.parent_dialog
            while obj:
                if obj.__class__.__name__ == "MainWindow":
                    return obj
                obj = obj.parent()

        # ??4???????????
        for widget in QApplication.topLevelWidgets():
            if widget.__class__.__name__ == "MainWindow":
                return widget

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
                try:
                    weather_thread.error_signal.disconnect(self._on_weather_error)
                except:
                    pass
                weather_thread.data_updated.connect(self._on_weather_updated)
                weather_thread.error_signal.connect(self._on_weather_error)
                self._signal_connected = True

                # 如果主窗口已有天气数据，设标志后由 check_status 判断（避免旧服务数据污染新服务）
                if hasattr(main_window, 'weather') and main_window.weather.get('city') != '--':
                    self._last_weather_received = True
                    self.check_status()

    def _on_weather_error(self, err_msg):
        """天气线程报错：标记配置无效，显示待配置"""
        if self._last_weather_received:
            return  # 之前成功过，保留"已连接"
        self._stop_loading_status()
        self.status_label.setText(self.tr("状态") + "：🛠️ " + self.tr("待配置"))

    def _on_weather_updated(self, data):
        # 过滤占位数据（线程失败时的兜底 ⚠️/?℃）
        if data.get("weather") == "⚠️" or data.get("temp") == "?":
            self._on_weather_error("")
            return

        # 强制停止所有定时器 - 直接操作，不依赖函数
        if self._loading_timer is not None:
            self._loading_timer.stop()
            self._loading_timer = None
        if self._timeout_timer is not None:
            self._timeout_timer.stop()
            self._timeout_timer = None
        # 标记已收到天气
        self._last_weather_received = True
        # 强制显示已连接
        self.status_label.setText(self.tr("状态") + "：✅ " + self.tr("已连接"))

    def load_settings(self):
        self._updating = True
        self._loading = True
        try:
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            freq = int(settings.value("refresh_minutes", 120))
            self.freq_spin.setValue(freq)

            weather_service = settings.value("weather_service", "")

            # ---- 首次安装：无记录时默认 Open-Meteo；后续启动记住用户选择 ----
            if not weather_service:
                weather_service = "open_meteo"
                settings.setValue("weather_service", "open_meteo")
                settings.setValue("api_url_open_meteo", "https://api.open-meteo.com/v1/forecast")
                settings.sync()

            idx = self.url_combo.findData(weather_service)
            if idx >= 0:
                self.url_combo.setCurrentIndex(idx)
            else:
                idx = self.url_combo.findData("open_meteo")
                if idx >= 0:
                    self.url_combo.setCurrentIndex(idx)

            self._on_provider_index_changed(self.url_combo.currentIndex())
            self.load_regions()

            # 重置标志并交由 check_status 统一判断状态
            self._last_weather_received = False
            self._connect_weather_signal()

        finally:
            self._loading = False
            self._updating = False

        # 必须在 finally 之后调用，否则 _loading=True 会导致 check_status 直接 return
        self.check_status()

    def check_status(self):
        if self._loading:
            return

        settings = QSettings("MyDesktopApp", "WeatherSettings")
        service_key = self.url_combo.currentData() or "custom"

        # 获取 URL 和 Key：优先从 QSettings 读取，fallback 到输入框
        url = settings.value(f"api_url_{service_key}", "")
        if not url:
            url = self.url_edit.text().strip()

        key = settings.value(f"api_key_{service_key}", "")
        if not key:
            key = self.key_edit.text().strip()

        # ---- 判断当前服务是否已配置完整 ----
        is_configured = False
        if service_key == "open_meteo":
            # Open-Meteo 不需要 Key，但必须有经纬度
            lat = settings.value("selected_latitude", "")
            lng = settings.value("selected_longitude", "")
            is_configured = bool(lat and lng)
        elif service_key == "gaode":
            is_configured = bool(key)  # 高德 URL 固定，只需要 Key
        else:
            is_configured = bool(url and key)

        # ---- 如果未配置：重置标志，显示待配置 ----
        if not is_configured:
            self._last_weather_received = False
            self._stop_loading_status()
            self.status_label.setText(self.tr("状态") + "：🛠️ " + self.tr("待配置"))
            return

        # ---- 已配置 + 已收到天气 → 已连接 ----
        if self._last_weather_received:
            self._stop_loading_status()
            self.status_label.setText(self.tr("状态") + "：✅ " + self.tr("已连接"))
            return

        # ---- 已配置但未收到天气 → 正在连接... ----
        self._start_loading_status()
