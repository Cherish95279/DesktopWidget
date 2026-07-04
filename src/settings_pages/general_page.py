from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QFontDatabase, QColor
from PyQt6.QtWidgets import QColorDialog
from ..autostart import set_autostart, get_autostart_status
from ..notice import NoticeWindow


# ===== QSS 统一下拉框样式（边框改为 #ddd） =====
COMBO_STYLE = """
    QComboBox {
        border: 1px solid #ddd;
        border-radius: 4px;
        background: #f5f5f5;
        color: #333;
        font-size: 12px;
        padding: 0 4px;
        height: 28px;
    }
    QComboBox:hover {
        background: #e6f4ff;
        border: 1px solid #1677ff;
        color: #1677ff;
    }
"""


class GeneralPage(QWidget):
    font_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_color = "#1c344d"
        self.autostart_checked = False
        self.parent_dialog = parent
        self._notice_window = None
        self._loading = False

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(10)

        autostart_row = QHBoxLayout()
        autostart_row.setContentsMargins(0, 0, 0, 0)
        autostart_row.setSpacing(6)

        self.autostart_icon = QLabel("✅", self)
        self.autostart_icon.setStyleSheet("font-size: 16px;")
        autostart_row.addWidget(self.autostart_icon)

        self.autostart_label = QLabel("开机自启动", self)
        self.autostart_label.setStyleSheet("font-size: 12px; color: #333;")
        autostart_row.addWidget(self.autostart_label)

        autostart_row.addStretch()

        self.notice_btn = QPushButton("📢 查看公告")
        self.notice_btn.setFixedSize(90, 28)
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
        self.notice_btn.clicked.connect(self._open_notice_window)
        autostart_row.addWidget(self.notice_btn)

        self.autostart_widget = QWidget(self)
        self.autostart_widget.setLayout(autostart_row)
        self.autostart_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        self.autostart_widget.mousePressEvent = self.on_autostart_widget_clicked

        layout.addWidget(self.autostart_widget)

        font_label = QLabel("字体设置")
        font_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(font_label)

        font_layout = QHBoxLayout()
        font_layout.setSpacing(10)

        self.font_combo = QComboBox()
        self.font_combo.setFixedSize(120, 28)
        self.font_combo.setStyleSheet(COMBO_STYLE)
        font_families = QFontDatabase.families()
        self.font_combo.addItems(font_families)
        font_layout.addWidget(self.font_combo)

        self.size_combo = QComboBox()
        self.size_combo.setFixedSize(90, 28)
        self.size_combo.setStyleSheet(COMBO_STYLE)
        for size in range(8, 16):
            self.size_combo.addItem(str(size))
        font_layout.addWidget(self.size_combo)

        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(90, 28)
        self.color_btn.setStyleSheet("border: 1px solid #999; border-radius: 4px;")
        self.color_btn.clicked.connect(self.choose_color)
        font_layout.addWidget(self.color_btn)

        font_layout.addStretch()
        layout.addLayout(font_layout)

        layout.addStretch()

        self.font_combo.currentTextChanged.connect(self.apply_font_settings)
        self.size_combo.currentTextChanged.connect(self.apply_font_settings)

    # ---------- 其余方法保持不变 ----------
    def _open_notice_window(self):
        if self._notice_window is not None and self._notice_window.isVisible():
            self._notice_window.raise_()
            self._notice_window.activateWindow()
            return

        parent = self.parent()
        if parent and hasattr(parent, 'parent'):
            main_window = parent.parent()
            if main_window:
                self._notice_window = NoticeWindow(main_window)
                self._notice_window.destroyed.connect(self._on_notice_window_destroyed)
                from ..notice import NoticeManager
                manager = NoticeManager.get_instance()
                current = manager.get_current_notice()
                if current:
                    notice_id = current.get("id")
                    if notice_id:
                        QTimer.singleShot(300, lambda: self._notice_window.select_notice_by_id(notice_id) if self._notice_window else None)
                self._notice_window.show()
                return

        self._notice_window = NoticeWindow(self)
        self._notice_window.show()

    def _on_notice_window_destroyed(self):
        self._notice_window = None

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

    def load_settings(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        self._loading = True
        try:
            self.autostart_checked = get_autostart_status()
            self.update_autostart_display()
            self.load_font_settings()
        finally:
            self._loading = False

    def save_settings(self):
        pass