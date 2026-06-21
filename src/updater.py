"""
自动更新模块
负责检查GitHub Releases、下载新版本、执行更新
"""
import sys
import os
import tempfile
import subprocess

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from .constants import VERSION, GITHUB_REPO

# GitHub API 地址
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class UpdateChecker(QThread):
    """检查更新的后台线程"""
    check_finished = pyqtSignal(dict)

    def run(self):
        try:
            resp = requests.get(GITHUB_API_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            latest_version = data.get("tag_name", "").strip()
            # 获取附件下载链接（匹配当前平台和品牌）
            assets = data.get("assets", [])
            download_url = None
            for asset in assets:
                name = asset.get("name", "")
                # 匹配命名规则: DesktopWidget-{version}-win64-Cherish.exe
                if name.startswith("DesktopWidget-") and name.endswith("-win64-Cherish.exe"):
                    download_url = asset.get("browser_download_url")
                    break
            release_notes = data.get("body", "")
            has_update = False
            if latest_version and download_url:
                if latest_version != VERSION:
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
    """下载新版本的线程"""
    progress = pyqtSignal(int)  # 0-100
    finished = pyqtSignal(bool, str)  # (success, file_path_or_error)

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
    """执行更新操作（外部脚本）"""
    @staticmethod
    def perform_update(new_exe_path: str, current_exe_path: str) -> bool:
        """
        生成并执行更新脚本
        new_exe_path: 新下载的exe路径
        current_exe_path: 当前运行的exe路径
        """
        try:
            # 创建临时bat文件
            bat_script = f"""
@echo off
timeout /t 2 /nobreak > nul
move /Y "{new_exe_path}" "{current_exe_path}"
start "" "{current_exe_path}"
del "%~f0"
"""
            bat_path = os.path.join(tempfile.gettempdir(), "update.bat")
            with open(bat_path, 'w', encoding='gbk') as f:
                f.write(bat_script)
            # 隐藏窗口执行
            subprocess.Popen(
                [bat_path],
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                shell=True
            )
            return True
        except Exception as e:
            print("Update failed:", e)
            return False