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
    """Get emoji icon for weather text in any language (auto-detects via translation tables)."""
    if not weather_str:
        return "🌡️"

    first = weather_str.split('转')[0] if '转' in weather_str else weather_str

    # English-only icon mapping (single source of truth)
    _ICON_MAP = {
        "Sunny": "☀️", "Clear": "☀️",
        "Fair to cloudy": "⛅", "Partly cloudy": "⛅",
        "Cloudy": "☁️", "Overcast": "☁️",
        "Mist": "🌫️", "Fog": "🌫️", "Freezing fog": "🌫️",
        "Smoke": "🌫️", "Haze": "🌫️", "Smokey haze": "🌫️", "Smoky haze": "🌫️",
        "Light drizzle": "🌦️", "Patchy light drizzle": "🌦️",
        "Patchy rain possible": "🌦️", "Patchy rain nearby": "🌦️",
        "Light rain": "🌦️", "Light rain shower": "🌦️",
        "Patchy light rain": "🌦️",
        "Rain": "🌧️", "Rain shower": "🌦️",
        "Moderate rain": "🌧️", "Moderate rain at times": "🌧️",
        "Moderate or heavy rain shower": "🌧️", "Heavy rain shower": "🌧️",
        "Heavy rain": "🌧️", "Heavy rain at times": "🌧️",
        "Torrential rain shower": "🌧️",
        "Light freezing rain": "🌧️", "Moderate or heavy freezing rain": "🌧️",
        "Freezing rain": "🌧️",
        "Light sleet": "🌨️", "Moderate or heavy sleet": "🌨️",
        "Light sleet showers": "🌨️", "Moderate or heavy sleet showers": "🌨️",
        "Patchy sleet possible": "🌨️",
        "Freezing drizzle": "🌧️", "Heavy freezing drizzle": "🌧️",
        "Patchy freezing drizzle possible": "🌧️",
        "Light snow": "🌨️", "Patchy light snow": "🌨️",
        "Moderate snow": "❄️", "Patchy moderate snow": "❄️",
        "Heavy snow": "❄️", "Patchy heavy snow": "❄️",
        "Snow": "❄️",
        "Patchy snow possible": "🌨️",
        "Snow shower": "🌨️",
        "Light snow showers": "🌨️", "Moderate or heavy snow showers": "❄️",
        "Blowing snow": "❄️", "Blizzard": "❄️",
        "Ice pellets": "🌨️",
        "Light showers of ice pellets": "🌨️",
        "Moderate or heavy showers of ice pellets": "🌨️",
        "Thundery outbreaks possible": "⛈️",
        "Thundery outbreaks in nearby": "⛈️",
        "Thunderstorm": "⛈️", "Thunderstorm with hail": "⛈️",
        "Patchy light rain with thunder": "⛈️",
        "Moderate or heavy rain with thunder": "⛈️",
        "Patchy light snow with thunder": "⛈️",
        "Moderate or heavy snow with thunder": "⛈️",
        "Windy": "💨", "Strong winds": "💨",
        "Hail": "🌨️",
    }

    # 1. Try direct English match (WeatherAPI or untranslated)
    if first in _ICON_MAP:
        return _ICON_MAP[first]
    # 1b. Case-insensitive fallback for WeatherAPI variants
    first_lower = first.lower()
    for key in _ICON_MAP:
        if key.lower() == first_lower:
            return _ICON_MAP[key]

    # 2. Reverse-translate from any language back to English, then look up icon
    for lang_key, translations in _WEATHER_TRANSLATIONS.items():
        for en_key, trans_val in translations.items():
            if trans_val == first:
                if en_key in _ICON_MAP:
                    return _ICON_MAP[en_key]

    return "🌡️"
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

