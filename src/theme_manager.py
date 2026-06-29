# -*- coding: utf-8 -*-
"""
主题管理器
负责扫描、切换、获取主题资源路径
"""

import os
from PyQt6.QtCore import QSettings


class ThemeManager:
    """主题管理器（单例）"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.skins_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skins")
        self._current_theme = None
        self._themes = {}

        # 加载设置
        self._load_settings()
        # 扫描主题
        self._scan_themes()
        # 确保当前主题有效
        self._validate_current_theme()

    def _scan_themes(self):
        """扫描 skins/ 目录，发现所有主题"""
        self._themes = {}
        if not os.path.exists(self.skins_root):
            os.makedirs(self.skins_root)

        for item in os.listdir(self.skins_root):
            theme_path = os.path.join(self.skins_root, item)
            if os.path.isdir(theme_path):
                # 检查是否包含 bg.png 和 face.png
                bg_path = os.path.join(theme_path, "bg.png")
                face_path = os.path.join(theme_path, "face.png")
                if os.path.exists(bg_path) and os.path.exists(face_path):
                    # 主题名称：文件夹名
                    display_name = self._get_display_name(item)
                    self._themes[display_name] = {
                        "path": theme_path,
                        "folder": item,
                        "display_name": display_name
                    }

    def _get_display_name(self, folder_name):
        """将文件夹名转换为显示名称"""
        name_map = {
            "default": "默认主题",
            "skins_01": "竹林",
        }
        return name_map.get(folder_name, folder_name)

    def _load_settings(self):
        """从 QSettings 加载当前主题"""
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        theme_name = settings.value("theme_name", "默认主题")
        self._current_theme = theme_name

    def _save_settings(self):
        """保存当前主题到 QSettings"""
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("theme_name", self._current_theme)
        settings.sync()

    def _validate_current_theme(self):
        """确保当前主题有效，否则回退到默认主题"""
        if self._current_theme not in self._themes:
            self._current_theme = "默认主题"
            self._save_settings()

    def get_current_theme(self) -> str:
        """获取当前主题名称"""
        return self._current_theme

    def list_themes(self) -> list:
        """获取所有主题名称列表"""
        return list(self._themes.keys())

    def get_theme_path(self, filename: str) -> str:
        """
        获取当前主题下某个文件的绝对路径
        如果当前主题不存在该文件，回退到默认主题
        """
        theme_info = self._themes.get(self._current_theme)
        if not theme_info:
            # 如果当前主题无效，强制切换到默认
            self.switch_theme("默认主题")
            theme_info = self._themes.get("默认主题")

        # 先尝试当前主题
        file_path = os.path.join(theme_info["path"], filename)
        if os.path.exists(file_path):
            return file_path

        # 回退到默认主题
        default_info = self._themes.get("默认主题")
        if default_info:
            fallback_path = os.path.join(default_info["path"], filename)
            if os.path.exists(fallback_path):
                print(f"⚠️ {filename} 在当前主题缺失，使用默认主题")
                return fallback_path

        # 如果默认主题也没有，返回 None（调用方处理）
        return None

    def switch_theme(self, theme_name: str):
        """切换主题"""
        if theme_name not in self._themes:
            print(f"❌ 主题 '{theme_name}' 不存在")
            return False

        if theme_name == self._current_theme:
            return True

        self._current_theme = theme_name
        self._save_settings()
        print(f"✅ 切换主题: {theme_name}")
        return True

    def get_theme_folder(self) -> str:
        """获取当前主题的文件夹名（用于资源路径）"""
        theme_info = self._themes.get(self._current_theme)
        if theme_info:
            return theme_info["folder"]
        return "default"

    def get_theme_info(self, theme_name: str = None) -> dict:
        """获取主题信息"""
        if theme_name is None:
            theme_name = self._current_theme
        return self._themes.get(theme_name, {})


# 全局单例实例
_theme_manager = None


def get_theme_manager():
    """获取主题管理器单例"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager