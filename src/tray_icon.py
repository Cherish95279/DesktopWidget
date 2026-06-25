import sys
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPainter, QColor, QPixmap
from PyQt6.QtCore import QSize, QTimer, Qt  # ← 添加 Qt
from .utils import resource_path
from .notice import NoticeManager, NoticeWindow


class TrayIcon(QSystemTrayIcon):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window

        # 加载托盘图标
        self._default_icon = QIcon()
        self._default_icon.addFile(resource_path("icons/tray_24.png"), QSize(24, 24))
        self._default_icon.addFile(resource_path("icons/tray_16.png"), QSize(16, 16))
        self.setIcon(self._default_icon)
        self.setToolTip("珍爱桌面小工具")

        # 公告相关状态
        self._flash_timer = None
        self._flash_count = 0
        self._has_notice = False
        self._green_dot_visible = False
        self._notice_opened = False

        self.activated.connect(self.on_activated)

        self.menu = QMenu()
        self.setup_menu()
        self.setContextMenu(self.menu)

        # 注册公告回调
        self._register_notice_callbacks()

    def _register_notice_callbacks(self):
        manager = NoticeManager.get_instance()
        manager.register_callback("on_new_notice", self._on_notice_received)
        manager.register_callback("on_no_notice", self._on_notice_cleared)
        print("📢 托盘回调注册成功")

    def _on_notice_received(self, notice):
        """有新公告"""
        print("🔔 托盘：收到新公告，开始闪烁")
        self._has_notice = True
        self._notice_opened = False
        self._green_dot_visible = True
        self._update_tooltip()
        # 延迟启动闪烁
        QTimer.singleShot(10, self._start_flash)

    def _on_notice_cleared(self):
        """无公告或已读"""
        print("🔕 托盘：公告已读或清除")
        self._has_notice = False
        self._notice_opened = True
        self._green_dot_visible = False
        self._stop_flash()
        QTimer.singleShot(10, lambda: self.setIcon(self._default_icon))
        self._update_tooltip()

    def _start_flash(self):
        if self._flash_timer is not None:
            return

        print("🔔 托盘图标开始闪烁")
        self._flash_count = 0
        self._flash_timer = QTimer()
        self._flash_timer.timeout.connect(self._flash_icon)
        self._flash_timer.start(500)

    def _flash_icon(self):
        self._flash_count += 1

        if self._flash_count % 2 == 1:
            self.setIcon(QIcon())
        else:
            self.setIcon(self._default_icon)
            if self._green_dot_visible and self._flash_count >= 20:
                self._draw_green_dot()

        if self._flash_count >= 20:
            self._stop_flash()
            QTimer.singleShot(50, lambda: self._draw_green_dot() if self._green_dot_visible else self.setIcon(self._default_icon))

    def _stop_flash(self):
        if self._flash_timer is not None:
            self._flash_timer.stop()
            self._flash_timer = None
            print("🔕 托盘图标停止闪烁")

    def _draw_green_dot(self):
        """绘制绿色小点（安全版本）"""
        try:
            pixmap = self._default_icon.pixmap(QSize(24, 24))
            if pixmap.isNull():
                pixmap = QPixmap(24, 24)
                pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            dot_size = 6
            dot_x = 24 - dot_size - 2
            dot_y = 24 - dot_size - 2
            painter.setBrush(QColor(0, 200, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)

            painter.end()
            self.setIcon(QIcon(pixmap))
            print("✅ 绿色小点已绘制")
        except Exception as e:
            print(f"⚠️ 绘制绿点失败: {e}")

    def _update_tooltip(self):
        if self._has_notice:
            self.setToolTip("珍爱桌面小工具\n🔔 有新的公告")
        else:
            self.setToolTip("珍爱桌面小工具")

    def setup_menu(self):
        self.menu.clear()

        show_action = QAction("🖥️ 显示主窗口", self)
        show_action.triggered.connect(self.show_window)
        self.menu.addAction(show_action)

        self.menu.addSeparator()

        settings_action = QAction("⚙️ 设置", self)
        settings_action.triggered.connect(self.parent_window.open_settings)
        self.menu.addAction(settings_action)

        theme_action = QAction("🎨 主题", self)
        theme_action.triggered.connect(lambda: self.parent_window.open_settings(initial_page="theme"))
        self.menu.addAction(theme_action)

        update_action = QAction("🔄 检查更新", self)
        update_action.triggered.connect(lambda: self.parent_window.open_settings(initial_page="update"))
        self.menu.addAction(update_action)

        self.menu.addSeparator()

        exit_action = QAction("❌ 退出", self)
        exit_action.triggered.connect(self.quit_app)
        self.menu.addAction(exit_action)

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self._has_notice and not self._notice_opened:
                print("🖱️ 左键单击托盘图标 → 打开公告")
                self._open_notice_window()
            else:
                self.toggle_window()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window()

    def _open_notice_window(self):
        manager = NoticeManager.get_instance()
        notice = manager.get_current_notice()
        if notice is None:
            return

        self._notice_opened = True
        self._green_dot_visible = False
        self.setIcon(self._default_icon)
        self._update_tooltip()

        if hasattr(self.parent_window, '_notice_window') and self.parent_window._notice_window is not None:
            window = self.parent_window._notice_window
            window.show()
            window.raise_()
            window.activateWindow()
        else:
            window = NoticeWindow(self.parent_window)
            window.show()
            self.parent_window._notice_window = window

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
        self.parent_window._exiting = True
        QApplication.quit()