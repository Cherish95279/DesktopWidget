import sys
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QSize
from .utils import resource_path

class TrayIcon(QSystemTrayIcon):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window

        # 加载托盘图标
        icon = QIcon()
        icon.addFile(resource_path("icons/tray_24.png"), QSize(24, 24))
        icon.addFile(resource_path("icons/tray_16.png"), QSize(16, 16))
        self.setIcon(icon)
        self.setToolTip("珍爱桌面小工具")

        self.activated.connect(self.on_activated)

        self.menu = QMenu()
        self.setup_menu()
        self.setContextMenu(self.menu)

    def setup_menu(self):
        self.menu.clear()

        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show_window)
        self.menu.addAction(show_action)

        self.menu.addSeparator()

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.parent_window.open_settings)
        self.menu.addAction(settings_action)

        theme_action = QAction("主题", self)
        theme_action.triggered.connect(lambda: self.parent_window.show_message("提示", "主题功能开发中..."))
        self.menu.addAction(theme_action)

        update_action = QAction("检查更新", self)
        update_action.triggered.connect(lambda: self.parent_window.show_message("提示", "检查更新功能开发中..."))
        self.menu.addAction(update_action)

        self.menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.quit_app)
        self.menu.addAction(exit_action)

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_window()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def toggle_window(self):
        if self.parent_window.isVisible():
            self.parent_window.hide()
        else:
            self.parent_window.show()
            self.parent_window.raise_()
            self.parent_window.activateWindow()

    def show_window(self):
        if not self.parent_window.isVisible():
            self.parent_window.show()
            self.parent_window.raise_()
            self.parent_window.activateWindow()

    def quit_app(self):
        QApplication.quit()