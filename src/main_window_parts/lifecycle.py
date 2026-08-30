# -*- coding: utf-8 -*-
"""
窗口行为层：拖拽、悬停、关闭、置位、任务栏切换、悬停弹窗。

作为 MainWindow 的 mixin。
"""

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtCore import Qt, QSettings, QRect

from ..constants import DEFAULT_LAYOUT


class LifecycleMixin:
    """窗口行为与交互逻辑。"""

    def move_to_top_right(self):
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.right() - self.width() - 100
            y = geometry.top() + 150
            self.move(x, y)

    def toggle_taskbar_window(self, visible: bool):
        """托盘右键菜单切换任务栏窗口显隐"""
        if hasattr(self, 'taskbar_widget') and self.taskbar_widget:
            if visible:
                self.taskbar_widget.show_in_taskbar()
            else:
                self.taskbar_widget.hide_from_taskbar()

    # ---------- hover detail popup ----------
    def _init_detail_popup(self):
        from ..widgets.detail_popup import DetailPopup
        self._detail_popup = DetailPopup(self)
        self.setMouseTracking(True)
        self._last_hover_slot = None
        # 启动时按当前窗口模式同步弹窗层级
        if hasattr(self, 'tray') and self.tray and hasattr(self.tray, '_window_mode'):
            self._detail_popup.apply_window_mode(self.tray._window_mode)
        if hasattr(self, 'notice_bubble') and self.notice_bubble:
            self.notice_bubble.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if hasattr(self, '_detail_popup'):
            self._last_hover_slot = None
            self._detail_popup.start_fade_out(200)

    def _get_hover_slot(self, pos):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        slot_position_map = {
            "slot_1": (20, 30, 105, 43),
            "slot_2": (20, 86, 85, 43),
            "slot_3": (20, 166, 70, 50),
            "slot_4": (20, 235, 88, 50),
            "slot_5": (280, 30, 94, 43),
            "slot_6": (314, 86, 71, 43),
            "slot_7": (324, 166, 60, 50),
            "slot_8": (273, 245, 97, 52),
        }
        for slot_key in ["slot_1", "slot_2", "slot_3", "slot_4", "slot_5", "slot_6", "slot_7", "slot_8"]:
            if slot_key not in slot_position_map:
                continue
            x, y, w, h = slot_position_map[slot_key]
            rect = QRect(x, y, w, h)
            if rect.contains(pos):
                content_key = settings.value(slot_key, DEFAULT_LAYOUT.get(slot_key, "empty"))
                return (slot_key, content_key, rect)
        return None

    def show_and_activate(self):
        """显示并激活主窗口（用于单实例唤起）。"""
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self._exiting:
            event.accept()
            return
        if self.tray.isVisible():
            self.hide()
            self.tray.showMessage(
                "珍爱桌面小工具",
                "程序已最小化到系统托盘，双击托盘图标可恢复窗口。",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
            event.ignore()
        else:
            self.shutdown()
            event.accept()

    def shutdown(self):
        """停止后台任务，避免 QApplication 退出时销毁仍在运行的 QThread。"""
        if getattr(self, "_shutdown_complete", False):
            return
        self._shutdown_complete = True

        if self._loading_timer is not None:
            self._loading_timer.stop()
        for timer_name in (
                "clock_timer",
                "perf_timer",
                "_initial_ping_timer",
                "_ping_timer",
        ):
            timer = getattr(self, timer_name, None)
            if timer is not None:
                timer.stop()

        for thread_name in ("weather_thread", "net_thread", "scanner"):
            thread = getattr(self, thread_name, None)
            if thread is not None:
                thread.stop()

        from ..notice import NoticeManager
        NoticeManager.get_instance().stop()

        # 退出前脱离任务栏，避免销毁仍挂在 explorer 的子窗口
        if hasattr(self, "taskbar_widget") and self.taskbar_widget:
            self.taskbar_widget.hide_from_taskbar()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = event.globalPosition().toPoint()
        if hasattr(self, '_detail_popup'):
            hover_enabled = QSettings("MyDesktopApp", "WeatherSettings").value("hover_enabled", True, type=bool)
            if hover_enabled:
                pos = event.position().toPoint()
                slot_info = self._get_hover_slot(pos)
                if slot_info:
                    slot_key, content_key, rect = slot_info
                    if self._last_hover_slot != (slot_key, content_key):
                        self._last_hover_slot = (slot_key, content_key)
                        self._detail_popup.stop_fade_out()
                        self._detail_popup.show_for_slot(slot_key, content_key, rect)
                else:
                    if self._last_hover_slot is not None:
                        self._last_hover_slot = None
                        self._detail_popup.start_fade_out(200)
            else:
                if self._last_hover_slot is not None:
                    self._last_hover_slot = None
                    self._detail_popup.hide()

    def mouseReleaseEvent(self, e):
        self.drag_pos = None

