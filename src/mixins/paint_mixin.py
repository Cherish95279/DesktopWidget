from PyQt6.QtCore import QTimer, QElapsedTimer, QRectF, QPointF, Qt
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPainterPath
from PyQt6.QtWidgets import QApplication
from ..constants import CENTER_X, CENTER_Y, DEFAULT_LAYOUT
from ..utils import get_weather_icon


class PaintMixin:
    """绘制引擎混入：paintEvent、指针绘制、FPS统计"""

    def _init_paint(self):
        """初始化绘制相关变量（由 __init__ 调用）"""
        self.paint_count = 0
        self.last_paint_time = QElapsedTimer()
        self.last_paint_time.start()
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(1000)

        # 屏幕分辨率
        screen = QApplication.primaryScreen()
        if screen:
            size = screen.size()
            self.screen_res = f"{size.width()}×{size.height()}"
        else:
            self.screen_res = "1920×1080"

    def update_fps(self):
        elapsed = self.last_paint_time.elapsed()
        if elapsed > 0:
            self.fps = int(self.paint_count * 1000 / elapsed)
        else:
            self.fps = 0
        self.paint_count = 0
        self.last_paint_time.restart()
        self.update()

    def paintEvent(self, event):
        self.paint_count += 1
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景（图片自身透明圆角）
        if hasattr(self, '_cached_bg') and self._cached_bg is not None and not self._cached_bg.isNull():
            if hasattr(self, '_cached_theme_opacity') and self._cached_theme_opacity is not None:
                mapped_opacity = 0.75 + (self._cached_theme_opacity - 20) * (0.25 / 80)
                painter.setOpacity(mapped_opacity)
            painter.drawPixmap(0, 0, self._cached_bg)
            painter.setOpacity(1.0)

        # 绘制表盘（自身透明圆角）
        if hasattr(self, 'face') and self.face is not None and not self.face.isNull():
            painter.drawPixmap(0, 0, self.face)

        # 绘制指针
        cx = CENTER_X
        cy = CENTER_Y
        now = self.now

        self.draw_hand(painter, self.hour, cx, cy, (now.hour % 12) * 30 + now.minute * 0.5)
        self.draw_hand(painter, self.minute, cx, cy, now.minute * 6 + now.second * 0.1)
        self.draw_hand(painter, self.second, cx, cy, now.second * 6)

        dot_size = 18
        scaled_dot = self.center_dot.scaled(
            dot_size, dot_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        painter.drawPixmap(cx - dot_size // 2, cy - dot_size // 2, scaled_dot)

        # 绘制文字信息
        self._draw_text_info(painter)

    def draw_hand(self, painter, pixmap, cx, cy, angle):
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(angle)
        painter.drawPixmap(-pixmap.width() // 2, -pixmap.height() // 2, pixmap)
        painter.restore()

    def _draw_text_info(self, painter):
        """绘制文字信息（拆分自 paintEvent）"""
        from PyQt6.QtCore import QSettings
        settings = QSettings("MyDesktopApp", "WeatherSettings")

        font_family = settings.value("font_family", "Microsoft YaHei")
        font_size = int(settings.value("font_size", 10))
        font_color = settings.value("font_color", "#1c344d")

        font = QFont(font_family, font_size)
        painter.setFont(font)
        painter.setPen(QPen(QColor(font_color)))

        slot_values = {}
        slot_keys = ["slot_1", "slot_2", "slot_3", "slot_4", "slot_5", "slot_6", "slot_7", "slot_8"]
        for key in slot_keys:
            default_val = DEFAULT_LAYOUT.get(key, "empty")
            slot_values[key] = settings.value(key, default_val)

        # 获取显示城市
        selected_city = settings.value("selected_city", "")
        selected_county = settings.value("selected_county", "")
        user_city = selected_county if selected_county else selected_city
        if user_city:
            display_city = user_city
        else:
            display_city = self.weather.get('city', '未知地区')
            if display_city == "--":
                display_city = "未知地区"

        # 准备各种文字
        weather_icon = get_weather_icon(self.weather['weather'])
        weather_text = f"{weather_icon} {self.weather['weather']} {self.weather['temp']}℃"
        netspeed_text = f"↓{self.down_speed:.1f}Mb/s\n↑{self.up_speed:.1f}Mb/s"
        cpu_text = f"CPU{int(self.cpu)}%"
        gpu_text = f"GPU{int(self.gpu)}%"
        resolution_text = f"{self.screen_res}"
        refresh_rate_text = f"{self.fps}Hz"
        memory_text = f"内存\n{int(self.mem)}%"
        date_text = f"{self.now.strftime('%Y/%m/%d')}\n  星期{['一','二','三','四','五','六','日'][self.now.weekday()]}"
        lunar_text = f"{self.lunar_text}\n{self.term_display}"
        ip_text = f"{self.local_ip}"

        content_text_map = {
            "ip": ip_text,
            "weather": weather_text,
            "netspeed": netspeed_text,
            "cpu": cpu_text,
            "gpu": gpu_text,
            "resolution": resolution_text,
            "refresh_rate": refresh_rate_text,
            "memory": memory_text,
            "date": date_text,
            "lunar": lunar_text,
            "empty": "",
        }

        multiline_map = {
            "lunar": [self.lunar_text, self.term_display],
            "date": [self.now.strftime('%Y/%m/%d'), f"星期{['一','二','三','四','五','六','日'][self.now.weekday()]}"],
            "netspeed": [f"↓{self.down_speed:.1f}Mb/s", f"↑{self.up_speed:.1f}Mb/s"],
            "memory": ["内存", f"{int(self.mem)}%"],
        }

        slot_position_map = {
            "slot_1": (20, 30, 105, 43),
            "slot_2": (20, 86, 85, 43),
            "slot_3": (20, 166, 70, 50),
            "slot_4": (20, 235, 88, 50),
            "slot_5": (280, 30, 94, 43),
            "slot_6": (314, 86, 71, 43),
            "slot_7": (324, 166, 60, 50),
            "slot_8": (273, 238, 97, 43),
        }

        for slot_key, (x, y, w, h) in slot_position_map.items():
            configured_key = slot_values.get(slot_key, "empty")
            if configured_key == "empty":
                continue

            if configured_key == "weather":
                painter.drawText(x, y, w, h // 2,
                                 Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                 display_city)

                if not self._api_configured:
                    painter.drawText(x, y + h // 2, w, h // 2,
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                     "设置API")
                elif self._loading_weather:
                    dots_text = "." * self._loading_dots
                    painter.drawText(x, y + h // 2, w, h // 2,
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                     f"⌛ 加载中{dots_text}")
                else:
                    weather_icon = get_weather_icon(self.weather['weather'])
                    weather_text = f"{weather_icon} {self.weather['weather']} {self.weather['temp']}℃"
                    painter.drawText(x, y + h // 2, w, h // 2,
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                     weather_text)
                continue

            if configured_key in multiline_map:
                lines = multiline_map[configured_key]
                line_height = h // 2
                for idx, line in enumerate(lines):
                    if line:
                        painter.drawText(x, y + idx * line_height, w, line_height,
                                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                         line)
            elif configured_key in content_text_map:
                text = content_text_map[configured_key]
                if text:
                    painter.drawText(x, y, w, h,
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                     text)