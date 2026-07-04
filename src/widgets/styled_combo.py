# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QComboBox, QStylePainter, QStyleOptionComboBox
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygon


class StyledComboBox(QComboBox):
    """统一样式下拉框，自定义绘制下拉箭头"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)

    def paintEvent(self, event):
        painter = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)

        rect = self.rect()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景和边框
        is_hover = opt.state & QStyle.StateFlag.State_MouseOver
        bg = "#e6f4ff" if is_hover else "#f5f5f5"
        border = "#1677ff" if is_hover else "#ccc"
        painter.setBrush(QColor(bg))
        painter.setPen(QPen(QColor(border), 1))
        painter.drawRoundedRect(rect, 4, 4)

        # 文字
        painter.setPen(QColor("#1677ff" if is_hover else "#333"))
        text_rect = rect.adjusted(6, 0, -24, 0)
        text = self.currentText()
        if text:
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)

        # 描边小三角
        color = "#1677ff" if is_hover else "#666"
        x = rect.right() - 18
        y = (rect.height() - 6) // 2
        painter.setPen(QPen(QColor(color), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(QPolygon([
            QPoint(x, y),
            QPoint(x + 10, y),
            QPoint(x + 5, y + 6)
        ]))

        painter.end()