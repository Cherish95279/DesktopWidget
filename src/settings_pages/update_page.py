from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
import os
import tempfile

from ..constants import VERSION
from ..updater import UpdateChecker, Downloader, Updater


class UpdatePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self.download_url = None
        self.downloader = None
        self.downloaded_setup_path = None
        self.checker = None
        self._auto_checked = False

        self.setup_ui()
        self.load_token()
        self.check_update_manually()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(8)

        self.version_label = QLabel(f"当前版本：{VERSION}")
        layout.addWidget(self.version_label)

        self.latest_version_label = QLabel("最新版本：检查中...")
        layout.addWidget(self.latest_version_label)

        self.update_status_label = QLabel("")
        layout.addWidget(self.update_status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.check_update_btn = QPushButton("检查更新")
        self.check_update_btn.setMinimumHeight(28)
        self.check_update_btn.clicked.connect(self.check_update_manually)
        layout.addWidget(self.check_update_btn)

        self.install_update_btn = QPushButton("检查更新")
        self.install_update_btn.setVisible(False)
        self.install_update_btn.setMinimumHeight(28)
        self.install_update_btn.clicked.connect(self.install_update)
        layout.addWidget(self.install_update_btn)

        # Token 区域
        token_label = QLabel("GitHub Token")
        token_label.setStyleSheet("font-size: 12px; color: #333;")
        layout.addWidget(token_label)

        token_input_layout = QHBoxLayout()
        self.token_edit = QLineEdit()
        self.token_edit.setPlaceholderText("GitHub Token（可选）")
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setMinimumHeight(28)
        token_input_layout.addWidget(self.token_edit)

        self.token_visibility_btn = QPushButton("👁")
        self.token_visibility_btn.setFixedSize(28, 28)
        self.token_visibility_btn.setCheckable(True)
        self.token_visibility_btn.setToolTip("显示/隐藏 Token")
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
        self.save_token_btn = QPushButton("保存 Token")
        self.save_token_btn.setMinimumHeight(28)
        self.save_token_btn.setStyleSheet("font-size: 12px; color: #333;")
        self.save_token_btn.clicked.connect(self.save_token)
        self.save_token_btn.setFixedWidth(self.save_token_btn.fontMetrics().boundingRect("保存 Token").width() + 24)
        token_btn_layout.addWidget(self.save_token_btn)
        layout.addLayout(token_btn_layout)

        layout.addStretch()

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
            self.update_status_label.setText("Token 已保存")
            self.check_update_manually()
        else:
            settings.remove("github_token")
            self.update_status_label.setText("Token 已清除")
            self.check_update_manually()

    def on_token_text_changed(self):
        pass

    def toggle_token_visibility(self):
        if self.token_visibility_btn.isChecked():
            self.token_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.token_visibility_btn.setText("🙈")
        else:
            self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.token_visibility_btn.setText("👁")

    # ---------- 更新 ----------
    def check_update_manually(self):
        if self.downloaded_setup_path and os.path.exists(self.downloaded_setup_path):
            self.update_status_label.setText("安装包已下载")
            self.check_update_btn.setVisible(False)
            self.install_update_btn.setVisible(True)
            self.install_update_btn.setText("检查更新")
            self.install_update_btn.setEnabled(True)
            return

        self.update_status_label.setText("正在检查...")
        self.check_update_btn.setEnabled(False)
        self.install_update_btn.setVisible(False)
        self.checker = UpdateChecker()
        self.checker.check_finished.connect(self.on_check_finished)
        self.checker.start()

    def on_check_finished(self, result):
        self.check_update_btn.setEnabled(True)
        if "error" in result:
            self.update_status_label.setText(f"检查失败：{result['error']}")
            if result.get("token_invalid", False):
                self.token_edit.clear()
                self.update_status_label.setText("Token 已失效，已自动清除")
            return
        if result.get("has_update", False):
            self.latest_version_label.setText(f"最新版本：{result['latest_version']}")
            self.update_status_label.setText("有新版本可用！")
            self.check_update_btn.setVisible(False)
            self.install_update_btn.setVisible(True)
            self.install_update_btn.setText("检查更新")
            self.download_url = result['download_url']
        else:
            self.latest_version_label.setText(f"最新版本：{VERSION} (已是最新)")
            self.update_status_label.setText("已是最新版本")

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
            self.install_update_btn.setText("检查更新")

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
                self.install_update_btn.setText("检查更新")
                self.check_update_btn.setVisible(False)
        else:
            self.update_status_label.setText(f"下载失败：{path_or_error}")
            self.install_update_btn.setEnabled(True)
            self.install_update_btn.setText("检查更新")