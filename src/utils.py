import sys
import os

# ---------- 资源路径 ----------
def resource_path(rel_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    # 如果路径已经以 skins/、icons/ 或 screenshots/ 开头，则直接拼接，否则默认加 skins/default/
    if not rel_path.startswith(('skins/', 'icons/', 'screenshots/')):
        rel_path = os.path.join("skins", "default", rel_path)
    return os.path.join(base_path, rel_path)
# ---------- 天气图标 ----------
def get_weather_icon(weather_str):
    mapping = {
        "晴": "☀️",
        "多云": "⛅",
        "阴": "☁️",
        "小雨": "🌦️",
        "中雨": "🌧️",
        "大雨": "🌧️",
        "雷阵雨": "⛈️",
        "小雪": "🌨️",
        "中雪": "❄️",
        "大雪": "❄️",
        "雾": "🌫️",
        "霾": "🌫️",
        "大风": "💨",
    }
    first = weather_str.split('转')[0] if '转' in weather_str else weather_str
    return mapping.get(first, "🌡️")