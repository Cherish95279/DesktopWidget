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
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowSystemMenuHint)
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
        self.pages = []

        # 创建页面
        self.general_page = GeneralPage(self)
        self.display_page = DisplayPage(self)
        self.weather_page = WeatherPage(self)
        self.theme_page = ThemePage(self)
        self.update_page = UpdatePage(self)
        self.donation_page = DonationPage(self)
        self.about_page = AboutPage(self)
        self.pages = [self.general_page, self.display_page, self.weather_page, self.theme_page, self.update_page, self.donation_page, self.about_page]

        # 连接常规页面的字体变化信号
        self.general_page.font_changed.connect(self.on_font_changed)

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

        # ---------- 右侧内容 ----------
        self.stacked = QStackedWidget()
        self.stacked.setStyleSheet("background-color: rgba(245, 245, 245, 0.9);")
        for page in self.pages:
            self.stacked.addWidget(page)

        main_layout.addWidget(self.stacked)

        # 切换到初始页面
        page_index = {"general": 0, "display": 1, "weather": 2, "theme": 3, "update": 4, "donation": 5, "about": 6}.get(initial_page, 0)
        self.switch_page(page_index)

    def switch_page(self, index):
        self.stacked.setCurrentIndex(index)
        for i, btn in enumerate(self.cat_buttons):
            btn.setChecked(i == index)

    def on_font_changed(self):
        parent = self.parent()
        if parent and hasattr(parent, 'update'):
            parent.update()

    def save_settings(self):
        """保存所有设置（由各页面自行保存，此方法仅作为兼容保留）"""
        pass

    def closeEvent(self, event):
        self._exiting = True
        event.accept()