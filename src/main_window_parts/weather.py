# -*- coding: utf-8 -*-
"""
天气与 Ping 层：天气线程、服务器扫描、加载动画、刷新率、启动上报。

作为 MainWindow 的 mixin。
"""

from PyQt6.QtCore import QTimer, QSettings

from ..constants import DEFAULT_LAYOUT
from ..region_data import get_coords_by_name, get_coords_for_city
from ..threads import WeatherThread


class WeatherMixin:
    """天气线程与周期上报逻辑。"""

    def _check_initial_ping_ready(self):
        """
        检查启动阶段的天气和更新检查是否都已经完成。

        第一次完整上报只允许执行一次。
        """
        if self._initial_ping_sent:
            return

        # --------------------------------------------------------
        # 1. 判断天气是否需要等待
        # --------------------------------------------------------

        settings = QSettings("MyDesktopApp", "WeatherSettings")

        has_weather = False

        for i in range(1, 9):
            key = f"slot_{i}"
            default_val = DEFAULT_LAYOUT.get(key, "empty")
            value = settings.value(key, default_val)

            if value == "weather":
                has_weather = True
                break

        if has_weather:
            weather_status = self.get_weather_status()

            # 天气线程还没有产生第一次结果
            if weather_status == "idle":
                return
        else:
            # 没有天气槽位，不需要等待天气
            weather_status = "not_enabled"

        # --------------------------------------------------------
        # 2. 判断更新检查是否完成
        # --------------------------------------------------------

        update_status = self.get_update_status()

        if update_status in ("idle", "checking"):
            return

        # --------------------------------------------------------
        # 3. 两项都完成
        # --------------------------------------------------------

        self._initial_ping_sent = True

        # 停止启动阶段轮询
        if self._initial_ping_timer.isActive():
            self._initial_ping_timer.stop()

        # 进行第一次完整上报
        try:
            from ..ping_client import report_launch_full

            report_launch_full(
                weather_status,
                update_status
            )
        except Exception:
            pass

        # --------------------------------------------------------
        # 4. 第一次上报之后开始30分钟周期上报
        # --------------------------------------------------------

        if not self._ping_timer.isActive():
            self._ping_timer.start(30 * 60 * 1000)

    def _periodic_ping(self):
        """
        每30分钟上报一次当前状态。
        """
        try:
            from ..ping_client import report_launch_full

            weather_status = self.get_weather_status()
            update_status = self.get_update_status()

            report_launch_full(
                weather_status,
                update_status
            )

        except Exception:
            pass

    def _read_refresh_rate(self):
        """读取 Windows 当前显示配置刷新率"""
        try:
            import ctypes, struct
            user32 = ctypes.windll.user32
            num_paths = ctypes.c_uint32(0)
            num_modes = ctypes.c_uint32(0)
            ret = user32.GetDisplayConfigBufferSizes(1, ctypes.byref(num_paths), ctypes.byref(num_modes))
            if ret == 0 and num_paths.value > 0:
                path_buf = (ctypes.c_ubyte * (num_paths.value * 72))()
                mode_buf = (ctypes.c_ubyte * (num_modes.value * 96))()
                actual_paths = ctypes.c_uint32(num_paths.value)
                actual_modes = ctypes.c_uint32(num_modes.value)
                ret = user32.QueryDisplayConfig(1, ctypes.byref(actual_paths), path_buf, ctypes.byref(actual_modes), mode_buf, None)
                if ret == 0:
                    for i in range(actual_paths.value):
                        num, den = struct.unpack_from('<II', path_buf, i * 72 + 48)
                        if den > 0 and num > 0:
                            return int(round(num / den))
        except Exception:
            pass
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hdc = user32.GetDC(0)
            refresh = ctypes.windll.gdi32.GetDeviceCaps(hdc, 116)
            user32.ReleaseDC(0, hdc)
            if refresh > 0:
                return refresh
        except Exception:
            pass
        return 60

    def start_loading_animation(self):
        self._loading_weather = True
        self._loading_dots = 0
        if self._loading_timer is None:
            self._loading_timer = QTimer()
            self._loading_timer.timeout.connect(self._update_loading_dots)
            self._loading_timer.start(500)
        self.update()

    def _update_loading_dots(self):
        self._loading_dots = (self._loading_dots + 1) % 4
        self.update()

    def stop_loading_animation(self):
        self._loading_weather = False
        if self._loading_timer is not None:
            self._loading_timer.stop()
            self._loading_timer = None
        self.update()

    def start_weather_thread(self, force_restart=False):
        """智能启动天气线程：根据布局配置和服务类型决定是否启动"""
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.sync()  # 确保读取最新配置

        weather_service = settings.value("weather_service", "open_meteo")
        api_url = settings.value(f"api_url_{weather_service}", "")
        api_key = settings.value(f"api_key_{weather_service}", "")
        refresh_minutes = int(settings.value("refresh_minutes", 120))
        lat = settings.value("selected_latitude", "")
        lng = settings.value("selected_longitude", "")

        print(f"U0001F324️ start_weather_thread 被调用，weather_service={weather_service}, force_restart={force_restart}")
        print(f"U0001F324️ lat={lat}, lng={lng}")

        # Open-Meteo: 尝试获取坐标（JSON 反查 > IP 定位）
        if weather_service == "open_meteo":
            if not lat or not lng:
                # 优先从本地 JSON 反查坐标（高德 IP 定位可能已写入城市名）
                city_name = settings.value("selected_city", "") or settings.value("selected_location_display", "")
                coords_from_json = False
                if city_name:
                    coords = get_coords_for_city(city_name) or get_coords_by_name(city_name)
                    if coords:
                        settings.setValue("selected_latitude", str(coords[0]))
                        settings.setValue("selected_longitude", str(coords[1]))
                        settings.setValue("location_source", "json")
                        settings.sync()
                        lat = str(coords[0])
                        lng = str(coords[1])
                        coords_from_json = True
                        print(f"U0001F310 从本地 JSON 推导坐标成功: {city_name} -> {coords[0]}, {coords[1]}")

                # JSON 反查失败才尝试网络 IP 定位
                if not coords_from_json:
                    ip_attempted = settings.value("_ip_attempted", False, type=bool)
                    if not ip_attempted:
                        from ..utils import get_ip_location
                        print("U0001F310 JSON 无匹配，尝试 IP 自动定位...")
                        new_lat, new_lng, city, ip_isp = get_ip_location()
                        settings.setValue("_ip_attempted", True)
                        if new_lat and new_lng:
                            settings.setValue("_ip_attempted", True)
                            settings.setValue("selected_latitude", str(new_lat))
                            settings.setValue("selected_longitude", str(new_lng))
                            if city:
                                settings.setValue("selected_city", city)
                                settings.setValue("selected_location_display", city)
                            if ip_isp:
                                settings.setValue("ip_isp", ip_isp)
                            settings.setValue("location_source", "ip")
                            settings.sync()
                            lat = str(new_lat)
                            lng = str(new_lng)
                            print(f"U0001F310 IP 定位成功: {city} ({new_lat}, {new_lng})")
                        else:
                            print("U0001F310 IP 定位失败，请手动搜索城市")
                            settings.sync()

        # 按服务类型读取 API Key（Open-Meteo 不需要）
        if weather_service != "open_meteo":
            api_key = api_key or settings.value(f"api_key_{weather_service}", "")

        # 判断 API 是否配置完整
        if weather_service == "open_meteo":
            self._api_configured = bool(lat and lng)
        else:
            self._api_configured = bool(api_url and api_key)

        print(f"U0001F324️ _api_configured={self._api_configured}")

        has_weather = False
        slot_keys = ["slot_1", "slot_2", "slot_3", "slot_4", "slot_5", "slot_6", "slot_7", "slot_8"]
        for key in slot_keys:
            default_val = DEFAULT_LAYOUT.get(key, "empty")
            value = settings.value(key, default_val)
            if value == "weather":
                has_weather = True
                break

        if not has_weather:
            if self.weather_thread is not None:
                print(" 布局中未配置天气，停止天气线程")
                try:
                    self.weather_thread.data_updated.disconnect()
                    self.weather_thread.error_signal.disconnect()
                except Exception as e:
                    print(f" 断开天气线程信号时出错: {e}")
                self.weather_thread.stop()
                self.weather_thread = None
            self.stop_loading_animation()
            return

        if not self._api_configured:
            print(f"U0001F324️ API 未配置，跳过启动")
            if self.weather_thread is not None:
                try:
                    self.weather_thread.data_updated.disconnect()
                    self.weather_thread.error_signal.disconnect()
                except Exception as e:
                    print(f" 断开天气线程信号时出错: {e}")
                self.weather_thread.stop()
                self.weather_thread = None
            self.stop_loading_animation()
            self.update()
            return

        if self.weather_thread is not None and not force_restart:
            print(f"U0001F324️ 线程已运行且非强制重启，跳过")
            return

        if self.weather_thread is not None:
            print(" 断开旧天气线程信号并停止...")
            try:
                self.weather_thread.data_updated.disconnect()
                self.weather_thread.error_signal.disconnect()
            except Exception as e:
                print(f" 断开信号时出错: {e}")
            self.weather_thread.stop()
            self.weather_thread = None

        if force_restart or self.weather.get("city") == "--":
            self.start_loading_animation()

        print(" 启动新天气线程...")
        self.weather_thread = WeatherThread(api_url, api_key, refresh_minutes)
        self.weather_thread.data_updated.connect(self.update_weather)
        self.weather_thread.error_signal.connect(self.on_weather_error)
        self.weather_thread.start()
        print(f"U0001F324️ 线程启动状态: {self.weather_thread is not None}")

    def update_weather(self, data):
        print(f" 主窗口收到天气更新: {data.get('city')} {data.get('weather')} {data.get('temp')}℃")
        self.stop_loading_animation()
        self.weather = data
        self.update()

    def on_weather_error(self, err_msg):
        if not err_msg:  # 空字符串不打印
            return
        print(f" 天气错误: {err_msg}")

