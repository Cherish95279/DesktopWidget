from datetime import datetime

# ---------- 节气数据 ----------
TERM_DATA = {
    2026: [
        (1, 5, "小寒"), (1, 20, "大寒"), (2, 4, "立春"), (2, 19, "雨水"),
        (3, 6, "惊蛰"), (3, 21, "春分"), (4, 5, "清明"), (4, 20, "谷雨"),
        (5, 5, "立夏"), (5, 21, "小满"), (6, 5, "芒种"), (6, 21, "夏至"),
        (7, 7, "小暑"), (7, 23, "大暑"), (8, 7, "立秋"), (8, 23, "处暑"),
        (9, 7, "白露"), (9, 23, "秋分"), (10, 8, "寒露"), (10, 23, "霜降"),
        (11, 7, "立冬"), (11, 22, "小雪"), (12, 7, "大雪"), (12, 22, "冬至")
    ],
    2027: [
        (1, 5, "小寒"), (1, 20, "大寒"), (2, 4, "立春"), (2, 19, "雨水"),
        (3, 6, "惊蛰"), (3, 21, "春分"), (4, 5, "清明"), (4, 20, "谷雨"),
        (5, 6, "立夏"), (5, 21, "小满"), (6, 6, "芒种"), (6, 21, "夏至"),
        (7, 7, "小暑"), (7, 23, "大暑"), (8, 7, "立秋"), (8, 23, "处暑"),
        (9, 8, "白露"), (9, 23, "秋分"), (10, 8, "寒露"), (10, 24, "霜降"),
        (11, 7, "立冬"), (11, 22, "小雪"), (12, 7, "大雪"), (12, 22, "冬至")
    ],
    2028: [
        (1, 6, "小寒"), (1, 21, "大寒"), (2, 4, "立春"), (2, 19, "雨水"),
        (3, 5, "惊蛰"), (3, 20, "春分"), (4, 4, "清明"), (4, 20, "谷雨"),
        (5, 5, "立夏"), (5, 21, "小满"), (6, 5, "芒种"), (6, 21, "夏至"),
        (7, 7, "小暑"), (7, 22, "大暑"), (8, 7, "立秋"), (8, 22, "处暑"),
        (9, 7, "白露"), (9, 22, "秋分"), (10, 8, "寒露"), (10, 23, "霜降"),
        (11, 7, "立冬"), (11, 22, "小雪"), (12, 7, "大雪"), (12, 21, "冬至")
    ],
    2029: [
        (1, 5, "小寒"), (1, 20, "大寒"), (2, 4, "立春"), (2, 19, "雨水"),
        (3, 5, "惊蛰"), (3, 20, "春分"), (4, 4, "清明"), (4, 20, "谷雨"),
        (5, 5, "立夏"), (5, 21, "小满"), (6, 5, "芒种"), (6, 21, "夏至"),
        (7, 7, "小暑"), (7, 22, "大暑"), (8, 7, "立秋"), (8, 23, "处暑"),
        (9, 7, "白露"), (9, 23, "秋分"), (10, 8, "寒露"), (10, 23, "霜降"),
        (11, 7, "立冬"), (11, 22, "小雪"), (12, 7, "大雪"), (12, 21, "冬至")
    ]
}


