import sys
import ctypes
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QIcon, QAction
from .utils import resource_path
from .settings_pages import GeneralPage, DisplayPage, WeatherPage, ThemePage, UpdatePage, DonationPage, AboutPage


class SettingsDialog(QWidget):
    def __init__(self, parent=None, initial_page="general"):
        super().__init__(None)
        self._main_window = parent
        self.setWindowTitle(self.tr("设置"))
        self.setFixedSize(500, 380)

        # ----- 系统标题栏（保留最小化和关闭按钮） -----
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )

        # 图标
        icon_path = resource_path("icons/app.ico")
        self.icon = QIcon(icon_path)
        self.setWindowIcon(self.icon)
        QApplication.setWindowIcon(self.icon)

        try:
            myappid = 'DesktopWidget.SettingsDialog.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        self._exiting = False
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)

        # ---------- 主布局（直接使用水平布局，无自定义标题栏） ----------
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航（浅灰色）
        left_panel = QWidget()
        left_panel.setFixedWidth(100)
        left_panel.setStyleSheet("background-color: #f5f6fa;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 20, 0, 20)
        left_layout.setSpacing(0)

        self.cat_labels = [self.tr("常规设置"), self.tr("显示项目"), self.tr("天气设置"), self.tr("主题"), self.tr("检查更新"), self.tr("捐赠"), self.tr("关于")]
        self.cat_buttons = []

        # 右侧堆叠
        self.stacked = QStackedWidget()
        self.stacked.setStyleSheet("background-color: white;")

        # 页面引用
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
                    border-radius: 0px;
                }
                QPushButton:hover {
                    background: #e8edf3;
                }
                QPushButton:checked {
                    background: #d0e4ff;
                    color: #1677ff;
                    font-weight: bold;
                }
            """)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, idx=i: self.switch_page(idx))
            left_layout.addWidget(btn)
            self.cat_buttons.append(btn)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        self.switch_page(0)
        main_layout.addWidget(self.stacked)

        page_index = {"general": 0, "display": 1, "weather": 2, "theme": 3, "update": 4, "donation": 5, "about": 6}.get(initial_page, 0)
        self.switch_page(page_index)

    # ---------- 以下方法保持不变 ----------
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
            self.theme_page.theme_changed.connect(self.on_theme_changed)
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

    def rebuild_all_pages(self):
        """重建所有设置页面（语言切换时调用）"""
        # 重新设置导航按钮文本
        self.setWindowTitle(self.tr("设置"))
        self.cat_labels = [self.tr("常规设置"), self.tr("显示项目"), self.tr("天气设置"),
                          self.tr("主题"), self.tr("检查更新"), self.tr("捐赠"), self.tr("关于")]
        for i, label in enumerate(self.cat_labels):
            if i < len(self.cat_buttons):
                self.cat_buttons[i].setText(label)
        # 销毁并重建所有页面
        for attr in ["general_page", "display_page", "weather_page",
                     "theme_page", "update_page", "donation_page", "about_page"]:
            page = getattr(self, attr, None)
            if page is not None:
                self.stacked.removeWidget(page)
                page.deleteLater()
                setattr(self, attr, None)
        # 切换到当前页面（触发重新创建）
        current_idx = 0
        for i, btn in enumerate(self.cat_buttons):
            if btn.isChecked():
                current_idx = i
                break
        self.switch_page(current_idx)

    def on_font_changed(self):
        if self._main_window and hasattr(self._main_window, '_refresh_font_cache'):
            self._main_window._refresh_font_cache()
            self._main_window.update()
        elif self._main_window and hasattr(self._main_window, 'update'):
            self._main_window.update()

    def on_theme_changed(self):
        if self._main_window and hasattr(self._main_window, 'reload_images'):
            self._main_window.reload_images()
        elif self._main_window and hasattr(self._main_window, 'update_theme_cache'):
            self._main_window.update_theme_cache(force=True)
        elif self._main_window and hasattr(self._main_window, 'update'):
            self._main_window.update()

    def save_settings(self):
        pass

    def closeEvent(self, event):
        self._exiting = True
        event.accept()
        if self._main_window and hasattr(self._main_window, '_refresh_draw_cache'):
            self._main_window._refresh_draw_cache()
            self._main_window._refresh_font_cache()
            self._main_window.update()