# ---------- 天气文本翻译（用于 WeatherAPI 英文→多语言）----------
_WEATHER_TRANSLATIONS = {
    "en": {
        "Sunny": "Sunny", "Clear": "Clear", "Partly cloudy": "Partly cloudy",
        "Cloudy": "Cloudy", "Overcast": "Overcast", "Mist": "Mist",
        "Fog": "Fog", "Freezing fog": "Freezing fog",
        "Light drizzle": "Light drizzle", "Patchy rain possible": "Patchy rain possible",
        "Patchy rain nearby": "Patchy rain nearby", "Patchy light drizzle": "Patchy light drizzle",
        "Light rain": "Light rain", "Moderate rain": "Moderate rain",
        "Rain": "Rain", "Freezing rain": "Freezing rain",
        "Rain shower": "Rain shower", "Heavy rain shower": "Heavy rain shower",
        "Snow": "Snow", "Snow shower": "Snow shower",
        "Thunderstorm": "Thunderstorm", "Thunderstorm with hail": "Thunderstorm with hail",
        "Fair to cloudy": "Fair to cloudy",
        "Moderate rain at times": "Moderate rain at times",
        "Heavy rain": "Heavy rain", "Heavy rain at times": "Heavy rain at times",
        "Light rain shower": "Light rain shower",
        "Moderate or heavy rain shower": "Moderate or heavy rain shower",
        "Torrential rain shower": "Torrential rain shower",
        "Light freezing rain": "Light freezing rain",
        "Moderate or heavy freezing rain": "Moderate or heavy freezing rain",
        "Light sleet": "Light sleet", "Moderate or heavy sleet": "Moderate or heavy sleet",
        "Light sleet showers": "Light sleet showers",
        "Moderate or heavy sleet showers": "Moderate or heavy sleet showers",
        "Patchy sleet possible": "Patchy sleet possible",
        "Freezing drizzle": "Freezing drizzle",
        "Heavy freezing drizzle": "Heavy freezing drizzle",
        "Patchy freezing drizzle possible": "Patchy freezing drizzle possible",
        "Light snow": "Light snow", "Moderate snow": "Moderate snow",
        "Heavy snow": "Heavy snow", "Patchy snow possible": "Patchy snow possible",
        "Patchy light snow": "Patchy light snow", "Patchy moderate snow": "Patchy moderate snow",
        "Patchy heavy snow": "Patchy heavy snow",
        "Light snow showers": "Light snow showers",
        "Moderate or heavy snow showers": "Moderate or heavy snow showers",
        "Blowing snow": "Blowing snow", "Blizzard": "Blizzard",
        "Ice pellets": "Ice pellets",
        "Light showers of ice pellets": "Light showers of ice pellets",
        "Moderate or heavy showers of ice pellets": "Moderate or heavy showers of ice pellets",
        "Thundery outbreaks possible": "Thundery outbreaks possible",
        "Thundery outbreaks in nearby": "Thundery outbreaks in nearby",
        "Patchy light rain with thunder": "Patchy light rain with thunder",
        "Moderate or heavy rain with thunder": "Moderate or heavy rain with thunder",
        "Patchy light snow with thunder": "Patchy light snow with thunder",
        "Moderate or heavy snow with thunder": "Moderate or heavy snow with thunder",
        "Smoke": "Smoke", "Haze": "Haze", "Smokey haze": "Smokey haze", "Smoky haze": "Smoky haze",
        "Windy": "Windy", "Strong winds": "Strong winds", "Hail": "Hail",
        "Shower rain": "Rain shower", "Shower Rain": "Rain shower",
            "Patchy light rain": "Patchy light rain",
},
    "zh": {
        "Sunny": "晴", "Clear": "晴", "Partly cloudy": "多云",
        "Cloudy": "阴", "Overcast": "阴", "Mist": "薄雾",
        "Fog": "雾", "Freezing fog": "冻雾",
        "Light drizzle": "毛毛雨", "Patchy rain possible": "局部阵雨",
        "Patchy rain nearby": "附近有雨", "Patchy light drizzle": "局部毛毛雨",
        "Light rain": "小雨", "Moderate rain": "中雨",
        "Rain": "雨", "Freezing rain": "冻雨",
        "Rain shower": "阵雨", "Heavy rain shower": "强阵雨",
        "Snow": "雪", "Snow shower": "阵雪",
        "Thunderstorm": "雷阵雨", "Thunderstorm with hail": "雷阵雨并伴有冰雹",
        "Fair to cloudy": "晴间多云",
        "Moderate rain at times": "间或中雨",
        "Heavy rain": "大雨", "Heavy rain at times": "间或大雨",
        "Light rain shower": "小阵雨",
        "Moderate or heavy rain shower": "中到大阵雨",
        "Torrential rain shower": "暴雨",
        "Light freezing rain": "小冻雨",
        "Moderate or heavy freezing rain": "中到大冻雨",
        "Light sleet": "小雨夹雪", "Moderate or heavy sleet": "中到大雨夹雪",
        "Light sleet showers": "小阵雨夹雪",
        "Moderate or heavy sleet showers": "中到大阵雨夹雪",
        "Patchy sleet possible": "局部雨夹雪",
        "Freezing drizzle": "冻毛毛雨",
        "Heavy freezing drizzle": "大冻毛毛雨",
        "Patchy freezing drizzle possible": "局部冻毛毛雨",
        "Light snow": "小雪", "Moderate snow": "中雪",
        "Heavy snow": "大雪", "Patchy snow possible": "局部阵雪",
        "Patchy light snow": "局部小雪", "Patchy moderate snow": "局部中雪",
        "Patchy heavy snow": "局部大雪",
        "Light snow showers": "小阵雪",
        "Moderate or heavy snow showers": "中到大阵雪",
        "Blowing snow": "吹雪", "Blizzard": "暴雪",
        "Ice pellets": "冰粒",
        "Light showers of ice pellets": "小冰粒阵雨",
        "Moderate or heavy showers of ice pellets": "中到大冰粒阵雨",
        "Thundery outbreaks possible": "可能有雷暴",
        "Thundery outbreaks in nearby": "附近有雷暴",
        "Patchy light rain with thunder": "局部雷阵雨",
        "Moderate or heavy rain with thunder": "中到大雷雨",
        "Patchy light snow with thunder": "局部雷阵雪",
        "Moderate or heavy snow with thunder": "中到大雷雪",
        "Smoke": "烟", "Haze": "霾", "Smokey haze": "烟雾霾", "Smoky haze": "烟雾霾",
        "Windy": "大风", "Strong winds": "强风", "Hail": "冰雹",
    },
    "zh_TW": {
        "Sunny": "晴", "Clear": "晴", "Partly cloudy": "多雲",
        "Cloudy": "陰", "Overcast": "陰", "Mist": "薄霧",
        "Fog": "霧", "Freezing fog": "凍霧",
        "Light drizzle": "毛毛雨", "Patchy rain possible": "局部陣雨",
        "Patchy rain nearby": "附近有雨",
        "Light rain": "小雨", "Moderate rain": "中雨",
        "Rain": "雨", "Freezing rain": "冻雨",
        "Rain shower": "阵雨", "Heavy rain shower": "强阵雨",
        "Snow": "雪", "Snow shower": "阵雪",
        "Thunderstorm": "雷阵雨", "Thunderstorm with hail": "雷阵雨并伴有冰雹",
        "Fair to cloudy": "晴间多云",
        "Heavy rain": "大雨",
        "Light sleet": "小雨夾雪", "Moderate or heavy sleet": "中到大雨夾雪",
        "Patchy sleet possible": "局部雨夾雪",
        "Light snow": "小雪", "Moderate snow": "中雪",
        "Heavy snow": "大雪", "Patchy snow possible": "局部陣雪",
        "Blizzard": "暴雪",
        "Thundery outbreaks possible": "可能有雷暴",
        "Thundery outbreaks in nearby": "附近有雷暴",
        "Smoke": "煙", "Haze": "霾", "Smokey haze": "煙霧霾", "Smoky haze": "煙霧霾",
        "Windy": "大風", "Strong winds": "強風",
            "Patchy freezing drizzle possible": "局部可能有凍毛毛雨",
        "Blowing snow": "吹雪",
        "Hail": "冰雹",
        "Heavy rain at times": "間或大雨",
        "Patchy light drizzle": "局部小毛毛雨",
        "Patchy light rain": "局部小雨",
        "Patchy moderate snow": "局部中雪",
},
    "zh_TW": {
        "Sunny": "晴", "Clear": "晴", "Partly cloudy": "多雲",
        "Cloudy": "陰", "Overcast": "陰", "Mist": "薄霧",
        "Fog": "霧", "Freezing fog": "凍霧",
        "Light rain": "小雨", "Moderate rain": "中雨", "Heavy rain": "大雨",
        "Rain": "雨", "Freezing rain": "凍雨",
        "Rain shower": "陣雨", "Heavy rain shower": "強陣雨",
        "Light snow": "小雪", "Moderate snow": "中雪", "Heavy snow": "大雪",
        "Snow": "雪", "Snow shower": "陣雪",
        "Blizzard": "暴雪",
        "Thundery outbreaks possible": "可能有雷暴",
        "Thundery outbreaks in nearby": "附近有雷暴",
        "Thunderstorm": "雷陣雨", "Thunderstorm with hail": "雷陣雨並伴有冰雹",
        "Smoke": "煙", "Haze": "霾", "Smokey haze": "煙霧霾", "Smoky haze": "煙霧霾",
        "Windy": "大風", "Strong winds": "強風",
        "Fair to cloudy": "晴間多雲",
    },
    "ja": {
        "Sunny": "晴れ", "Clear": "晴れ", "Partly cloudy": "曇り時々晴れ",
        "Cloudy": "曇り", "Overcast": "曇り", "Mist": "霧",
        "Fog": "濃霧", "Freezing fog": "凍霧",
        "Light rain": "小雨", "Moderate rain": "雨", "Heavy rain": "大雨",
        "Light snow": "小雪", "Moderate snow": "雪", "Heavy snow": "大雪",
        "Blizzard": "吹雪", "Thundery outbreaks possible": "雷雨",
        "Thundery outbreaks in nearby": "付近で雷雨",
        "Smoke": "煙", "Haze": "靄", "Smokey haze": "煙霧", "Smoky haze": "煙霧",
        "Windy": "強風", "Strong winds": "暴風",
        "Rain": "雨", "Freezing rain": "凍雨",
        "Rain shower": "にわか雨", "Heavy rain shower": "強いにわか雨",
        "Snow": "雪", "Snow shower": "にわか雪",
        "Thunderstorm": "雷雨", "Thunderstorm with hail": "雷雨・雹を伴う",
        "Fair to cloudy": "晴れ時々曇り",
            "Patchy rain possible": "所により雨",
        "Patchy rain nearby": "付近で雨",
        "Patchy snow possible": "所により雪",
        "Patchy sleet possible": "所によりみぞれ",
        "Patchy freezing drizzle possible": "所により着氷性霧雨",
        "Blowing snow": "地吹雪",
        "Hail": "雹",
        "Heavy rain at times": "時々大雨",
        "Moderate or heavy sleet": "中程度以上のみぞれ",
        "Patchy light drizzle": "所により霧雨",
        "Patchy light rain": "所により小雨",
        "Patchy moderate snow": "所により中程度の雪",
},
    "ko": {
        "Sunny": "맑음", "Clear": "맑음", "Partly cloudy": "구름 조금",
        "Cloudy": "흐림", "Overcast": "흐림", "Mist": "안개",
        "Fog": "짙은 안개",
        "Light rain": "약한 비", "Moderate rain": "비", "Heavy rain": "강한 비",
        "Light snow": "약한 눈", "Moderate snow": "눈", "Heavy snow": "강한 눈",
        "Blizzard": "눈보라",
        "Thundery outbreaks possible": "뇌우",
        "Thundery outbreaks in nearby": "인근 뇌우",
        "Smoke": "연기", "Haze": "안개", "Smokey haze": "연무", "Smoky haze": "연무",
        "Windy": "강풍", "Strong winds": "폭풍",
        "Rain": "비", "Freezing rain": "진눈깨비",
        "Rain shower": "소나기", "Heavy rain shower": "강한 소나기",
        "Snow": "눈", "Snow shower": "소낙눈",
        "Thunderstorm": "뇌우", "Thunderstorm with hail": "우박 동반 뇌우",
        "Fair to cloudy": "구름 조금",
            "Freezing fog": "착빙 안개",
        "Patchy rain possible": "국지적 비 가능",
        "Patchy rain nearby": "인근에 비",
        "Patchy snow possible": "국지적 눈 가능",
        "Patchy sleet possible": "국지적 진눈깨비 가능",
        "Patchy freezing drizzle possible": "국지적 착빙 이슬비 가능",
        "Blowing snow": "날린 눈",
        "Hail": "우박",
        "Heavy rain at times": "때때로 큰 비",
        "Moderate or heavy sleet": "중간 이상 진눈깨비",
        "Patchy light drizzle": "국지적 가벼운 이슬비",
        "Patchy light rain": "국지적 가벼운 비",
        "Patchy moderate snow": "국지적 보통 눈",
},
    "es": {
        "Sunny": "Soleado", "Clear": "Despejado", "Partly cloudy": "Parcialmente nublado",
        "Cloudy": "Nublado", "Overcast": "Cubierto", "Mist": "Bruma",
        "Fog": "Niebla",
        "Light rain": "Lluvia ligera", "Moderate rain": "Lluvia moderada", "Heavy rain": "Lluvia fuerte",
        "Light snow": "Nieve ligera", "Moderate snow": "Nieve moderada", "Heavy snow": "Nieve fuerte",
        "Blizzard": "Ventisca",
        "Thundery outbreaks possible": "Tormenta eléctrica",
        "Thundery outbreaks in nearby": "Tormenta eléctrica cercana",
        "Smoke": "Humo", "Haze": "Neblina", "Smokey haze": "Neblina de humo", "Smoky haze": "Neblina de humo",
        "Windy": "Ventoso", "Strong winds": "Vientos fuertes",
        "Rain": "Lluvia", "Freezing rain": "Lluvia helada",
        "Rain shower": "Chubasco", "Heavy rain shower": "Chubasco fuerte",
        "Snow": "Nieve", "Snow shower": "Chubasco de nieve",
        "Thunderstorm": "Tormenta", "Thunderstorm with hail": "Tormenta con granizo",
        "Fair to cloudy": "Parcialmente soleado",
            "Freezing fog": "Niebla helada",
        "Patchy rain possible": "Posible lluvia irregular",
        "Patchy rain nearby": "Lluvia cercana",
        "Patchy snow possible": "Posible nieve irregular",
        "Patchy sleet possible": "Posible aguanieve irregular",
        "Patchy freezing drizzle possible": "Posible llovizna helada irregular",
        "Blowing snow": "Nieve arrastrada por el viento",
        "Hail": "Granizo",
        "Heavy rain at times": "Lluvia fuerte a ratos",
        "Moderate or heavy sleet": "Aguanieve moderada a fuerte",
        "Patchy light drizzle": "Llovizna ligera irregular",
        "Patchy light rain": "Lluvia ligera irregular",
        "Patchy moderate snow": "Nieve moderada irregular",
},
    "fr": {
        "Sunny": "Ensoleillé", "Clear": "Dégagé", "Partly cloudy": "Partiellement nuageux",
        "Cloudy": "Nuageux", "Overcast": "Couvert", "Mist": "Brume",
        "Fog": "Brouillard",
        "Light rain": "Pluie légère", "Moderate rain": "Pluie modérée", "Heavy rain": "Pluie forte",
        "Light snow": "Neige légère", "Moderate snow": "Neige modérée", "Heavy snow": "Neige forte",
        "Blizzard": "Blizzard",
        "Thundery outbreaks possible": "Orages possibles",
        "Thundery outbreaks in nearby": "Orages à proximité",
        "Smoke": "Fumée", "Haze": "Brume sèche", "Smokey haze": "Brume de fumée", "Smoky haze": "Brume de fumée",
        "Windy": "Venteux", "Strong winds": "Vents forts",
        "Rain": "Pluie", "Freezing rain": "Pluie verglaçante",
        "Rain shower": "Averse", "Heavy rain shower": "Forte averse",
        "Snow": "Neige", "Snow shower": "Averse de neige",
        "Thunderstorm": "Orage", "Thunderstorm with hail": "Orage de grêle",
        "Fair to cloudy": "Assez ensoleillé",
            "Freezing fog": "Brouillard givrant",
        "Patchy rain possible": "Pluie éparse possible",
        "Patchy rain nearby": "Pluie à proximité",
        "Patchy snow possible": "Neige éparse possible",
        "Patchy sleet possible": "Neige fondue éparse possible",
        "Patchy freezing drizzle possible": "Bruine givrante éparse possible",
        "Blowing snow": "Poudrerie",
        "Hail": "Grêle",
        "Heavy rain at times": "Forte pluie par moments",
        "Moderate or heavy sleet": "Neige fondue modérée à forte",
        "Patchy light drizzle": "Bruine légère éparse",
        "Patchy light rain": "Pluie légère éparse",
        "Patchy moderate snow": "Neige modérée éparse",
},
    "de": {
        "Sunny": "Sonnig", "Clear": "Klar", "Partly cloudy": "Teilweise bewölkt",
        "Cloudy": "Bewölkt", "Overcast": "Bedeckt", "Mist": "Dunst",
        "Fog": "Nebel",
        "Light rain": "Leichter Regen", "Moderate rain": "Mäßiger Regen", "Heavy rain": "Starker Regen",
        "Light snow": "Leichter Schnee", "Moderate snow": "Mäßiger Schnee", "Heavy snow": "Starker Schnee",
        "Blizzard": "Schneesturm",
        "Thundery outbreaks possible": "Gewitter möglich",
        "Thundery outbreaks in nearby": "Gewitter in der Nähe",
        "Smoke": "Rauch", "Haze": "Dunst", "Smokey haze": "Rauchdunst", "Smoky haze": "Rauchdunst",
        "Windy": "Windig", "Strong winds": "Starke Winde",
        "Rain": "Regen", "Freezing rain": "Gefrierender Regen",
        "Rain shower": "Regenschauer", "Heavy rain shower": "Starker Regenschauer",
        "Snow": "Schnee", "Snow shower": "Schneeschauer",
        "Thunderstorm": "Gewitter", "Thunderstorm with hail": "Gewitter mit Hagel",
        "Fair to cloudy": "Heiter bis bewölkt",
            "Freezing fog": "Gefrierender Nebel",
        "Patchy rain possible": "Vereinzelt Regen möglich",
        "Patchy rain nearby": "Regen in der Nähe",
        "Patchy snow possible": "Vereinzelt Schnee möglich",
        "Patchy sleet possible": "Vereinzelt Schneeregen möglich",
        "Patchy freezing drizzle possible": "Vereinzelt gefrierender Sprühregen möglich",
        "Blowing snow": "Schneefegen",
        "Hail": "Hagel",
        "Heavy rain at times": "Zeitweise starker Regen",
        "Moderate or heavy sleet": "Mäßiger bis starker Schneeregen",
        "Patchy light drizzle": "Vereinzelt leichter Sprühregen",
        "Patchy light rain": "Vereinzelt leichter Regen",
        "Patchy moderate snow": "Vereinzelt mäßiger Schnee",
},
}

