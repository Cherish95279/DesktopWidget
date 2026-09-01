from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QColorDialog
from ..constants import DEFAULT_THEME, THEME_PRESETS
from PyQt6.QtCore import QCoreApplication
from ..theme_manager import get_theme_manager
from .import_theme_dialog import ImportThemeDialog


# ===== 统一下拉框样式 =====
COMBO_STYLE = """
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
"""


BTN_STYLE = """
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
    QPushButton:disabled {
        color: #aaa;
        background: #f0f0f0;
        border: 1px solid #ddd;
    }
"""


class ThemePage(QWidget):
    """主题设置页面"""

    theme_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self._updating = False
        self.theme_manager = get_theme_manager()

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 20, 15, 15)
        main_layout.setSpacing(10)

        self._create_label_row(main_layout)
        self._create_control_row(main_layout)
        self._create_import_delete_row(main_layout)
        self._create_opacity_section(main_layout)
        self._create_tint_section(main_layout)
        self._create_reset_button(main_layout)

        main_layout.addStretch()

    def _create_label_row(self, parent_layout):
        """创建第一行：主题切换 + 背景颜色标签"""
        label_row = QHBoxLayout()
        label_row.setSpacing(0)
        label_row.setContentsMargins(0, 0, 0, 0)

        self.theme_label = QLabel(self.tr("主题切换"))
        self.theme_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        label_row.addWidget(self.theme_label)

        label_row.addStretch()

        # 容器宽度与色块组宽度一致：3个预设(28px) + 1个自定义(28px) + 3个间距(6px) = 130px
        color_label_widget = QWidget()
        color_label_widget.setFixedWidth(130)
        color_label_widget.setStyleSheet("background: transparent;")
        color_label_inner = QHBoxLayout(color_label_widget)
        color_label_inner.setContentsMargins(0, 0, 0, 0)
        color_label_inner.setSpacing(0)

        self.color_label = QLabel(self.tr("背景颜色"))
        self.color_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        color_label_inner.addWidget(self.color_label)
        color_label_inner.addStretch()

        label_row.addWidget(color_label_widget)
        parent_layout.addLayout(label_row)

    def _create_control_row(self, parent_layout):
        """创建第二行：主题下拉框 + 颜色预设按钮"""
        control_row = QHBoxLayout()
        control_row.setSpacing(10)
        control_row.setContentsMargins(0, 0, 0, 0)

        self.theme_combo = QComboBox()
        self.theme_combo.setFixedWidth(140)
        self.theme_combo.setFixedHeight(28)
        self.theme_combo.setStyleSheet(COMBO_STYLE)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        control_row.addWidget(self.theme_combo)

        control_row.addStretch()

        color_widget = QWidget()
        color_layout = QHBoxLayout(color_widget)
        color_layout.setSpacing(6)
        color_layout.setContentsMargins(0, 0, 0, 0)

        self._create_color_buttons(color_layout)

        control_row.addWidget(color_widget)
        parent_layout.addLayout(control_row)

    def _create_color_buttons(self, color_layout):
        """创建颜色预设按钮和自定义颜色按钮"""
        self.color_buttons = []
        for preset in THEME_PRESETS:
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {preset['color']};
                    border: 2px solid #ccc;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid #888;
                }}
                QPushButton:checked {{
                    border: 3px solid #1677ff;
                }}
            """)
            btn.setCheckable(True)
            btn.setToolTip(preset['name'])
            btn.setProperty("color", preset['color'])
            btn.clicked.connect(lambda checked, b=btn: self._on_preset_clicked(b))
            color_layout.addWidget(btn)
            self.color_buttons.append(btn)

        self.custom_btn = QPushButton("🎨")
        self.custom_btn.setFixedSize(28, 28)
        self.custom_btn.setStyleSheet("""
            QPushButton {
                border: 2px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                border: 2px solid #888;
            }
        """)
        self.custom_btn.setToolTip(self.tr("自定义颜色"))
        self.custom_btn.clicked.connect(self._on_custom_color)
        color_layout.addWidget(self.custom_btn)

    def _create_opacity_section(self, parent_layout):
        """创建不透明度滑块区域"""
        opacity_label = QLabel(self.tr("不透明度"))
        opacity_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        parent_layout.addWidget(opacity_label)

        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(10)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setTickInterval(10)
        self.opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self.opacity_slider)

        self.opacity_label = QLabel("100%")
        self.opacity_label.setFixedWidth(40)
        self.opacity_label.setStyleSheet("font-size: 13px; color: #666;")
        opacity_row.addWidget(self.opacity_label)

        parent_layout.addLayout(opacity_row)

    def _create_tint_section(self, parent_layout):
        """创建着色强度滑块区域"""
        tint_label = QLabel(self.tr("着色强度"))
        tint_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        parent_layout.addWidget(tint_label)

        tint_row = QHBoxLayout()
        tint_row.setSpacing(10)

        self.tint_slider = QSlider(Qt.Orientation.Horizontal)
        self.tint_slider.setRange(0, 255)
        self.tint_slider.setValue(80)
        self.tint_slider.setTickInterval(25)
        self.tint_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.tint_slider.valueChanged.connect(self._on_tint_changed)
        tint_row.addWidget(self.tint_slider)

        self.tint_label = QLabel("31%")
        self.tint_label.setFixedWidth(40)
        self.tint_label.setStyleSheet("font-size: 13px; color: #666;")
        tint_row.addWidget(self.tint_label)

        parent_layout.addLayout(tint_row)

    def _create_reset_button(self, parent_layout):
        """创建底部的\"恢复默认\"按钮"""
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.restore_btn = QPushButton(self.tr("恢复默认"))
        self.restore_btn.setFixedSize(90, 28)
        self.restore_btn.setStyleSheet("""
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
        self.restore_btn.clicked.connect(self.restore_default)
        btn_row.addWidget(self.restore_btn)

        parent_layout.addLayout(btn_row)

    def _create_import_delete_row(self, parent_layout):
        """创建导入/删除主题按钮行"""
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)

        self.import_btn = QPushButton(self.tr("导入主题"))
        self.import_btn.setFixedSize(90, 28)
        self.import_btn.setStyleSheet(BTN_STYLE)
        self.import_btn.clicked.connect(self._on_import_theme)
        row.addWidget(self.import_btn)

        row.addStretch()

        self.delete_btn = QPushButton(self.tr("删除主题"))
        self.delete_btn.setFixedSize(90, 28)
        self.delete_btn.setStyleSheet(BTN_STYLE)
        self.delete_btn.clicked.connect(self._on_delete_theme)
        row.addWidget(self.delete_btn)

        parent_layout.addLayout(row)
        # 主题切换时同步删除按钮可用状态
        self.theme_combo.currentTextChanged.connect(self._update_delete_button_state)

    # ---------- 导入 / 删除主题 ----------
    def _update_delete_button_state(self, _text=None):
        current = self.theme_combo.currentText()
        if current and not self.theme_manager.is_builtin(current):
            self.delete_btn.setEnabled(True)
            self.delete_btn.setToolTip("")
        else:
            self.delete_btn.setEnabled(False)
            self.delete_btn.setToolTip(self.tr("内置主题不可删除"))

    def _on_import_theme(self):
        dialog = ImportThemeDialog(self.theme_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.imported_theme_name
            if new_name:
                self.theme_manager.switch_theme(new_name)
                self._refresh_theme_combo(select_name=new_name)
                self.theme_changed.emit()
                self._force_reload_images()

    def _on_delete_theme(self):
        current = self.theme_combo.currentText()
        if not current or self.theme_manager.is_builtin(current):
            return
        confirm = QMessageBox.question(
            self, self.tr("删除主题"),
            self.tr("确定删除主题「%1」吗？此操作不可撤销").arg(current),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        success, msg = self.theme_manager.delete_theme(current)
        if success:
            self._refresh_theme_combo(select_name=msg)
            self.theme_changed.emit()
            self._force_reload_images()
        else:
            QMessageBox.warning(self, self.tr("删除失败"), msg)

    def _refresh_theme_combo(self, select_name=None):
        self._updating = True
        try:
            self.theme_combo.clear()
            self.theme_combo.addItems(self.theme_manager.list_themes())
            target = select_name or self.theme_manager.get_current_theme()
            idx = self.theme_combo.findText(target)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)
        finally:
            self._updating = False
        self._update_delete_button_state()

    # ---------- 信号处理 ----------
    def _on_theme_changed(self, theme_name):
        if self._updating:
            return
        if theme_name:
            self.theme_manager.switch_theme(theme_name)
            self.theme_changed.emit()
            self._force_reload_images()

    def _on_opacity_changed(self, value):
        self.opacity_label.setText(f"{value}%")
        self._apply_theme()

    def _on_tint_changed(self, value):
        percent = int(value / 255 * 100)
        self.tint_label.setText(f"{percent}%")
        self._apply_theme()

    def _on_preset_clicked(self, btn):
        color = btn.property("color")
        for b in self.color_buttons:
            b.setChecked(b is btn)
        self.custom_btn.setChecked(False)
        self._apply_theme(color=color)

    def _on_custom_color(self):
        current_color = self._get_current_color()
        dialog = QColorDialog(QColor(current_color), self)
        # ???? Qt ???????Windows ????????? Qt ?????
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        dialog.setWindowTitle(self.tr("选择背景颜色"))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            color = dialog.currentColor()
            if color.isValid():
                color_hex = color.name()
                for b in self.color_buttons:
                    b.setChecked(False)
                self.custom_btn.setChecked(True)
                self._apply_theme(color=color_hex)

    # ---------- 核心方法 ----------
    def _get_current_color(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        return settings.value("theme_color", DEFAULT_THEME["color"])

    def _apply_theme(self, color=None, opacity=None, tint=None):
        if self._updating:
            return

        settings = QSettings("MyDesktopApp", "WeatherSettings")
        current_color = color if color is not None else settings.value("theme_color", DEFAULT_THEME["color"])
        current_opacity = opacity if opacity is not None else self.opacity_slider.value()
        current_tint = tint if tint is not None else self.tint_slider.value()

        settings.setValue("theme_color", current_color)
        settings.setValue("theme_opacity", current_opacity)
        settings.setValue("theme_tint_alpha", current_tint)
        settings.sync()

        self.theme_changed.emit()
        self._update_main_window()

    def _update_main_window(self):
        main_window = self.parent_dialog.parent() if self.parent_dialog else None
        if main_window and hasattr(main_window, 'update_theme_cache'):
            main_window.update_theme_cache()
        elif main_window and hasattr(main_window, 'update'):
            main_window.update()

    def _force_reload_images(self):
        main_window = None
        if self.parent_dialog:
            main_window = getattr(self.parent_dialog, '_main_window', None)
        if main_window is None and self.parent_dialog:
            main_window = self.parent_dialog.parent()
        if main_window and hasattr(main_window, 'reload_images'):
            main_window.reload_images()

    def _force_update_main_window(self):
        main_window = self.parent_dialog.parent() if self.parent_dialog else None
        if main_window and hasattr(main_window, 'update_theme_cache'):
            main_window.update_theme_cache(force=True)
            main_window.update()

    # ---------- 恢复默认 ----------
    def restore_default(self):
        self._updating = True
        try:
            self.theme_manager.switch_theme(QCoreApplication.translate("ThemeManager", "默认主题"))
            idx = self.theme_combo.findText(QCoreApplication.translate("ThemeManager", "默认主题"))
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)

            self.opacity_slider.setValue(DEFAULT_THEME["opacity"])
            self.opacity_label.setText(f"{DEFAULT_THEME['opacity']}%")

            self.tint_slider.setValue(80)
            self.tint_label.setText("31%")

            default_color = DEFAULT_THEME["color"]
            found = False
            for btn in self.color_buttons:
                if btn.property("color") == default_color:
                    btn.setChecked(True)
                    found = True
                else:
                    btn.setChecked(False)
            self.custom_btn.setChecked(not found)

            settings = QSettings("MyDesktopApp", "WeatherSettings")
            settings.setValue("theme_color", default_color)
            settings.setValue("theme_opacity", DEFAULT_THEME["opacity"])
            settings.setValue("theme_tint_alpha", 80)
            settings.sync()

            self._force_reload_images()
            self.theme_changed.emit()

        finally:
            self._updating = False

    # ---------- 加载设置 ----------
    def load_settings(self):
        self._updating = True
        try:
            settings = QSettings("MyDesktopApp", "WeatherSettings")

            current_theme = self.theme_manager.get_current_theme()
            themes = self.theme_manager.list_themes()
            self.theme_combo.clear()
            self.theme_combo.addItems(themes)
            idx = self.theme_combo.findText(current_theme)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)

            opacity = int(settings.value("theme_opacity", DEFAULT_THEME["opacity"]))
            self.opacity_slider.setValue(opacity)
            self.opacity_label.setText(f"{opacity}%")

            tint = int(settings.value("theme_tint_alpha", 80))
            self.tint_slider.setValue(tint)
            percent = int(tint / 255 * 100)
            self.tint_label.setText(f"{percent}%")

            color = settings.value("theme_color", DEFAULT_THEME["color"])
            found = False
            for btn in self.color_buttons:
                if btn.property("color") == color:
                    btn.setChecked(True)
                    found = True
                else:
                    btn.setChecked(False)
            self.custom_btn.setChecked(not found)

            self._update_delete_button_state()

        finally:
            self._updating = False