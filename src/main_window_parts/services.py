# -*- coding: utf-8 -*-
"""
服务层：公告通知、设置对话框、更新检查。

作为 MainWindow 的 mixin。
"""

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer, QSettings

from ..settings_dialog import SettingsDialog
from ..updater import UpdateChecker


class ServicesMixin:
    """公呃通知、设置与更新检查逻辑。"""

    def _on_bubble_clicked(self):
        self._acknowledge_notice()

    def _acknowledge_notice(self):
        """统一处理公呃确认：停止所有闪烁，打开公呃窗口"""
        # 停止气泡闪烁
        if hasattr(self, 'notice_bubble') and self.notice_bubble:
            self.notice_bubble.hide_bubble()
        # 停止托盘闪烁
        if hasattr(self, 'tray') and self.tray:
            self.tray._stop_flash()
            self.tray._green_dot_visible = False
            self.tray._notice_opened = True
            QTimer.singleShot(10, lambda: self.tray.setIcon(self.tray._default_icon))
            self.tray._update_tooltip()
        # 打开公呃窗口
        self._open_notice_window()

    def _open_notice_window(self):
        from ..notice import NoticeWindow, NoticeManager
        if self._notice_window is not None and self._notice_window.isVisible():
            self._notice_window.raise_()
            self._notice_window.activateWindow()
            return
        QTimer.singleShot(200, self._create_notice_window)

    def _create_notice_window(self):
        from ..notice import NoticeWindow, NoticeManager
        self._notice_window = NoticeWindow(self)
        self._notice_window.destroyed.connect(self._on_notice_window_destroyed)
        manager = NoticeManager.get_instance()
        current_notice = manager.get_current_notice()
        if current_notice:
            notice_id = current_notice.get("id")
            if notice_id:
                QTimer.singleShot(300, lambda: self._notice_window.select_notice_by_id(
                    notice_id) if self._notice_window else None)
        self._notice_window.show()

    def _on_notice_window_destroyed(self):
        self._notice_window = None

    def open_settings(self, initial_page="general"):
        if self.settings_dialog is not None and self.settings_dialog.isVisible():
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            if hasattr(self.settings_dialog, 'switch_page'):
                page_index = {"general": 0, "display": 1, "weather": 2, "theme": 3, "update": 4, "donation": 5,
                              "about": 6}.get(initial_page, 0)
                self.settings_dialog.switch_page(page_index)
            return
        try:
            dialog = SettingsDialog(self, initial_page=initial_page)
            screen = QApplication.primaryScreen()
            if screen:
                geometry = screen.availableGeometry()
                x = geometry.right() - dialog.width() - 100
                y = geometry.bottom() - dialog.height() - 200
                if y < 0:
                    y = 0
                dialog.move(x, y)
            self.settings_dialog = dialog
            dialog.destroyed.connect(self._on_settings_closed)
            dialog.show()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开设置失败：{str(e)}")

    def _on_settings_closed(self):
        self.settings_dialog = None

    def check_for_updates_auto(self):
        if self.update_checker is not None and self.update_checker.isRunning():
            return

        settings = QSettings("MyDesktopApp", "WeatherSettings")
        channel = settings.value("update_channel", "gitee")
        if channel == "gitee":
            url = "https://gitee.com/api/v5/repos/Cherish95279/DesktopWidget/releases/latest"
            self.update_checker = UpdateChecker(url, use_token=False)
        else:
            self.update_checker = UpdateChecker()
        self.update_check_status = "checking"
        self.update_checker.check_finished.connect(self.on_update_check_finished)
        self.update_checker.start()

    def on_update_check_finished(self, result):
        if "error" in result:
            self.update_check_status = "failed"
            self.has_update = False
            self._push_update_result(result)
            return
        if result.get("has_update", False):
            self.has_update = True
            self.latest_version_info = result
            self.update_check_status = "success"
            # 通知托盘图标闪烁
            if hasattr(self, 'tray') and self.tray:
                self.tray.start_update_flash()
        else:
            self.has_update = False
            self.update_check_status = "no_update"
        self._push_update_result(result)

    def _push_update_result(self, result):
        """将更新检查结果推送给已打开的更新页（避免重复请求）。"""
        if (hasattr(self, 'settings_dialog') and self.settings_dialog
                and getattr(self.settings_dialog, 'update_page', None) is not None):
            try:
                self.settings_dialog.update_page.apply_result(result)
            except Exception:
                pass

    def get_latest_version_info(self):
        return self.latest_version_info if self.has_update else None

