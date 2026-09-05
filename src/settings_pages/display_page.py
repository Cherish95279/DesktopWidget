from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from ..constants import DEFAULT_LAYOUT
from ..plugin_manager import get_plugin_manager


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
            ("memory", self.tr("内存")),
            ("date", self.tr("公历")),
            ("lunar", self.tr("农历")),
            ("term", self.tr("节气")),
            ("uptime", self.tr("运行时间")),
        ]
        # 动态检测物理硬盘盘符
        import psutil
        self._detected_disk_keys = set()
        for part in psutil.disk_partitions():
            if (not part.opts.startswith("cdrom")
                and not part.device.startswith("\\\\")
                and part.fstype not in ("", "udf", "iso9660")):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    if usage.total > 0:
                        letter = part.mountpoint.split(":")[0].rstrip("\\").upper()
                        self.content_pool.append((f"disk_{letter}", QCoreApplication.translate("Constants", f"{letter}盘")))
                        self._detected_disk_keys.add(f"disk_{letter}")
                except (PermissionError, OSError):
                    pass
        self.content_pool.append(("disk_total", self.tr("磁盘总计")))
        self.content_pool.append(("empty", self.tr("空")))
        self.all_values = [v for v, _ in self.content_pool]

        # 信息条显示的筛选内容池（紧凑型数据，无empty）
        self.taskbar_pool = [
            ("netspeed", self.tr("网速")),
            ("weather", self.tr("天气")),
            ("cpu", self.tr("CPU")),
            ("gpu", self.tr("GPU")),
            ("memory", self.tr("内存")),
            ("uptime", self.tr("运行时间")),
        ]
        # 已检测到的盘符（从content_pool继承）
        for dk in sorted(self._detected_disk_keys):
            letter = dk.replace("disk_", "")
            label = QCoreApplication.translate("Constants", f"{letter}盘")
            self.taskbar_pool.append((dk, label))
        self.taskbar_pool.append(("disk_total", self.tr("磁盘总计")))

        # 加载插件条目
        self._plugin_keys = set()
        self._add_plugin_entries()

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

        # ===== 分隔线 =====
        separator = QLabel("")
        separator.setFixedHeight(1)
        separator.setStyleSheet("background: #e0e0e0; margin: 5px 0;")
        main_layout.addWidget(separator)

        # ===== 信息条 + 悬停开关（和上面8个下拉框对齐） =====
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        bottom_row.setContentsMargins(0, 0, 0, 0)

        # 信息条容器（和槽位容器一样 160px 宽）
        taskbar_container = QWidget()
        taskbar_container.setFixedWidth(160)
        taskbar_layout = QHBoxLayout(taskbar_container)
        taskbar_layout.setSpacing(4)
        taskbar_layout.setContentsMargins(0, 0, 0, 0)
        taskbar_label = QLabel(self.tr("任务栏"))
        taskbar_label.setStyleSheet("font-size: 12px; color: #333;")
        taskbar_label.setFixedWidth(48)
        taskbar_layout.addWidget(taskbar_label)
        self.taskbar_combo = QComboBox()
        self.taskbar_combo.setMinimumWidth(82)
        self.taskbar_combo.setFixedHeight(28)
        self.taskbar_combo.setStyleSheet(COMBO_STYLE)
        self.taskbar_combo.addItem(self.tr("不显示"), "none")
        for val, text in self.taskbar_pool:
            self.taskbar_combo.addItem(text, val)
        self.taskbar_combo.currentIndexChanged.connect(self._on_taskbar_combo_changed)
        taskbar_layout.addWidget(self.taskbar_combo)
        bottom_row.addWidget(taskbar_container)

        # 悬停开关容器（和槽位容器一样 160px 宽）
        hover_container = QWidget()
        hover_container.setFixedWidth(160)
        hover_layout = QHBoxLayout(hover_container)
        hover_layout.setSpacing(4)
        hover_layout.setContentsMargins(0, 0, 0, 0)
        hover_label = QLabel(self.tr("悬停开关"))
        hover_label.setStyleSheet("font-size: 12px; color: #333;")
        hover_label.setFixedWidth(48)
        hover_layout.addWidget(hover_label)
        self.hover_combo = QComboBox()
        self.hover_combo.setMinimumWidth(82)
        self.hover_combo.setFixedHeight(28)
        self.hover_combo.setStyleSheet(COMBO_STYLE)
        self.hover_combo.addItem(self.tr("开"), "on")
        self.hover_combo.addItem(self.tr("关"), "off")
        self.hover_combo.currentIndexChanged.connect(self._on_hover_combo_changed)
        hover_layout.addWidget(self.hover_combo)
        bottom_row.addWidget(hover_container)

        bottom_row.addStretch()
        main_layout.addLayout(bottom_row)

        # 提示文字（移到底部）
        info_label = QLabel(self.tr("修改下拉菜单立即生效，无需保存"))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #888; font-size: 12px; margin: 10px 0;")
        main_layout.addWidget(info_label)

        # 按钮行（管理插件 + 恢复默认）
        btn_layout = QHBoxLayout()
        self.plugin_btn = QPushButton(self.tr("管理插件"))
        self.plugin_btn.setFixedSize(90, 28)
        self.plugin_btn.setStyleSheet("""
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
        self.plugin_btn.clicked.connect(self._on_manage_plugins)
        btn_layout.addWidget(self.plugin_btn)
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

        from PyQt6.QtWidgets import QApplication
        main_window = None
        dlg = self.parent()
        if dlg and hasattr(dlg, '_main_window'):
            main_window = dlg._main_window
        if not main_window:
            for w in QApplication.topLevelWidgets():
                if w.__class__.__name__ == 'MainWindow':
                    main_window = w
                    break
        if main_window:
            if hasattr(main_window, '_refresh_draw_cache'):
                main_window._refresh_draw_cache()
            if hasattr(main_window, 'update'):
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

            # 加载信息条显示设置
            self._load_taskbar_setting()

        finally:
            self._loading = False

    # ---------- 信息条显示 ----------
    def _load_taskbar_setting(self):
        """加载信息条显示设置和悬停开关设置"""
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        val = settings.value("taskbar_display", "netspeed")
        idx = self.taskbar_combo.findData(val)
        if idx >= 0:
            self.taskbar_combo.blockSignals(True)
            self.taskbar_combo.setCurrentIndex(idx)
            self.taskbar_combo.blockSignals(False)
        # 加载悬停开关
        hover_enabled = settings.value("hover_enabled", True, type=bool)
        hover_idx = self.hover_combo.findData("on" if hover_enabled else "off")
        if hover_idx >= 0:
            self.hover_combo.blockSignals(True)
            self.hover_combo.setCurrentIndex(hover_idx)
            self.hover_combo.blockSignals(False)

    def _on_taskbar_combo_changed(self):
        """信息条显示下拉框变更 → 立即保存"""
        if self._loading:
            return
        val = self.taskbar_combo.currentData()
        if val is None:
            return
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("taskbar_display", val)
        settings.sync()
        # 如果选了"不显示"，隐藏信息条
        from PyQt6.QtWidgets import QApplication
        main_window = None
        dlg = self.parent()
        if dlg and hasattr(dlg, '_main_window'):
            main_window = dlg._main_window
        if not main_window:
            for w in QApplication.topLevelWidgets():
                if w.__class__.__name__ == 'MainWindow':
                    main_window = w
                    break
        if main_window and hasattr(main_window, 'taskbar_widget'):
            if val == "none":
                main_window.taskbar_widget.hide()
                settings.setValue("taskbar_visible", False)
            else:
                main_window.taskbar_widget.show()
                settings.setValue("taskbar_visible", True)
            settings.sync()

    def _on_hover_combo_changed(self):
        """悬停开关变更 → 立即保存"""
        if self._loading:
            return
        val = self.hover_combo.currentData()
        if val is None:
            return
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("hover_enabled", val == "on")
        settings.sync()

    def _add_plugin_entries(self):
        """将插件条目添加到 content_pool 和 taskbar_pool"""
        # 先移除旧的插件条目
        self.content_pool = [
            (v, t) for v, t in self.content_pool if v not in self._plugin_keys
        ]
        self.taskbar_pool = [
            (v, t) for v, t in self.taskbar_pool if v not in self._plugin_keys
        ]
        self._plugin_keys.clear()

        # 从插件管理器获取条目
        try:
            pm = get_plugin_manager()
            # content_pool: 所有插件
            for key, name in pm.get_entries():
                # 插入到 "empty" 之前
                empty_idx = next(
                    (i for i, (v, _) in enumerate(self.content_pool) if v == "empty"),
                    len(self.content_pool))
                self.content_pool.insert(empty_idx, (key, name))
                self._plugin_keys.add(key)

            # taskbar_pool: 仅支持任务栏的插件
            for key, name in pm.get_taskbar_entries():
                self.taskbar_pool.append((key, name))
                self._plugin_keys.add(key)
        except Exception:
            pass

        # 更新 all_values
        self.all_values = [v for v, _ in self.content_pool]

    def _on_manage_plugins(self):
        """打开管理插件对话框"""
        from .manage_plugin_dialog import ManagePluginDialog
        try:
            pm = get_plugin_manager()
            dialog = ManagePluginDialog(pm, self)
            dialog.exec()
            # 对话框关闭后刷新插件条目和下拉框
            self._add_plugin_entries()
            self._rebuild_combo_options()
            self._apply_layout_to_ui()
            self._load_taskbar_setting()
            self._apply_changes()
        except Exception as e:
            print(f"打开管理插件失败: {e}")

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