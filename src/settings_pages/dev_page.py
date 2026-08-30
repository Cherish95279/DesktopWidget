# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *


class DevPage(QWidget):
    dev_mode_changed = pyqtSignal(bool)
    pro_status_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self._loading = True
        self._dev_enabled = QSettings("MyDesktopApp", "WeatherSettings").value("dev_mode_enabled", False, type=bool)
        self._pro_enabled = QSettings("MyDesktopApp", "WeatherSettings").value("dev_pro_enabled", False, type=bool)
        self.setup_ui()
        self.load_token()
        self.load_settings()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 20, 15, 15)
        main_layout.setSpacing(15)

        # 标题
        title = QLabel(self.tr("开发选项"))
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        main_layout.addWidget(title)

        # 启用开发模式 - 与开机自启同款UI
        self.dev_btn = QPushButton("✅ " + self.tr("启用开发模式") if self._dev_enabled else "⬜ " + self.tr("启用开发模式"))
        self.dev_btn.setFlat(True)
        self.dev_btn.setStyleSheet("""
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
        self.dev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dev_btn.clicked.connect(self._toggle_dev_mode)
        main_layout.addWidget(self.dev_btn)

        # ---------- Token 区域 ----------
        token_label = QLabel(self.tr("GitHub Token"))
        token_label.setStyleSheet("font-size: 12px; color: #333;")
        main_layout.addWidget(token_label)

        token_input_layout = QHBoxLayout()
        self.token_edit = QLineEdit()
        self.token_edit.setPlaceholderText(self.tr("GitHub Token（可选）"))
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setMinimumHeight(28)
        self.token_edit.textChanged.connect(self.save_token)
        token_input_layout.addWidget(self.token_edit)

        self.token_visibility_btn = QPushButton("👁")
        self.token_visibility_btn.setFixedSize(28, 28)
        self.token_visibility_btn.setCheckable(True)
        self.token_visibility_btn.setToolTip(self.tr("显示/隐藏 Token"))
        self.token_visibility_btn.clicked.connect(self.toggle_token_visibility)
        self.token_visibility_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 4px;
                background: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #f0f0f0;
            }
        """)
        token_input_layout.addWidget(self.token_visibility_btn)
        main_layout.addLayout(token_input_layout)


        # ---------- 付费状态 ----------
        pro_label = QLabel(self.tr("付费状态（开发测试）"))
        pro_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #e67e22;")
        main_layout.addWidget(pro_label)

        pro_row = QHBoxLayout()
        self.pro_combo = QComboBox()
        self.pro_combo.setFixedHeight(28)
        self.pro_combo.setMinimumWidth(120)
        self.pro_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ccc;
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
        """)
        self.pro_combo.addItem(self.tr("免费版"), False)
        self.pro_combo.addItem(self.tr("已付费"), True)
        self.pro_combo.currentIndexChanged.connect(self._on_pro_changed)
        pro_row.addWidget(self.pro_combo)

        self.pro_status_label = QLabel()
        self.pro_status_label.setStyleSheet("font-size: 11px; color: #999;")
        pro_row.addWidget(self.pro_status_label)
        pro_row.addStretch()
        main_layout.addLayout(pro_row)

        # ---------- 版本选择 ----------
        version_label = QLabel(self.tr("版本"))
        version_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #e67e22;")
        main_layout.addWidget(version_label)

        version_row = QHBoxLayout()
        self.version_combo = QComboBox()
        self.version_combo.setFixedHeight(28)
        self.version_combo.setMinimumWidth(120)
        self.version_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ccc;
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
        """)
        self.version_combo.addItem(self.tr("exe版"), "exe")
        self.version_combo.addItem(self.tr("商店版"), "store")
        self.version_combo.currentIndexChanged.connect(self._on_version_changed)
        version_row.addWidget(self.version_combo)
        version_row.addStretch()
        main_layout.addLayout(version_row)

        main_layout.addStretch()
        self.load_settings()

    def _toggle_dev_mode(self):
        self._dev_enabled = not self._dev_enabled
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("dev_mode_enabled", self._dev_enabled)
        settings.sync()
        self._update_button_text()
        self.dev_mode_changed.emit(self._dev_enabled)

    def _on_pro_changed(self, index):
        self._pro_enabled = self.pro_combo.currentData()
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("dev_pro_enabled", self._pro_enabled)
        settings.sync()
        self._update_pro_status_text()
        self.pro_status_changed.emit(self._pro_enabled)

    def _on_version_changed(self, index):
        if self._loading:
            return
        val = self.version_combo.currentData()
        if val is None:
            return
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("dev_version", val)
        # exe版：悬停开关默认关；商店版：悬停开关默认开
        hover_on = (val == "store")
        settings.setValue("hover_enabled", hover_on)
        settings.sync()
        # 同步显示项目页的悬停开关下拉框
        dlg = self.parent_dialog
        if dlg and hasattr(dlg, 'page_creators'):
            # 确保显示项目页已创建
            if 1 in dlg.page_creators:
                display_page = dlg.page_creators[1]()
                if hasattr(display_page, "hover_combo"):
                    hover_idx = display_page.hover_combo.findData("on" if hover_on else "off")
                    if hover_idx >= 0:
                        display_page.hover_combo.blockSignals(True)
                        display_page.hover_combo.setCurrentIndex(hover_idx)
                        display_page.hover_combo.blockSignals(False)

    def _update_pro_status_text(self):
        if self._pro_enabled:
            self.pro_status_label.setText(self.tr("✅ 开发测试中"))
        else:
            self.pro_status_label.setText("")

    def _update_button_text(self):
        if self._dev_enabled:
            self.dev_btn.setText("✅ " + self.tr("启用开发模式"))
        else:
            self.dev_btn.setText("⬜ " + self.tr("启用开发模式"))

    def load_token(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        token = settings.value("github_token", "")
        if token:
            self.token_edit.setText(token)

    def save_token(self):
        token = self.token_edit.text().strip()
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        if token:
            settings.setValue("github_token", token)
        else:
            settings.remove("github_token")

    def toggle_token_visibility(self):
        if self.token_visibility_btn.isChecked():
            self.token_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.token_visibility_btn.setText("🙈")
        else:
            self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.token_visibility_btn.setText("👁")

    def load_settings(self):
        self._loading = True
        try:
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            self._dev_enabled = settings.value("dev_mode_enabled", False, type=bool)
            self._pro_enabled = settings.value("dev_pro_enabled", False, type=bool)
            self._update_button_text()
            self._update_pro_status_text()
            # 同步下拉框
            idx = self.pro_combo.findData(self._pro_enabled)
            if idx >= 0:
                self.pro_combo.setCurrentIndex(idx)
            # 同步版本下拉框
            dev_version = settings.value("dev_version", "", type=str)
            if not dev_version:
                # 首次打开：自动检测真实版本
                from ..updater import is_store_version
                dev_version = "store" if is_store_version() else "exe"
                settings.setValue("dev_version", dev_version)
                settings.sync()
            vidx = self.version_combo.findData(dev_version)
            if vidx >= 0:
                self.version_combo.setCurrentIndex(vidx)
        finally:
            self._loading = False