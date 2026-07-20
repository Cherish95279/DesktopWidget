p = r"D:/PythonProjects/DesktopWidget/src/settings_pages/weather_page.py"
c = open(p, encoding="utf-8").read()

# Fix: use itemData instead of text matching for provider detection
# 1. Change dropdown setup to use addItem with data
old_dropdown = 'self.url_combo.addItems([self.tr("高德"), self.tr("Open-Meteo"), self.tr("和风天气"), self.tr("WeatherAPI"), self.tr("自定义")])'
new_dropdown = '''        self._providers = [
            ("gaode",      self.tr("高德")),
            ("open_meteo", self.tr("Open-Meteo")),
            ("qweather",   self.tr("和风天气")),
            ("weatherapi", self.tr("WeatherAPI")),
            ("custom",     self.tr("自定义")),
        ]
        for key, label in self._providers:
            self.url_combo.addItem(label, key)'''
c = c.replace(old_dropdown, new_dropdown)

# 2. Fix on_provider_changed to use currentData()
old_method_start = 'def on_provider_changed(self, text):'
new_method = '''    def on_provider_changed(self, text):
        if self._loading:
            return

        service_key = self.url_combo.currentData()
        if not service_key:
            return

        service_map = {
            "gaode":      ("https://restapi.amap.com",                        self.tr("请输入高德 API Key"),       True),
            "open_meteo": ("https://api.open-meteo.com/v1/forecast",          self.tr("无需 API Key（可留空）"), False),
            "qweather":   ("https://devapi.qweather.com/v7/weather/now",      self.tr("请输入和风天气 API Key"), True),
            "weatherapi": ("https://api.weatherapi.com/v1/current.json",      self.tr("请输入 WeatherAPI Key"),               True),
            "custom":     ("",                                                 self.tr("请输入 API Key"),                      False),
        }

        if service_key in service_map:
            url, placeholder, readonly = service_map[service_key]
            self.url_edit.setText(url)
            self.url_edit.setReadOnly(readonly)
            self.key_edit.setPlaceholderText(placeholder)

        self.save_api_settings()'''

# Find the old method and replace
old_method_idx = c.find('def on_provider_changed')
old_next_method = c.find('def on_url_changed', old_method_idx)
old_method = c[old_method_idx:old_next_method]
c = c.replace(old_method, new_method + '

    ')

# 3. Fix load_settings to use findData instead of setCurrentText
old_load = '''            weather_service = settings.value("weather_service", "")
            service_to_label = {
                "gaode": self.tr("高德"),
                "open_meteo": self.tr("Open-Meteo"),
                "qweather": self.tr("和风天气"),
                "weatherapi": self.tr("WeatherAPI"),
                "custom": self.tr("自定义"),
            }
            if weather_service and weather_service in service_to_label:
                self.url_combo.setCurrentText(service_to_label[weather_service])
            elif url == "https://restapi.amap.com":
                self.url_combo.setCurrentText(self.tr("高德"))
            else:
                self.url_combo.setCurrentText(self.tr("自定义"))'''

new_load = '''            weather_service = settings.value("weather_service", "")
            if weather_service:
                idx = self.url_combo.findData(weather_service)
                if idx >= 0:
                    self.url_combo.setCurrentIndex(idx)
            elif url == "https://restapi.amap.com":
                idx = self.url_combo.findData("gaode")
                if idx >= 0:
                    self.url_combo.setCurrentIndex(idx)
            else:
                idx = self.url_combo.findData("custom")
                if idx >= 0:
                    self.url_combo.setCurrentIndex(idx)'''

c = c.replace(old_load, new_load)

open(p, "w", encoding="utf-8").write(c)
print("ok")
