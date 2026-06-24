from PyQt6.QtWidgets import *
from PyQt6.QtCore import *


class ThemePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("主题功能开发中，敬请期待...")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(label)