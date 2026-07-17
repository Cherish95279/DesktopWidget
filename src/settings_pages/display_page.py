from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from ..constants import DEFAULT_LAYOUT


# ===== 统一下拉框样式（与 general_page 保持一致） =====
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


class DisplayPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent

        # 内容池定义
        self.content_pool = [
            ("ip", self.tr("IP")),
            ("weather", self.tr("天气")),
            ("netspeed", self.tr("网速")),
            ("cpu", self.tr("CPU")),
            ("gpu", self.tr("GPU")),
            ("resolution", self.tr("分辨率")),
            ("refresh_rate", self.tr("刷新率")),
            ("memory", self.tr("内存")),
            ("date", self.tr("公历")),
            ("lunar", self.tr("农历")),
            ("empty", self.tr("空")),
        ]
        self.all_values = [v for v, _ in self.content_pool]

        # 8个位置
        self.slot_defs = [
            {"key": "slot_1", "name": self.tr("左一")},
            {"key": "slot_2", "name": self.tr("左二")},
            {"key": "slot_3", "name": self.tr("左三")},
            {"key": "slot_4", "name": self.tr("左四")},
            {"key": "slot_5", "name": self.tr("右一")},
            {"key": "slot_6", "name": self.tr("右二")},
            {"key": "slot_7", "name": self.tr("右三")},
            {"key": "slot_8", "name": self.tr("右四")},
        ]
        self.slot_keys = [s["key"] for s in self.slot_defs]

        # 数据层
        self.default_layout = DEFAULT_LAYOUT.copy()
        self.layout_data = self.default_layout.copy()
        self.combos = []
        self._loading = False
        self._last_has_weather = False

        self.setup_ui()
        self.load_layout_settings()

    # ---------- UI 构建 ----------
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 20, 15, 15)
        main_layout.setSpacing(12)

        pairs = [(0, 4), (1, 5), (2, 6), (3, 7)]
        for left_idx, right_idx in pairs:
            row = QHBoxLayout()
            row.setSpacing(10)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(self._create_combo_container(self.slot_defs[left_idx]))
            row.addWidget(self._create_combo_container(self.slot_defs[right_idx]))
            row.addStretch()
            main_layout.addLayout(row)

        # 提示文字
        info_label = QLabel(self.tr("修改下拉菜单立即生效，无需保存"))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #888; font-size: 12px; margin: 10px 0;")
        main_layout.addWidget(info_label)

        # 按钮行（恢复默认）
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        restore_btn = QPushButton(self.tr("恢复默认"))
        restore_btn.setFixedSize(90, 28)
        restore_btn.setStyleSheet("""
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
        restore_btn.clicked.connect(self.restore_default)
        btn_layout.addWidget(restore_btn)
        main_layout.addLayout(btn_layout)
        main_layout.addStretch()

    def _create_combo_container(self, slot):
        container = QWidget()
        container.setFixedWidth(160)

        layout = QHBoxLayout(container)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(slot["name"])
        label.setStyleSheet("font-size: 12px; color: #333;")
        label.setFixedWidth(30)
        layout.addWidget(label)

        # ===== 下拉框（统一风格） =====
        combo = QComboBox()
        combo.setMinimumWidth(100)
        combo.setFixedHeight(28)
        combo.setStyleSheet(COMBO_STYLE)
        combo.setProperty("slot_key", slot["key"])
        combo.currentIndexChanged.connect(self._on_combo_changed)
        self.combos.append(combo)
        layout.addWidget(combo)

        return container

    # ---------- 核心数据同步 ----------
    def _apply_layout_to_ui(self):
        for combo in self.combos:
            combo.blockSignals(True)

        for combo in self.combos:
            key = combo.property("slot_key")
            value = str(self.layout_data.get(key, "empty"))
            idx = combo.findData(value)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                empty_idx = combo.findData("empty")
                combo.setCurrentIndex(empty_idx if empty_idx >= 0 else 0)

        for combo in self.combos:
            combo.blockSignals(False)

    def _sync_ui_to_data(self):
        for combo in self.combos:
            key = combo.property("slot_key")
            val = combo.currentData()
            self.layout_data[key] = str(val) if val is not None else "empty"

    def _rebuild_combo_options(self):
        all_non_empty = set()
        for key in self.slot_keys:
            val = str(self.layout_data.get(key, "empty"))
            if val != "empty":
                all_non_empty.add(val)

        for combo in self.combos:
            key = combo.property("slot_key")
            current_val = str(self.layout_data.get(key, "empty"))

            combo.blockSignals(True)

            available = []
            for val, text in self.content_pool:
                if val == "empty":
                    continue
                if val not in all_non_empty or val == current_val:
                    available.append((val, text))

            combo.clear()
            for val, text in available:
                combo.addItem(text, val)
            combo.addItem(self.tr(self.tr(self.tr(self.tr("空")))), "empty")

            combo.blockSignals(False)

    def _apply_changes(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        values = list(self.layout_data.values())
        non_empty = [v for v in values if v != "empty"]
        if len(non_empty) != len(set(non_empty)):
            return

        new_has_weather = "weather" in values
        old_has_weather = getattr(self, "_last_has_weather", False)

        for key, value in self.layout_data.items():
            settings.setValue(key, str(value))

        parent = self.parent()
        if parent and hasattr(parent, 'parent'):
            main_window = parent.parent()
            if main_window and hasattr(main_window, 'update'):
                main_window.update()

            if new_has_weather != old_has_weather:
                if main_window and hasattr(main_window, 'start_weather_thread'):
                    main_window.start_weather_thread()

        self._last_has_weather = new_has_weather

    # ---------- 信号处理 ----------
    def _on_combo_changed(self):
        if self._loading:
            return

        changed_combo = self.sender()
        if changed_combo is None:
            return

        key = changed_combo.property("slot_key")
        new_value = changed_combo.currentData()
        new_value = str(new_value) if new_value is not None else "empty"

        self.layout_data[key] = new_value

        if new_value != "empty":
            all_non_empty = [str(v) for v in self.layout_data.values() if v != "empty"]
            if all_non_empty.count(new_value) > 1:
                self._loading = True
                self.layout_data[key] = "empty"
                empty_idx = changed_combo.findData("empty")
                changed_combo.blockSignals(True)
                changed_combo.setCurrentIndex(empty_idx if empty_idx >= 0 else 0)
                changed_combo.blockSignals(False)
                self._loading = False

        self._rebuild_combo_options()
        self._apply_layout_to_ui()
        self._sync_ui_to_data()
        self._apply_changes()

    # ---------- 加载 / 恢复 ----------
    def load_layout_settings(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        self._loading = True

        try:
            for key in self.slot_keys:
                default_val = str(self.default_layout.get(key, "empty"))
                val = settings.value(key, default_val)
                if val is None:
                    val = default_val
                else:
                    val = str(val)
                if val not in self.all_values:
                    val = "empty"
                self.layout_data[key] = val

            seen = set()
            for key in self.slot_keys:
                val = self.layout_data.get(key, "empty")
                if val != "empty":
                    if val in seen:
                        self.layout_data[key] = "empty"
                    else:
                        seen.add(val)

            self._rebuild_combo_options()
            self._apply_layout_to_ui()
            self._sync_ui_to_data()

            for key, value in self.layout_data.items():
                settings.setValue(key, str(value))

            self._last_has_weather = "weather" in self.layout_data.values()

        finally:
            self._loading = False

    def restore_default(self):
        self._loading = True
        try:
            self.layout_data = self.default_layout.copy()
            for key in self.layout_data:
                self.layout_data[key] = str(self.layout_data[key])
            self._rebuild_combo_options()
            self._apply_layout_to_ui()
            self._sync_ui_to_data()
            self._apply_changes()
        finally:
            self._loading = False