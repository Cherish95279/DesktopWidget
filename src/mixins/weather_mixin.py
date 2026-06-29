from PyQt6.QtCore import QTimer, QSettings
from ..constants import DEFAULT_LAYOUT
from ..threads import WeatherThread


class WeatherMixin:
    """天气管理混入：线程控制、加载动画、数据更新"""

    def start_loading_animation(self):
        """开始加载动画"""
        self._loading_weather = True
        self._loading_dots = 0
        if self._loading_timer is None:
            self._loading_timer = QTimer()
            self._loading_timer.timeout.connect(self._update_loading_dots)
            self._loading_timer.start(500)
        self.update()

    def _update_loading_dots(self):
        """更新加载动画的点数（0-3循环）"""
        self._loading_dots = (self._loading_dots + 1) % 4
        self.update()

    def stop_loading_animation(self):
        """停止加载动画"""
        self._loading_weather = False
        if self._loading_timer is not None:
            self._loading_timer.stop()
            self._loading_timer = None
        self.update()

    def start_weather_thread(self, force_restart=False):
        """智能启动天气线程：根据布局配置决定是否启动"""
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        api_url = settings.value("api_url", "")
        api_key = settings.value("api_key", "")
        refresh_minutes = int(settings.value("refresh_minutes", 120))
        self._api_configured = bool(api_url and api_key)

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
                print("🌤️ 布局中未配置天气，停止天气线程")
                try:
                    self.weather_thread.data_updated.disconnect()
                    self.weather_thread.error_signal.disconnect()
                except:
                    pass
                self.weather_thread.stop()
                self.weather_thread = None
            self.stop_loading_animation()
            return

        if not self._api_configured:
            if self.weather_thread is not None:
                try:
                    self.weather_thread.data_updated.disconnect()
                    self.weather_thread.error_signal.disconnect()
                except:
                    pass
                self.weather_thread.stop()
                self.weather_thread = None
            self.stop_loading_animation()
            self.update()
            return

        if self.weather_thread is not None and not force_restart:
            return

        if self.weather_thread is not None:
            print("🔄 断开旧天气线程信号并停止...")
            try:
                self.weather_thread.data_updated.disconnect()
                self.weather_thread.error_signal.disconnect()
            except Exception as e:
                print(f"⚠️ 断开信号时出错: {e}")
            self.weather_thread.stop()
            self.weather_thread = None

        if force_restart or self.weather.get("city") == "--":
            self.start_loading_animation()

        print("🌤️ 启动新天气线程...")
        self.weather_thread = WeatherThread(api_url, api_key, refresh_minutes)
        self.weather_thread.data_updated.connect(self.update_weather)
        self.weather_thread.error_signal.connect(self.on_weather_error)
        self.weather_thread.start()
        print("🌤️ 天气线程已启动")

    def update_weather(self, data):
        print(f"🔔 主窗口收到天气更新: {data.get('city')} {data.get('weather')} {data.get('temp')}℃")
        self.stop_loading_animation()
        self.weather = data
        self.update()

    def on_weather_error(self, err_msg):
        print(f"❌ 天气错误: {err_msg}")