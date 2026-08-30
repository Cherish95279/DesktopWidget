# -*- coding: utf-8 -*-
"""
绘制层：表盘背景/指针/文字信息绘制、主题缓存、图片加载。

作为 MainWindow 的 mixin，提供 paintEvent / draw_hand / 主题缓存 / 图片加载等能力。
"""

import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QPainter, QPixmap, QColor, QFont, QPen

from ..constants import CENTER_X, CENTER_Y, DEFAULT_LAYOUT
from ..utils import get_weather_icon


class PaintMixin:
    """表盘绘制相关逻辑。"""

    def _init_paint(self):
        """初始化屏幕信息。"""
        screen = QApplication.primaryScreen()
        self.refresh_rate = self._read_refresh_rate()
        self.screen_res = (
            f"{screen.size().width()}×{screen.size().height()}"
            if screen else "1920×1080"
        )

    # ===== 加载图片（通过主题管理器） =====
    def _load_images(self):
        """通过主题管理器加载当前主题的所有图片"""
        bg_path = self.theme_manager.get_theme_path("bg.png")
        face_path = self.theme_manager.get_theme_path("face.png")
        self.bg = QPixmap(bg_path) if bg_path and os.path.exists(bg_path) else QPixmap()
        self.face = QPixmap(face_path) if face_path and os.path.exists(face_path) else QPixmap()
        hour_path = self.theme_manager.get_theme_path("Hour_Hand.png")
        minute_path = self.theme_manager.get_theme_path("Minute_Hand.png")
        second_path = self.theme_manager.get_theme_path("Second_Hand.png")
        self.hour = QPixmap(hour_path) if hour_path and os.path.exists(hour_path) else QPixmap()
        self.minute = QPixmap(minute_path) if minute_path and os.path.exists(minute_path) else QPixmap()
        self.second = QPixmap(second_path) if second_path and os.path.exists(second_path) else QPixmap()

        # 如果 face 为空，用 bg 替代
        if self.face.isNull():
            self.face = self.bg

        # 检查关键图片是否存在
        if any(p.isNull() for p in [self.bg, self.hour, self.minute, self.second]):
            print(" 部分图片加载失败，请检查主题文件")

    def _apply_hand_pivot(self):
        """根据当前主题设置指针旋转枢轴偏移量"""
        self.hand_px = 199
        self.hand_py = 143

    def reload_images(self):
        """重新加载当前主题的所有图片（主题切换时调用）"""
        self._load_images()
        self._apply_hand_pivot()
        # 强制重建背景缓存
        self._cached_bg = None
        self.update_theme_cache(force=True)
        self.update()
        # 切换主题时立即上报
        from src.ping_client import report_launch_full
        report_launch_full("idle", "theme_switched")

    # ---------- 主题缓存 ----------
    def update_theme_cache(self, force=False):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        theme_opacity = int(settings.value("theme_opacity", 100))
        theme_color = settings.value("theme_color", "#a8c7dc")
        theme_tint_alpha = int(settings.value("theme_tint_alpha", 80))

        if not force and (self._cached_bg is not None and
                          self._cached_theme_color == theme_color and
                          self._cached_theme_opacity == theme_opacity and
                          self._cached_tint_alpha == theme_tint_alpha):
            return

        self._cached_theme_color = theme_color
        self._cached_theme_opacity = theme_opacity
        self._cached_tint_alpha = theme_tint_alpha

        if not self.bg.isNull():
            bg_pixmap = self.bg.copy()
            if not bg_pixmap.isNull():
                color = QColor(theme_color)
                color.setAlpha(theme_tint_alpha)
                temp_painter = QPainter(bg_pixmap)
                temp_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
                temp_painter.fillRect(bg_pixmap.rect(), color)
                temp_painter.end()
                self._cached_bg = bg_pixmap
            else:
                self._cached_bg = self.bg
        else:
            self._cached_bg = QPixmap(400, 297)
            self._cached_bg.fill(QColor(theme_color))

        self.update()

    def draw_hand(self, painter, pixmap, cx, cy, px, py, angle):
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(angle)
        painter.drawPixmap(-px, -py, pixmap)
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._cached_bg is not None and not self._cached_bg.isNull():
            if self._cached_theme_opacity is not None:
                mapped_opacity = 0.75 + (self._cached_theme_opacity - 20) * (0.25 / 80)
                painter.setOpacity(mapped_opacity)
            painter.drawPixmap(0, 0, self._cached_bg)
            painter.setOpacity(1.0)

        if self.face is not None and not self.face.isNull():
            painter.drawPixmap(0, 0, self.face)

        cx = CENTER_X
        cy = CENTER_Y
        now = self.now
        self.draw_hand(painter, self.hour, cx, cy, self.hand_px, self.hand_py, (now.hour % 12) * 30 + now.minute * 0.5)
        self.draw_hand(painter, self.minute, cx, cy, self.hand_px, self.hand_py, now.minute * 6 + now.second * 0.1)
        self.draw_hand(painter, self.second, cx, cy, self.hand_px, self.hand_py, now.second * 6)

        # 绘制文字信息
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

        ip_text = f"{self.public_ip or self.local_ip}"

        # ---- 只显示短格式地区名 ----
        selected_county = settings.value("selected_county", "")
        selected_city = settings.value("selected_city", "")
        selected_province = settings.value("selected_province", "")

        if selected_county:
            display_city = selected_county
        elif selected_city:
            display_city = selected_city
        elif selected_province:
            display_city = selected_province
        else:
            display_city = self.weather.get('city', self._i18n['unknown_location'])
            if display_city == "--":
                display_city = self._i18n['unknown_location']

        weather_icon = get_weather_icon(self.weather['weather'])
        weather_text = f"{weather_icon} {self.weather['weather']} {self.weather['temp']}℃"
        netspeed_text = f"↓{self.down_speed:.1f}Mb/s\n↑{self.up_speed:.1f}Mb/s"
        cpu_text = f"CPU{int(self.cpu)}%"
        gpu_text = f"GPU{int(self.gpu)}%"
        resolution_text = f"{self.screen_res}"
        memory_text = f"{self._i18n['memory']}\n{int(self.mem)}%"
        uptime_text = self.uptime
        term_text = self.term_display if self.term_display else ""
        date_text = f"{self.now.strftime('%Y/%m/%d')}\n  {self._i18n['week']}{self._i18n['weekdays'][self.now.weekday()]}"
        lunar_text = self.lunar_text

        content_text_map = {
            "ip": ip_text,
            "weather": weather_text,
            "netspeed": netspeed_text,
            "cpu": cpu_text,
            "gpu": gpu_text,
            "resolution": resolution_text,
            "memory": memory_text,
            "date": date_text,
            "lunar": lunar_text,
            "term": term_text,
            "uptime": uptime_text,
            "empty": "",
        }
        # 遍历磁盘使用率，补充 content_text_map
        for dk, dv in self.disk_usage.items():
            if dk == "disk_total":
                content_text_map[dk] = f"{int(dv)}%"
            else:
                letter = dk.replace("disk_", "")
                content_text_map[dk] = f"{letter}: {int(dv)}%"

        multiline_map = {
            "date": [self.now.strftime('%Y/%m/%d'),
                     f"{self._i18n['week']}{self._i18n['weekdays'][self.now.weekday()]}"],
            "netspeed": [f"↓{self.down_speed:.1f}Mb/s", f"↑{self.up_speed:.1f}Mb/s"],
            "memory": [self._i18n['memory'], f"{int(self.mem)}%"],
            "disk_total": [self._i18n['disk_total'], f"{int(self.disk_usage.get('disk_total', 0))}%"],
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
                                     self._i18n['set_api'])
                elif self._loading_weather:
                    dots_text = "." * self._loading_dots
                    painter.drawText(x, y + h // 2, w, h // 2,
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                     f"⌛ {self._i18n['loading']}{dots_text}")
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

