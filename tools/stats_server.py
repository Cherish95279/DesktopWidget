#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DesktopWidget 统计服务器 v2
运行: python3 stats_server.py
新增: 语言/屏幕分辨率/槽位配置/运行时长/国家分布 + Chart.js 图表
"""

import json, os
from datetime import datetime, date, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = 8080
DATA_FILE = "data.json"
DAYS_TO_KEEP = 30

COUNTRY_NAMES_ZH = {
    "CN": "中国", "DE": "德国", "US": "美国", "FR": "法国",
    "JP": "日本", "KR": "韩国", "ES": "西班牙", "GB": "英国",
    "IT": "意大利", "CA": "加拿大", "AU": "澳大利亚", "BR": "巴西",
    "IN": "印度", "RU": "俄罗斯", "NL": "荷兰", "SE": "瑞典",
    "TW": "台湾", "HK": "香港", "SG": "新加坡", "TH": "泰国",
    "VN": "越南", "ID": "印度尼西亚", "MY": "马来西亚", "PH": "菲律宾",
    "PL": "波兰", "TR": "土耳其", "AR": "阿根廷", "MX": "墨西哥",
    "BE": "比利时", "CH": "瑞士", "AT": "奥地利", "NO": "挪威",
    "DK": "丹麦", "FI": "芬兰", "PT": "葡萄牙", "CZ": "捷克",
}

LANG_LABELS = {
    "zh_CN": "中文简体", "zh_TW": "中文繁体", "zh": "中文",
    "en": "English", "de": "Deutsch", "fr": "Fran\u00e7ais",
    "ja": "\u65e5\u672c\u8a9e", "ko": "\ud55c\uad6d\uc5b4",
    "es": "Espa\u00f1ol", "auto": "\u81ea\u52a8\u68c0\u6d4b",
}

SLOT_LABELS = {
    "weather": "\u5929\u6c14", "netspeed": "\u7f51\u901f", "cpu": "CPU",
    "gpu": "GPU", "memory": "\u5185\u5b58", "disk": "\u786c\u76d8",
    "ip": "IP", "date": "\u65e5\u671f", "lunar": "\u519c\u5386",
    "solar_term": "\u8282\u6c14", "time": "\u65f6\u95f4",
}

def lang_to_cc(lang):
    if lang in ("zh_CN", "zh"):
        return "CN"
    if lang == "zh_TW":
        return "TW"
    if lang == "de":
        return "DE"
    if lang == "fr":
        return "FR"
    if lang == "ja":
        return "JP"
    if lang == "ko":
        return "KR"
    if lang == "es":
        return "ES"
    if lang == "en":
        return "US"
    return "other"


class StatsHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/ping":
            self._handle_ping(query)
        elif path == "/stats":
            self._handle_stats()
        else:
            self._send_response(404, {"error": "Not Found"})

    def _handle_ping(self, query):
        uuid = query.get("uuid", [""])[0]
        version = query.get("version", ["unknown"])[0]
        os_info = query.get("os", ["unknown"])[0]
        autostart = query.get("autostart", ["unknown"])[0]
        theme = query.get("theme", ["unknown"])[0]
        weather = query.get("weather", ["unknown"])[0]
        update = query.get("update", ["unknown"])[0]
        lang = query.get("lang", ["unknown"])[0]
        screen = query.get("screen", ["unknown"])[0]
        slots = query.get("slots", ["unknown"])[0]

        if not uuid:
            self._send_response(400, {"error": "Missing uuid"})
            return

        data = self._load_data()
        today = date.today().isoformat()

        if uuid not in data["all_time_devices"]:
            data["all_time_devices"].append(uuid)

        if today not in data["daily"]:
            data["daily"][today] = {"devices": {}}

        prev = data["daily"][today]["devices"].get(uuid, {})
        data["daily"][today]["devices"][uuid] = {
            "version": version,
            "os": os_info,
            "autostart": autostart,
            "theme": theme,
            "weather": weather,
            "update": update,
            "lang": lang,
            "screen": screen,
            "slots": slots,
            "last_seen": datetime.now().strftime("%H:%M:%S"),
            "heartbeats": prev.get("heartbeats", 0) + 1,
        }

        self._clean_old_data(data)
        self._save_data(data)
        self._send_response(200, {
            "status": "ok",
            "today_total": len(data["daily"][today]["devices"]),
            "all_time_total": len(data["all_time_devices"])
        })

    def _handle_stats(self):
        data = self._load_data()
        html = self._render_html(data)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"all_time_devices": [], "daily": {}}

    def _save_data(self, data):
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)

    def _clean_old_data(self, data):
        cutoff = (date.today() - timedelta(days=DAYS_TO_KEEP)).isoformat()
        data["daily"] = {k: v for k, v in data["daily"].items() if k >= cutoff}

    def _render_html(self, data):
        today = date.today().isoformat()
        today_devices = data["daily"].get(today, {}).get("devices", {})
        all_time = len(data["all_time_devices"])
        today_count = len(today_devices)

        os_stats = {}
        autostart_on = 0
        autostart_off = 0
        theme_stats = {}
        weather_stats = {"success": 0, "failed": 0, "idle": 0, "unknown": 0}
        update_stats = {"success": 0, "no_update": 0, "failed": 0, "idle": 0, "unknown": 0}
        lang_stats = {}
        screen_stats = {}
        slot_stats_raw = {}
        total_heartbeats = 0

        for info in today_devices.values():
            os_val = info.get("os", "unknown")
            os_stats[os_val] = os_stats.get(os_val, 0) + 1

            if info.get("autostart") == "1":
                autostart_on += 1
            else:
                autostart_off += 1

            theme_val = info.get("theme", "unknown")
            theme_stats[theme_val] = theme_stats.get(theme_val, 0) + 1

            w = info.get("weather", "unknown")
            weather_stats[w if w in weather_stats else "unknown"] += 1

            u = info.get("update", "unknown")
            update_stats[u if u in update_stats else "unknown"] += 1

            lang_val = info.get("lang", "unknown")
            lang_label = LANG_LABELS.get(lang_val, lang_val)
            lang_stats[lang_label] = lang_stats.get(lang_label, 0) + 1

            screen_val = info.get("screen", "unknown")
            screen_stats[screen_val] = screen_stats.get(screen_val, 0) + 1

            slots_val = info.get("slots", "")
            if slots_val and slots_val != "unknown":
                for s in slots_val.split(","):
                    if s and s != "empty":
                        label = SLOT_LABELS.get(s, s)
                        slot_stats_raw[label] = slot_stats_raw.get(label, 0) + 1

            total_heartbeats += info.get("heartbeats", 0)

        avg_runtime_min = (total_heartbeats * 30 / today_count) if today_count > 0 else 0
        if avg_runtime_min >= 60:
            avg_runtime_str = f"{avg_runtime_min / 60:.1f}h"
        else:
            avg_runtime_str = f"{avg_runtime_min:.0f}min"

        trend_days = []
        trend_values = []
        for i in range(29, -1, -1):
            d = (date.today() - timedelta(days=i)).isoformat()
            count = len(data["daily"].get(d, {}).get("devices", {}))
            trend_days.append(d[5:])
            trend_values.append(count)

        country_stats = {}
        for info in today_devices.values():
            lang = info.get("lang", "unknown")
            cc = lang_to_cc(lang)
            country_stats[cc] = country_stats.get(cc, 0) + 1

        def render_items(stats_dict):
            items = sorted(stats_dict.items(), key=lambda x: -x[1])
            return "".join(
                f'<div class="stat-item"><span class="key">{k}</span><span class="val">{v}</span></div>'
                for k, v in items
            )

        def render_expandable(stats_dict, card_id, top=5):
            items = sorted(stats_dict.items(), key=lambda x: -x[1])
            shown = items[:top]
            hidden = items[top:]
            html = "".join(
                f'<div class="stat-item"><span class="key">{k}</span><span class="val">{v}</span></div>'
                for k, v in shown
            )
            if hidden:
                html += '<div class="stat-body-hidden">'
                html += "".join(
                    f'<div class="stat-item"><span class="key">{k}</span><span class="val">{v}</span></div>'
                    for k, v in hidden
                )
                html += '</div>'
                html += f'<div class="more" onclick="toggleDetail(\'{card_id}\')">... 展开全部 ({len(items)}项) ▼</div>'
            return html

        chart_labels = json.dumps(trend_days)
        chart_data = json.dumps(trend_values)

        country_sorted = sorted(country_stats.items(), key=lambda x: -x[1])[:8]
        country_labels = json.dumps([COUNTRY_NAMES_ZH.get(c[0], c[0]) for c in country_sorted])
        country_data = json.dumps([c[1] for c in country_sorted])
        colors = ["#1d9bf0","#f91880","#00ba7c","#ff7a00","#8b5cf6","#ef4444","#facc15","#536471"]
        country_colors = json.dumps(colors[:len(country_sorted)])

        week_new = sum(1 for uid in data.get("all_time_devices", [])
                       if any(uid in data["daily"].get(
                           (date.today() - timedelta(days=i)).isoformat(), {}
                       ).get("devices", {}) for i in range(7)))

        runtime_buckets = {"< 30min": 0, "30min - 2h": 0, "2h - 6h": 0, "> 6h": 0}
        for v in today_devices.values():
            hb = v.get("heartbeats", 0)
            if hb <= 1:
                runtime_buckets["< 30min"] += 1
            elif hb <= 4:
                runtime_buckets["30min - 2h"] += 1
            elif hb <= 12:
                runtime_buckets["2h - 6h"] += 1
            else:
                runtime_buckets["> 6h"] += 1

        return HTML_TEMPLATE.format(
            all_time=all_time,
            today_count=today_count,
            autostart_on=autostart_on,
            autostart_off=autostart_off,
            week_new=week_new,
            avg_runtime_str=avg_runtime_str,
            os_items=render_items(os_stats),
            lang_items=render_expandable(lang_stats, "langCard"),
            theme_items=render_items(theme_stats),
            weather_items=render_items(weather_stats),
            screen_items=render_expandable(screen_stats, "resCard"),
            slot_items=render_expandable(slot_stats_raw, "slotCard", top=4),
            runtime_items="".join(
                f'<div class="stat-item"><span class="key">{k}</span><span class="val">{v}</span></div>'
                for k, v in runtime_buckets.items()
            ),
            chart_labels=chart_labels,
            chart_data=chart_data,
            country_labels=country_labels,
            country_data=country_data,
            country_colors=country_colors,
            days=DAYS_TO_KEEP,
        )

    def _send_response(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DesktopWidget 统计面板</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
:root {{ --bg:#0f1419;--card:#1a1f26;--text:#e7e9ea;--sub:#8899a6;--muted:#536471;--accent:#1d9bf0;--border:#2f3336;--hover:#1e2732; }}
[data-theme="light"] {{ --bg:#f5f7fa;--card:#fff;--text:#1a1a2e;--sub:#666;--muted:#999;--accent:#1677ff;--border:#e8e8e8;--hover:#f0f5ff; }}
* {{ margin:0;padding:0;box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);max-width:1100px;margin:20px auto;padding:0 16px; }}
.header {{ display:flex;justify-content:space-between;align-items:center;margin-bottom:16px; }}
h1 {{ font-size:22px; }}
.theme-btn {{ background:var(--card);border:1px solid var(--border);color:var(--text);font-size:18px;padding:6px 12px;border-radius:8px;cursor:pointer; }}
.theme-btn:hover {{ background:var(--hover); }}
.top-row {{ display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px; }}
.big-card {{ background:var(--card);border-radius:12px;padding:18px;text-align:center;border:1px solid var(--border); }}
.big-card .label {{ font-size:13px;color:var(--sub);margin-bottom:4px; }}
.big-card .value {{ font-size:32px;font-weight:700;color:var(--accent); }}
.big-card .sub {{ font-size:12px;color:var(--muted);margin-top:2px; }}
.chart-row {{ display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px; }}
.chart-card {{ background:var(--card);border-radius:12px;padding:16px;border:1px solid var(--border); }}
.chart-card h3 {{ font-size:14px;color:var(--sub);margin-bottom:10px;text-align:center; }}
.chart-card canvas {{ max-height:220px; }}
.stat-grid {{ display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px; }}
.stat-card {{ background:var(--card);border-radius:12px;padding:14px 16px;border:1px solid var(--border); }}
.stat-card h3 {{ font-size:13px;color:var(--sub);margin-bottom:8px;display:flex;justify-content:space-between;align-items:center; }}
.stat-item {{ display:flex;justify-content:space-between;font-size:13px;padding:3px 0; }}
.stat-item .key {{ color:var(--text); }}
.stat-item .val {{ color:var(--accent);font-weight:600; }}
.stat-body-hidden {{ max-height:0;overflow:hidden;transition:max-height .3s; }}
.stat-body-hidden.show {{ max-height:600px; }}
.more {{ text-align:center;color:var(--accent);font-size:12px;padding:4px 0;cursor:pointer; }}
.more:hover {{ text-decoration:underline; }}
.footer {{ text-align:center;color:var(--muted);font-size:11px;margin-top:16px;padding-bottom:20px; }}
</style>
</head>
<body>
<div class="header">
    <h1>DesktopWidget 统计面板</h1>
    <button class="theme-btn" onclick="toggleTheme()" id="themeBtn">&#x2600;&#xFE0F;</button>
</div>
<div class="top-row">
    <div class="big-card"><div class="label">累计设备</div><div class="value">{all_time}</div></div>
    <div class="big-card"><div class="label">今日活跃</div><div class="value">{today_count}</div><div class="sub">平均运行 {avg_runtime_str}</div></div>
    <div class="big-card"><div class="label">开机自启</div><div class="value">{autostart_on}</div><div class="sub">开启 {autostart_on} · 关闭 {autostart_off}</div></div>
    <div class="big-card"><div class="label">本周新增</div><div class="value">{week_new}</div></div>
</div>
<div class="chart-row">
    <div class="chart-card">
        <h3>近30天活跃趋势</h3>
        <canvas id="trendChart"></canvas>
    </div>
    <div class="chart-card">
        <h3>国家 / 地区分布</h3>
        <canvas id="countryChart"></canvas>
    </div>
</div>
<div class="stat-grid">
    <div class="stat-card"><h3>操作系统</h3>{os_items}</div>
    <div class="stat-card" id="langCard"><h3>语言分布</h3>{lang_items}</div>
    <div class="stat-card"><h3>主题分布</h3>{theme_items}</div>
    <div class="stat-card"><h3>天气状态</h3>{weather_items}</div>
    <div class="stat-card" id="resCard"><h3>屏幕分辨率</h3>{screen_items}</div>
    <div class="stat-card" id="slotCard"><h3>显示槽位配置</h3>{slot_items}</div>
    <div class="stat-card"><h3>运行时长分布</h3>{runtime_items}</div>
</div>
<div class="footer">数据保留最近 {days} 天 · 匿名统计 · 仅自己可见 · 国家依据语言推断</div>
<script>
function toggleTheme() {{
    var h = document.documentElement, b = document.getElementById('themeBtn');
    if (h.getAttribute('data-theme') === 'dark') {{ h.setAttribute('data-theme','light'); b.innerHTML='&#x1F319;'; }}
    else {{ h.setAttribute('data-theme','dark'); b.innerHTML='&#x2600;&#xFE0F;'; }}
}}
function toggleDetail(id) {{
    var card = document.getElementById(id);
    var hidden = card.querySelector('.stat-body-hidden');
    var more = card.querySelector('.more');
    if (hidden) {{ hidden.classList.toggle('show'); more.style.display = hidden.classList.contains('show') ? 'none' : ''; }}
}}
new Chart(document.getElementById('trendChart'), {{
    type:'line',
    data:{{ labels:{chart_labels}, datasets:[{{ data:{chart_data}, borderColor:'#1d9bf0', backgroundColor:'rgba(29,155,240,0.1)', fill:true, tension:.3, pointRadius:3, pointBackgroundColor:'#1d9bf0' }}] }},
    options:{{ responsive:true, maintainAspectRatio:false, plugins:{{ legend:{{ display:false }} }}, scales:{{ x:{{ ticks:{{ font:{{ size:10 }} }} }}, y:{{ ticks:{{ font:{{ size:10 }} }}, beginAtZero:true }} }} }}
}});
new Chart(document.getElementById('countryChart'), {{
    type:'bar',
    data:{{ labels:{country_labels}, datasets:[{{ data:{country_data}, backgroundColor:{country_colors} }}] }},
    options:{{ responsive:true, maintainAspectRatio:false, plugins:{{ legend:{{ display:false }} }}, scales:{{ x:{{ ticks:{{ font:{{ size:10 }} }}, grid:{{ display:false }} }}, y:{{ ticks:{{ font:{{ size:10 }} }}, beginAtZero:true }} }} }}
}});
</script>
</body>
</html>'''


def run_server():
    server = HTTPServer(("0.0.0.0", PORT), StatsHandler)
    print(f"Stats server v2 started on port {PORT}")
    print(f"Stats page: http://0.0.0.0:{PORT}/stats")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
