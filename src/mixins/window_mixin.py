from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent


class WindowMixin:
    """窗口行为混入：拖动、移动、位置"""

    def move_to_top_right(self):
        """将窗口移动到屏幕右上角"""
        screen = self.screen() if hasattr(self, 'screen') else None
        if not screen:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.right() - self.width() - 100
            y = geometry.top() + 150
            self.move(x, y)

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e: QMouseEvent):
        if hasattr(self, 'drag_pos') and self.drag_pos:
            self.move(self.pos() + e.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e: QMouseEvent):
        self.drag_pos = None