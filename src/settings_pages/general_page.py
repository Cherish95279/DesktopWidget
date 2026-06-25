from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QFontDatabase, QColor
from PyQt6.QtWidgets import QColorDialog
from ..autostart import set_autostart, get_autostart_status


class GeneralPage(QWidget):
    font_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_color = "#1c344d"
        self.autostart_checked = False
        self.parent_dialog = parent

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(10)

        # ---------- 第一行：公告弹窗 + 开机自启动 ----------
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # 公告弹窗按钮
        self.notice_btn = QPushButton("📋 公告弹窗")
        self.notice_btn.setFixedSize(100, 28)
        self.notice_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: #f5f5f5;
                color: #333;
            }
            QPushButton:hover {
                background: #e6f4ff;
                border: 1px solid #1677ff;
                color: #1677ff;
            }
        """)
        self.notice_btn.clicked.connect(self.open_notice_dialog)
        top_row.addWidget(self.notice_btn)

        # 按钮与自启动之间的间距
        top_row.addSpacing(10)

        # 开机自启动控件
        self.autostart_widget = QWidget(self)
        autostart_layout = QHBoxLayout(self.autostart_widget)
        autostart_layout.setContentsMargins(0, 0, 0, 0)
        autostart_layout.setSpacing(6)

        self.autostart_icon = QLabel("✅", self)
        self.autostart_icon.setStyleSheet("font-size: 16px;")
        autostart_layout.addWidget(self.autostart_icon)

        self.autostart_label = QLabel("开机自启动", self)
        self.autostart_label.setStyleSheet("font-size: 12px; color: #333;")
        autostart_layout.addWidget(self.autostart_label)

        autostart_layout.addStretch()
        self.autostart_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        self.autostart_widget.mousePressEvent = self.on_autostart_widget_clicked

        top_row.addWidget(self.autostart_widget)
        top_row.addStretch()

        layout.addLayout(top_row)

        # ---------- 字体设置 ----------
        font_label = QLabel("字体设置")
        font_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(font_label)

        font_layout = QHBoxLayout()
        font_layout.setSpacing(10)

        self.font_combo = QComboBox()
        self.font_combo.setMinimumWidth(100)
        font_families = QFontDatabase.families()
        self.font_combo.addItems(font_families)
        font_layout.addWidget(self.font_combo)

        self.size_combo = QComboBox()
        self.size_combo.setMinimumWidth(50)
        for size in range(8, 16):
            self.size_combo.addItem(str(size))
        font_layout.addWidget(self.size_combo)

        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(30, 28)
        self.color_btn.setStyleSheet("border: 1px solid #999; border-radius: 4px;")
        self.color_btn.clicked.connect(self.choose_color)
        font_layout.addWidget(self.color_btn)
        font_layout.addStretch()

        layout.addLayout(font_layout)

        layout.addStretch()

        # 信号连接（字体实时生效）
        self.font_combo.currentTextChanged.connect(self.apply_font_settings)
        self.size_combo.currentTextChanged.connect(self.apply_font_settings)

    # ==================== 修改点 ====================
    def open_notice_dialog(self):
        """打开公告窗口（复用主窗口的管理逻辑，避免创建多个窗口）"""
        # 通过父级链获取主窗口
        main_window = self.parent_dialog.parent() if self.parent_dialog else None
        if main_window and hasattr(main_window, '_open_notice_window'):
            main_window._open_notice_window()
        else:
            # 保底方案：直接创建（正常情况下不会执行到这里）
            from ..notice import NoticeWindow
            window = NoticeWindow(self)
            window.show()
    # =============================================

    # ---------- 开机自启动 ----------
    def update_autostart_display(self):
        if self.autostart_checked:
            self.autostart_icon.setText("✅")
        else:
            self.autostart_icon.setText("⬜")
        self.autostart_label.setStyleSheet("font-size: 12px; color: #333;")

    def on_autostart_widget_clicked(self, event):
        self.autostart_checked = not self.autostart_checked
        self.update_autostart_display()
        if self.autostart_checked:
            if not set_autostart(True):
                QMessageBox.warning(self, "提示", "设置开机自启动失败，请检查权限")
                self.autostart_checked = False
                self.update_autostart_display()
        else:
            set_autostart(False)

    # ---------- 字体设置 ----------
    def load_font_settings(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        font_family = settings.value("font_family", "Microsoft YaHei")
        font_size = int(settings.value("font_size", 10))
        font_color = settings.value("font_color", "#1c344d")

        idx = self.font_combo.findText(font_family)
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)

        idx = self.size_combo.findText(str(font_size))
        if idx >= 0:
            self.size_combo.setCurrentIndex(idx)

        self._current_color = font_color
        self.update_color_button()

    def update_color_button(self):
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._current_color};
                border: 1px solid #999;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #666;
            }}
        """)

    def choose_color(self):
        try:
            dialog = QColorDialog(self)
            dialog.setCurrentColor(QColor(self._current_color))
            dialog.setWindowTitle("选择文字颜色")
            if dialog.exec() == QDialog.DialogCode.Accepted:
                color = dialog.selectedColor()
                if color.isValid():
                    self._current_color = color.name()
                    self.update_color_button()
                    self.apply_font_settings()
        except Exception as e:
            print(f"颜色选择异常: {e}")

    def apply_font_settings(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("font_family", self.font_combo.currentText())
        settings.setValue("font_size", int(self.size_combo.currentText()))
        settings.setValue("font_color", self._current_color)
        self.font_changed.emit()

    # ---------- 加载 ----------
    def load_settings(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        self.autostart_checked = get_autostart_status()
        self.update_autostart_display()
        self.load_font_settings()

    def save_settings(self):
        pass