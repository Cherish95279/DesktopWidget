from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QMouseEvent


class NoticeBubble(QLabel):
    """右下角的公告气泡组件（💬）"""

    def __init__(self, parent=None):
        super().__init__("💬", parent)
        self.setStyleSheet("""
            QLabel {
                background: transparent;
                font-size: 20px;
                padding: 4px 6px;
                border-radius: 4px;
            }
            QLabel:hover {
                background: rgba(255,255,255,60);
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adjustSize()

        self._flash_timer = None
        self._flash_count = 0
        self._is_visible = True
        self._on_click_callback = None

    def set_on_click(self, callback):
        self._on_click_callback = callback

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._on_click_callback:
            self._on_click_callback()

    def start_flash(self):
        if self._flash_timer is not None:
            return

        self._is_visible = True
        self.show()
        self._flash_count = 0

        self._flash_timer = QTimer()
        self._flash_timer.timeout.connect(self._flash_toggle)
        self._flash_timer.start(500)

    def _flash_toggle(self):
        self._flash_count += 1

        if self._flash_count % 2 == 1:
            self.hide()
        else:
            self.show()

        if self._flash_count >= 20:
            self._stop_flash()

    def _stop_flash(self):
        if self._flash_timer is not None:
            self._flash_timer.stop()
            self._flash_timer = None
        self._is_visible = True
        self.show()

    def hide_bubble(self):
        self._stop_flash()
        self._is_visible = False
        self.hide()

    def show_bubble(self):
        self._is_visible = True
        self.show()

    def is_visible(self) -> bool:
        return self._is_visible