# ---------- 节气多语言翻译 ----------
# en: WMO/主流媒体通行标准 | ja/ko: 当地标准 | es/fr/de: 拼音
_TERM_TRANSLATIONS = {
    "zh_CN": {
        "小寒": "小寒", "大寒": "大寒", "立春": "立春", "雨水": "雨水",
        "惊蛰": "惊蛰", "春分": "春分", "清明": "清明", "谷雨": "谷雨",
        "立夏": "立夏", "小满": "小满", "芒种": "芒种", "夏至": "夏至",
        "小暑": "小暑", "大暑": "大暑", "立秋": "立秋", "处暑": "处暑",
        "白露": "白露", "秋分": "秋分", "寒露": "寒露", "霜降": "霜降",
        "立冬": "立冬", "小雪": "小雪", "大雪": "大雪", "冬至": "冬至",
    },
    "zh_TW": {
        "小寒": "小寒", "大寒": "大寒", "立春": "立春", "雨水": "雨水",
        "惊蛰": "驚蟄", "春分": "春分", "清明": "清明", "谷雨": "穀雨",
        "立夏": "立夏", "小满": "小滿", "芒种": "芒種", "夏至": "夏至",
        "小暑": "小暑", "大暑": "大暑", "立秋": "立秋", "处暑": "處暑",
        "白露": "白露", "秋分": "秋分", "寒露": "寒露", "霜降": "霜降",
        "立冬": "立冬", "小雪": "小雪", "大雪": "大雪", "冬至": "冬至",
    },
    "en": {
        "小寒": "Minor Cold", "大寒": "Major Cold", "立春": "Start of Spring", "雨水": "Rain Water",
        "惊蛰": "Awakening of Insects", "春分": "Spring Equinox", "清明": "Pure Brightness", "谷雨": "Grain Rain",
        "立夏": "Start of Summer", "小满": "Grain Buds", "芒种": "Grain in Ear", "夏至": "Summer Solstice",
        "小暑": "Minor Heat", "大暑": "Major Heat", "立秋": "Start of Autumn", "处暑": "End of Heat",
        "白露": "White Dew", "秋分": "Autumn Equinox", "寒露": "Cold Dew", "霜降": "First Frost",
        "立冬": "Start of Winter", "小雪": "Minor Snow", "大雪": "Major Snow", "冬至": "Winter Solstice",
    },
    "ja": {
        "小寒": "小寒", "大寒": "大寒", "立春": "立春", "雨水": "雨水",
        "惊蛰": "啓蟄", "春分": "春分", "清明": "清明", "谷雨": "穀雨",
        "立夏": "立夏", "小满": "小満", "芒种": "芒種", "夏至": "夏至",
        "小暑": "小暑", "大暑": "大暑", "立秋": "立秋", "处暑": "処暑",
        "白露": "白露", "秋分": "秋分", "寒露": "寒露", "霜降": "霜降",
        "立冬": "立冬", "小雪": "小雪", "大雪": "大雪", "冬至": "冬至",
    },
    "ko": {
        "小寒": "소한", "大寒": "대한", "立春": "입춘", "雨水": "우수",
        "惊蛰": "경칩", "春分": "춘분", "清明": "청명", "谷雨": "곡우",
        "立夏": "입하", "小满": "소만", "芒种": "망종", "夏至": "하지",
        "小暑": "소서", "大暑": "대서", "立秋": "입추", "处暑": "처서",
        "白露": "백로", "秋分": "추분", "寒露": "한로", "霜降": "상강",
        "立冬": "입동", "小雪": "소설", "大雪": "대설", "冬至": "동지",
    },
    "es": {
        "小寒": "Xiaohan", "大寒": "Dahan", "立春": "Lichun", "雨水": "Yushui",
        "惊蛰": "Jingzhe", "春分": "Chunfen", "清明": "Qingming", "谷雨": "Guyu",
        "立夏": "Lixia", "小满": "Xiaoman", "芒种": "Mangzhong", "夏至": "Xiazhi",
        "小暑": "Xiaoshu", "大暑": "Dashu", "立秋": "Liqiu", "处暑": "Chushu",
        "白露": "Bailu", "秋分": "Qiufen", "寒露": "Hanlu", "霜降": "Shuangjiang",
        "立冬": "Lidong", "小雪": "Xiaoxue", "大雪": "Daxue", "冬至": "Dongzhi",
    },
    "fr": {
        "小寒": "Xiaohan", "大寒": "Dahan", "立春": "Lichun", "雨水": "Yushui",
        "惊蛰": "Jingzhe", "春分": "Chunfen", "清明": "Qingming", "谷雨": "Guyu",
        "立夏": "Lixia", "小满": "Xiaoman", "芒种": "Mangzhong", "夏至": "Xiazhi",
        "小暑": "Xiaoshu", "大暑": "Dashu", "立秋": "Liqiu", "处暑": "Chushu",
        "白露": "Bailu", "秋分": "Qiufen", "寒露": "Hanlu", "霜降": "Shuangjiang",
        "立冬": "Lidong", "小雪": "Xiaoxue", "大雪": "Daxue", "冬至": "Dongzhi",
    },
    "de": {
        "小寒": "Xiaohan", "大寒": "Dahan", "立春": "Lichun", "雨水": "Yushui",
        "惊蛰": "Jingzhe", "春分": "Chunfen", "清明": "Qingming", "谷雨": "Guyu",
        "立夏": "Lixia", "小满": "Xiaoman", "芒种": "Mangzhong", "夏至": "Xiazhi",
        "小暑": "Xiaoshu", "大暑": "Dashu", "立秋": "Liqiu", "处暑": "Chushu",
        "白露": "Bailu", "秋分": "Qiufen", "寒露": "Hanlu", "霜降": "Shuangjiang",
        "立冬": "Lidong", "小雪": "Xiaoxue", "大雪": "Daxue", "冬至": "Dongzhi",
    },
}


def translate_term(cn_name: str, language_code: str = None) -> str:
    """将节气中文名翻译为目标语言"""
    if language_code is None:
        from PyQt6.QtCore import QSettings
        language_code = QSettings("MyDesktopApp", "WeatherSettings").value("language", "")
        if not language_code:
            language_code = "zh_CN"
    # Try full code first, then prefix
    trans = _TERM_TRANSLATIONS.get(language_code)
    if trans is None:
        prefix = language_code.split("_")[0] if "_" in language_code else language_code
        trans = _TERM_TRANSLATIONS.get(prefix)
    if trans is None:
        trans = _TERM_TRANSLATIONS.get("zh_CN", {})
    return trans.get(cn_name, cn_name)

def get_next_term_info(year, month, day):
    all_terms = []
    for y, terms in TERM_DATA.items():
        for m, d, name in terms:
            all_terms.append((y, m, d, name))
    all_terms.sort(key=lambda x: (x[0], x[1], x[2]))
    cur_date = datetime(year, month, day)
    cur_ymd = (year, month, day)
    future_terms = []
    for y, m, d, name in all_terms:
        if (y, m, d) >= cur_ymd:
            future_terms.append((y, m, d, name))
    if not future_terms:
        next_year = year + 1
        if next_year in TERM_DATA:
            first_term = TERM_DATA[next_year][0]
            next_date = datetime(next_year, first_term[0], first_term[1])
            days = (next_date - cur_date).days
            return (None, first_term[2], days)
        else:
            return (None, None, None)
    y0, m0, d0, name0 = future_terms[0]
    if (y0, m0, d0) == cur_ymd:
        return (name0, None, None)
    else:
        next_date = datetime(y0, m0, d0)
        days = (next_date - cur_date).days
        return (None, name0, days)