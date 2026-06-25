import sys
import os

# ---------- 资源路径缓存 ----------
_path_cache = {}
_meipass_checked = False
_meipass_path = None


def resource_path(rel_path):
    """获取资源文件的绝对路径（带缓存）"""
    # 检查缓存
    if rel_path in _path_cache:
        return _path_cache[rel_path]

    # 确定基础路径（只检查一次 sys._MEIPASS）
    global _meipass_checked, _meipass_path
    if not _meipass_checked:
        try:
            _meipass_path = sys._MEIPASS
        except Exception:
            _meipass_path = None
        _meipass_checked = True

    base_path = _meipass_path if _meipass_path else os.path.abspath(".")

    # 如果路径已经以 skins/、icons/ 或 screenshots/ 开头，直接拼接，否则默认加 skins/default/
    if not rel_path.startswith(('skins/', 'icons/', 'screenshots/')):
        rel_path = os.path.join("skins", "default", rel_path)

    abs_path = os.path.join(base_path, rel_path)

    # 存入缓存
    _path_cache[rel_path] = abs_path
    return abs_path


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