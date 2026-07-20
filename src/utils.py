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

    # 开发环境也应相对项目根目录定位资源，而不是依赖进程当前目录。
    base_path = (
        _meipass_path
        if _meipass_path
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

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
        # ===== 中文映射（原有） =====
        "晴": "☀️",
        "晴间多云": "⛅",
        "多云": "⛅",
        "阴": "☁️",
        "小雨": "🌦️",
        "中雨": "🌧️",
        "大雨": "🌧️",
        "雷阵雨": "⛈️",
        "雷阵雨并伴有冰雹": "⛈️",
        "阵雨": "🌦️",
        "强阵雨": "🌧️",
        "小雪": "🌨️",
        "中雪": "❄️",
        "大雪": "❄️",
        "阵雪": "🌨️",
        "毛毛雨/细雨": "🌦️",
        "雨": "🌧️",
        "雪": "❄️",
        "冻雨": "🌧️",
        "雾": "🌫️",
        "霾": "🌫️",
        "大风": "💨",

        # ===== 英文映射（新增，用于 WeatherAPI） =====
        "Sunny": "☀️",
        "Clear": "☀️",
        "Partly cloudy": "⛅",
        "Cloudy": "☁️",
        "Overcast": "☁️",
        "Mist": "🌫️",
        "Fog": "🌫️",
        "Light rain": "🌦️",
        "Moderate rain": "🌧️",
        "Heavy rain": "🌧️",
        "Patchy rain possible": "🌦️",
        "Light drizzle": "🌦️",
        "Thundery outbreaks possible": "⛈️",
        "Light snow": "🌨️",
        "Moderate snow": "❄️",
        "Heavy snow": "❄️",
        "Patchy snow possible": "🌨️",
        "Blizzard": "❄️",
        "Windy": "💨",
        "Strong winds": "💨",
    }
    first = weather_str.split('转')[0] if '转' in weather_str else weather_str
    return mapping.get(first, "🌡️")


# ---------- IP 定位 ----------
def get_ip_location():
    """
    调用 ip-api.com 获取当前 IP 的地理位置
    返回: (latitude, longitude, city) 或 (None, None, None)
    """
    import requests
    try:
        url = "http://ip-api.com/json/?lang=zh-CN&fields=status,country,city,lat,lon"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                return (
                    data.get("lat"),
                    data.get("lon"),
                    data.get("city")
                )
    except Exception:
        pass
    return None, None, None

# ---------- 天气文本翻译（用于 WeatherAPI 英文→多语言） ----------
_WEATHER_TRANSLATIONS = {
    "en": {
        "Sunny": "Sunny", "Clear": "Clear", "Partly cloudy": "Partly cloudy",
        "Cloudy": "Cloudy", "Overcast": "Overcast", "Mist": "Mist", "Fog": "Fog",
        "Light rain": "Light rain", "Moderate rain": "Moderate rain",
        "Heavy rain": "Heavy rain", "Patchy rain possible": "Patchy rain possible",
        "Light drizzle": "Light drizzle", "Thundery outbreaks possible": "Thundery outbreaks possible",
        "Light snow": "Light snow", "Moderate snow": "Moderate snow",
        "Heavy snow": "Heavy snow", "Patchy snow possible": "Patchy snow possible",
        "Blizzard": "Blizzard", "Windy": "Windy", "Strong winds": "Strong winds",
    },
    "zh": {
        "Sunny": "晴", "Clear": "晴", "Partly cloudy": "多云", "Cloudy": "阴",
        "Overcast": "阴", "Mist": "雾", "Fog": "雾", "Light rain": "小雨",
        "Moderate rain": "中雨", "Heavy rain": "大雨", "Patchy rain possible": "阵雨",
        "Light drizzle": "毛毛雨", "Thundery outbreaks possible": "雷阵雨",
        "Light snow": "小雪", "Moderate snow": "中雪", "Heavy snow": "大雪",
        "Patchy snow possible": "阵雪", "Blizzard": "暴雪", "Windy": "大风", "Strong winds": "大风",
    },
    "ja": {
        "Sunny": "晴れ", "Clear": "晴れ", "Partly cloudy": "曇り時々晴れ",
        "Cloudy": "曇り", "Overcast": "曇り", "Mist": "霧", "Fog": "濃霧",
        "Light rain": "小雨", "Moderate rain": "雨", "Heavy rain": "大雨",
        "Patchy rain possible": "にわか雨", "Light drizzle": "霧雨",
        "Thundery outbreaks possible": "雷雨", "Light snow": "小雪",
        "Moderate snow": "雪", "Heavy snow": "大雪", "Patchy snow possible": "にわか雪",
        "Blizzard": "吹雪", "Windy": "強風", "Strong winds": "暴風",
    },
    "ko": {
        "Sunny": "맑음", "Clear": "맑음", "Partly cloudy": "구름 조금",
        "Cloudy": "흐림", "Overcast": "흐림", "Mist": "안개", "Fog": "짙은 안개",
        "Light rain": "약한 비", "Moderate rain": "비", "Heavy rain": "강한 비",
        "Patchy rain possible": "소나기", "Light drizzle": "이슬비",
        "Thundery outbreaks possible": "뇌우", "Light snow": "약한 눈",
        "Moderate snow": "눈", "Heavy snow": "강한 눈", "Patchy snow possible": "소낙눈",
        "Blizzard": "눈보라", "Windy": "강풍", "Strong winds": "폭풍",
    },
    "es": {
        "Sunny": "Soleado", "Clear": "Despejado", "Partly cloudy": "Parcialmente nublado",
        "Cloudy": "Nublado", "Overcast": "Cubierto", "Mist": "Bruma", "Fog": "Niebla",
        "Light rain": "Lluvia ligera", "Moderate rain": "Lluvia moderada",
        "Heavy rain": "Lluvia fuerte", "Patchy rain possible": "Lluvia dispersa",
        "Light drizzle": "Llovizna", "Thundery outbreaks possible": "Tormenta eléctrica",
        "Light snow": "Nieve ligera", "Moderate snow": "Nieve moderada",
        "Heavy snow": "Nieve fuerte", "Patchy snow possible": "Nieve dispersa",
        "Blizzard": "Ventisca", "Windy": "Ventoso", "Strong winds": "Vientos fuertes",
    },
    "fr": {
        "Sunny": "Ensoleillé", "Clear": "Dégagé", "Partly cloudy": "Partiellement nuageux",
        "Cloudy": "Nuageux", "Overcast": "Couvert", "Mist": "Brume", "Fog": "Brouillard",
        "Light rain": "Pluie légère", "Moderate rain": "Pluie modérée",
        "Heavy rain": "Pluie forte", "Patchy rain possible": "Averses éparses",
        "Light drizzle": "Bruine", "Thundery outbreaks possible": "Orages possibles",
        "Light snow": "Neige légère", "Moderate snow": "Neige modérée",
        "Heavy snow": "Neige forte", "Patchy snow possible": "Averses de neige",
        "Blizzard": "Blizzard", "Windy": "Venteux", "Strong winds": "Vents forts",
    },
    "de": {
        "Sunny": "Sonnig", "Clear": "Klar", "Partly cloudy": "Teilweise bewölkt",
        "Cloudy": "Bewölkt", "Overcast": "Bedeckt", "Mist": "Dunst", "Fog": "Nebel",
        "Light rain": "Leichter Regen", "Moderate rain": "Mäßiger Regen",
        "Heavy rain": "Starker Regen", "Patchy rain possible": "Vereinzelter Regen",
        "Light drizzle": "Nieselregen", "Thundery outbreaks possible": "Gewitter möglich",
        "Light snow": "Leichter Schnee", "Moderate snow": "Mäßiger Schnee",
        "Heavy snow": "Starker Schnee", "Patchy snow possible": "Vereinzelter Schnee",
        "Blizzard": "Schneesturm", "Windy": "Windig", "Strong winds": "Starke Winde",
    },
    "zh_TW": {
        "Sunny": "晴", "Clear": "晴", "Partly cloudy": "多雲", "Cloudy": "陰",
        "Overcast": "陰", "Mist": "霧", "Fog": "濃霧", "Light rain": "小雨",
        "Moderate rain": "中雨", "Heavy rain": "大雨", "Patchy rain possible": "陣雨",
        "Light drizzle": "毛毛雨", "Thundery outbreaks possible": "雷陣雨",
        "Light snow": "小雪", "Moderate snow": "中雪", "Heavy snow": "大雪",
        "Patchy snow possible": "陣雪", "Blizzard": "暴雪", "Windy": "大風", "Strong winds": "強風",
    },
}


def translate_weather_text(weather_en: str, language_code: str = None) -> str:
    """
    将英文天气描述翻译为目标语言
    :param weather_en: 英文天气描述（如 "Sunny"）
    :param language_code: 语言代码（如 "zh_CN", "en", "ja"），如果为 None 则使用当前系统语言
    :return: 翻译后的天气描述
    """
    if not weather_en:
        return weather_en

    if language_code is None:
        from PyQt6.QtCore import QLocale
        language_code = QLocale.system().name()

    lang_key = language_code.split("_")[0] if "_" in language_code else language_code

    translations = _WEATHER_TRANSLATIONS.get(lang_key)
    if not translations:
        return weather_en

    return translations.get(weather_en, weather_en)
