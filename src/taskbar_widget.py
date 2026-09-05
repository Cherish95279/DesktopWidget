# -*- coding: utf-8 -*-
"""任务栏嵌入显示窗口 - 嵌入 Windows 任务栏通知区域左侧。

放弃自由拖动，改为通过 Win32 SetParent 嵌入任务栏。
宽度根据内容自适应，高度适配任务栏客户区。
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QPainter, QFont, QColor, QPen, QFontMetrics

from .i18n.translations import TranslatorManager
from .taskbar.taskbar_embedder import TaskbarEmbedder


class TaskbarWidget(QWidget):
    """嵌入任务栏的信息显示窗。"""

    def __init__(self, main_window, tray_menu=None):
        super().__init__(None)
        self.main_window = main_window
        self._tray_menu = tray_menu
        self._lang = 'zh'

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # 初始尺寸，嵌入后由 embedder 接管
        self.setFixedSize(120, 28)

        self._bg_color = QColor(30, 30, 30, 200)
        self._text_color = QColor(255, 255, 255)
        self._font = QFont('Microsoft YaHei', 9)

        self._init_i18n_texts()
        TranslatorManager().on_language_changed(self._on_language_changed)

        # 数据刷新定时器（复用现有机制，仅触发重绘）
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000)

        # 嵌入管理器
        self._embedder = TaskbarEmbedder(self)

    # ---------- 嵌入控制 ----------
    def show_in_taskbar(self):
        """显示并嵌入任务栏。"""
        self._embedder.enable()

    def hide_from_taskbar(self):
        """脱离任务栏并隐藏。"""
        self._embedder.disable()

    def retranslate_ui(self):
        self._on_language_changed(self._lang)

    def _init_i18n_texts(self):
        t = TranslatorManager().translate
        self._i18n = {
            "memory": t('MainWindow', '内存'),
            "disk_total": t('MainWindow', '磁盘总计'),
            "run_prefix": t('MainWindow', '运行'),
            "min_unit": t('MainWindow', '分钟'),
            "hour_unit": t('MainWindow', '小时'),
            "month_unit": t('MainWindow', '月'),
        }

    def _on_language_changed(self, lang_code):
        self._lang = lang_code
        self._init_i18n_texts()
        self.update()

    def desired_width(self):
        """根据当前内容计算所需宽度（供 embedder 定位使用）。"""
        text = self._get_display_text()
        fm = QFontMetrics(self._font)
        # 多行时取最长行的宽度
        max_w = max(fm.horizontalAdvance(line) for line in text.split('\n'))
        return max_w + 16  # 左右各 8px 内边距

    def contextMenuEvent(self, event):
        if self._tray_menu is not None:
            pos = event.globalPos()
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._tray_menu.exec(pos))

    def paintEvent(self, event):
        painter = QPainter(self)
        # 恢复抗锯齿：colorkey 用浅灰色，文字边缘半透明像素偏浅灰，融入浅色任务栏
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 填充色键色 RGB(210,210,211)，该色被 SetLayeredWindowAttributes 设为透明
        painter.fillRect(self.rect(), QColor(210, 210, 211))
        painter.setFont(self._font)
        font_color = QSettings('MyDesktopApp', 'WeatherSettings').value('font_color', '#1c344d')
        painter.setPen(QPen(QColor(font_color)))

        text = self._get_display_text()
        lines = text.split('\n')
        if len(lines) == 1:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
        else:
            # 多行手动绘制，控制行距
            fm = QFontMetrics(self._font)
            line_h = fm.height()
            total_h = line_h * len(lines)
            y = (self.height() - total_h) // 2 + fm.ascent()
            for line in lines:
                painter.drawText(0, y - line_h, self.width(), line_h,
                                 Qt.AlignmentFlag.AlignCenter, line)
                y += line_h

    def _get_display_text(self):
        settings = QSettings('MyDesktopApp', 'WeatherSettings')
        key = settings.value('taskbar_display', 'netspeed')
        mw = self.main_window

        if key == 'netspeed':
            return chr(8593) + ' {:.1f}MB/s'.format(mw.up_speed) + '\n' + chr(8595) + ' {:.1f}MB/s'.format(mw.down_speed)
        elif key == 'weather':
            w = mw.weather.get('weather', '--')
            t = mw.weather.get('temp', '--')
            return '{} {}'.format(w, t) + chr(8451)
        elif key == 'cpu':
            return 'CPU {}%'.format(int(mw.cpu))
        elif key == 'gpu':
            return 'GPU {}%'.format(int(mw.gpu))
        elif key == 'memory':
            mem_label = self._i18n.get('memory', '内存')
            return '{} {}%'.format(mem_label, int(mw.mem))
        elif key == 'uptime':
            return mw.uptime if mw.uptime else ''
        elif key == 'disk_total':
            label = self._i18n.get('disk_total', '磁盘总计')
            val = mw.disk_usage.get('disk_total', 926)
            return '{} {}%'.format(label, int(val))
        elif key.startswith('disk_'):
            letter = key.replace('disk_', '')
            val = mw.disk_usage.get(key, 926)
            return '{}: {}%'.format(letter, int(val))
        else:
            # 插件内容渲染
            try:
                from .plugin_manager import get_plugin_manager
                pm = get_plugin_manager()
                if pm.is_plugin_key(key):
                    return pm.render_taskbar(key, self._i18n)
            except Exception:
                pass
            return ''
