"""
自动更新模块
负责检查GitHub Releases、下载新版本、执行更新
"""
import sys
import os
import tempfile
import subprocess
import time

import requests
from PyQt6.QtCore import QThread, pyqtSignal, QSettings

from .constants import VERSION, GITHUB_REPO


def _get_github_headers():
    """从 QSettings 读取 Token，构造请求头"""
    settings = QSettings("MyDesktopApp", "WeatherSettings")
    token = settings.value("github_token", "").strip()
    if token:
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    else:
        return {
            "Accept": "application/vnd.github.v3+json"
        }


def parse_version(version_str):
    """将版本号字符串转换为整数列表，用于语义化比较"""
    if version_str.startswith('v'):
        version_str = version_str[1:]
    parts = version_str.split('.')
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            result.append(0)
    while len(result) < 3:
        result.append(0)
    return result


def compare_versions(v1, v2):
    """语义化版本比较，返回 True 如果 v1 < v2"""
    return parse_version(v1) < parse_version(v2)


class UpdateChecker(QThread):
    check_finished = pyqtSignal(dict)

    def run(self):
        try:
            headers = _get_github_headers()
            resp = requests.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                headers=headers,
                timeout=10
            )
            # 如果返回 401，说明 Token 无效，清除保存的 Token 并重试
            if resp.status_code == 401:
                settings = QSettings("MyDesktopApp", "WeatherSettings")
                settings.remove("github_token")
                # 使用未认证请求重试
                resp = requests.get(
                    f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                    headers={"Accept": "application/vnd.github.v3+json"},
                    timeout=10
                )
                resp.raise_for_status()
                self.check_finished.emit({
                    "has_update": False,
                    "error": "Token 已失效，已清除，请重新填写",
                    "token_invalid": True
                })
                return

            resp.raise_for_status()
            data = resp.json()
            latest_version = data.get("tag_name", "").strip()
            assets = data.get("assets", [])
            download_url = None
            for asset in assets:
                name = asset.get("name", "")
                if name.startswith("DesktopWidget-") and name.endswith("-win64-Cherish-Setup.exe"):
                    download_url = asset.get("browser_download_url")
                    break
            release_notes = data.get("body", "")
            has_update = False
            if latest_version and download_url:
                if compare_versions(VERSION, latest_version):
                    has_update = True
            self.check_finished.emit({
                "has_update": has_update,
                "latest_version": latest_version,
                "download_url": download_url,
                "release_notes": release_notes,
            })
        except Exception as e:
            self.check_finished.emit({
                "has_update": False,
                "error": str(e),
            })


class Downloader(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, dest_path):
        super().__init__()
        self.url = url
        self.dest_path = dest_path

    def run(self):
        try:
            resp = requests.get(self.url, stream=True, timeout=30)
            resp.raise_for_status()
            total_size = int(resp.headers.get('content-length', 0))
            downloaded = 0
            with open(self.dest_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int(downloaded / total_size * 100)
                            self.progress.emit(progress)
            self.finished.emit(True, self.dest_path)
        except Exception as e:
            self.finished.emit(False, str(e))


class Updater:
    @staticmethod
    def perform_update(new_setup_path: str) -> bool:
        """
        执行更新：直接启动安装程序（让用户看到安装界面）
        """
        try:
            subprocess.Popen(
                [new_setup_path],
                shell=True,
                env=os.environ.copy()
            )
            return True
        except Exception as e:
            return False