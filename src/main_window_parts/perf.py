# -*- coding: utf-8 -*-
"""
性能采集层：CPU/GPU/内存/磁盘/运行时间/网速/时钟/IP。

作为 MainWindow 的 mixin，定期采集系统指标并刷新界面。
"""

import socket
import ctypes
import ctypes.util
from datetime import datetime

import psutil

from ..solar_terms import get_next_term_info, translate_term

try:
    from zhdate import ZhDate

    LUNAR_AVAILABLE = True
except ImportError:
    LUNAR_AVAILABLE = False



class PerfMixin:
    """性能指标与时钟更新逻辑。"""

    def get_public_ip(self):
        """获取公网 IP，多个备用接口"""
        import requests
        urls = [
            ("https://api.ipify.org?format=json", "json", "ip"),
            ("https://httpbin.org/ip", "json", "origin"),
            ("https://myip.ipip.net", "text", None),
        ]
        for url, fmt, key in urls:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    if fmt == "json":
                        return resp.json().get(key, "")
                    else:
                        # text format: "当前 IP：x.x.x.x  来自于：..."
                        text = resp.text
                        import re
                        m = re.search(r"(\d+\.\d+\.\d+\.\d+)", text)
                        if m:
                            return m.group(1)
            except Exception:
                continue
        return ""

    def _fetch_public_ip(self):
        """后台获取公网 IP"""
        ip = self.get_public_ip()
        if ip:
            self.public_ip = ip

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except (OSError, socket.error):
            return "127.0.0.1"

    def on_speed_update(self, down, up, total_recv=0, total_sent=0):
        self.down_speed = max(0, down)
        self.up_speed = max(0, up)
        self.total_recv = total_recv
        self.total_sent = total_sent
        self.update()

    def update_perf(self):
        try:
            self.cpu = psutil.cpu_percent()
            self.mem = psutil.virtual_memory().percent

            # GPU 读取
            try:
                # 尝试加载 nvml.dll
                nvml = ctypes.WinDLL(r"C:\Windows\System32\nvml.dll")
            except OSError:
                # 尝试用 find_library 查找
                lib_path = ctypes.util.find_library("nvml")
                if lib_path:
                    try:
                        nvml = ctypes.WinDLL(lib_path)
                    except OSError:
                        nvml = None
                else:
                    nvml = None

            if nvml:
                # 定义函数原型
                nvmlInit = nvml.nvmlInit
                nvmlInit.restype = ctypes.c_int
                nvmlDeviceGetHandleByIndex = nvml.nvmlDeviceGetHandleByIndex
                nvmlDeviceGetHandleByIndex.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)]
                nvmlDeviceGetUtilizationRates = nvml.nvmlDeviceGetUtilizationRates
                nvmlDeviceGetUtilizationRates.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]

                ret = nvmlInit()
                if ret == 0:  # NVML_SUCCESS
                    handle = ctypes.c_void_p()
                    ret = nvmlDeviceGetHandleByIndex(0, ctypes.byref(handle))
                    if ret == 0:
                        util = ctypes.c_uint()
                        ret = nvmlDeviceGetUtilizationRates(handle, ctypes.byref(util))
                        if ret == 0:
                            self.gpu = util.value
                        # GPU memory info
                        try:
                            class nvmlMemory_t(ctypes.Structure):
                                _fields_ = [("total", ctypes.c_ulonglong), ("free", ctypes.c_ulonglong), ("used", ctypes.c_ulonglong)]
                            mem_info = nvmlMemory_t()
                            nvmlDeviceGetMemoryInfo = nvml.nvmlDeviceGetMemoryInfo
                            nvmlDeviceGetMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(nvmlMemory_t)]
                            nvmlDeviceGetMemoryInfo.restype = ctypes.c_int
                            if nvmlDeviceGetMemoryInfo(handle, ctypes.byref(mem_info)) == 0:
                                self.gpu_mem_total = mem_info.total
                                self.gpu_mem_used = mem_info.used
                        except Exception:
                            pass
                        # GPU clock
                        try:
                            nvmlDeviceGetClockInfo = nvml.nvmlDeviceGetClockInfo
                            nvmlDeviceGetClockInfo.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)]
                            nvmlDeviceGetClockInfo.restype = ctypes.c_int
                            clock = ctypes.c_uint()
                            if nvmlDeviceGetClockInfo(handle, 0, ctypes.byref(clock)) == 0:
                                self.gpu_clock = clock.value
                        except Exception:
                            pass
                        # GPU power
                        try:
                            nvmlDeviceGetPowerUsage = nvml.nvmlDeviceGetPowerUsage
                            nvmlDeviceGetPowerUsage.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
                            nvmlDeviceGetPowerUsage.restype = ctypes.c_int
                            power = ctypes.c_uint()
                            if nvmlDeviceGetPowerUsage(handle, ctypes.byref(power)) == 0:
                                self.gpu_power = power.value
                        except Exception:
                            pass
                    else:
                        self.gpu = 0
                else:
                    self.gpu = 0
            else:
                self.gpu = 0

            self._update_disk_usage()
            self._update_uptime()
            self.update()
        except Exception:
            # 出错时 GPU 设为 0
            self.gpu = 0
            self.update()

    def _update_disk_usage(self):
        """遍历磁盘分区，计算各区使用率和总使用率"""
        import psutil
        self.disk_usage = {}
        total_used = 0
        total_all = 0
        for part in psutil.disk_partitions():
            if (not part.opts.startswith("cdrom")
                    and not part.device.startswith("\\\\")
                    and part.fstype not in ("", "udf", "iso9660")):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    if usage.total > 0:
                        letter = part.mountpoint.split(":")[0].rstrip("\\").upper()
                        self.disk_usage[f"disk_{letter}"] = usage.percent
                        total_used += usage.used
                        total_all += usage.total
                except (PermissionError, OSError):
                    pass
        if total_all > 0:
            self.disk_usage["disk_total"] = int(total_used / total_all * 100)
        else:
            self.disk_usage["disk_total"] = 0

    def _update_uptime(self):
        """计算系统已运行时长"""
        import time
        boot_time = psutil.boot_time()
        self._uptime_seconds = int(time.time() - boot_time)
        total_minutes = self._uptime_seconds // 60
        total_hours = total_minutes // 60
        days = total_hours // 24
        hours = total_hours % 24
        minutes = total_minutes % 60

        rp = self._i18n["run_prefix"]
        mu_min = self._i18n["min_unit"]
        mu_hour = self._i18n["hour_unit"]
        mu_day = self._i18n["day_unit"]
        mu_month = self._i18n["month_unit"]

        if days >= 30:
            months = days // 30
            remaining_days = days % 30
            self.uptime = f"{rp}{months}{mu_month}{remaining_days}{mu_day}"
        elif days >= 1:
            self.uptime = f"{rp}{days}{mu_day}"
        elif total_hours < 3:
            self.uptime = f"{rp}{total_minutes}{mu_min}"
        else:
            if minutes >= 30:
                self.uptime = f"{rp}{hours}.5{mu_hour}"
            else:
                self.uptime = f"{rp}{hours}{mu_hour}"

    def update_clock(self):
        self.now = datetime.now()
        if LUNAR_AVAILABLE:
            try:
                lunar = ZhDate.from_datetime(self.now)
                from lunar_python import Solar as _Solar
                _lunar = _Solar.fromDate(self.now).getLunar()
                self.lunar_text = f"{self._i18n['lunar']} {_lunar.getMonthInChinese()}月{_lunar.getDayInChinese()}"
            except Exception:
                self.lunar_text = self._i18n['lunar_error']
        else:
            self.lunar_text = self._i18n['not_installed']

        current, next_name, days = get_next_term_info(self.now.year, self.now.month, self.now.day)
        if current:
            self.term_display = translate_term(current)
        elif next_name is not None and days is not None:
            trans_name = translate_term(next_name)
            self.term_display = f"{self._i18n['distance']}{trans_name} {days}{self._i18n['day_unit']}"
        else:
            self.term_display = ""
        self.update()

