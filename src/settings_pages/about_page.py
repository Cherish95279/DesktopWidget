from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QDesktopServices
from ..constants import VERSION


class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题
        title = QLabel(f"珍爱桌面小工具 {VERSION}")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 作者
        author = QLabel("作者：Cherish95279")
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(author)

        # 致谢（fkp123 可点击）
        thanks = QLabel(
            '致谢：<a href="https://github.com/fkp123" style="color: #0366d6; text-decoration: none;">fkp123</a>'
        )
        thanks.setOpenExternalLinks(True)
        thanks.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thanks.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(thanks)

        # GitHub 链接
        github = QLabel(
            '<a href="https://github.com/Cherish95279/DesktopWidget">GitHub：https://github.com/Cherish95279/DesktopWidget</a>'
        )
        github.setOpenExternalLinks(True)
        github.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(github)

        # 反馈按钮
        feedback_btn = QPushButton("💬 前往讨论区")
        feedback_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 14px;
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
        feedback_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        feedback_btn.clicked.connect(self.open_feedback)
        layout.addWidget(feedback_btn)

        layout.addStretch()

    def open_feedback(self):
        """打开 GitHub Discussions 反馈页面"""
        url = "https://github.com/Cherish95279/DesktopWidget/discussions/new/choose"
        QDesktopServices.openUrl(QUrl(url))