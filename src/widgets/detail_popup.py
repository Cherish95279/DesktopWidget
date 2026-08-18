# -*- coding: utf-8 -*-
import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import psutil


class DetailPopup(QWidget):
    """
    鼠标悬停时显示的详细信息浮动面板。
    无边框、半透明背景，跟随主窗口槽位位置弹出。
    根据 is_pro_enabled() 区分 Free/Pro 显示内容。
    """

    F_POPUP_WIDTH = 220
    F_POPUP_MIN_HEIGHT = 60
    F_BG_COLOR = QColor(245, 246, 250, 220)    # 浅灰半透明
    F_BORDER_COLOR = QColor(208, 213, 221, 180) # 浅灰边框半透明
    F_TEXT_COLOR = QColor(51, 51, 51)           # #333333
    F_SECONDARY_COLOR = QColor(102, 102, 102)  # #666666
    F_PADDING = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self._main_window = parent
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

        self._current_slot_key = None
        self._current_content_key = None
        self._fade_timer = QTimer()
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self.hide)

        self._setup_ui()

    def _setup_ui(self):
        self.setMinimumWidth(220)
        self.setMaximumWidth(350)
        self.setMinimumHeight(60)
        self.setMaximumHeight(9999)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 圆角背景
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 8, 8)
        painter.setClipPath(path)

        painter.fillRect(rect, self.F_BG_COLOR)

        # 边框
        pen = QPen(self.F_BORDER_COLOR, 1)
        painter.setPen(pen)
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 18, 8)

    def show_for_slot(self, slot_key, content_key, slot_rect):
        """
        Show popup next to the slot.
        """
        # Skip update if same slot and visible (anti-flicker)
        if (self._current_slot_key == slot_key and
                self._current_content_key == content_key and
                self.isVisible()):
            return

        self._current_slot_key = slot_key
        self._current_content_key = content_key

        # Build content
        text = self._build_content(content_key)
        self._render_text(text)

        # Calculate position: prefer right side, fallback to left
        from PyQt6.QtWidgets import QApplication
        main_pos = self._main_window.mapToGlobal(QPoint(0, 0))
        popup_x = main_pos.x() + slot_rect.x() + slot_rect.width() + 5
        popup_y = main_pos.y() + slot_rect.y()

        screen = QApplication.primaryScreen()
        if screen:
            screen_rect = screen.availableGeometry()
            # If right side overflows, show on left side of slot
            if popup_x + self.width() > screen_rect.right():
                popup_x = main_pos.x() + slot_rect.x() - self.width() - 5
            # If left side also overflows, clamp to screen
            if popup_x < screen_rect.left():
                popup_x = screen_rect.left() + 5
            if popup_y + self.height() > screen_rect.bottom():
                popup_y = screen_rect.bottom() - self.height() - 5
            if popup_y < screen_rect.top():
                popup_y = screen_rect.top()

        self.move(popup_x, popup_y)
        self.raise_()
        self.show()

    def _build_content(self, content_key):
        """根据内容类型和付费状态构建显示文本"""
        from ..utils import is_pro_enabled
        is_pro = is_pro_enabled()
        mw = self._main_window
        if not mw:
            return ""

        lines = []
        now = getattr(mw, 'now', None)

        if content_key in ('cpu',):
            cpu_val = int(getattr(mw, 'cpu', 0))
            lines.append(self.tr("CPU 使用率：{}%").format(cpu_val))
            if is_pro:
                # Pro：尝试获取温度、频率、核心数
                try:
                    freq = psutil.cpu_freq()
                    if freq:
                        lines.append(self.tr("频率：{:.0f} MHz").format(freq.current))
                except Exception:
                    pass
                lines.append(self.tr("核心/线程：{}/{}").format(
                    psutil.cpu_count(logical=False) or "?",
                    psutil.cpu_count(logical=True) or "?"
                ))
                try:
                    import subprocess
                    result = subprocess.run(
                        ['wmic', '/namespace:\\\\root\\\\wmi', 'PATH', 'MSAcpi_ThermalZoneTemperature', 'get', 'CurrentTemperature'],
                        capture_output=True, text=True, timeout=5,
                        creationflags=0x08000000
                    )
                    for line in result.stdout.strip().split('\n'):
                        line = line.strip()
                        if line and line.isdigit():
                            temp_c = (int(line) - 2732) / 10.0
                            lines.append(self.tr("温度：{:.1f}°C").format(temp_c))
                            break
                except Exception:
                    pass

        elif content_key in ('gpu',):
            gpu_val = int(getattr(mw, 'gpu', 0))
            lines.append(self.tr("GPU 使用率：{}%").format(gpu_val))
            if is_pro:
                gpu_mem_total = getattr(mw, 'gpu_mem_total', 0)
                gpu_mem_used = getattr(mw, 'gpu_mem_used', 0)
                if gpu_mem_total > 0:
                    mem_pct = gpu_mem_used / gpu_mem_total * 100
                    lines.append(self.tr("显存使用率：{:.0f}%").format(mem_pct))
                    lines.append(self.tr("显存：{:.1f} GB / {:.1f} GB").format(gpu_mem_used/1024**3, gpu_mem_total/1024**3))
                gpu_clock = getattr(mw, 'gpu_clock', 0)
                if gpu_clock > 0:
                    lines.append(self.tr("频率：{} MHz").format(gpu_clock))
                gpu_power = getattr(mw, 'gpu_power', 0)
                if gpu_power > 0:
                    lines.append(self.tr("功耗：{:.1f} W").format(gpu_power / 1000))

        elif content_key in ('memory', 'mem'):
            mem_val = int(getattr(mw, 'mem', 0))
            lines.append(self.tr("内存使用率：{}%").format(mem_val))
            if is_pro:
                try:
                    mem_info = psutil.virtual_memory()
                    total_gb = mem_info.total / (1024 ** 3)
                    used_gb = mem_info.used / (1024 ** 3)
                    avail_gb = mem_info.available / (1024 ** 3)
                    lines.append(self.tr("已用：{:.1f} GB / 总计：{:.1f} GB").format(used_gb, total_gb))
                    lines.append(self.tr("可用：{:.1f} GB").format(avail_gb))
                except Exception:
                    pass

        elif content_key in ('netspeed',):
            down = getattr(mw, 'down_speed', 0.0)
            up = getattr(mw, 'up_speed', 0.0)
            lines.append(self.tr("下载：{:.1f} Mb/s").format(down))
            lines.append(self.tr("上传：{:.1f} Mb/s").format(up))
            if is_pro:
                total_recv = getattr(mw, 'total_recv', 0)
                total_sent = getattr(mw, 'total_sent', 0)
                recv_mb = total_recv / (1024 * 1024)
                sent_mb = total_sent / (1024 * 1024)
                if recv_mb >= 1024:
                    lines.append(self.tr("累计下载：{:.1f} GB").format(recv_mb / 1024))
                else:
                    lines.append(self.tr("累计下载：{:.1f} MB").format(recv_mb))
                if sent_mb >= 1024:
                    lines.append(self.tr("累计上传：{:.1f} GB").format(sent_mb / 1024))
                else:
                    lines.append(self.tr("累计上传：{:.1f} MB").format(sent_mb))

        elif content_key in ('weather',):
            weather = getattr(mw, 'weather', {})
            lines.append(self.tr("天气：{}").format(weather.get('weather', '--')))
            lines.append(self.tr("温度：{}℃").format(weather.get('temp', '--')))
            if is_pro:
                wind = weather.get('wind', '')
                if wind:
                    import re
                    m = re.match(r'([\u4e00-\u9fa5A-Za-z]+)([\d.]+)(.*)', wind)
                    if m:
                        direction, speed, unit = m.groups()
                        dir_trans = self.tr(direction)
                        if unit.strip() == '级':
                            lines.append(self.tr('风速：{}').format(dir_trans + ' ' + speed + '级'))
                        else:
                            lines.append(self.tr('风速：{}').format(dir_trans + ' ' + speed + ' ' + unit.strip()))
                    else:
                        lines.append(self.tr('风速：{}').format(wind))
                at = weather.get('apparent_temp', '--')
                if at != '--':
                    lines.append(self.tr("体感温度：{}℃").format(at))
                hum = weather.get('humidity', '--')
                if hum != '--':
                    lines.append(self.tr("湿度：{}%").format(hum))
                pres = weather.get('pressure', '--')
                if pres != '--':
                    lines.append(self.tr("气压：{:.0f} hPa").format(pres))

        elif content_key in ('ip',):
            public_ip = getattr(mw, 'public_ip', '')
            if not public_ip:
                public_ip = getattr(mw, 'local_ip', '--')
            lines.append(self.tr("公网 IP：{}").format(public_ip))
            if is_pro:
                local = getattr(mw, 'local_ip', '--')
                lines.append(self.tr("本机 IP：{}").format(local))
                server = getattr(mw, 'server_ip', '')
                # 只在扫描完成且不是默认值时显示内网服务器
                if server and server != '扫描中...' and server != '192.168.0.135':
                    lines.append(self.tr("内网服务器：{}").format(server))
                try:
                    from PyQt6.QtCore import QSettings
                    isp = QSettings("MyDesktopApp", "WeatherSettings").value("ip_isp", "")
                    if isp:
                        lines.append(self.tr("运营商：{}").format(isp))
                except Exception:
                    pass

        elif content_key in ('date',):
            if now:
                lines.append(now.strftime(self.tr("%Y/%m/%d %A")))
            if is_pro:
                if now:
                    day_of_year = now.timetuple().tm_yday
                    lines.append(self.tr("年内第 {} 天").format(day_of_year))

        elif content_key in ('lunar',):
            lunar_text = getattr(mw, 'lunar_text', '')
            if is_pro:
                try:
                    from lunar_python import Solar
                    now = getattr(mw, 'now', None)
                    if now:
                        solar = Solar.fromDate(now)
                        lunar = solar.getLunar()
                        # 农历日期
                        lines.append(self.tr("农历：{}月{}").format(lunar.getMonthInChinese(), lunar.getDayInChinese()))
                        # 干支（拼音）
                        ganzhi_map = {"甲子":"JiaZi","乙丑":"YiChou","丙寅":"BingYin","丁卯":"DingMao","戊辰":"WuChen","己巳":"JiSi","庚午":"GengWu","辛未":"XinWei","壬申":"RenShen","癸酉":"GuiYou","甲戌":"JiaXu","乙亥":"YiHai","丙子":"BingZi","丁丑":"DingChou","戊寅":"WuYin","己卯":"JiMao","庚辰":"GengChen","辛巳":"XinSi","壬午":"RenWu","癸未":"GuiWei","甲申":"JiaShen","乙酉":"YiYou","丙戌":"BingXu","丁亥":"DingHai","戊子":"WuZi","己丑":"JiChou","庚寅":"GengYin","辛卯":"XinMao","壬辰":"RenChen","癸巳":"GuiSi","甲午":"JiaWu","乙未":"YiWei","丙申":"BingShen","丁酉":"DingYou","戊戌":"WuXu","己亥":"JiHai","庚子":"GengZi","辛丑":"XinChou","壬寅":"RenYin","癸卯":"GuiMao","甲辰":"JiaChen","乙巳":"YiSi","丙午":"BingWu","丁未":"DingWei","戊申":"WuShen","己酉":"JiYou","庚戌":"GengXu","辛亥":"XinHai","壬子":"RenZi","癸丑":"GuiChou","甲寅":"JiaYin","乙卯":"YiMao","丙辰":"BingChen","丁巳":"DingSi","戊午":"WuWu","己未":"JiWei","庚申":"GengShen","辛酉":"XinYou","壬戌":"RenXu","癸亥":"GuiHai"}
                        ganzhi = lunar.getYearInGanZhi()
                        # 中文直接显示，英文用拼音
                        from PyQt6.QtCore import QSettings
                        lang = QSettings("MyDesktopApp", "WeatherSettings").value("language", "")
                        if lang and lang != "zh_CN" and lang != "zh_TW":
                            ganzhi = ganzhi_map.get(ganzhi, ganzhi)
                        lines.append(self.tr("干支：{}年").format(ganzhi))
                        # 生肖（拼音）
                        zodiac_map = {"鼠":"Shu(Rat)","牛":"Niu(Ox)","虎":"Hu(Tiger)","兔":"Tu(Rabbit)","龙":"Long(Dragon)","蛇":"She(Snake)","马":"Ma(Horse)","羊":"Yang(Goat)","猴":"Hou(Monkey)","鸡":"Ji(Rooster)","狗":"Gou(Dog)","猪":"Zhu(Pig)"}
                        zodiac = lunar.getYearShengXiao()
                        if lang and lang != "zh_CN" and lang != "zh_TW":
                            zodiac = zodiac_map.get(zodiac, zodiac)
                        lines.append(self.tr("生肖：{}").format(zodiac))
                except Exception:
                    pass
            else:
                lines.append(lunar_text if lunar_text else '--')

        elif content_key in ('term',):
            term = getattr(mw, 'term_display', '')
            lines.append(self.tr("节气：{}").format(term if term else '--'))
            if is_pro:
                try:
                    from lunar_python import Solar
                    now = getattr(mw, 'now', None)
                    if now:
                        solar = Solar.fromDate(now)
                        lunar = solar.getLunar()
                        from ..solar_terms import translate_term
                        # 当前节气
                        prev = lunar.getPrevJieQi()
                        if prev:
                            ps = prev.getSolar()
                            lines.append(self.tr("当前节气：{}").format(translate_term(prev.getName())))
                            lines.append(self.tr("精确时间：{}月{}日 {}:{:02d}").format(ps.getMonth(), ps.getDay(), ps.getHour(), ps.getMinute()))
                        # 下一节气
                        nxt = lunar.getNextJieQi()
                        if nxt:
                            ns = nxt.getSolar()
                            lines.append(self.tr("下一节气：{}").format(translate_term(nxt.getName())))
                            lines.append(self.tr("精确时间：{}月{}日 {}:{:02d}").format(ns.getMonth(), ns.getDay(), ns.getHour(), ns.getMinute()))
                        # 所属季节
                        season = lunar.getSeason()
                        if season:
                            # 孟/仲/季 + 季节 → 只保留季节
                            season_map = {"孟春":"春","仲春":"春","季春":"春","孟夏":"夏","仲夏":"夏","季夏":"夏","孟秋":"秋","仲秋":"秋","季秋":"秋","孟冬":"冬","仲冬":"冬","季冬":"冬"}
                            simple_season = season_map.get(season, season)
                            lines.append(self.tr("所属季节：{}").format(self.tr(simple_season)))
                except Exception:
                    pass

        elif content_key in ('uptime',):
            uptime = getattr(mw, 'uptime', '')
            lines.append(self.tr("已运行：{}").format(uptime))
            if is_pro:
                try:
                    boot_time = psutil.boot_time()
                    from datetime import datetime
                    boot_dt = datetime.fromtimestamp(boot_time)
                    lines.append(self.tr("启动时间：{}").format(boot_dt.strftime('%Y/%m/%d %H:%M')))
                except Exception:
                    pass

        elif content_key == 'disk_total':
            disk = getattr(mw, 'disk_usage', {})
            total_pct = int(disk.get('disk_total', 0))
            lines.append(self.tr("总磁盘使用率：{}%").format(total_pct))
            if is_pro:
                try:
                    all_total = 0
                    all_used = 0
                    all_free = 0
                    for part in psutil.disk_partitions():
                        if not part.opts.startswith('cdrom') and part.fstype:
                            try:
                                du = psutil.disk_usage(part.mountpoint)
                                all_total += du.total
                                all_used += du.used
                                all_free += du.free
                                disk_letter = part.mountpoint.split(':')[0]
                                lines.append(self.tr("{}: {:.0f}GB / {:.0f}GB").format(disk_letter, du.used/1024**3, du.total/1024**3))
                            except Exception:
                                pass
                    lines.append(self.tr("总容量：{:.1f} GB").format(all_total / 1024**3))
                    lines.append(self.tr("已用：{:.1f} GB").format(all_used / 1024**3))
                    lines.append(self.tr("可用：{:.1f} GB").format(all_free / 1024**3))
                except Exception:
                    pass

        # 盘符（如 disk_c, disk_d 等）
        if content_key and content_key.startswith('disk_') and content_key != 'disk_total':
            disk = getattr(mw, 'disk_usage', {})
            letter = content_key.replace('disk_', '').upper()
            pct = int(disk.get(content_key, 0))
            lines.append(self.tr("{} 盘使用率：{}%").format(letter, pct))
            if is_pro:
                try:
                    usage = psutil.disk_usage(letter + ':/')
                    total_gb = usage.total / (1024 ** 3)
                    used_gb = usage.used / (1024 ** 3)
                    free_gb = usage.free / (1024 ** 3)
                    lines.append(self.tr("总容量：{:.1f} GB").format(total_gb))
                    lines.append(self.tr("已用：{:.1f} GB").format(used_gb))
                    lines.append(self.tr("可用：{:.1f} GB").format(free_gb))
                    try:
                        for part in psutil.disk_partitions():
                            if part.mountpoint.upper().startswith(letter + ':'):
                                opts = part.opts.lower()
                                if 'ssd' in opts:
                                    lines.append(self.tr("类型：SSD"))
                                elif 'hdd' in opts:
                                    lines.append(self.tr("类型：HDD"))
                                else:
                                    lines.append(self.tr("类型：{}").format(part.fstype))
                                break
                    except Exception:
                        pass
                except Exception:
                    pass

        elif content_key in ('resolution',):
            res = getattr(mw, 'screen_res', '--')
            lines.append(self.tr("分辨率：{}").format(res))
            refresh_rate = getattr(mw, 'refresh_rate', 0)
            if refresh_rate > 0:
                lines.append(self.tr("刷新率：{}Hz").format(refresh_rate))
            if is_pro:
                try:
                    from PyQt6.QtWidgets import QApplication
                    screen = QApplication.primaryScreen()
                    if screen:
                        geom = screen.geometry()
                        virt = screen.virtualGeometry()
                        if virt.width() > 0:
                            scale = geom.width() / virt.width() * 100
                            lines.append(self.tr("缩放：{:.0f}%").format(scale))
                except Exception:
                    pass

        if not lines:
            lines.append(self.tr("暂无数据"))

        if not is_pro:
            lines.append("")
            lines.append(self.tr("Pro · 更多详情"))

        return lines

    def _render_text(self, lines):
        """将文本行绘制到弹窗上"""
        self._cached_lines = lines
        line_count = len(lines)
        text_height = line_count * 22 + self.F_PADDING * 2
        self.setFixedHeight(max(self.F_POPUP_MIN_HEIGHT, text_height))
        # 根据最长行计算宽度
        from PyQt6.QtGui import QFontMetrics
        font = QFont("Microsoft YaHei", 11)
        fm = QFontMetrics(font)
        max_width = 0
        for line in lines:
            w = fm.horizontalAdvance(line)
            if w > max_width:
                max_width = w
        popup_width = max_width + self.F_PADDING * 2 + 10
        popup_width = max(220, min(popup_width, 350))
        self.setFixedWidth(popup_width)
        self.update()

    def paintText(self, painter):
        """绘制文字内容"""
        if not hasattr(self, '_cached_lines') or not self._cached_lines:
            return

        painter.setPen(self.F_TEXT_COLOR)
        font = QFont("Microsoft YaHei", 11)
        painter.setFont(font)

        y_offset = self.F_PADDING
        for i, line in enumerate(self._cached_lines):
            # Pro 提示行：右对齐 + 小字号
            if line.startswith("Pro"):
                painter.setPen(QColor(22, 119, 255))
                small_font = QFont("Microsoft YaHei", 9)
                painter.setFont(small_font)
                painter.drawText(
                    self.F_PADDING, y_offset,
                    self.width() - self.F_PADDING * 2, 18,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    line
                )
                painter.setFont(font)
            else:
                painter.setPen(self.F_TEXT_COLOR)
                painter.drawText(
                    self.F_PADDING, y_offset,
                    self.width() - self.F_PADDING * 2, 22,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    line
                )
            y_offset += 22

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 8, 8)
        painter.setClipPath(path)

        painter.fillRect(rect, self.F_BG_COLOR)

        pen = QPen(self.F_BORDER_COLOR, 1)
        painter.setPen(pen)
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 8, 18)

        self.paintText(painter)

    def start_fade_out(self, delay_ms=2000):
        self._fade_timer.start(delay_ms)

    def stop_fade_out(self):
        self._fade_timer.stop()

    def enterEvent(self, event):
        """鼠标进入弹窗时取消消失"""
        self._fade_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开弹窗时开始消失"""
        self.start_fade_out(1000)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """点击弹窗"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否点击了 Pro 提示行
            if hasattr(self, '_cached_lines') and self._cached_lines:
                # Pro 提示行在最后一行，计算其 y 位置
                pro_line_idx = len(self._cached_lines) - 1
                pro_y = self.F_PADDING + pro_line_idx * 22
                click_y = event.position().toPoint().y()
                if click_y >= pro_y:
                    # 点击了 Pro 提示行
                    self._on_pro_clicked()
                    return
        super().mousePressEvent(event)

    def _on_pro_clicked(self):
        """点击 Pro 提示行，触发购买"""
        try:
            from ..utils import is_pro_enabled
            pro = is_pro_enabled()
            if pro:
                return
            from PyQt6.QtCore import QSettings
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            dev_version = settings.value("dev_version", "", type=str)
            if dev_version:
                is_store = (dev_version == "store")
            else:
                from ..updater import is_store_version
                is_store = is_store_version()
            if is_store:
                # 商店版：调用购买 API
                from ..store_license import request_purchase
                window_handle = int(self._main_window.winId())
                request_purchase(callback=self._on_purchase_result, window_handle=window_handle)
            else:
                # exe版/开发环境：打开商店网页
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl("ms-windows-store://pdp/?productid=9P6GSZ8NNW52"))
        except Exception as e:
            print(f"[Pro] click error: {e}")

    def _on_purchase_result(self, result):
        """购买结果回调"""
        if result is True:
            # 购买成功，刷新显示
            self.hide()

    def hideEvent(self, event):
        self._fade_timer.stop()
        super().hideEvent(event)

    def tr(self, text):
        return QCoreApplication.translate("DetailPopup", text)
