from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPainter, QColor, QPixmap
from PyQt6.QtCore import QSize, QTimer, QSettings, Qt
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

        self.setToolTip(self.tr("珍爱桌面小工具"))

        # 公告相关状态
        self._flash_timer = None
        self._flash_count = 0
        self._has_notice = False
        self._green_dot_visible = False
        self._notice_opened = False

        # 更新通知状态
        self._has_update = False
        self._update_flash_timer = None
        self._update_flash_count = 0

        # 窗口模式相关
        self._window_mode = "float"  # bottom / float / top

        # 任务栏窗口相关
        self._taskbar_visible = True
        self._taskbar_action = None

        self.activated.connect(self.on_activated)

        self.menu = QMenu()
        self.setup_menu()
        # 菜单弹出时暂停嵌入器定时器，避免 bring_to_top 搅动 z-order 导致菜单被任务栏压住
        self.menu.aboutToShow.connect(self._on_menu_about_to_show)
        self.menu.aboutToHide.connect(self._on_menu_about_to_hide)

        # 注册公告回调
        self._register_notice_callbacks()

        # 恢复窗口模式状态
        self._load_window_mode()


    def _register_notice_callbacks(self):
        manager = NoticeManager.get_instance()
        manager.register_callback("on_new_notice", self._on_notice_received)
        manager.register_callback("on_no_notice", self._on_notice_cleared)
        print("[Tray] 托盘回调注册成功")

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

            dot_size = 10
            dot_x = 18 - dot_size // 2
            dot_y = 19 - dot_size // 2
            painter.setBrush(QColor(0, 200, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)

            painter.end()
            self.setIcon(QIcon(pixmap))
            print("[OK] 绿色小点已绘制")
        except Exception as e:
            print(f"[WARN] 绘制绿点失败: {e}")

    def _draw_red_dot(self):
        """在默认图标上绘制红色圆点（更新通知）"""
        try:
            pixmap = self._default_icon.pixmap(QSize(24, 24))
            if pixmap.isNull():
                pixmap = QPixmap(24, 24)
                pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            dot_size = 10
            dot_x = 18 - dot_size // 2
            dot_y = 6 - dot_size // 2
            painter.setBrush(QColor(0xFF, 0x3B, 0x30))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)
            painter.end()
            return QIcon(pixmap)
        except Exception as e:
            print(f"[WARN] 绘制红点失败: {e}")
            return self._default_icon

    def _update_tooltip(self):
        if self._has_notice:
            self.setToolTip(self.tr("珍爱桌面小工具") + "\n🔔 " + self.tr("有新的公告"))
        else:
            self.setToolTip(self.tr("珍爱桌面小工具"))

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

        # 同步悬停详情弹窗的层级，使其跟随主窗口模式
        if hasattr(window, '_detail_popup') and window._detail_popup:
            window._detail_popup.apply_window_mode(mode)

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

        mode_names = {"bottom": self.tr("置底"), "float": self.tr("悬浮模式"), "top": self.tr("总是置顶")}
        print(f"📌 窗口模式: {mode_names.get(mode, mode)}")

    def _on_mode_triggered(self, mode):
        """窗口模式切换（由菜单触发）"""
        if mode == self._window_mode:
            return
        self._apply_window_mode(mode)

    # ===== 任务栏窗口控制 =====
    def _load_taskbar_visible(self):
        """从 QSettings 加载任务栏窗口可见性，并同步菜单勾选与显示状态"""
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        self._taskbar_visible = settings.value("taskbar_visible", True, type=bool)
        # 同步菜单勾选状态
        if self._taskbar_action:
            self._taskbar_action.setChecked(self._taskbar_visible)
        # 统一由这里控制显示，避免 main_window 重复调用
        if hasattr(self.parent_window, 'toggle_taskbar_window'):
            self.parent_window.toggle_taskbar_window(self._taskbar_visible)

    def _save_taskbar_visible(self, visible: bool):
        """保存任务栏窗口可见性到 QSettings"""
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("taskbar_visible", visible)
        settings.sync()

    def _on_taskbar_toggled(self, checked: bool):
        """任务栏窗口显示/隐藏切换"""
        self._taskbar_visible = checked
        self._save_taskbar_visible(checked)
        if hasattr(self.parent_window, 'toggle_taskbar_window'):
            self.parent_window.toggle_taskbar_window(checked)
        print(f"\U0001f4bb 任务栏窗口: {'显示' if checked else '隐藏'}")

    # ===== 菜单 =====
    def _refresh_menu(self):
        """重新构建托盘菜单（语言切换时调用）"""
        self.setup_menu()

    def setup_menu(self):
        self.menu.clear()

        # 窗口模式（三个互斥选项）
        self._bottom_action = QAction("⬇️ " + self.tr("置底"), self)
        self._bottom_action.setCheckable(True)
        self._bottom_action.triggered.connect(lambda: self._on_mode_triggered("bottom"))

        self._float_action = QAction("↕️ " + self.tr("悬浮模式"), self)
        self._float_action.setCheckable(True)
        self._float_action.setChecked(True)  # 默认选中
        self._float_action.triggered.connect(lambda: self._on_mode_triggered("float"))

        self._top_action = QAction("📌 " + self.tr("总是置顶"), self)
        self._top_action.setCheckable(True)
        self._top_action.triggered.connect(lambda: self._on_mode_triggered("top"))

        # 添加到菜单（顺序固定）
        self.menu.addAction(self._bottom_action)
        self.menu.addAction(self._float_action)
        self.menu.addAction(self._top_action)

        self.menu.addSeparator()

        # 任务栏显示窗口（独立打勾）
        self._taskbar_action = QAction("\U0001f4bb " + self.tr("任务栏显示"), self)
        self._taskbar_action.setCheckable(True)
        self._taskbar_action.setChecked(self._taskbar_visible)
        self._taskbar_action.triggered.connect(self._on_taskbar_toggled)
        self.menu.addAction(self._taskbar_action)

        self.menu.addSeparator()

        # 设置、主题、检查更新
        settings_action = QAction("⚙️ " + self.tr("设置"), self)
        settings_action.triggered.connect(self.parent_window.open_settings)
        self.menu.addAction(settings_action)

        theme_action = QAction("🎨 " + self.tr("主题"), self)
        theme_action.triggered.connect(lambda: self.parent_window.open_settings(initial_page="theme"))
        self.menu.addAction(theme_action)

        update_action = QAction("🔄 " + self.tr("检查更新"), self)
        update_action.triggered.connect(lambda: self.parent_window.open_settings(initial_page="update"))
        self.menu.addAction(update_action)

        self.menu.addSeparator()

        exit_action = QAction("❌ " + self.tr("退出"), self)
        exit_action.triggered.connect(self.quit_app)
        self.menu.addAction(exit_action)

    def _on_menu_about_to_show(self):
        """菜单弹出前暂停嵌入器定时器，避免 bring_to_top 与菜单 z-order 竞态。"""
        mw = self.parent_window
        if mw and hasattr(mw, 'taskbar_widget') and mw.taskbar_widget:
            embedder = getattr(mw.taskbar_widget, '_embedder', None)
            if embedder:
                embedder._timer.stop()

    def _on_menu_about_to_hide(self):
        """菜单隐藏后恢复嵌入器定时器。"""
        mw = self.parent_window
        if mw and hasattr(mw, 'taskbar_widget') and mw.taskbar_widget:
            embedder = getattr(mw.taskbar_widget, '_embedder', None)
            if embedder and embedder._embedded:
                embedder._timer.start(500)

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Context:
            # 延迟 exec，避免在 activated 信号回调里嵌套事件循环导致栈损坏
            from PyQt6.QtGui import QCursor
            pos = QCursor.pos()
            QTimer.singleShot(0, lambda: self.menu.exec(pos))
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self._has_notice and not self._notice_opened:
                print("🖱 左键单击托盘图标 → 打开公告")
                self._open_notice_window()
            else:
                self.toggle_window()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window()

    # ===== 更新通知闪烁 =====
    def start_update_flash(self):
        """开始更新通知闪烁（红点 ↔ 默认图标，700ms）"""
        if self._update_flash_timer is not None:
            return
        # 停止公告闪烁
        self._stop_flash()
        self._green_dot_visible = False
        self._has_update = True
        self._update_flash_count = 0
        self._update_flash_timer = QTimer()
        self._update_flash_timer.timeout.connect(self._update_flash_icon)
        self._update_flash_timer.start(700)
        print("[Update] 托盘更新通知闪烁已启动")

    def _update_flash_icon(self):
        self._update_flash_count += 1
        if self._update_flash_count % 2 == 1:
            self.setIcon(self._draw_red_dot())
        else:
            self.setIcon(self._default_icon)

    def stop_update_flash(self):
        """停止更新通知闪烁，恢复默认图标"""
        if self._update_flash_timer is not None:
            self._update_flash_timer.stop()
            self._update_flash_timer = None
        self._has_update = False
        self._update_flash_count = 0
        self.setIcon(self._default_icon)
        self._update_tooltip()
        print("[Update] 托盘更新通知闪烁已停止")

    def _open_notice_window(self):
        manager = NoticeManager.get_instance()
        notice = manager.get_current_notice()
        if notice is None:
            return

        self._notice_opened = True
        self._green_dot_visible = False
        self.setIcon(self._default_icon)
        self._update_tooltip()

        # 同时停止主窗口气泡闪烁
        if hasattr(self.parent_window, 'notice_bubble') and self.parent_window.notice_bubble:
            self.parent_window.notice_bubble.hide_bubble()

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

    def quit_app(self):
        self.parent_window._exiting = True
        self.parent_window.shutdown()
        QApplication.quit()
