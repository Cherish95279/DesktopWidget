from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QColor
from ..constants import DEFAULT_THEME, THEME_PRESETS
from ..theme_manager import get_theme_manager


class ThemePage(QWidget):
    """主题设置页面（新布局）"""

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
        main_layout.setSpacing(8)

        # ===== 前两行使用 QGridLayout 实现精确对齐 =====
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)

        # 第一行：标签
        self.theme_label = QLabel("主题切换")
        self.theme_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        grid.addWidget(self.theme_label, 0, 0, Qt.AlignmentFlag.AlignLeft)

        self.color_label = QLabel("背景颜色")
        self.color_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        grid.addWidget(self.color_label, 0, 1, Qt.AlignmentFlag.AlignLeft)

        # 第二行：控件
        self.theme_combo = QComboBox()
        self.theme_combo.setFixedWidth(140)
        self.theme_combo.setFixedHeight(28)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        grid.addWidget(self.theme_combo, 1, 0, Qt.AlignmentFlag.AlignLeft)

        color_widget = QWidget()
        color_layout = QHBoxLayout(color_widget)
        color_layout.setSpacing(6)
        color_layout.setContentsMargins(0, 0, 0, 0)

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
        self.custom_btn.setToolTip("自定义颜色")
        self.custom_btn.clicked.connect(self._on_custom_color)
        color_layout.addWidget(self.custom_btn)

        grid.addWidget(color_widget, 1, 1, Qt.AlignmentFlag.AlignLeft)

        main_layout.addLayout(grid)

        # ===== 间距：下拉框和不透明度之间拉开两行 =====
        main_layout.addSpacing(24)  # 改为两行高度

        # ===== 第三行：不透明度标签 =====
        opacity_label = QLabel("不透明度")
        opacity_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        main_layout.addWidget(opacity_label)

        # ===== 第四行：不透明度滑块 =====
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

        main_layout.addLayout(opacity_row)

        # ===== 间距：不透明度滑块和着色强度之间拉开两行 =====
        main_layout.addSpacing(24)

        # ===== 第五行：着色强度 =====
        tint_row = QHBoxLayout()
        tint_row.setSpacing(10)

        tint_label = QLabel("着色强度")
        tint_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        tint_row.addWidget(tint_label)

        self.tint_spin = QSpinBox()
        self.tint_spin.setRange(0, 255)
        self.tint_spin.setValue(80)
        self.tint_spin.setSingleStep(1)
        self.tint_spin.setSuffix("")
        self.tint_spin.setToolTip("值越小背景越透，原图越清晰；值越大颜色越浓")
        self.tint_spin.valueChanged.connect(self._on_tint_changed)
        tint_row.addWidget(self.tint_spin)

        tint_row.addStretch()
        main_layout.addLayout(tint_row)

        # ===== 底部弹性空间 + 恢复默认按钮 =====
        main_layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.restore_btn = QPushButton("恢复默认")
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

        main_layout.addLayout(btn_row)

    # ---------- 信号处理 ----------
    def _on_theme_changed(self, theme_name):
        if self._updating:
            return
        if theme_name:
            print(f"🎨 用户选择主题: {theme_name}")
            self.theme_manager.switch_theme(theme_name)
            self.theme_changed.emit()
            self._update_main_window()

    def _on_opacity_changed(self, value):
        self.opacity_label.setText(f"{value}%")
        self._apply_theme()

    def _on_tint_changed(self, value):
        self._apply_theme()

    def _on_preset_clicked(self, btn):
        color = btn.property("color")
        for b in self.color_buttons:
            b.setChecked(b is btn)
        self.custom_btn.setChecked(False)
        self._apply_theme(color=color)

    def _on_custom_color(self):
        current_color = self._get_current_color()
        color = QColorDialog.getColor(QColor(current_color), self, "选择背景颜色")
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
        current_tint = tint if tint is not None else self.tint_spin.value()

        settings.setValue("theme_color", current_color)
        settings.setValue("theme_opacity", current_opacity)
        settings.setValue("theme_tint_alpha", current_tint)
        settings.sync()

        self.theme_changed.emit()
        self._update_main_window()

    def _get_main_window(self):
        parent = self.parent()
        while parent:
            if parent.__class__.__name__ == "MainWindow":
                return parent
            parent = parent.parent()
        return None

    def _update_main_window(self):
        main_window = self._get_main_window()
        if main_window:
            if hasattr(main_window, 'reload_images'):
                main_window.reload_images()
            elif hasattr(main_window, 'update_theme_cache'):
                main_window.update_theme_cache()
            elif hasattr(main_window, 'update'):
                main_window.update()

    def _force_update_main_window(self):
        main_window = self._get_main_window()
        if main_window:
            if hasattr(main_window, 'reload_images'):
                main_window.reload_images()
            elif hasattr(main_window, 'update_theme_cache'):
                main_window.update_theme_cache(force=True)
            elif hasattr(main_window, 'update'):
                main_window.update()

    # ---------- 恢复默认 ----------
    def restore_default(self):
        self._updating = True
        try:
            self.theme_manager.switch_theme("默认主题")
            idx = self.theme_combo.findText("默认主题")
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)

            self.opacity_slider.setValue(DEFAULT_THEME["opacity"])
            self.opacity_label.setText(f"{DEFAULT_THEME['opacity']}%")
            self.tint_spin.setValue(80)

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

            self._force_update_main_window()
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
            self.tint_spin.setValue(tint)

            color = settings.value("theme_color", DEFAULT_THEME["color"])
            found = False
            for btn in self.color_buttons:
                if btn.property("color") == color:
                    btn.setChecked(True)
                    found = True
                else:
                    btn.setChecked(False)
            self.custom_btn.setChecked(not found)

        finally:
            self._updating = False