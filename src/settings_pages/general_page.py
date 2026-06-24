from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QFontDatabase, QColor
from PyQt6.QtWidgets import QColorDialog
from ..autostart import set_autostart, get_autostart_status
from ..region_data import REGIONS


class GeneralPage(QWidget):
    font_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_color = "#1c344d"
        self.autostart_checked = False
        self.parent_dialog = parent

        self.setup_ui()
        self.load_settings()
        self.load_regions_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(10)

        # ---------- 开机自启动 ----------
        self.autostart_widget = QWidget(self)
        autostart_layout = QHBoxLayout(self.autostart_widget)
        autostart_layout.setContentsMargins(0, 0, 0, 0)
        autostart_layout.setSpacing(6)

        self.autostart_icon = QLabel("✅", self)
        self.autostart_icon.setStyleSheet("font-size: 16px;")
        autostart_layout.addWidget(self.autostart_icon)

        self.autostart_label = QLabel("开机自启动", self)
        self.autostart_label.setStyleSheet("font-size: 12px; color: #333;")
        autostart_layout.addWidget(self.autostart_label)

        autostart_layout.addStretch()
        self.autostart_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        self.autostart_widget.mousePressEvent = self.on_autostart_widget_clicked

        layout.addWidget(self.autostart_widget)

        # ---------- 字体设置 ----------
        font_label = QLabel("字体设置")
        font_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(font_label)

        font_layout = QHBoxLayout()
        font_layout.setSpacing(10)

        self.font_combo = QComboBox()
        self.font_combo.setMinimumWidth(100)
        font_families = QFontDatabase.families()
        self.font_combo.addItems(font_families)
        font_layout.addWidget(self.font_combo)

        self.size_combo = QComboBox()
        self.size_combo.setMinimumWidth(50)
        for size in range(8, 16):
            self.size_combo.addItem(str(size))
        font_layout.addWidget(self.size_combo)

        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(30, 28)
        self.color_btn.setStyleSheet("border: 1px solid #999; border-radius: 4px;")
        self.color_btn.clicked.connect(self.choose_color)
        font_layout.addWidget(self.color_btn)
        font_layout.addStretch()

        layout.addLayout(font_layout)

        # ---------- 天气显示地区 ----------
        region_label = QLabel("天气显示地区")
        region_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
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

        # 信号连接（字体实时生效）
        self.font_combo.currentTextChanged.connect(self.apply_font_settings)
        self.size_combo.currentTextChanged.connect(self.apply_font_settings)

    # ---------- 开机自启动 ----------
    def update_autostart_display(self):
        if self.autostart_checked:
            self.autostart_icon.setText("✅")
        else:
            self.autostart_icon.setText("⬜")
        self.autostart_label.setStyleSheet("font-size: 12px; color: #333;")

    def on_autostart_widget_clicked(self, event):
        self.autostart_checked = not self.autostart_checked
        self.update_autostart_display()
        if self.autostart_checked:
            if not set_autostart(True):
                QMessageBox.warning(self, "提示", "设置开机自启动失败，请检查权限")
                self.autostart_checked = False
                self.update_autostart_display()
        else:
            set_autostart(False)

    # ---------- 字体设置 ----------
    def load_font_settings(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        font_family = settings.value("font_family", "Microsoft YaHei")
        font_size = int(settings.value("font_size", 10))
        font_color = settings.value("font_color", "#1c344d")

        idx = self.font_combo.findText(font_family)
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)

        idx = self.size_combo.findText(str(font_size))
        if idx >= 0:
            self.size_combo.setCurrentIndex(idx)

        self._current_color = font_color
        self.update_color_button()

    def update_color_button(self):
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._current_color};
                border: 1px solid #999;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #666;
            }}
        """)

    def choose_color(self):
        try:
            dialog = QColorDialog(self)
            dialog.setCurrentColor(QColor(self._current_color))
            dialog.setWindowTitle("选择文字颜色")
            if dialog.exec() == QDialog.DialogCode.Accepted:
                color = dialog.selectedColor()
                if color.isValid():
                    self._current_color = color.name()
                    self.update_color_button()
                    self.apply_font_settings()
        except Exception as e:
            print(f"颜色选择异常: {e}")

    def apply_font_settings(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("font_family", self.font_combo.currentText())
        settings.setValue("font_size", int(self.size_combo.currentText()))
        settings.setValue("font_color", self._current_color)
        self.font_changed.emit()

    # ---------- 地区数据 ----------
    def load_regions_data(self):
        provinces = list(REGIONS.keys())
        self.province_combo.clear()
        self.province_combo.addItem("请选择省份")
        self.province_combo.addItems(provinces)
        self.province_combo.currentTextChanged.connect(self.on_province_changed)
        self.city_combo.currentTextChanged.connect(self.on_city_changed)

    def on_province_changed(self, province):
        self.city_combo.clear()
        self.city_combo.addItem("请选择城市")
        if province and province in REGIONS:
            cities = list(REGIONS[province].get("cities", {}).keys())
            self.city_combo.addItems(cities)
        self.county_combo.clear()
        self.county_combo.addItem("请选择区县")

    def on_city_changed(self, city):
        self.county_combo.clear()
        self.county_combo.addItem("请选择区县")
        province = self.province_combo.currentText()
        if province and city and province in REGIONS:
            counties = REGIONS[province].get("cities", {}).get(city, {}).get("counties", [])
            self.county_combo.addItems(counties)

    # ---------- 加载/保存 ----------
    def load_settings(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")

        self.autostart_checked = get_autostart_status()
        self.update_autostart_display()

        self.load_font_settings()

        province = settings.value("selected_province", "")
        city = settings.value("selected_city", "")
        county = settings.value("selected_county", "")
        if province:
            idx = self.province_combo.findText(province)
            if idx >= 0:
                self.province_combo.setCurrentIndex(idx)
        if city:
            idx_city = self.city_combo.findText(city)
            if idx_city >= 0:
                self.city_combo.setCurrentIndex(idx_city)
        if county:
            idx_county = self.county_combo.findText(county)
            if idx_county >= 0:
                self.county_combo.setCurrentIndex(idx_county)

    def save_settings(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")

        province = self.province_combo.currentText()
        city = self.city_combo.currentText()
        county = self.county_combo.currentText()
        if province != "请选择省份" and city != "请选择城市":
            settings.setValue("selected_province", province)
            settings.setValue("selected_city", city)
            if county != "请选择区县":
                settings.setValue("selected_county", county)
            else:
                settings.remove("selected_county")
        else:
            settings.remove("selected_province")
            settings.remove("selected_city")
            settings.remove("selected_county")