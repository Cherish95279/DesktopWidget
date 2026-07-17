from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
import os
import tempfile

from ..constants import VERSION, GITHUB_REPO
from ..updater import UpdateChecker, Downloader, Updater


# ===== 统一下拉框样式 =====
COMBO_STYLE = """
    QComboBox {
        border: 1px solid #ccc;
        border-radius: 4px;
        background: #f5f5f5;
        color: #333;
        font-size: 12px;
        padding: 0 4px;
        height: 28px;
    }
    QComboBox:hover {
        background: #e6f4ff;
        border: 1px solid #1677ff;
        color: #1677ff;
    }
"""


class UpdatePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self.download_url = None
        self.downloader = None
        self.downloaded_setup_path = None
        self.checker = None
        self._auto_checked = False
        self._current_channel = "gitee"

        self.setup_ui()
        self.load_token()
        self.load_channel_setting()
        self.check_update_manually()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(8)

        # ---------- 当前版本 ----------
        self.version_label = QLabel(self.tr("当前版本：") + VERSION)
        layout.addWidget(self.version_label)

        # ---------- 最新版本 ----------
        self.latest_version_label = QLabel(self.tr("最新版本：检查中..."))
        layout.addWidget(self.latest_version_label)

        # ---------- 更新状态 ----------
        self.update_status_label = QLabel("")
        layout.addWidget(self.update_status_label)

        # ---------- 进度条 ----------
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # ---------- 更新渠道（标签 + 下拉框，同一行） ----------
        channel_row = QHBoxLayout()
        channel_row.setSpacing(30)
        channel_row.setContentsMargins(0, 0, 0, 0)

        channel_label = QLabel(self.tr("更新渠道"))
        channel_label.setStyleSheet("font-size: 13px; color: #333;")
        channel_row.addWidget(channel_label)

        # ===== 更新渠道下拉框（统一风格） =====
        self.channel_combo = QComboBox()
        self.channel_combo.setFixedWidth(120)
        self.channel_combo.setFixedHeight(28)
        self.channel_combo.setStyleSheet(COMBO_STYLE)
        self.channel_combo.addItem(self.tr("Gitee源"), "gitee")
        self.channel_combo.addItem(self.tr("GitHub源"), "github")
        self.channel_combo.currentIndexChanged.connect(self._on_channel_changed)
        channel_row.addWidget(self.channel_combo)

        channel_row.addStretch()
        layout.addLayout(channel_row)

        # ---------- 检查更新按钮 ----------
        self.check_update_btn = QPushButton(self.tr("检查更新"))
        self.check_update_btn.setFixedHeight(28)
        self.check_update_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: #f5f5f5;
                color: #333;
            }
            QPushButton:hover {
                background: #e6f4ff;
                border: 1px solid #1677ff;
                color: #1677ff;
            }
        """)
        self.check_update_btn.clicked.connect(self.check_update_manually)
        layout.addWidget(self.check_update_btn)

        # ---------- 安装更新按钮 ----------
        self.install_update_btn = QPushButton(self.tr("检查更新"))
        self.install_update_btn.setVisible(False)
        self.install_update_btn.setFixedHeight(28)
        self.install_update_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: #f5f5f5;
                color: #333;
            }
            QPushButton:hover {
                background: #e6f4ff;
                border: 1px solid #1677ff;
                color: #1677ff;
            }
        """)
        self.install_update_btn.clicked.connect(self.install_update)
        layout.addWidget(self.install_update_btn)

        # ---------- Token 区域 ----------
        token_label = QLabel(self.tr("GitHub Token"))
        token_label.setStyleSheet("font-size: 12px; color: #333;")
        layout.addWidget(token_label)

        token_input_layout = QHBoxLayout()
        self.token_edit = QLineEdit()
        self.token_edit.setPlaceholderText(self.tr("GitHub Token（可选）"))
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setMinimumHeight(28)
        token_input_layout.addWidget(self.token_edit)

        self.token_visibility_btn = QPushButton("👁")
        self.token_visibility_btn.setFixedSize(28, 28)
        self.token_visibility_btn.setCheckable(True)
        self.token_visibility_btn.setToolTip(self.tr("显示/隐藏 Token"))
        self.token_visibility_btn.clicked.connect(self.toggle_token_visibility)
        self.token_visibility_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 4px;
                background: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #f0f0f0;
            }
        """)
        token_input_layout.addWidget(self.token_visibility_btn)
        layout.addLayout(token_input_layout)

        token_btn_layout = QHBoxLayout()
        token_btn_layout.addStretch()

        self.save_token_btn = QPushButton(self.tr("保存 Token"))
        self.save_token_btn.setFixedSize(100, 28)
        self.save_token_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: #f5f5f5;
                color: #333;
            }
            QPushButton:hover {
                background: #e6f4ff;
                border: 1px solid #1677ff;
                color: #1677ff;
            }
        """)
        self.save_token_btn.clicked.connect(self.save_token)
        token_btn_layout.addWidget(self.save_token_btn)
        layout.addLayout(token_btn_layout)

        layout.addStretch()

    # ---------- 更新渠道 ----------
    def load_channel_setting(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        channel = settings.value("update_channel", "gitee")
        self._current_channel = channel

        index = self.channel_combo.findData(channel)
        if index >= 0:
            self.channel_combo.setCurrentIndex(index)
        else:
            self.channel_combo.setCurrentIndex(0)

        self.token_edit.setEnabled(channel == "github")

    def _on_channel_changed(self, index):
        channel = self.channel_combo.currentData()
        if channel == self._current_channel:
            return

        self._current_channel = channel

        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("update_channel", channel)
        settings.sync()

        self.token_edit.setEnabled(channel == "github")

        channel_name = "Gitee" if channel == "gitee" else "GitHub"
        self.update_status_label.setText(f"已切换到 {channel_name} 源，请点击检查更新")
        self.latest_version_label.setText(self.tr("最新版本：请点击检查更新"))
        self.install_update_btn.setVisible(False)
        self.check_update_btn.setVisible(True)
        self.download_url = None
        self.downloaded_setup_path = None

    # ---------- Token ----------
    def load_token(self):
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        token = settings.value("github_token", "")
        if token:
            self.token_edit.setText(token)

    def save_token(self):
        token = self.token_edit.text().strip()
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        if token:
            settings.setValue("github_token", token)
            self.update_status_label.setText(self.tr("Token 已保存"))
            self.check_update_manually()
        else:
            settings.remove("github_token")
            self.update_status_label.setText(self.tr("Token 已清除"))
            self.check_update_manually()

    def toggle_token_visibility(self):
        if self.token_visibility_btn.isChecked():
            self.token_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.token_visibility_btn.setText("🙈")
        else:
            self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.token_visibility_btn.setText("👁")

    # ---------- 更新检查 ----------
    def check_update_manually(self):
        if self.downloaded_setup_path and os.path.exists(self.downloaded_setup_path):
            self.update_status_label.setText(self.tr("安装包已下载"))
            self.check_update_btn.setVisible(False)
            self.install_update_btn.setVisible(True)
            self.install_update_btn.setText(self.tr("检查更新"))
            self.install_update_btn.setEnabled(True)
            return

        self.update_status_label.setText(self.tr("正在检查..."))
        self.check_update_btn.setEnabled(False)
        self.install_update_btn.setVisible(False)

        channel = self._current_channel
        if channel == "gitee":
            url = "https://gitee.com/api/v5/repos/Cherish95279/DesktopWidget/releases/latest"
            self.checker = UpdateChecker(url, use_token=False)
        else:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            self.checker = UpdateChecker(url, use_token=True)

        self.checker.check_finished.connect(self.on_check_finished)
        self.checker.start()

    def on_check_finished(self, result):
        self.check_update_btn.setEnabled(True)

        if "error" in result:
            self.update_status_label.setText(self.tr("检查失败：") + result['error'])
            if result.get("token_invalid", False):
                self.token_edit.clear()
                self.update_status_label.setText(self.tr("Token 已失效，已自动清除"))
            return

        if result.get("has_update", False):
            latest_version = result['latest_version']
            self.latest_version_label.setText(self.tr("最新版本：") + latest_version)

            download_url = result.get('download_url')
            release_notes = result.get('release_notes', '')

            self.update_status_label.setText(self.tr("有新版本可用！"))
            self.check_update_btn.setVisible(False)
            self.install_update_btn.setVisible(True)
            self.install_update_btn.setText("⬇ " + self.tr("下载更新"))
            self.download_url = download_url

            if release_notes:
                self.update_status_label.setText(self.tr("有新版本可用！") + f"\n{release_notes[:100]}...")
        else:
            self.latest_version_label.setText(self.tr("最新版本：") + f"{VERSION} (" + self.tr("已是最新") + ")")
            self.update_status_label.setText(self.tr("已是最新版本"))

    # ---------- 下载与安装 ----------
    def install_update(self):
        if self.downloaded_setup_path and os.path.exists(self.downloaded_setup_path):
            reply = QMessageBox.question(
                self,
                self.tr("安装更新"),
                self.tr("安装包已下载，是否立即安装？") + "\n" + self.tr("程序将自动退出并启动安装程序。"),
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
                    self.update_status_label.setText(self.tr("启动安装失败，请手动运行安装包"))
                    self.install_update_btn.setEnabled(True)
            return

        if not self.download_url:
            self.update_status_label.setText("❌ " + self.tr("下载链接无效"))
            return

        self.install_update_btn.setEnabled(False)
        self.update_status_label.setText(self.tr("正在下载..."))
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
            self.update_status_label.setText(self.tr("下载完成"))
            self.install_update_btn.setEnabled(True)
            self.install_update_btn.setText(self.tr("检查更新"))

            reply = QMessageBox.question(
                self,
                self.tr("更新已就绪"),
                self.tr("新版本已下载完成，是否立即安装？") + "\n" + self.tr("程序将自动退出并启动安装程序。"),
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
                    self.update_status_label.setText(self.tr("启动安装失败，请手动运行安装包"))
                    self.install_update_btn.setEnabled(True)
            else:
                self.update_status_label.setText(self.tr("更新已取消，下次启动可继续"))
                self.install_update_btn.setEnabled(True)
                self.install_update_btn.setVisible(True)
                self.install_update_btn.setText(self.tr("检查更新"))
                self.check_update_btn.setVisible(False)
        else:
            self.update_status_label.setText(self.tr("下载失败：") + str(path_or_error))
            self.install_update_btn.setEnabled(True)
            self.install_update_btn.setText(self.tr("检查更新"))