# ---------- 常量定义 ----------
AMAP_KEY = "c348525fc6252c6a54b8c72fa5017a45"
ORIG_W, ORIG_H = 400, 297
CENTER_X, CENTER_Y = 201, 144
VERSION = "v1.2.5"

# GitHub 仓库信息
GITHUB_REPO = "Cherish95279/DesktopWidget"

# ---------- 布局默认值 ----------
DEFAULT_LAYOUT = {
    "slot_1": "ip",
    "slot_2": "netspeed",
    "slot_3": "resolution",
    "slot_4": "date",
    "slot_5": "weather",
    "slot_6": "gpu",
    "slot_7": "memory",
    "slot_8": "lunar"
}

# ---------- 主题配置 ----------
DEFAULT_THEME = {
    "opacity": 100,
    "color": "#a8c7dc",
}
THEME_PRESETS = [
    {"name": "经典暗色", "color": "#1c344d"},
    {"name": "浅色主题", "color": "#f0f0f0"},
    {"name": "浅蓝灰", "color": "#a8c7dc"},
]

# ===== 新增：主题名称常量 =====
DEFAULT_THEME_NAME = "默认主题"
THEME_NAMES = {
    "default": "默认主题",
    "skins_01": "竹林",
}