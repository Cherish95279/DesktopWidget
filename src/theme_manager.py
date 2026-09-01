# -*- coding: utf-8 -*-
"""
主题管理器
负责扫描、切换、获取主题资源路径，以及导入/删除用户主题
"""

import os
import re
import shutil
import tempfile
import zipfile
from PyQt6.QtCore import QCoreApplication, QSettings, QStandardPaths


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
        # 用户主题目录（可写）。打包后内置 skins 只读，导入的主题存放于此。
        app_data = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation)
        if not app_data:
            app_data = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                "MyDesktopApp", "DesktopWidget")
        self.user_skins_root = os.path.join(app_data, "skins")
        # 受保护的内置主题文件夹名，不可删除/覆盖
        self.BUILTIN_THEMES = {"default", "skins_01", "skins_02"}
        self._current_theme = None
        self._themes = {}

        # 加载设置
        self._load_settings()
        # 扫描主题
        self._scan_themes()
        # 确保当前主题有效
        self._validate_current_theme()

    def rescan_themes(self):
        """重新扫描主题（语言切换后调用，刷新主题显示名）"""
        self._scan_themes()
        self._validate_current_theme()

    def _scan_themes(self):
        """扫描内置与用户主题目录，发现所有主题"""
        self._themes = {}
        # 先扫描内置主题（只读），再扫描用户主题（可写）
        self._scan_root(self.skins_root, is_builtin=True)
        self._scan_root(self.user_skins_root, is_builtin=False)

    def _scan_root(self, root, is_builtin):
        """扫描单个主题根目录"""
        if not os.path.exists(root):
            if not is_builtin:
                try:
                    os.makedirs(root)
                except Exception:
                    pass
            return
        for item in os.listdir(root):
            theme_path = os.path.join(root, item)
            if not os.path.isdir(theme_path):
                continue
            bg_path = os.path.join(theme_path, "bg.png")
            face_path = os.path.join(theme_path, "face.png")
            if not (os.path.exists(bg_path) and os.path.exists(face_path)):
                continue
            # 用户主题不得覆盖内置主题
            if not is_builtin and item in self.BUILTIN_THEMES:
                continue
            display_name = self._get_display_name(item)
            if display_name in self._themes:
                continue
            self._themes[display_name] = {
                "path": theme_path,
                "folder": item,
                "display_name": display_name,
                "is_builtin": is_builtin,
            }

    def _get_display_name(self, folder_name):
        """将文件夹名转换为显示名称"""
        name_map = {
            "default": QCoreApplication.translate("ThemeManager", "默认主题"),
            "skins_01": QCoreApplication.translate("ThemeManager", "竹林"),
            "skins_02": QCoreApplication.translate("ThemeManager", "赛博风"),
        }
        return name_map.get(folder_name, folder_name)

    def _load_settings(self):
        """从 QSettings 加载当前主题"""
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        theme_name = settings.value("theme_name", QCoreApplication.translate("ThemeManager", "默认主题"))
        self._current_theme = theme_name

    def _save_settings(self):
        """保存当前主题到 QSettings"""
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        settings.setValue("theme_name", self._current_theme)
        settings.sync()

    def _validate_current_theme(self):
        """确保当前主题有效，否则回退到默认主题"""
        if self._current_theme not in self._themes:
            self._current_theme = QCoreApplication.translate("ThemeManager", "默认主题")
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
            self.switch_theme(QCoreApplication.translate("ThemeManager", "默认主题"))
            theme_info = self._themes.get(QCoreApplication.translate("ThemeManager", "默认主题"))

        # 先尝试当前主题
        file_path = os.path.join(theme_info["path"], filename)
        if os.path.exists(file_path):
            return file_path

        # 回退到默认主题
        default_info = self._themes.get(QCoreApplication.translate("ThemeManager", "默认主题"))
        if default_info:
            fallback_path = os.path.join(default_info["path"], filename)
            if os.path.exists(fallback_path):
                print(f" {filename} " + QCoreApplication.translate("ThemeManager", "在当前主题缺失，使用默认主题"))
                return fallback_path

        # 如果默认主题也没有，返回 None（调用方处理）
        return None

    def switch_theme(self, theme_name: str):
        """切换主题"""
        if theme_name not in self._themes:
            print(f" 主题 '{theme_name}' 不存在")
            return False

        if theme_name == self._current_theme:
            return True

        self._current_theme = theme_name
        self._save_settings()
        print(f" 切换主题: {theme_name}")
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

    # ---------- 导入 / 删除 ----------
    def is_builtin(self, theme_name: str) -> bool:
        """判断主题是否为内置（不可删除）"""
        info = self._themes.get(theme_name)
        return bool(info and info.get("is_builtin", True))

    def analyze_zip(self, zip_path: str) -> dict:
        """分析主题压缩包：解压到临时目录并校验，不写入用户主题目录。

        返回 dict:
            valid(bool)            必需素材是否齐全
            display_name(str)      主题显示名（文件夹名）
            source_path(str)       临时目录中的主题文件夹路径
            missing_required(list) 缺失的必需文件
            missing_optional(list) 缺失的可选文件
            temp_dir(str)          临时目录（调用方负责清理）
            error(str)             错误信息（None 表示无错误）
        """
        required = ["bg.png", "face.png"]
        optional = ["Hour_Hand.png", "Minute_Hand.png", "Second_Hand.png"]
        result = {
            "valid": False, "display_name": None, "source_path": None,
            "missing_required": [], "missing_optional": [],
            "temp_dir": None, "error": None,
        }
        if not zip_path or not os.path.isfile(zip_path):
            result["error"] = QCoreApplication.translate("ThemeManager", "文件不存在")
            return result
        try:
            temp_dir = tempfile.mkdtemp(prefix="theme_import_")
        except Exception as exc:
            result["error"] = str(exc)
            return result
        result["temp_dir"] = temp_dir
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)
        except Exception as exc:
            result["error"] = QCoreApplication.translate(
                "ThemeManager", "无法解压压缩包") + f": {exc}"
            return result

        theme_folder = self._locate_theme_folder(temp_dir)
        # 扁平结构：素材直接在压缩包根，按 zip 文件名建文件夹
        if theme_folder is None and (
            os.path.exists(os.path.join(temp_dir, "bg.png"))
            or os.path.exists(os.path.join(temp_dir, "face.png"))
        ):
            zip_name = os.path.splitext(os.path.basename(zip_path))[0]
            folder_name = self._sanitize_folder_name(zip_name)
            new_folder = os.path.join(temp_dir, folder_name)
            os.makedirs(new_folder, exist_ok=True)
            for fname in required + optional:
                src = os.path.join(temp_dir, fname)
                if os.path.exists(src):
                    shutil.move(src, os.path.join(new_folder, fname))
            theme_folder = new_folder

        if theme_folder is None:
            result["error"] = QCoreApplication.translate(
                "ThemeManager", "压缩包缺少必需素材")
            return result

        for fname in required:
            if not os.path.exists(os.path.join(theme_folder, fname)):
                result["missing_required"].append(fname)
        for fname in optional:
            if not os.path.exists(os.path.join(theme_folder, fname)):
                result["missing_optional"].append(fname)

        result["source_path"] = theme_folder
        result["display_name"] = os.path.basename(theme_folder)
        result["valid"] = len(result["missing_required"]) == 0
        return result

    @staticmethod
    def _locate_theme_folder(temp_dir):
        """定位可能的主题文件夹（含 bg.png 或 face.png 的顶层目录）"""
        for item in os.listdir(temp_dir):
            if item.startswith("__MACOSX"):
                continue
            full = os.path.join(temp_dir, item)
            if os.path.isdir(full):
                has_bg = os.path.exists(os.path.join(full, "bg.png"))
                has_face = os.path.exists(os.path.join(full, "face.png"))
                if has_bg or has_face:
                    return full
        return None

    @staticmethod
    def _sanitize_folder_name(name):
        """清理文件夹名中的非法字符"""
        name = (name or "").strip()
        name = re.sub(r'[<>:"/\\|?*]', "_", name)
        if not name or name in (".", ".."):
            name = "theme"
        return name

    def _unique_folder_name(self, name):
        """生成不与现有主题冲突的文件夹名"""
        used = set(self.BUILTIN_THEMES)
        for root in (self.skins_root, self.user_skins_root):
            if os.path.isdir(root):
                used |= set(os.listdir(root))
        used |= set(self._themes.keys())
        candidate = name
        index = 2
        while candidate in used:
            candidate = f"{name}_{index}"
            index += 1
        return candidate

    def commit_import(self, analysis: dict):
        """将已分析的主题写入用户主题目录，处理命名冲突后重新扫描。

        返回 (success, display_name_or_message)
        """
        if not analysis or not analysis.get("valid"):
            return (False, QCoreApplication.translate("ThemeManager", "主题校验未通过"))
        src = analysis.get("source_path")
        if not src or not os.path.isdir(src):
            return (False, QCoreApplication.translate("ThemeManager", "主题校验未通过"))
        folder_name = self._sanitize_folder_name(os.path.basename(src))
        folder_name = self._unique_folder_name(folder_name)
        target_path = os.path.join(self.user_skins_root, folder_name)
        try:
            shutil.copytree(src, target_path)
        except Exception as exc:
            return (False, str(exc))
        self.rescan_themes()
        return (True, folder_name)

    def cleanup_temp(self, analysis: dict):
        """清理 analyze_zip 产生的临时目录"""
        temp_dir = analysis.get("temp_dir") if analysis else None
        if temp_dir and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    def delete_theme(self, theme_name: str):
        """删除用户主题。内置主题不可删除。

        返回 (success, message)。成功时 message 为切换后的主题显示名。
        """
        info = self._themes.get(theme_name)
        if not info:
            return (False, QCoreApplication.translate("ThemeManager", "主题不存在"))
        if info.get("is_builtin", True):
            return (False, QCoreApplication.translate("ThemeManager", "内置主题不可删除"))
        default_name = QCoreApplication.translate("ThemeManager", "默认主题")
        if theme_name == self._current_theme:
            self._current_theme = default_name
            self._save_settings()
        try:
            shutil.rmtree(info["path"])
        except Exception as exc:
            return (False, str(exc))
        self.rescan_themes()
        return (True, default_name)


# 全局单例实例
_theme_manager = None


def get_theme_manager():
    """获取主题管理器单例"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
