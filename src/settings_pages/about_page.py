from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from ..constants import VERSION


class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(f"珍爱桌面小工具 {VERSION}")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        author = QLabel("作者：Cherish95279")
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(author)

        thanks = QLabel("致谢：fkp123")  # 已修改
        thanks.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thanks)

        github = QLabel('<a href="https://github.com/Cherish95279/DesktopWidget">GitHub：https://github.com/Cherish95279/DesktopWidget</a>')
        github.setOpenExternalLinks(True)
        github.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(github)

        layout.addStretch()