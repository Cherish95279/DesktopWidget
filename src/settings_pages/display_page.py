from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from ..constants import DEFAULT_LAYOUT


class DisplayPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent

        # 内容池定义（已移除 sunrise）
        self.content_pool = [
            ("ip", "IP"),
            ("weather", "天气"),
            ("netspeed", "网速"),
            ("cpu", "CPU"),
            ("gpu", "GPU"),
            ("resolution", "分辨率"),
            ("refresh_rate", "刷新率"),
            ("memory", "内存"),
            ("date", "公历"),
            ("lunar", "农历"),
            ("empty", "空"),
        ]
        self.all_values = [v for v, _ in self.content_pool]

        # 8个位置
        self.slot_defs = [
            {"key": "slot_1", "name": "左一"},
            {"key": "slot_2", "name": "左二"},
            {"key": "slot_3", "name": "左三"},
            {"key": "slot_4", "name": "左四"},
            {"key": "slot_5", "name": "右一"},
            {"key": "slot_6", "name": "右二"},
            {"key": "slot_7", "name": "右三"},
            {"key": "slot_8", "name": "右四"},
        ]
        self.slot_keys = [s["key"] for s in self.slot_defs]

        # 数据层
        self.default_layout = DEFAULT_LAYOUT.copy()
        self.layout_data = self.default_layout.copy()
        self.combos = []
        self._loading = False

        self.setup_ui()
        self.load_layout_settings()

    # ---------- UI 构建 ----------
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 20, 15, 15)
        main_layout.setSpacing(8)

        pairs = [(0, 4), (1, 5), (2, 6), (3, 7)]
        for left_idx, right_idx in pairs:
            row = QHBoxLayout()
            row.setSpacing(10)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(self._create_combo_container(self.slot_defs[left_idx]))
            row.addWidget(self._create_combo_container(self.slot_defs[right_idx]))
            row.addStretch()
            main_layout.addLayout(row)

        info_label = QLabel("修改下拉菜单立即生效，无需保存")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #888; font-size: 12px; margin: 10px 0;")
        main_layout.addWidget(info_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        restore_btn = QPushButton("恢复默认")
        restore_btn.setFixedSize(90, 28)
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
        label.setStyleSheet("font-size: 11px; color: #333;")
        label.setFixedWidth(30)
        layout.addWidget(label)

        combo = QComboBox()
        combo.setMinimumWidth(100)
        combo.setFixedHeight(24)
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
            combo.addItem("空", "empty")

            combo.blockSignals(False)

    def _apply_changes(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        values = list(self.layout_data.values())
        non_empty = [v for v in values if v != "empty"]
        if len(non_empty) != len(set(non_empty)):
            return
        for key, value in self.layout_data.items():
            settings.setValue(key, str(value))
        parent = self.parent()
        if parent and hasattr(parent, 'parent'):
            main_window = parent.parent()
            if main_window and hasattr(main_window, 'update'):
                main_window.update()

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