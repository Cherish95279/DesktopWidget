import sys
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPainter, QColor, QPixmap
from PyQt6.QtCore import QSize, QTimer, QSettings, Qt  # 添加 Qt 导入
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

        # 窗口模式相关
        self._window_mode = "float"  # bottom / float / top

        self.activated.connect(self.on_activated)

        self.menu = QMenu()
        self.setup_menu()
        self.setContextMenu(self.menu)

        # 注册公告回调
        self._register_notice_callbacks()

        # 恢复窗口模式状态
        self._load_window_mode()

    def _register_notice_callbacks(self):
        manager = NoticeManager.get_instance()
        manager.register_callback("on_new_notice", self._on_notice_received)
        manager.register_callback("on_no_notice", self._on_notice_cleared)
        print("📢 托盘回调注册成功")

    def _on_notice_received(self, notice):
        print("🔔 托盘：收到新公告，开始闪烁")
        self._has_notice = True
        self._notice_opened = False
        self._green_dot_visible = True
        self._update_tooltip()
        QTimer.singleShot(10, self._start_flash)

    def _on_notice_cleared(self):
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

    # ===== 窗口模式管理 =====
    def _load_window_mode(self):
        """从 QSettings 加载窗口模式"""
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        mode = settings.value("window_mode", "float")
        if mode not in ["bottom", "float", "top"]:
            mode = "float"
        self._window_mode = mode
        self._apply_window_mode(mode, save=False)

    def _save_window_mode(self, mode):
        """保存窗口模式到 QSettings"""
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("window_mode", mode)
        settings.sync()

    def _apply_window_mode(self, mode, save=True):
        """应用窗口模式到主窗口"""
        window = self.parent_window
        if not window:
            return

        # 获取当前窗口标志
        flags = window.windowFlags()

        # 清除所有置顶/置底标志
        flags = flags & ~Qt.WindowType.WindowStaysOnTopHint
        flags = flags & ~Qt.WindowType.WindowStaysOnBottomHint

        if mode == "bottom":
            flags = flags | Qt.WindowType.WindowStaysOnBottomHint
        elif mode == "top":
            flags = flags | Qt.WindowType.WindowStaysOnTopHint
        # "float" 模式不添加任何特殊标志

        window.setWindowFlags(flags)
        window.show()  # 重新显示使标志生效

        # 更新菜单项选中状态
        if hasattr(self, '_bottom_action'):
            self._bottom_action.setChecked(mode == "bottom")
        if hasattr(self, '_float_action'):
            self._float_action.setChecked(mode == "float")
        if hasattr(self, '_top_action'):
            self._top_action.setChecked(mode == "top")

        self._window_mode = mode

        if save:
            self._save_window_mode(mode)

        mode_names = {"bottom": "置底", "float": "悬浮模式", "top": "总是置顶"}
        print(f"📌 窗口模式: {mode_names.get(mode, mode)}")

    def _on_mode_triggered(self, mode):
        """窗口模式切换（由菜单触发）"""
        if mode == self._window_mode:
            return
        self._apply_window_mode(mode)

    # ===== 菜单 =====
    def setup_menu(self):
        self.menu.clear()

        # 显示主窗口
        show_action = QAction("🖥️ 显示主窗口", self)
        show_action.triggered.connect(self.show_window)
        self.menu.addAction(show_action)

        self.menu.addSeparator()

        # 窗口模式（三个互斥选项）
        self._bottom_action = QAction("⬇️ 置底", self)
        self._bottom_action.setCheckable(True)
        self._bottom_action.triggered.connect(lambda: self._on_mode_triggered("bottom"))

        self._float_action = QAction("↕️ 悬浮模式", self)
        self._float_action.setCheckable(True)
        self._float_action.setChecked(True)  # 默认选中
        self._float_action.triggered.connect(lambda: self._on_mode_triggered("float"))

        self._top_action = QAction("📌 总是置顶", self)
        self._top_action.setCheckable(True)
        self._top_action.triggered.connect(lambda: self._on_mode_triggered("top"))

        # 添加到菜单（顺序固定）
        self.menu.addAction(self._bottom_action)
        self.menu.addAction(self._float_action)
        self.menu.addAction(self._top_action)

        self.menu.addSeparator()

        # 设置、主题、检查更新
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