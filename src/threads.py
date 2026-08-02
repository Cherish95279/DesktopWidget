import socket
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QSettings
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import certifi
from .utils import translate_weather_text, translate_weather_text_cn
import urllib.request
import urllib.error
import gzip
import json
import psutil
from .constants import AMAP_KEY


# ---------- 扫描 HA 服务器 ----------
class ServerScanner(QThread):
    ip_found = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._stopped = False

    def stop(self):
        self._stopped = True
        self.wait(3000)

    def run(self):
        local_ip = "192.168.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
        except (OSError, socket.error):
            pass
        subnet = ".".join(local_ip.split('.')[:-1]) + "."
        found = None
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(self.check_port, subnet + str(i)): i for i in range(1, 255)}
            for f in as_completed(futures):
                if self._stopped:
                    break
                res = f.result()
                if res:
                    found = res
                    break
        if not self._stopped:
            self.ip_found.emit(found if found else "192.168.0.135")

    def check_port(self, ip):
        if self._stopped:
            return None
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.15)
                if s.connect_ex((ip, 8123)) == 0:
                    return ip
        except (OSError, socket.error):
            return None


# ---------- 天气线程（增加经纬度支持） ----------
class WeatherThread(QThread):
    data_updated = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, api_url, api_key, refresh_minutes):
        super().__init__()
        self.api_url = api_url or ""
        self.api_key = api_key or ""
        self.refresh_minutes = max(1, refresh_minutes)
        self._stopped = False
        self.last_status = "idle"

    _WEATHERCODE_MAP = {
        0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
        45: "雾", 48: "雾",
        51: "毛毛雨/细雨", 53: "毛毛雨/细雨", 55: "雨",
        56: "冻雨", 57: "冻雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        66: "冻雨", 67: "冻雨",
        71: "小雪", 73: "中雪", 75: "大雪", 77: "雪",
        80: "阵雨", 81: "强阵雨", 82: "强阵雨",
        85: "阵雪", 86: "阵雪",
        95: "雷阵雨", 96: "雷阵雨并伴有冰雹", 99: "雷阵雨并伴有冰雹"
    }

    @staticmethod
    def _wind_direction(degrees):
        dirs = ["北", "北东北", "东北", "东东北", "东",
                "东东南", "东南", "南东南", "南",
                "南南西", "西南", "西南西", "西",
                "西西北", "西北", "北西北"]
        idx = round(degrees / 22.5) % 16
        return dirs[idx]

    def _fetch_open_meteo(self, lat, lng, city_name):
        # 防御：如果经纬度为空，尝试从 QSettings 读取
        if not lat or not lng:
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            lat = settings.value("selected_latitude", "")
            lng = settings.value("selected_longitude", "")
            if not lat or not lng:
                self.error_signal.emit("未设置经纬度，请搜索城市")
                self.last_status = "error_no_latlon"
                return None
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                "?latitude={}&longitude={}"
                "&current_weather=true"
                "&timezone=auto"
                "&forecast_days=1"
            ).format(lat, lng)
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=8) as resp:
                import json
                data = json.loads(resp.read().decode("utf-8"))
            cw = data.get("current_weather", {})
            weather_code = cw.get("weathercode", 0)
            weather_raw = self._WEATHERCODE_MAP.get(weather_code, "未知")
            weather_text = translate_weather_text_cn(weather_raw)
            temp = str(cw.get("temperature", "--"))
            wind_dir = self._wind_direction(cw.get("winddirection", 0))
            wind_speed = cw.get("windspeed", 0)
            wind_text = f"{wind_dir}{wind_speed:.0f}m/s" if wind_speed else ""
            return {
                "city": city_name,
                "weather": weather_text,
                "temp": temp,
                "wind": wind_text,
                "sunrise": "--:--",
                "sunset": "--:--",
            }
        except Exception as e:
            self.error_signal.emit(f"Open-Meteo: {e}")
            self.last_status = "failed"
            return None

    def stop(self):
        self._stopped = True
        self.quit()
        self.wait(1000)

    def get_adcode(self, city_name):
        """通过城市名称获取高德城市代码（adcode）"""
        if not city_name or city_name == "--" or city_name == "未知地区":
            return None
        try:
            url = f"{self.api_url}/v3/geocode/geo?key={self.api_key}&address={city_name}"
            resp = requests.get(url, timeout=5, verify=certifi.where())
            resp.raise_for_status()
            data = resp.json()
            if data['status'] == '1' and data['count'] != '0':
                return data['geocodes'][0]['adcode']
            return None
        except Exception as e:
            print(f"获取 adcode 失败: {e}")
            return None

    def get_ip_adcode(self):
        """通过 IP 获取城市代码（adcode）"""
        try:
            ip_url = f"{self.api_url}/v3/ip?key={self.api_key}"
            ip_resp = requests.get(ip_url, timeout=5, verify=certifi.where())
            ip_resp.raise_for_status()
            ip_data = ip_resp.json()
            if ip_data['status'] == '1':
                return ip_data.get('adcode', '110101'), ip_data.get('city', '未知地区')
            return None, None
        except Exception:
            return None, None

    def run(self):
        while not self._stopped:
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            service = settings.value("weather_service", "open_meteo")

            # Open-Meteo 不需要 API Key
            if service != "open_meteo":
                if not self.api_url or not self.api_key:
                    self.error_signal.emit("未配置 API 地址或密钥")
                    self.last_status = "failed"
                    self.msleep(60000)
                    continue

            # ---- 检查天气服务类型 ----
            if not service:
                api_url_now = settings.value("api_url", "")
                if api_url_now and "open-meteo" in api_url_now.lower():
                    service = "open_meteo"
                else:
                    service = "open_meteo"

            # ---- 获取城市名和经纬度 ----
            lat = settings.value("selected_latitude", "")
            lng = settings.value("selected_longitude", "")
            city_name = (
                settings.value("selected_location_display") or
                settings.value("selected_city") or
                settings.value("selected_county") or
                "未知地区"
            )

            # ---- Open-Meteo 分支 ----
            if service == "open_meteo":
                if lat and lng:
                    result = self._fetch_open_meteo(float(lat), float(lng), city_name)
                    if result:
                        self.data_updated.emit(result)
                        self.last_status = "success"
                    else:
                        self.data_updated.emit({
                            "city": city_name,
                            "weather": "⚠️",
                            "temp": "?",
                            "wind": "",
                            "sunrise": "--:--",
                            "sunset": "--:--",
                        })
                else:
                    self.error_signal.emit("Open-Meteo 需要经纬度，请先搜索城市")
                    self.last_status = "failed"
                for _ in range(self.refresh_minutes * 60):
                    if self._stopped:
                        break
                    self.msleep(1000)
                continue

            # ---- 和风天气 (QWeather) 分支 ----
            elif service == "qweather":
                try:
                    print("\U0001f525 qweather \u5206\u652f\u5f00\u59cb")
                    qw_api_key = getattr(self, "api_key", "") or ""
                    print("\U0001f525 1. \u5f00\u59cb\u68c0\u67e5 API Key")
                    if not qw_api_key:
                        self.error_signal.emit("\u548c\u98ce\u5929\u6c14 API Key \u672a\u914d\u7f6e")
                        self.last_status = "failed"
                        self.msleep(60000)
                        continue
                    print("\U0001f525 2. API Key \u68c0\u67e5\u901a\u8fc7")
                    print("\U0001f525 3. \u68c0\u67e5\u7ecf\u7eac\u5ea6...")
                    if not lat or not lng:
                        self.error_signal.emit("\u7f3a\u5c11\u7ecf\u7eac\u5ea6\uff0c\u8bf7\u5728\u8bbe\u7f6e\u4e2d\u641c\u7d22\u5730\u533a")
                        self.last_status = "failed"
                        self.msleep(60000)
                        continue
                    print("\U0001f525 3. \u7ecf\u7eac\u5ea6\u68c0\u67e5\u901a\u8fc7")

                    retry_count = 0
                    max_retries = 3
                    success = False
                    while retry_count < max_retries and not self._stopped:
                        retry_count += 1
                        try:
                            print("\U0001f525 4. URL \u6784\u5efa\u5f00\u59cb")
                            base_url = self.api_url.strip()
                            if not base_url.startswith(("http://", "https://")):
                                base_url = "https://" + base_url
                            if base_url.endswith("/"):
                                base_url = base_url[:-1]
                            qw_url = f"{base_url}/v7/weather/now?location={lng},{lat}&key={qw_api_key}"
                            print("\U0001f525 4. URL \u6784\u5efa\u5b8c\u6210")
                            masked_key = qw_api_key[:4] + "****" if len(qw_api_key) > 4 else "****"
                            print(f"\U0001f525 \u8bf7\u6c42 URL: {base_url}/v7/weather/now?location={lng},{lat}&key={masked_key}")
                            print(f"\U0001f525 \u7b2c {retry_count}/{max_retries} \u6b21\u8bf7\u6c42...")

                            print("\U0001f525 5. \u51c6\u5907\u53d1\u8d77\u8bf7\u6c42 (urllib)")
                            req = urllib.request.Request(qw_url, headers={
                                "User-Agent": "Mozilla/5.0",
                                "Accept-Encoding": "gzip, deflate"
                            })
                            with urllib.request.urlopen(req, timeout=10) as resp:
                                print(f"\U0001f525 6. \u8bf7\u6c42\u5b8c\u6210 (HTTP {resp.status})")
                                # 处理 gzip 压缩
                                raw_data = resp.read()
                                content_encoding = resp.info().get("Content-Encoding", "")
                                if "gzip" in content_encoding:
                                    try:
                                        raw_data = gzip.decompress(raw_data)
                                    except Exception:
                                        pass
                                qw_data = json.loads(raw_data.decode("utf-8"))

                            print(f"\U0001f525 \u54cd\u5e94\u4ee3\u7801: {qw_data.get('code')}")
                            if qw_data.get("code") == "200":
                                now = qw_data["now"]
                                wind_dir = now.get("windDir", "")
                                wind_speed = now.get("windSpeed", "0")
                                display = settings.value("selected_location_display", "") or city_name
                                self.data_updated.emit({
                                    "city": display,
                                    "weather": translate_weather_text_cn(now.get("text", "\u672a\u77e5")),
                                    "temp": now.get("temp", "--"),
                                    "wind": f"{wind_dir}{wind_speed}km/h" if wind_dir else "",
                                    "sunrise": "--:--",
                                    "sunset": "--:--",
                                })
                                self.last_status = "success"
                                print(f" \u548c\u98ce\u5929\u6c14\u66f4\u65b0\u6210\u529f: {display} {now.get('text')} {now.get('temp')}\u2103")
                                success = True
                                break
                            else:
                                print(f"\U0001f525 \u548c\u98ce\u5929\u6c14 API \u9519\u8bef: {qw_data.get('code')}")
                                self.error_signal.emit(f"\u548c\u98ce\u5929\u6c14\u9519\u8bef: {qw_data.get('code')}")
                                self.last_status = "failed"
                        except Exception as e:
                            print(f"\U0001f525 \u548c\u98ce\u5929\u6c14\u5f02\u5e38: {type(e).__name__}: {e}")
                            self.error_signal.emit(f"\u548c\u98ce\u5929\u6c14: {e}")
                            self.last_status = "failed"

                        if retry_count < max_retries and not self._stopped:
                            print(f"\U0001f525 \u7b49\u5f85 5 \u79d2\u540e\u91cd\u8bd5...")
                            self.msleep(5000)

                    if not success:
                        display = settings.value("selected_location_display", "") or city_name
                        self.data_updated.emit({
                            "city": display,
                            "weather": "\u26a0\ufe0f",
                            "temp": "?",
                            "wind": "",
                            "sunrise": "--:--",
                            "sunset": "--:--",
                        })
                        print(f"\U0001f525 \u548c\u98ce\u5929\u6c14\u91cd\u8bd5\u5168\u90e8\u5931\u8d25")

                    for _ in range(self.refresh_minutes * 60):
                        if self._stopped:
                            break
                        self.msleep(1000)
                except Exception as e:
                    print(f"\U0001f525 qweather \u5206\u652f\u5f02\u5e38: {e}")
                    import traceback
                    traceback.print_exc()
                    self.error_signal.emit(f"\u548c\u98ce\u5929\u6c14\u5185\u90e8\u9519\u8bef: {e}")
                    self.last_status = "failed"
                    self.msleep(60000)
                continue

            # ---- WeatherAPI 分支（带 3 次重试） ----
            elif service == "weatherapi":
                try:
                    print("🌤️ WeatherAPI 分支开始")
                    wa_api_key = getattr(self, "api_key", "") or ""
                    if not wa_api_key:
                        self.error_signal.emit("WeatherAPI Key not configured")
                        self.last_status = "failed"
                        self.msleep(60000)
                        continue

                    if not lat or not lng:
                        self.error_signal.emit("Missing coordinates, please search a city first")
                        self.last_status = "failed"
                        self.msleep(60000)
                        continue

                    retry_count = 0
                    max_retries = 3
                    success = False
                    display = settings.value("selected_location_display", "") or city_name

                    while retry_count < max_retries and not self._stopped:
                        retry_count += 1
                        try:
                            # 补全协议
                            base_url = self.api_url.strip()
                            if not base_url.startswith(("http://", "https://")):
                                base_url = "https://" + base_url
                            if base_url.endswith("/"):
                                base_url = base_url[:-1]
                            wa_url = f"{base_url}?key={wa_api_key}&q={lat},{lng}&aqi=no"
                            print(f"🌤️ WeatherAPI 请求: {wa_url[:80]}... (第 {retry_count}/{max_retries} 次)")

                            wa_resp = requests.get(wa_url, timeout=10)
                            if wa_resp.status_code != 200:
                                raise Exception(f"HTTP {wa_resp.status_code}")

                            wa_data = wa_resp.json()
                            if "error" in wa_data:
                                raise Exception(wa_data["error"].get("message", "Unknown"))

                            cur = wa_data.get("current", {})
                            if not cur:
                                raise Exception("No current field in response")

                            cond = cur.get("condition", {})
                            weather_en = cond.get("text", "Unknown")
                            weather_translated = translate_weather_text(weather_en)
                            print(f"[WeatherAPI] raw='{weather_en}' -> translated='{weather_translated}'")
                            wd = cur.get("wind_dir", "")
                            wk = cur.get("wind_kph", 0)
                            wind_text = f"{wd}{wk}km/h" if wd else ""

                            self.data_updated.emit({
                                "city": display,
                                "weather": weather_translated,
                                "temp": str(cur.get("temp_c", "--")),
                                "wind": wind_text,
                                "sunrise": "--:--",
                                "sunset": "--:--",
                            })
                            self.last_status = "success"
                            self.error_signal.emit("")  # 清空错误
                            print(f"🌤️ WeatherAPI 更新成功: {display} {weather_translated} {cur.get('temp_c')}℃")
                            success = True
                            break

                        except Exception as e:
                            print(f"🌤️ WeatherAPI 异常 (第 {retry_count}/{max_retries} 次): {e}")
                            self.last_status = "failed"
                            if retry_count < max_retries and not self._stopped:
                                print("🌤️ 等待 5 秒后重试...")
                                self.msleep(5000)

                    if not success:
                        self.data_updated.emit({
                            "city": display,
                            "weather": "⚠️",
                            "temp": "?",
                            "wind": "",
                            "sunrise": "--:--",
                            "sunset": "--:--",
                        })
                        print("🌤️ WeatherAPI 重试全部失败")

                    for _ in range(self.refresh_minutes * 60):
                        if self._stopped:
                            break
                        self.msleep(1000)

                except Exception as e:
                    print(f"🌤️ WeatherAPI 分支异常: {e}")
                    import traceback
                    traceback.print_exc()
                    self.error_signal.emit(f"WeatherAPI 内部错误: {e}")
                    self.last_status = "failed"
                    self.msleep(60000)
                continue

            # ---- 高德 API 分支（原有逻辑） ----
            # ---- 优先使用经纬度（全球城市） ----
            lat = settings.value("selected_latitude", "")
            lng = settings.value("selected_longitude", "")
            city_param = None
            display_city = None

            if lat and lng:
                # 使用经纬度（格式：经度,纬度）
                city_param = f"{lng},{lat}"
                display_city = settings.value("selected_location_display", "")
                if not display_city:
                    # 如果没有保存长格式名称，用城市名回退
                    display_city = settings.value("selected_city", "未知地区")
                print(f" 使用经纬度请求天气: {display_city} ({lng},{lat})")
            else:
                # ---- 回退到旧逻辑（中国城市 adcode） ----
                selected_city = settings.value("selected_city", "")
                selected_county = settings.value("selected_county", "")
                user_location = selected_county if selected_county else selected_city

                if user_location:
                    city_param = self.get_adcode(user_location)
                    display_city = user_location
                    if not city_param:
                        print(f" 获取 {user_location} 的 adcode 失败，回退到 IP 定位")
                        city_param, ip_city = self.get_ip_adcode()
                        display_city = user_location
                        if not city_param:
                            self.error_signal.emit("无法获取城市代码")
                            self.last_status = "failed"
                            self.msleep(60000)
                            continue
                else:
                    city_param, ip_city = self.get_ip_adcode()
                    display_city = ip_city if ip_city else "未知地区"
                    if not city_param:
                        self.error_signal.emit("无法获取 IP 定位的城市代码")
                        self.last_status = "failed"
                        self.msleep(60000)
                        continue
                    print(f" 使用 IP 定位: {display_city} (adcode: {city_param})")

                # 如果 city_param 是 adcode（纯数字），直接使用；如果是经纬度字符串，也支持
                # 高德 API 的 city 参数同时支持 adcode 和 经纬度

            try:
                # 构建天气请求 URL（city 参数同时支持 adcode 和 经纬度）
                weather_url = f"{self.api_url}/v3/weather/weatherInfo?key={self.api_key}&city={city_param}&extensions=base"
                w_resp = requests.get(weather_url, timeout=5, verify=certifi.where())
                w_resp.raise_for_status()
                data = w_resp.json()

                if data['status'] == '1' and data['count'] != '0':
                    live = data['lives'][0]
                    self.data_updated.emit({
                        'city': display_city,
                        'weather': translate_weather_text_cn(live['weather']),
                        'temp': live['temperature'],
                        'wind': live['winddirection'] + live['windpower'] + '级',
                        'sunrise': '--:--',
                        'sunset': '--:--',
                    })
                    self.last_status = "success"
                    print(f" 天气更新成功: {display_city} {live['weather']} {live['temperature']}℃")
                elif data['status'] == '1' and data['count'] == '0' and display_city and display_city != "未知地区":
                    # 经纬度查询无结果，回退到城市名查询
                    # 优先级：selected_city > selected_county > selected_province > display_city
                    fallback_city = settings.value("selected_city", "")
                    if not fallback_city:
                        fallback_city = settings.value("selected_county", "")
                    if not fallback_city:
                        fallback_city = settings.value("selected_province", "")
                    if not fallback_city:
                        fallback_city = display_city
                    print(f"⚠️ 经纬度查询无结果，回退到城市名查询: {fallback_city}")
                    try:
                        fallback_url = f"{self.api_url}/v3/weather/weatherInfo?key={self.api_key}&city={fallback_city}&extensions=base"
                        fb_resp = requests.get(fallback_url, timeout=5, verify=certifi.where())
                        fb_resp.raise_for_status()
                        fb_data = fb_resp.json()
                        if fb_data['status'] == '1' and fb_data['count'] != '0':
                            live = fb_data['lives'][0]
                            self.data_updated.emit({
                                'city': display_city,
                                'weather': translate_weather_text_cn(live['weather']),
                                'temp': live['temperature'],
                                'wind': live['winddirection'] + live['windpower'] + '级',
                                'sunrise': '--:--',
                                'sunset': '--:--',
                            })
                            self.last_status = "success"
                            print(f" 城市名回退查询成功: {display_city} {live['weather']} {live['temperature']}℃")
                        else:
                            raise Exception("城市名回退也失败")
                    except Exception:
                        self.error_signal.emit(f"API无数据: {display_city}")
                        self.last_status = "failed"
                        self.data_updated.emit({
                            'city': display_city,
                            'weather': '⚠️',
                            'temp': '?',
                            'wind': '',
                            'sunrise': '--:--',
                            'sunset': '--:--',
                        })
                else:
                    error_msg = data.get('info', '未知错误')
                    self.error_signal.emit(f"API错误: {error_msg}")
                    self.last_status = "failed"
                    self.data_updated.emit({
                        'city': display_city,
                        'weather': '⚠️',
                        'temp': '?',
                        'wind': '',
                        'sunrise': '--:--',
                        'sunset': '--:--',
                    })

            except Exception as e:
                print(f" 天气请求异常: {e}")
                self.last_status = "failed"
                # 重试机制
                retry_count = 0
                max_retries = 6
                while retry_count < max_retries and not self._stopped:
                    retry_count += 1
                    print(f" 天气请求失败，{retry_count}/{max_retries} 次重试...")
                    self.error_signal.emit(f"请求异常，正在重试 ({retry_count}/{max_retries})...")
                    for _ in range(10):
                        if self._stopped:
                            break
                        self.msleep(1000)
                    if self._stopped:
                        break
                    try:
                        settings = QSettings("MyDesktopApp", "WeatherSettings")
                        lat = settings.value("selected_latitude", "")
                        lng = settings.value("selected_longitude", "")

                        if lat and lng:
                            city_param = f"{lng},{lat}"
                            display_city = settings.value("selected_location_display", "未知地区")
                        else:
                            selected_city = settings.value("selected_city", "")
                            selected_county = settings.value("selected_county", "")
                            user_location = selected_county if selected_county else selected_city
                            if user_location:
                                city_param = self.get_adcode(user_location)
                                display_city = user_location
                                if not city_param:
                                    city_param, ip_city = self.get_ip_adcode()
                                    display_city = user_location
                            else:
                                city_param, ip_city = self.get_ip_adcode()
                                display_city = ip_city if ip_city else "未知地区"

                        if city_param:
                            weather_url = f"{self.api_url}/v3/weather/weatherInfo?key={self.api_key}&city={city_param}&extensions=base"
                            w_resp = requests.get(weather_url, timeout=5, verify=certifi.where())
                            w_resp.raise_for_status()
                            data = w_resp.json()
                            if data['status'] == '1' and data['count'] != '0':
                                live = data['lives'][0]
                                self.data_updated.emit({
                                    'city': display_city,
                                    'weather': translate_weather_text_cn(live['weather']),
                                    'temp': live['temperature'],
                                    'wind': live['winddirection'] + live['windpower'] + '级',
                                    'sunrise': '--:--',
                                    'sunset': '--:--',
                                })
                                self.last_status = "success"
                                print(f" 重试成功，天气更新成功: {display_city} {live['weather']} {live['temperature']}℃")
                                self.error_signal.emit("")
                                break
                    except Exception as retry_e:
                        print(f" 重试失败: {retry_e}")
                        self.last_status = "failed"
                        continue
                else:
                    self.error_signal.emit(f"请求异常（重试 {max_retries} 次后失败）: {str(e)}")
                    self.last_status = "failed"
                    if user_location:
                        self.data_updated.emit({
                            'city': user_location,
                            'weather': '⚠️',
                            'temp': '?',
                            'wind': '',
                            'sunrise': '--:--',
                            'sunset': '--:--',
                        })
                    for _ in range(self.refresh_minutes * 60):
                        if self._stopped:
                            break
                        self.msleep(1000)
                    continue

            # 正常等待
            for _ in range(self.refresh_minutes * 60):
                if self._stopped:
                    break
                self.msleep(1000)


# ---------- 网速监控 ----------
class NetSpeedThread(QThread):
    speed_updated = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.last_bytes = psutil.net_io_counters()
        self.last_time = datetime.now()
        self._stopped = False

    def stop(self):
        self._stopped = True
        self.wait(3000)

    def run(self):
        while not self._stopped:
            now = datetime.now()
            current = psutil.net_io_counters()
            dt = (now - self.last_time).total_seconds()
            if dt > 0:
                down = (current.bytes_recv - self.last_bytes.bytes_recv) / dt / 1024 / 1024 * 8
                up = (current.bytes_sent - self.last_bytes.bytes_sent) / dt / 1024 / 1024 * 8
                self.speed_updated.emit(down, up)
            self.last_bytes = current
            self.last_time = now
            self.sleep(1)

