# -*- coding: utf-8 -*-
"""日出日落插件 - 显示今日日出日落时间"""

import math
from datetime import datetime
from plugin_manager import ContentPlugin


class SunriseSunsetPlugin(ContentPlugin):
    """日出日落插件"""

    def collect(self, context):
        """计算今日日出日落时间"""
        now = context.now
        lat, lon = self._get_location(context)

        sunrise, sunset = self._calc_sunrise_sunset(
            now.year, now.month, now.day, lat, lon)

        if sunrise is None or sunset is None:
            return {
                "sunrise": "--",
                "sunset": "--",
                "day_length": "--",
                "date": now.strftime("%Y/%m/%d"),
            }

        day_length = sunset - sunrise
        hours = int(day_length.total_seconds() // 3600)
        minutes = int((day_length.total_seconds() % 3600) // 60)

        return {
            "sunrise": sunrise.strftime("%H:%M"),
            "sunset": sunset.strftime("%H:%M"),
            "day_length": str(hours) + "h " + str(minutes) + "m",
            "date": now.strftime("%Y/%m/%d"),
        }

    def render_short(self, data, i18n):
        """表盘显示：两行"""
        return ["🌅 " + data["sunrise"], "🌇 " + data["sunset"]]

    def render_detail(self, data, is_pro, i18n):
        """悬停详情"""
        lines = [
            "日期：" + data["date"],
            "日出：" + data["sunrise"],
            "日落：" + data["sunset"],
        ]
        if is_pro:
            lines.append("昼长：" + data["day_length"])
        return lines

    def render_taskbar(self, data, i18n):
        """任务栏：单行"""
        return "🌅" + data["sunrise"] + " 🌇" + data["sunset"]

    # ---------- 内部方法 ----------

    def _get_location(self, context):
        """从用户设置获取经纬度，默认北京"""
        city = context.get_setting("selected_city", "")
        # 简单的城市经纬度映射，可扩展
        city_coords = {
            "北京": (39.9042, 116.4074),
            "上海": (31.2304, 121.4737),
            "广州": (23.1291, 113.2644),
            "深圳": (22.5431, 114.0579),
            "成都": (30.5728, 104.0668),
            "武汉": (30.5928, 114.3055),
            "杭州": (30.2741, 120.1551),
            "南京": (32.0603, 118.7969),
            "西安": (34.3416, 108.9398),
            "重庆": (29.4316, 106.9123),
        }
        if city in city_coords:
            return city_coords[city]
        return 39.9042, 116.4074  # 默认北京

    def _calc_sunrise_sunset(self, year, month, day, lat, lon):
        """简化的日出日落计算（基于天文公式）"""
        n = datetime(year, month, day).timetuple().tm_yday

        # 太阳赤纬
        decl = 23.45 * math.sin(math.radians(360 * (284 + n) / 365))

        # 时角
        lat_rad = math.radians(lat)
        decl_rad = math.radians(decl)
        cos_omega = -math.tan(lat_rad) * math.tan(decl_rad)

        # 极昼/极夜处理
        if cos_omega > 1:
            return None, None  # 极夜
        if cos_omega < -1:
            return None, None  # 极昼

        omega = math.degrees(math.acos(cos_omega))

        # 日出日落时间（UTC，粗略）
        sunrise_utc = 12 - omega / 15 - lon / 15
        sunset_utc = 12 + omega / 15 - lon / 15

        # 转为北京时间（UTC+8）
        tz_offset = 8
        sunrise_hour = (sunrise_utc + tz_offset) % 24
        sunset_hour = (sunset_utc + tz_offset) % 24

        sunrise = self._hour_to_datetime(year, month, day, sunrise_hour)
        sunset = self._hour_to_datetime(year, month, day, sunset_hour)

        return sunrise, sunset

    def _hour_to_datetime(self, year, month, day, hour_float):
        """将小时浮点数转为 datetime"""
        h = int(hour_float)
        m = int((hour_float - h) * 60)
        s = int(((hour_float - h) * 60 - m) * 60)
        return datetime(year, month, day, h, m, s)
