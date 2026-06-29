from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox
from ..settings_dialog import SettingsDialog


class DialogMixin:
    """对话框管理混入：设置、公告窗口"""

    def _on_bubble_clicked(self):
        """点击聊天气泡 → 打开公告窗口"""
        self._open_notice_window()

    def _open_notice_window(self):
        """打开公告窗口（延迟创建，避免与闪烁冲突）"""
        from ..notice import NoticeWindow, NoticeManager

        if self._notice_window is not None and self._notice_window.isVisible():
            self._notice_window.raise_()
            self._notice_window.activateWindow()
            return

        QTimer.singleShot(200, self._create_notice_window)

    def _create_notice_window(self):
        """实际创建公告窗口"""
        from ..notice import NoticeWindow, NoticeManager

        self._notice_window = NoticeWindow(self)
        self._notice_window.destroyed.connect(self._on_notice_window_destroyed)

        manager = NoticeManager.get_instance()
        current_notice = manager.get_current_notice()
        if current_notice:
            notice_id = current_notice.get("id")
            if notice_id:
                QTimer.singleShot(300, lambda: self._notice_window.select_notice_by_id(notice_id) if self._notice_window else None)

        self._notice_window.show()

    def _on_notice_window_destroyed(self):
        """公告窗口销毁时清理引用"""
        self._notice_window = None

    def open_settings(self, initial_page="general"):
        if self.settings_dialog is not None and self.settings_dialog.isVisible():
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            if hasattr(self.settings_dialog, 'switch_page'):
                page_index = {"general": 0, "display": 1, "weather": 2, "theme": 3, "update": 4, "donation": 5, "about": 6}.get(initial_page, 0)
                self.settings_dialog.switch_page(page_index)
            return

        try:
            dialog = SettingsDialog(self, initial_page=initial_page)
            dialog.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)

            screen = QApplication.primaryScreen()
            if screen:
                geometry = screen.availableGeometry()
                x = geometry.right() - dialog.width() - 100
                y = geometry.bottom() - dialog.height() - 200
                if y < 0:
                    y = 0
                dialog.move(x, y)

            self.settings_dialog = dialog
            dialog.finished.connect(self._on_settings_closed)
            dialog.show()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开设置失败：{str(e)}")

    def _on_settings_closed(self):
        self.settings_dialog = None