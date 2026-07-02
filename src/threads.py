import socket
from datetime import datetime, timedelta, timezone
from PyQt6.QtCore import QThread, pyqtSignal, QSettings
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import certifi
import psutil
from .constants import AMAP_KEY


# ---------- 扫描 HA 服务器 ----------
class ServerScanner(QThread):
    ip_found = pyqtSignal(str)

    def run(self):
        local_ip = "192.168.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            pass
        subnet = ".".join(local_ip.split('.')[:-1]) + "."
        found = None
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(self.check_port, subnet + str(i)): i for i in range(1, 255)}
            for f in as_completed(futures):
                res = f.result()
                if res:
                    found = res
                    break
        self.ip_found.emit(found if found else "192.168.0.135")

    def check_port(self, ip):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.15)
                if s.connect_ex((ip, 8123)) == 0:
                    return ip
        except:
            return None


# ---------- 天气线程（增加 last_status 记录） ----------
class WeatherThread(QThread):
    data_updated = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, api_url, api_key, refresh_minutes):
        super().__init__()
        self.api_url = api_url
        self.api_key = api_key
        self.refresh_minutes = max(1, refresh_minutes)
        self._stopped = False
        # ===== 新增：记录本次启动以来的天气请求状态 =====
        self.last_status = "idle"  # idle / success / failed

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
            if not self.api_url or not self.api_key:
                self.error_signal.emit("未配置 API 地址或密钥")
                self.last_status = "failed"
                self.msleep(60000)
                continue

            settings = QSettings("MyDesktopApp", "WeatherSettings")
            selected_city = settings.value("selected_city", "")
            selected_county = settings.value("selected_county", "")
            user_location = selected_county if selected_county else selected_city

            try:
                city_code = None
                display_city = None

                if user_location:
                    city_code = self.get_adcode(user_location)
                    if city_code:
                        display_city = user_location
                        print(f"✅ 使用用户选择的城市: {user_location} (adcode: {city_code})")
                    else:
                        print(f"⚠️ 获取 {user_location} 的 adcode 失败，回退到 IP 定位")
                        city_code, ip_city = self.get_ip_adcode()
                        display_city = user_location
                        if not city_code:
                            raise Exception("无法获取城市代码")
                else:
                    city_code, ip_city = self.get_ip_adcode()
                    display_city = ip_city if ip_city else "未知地区"
                    if not city_code:
                        raise Exception("无法获取 IP 定位的城市代码")
                    print(f"📍 使用 IP 定位: {display_city} (adcode: {city_code})")

                weather_url = f"{self.api_url}/v3/weather/weatherInfo?key={self.api_key}&city={city_code}&extensions=base"
                w_resp = requests.get(weather_url, timeout=5, verify=certifi.where())
                w_resp.raise_for_status()
                data = w_resp.json()

                if data['status'] == '1' and data['count'] != '0':
                    live = data['lives'][0]
                    self.data_updated.emit({
                        'city': display_city,
                        'weather': live['weather'],
                        'temp': live['temperature'],
                        'wind': live['winddirection'] + live['windpower'] + '级',
                        'sunrise': '--:--',
                        'sunset': '--:--',
                    })
                    # ===== 成功 =====
                    self.last_status = "success"
                    print(f"✅ 天气更新成功: {display_city} {live['weather']} {live['temperature']}℃")
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
                print(f"❌ 天气请求异常: {e}")
                self.last_status = "failed"
                # 重试机制（略，保持原逻辑）
                retry_count = 0
                max_retries = 6
                while retry_count < max_retries and not self._stopped:
                    retry_count += 1
                    print(f"🔄 天气请求失败，{retry_count}/{max_retries} 次重试...")
                    self.error_signal.emit(f"请求异常，正在重试 ({retry_count}/{max_retries})...")
                    for _ in range(10):
                        if self._stopped:
                            break
                        self.msleep(1000)
                    if self._stopped:
                        break
                    try:
                        settings = QSettings("MyDesktopApp", "WeatherSettings")
                        selected_city = settings.value("selected_city", "")
                        selected_county = settings.value("selected_county", "")
                        user_location = selected_county if selected_county else selected_city

                        if user_location:
                            city_code = self.get_adcode(user_location)
                            if not city_code:
                                city_code, ip_city = self.get_ip_adcode()
                                display_city = user_location
                            else:
                                display_city = user_location
                        else:
                            city_code, ip_city = self.get_ip_adcode()
                            display_city = ip_city if ip_city else "未知地区"

                        if city_code:
                            weather_url = f"{self.api_url}/v3/weather/weatherInfo?key={self.api_key}&city={city_code}&extensions=base"
                            w_resp = requests.get(weather_url, timeout=5, verify=certifi.where())
                            w_resp.raise_for_status()
                            data = w_resp.json()
                            if data['status'] == '1' and data['count'] != '0':
                                live = data['lives'][0]
                                self.data_updated.emit({
                                    'city': display_city,
                                    'weather': live['weather'],
                                    'temp': live['temperature'],
                                    'wind': live['winddirection'] + live['windpower'] + '级',
                                    'sunrise': '--:--',
                                    'sunset': '--:--',
                                })
                                self.last_status = "success"
                                print(f"✅ 重试成功，天气更新成功: {display_city} {live['weather']} {live['temperature']}℃")
                                self.error_signal.emit("")
                                break
                    except Exception as retry_e:
                        print(f"❌ 重试失败: {retry_e}")
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

    def run(self):
        while True:
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