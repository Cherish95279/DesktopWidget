import sys
import locale
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QColor, QFont, QFontDatabase
from ..utils import resource_path
from ..i18n.translations import TranslatorManager
from ..notice.notice_manager import NoticeManager


class GeneralPage(QWidget):
    font_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self._loading = True
        self._updating = False
        self.autostart_checked = False
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 20, 15, 15)
        main_layout.setSpacing(15)

        # 第1行：开机自启动 + 查看公告
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self.autostart_btn = QPushButton("⬜ " + self.tr("开机时自动启动"))
        self.autostart_btn.setFlat(True)
        self.autostart_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-size: 12px;
                color: #333;
                background: transparent;
                border: none;
                padding: 2px 0;
            }
            QPushButton:hover {
                color: #1677ff;
            }
        """)
        self.autostart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.autostart_btn.clicked.connect(self._toggle_autostart)
        row1.addWidget(self.autostart_btn)

        row1.addStretch()

        self.notice_btn = QPushButton("📢 " + self.tr("查看公告"))
        self.notice_btn.setFixedSize(120, 28)
        self.notice_btn.setStyleSheet(self._btn_style())
        self.notice_btn.clicked.connect(self._on_notice_clicked)
        row1.addWidget(self.notice_btn)

        main_layout.addLayout(row1)

        # 字体设置
        font_label = QLabel(self.tr("字体设置"))
        font_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        main_layout.addWidget(font_label)

        row3 = QHBoxLayout()
        row3.setSpacing(10)

        self.font_combo = QComboBox()
        self.font_combo.setFixedHeight(28)
        self.font_combo.setMinimumWidth(180)
        self.font_combo.addItems(QFontDatabase.families())
        self.font_combo.setStyleSheet(self._combo_style())
        self.font_combo.currentTextChanged.connect(self._on_font_changed)
        row3.addWidget(self.font_combo)

        self.font_size_combo = QComboBox()
        self.font_size_combo.setFixedHeight(28)
        self.font_size_combo.addItems([str(i) for i in range(8, 16)])
        self.font_size_combo.setStyleSheet(self._combo_style())
        self.font_size_combo.currentTextChanged.connect(self._on_font_size_changed)
        row3.addWidget(self.font_size_combo)

        self.font_color_btn = QPushButton(self.tr("字体颜色"))
        self.font_color_btn.setFixedSize(80, 28)
        self.font_color_btn.setStyleSheet(self._btn_style())
        self.font_color_btn.clicked.connect(self._on_font_color_clicked)
        row3.addWidget(self.font_color_btn)

        row3.addStretch()
        main_layout.addLayout(row3)

        # 窗口模式 + 语言设置
        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(6)

        # 窗口模式
        mode_label = QLabel(self.tr("窗口模式"))
        mode_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        grid.addWidget(mode_label, 0, 0, Qt.AlignmentFlag.AlignLeft)

        self.mode_combo = QComboBox()
        self.mode_combo.setFixedHeight(28)
        self.mode_combo.addItems([
            self.tr("悬浮模式"),
            self.tr("置底"),
            self.tr("总是置顶")
        ])
        self.mode_combo.setStyleSheet(self._combo_style())
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        grid.addWidget(self.mode_combo, 1, 0, Qt.AlignmentFlag.AlignLeft)

        # 语言设置（下拉框选项已用 tr() 包裹）
        lang_label = QLabel(self.tr("语言设置"))
        lang_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        grid.addWidget(lang_label, 0, 1, Qt.AlignmentFlag.AlignLeft)

        self.lang_combo = QComboBox()
        self.lang_combo.setFixedHeight(28)
        self.lang_combo.addItems([
            "中文简体",
            "中文繁體",
            "English",
            "Español",
            "日本語",
            "Deutsch",
            "Français",
            "한국어"
        ])
        self.lang_combo.setStyleSheet(self._combo_style())
        self.lang_codes = ["zh_CN", "zh_TW", "en", "es", "ja", "de", "fr", "ko"]
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        grid.addWidget(self.lang_combo, 1, 1, Qt.AlignmentFlag.AlignLeft)

        main_layout.addLayout(grid)

        # 恢复默认按钮
        main_layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.restore_btn = QPushButton(self.tr("恢复默认"))
        self.restore_btn.setFixedSize(90, 28)
        self.restore_btn.setStyleSheet(self._btn_style())
        self.restore_btn.clicked.connect(self.restore_default)
        btn_row.addWidget(self.restore_btn)

        main_layout.addLayout(btn_row)
        main_layout.addStretch()

    # ---------- 样式 ----------
    def _btn_style(self):
        return """
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
        """

    def _combo_style(self):
        return """
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                background: #f5f5f5;
                color: #333;
                font-size: 12px;
                padding: 0 4px;
                height: 28px;
                min-width: 100px;
            }
            QComboBox:hover {
                background: #e6f4ff;
                border: 1px solid #1677ff;
                color: #1677ff;
            }
            QComboBox::item:selected {
                background: #1677ff;
                color: white;
            }
        """

    # ---------- 信号处理 ----------
    def _toggle_autostart(self):
        if self._updating:
            return
        self.autostart_checked = not self.autostart_checked
        self._update_autostart_button()
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("autostart", self.autostart_checked)
        settings.sync()
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, 'set_autostart'):
            if not main_window.set_autostart(self.autostart_checked):
                QMessageBox.warning(
                    self,
                    self.tr("提示"),
                    self.tr("设置开机自启动失败，请检查权限")
                )

    def _update_autostart_button(self):
        if self.autostart_checked:
            self.autostart_btn.setText("✅ " + self.tr("开机时自动启动"))
        else:
            self.autostart_btn.setText("⬜ " + self.tr("开机时自动启动"))

    def _on_notice_clicked(self):
        # 1. 触发远程刷新
        NoticeManager.get_instance().refresh_notice()
        # 2. 打开公告窗口（原有逻辑不变）
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, '_open_notice_window'):
            main_window._open_notice_window()
    def _on_mode_changed(self, index):
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, '_open_notice_window'):
            main_window._open_notice_window()

    def _on_mode_changed(self, index):
        if self._updating:
            return
        modes = ["float", "bottom", "top"]
        mode = modes[index]
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("window_mode", mode)
        settings.sync()
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, 'tray'):
            main_window.tray._apply_window_mode(mode)

    def _on_font_changed(self, font_name):
        if self._updating:
            return
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("font_family", font_name)
        settings.sync()
        self.font_changed.emit()

    def _on_font_size_changed(self, size_str):
        if self._updating:
            return
        try:
            size = int(size_str)
        except ValueError:
            return
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("font_size", size)
        settings.sync()
        self.font_changed.emit()

    def _on_font_color_clicked(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        current_color = settings.value("font_color", "#1c344d")
        color = QColorDialog.getColor(QColor(current_color), self, self.tr("选择文字颜色"))
        if color.isValid():
            settings.setValue("font_color", color.name())
            settings.sync()
            self.font_changed.emit()

    def _on_language_changed(self, index):
        if self._loading or self._updating:
            return
        if index < 0 or index >= len(self.lang_codes):
            return
        lang_code = self.lang_codes[index]
        TranslatorManager().switch_language(lang_code)

        # 重启提示
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("提示"))
        msg.setText(self.tr("语言设置已更改，需要重新启动程序才能生效。是否立即重启？"))
        yes_btn = msg.addButton(self.tr("是"), QMessageBox.ButtonRole.YesRole)
        no_btn = msg.addButton(self.tr("否"), QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(yes_btn)
        msg.exec()
        if msg.clickedButton() == yes_btn:
            self._restart_app()

    def _restart_app(self):
        if self._loading:
            return
        if getattr(sys, 'frozen', False):
            QProcess.startDetached(sys.executable, sys.argv)
        else:
            import os
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "widget.py")
            QProcess.startDetached(sys.executable, [script_path])
        os._exit(0)

    # ---------- 加载设置 ----------
    def load_settings(self):
        self._updating = True
        self._loading = True
        try:
            settings = QSettings("MyDesktopApp", "WeatherSettings")

            self.autostart_checked = settings.value("autostart", False, type=bool)
            self._update_autostart_button()

            mode = settings.value("window_mode", "float")
            mode_index = {"float": 0, "bottom": 1, "top": 2}.get(mode, 0)
            self.mode_combo.setCurrentIndex(mode_index)

            font_family = settings.value("font_family", "微软雅黑")
            idx = self.font_combo.findText(font_family)
            if idx >= 0:
                self.font_combo.setCurrentIndex(idx)

            font_size = settings.value("font_size", 10, type=int)
            size_str = str(font_size)
            idx = self.font_size_combo.findText(size_str)
            if idx >= 0:
                self.font_size_combo.setCurrentIndex(idx)

            # 语言（阻断信号，避免初始化时触发切换）
            self.lang_combo.blockSignals(True)
            self._load_language_setting()
            self.lang_combo.blockSignals(False)

        finally:
            self._updating = False
            self._loading = False

    def _load_language_setting(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        lang_code = settings.value("language", "")
        if not lang_code:
            try:
                sys_lang, _ = locale.getdefaultlocale()
                if sys_lang:
                    if sys_lang.startswith("zh_CN"):
                        lang_code = "zh_CN"
                    elif sys_lang.startswith("zh_TW") or sys_lang.startswith("zh_HK"):
                        lang_code = "zh_TW"
                    elif sys_lang.startswith("en"):
                        lang_code = "en"
                    elif sys_lang.startswith("es"):
                        lang_code = "es"
                    elif sys_lang.startswith("ja"):
                        lang_code = "ja"
                    elif sys_lang.startswith("de"):
                        lang_code = "de"
                    elif sys_lang.startswith("fr"):
                        lang_code = "fr"
                    elif sys_lang.startswith("ko"):
                        lang_code = "ko"
                    else:
                        lang_code = "zh_CN"
                else:
                    lang_code = "zh_CN"
            except:
                lang_code = "zh_CN"
            settings.setValue("language", lang_code)
            settings.sync()

        if lang_code in self.lang_codes:
            index = self.lang_codes.index(lang_code)
            self.lang_combo.setCurrentIndex(index)

    def _get_main_window(self):
        if self.parent_dialog:
            main = self.parent_dialog.parent()
            if main:
                return main
        for widget in QApplication.topLevelWidgets():
            if widget.__class__.__name__ == "MainWindow":
                return widget
        return None

    # ---------- 恢复默认 ----------
    def restore_default(self):
        self._updating = True
        try:
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            settings.remove("autostart")
            settings.remove("window_mode")
            settings.remove("font_family")
            settings.remove("font_size")
            settings.remove("font_color")
            # settings.remove("language")  # 注释掉：恢复默认时不重置语言设置
            settings.sync()

            self.autostart_checked = False
            self._update_autostart_button()
            self.mode_combo.setCurrentIndex(0)
            self.font_combo.setCurrentIndex(0)
            self.font_size_combo.setCurrentText("10")
            self.font_changed.emit()

            # self._load_language_setting()  # 注释掉：不重新加载语言设置

            main_window = self._get_main_window()
            if main_window and hasattr(main_window, 'tray'):
                main_window.tray._apply_window_mode("float")

        finally:
            self._updating = False