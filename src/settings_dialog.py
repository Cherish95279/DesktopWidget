from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QIcon
import requests
import certifi
import sys
import tempfile
import os
import winreg

from .constants import VERSION
from .updater import UpdateChecker, Downloader, Updater
from .utils import resource_path
from .region_data import REGIONS


def set_autostart(enabled: bool):
    """设置开机自启动"""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "DesktopWidget"
    exe_path = sys.executable
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except PermissionError:
        return False
    except OSError:
        return False


def get_autostart_status() -> bool:
    """获取开机自启动状态"""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "DesktopWidget"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except PermissionError:
        return False


class SettingsDialog(QDialog):
    def __init__(self, parent=None, initial_page="weather"):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowSystemMenuHint)
        self.setWindowIcon(QIcon(resource_path("icons/app.ico")))

        self.download_url = None
        self.downloader = None
        self.downloaded_setup_path = None
        self.has_update = False
        self.latest_version_info = {}
        self.checker = None

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---------- 左侧目录 ----------
        left_panel = QWidget()
        left_panel.setFixedWidth(100)
        left_panel.setStyleSheet("background-color: #f0f0f0;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 20, 0, 20)
        left_layout.setSpacing(0)

        self.cat_buttons = []
        self.cat_labels = ["常规设置", "天气设置", "主题", "检查更新", "关于"]

        for i, label in enumerate(self.cat_labels):
            btn = QPushButton(label)
            btn.setFixedHeight(40)
            btn.setFlat(True)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: center;
                    font-size: 12px;
                    color: #333;
                    border: none;
                    background: transparent;
                }
                QPushButton:hover {
                    background: #e0e0e0;
                }
                QPushButton:checked {
                    background: #d0e4ff;
                }
            """)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            if i == 0:
                btn.setChecked(True)
            left_layout.addWidget(btn)
            self.cat_buttons.append(btn)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # ---------- 右侧内容 ----------
        self.stacked = QStackedWidget()
        self.stacked.setStyleSheet("background-color: rgba(245, 245, 245, 0.9);")

        # 页面0：常规设置
        page_general = QWidget()
        general_layout = QVBoxLayout(page_general)
        general_layout.setContentsMargins(15, 20, 15, 15)
        general_layout.setSpacing(10)

        # ---------- 开机自启动（默认勾选） ----------
        self.autostart_widget = QWidget(self)
        autostart_layout = QHBoxLayout(self.autostart_widget)
        autostart_layout.setContentsMargins(0, 0, 0, 0)
        autostart_layout.setSpacing(6)

        self.autostart_icon = QLabel("✅", self)
        self.autostart_icon.setStyleSheet("font-size: 16px;")
        autostart_layout.addWidget(self.autostart_icon)

        self.autostart_label = QLabel("开机自启动", self)
        self.autostart_label.setStyleSheet("font-size: 12px; color: #333;")
        autostart_layout.addWidget(self.autostart_label)

        autostart_layout.addStretch()

        self.autostart_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        self.autostart_widget.mousePressEvent = self.on_autostart_widget_clicked

        # 强制默认勾选，并写入注册表
        self.autostart_checked = True
        set_autostart(True)
        self.update_autostart_display()

        general_layout.addWidget(self.autostart_widget)

        # 天气显示地区
        region_label = QLabel("天气显示地区")
        region_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        general_layout.addWidget(region_label)

        region_layout = QHBoxLayout()
        self.province_combo = QComboBox()
        self.province_combo.setMinimumWidth(80)
        self.city_combo = QComboBox()
        self.city_combo.setMinimumWidth(80)
        self.county_combo = QComboBox()
        self.county_combo.setMinimumWidth(80)
        region_layout.addWidget(self.province_combo)
        region_layout.addWidget(self.city_combo)
        region_layout.addWidget(self.county_combo)
        region_layout.addStretch()
        general_layout.addLayout(region_layout)

        general_layout.addStretch()
        self.stacked.addWidget(page_general)

        # 页面1：天气设置
        page_weather = QWidget()
        weather_layout = QVBoxLayout(page_weather)
        weather_layout.setContentsMargins(15, 20, 15, 15)
        weather_layout.setSpacing(5)

        lbl_url = QLabel("API 地址")
        weather_layout.addWidget(lbl_url)
        url_layout = QHBoxLayout()
        self.url_combo = QComboBox()
        self.url_combo.addItems(["高德", "自定义"])
        self.url_combo.currentTextChanged.connect(self.on_provider_changed)
        url_layout.addWidget(self.url_combo)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("请输入 API 地址")
        url_layout.addWidget(self.url_edit)
        weather_layout.addLayout(url_layout)

        lbl_key = QLabel("API 密钥")
        weather_layout.addWidget(lbl_key)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("请输入 API 密钥")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        weather_layout.addWidget(self.key_edit)

        status_layout = QHBoxLayout()
        self.status_label = QLabel("状态：未配置")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        freq_label1 = QLabel("每")
        status_layout.addWidget(freq_label1)
        self.freq_spin = QSpinBox()
        self.freq_spin.setRange(1, 1440)
        self.freq_spin.setSuffix(" 分钟")
        self.freq_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.freq_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 2px 4px;
                background: white;
            }
        """)
        status_layout.addWidget(self.freq_spin)
        freq_label2 = QLabel("刷新天气")
        status_layout.addWidget(freq_label2)
        weather_layout.addLayout(status_layout)

        spacer = QLabel("")
        spacer.setFixedHeight(10)
        weather_layout.addWidget(spacer)

        info_label = QLabel("说明：API地址和密钥可在高德API免费获取，5000次/月，本程序默认每2小时更新一次天气")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; font-size: 12px; font-weight: normal;")
        weather_layout.addWidget(info_label)

        weather_layout.addStretch()
        self.stacked.addWidget(page_weather)

        # 页面2：主题（占位）
        page_theme = QWidget()
        theme_layout = QVBoxLayout(page_theme)
        theme_layout.setContentsMargins(15, 20, 15, 15)
        theme_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        theme_label = QLabel("主题功能开发中，敬请期待...")
        theme_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        theme_label.setStyleSheet("font-size: 14px; color: #666;")
        theme_layout.addWidget(theme_label)
        self.stacked.addWidget(page_theme)

        # 页面3：检查更新
        page_update = QWidget()
        update_layout = QVBoxLayout(page_update)
        update_layout.setContentsMargins(15, 20, 15, 15)
        update_layout.setSpacing(8)

        self.version_label = QLabel(f"当前版本：{VERSION}")
        update_layout.addWidget(self.version_label)

        self.latest_version_label = QLabel("最新版本：检查中...")
        update_layout.addWidget(self.latest_version_label)

        self.update_status_label = QLabel("")
        update_layout.addWidget(self.update_status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        update_layout.addWidget(self.progress_bar)

        self.check_update_btn = QPushButton("检查更新")
        self.check_update_btn.setMinimumHeight(28)
        self.check_update_btn.clicked.connect(self.check_update_manually)
        update_layout.addWidget(self.check_update_btn)

        self.install_update_btn = QPushButton("立即重启安装")
        self.install_update_btn.setVisible(False)
        self.install_update_btn.setMinimumHeight(28)
        self.install_update_btn.clicked.connect(self.install_update)
        update_layout.addWidget(self.install_update_btn)

        update_layout.addStretch()
        self.stacked.addWidget(page_update)

        # 页面4：关于
        page_about = QWidget()
        about_layout = QVBoxLayout(page_about)
        about_layout.setContentsMargins(15, 20, 15, 15)
        about_layout.setSpacing(12)
        about_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(f"珍爱桌面小工具 {VERSION}")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(title)

        author = QLabel("作者：Cherish95279")
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(author)

        thanks = QLabel("致谢：fqk_123456")
        thanks.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(thanks)

        github = QLabel('<a href="https://github.com/Cherish95279/DesktopWidget">GitHub：https://github.com/Cherish95279/DesktopWidget</a>')
        github.setOpenExternalLinks(True)
        github.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(github)

        about_layout.addStretch()
        self.stacked.addWidget(page_about)

        # ---------- 右侧布局 ----------
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.stacked)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.setContentsMargins(0, 0, 0, 5)
        right_layout.addLayout(btn_layout)

        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        right_widget.setStyleSheet("background-color: rgba(245, 245, 245, 0.9);")
        main_layout.addWidget(right_widget)

        # 信号连接
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)
        for i, btn in enumerate(self.cat_buttons):
            btn.clicked.connect(lambda checked, idx=i: self.switch_page(idx))

        # 加载区域数据
        self.regions_data = REGIONS
        self.load_regions_data()

        self.load_settings()

        page_index = {"general": 0, "weather": 1, "theme": 2, "update": 3, "about": 4}.get(initial_page, 0)
        self.switch_page(page_index)

        self._auto_checked = False
        self.update_red_dot()

    # ---------- 开机自启动 ----------
    def update_autostart_display(self):
        """只更新图标，文字颜色永远不变"""
        if self.autostart_checked:
            self.autostart_icon.setText("✅")
        else:
            self.autostart_icon.setText("⬜")
        self.autostart_label.setStyleSheet("font-size: 12px; color: #333;")

    def on_autostart_widget_clicked(self, event):
        self.autostart_checked = not self.autostart_checked
        self.update_autostart_display()
        if self.autostart_checked:
            if not set_autostart(True):
                QMessageBox.warning(self, "提示", "设置开机自启动失败，请检查权限")
                self.autostart_checked = False
                self.update_autostart_display()
        else:
            set_autostart(False)

    # ---------- 区域数据 ----------
    def load_regions_data(self):
        provinces = list(self.regions_data.keys())
        self.province_combo.clear()
        self.province_combo.addItem("请选择省份")
        self.province_combo.addItems(provinces)
        self.province_combo.currentTextChanged.connect(self.on_province_changed)
        self.city_combo.currentTextChanged.connect(self.on_city_changed)

    def on_province_changed(self, province):
        self.city_combo.clear()
        self.city_combo.addItem("请选择城市")
        if province and province in self.regions_data:
            cities = list(self.regions_data[province].get("cities", {}).keys())
            self.city_combo.addItems(cities)
        self.county_combo.clear()
        self.county_combo.addItem("请选择区县")

    def on_city_changed(self, city):
        self.county_combo.clear()
        self.county_combo.addItem("请选择区县")
        province = self.province_combo.currentText()
        if province and city and province in self.regions_data:
            counties = self.regions_data[province].get("cities", {}).get(city, {}).get("counties", [])
            self.county_combo.addItems(counties)

    # ---------- 页面切换 ----------
    def switch_page(self, index):
        self.stacked.setCurrentIndex(index)
        for i, btn in enumerate(self.cat_buttons):
            btn.setChecked(i == index)
        if index == 3 and not self._auto_checked:
            self._auto_checked = True
            self.check_update_manually()

    # ---------- 天气设置 ----------
    def on_provider_changed(self, text):
        if text == "高德":
            self.url_edit.setText("https://restapi.amap.com")
            self.url_edit.setReadOnly(True)
        else:
            self.url_edit.clear()
            self.url_edit.setReadOnly(False)

    def load_settings(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        url = settings.value("api_url", "")
        key = settings.value("api_key", "")
        freq = int(settings.value("refresh_minutes", 120))
        self.url_edit.setText(url)
        self.key_edit.setText(key)
        self.freq_spin.setValue(freq)
        if url == "https://restapi.amap.com":
            self.url_combo.setCurrentText("高德")
        else:
            self.url_combo.setCurrentText("自定义")
        self.check_status()

        province = settings.value("selected_province", "")
        city = settings.value("selected_city", "")
        county = settings.value("selected_county", "")
        if province:
            idx = self.province_combo.findText(province)
            if idx >= 0:
                self.province_combo.setCurrentIndex(idx)
        if city:
            idx_city = self.city_combo.findText(city)
            if idx_city >= 0:
                self.city_combo.setCurrentIndex(idx_city)
        if county:
            idx_county = self.county_combo.findText(county)
            if idx_county >= 0:
                self.county_combo.setCurrentIndex(idx_county)

    def check_status(self):
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        if not url or not key:
            self.status_label.setText("状态：❌ 未填写完整")
            return
        try:
            test_url = f"{url}/v3/ip?key={key}"
            resp = requests.get(test_url, timeout=3, verify=certifi.where())
            if resp.status_code == 200 and resp.json().get('status') == '1':
                self.status_label.setText("状态：✅ 已连接")
            else:
                self.status_label.setText("状态：❌ 连接失败（请检查地址和密钥）")
        except requests.RequestException:
            self.status_label.setText("状态：❌ 连接失败（网络或服务器错误）")

    def save_settings(self):
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        freq = self.freq_spin.value()
        if not url or not key:
            QMessageBox.warning(self, "提示", "请完整填写 API 地址和密钥")
            return
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("api_url", url)
        settings.setValue("api_key", key)
        settings.setValue("refresh_minutes", freq)

        province = self.province_combo.currentText()
        city = self.city_combo.currentText()
        county = self.county_combo.currentText()
        if province != "请选择省份" and city != "请选择城市":
            settings.setValue("selected_province", province)
            settings.setValue("selected_city", city)
            if county != "请选择区县":
                settings.setValue("selected_county", county)
            else:
                settings.remove("selected_county")
        else:
            settings.remove("selected_province")
            settings.remove("selected_city")
            settings.remove("selected_county")

        self.accept()

    def reject(self):
        super().reject()

    def closeEvent(self, event):
        self.reject()
        event.accept()

    # ---------- 更新红点 ----------
    def update_red_dot(self):
        parent = self.parent()
        if parent and hasattr(parent, 'has_update') and parent.has_update:
            self.has_update = True
            btn = self.cat_buttons[3]
            btn.setText("检查更新 ●")
        else:
            self.has_update = False
            btn = self.cat_buttons[3]
            btn.setText("检查更新")

    # ---------- 更新相关 ----------
    def check_update_manually(self):
        if self.downloaded_setup_path and os.path.exists(self.downloaded_setup_path):
            self.update_status_label.setText("安装包已下载")
            self.check_update_btn.setVisible(False)
            self.install_update_btn.setVisible(True)
            self.install_update_btn.setText("继续安装")
            self.install_update_btn.setEnabled(True)
            return

        self.update_status_label.setText("正在检查...")
        self.check_update_btn.setEnabled(False)
        self.checker = UpdateChecker()
        self.checker.check_finished.connect(self.on_manual_check_finished)
        self.checker.start()

    def on_manual_check_finished(self, result):
        self.check_update_btn.setEnabled(True)
        if "error" in result:
            self.update_status_label.setText(f"检查失败：{result['error']}")
            return
        if result.get("has_update", False):
            self.latest_version_label.setText(f"最新版本：{result['latest_version']}")
            self.update_status_label.setText("有新版本可用！")
            self.check_update_btn.setVisible(False)
            self.install_update_btn.setVisible(True)
            self.install_update_btn.setText("立即重启安装")
            self.download_url = result['download_url']
            self.has_update = True
            self.update_red_dot()
        else:
            self.latest_version_label.setText(f"最新版本：{VERSION} (已是最新)")
            self.update_status_label.setText("已是最新版本")
            self.has_update = False
            self.update_red_dot()

    def install_update(self):
        if self.downloaded_setup_path and os.path.exists(self.downloaded_setup_path):
            reply = QMessageBox.question(
                self,
                "安装更新",
                "安装包已下载，是否立即安装？\n程序将自动退出并启动安装程序。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                if Updater.perform_update(self.downloaded_setup_path):
                    parent = self.parent()
                    if parent:
                        parent._exiting = True
                    QApplication.quit()
                else:
                    self.update_status_label.setText("启动安装失败，请手动运行安装包")
                    self.install_update_btn.setEnabled(True)
            return

        if not self.download_url:
            return
        self.install_update_btn.setEnabled(False)
        self.update_status_label.setText("正在下载...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        dest = os.path.join(tempfile.gettempdir(), "DesktopWidget-Setup.exe")
        self.downloader = Downloader(self.download_url, dest)
        self.downloader.progress.connect(self.progress_bar.setValue)
        self.downloader.finished.connect(self.on_download_finished)
        self.downloader.start()

    def on_download_finished(self, success, path_or_error):
        self.progress_bar.setVisible(False)
        if success:
            self.downloaded_setup_path = path_or_error
            self.update_status_label.setText("下载完成")
            self.install_update_btn.setEnabled(True)
            self.install_update_btn.setText("立即安装")

            reply = QMessageBox.question(
                self,
                "更新已就绪",
                "新版本已下载完成，是否立即安装？\n程序将自动退出并启动安装程序。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                if Updater.perform_update(path_or_error):
                    parent = self.parent()
                    if parent:
                        parent._exiting = True
                    QApplication.quit()
                else:
                    self.update_status_label.setText("启动安装失败，请手动运行安装包")
                    self.install_update_btn.setEnabled(True)
            else:
                self.update_status_label.setText("更新已取消，下次启动或点击'继续安装'可继续")
                self.install_update_btn.setEnabled(True)
                self.install_update_btn.setVisible(True)
                self.install_update_btn.setText("继续安装")
                self.check_update_btn.setVisible(False)
        else:
            self.update_status_label.setText(f"下载失败：{path_or_error}")
            self.install_update_btn.setEnabled(True)
            self.install_update_btn.setText("重试下载")