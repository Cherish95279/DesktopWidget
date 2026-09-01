# -*- coding: utf-8 -*-
"""
主题导入对话框
选择压缩包 -> 校验素材 -> 确认导入
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QFrame,
)


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


class ImportThemeDialog(QDialog):
    """导入主题对话框"""

    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self._analysis = None
        self.imported_theme_name = None
        self.setWindowTitle(self.tr("导入主题"))
        self.setFixedWidth(420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # 选择压缩包
        pick_label = QLabel(self.tr("选择压缩包"))
        pick_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(pick_label)

        pick_row = QHBoxLayout()
        pick_row.setSpacing(8)
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setFixedHeight(28)
        self.path_edit.setMaximumWidth(240)
        self.path_edit.setPlaceholderText(self.tr("点击右侧按钮选择 .zip 文件"))
        pick_row.addWidget(self.path_edit)
        self.browse_btn = QPushButton(self.tr("浏览..."))
        self.browse_btn.setFixedSize(90, 28)
        self.browse_btn.setStyleSheet(BTN_STYLE)
        self.browse_btn.clicked.connect(self._on_browse)
        pick_row.addWidget(self.browse_btn)
        layout.addLayout(pick_row)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ddd;")
        layout.addWidget(sep)

        # 校验结果
        result_title = QLabel(self.tr("校验结果"))
        result_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(result_title)

        self.name_label = QLabel("")
        self.name_label.setStyleSheet("font-size: 13px; color: #555;")
        self.name_label.setVisible(False)
        layout.addWidget(self.name_label)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.result_label)

        layout.addStretch()

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.cancel_btn = QPushButton(self.tr("取消"))
        self.cancel_btn.setFixedSize(72, 28)
        self.cancel_btn.setStyleSheet(BTN_STYLE)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)
        self.import_btn = QPushButton(self.tr("导入"))
        self.import_btn.setFixedSize(72, 28)
        self.import_btn.setStyleSheet(BTN_STYLE)
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._on_import)
        btn_row.addWidget(self.import_btn)
        layout.addLayout(btn_row)

    # ---------- 选择压缩包 ----------
    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("选择主题压缩包"), "",
            self.tr("主题压缩包 (*.zip)"))
        if not path:
            return
        self.path_edit.setText(path)
        self._validate(path)

    # ---------- 校验 ----------
    def _validate(self, zip_path):
        self._cleanup_temp()
        self._analysis = self.theme_manager.analyze_zip(zip_path)
        a = self._analysis
        if a.get("error"):
            self.name_label.setVisible(False)
            self.result_label.setText("❌ " + a["error"])
            self.result_label.setStyleSheet("font-size: 13px; color: #d4380d;")
            self.import_btn.setEnabled(False)
            return
        name = a.get("display_name") or ""
        self.name_label.setText(self.tr("主题名称") + ":  " + name)
        self.name_label.setVisible(True)
        if not a.get("valid"):
            missing = ", ".join(a.get("missing_required", []))
            self.result_label.setText("❌ " + self.tr("缺少") + " " + missing)
            self.result_label.setStyleSheet("font-size: 13px; color: #d4380d;")
            self.import_btn.setEnabled(False)
        else:
            opt = a.get("missing_optional", [])
            if opt:
                self.result_label.setText(
                    "✅ " + self.tr("校验通过") + "，" +
                    self.tr("缺失可选素材") + "：" + ", ".join(opt))
            else:
                self.result_label.setText("✅ " + self.tr("校验通过"))
            self.result_label.setStyleSheet("font-size: 13px; color: #389e0d;")
            self.import_btn.setEnabled(True)

    # ---------- 导入 ----------
    def _on_import(self):
        if not self._analysis or not self._analysis.get("valid"):
            return
        success, msg = self.theme_manager.commit_import(self._analysis)
        if success:
            self.imported_theme_name = msg
            self._cleanup_temp()
            self.accept()
        else:
            self.result_label.setText("❌ " + msg)
            self.result_label.setStyleSheet("font-size: 13px; color: #d4380d;")

    # ---------- 清理临时目录 ----------
    def _cleanup_temp(self):
        if self._analysis:
            self.theme_manager.cleanup_temp(self._analysis)

    def closeEvent(self, event):
        self._cleanup_temp()
        super().closeEvent(event)
