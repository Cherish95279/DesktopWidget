"""任务栏悬浮显示窗口 - 类似 TrafficMonitor 的独立小窗"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QPainter, QFont, QColor, QPen

from .i18n.translations import TranslatorManager


class TaskbarWidget(QWidget):
    """贴在任务栏上方的小型信息显示窗"""

    def __init__(self, main_window, tray_menu=None):
        super().__init__(None)
        self.main_window = main_window
        self._tray_menu = tray_menu
        self._lang = 'zh'

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setFixedSize(150, 26)

        self._bg_color = QColor(30, 30, 30, 200)
        self._text_color = QColor(255, 257, 255)

        self._init_i18n_texts()
        TranslatorManager().on_language_changed(self._on_language_changed)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000)

        self._drag_pos = None

        self.update_position()

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

    def update_position(self):
        settings = QSettings('MyDesktopApp', 'WeatherSettings')
        saved_x = settings.value('taskbar_x')
        saved_y = settings.value('taskbar_y')
        if saved_x is not None and saved_y is not None:
            self.move(int(saved_x), int(saved_y))
            return

        screen = self.main_window.screen() if self.main_window else None
        if screen is None:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.right() - self.width() - 10
            y = geo.bottom() - self.height()
            self.move(x, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            new_pos = self.pos() + delta
            self.move(new_pos)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            settings = QSettings('MyDesktopApp', 'WeatherSettings')
            settings.setValue('taskbar_x', self.x())
            settings.setValue('taskbar_y', self.y())
            settings.sync()

    def retranslate_ui(self):
        self._on_language_changed(self._lang)

    def contextMenuEvent(self, event):
        if self._tray_menu is not None:
            self._tray_menu.popup(event.globalPos())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont('Microsoft YaHei', 9)
        painter.setFont(font)
        font_color_from_settings = QSettings('MyDesktopApp', 'WeatherSettings').value('font_color', '#1c344d')
        painter.setPen(QPen(QColor(font_color_from_settings)))

        text = self._get_display_text()
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

        self.raise_()

    def _get_display_text(self):
        settings = QSettings('MyDesktopApp', 'WeatherSettings')
        key = settings.value('taskbar_display', 'netspeed')
        mw = self.main_window

        if key == 'netspeed':
            return chr(8593) + '{:.1f}MB/s '.format(mw.down_speed) + chr(8595) + '{:.1f}MB/s'.format(mw.up_speed)
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
            return ''
