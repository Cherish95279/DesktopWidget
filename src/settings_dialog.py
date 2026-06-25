from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QIcon
from .utils import resource_path
from .settings_pages import GeneralPage, DisplayPage, WeatherPage, ThemePage, UpdatePage, DonationPage, AboutPage


class SettingsDialog(QDialog):
    def __init__(self, parent=None, initial_page="general"):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setFixedSize(500, 380)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowSystemMenuHint
        )
        self.setWindowIcon(QIcon(resource_path("icons/app.ico")))

        self._exiting = False

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

        self.cat_labels = ["常规设置", "显示项目", "天气设置", "主题", "检查更新", "捐赠", "关于"]
        self.cat_buttons = []

        # ---------- 右侧内容 ----------
        self.stacked = QStackedWidget()
        self.stacked.setStyleSheet("background-color: rgba(245, 245, 245, 0.9);")

        # ---------- 页面引用（懒加载） ----------
        self.general_page = None
        self.display_page = None
        self.weather_page = None
        self.theme_page = None
        self.update_page = None
        self.donation_page = None
        self.about_page = None

        self.page_creators = {
            0: self._create_general_page,
            1: self._create_display_page,
            2: self._create_weather_page,
            3: self._create_theme_page,
            4: self._create_update_page,
            5: self._create_donation_page,
            6: self._create_about_page,
        }

        # 创建左侧导航按钮
        for i, label in enumerate(self.cat_labels):
            btn = QPushButton(label)
            btn.setFixedHeight(40)
            btn.setFlat(True)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
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
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, idx=i: self.switch_page(idx))
            left_layout.addWidget(btn)
            self.cat_buttons.append(btn)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # ---------- 默认加载第一个页面 ----------
        self.switch_page(0)

        main_layout.addWidget(self.stacked)

        page_index = {"general": 0, "display": 1, "weather": 2, "theme": 3, "update": 4, "donation": 5, "about": 6}.get(initial_page, 0)
        self.switch_page(page_index)

    def _create_general_page(self):
        if self.general_page is None:
            self.general_page = GeneralPage(self)
            self.general_page.font_changed.connect(self.on_font_changed)
            self.stacked.addWidget(self.general_page)
        return self.general_page

    def _create_display_page(self):
        if self.display_page is None:
            self.display_page = DisplayPage(self)
            self.stacked.addWidget(self.display_page)
        return self.display_page

    def _create_weather_page(self):
        if self.weather_page is None:
            self.weather_page = WeatherPage(self)
            self.stacked.addWidget(self.weather_page)
        return self.weather_page

    def _create_theme_page(self):
        if self.theme_page is None:
            self.theme_page = ThemePage(self)
            self.stacked.addWidget(self.theme_page)
        return self.theme_page

    def _create_update_page(self):
        if self.update_page is None:
            self.update_page = UpdatePage(self)
            self.stacked.addWidget(self.update_page)
        return self.update_page

    def _create_donation_page(self):
        if self.donation_page is None:
            self.donation_page = DonationPage(self)
            self.stacked.addWidget(self.donation_page)
        return self.donation_page

    def _create_about_page(self):
        if self.about_page is None:
            self.about_page = AboutPage(self)
            self.stacked.addWidget(self.about_page)
        return self.about_page

    def switch_page(self, index):
        page = self.page_creators[index]()
        self.stacked.setCurrentWidget(page)
        for i, btn in enumerate(self.cat_buttons):
            btn.setChecked(i == index)

    def on_font_changed(self):
        parent = self.parent()
        if parent and hasattr(parent, 'update'):
            parent.update()

    def save_settings(self):
        pass

    def closeEvent(self, event):
        self._exiting = True
        event.accept()