# 未覆盖的英文描述保留原文（translate_weather_text 末尾已处理）


# ---- 中文→英文反向索引（用于高德/和风/Open-Meteo 的中文天气翻译） ----
_CN_TO_EN = {}
for _en_key, _cn_val in _WEATHER_TRANSLATIONS.get("zh", {}).items():
    if _cn_val:
        _CN_TO_EN[_cn_val] = _en_key

# 手动补充 Open-Meteo _WEATHERCODE_MAP 中的特殊格式
_CN_TO_EN["毛毛雨/细雨"] = "Light drizzle"
_CN_TO_EN["冻雨"] = "Freezing rain"
_CN_TO_EN["雷阵雨并伴有冰雹"] = "Thunderstorm with hail"
_CN_TO_EN["强阵雨"] = "Heavy rain shower"


def translate_weather_text_cn(weather_cn: str, language_code: str = None) -> str:
    """
    将中文天气描述翻译为目标语言（高德/和风/Open-Meteo 等中文 API）
    :param weather_cn: 中文天气描述（如 "晴"、"多云"、"小雨"）
    :param language_code: 目标语言代码，None 则使用系统语言
    :return: 翻译后的天气描述
    """
    if not weather_cn:
        return weather_cn

    # 取第一个天气（如 "晴转多云" -> "晴"）
    first = weather_cn.split('转')[0] if '转' in weather_cn else weather_cn

    # 中文→英文→目标语言
    en_key = _CN_TO_EN.get(first)
    if en_key:
        return translate_weather_text(en_key, language_code)
    # 中文反查失败（如和风天气对国际城市返回英文 "Shower rain"），走英文翻译
    return translate_weather_text(first, language_code)


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
        from PyQt6.QtCore import QSettings
        language_code = QSettings("MyDesktopApp", "WeatherSettings").value("language", "")
        if not language_code:
            from PyQt6.QtCore import QLocale
            language_code = QLocale.system().name()

    # Try full code first (e.g. "zh_TW"), then fall back to prefix (e.g. "zh")
    translations = _WEATHER_TRANSLATIONS.get(language_code)
    if translations is None:
        lang_key = language_code.split("_")[0] if "_" in language_code else language_code
        translations = _WEATHER_TRANSLATIONS.get(lang_key)
    if not translations:
        return weather_en

    # 精确匹配优先
    result = translations.get(weather_en)
    if result is not None:
        return result
    # 大小写不敏感回退
    weather_lower = weather_en.lower()
    for key, value in translations.items():
        if key.lower() == weather_lower:
            return value
    # 通过英文表规范化（处理 "Shower rain" → "Rain shower" 等别名）
    en_translations = _WEATHER_TRANSLATIONS.get("en", {})
    canonical = en_translations.get(weather_en)
    if canonical is None:
        for key, value in en_translations.items():
            if key.lower() == weather_lower:
                canonical = value
                break
    if canonical and canonical != weather_en:
        # 用规范化后的键重试目标语言
        result = translations.get(canonical)
        if result is not None:
            return result
    return weather_en
