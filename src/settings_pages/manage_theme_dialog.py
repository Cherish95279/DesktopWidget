# -*- coding: utf-8 -*-
"""
主题管理对话框

统一管理主题的导入与删除：
- 上半部分：导入主题（选择 zip → 校验 → 导入）
- 下半部分：已安装主题列表（多选删除自定义主题）
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QFrame, QListWidget,
    QListWidgetItem, QMessageBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QUrl, QSettings, QCoreApplication
from PyQt6.QtGui import QDesktopServices


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

DANGER_BTN_STYLE = """
    QPushButton {
        font-size: 12px;
        border: 1px solid #ff7875;
        border-radius: 4px;
        background: #fff1f0;
        color: #d4380d;
    }
    QPushButton:hover {
        background: #ffccc7;
        border: 1px solid #ff4d4f;
        color: #cf1322;
    }
    QPushButton:disabled {
        color: #aaa;
        background: #f0f0f0;
        border: 1px solid #ddd;
    }
"""


class ManageThemeDialog(QDialog):
    """管理主题对话框（导入 + 删除）"""

    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self._analysis = None
        self.setWindowTitle(self.tr("管理主题"))
        self.setFixedWidth(480)
        self._setup_ui()
        self._load_themes()

    # ================================================================
    # UI 构建
    # ================================================================
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        # ---- 上半部分：导入主题 ----
        import_title = QLabel("📥 " + self.tr("导入主题"))
        import_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(import_title)

        pick_row = QHBoxLayout()
        pick_row.setSpacing(8)
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setFixedHeight(28)
        self.path_edit.setPlaceholderText(self.tr("点击右侧按钮选择 .zip 文件"))
        pick_row.addWidget(self.path_edit)
        self.browse_btn = QPushButton(self.tr("浏览..."))
        self.browse_btn.setFixedSize(80, 28)
        self.browse_btn.setStyleSheet(BTN_STYLE)
        self.browse_btn.clicked.connect(self._on_browse)
        pick_row.addWidget(self.browse_btn)
        layout.addLayout(pick_row)

        self.name_label = QLabel("")
        self.name_label.setStyleSheet("font-size: 12px; color: #555;")
        self.name_label.setVisible(False)
        layout.addWidget(self.name_label)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.result_label)

        # 导入按钮行
        import_btn_row = QHBoxLayout()
        import_btn_row.addStretch()
 
        self.download_btn = QPushButton(self.tr("更多主题下载"))
        self.download_btn.setFixedSize(110, 28)
        self.download_btn.setStyleSheet(BTN_STYLE)
        self.download_btn.clicked.connect(self._on_open_download)
        import_btn_row.addWidget(self.download_btn)
 
        self.guide_btn = QPushButton(self.tr("主题制作指南"))
        self.guide_btn.setFixedSize(96, 28)
        self.guide_btn.setStyleSheet(BTN_STYLE)
        self.guide_btn.clicked.connect(self._on_open_guide)
        import_btn_row.addWidget(self.guide_btn)

        self.import_btn = QPushButton(self.tr("导入"))
        self.import_btn.setFixedSize(72, 28)
        self.import_btn.setStyleSheet(BTN_STYLE)
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._on_import)
        import_btn_row.addWidget(self.import_btn)
        layout.addLayout(import_btn_row)

        # ---- 分隔线 ----
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ddd;")
        layout.addWidget(sep)

        # ---- 下半部分：已安装主题列表 ----
        list_title = QLabel("🗑️ " + self.tr("已安装主题"))
        list_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(list_title)

        self.theme_list = QListWidget()
        self.theme_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.theme_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: #fafafa;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 5px 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:disabled {
                color: #bbb;
            }
        """)
        self.theme_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.theme_list)

        # 状态提示
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; color: #888;")
        layout.addWidget(self.status_label)

        # ---- 底部按钮 ----
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.cancel_btn = QPushButton(self.tr("关闭"))
        self.cancel_btn.setFixedSize(72, 28)
        self.cancel_btn.setStyleSheet(BTN_STYLE)
        self.cancel_btn.clicked.connect(self._on_close)
        btn_row.addWidget(self.cancel_btn)

        self.delete_btn = QPushButton(self.tr("删除所选"))
        self.delete_btn.setFixedSize(100, 28)
        self.delete_btn.setStyleSheet(DANGER_BTN_STYLE)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self.delete_btn)

        layout.addLayout(btn_row)

    # ================================================================
    # 打开主题下载页面
    # ================================================================
    def _on_open_download(self):
        """打开官方主题仓库的 Releases 页面"""
        url = QUrl("https://github.com/Cherish95279/DesktopWidget-Themes/releases")
        QDesktopServices.openUrl(url)

    # ================================================================
    # 打开主题制作指南
    # ================================================================
    def _on_open_guide(self):
        """根据当前界面语言打开对应的主题制作指南"""
        lang = QSettings("MyDesktopApp", "WeatherSettings").value("language", "")
        if lang in ("zh_CN", "zh_TW"):
            url = QUrl("https://github.com/Cherish95279/DesktopWidget/blob/main/docs/THEME_DEV_GUIDE.md")
        else:
            url = QUrl("https://github.com/Cherish95279/DesktopWidget/blob/main/docs/THEME_DEV_GUIDE_EN.md")
        QDesktopServices.openUrl(url)

    # ================================================================
    # 导入逻辑
    # ================================================================
    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("选择主题压缩包"), "",
            self.tr("主题压缩包 (*.zip)"))
        if not path:
            return
        self.path_edit.setText(path)
        self._validate(path)

    def _validate(self, zip_path):
        self._cleanup_temp()
        self._analysis = self.theme_manager.analyze_zip(zip_path)
        a = self._analysis
        if a.get("error"):
            self.name_label.setVisible(False)
            self.result_label.setText("❌ " + a["error"])
            self.result_label.setStyleSheet("font-size: 12px; color: #d4380d;")
            self.import_btn.setEnabled(False)
            return
        name = a.get("display_name") or ""
        self.name_label.setText(self.tr("主题名称") + ":  " + name)
        self.name_label.setVisible(True)
        if not a.get("valid"):
            missing = ", ".join(a.get("missing_required", []))
            self.result_label.setText("❌ " + self.tr("缺少") + " " + missing)
            self.result_label.setStyleSheet("font-size: 12px; color: #d4380d;")
            self.import_btn.setEnabled(False)
        else:
            opt = a.get("missing_optional", [])
            if opt:
                self.result_label.setText(
                    "✅ " + self.tr("校验通过") + "，" +
                    self.tr("缺失可选素材") + "：" + ", ".join(opt))
            else:
                self.result_label.setText("✅ " + self.tr("校验通过"))
            self.result_label.setStyleSheet("font-size: 12px; color: #389e0d;")
            self.import_btn.setEnabled(True)

    def _on_import(self):
        if not self._analysis or not self._analysis.get("valid"):
            return
        success, msg = self.theme_manager.commit_import(self._analysis)
        if success:
            self._cleanup_temp()
            self._analysis = None
            self.path_edit.clear()
            self.name_label.setVisible(False)
            self.result_label.setText("")
            self.import_btn.setEnabled(False)
            # 导入成功后刷新列表，不关闭对话框
            self._load_themes()
        else:
            self.result_label.setText("❌ " + msg)
            self.result_label.setStyleSheet("font-size: 12px; color: #d4380d;")

    def _cleanup_temp(self):
        if self._analysis:
            self.theme_manager.cleanup_temp(self._analysis)

    # ================================================================
    # 列表逻辑（删除）
    # ================================================================
    def _load_themes(self):
        """加载所有主题到列表"""
        self.theme_list.clear()
        themes = self.theme_manager.list_themes()
        for name in themes:
            is_builtin = self.theme_manager.is_builtin(name)
            if is_builtin:
                item = QListWidgetItem("🔒  " + name + "  (" + self.tr("内置") + ")")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            else:
                item = QListWidgetItem("⬜  " + name)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setData(Qt.ItemDataRole.UserRole + 1, False)
            self.theme_list.addItem(item)
        self._update_status()

    def _get_selected_themes(self):
        """获取所有选中的自定义主题名"""
        selected = []
        for i in range(self.theme_list.count()):
            item = self.theme_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole + 1):
                name = item.data(Qt.ItemDataRole.UserRole)
                selected.append(name)
        return selected

    def _on_item_clicked(self, item):
        """点击自定义主题时切换选中状态"""
        if not (item.flags() & Qt.ItemFlag.ItemIsEnabled):
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if name is None:
            return
        selected = item.data(Qt.ItemDataRole.UserRole + 1)
        selected = not selected
        item.setData(Qt.ItemDataRole.UserRole + 1, selected)
        if selected:
            item.setText("✔️  " + name)
        else:
            item.setText("⬜  " + name)
        self._update_status()

    def _update_status(self):
        """更新状态提示和删除按钮文案"""
        selected = self._get_selected_themes()
        count = len(selected)
        if count == 0:
            self.status_label.setText(self.tr("勾选要删除的自定义主题，内置主题不可删除"))
            self.delete_btn.setText(self.tr("删除所选"))
            self.delete_btn.setEnabled(False)
        else:
            self.status_label.setText(self.tr("已选择 {} 个主题").format(count))
            self.delete_btn.setText(self.tr("删除所选({})").format(count))
            self.delete_btn.setEnabled(True)

    def _on_delete(self):
        """删除选中的主题"""
        selected = self._get_selected_themes()
        if not selected:
            return

        names = "\n".join("  • " + name for name in selected)
        confirm = QMessageBox.question(
            self, self.tr("确认删除"),
            self.tr("确定删除以下主题吗？此操作不可撤销：\n\n{}").format(names),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        failed = []
        for name in selected:
            success, _msg = self.theme_manager.delete_theme(name)
            if not success:
                failed.append(name)

        if failed:
            QMessageBox.warning(
                self, self.tr("部分删除失败"),
                self.tr("以下主题删除失败：\n{}").format("\n".join(failed))
            )

        # 删除后刷新列表，不关闭对话框
        self._load_themes()

    # ================================================================
    # 关闭
    # ================================================================
    def _on_close(self):
        self._cleanup_temp()
        self.accept()

    def closeEvent(self, event):
        self._cleanup_temp()
        super().closeEvent(event)
