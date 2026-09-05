# -*- coding: utf-8 -*-
"""
内容池插件管理器

负责插件的扫描、加载、调度采集、渲染调用、导入校验、删除。

插件目录结构：
    %LOCALAPPDATA%\MyDesktopApp\DesktopWidget\plugins\
        sunrise_sunset\
            plugin.json
            sunrise_sunset.py
            translations\       (可选)

plugin.json 字段：
    key             (str)   内容池唯一标识，如 "sunrise_sunset"
    name            (str)   显示名称
    description     (str)   简短描述
    version         (str)   版本号
    author          (str)   作者
    min_app_version (str)   最低支持的 App 版本（可选）
    collect_interval (int)  采集间隔秒数，默认 300
    supports_taskbar (bool) 是否支持任务栏显示，默认 False

插件主模块需实现 ContentPlugin 接口类（见下方定义）。
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
import importlib
from datetime import datetime

from PyQt6.QtCore import QObject, QTimer, QStandardPaths, QSettings


# ============================================================
# 插件标准接口
# ============================================================

class ContentPlugin:
    """内容池插件标准接口，插件主模块需继承此类。

    子类实现以下方法，由 PluginManager 在对应时机调用。
    所有方法都应返回指定类型，异常会被 PluginManager 捕获。
    """

    def collect(self, context):
        """数据采集。

        Args:
            context: PluginContext 实例，提供 settings、now 等访问能力。

        Returns:
            dict: 采集到的数据，任意结构，会传给 render_* 方法。
        """
        return {}

    def render_short(self, data, i18n):
        """表盘槽位短文本。

        Args:
            data: collect() 返回的 dict。
            i18n: 国际化文本字典（与 MainWindow._i18n 相同结构）。

        Returns:
            str 或 list: 单行文本字符串，或两行文本的列表。
        """
        return ""

    def render_detail(self, data, is_pro, i18n):
        """悬停详情多行文本。

        Args:
            data: collect() 返回的 dict。
            is_pro: bool，是否为 Pro 用户。
            i18n: 国际化文本字典。

        Returns:
            list[str]: 每行一个字符串。
        """
        return []

    def render_taskbar(self, data, i18n):
        """任务栏单行文本（可选，supports_taskbar=True 时调用）。

        Returns:
            str: 单行文本。
        """
        return ""


# ============================================================
# 插件上下文
# ============================================================

class PluginContext:
    """插件运行上下文，提供对用户设置和基础能力的访问。

    插件不应直接访问 MainWindow 实例，而应通过此上下文获取数据。
    """

    def __init__(self, settings):
        self._settings = settings

    @property
    def settings(self):
        """QSettings 实例，可读取用户配置（语言、位置等）"""
        return self._settings

    @property
    def now(self):
        """当前时间 datetime 对象"""
        return datetime.now()

    def get_setting(self, key, default=None, type=None):
        """便捷读取 QSettings 值"""
        if type is not None:
            return self._settings.value(key, default, type=type)
        return self._settings.value(key, default)


# ============================================================
# 插件信息
# ============================================================

class PluginInfo:
    """存储单个插件的元数据和运行时状态"""

    def __init__(self, key, name, description, version, author,
                 folder, module_name, collect_interval=300,
                 supports_taskbar=False, min_app_version=""):
        self.key = key
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.folder = folder
        self.module_name = module_name
        self.collect_interval = collect_interval
        self.supports_taskbar = supports_taskbar
        self.min_app_version = min_app_version
        # 运行时状态
        self.instance = None        # ContentPlugin 实例
        self.data = {}              # 采集缓存
        self.timer = None           # 采集定时器
        self.error_count = 0        # 连续错误计数
        self.enabled = True         # 是否启用（出错过多后自动禁用）

    def entry(self):
        """返回 (key, name) 元组，供 content_pool 使用"""
        return (self.key, self.name)


# ============================================================
# 插件管理器
# ============================================================

# 最大连续错误次数，超过后自动禁用插件
_MAX_ERRORS = 5


class PluginManager(QObject):
    """插件管理器单例。

    负责：
    - 扫描插件目录并加载插件
    - 按各插件的 collect_interval 定时采集数据
    - 提供 render_short / render_detail / render_taskbar 调用
    - 导入校验（解压 ZIP、校验 JSON、校验模块加载、静态扫描）
    - 删除插件
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        self._plugins = {}          # key -> PluginInfo
        self._context = None        # PluginContext
        self._timers = []           # 所有采集定时器（用于 shutdown）

        # 插件根目录（可写，与用户主题同目录体系）
        app_data = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation)
        if not app_data:
            app_data = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                "MyDesktopApp", "DesktopWidget")
        self.plugins_root = os.path.join(app_data, "plugins")

        # 确保目录存在
        os.makedirs(self.plugins_root, exist_ok=True)

        # 初始化上下文
        self._context = PluginContext(
            QSettings("MyDesktopApp", "WeatherSettings"))

        # 扫描并加载插件
        self.scan_plugins()

    # ============================================================
    # 扫描与加载
    # ============================================================

    def scan_plugins(self):
        """重新扫描插件目录，加载所有有效插件"""
        # 停止所有旧定时器
        self._stop_all_timers()
        self._plugins.clear()

        if not os.path.isdir(self.plugins_root):
            return

        for folder_name in os.listdir(self.plugins_root):
            folder_path = os.path.join(self.plugins_root, folder_name)
            if not os.path.isdir(folder_path):
                continue
            self._load_plugin(folder_path)

        # 启动采集定时器
        self._start_all_timers()

    def _load_plugin(self, folder_path):
        """加载单个插件目录"""
        # 读取 plugin.json
        json_path = os.path.join(folder_path, "plugin.json")
        if not os.path.isfile(json_path):
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        key = meta.get("key", "")
        if not key or not isinstance(key, str):
            return
        # key 只允许字母、数字、下划线
        if not key.replace("_", "").isalnum():
            return

        name = meta.get("name", key)
        description = meta.get("description", "")
        version = meta.get("version", "1.0.0")
        author = meta.get("author", "")
        collect_interval = meta.get("collect_interval", 300)
        supports_taskbar = meta.get("supports_taskbar", False)
        min_app_version = meta.get("min_app_version", "")

        # 确定模块名：plugin.json 所在目录名
        folder_name = os.path.basename(folder_path)
        module_path = os.path.join(folder_path, folder_name + ".py")
        if not os.path.isfile(module_path):
            # 也尝试 key.py
            module_path = os.path.join(folder_path, key + ".py")
            if not os.path.isfile(module_path):
                return

        module_name = os.path.splitext(os.path.basename(module_path))[0]

        info = PluginInfo(
            key=key, name=name, description=description,
            version=version, author=author,
            folder=folder_path, module_name=module_name,
            collect_interval=collect_interval,
            supports_taskbar=supports_taskbar,
            min_app_version=min_app_version,
        )

        # 动态 import 插件模块
        try:
            # 将插件目录加入 sys.path
            if folder_path not in sys.path:
                sys.path.insert(0, folder_path)
            module = importlib.import_module(module_name)
            # 查找 ContentPlugin 子类
            plugin_cls = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and issubclass(attr, ContentPlugin)
                        and attr is not ContentPlugin):
                    plugin_cls = attr
                    break
            if plugin_cls is None:
                return
            info.instance = plugin_cls()
        except Exception:
            # 加载失败，跳过该插件
            return

        # 立即采集一次
        self._collect_plugin(info)

        self._plugins[key] = info

    # ============================================================
    # 定时采集
    # ============================================================

    def _start_all_timers(self):
        """为每个已加载插件启动采集定时器"""
        for info in self._plugins.values():
            interval_ms = max(info.collect_interval, 5) * 1000
            timer = QTimer(self)
            timer.timeout.connect(lambda _k=info.key: self._collect_by_key(_k))
            timer.start(interval_ms)
            info.timer = timer
            self._timers.append(timer)

    def _stop_all_timers(self):
        """停止所有采集定时器"""
        for timer in self._timers:
            timer.stop()
        self._timers.clear()
        for info in self._plugins.values():
            info.timer = None

    def _collect_by_key(self, key):
        """按 key 触发单个插件采集"""
        info = self._plugins.get(key)
        if info is None or not info.enabled:
            return
        self._collect_plugin(info)

    def _collect_plugin(self, info):
        """执行单个插件的数据采集"""
        if info.instance is None or not info.enabled:
            return
        try:
            data = info.instance.collect(self._context)
            if isinstance(data, dict):
                info.data = data
            info.error_count = 0
        except Exception:
            info.error_count += 1
            if info.error_count >= _MAX_ERRORS:
                info.enabled = False

    def collect_all(self):
        """手动触发所有插件采集一次"""
        for info in self._plugins.values():
            self._collect_plugin(info)

    # ============================================================
    # 渲染调用
    # ============================================================

    def render_short(self, key, i18n):
        """调用插件的 render_short，返回文本或空字符串"""
        info = self._plugins.get(key)
        if info is None or info.instance is None or not info.enabled:
            return ""
        try:
            result = info.instance.render_short(info.data, i18n)
            if isinstance(result, list):
                return result
            return str(result) if result else ""
        except Exception:
            return ""

    def render_detail(self, key, is_pro, i18n):
        """调用插件的 render_detail，返回行列表"""
        info = self._plugins.get(key)
        if info is None or info.instance is None or not info.enabled:
            return []
        try:
            result = info.instance.render_detail(info.data, is_pro, i18n)
            if isinstance(result, list):
                return result
            return []
        except Exception:
            return []

    def render_taskbar(self, key, i18n):
        """调用插件的 render_taskbar，返回文本或空字符串"""
        info = self._plugins.get(key)
        if info is None or info.instance is None or not info.enabled:
            return ""
        if not info.supports_taskbar:
            return ""
        try:
            result = info.instance.render_taskbar(info.data, i18n)
            return str(result) if result else ""
        except Exception:
            return ""

    # ============================================================
    # 查询接口
    # ============================================================

    def list_plugins(self):
        """返回所有已加载插件的 PluginInfo 列表"""
        return list(self._plugins.values())

    def get_plugin_keys(self):
        """返回所有已加载插件的 key 集合"""
        return set(self._plugins.keys())

    def get_entries(self):
        """返回所有插件的 (key, name) 列表，供 content_pool 使用"""
        return [info.entry() for info in self._plugins.values()]

    def get_taskbar_entries(self):
        """返回支持任务栏的插件的 (key, name) 列表"""
        return [info.entry() for info in self._plugins.values()
                if info.supports_taskbar]

    def is_plugin_key(self, key):
        """判断某个 key 是否为插件 key"""
        return key in self._plugins

    def get_plugin_info(self, key):
        """获取某个插件的 PluginInfo"""
        return self._plugins.get(key)

    # ============================================================
    # 导入校验
    # ============================================================

    def analyze_zip(self, zip_path):
        """分析 ZIP 插件包，返回校验结果 dict。

        返回结构：
            {
                "valid": bool,           # 是否通过校验
                "error": str,            # 错误信息（校验失败时）
                "key": str,              # 插件 key
                "name": str,             # 插件名称
                "version": str,          # 版本
                "author": str,           # 作者
                "description": str,      # 描述
                "warnings": list,        # 静态扫描警告列表
                "temp_dir": str,         # 临时解压目录（commit 时用）
                "folder_name": str,      # 插件文件夹名
            }
        """
        result = {
            "valid": False, "error": "", "key": "", "name": "",
            "version": "", "author": "", "description": "",
            "warnings": [], "temp_dir": "", "folder_name": "",
        }

        if not os.path.isfile(zip_path):
            result["error"] = "文件不存在"
            return result

        # 解压到临时目录
        temp_dir = tempfile.mkdtemp(prefix="dw_plugin_")
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)
        except (zipfile.BadZipFile, OSError) as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            result["error"] = f"解压失败: {exc}"
            return result

        result["temp_dir"] = temp_dir

        # 查找 plugin.json（可能在根目录或一级子目录）
        json_path = os.path.join(temp_dir, "plugin.json")
        folder_name = ""
        if not os.path.isfile(json_path):
            # 尝试一级子目录
            for name in os.listdir(temp_dir):
                candidate = os.path.join(temp_dir, name, "plugin.json")
                if os.path.isfile(candidate):
                    json_path = candidate
                    folder_name = name
                    break
            if not os.path.isfile(json_path):
                shutil.rmtree(temp_dir, ignore_errors=True)
                result["error"] = "未找到 plugin.json"
                return result
        else:
            folder_name = os.path.basename(temp_dir)

        result["folder_name"] = folder_name if folder_name else os.path.basename(temp_dir)

        # 读取 plugin.json
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            result["error"] = f"plugin.json 格式错误: {exc}"
            return result

        key = meta.get("key", "")
        if not key or not isinstance(key, str):
            shutil.rmtree(temp_dir, ignore_errors=True)
            result["error"] = "plugin.json 缺少有效的 key 字段"
            return result
        if not key.replace("_", "").isalnum():
            shutil.rmtree(temp_dir, ignore_errors=True)
            result["error"] = "key 只允许字母、数字、下划线"
            return result

        # 如果 json 在子目录，确保子目录名与 key 一致
        plugin_dir = os.path.dirname(json_path)

        # 查找主模块文件
        module_candidates = [
            os.path.join(plugin_dir, folder_name + ".py"),
            os.path.join(plugin_dir, key + ".py"),
        ]
        module_path = None
        for candidate in module_candidates:
            if os.path.isfile(candidate):
                module_path = candidate
                break
        if module_path is None:
            shutil.rmtree(temp_dir, ignore_errors=True)
            result["error"] = "未找到插件主模块文件"
            return result

        # 静态扫描危险代码
        warnings = self._scan_dangerous_code(module_path)

        # 尝试 import 模块
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        try:
            if plugin_dir not in sys.path:
                sys.path.insert(0, plugin_dir)
            module = importlib.import_module(module_name)
            # 检查是否有 ContentPlugin 子类
            has_plugin_class = False
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and issubclass(attr, ContentPlugin)
                        and attr is not ContentPlugin):
                    has_plugin_class = True
                    break
            if not has_plugin_class:
                shutil.rmtree(temp_dir, ignore_errors=True)
                result["error"] = "插件模块未定义 ContentPlugin 子类"
                return result
            # 清理 sys.path
            if plugin_dir in sys.path:
                sys.path.remove(plugin_dir)
            # 清理已加载的模块，避免冲突
            if module_name in sys.modules:
                del sys.modules[module_name]
        except Exception as exc:
            if plugin_dir in sys.path:
                sys.path.remove(plugin_dir)
            shutil.rmtree(temp_dir, ignore_errors=True)
            result["error"] = f"模块加载失败: {exc}"
            return result

        # 校验通过
        result["valid"] = True
        result["key"] = key
        result["name"] = meta.get("name", key)
        result["version"] = meta.get("version", "1.0.0")
        result["author"] = meta.get("author", "")
        result["description"] = meta.get("description", "")
        result["warnings"] = warnings
        return result

    def _scan_dangerous_code(self, py_path):
        """静态扫描 Python 文件中的危险代码模式，返回警告列表"""
        warnings = []
        dangerous_patterns = [
            ("os.system", "系统命令执行"),
            ("os.popen", "系统命令执行"),
            ("subprocess.Popen", "子进程执行"),
            ("subprocess.run", "子进程执行"),
            ("subprocess.call", "子进程执行"),
            ("os.exec", "进程替换"),
            ("eval(", "动态代码执行"),
            ("exec(", "动态代码执行"),
            ("__import__", "动态导入"),
            ("ctypes.CDLL", "DLL 加载"),
            ("ctypes.WinDLL", "DLL 加载"),
            ("ctypes.windll", "DLL 加载"),
            ("os.remove", "文件删除"),
            ("shutil.rmtree", "目录删除"),
            ("open(", "文件操作（请确认用途）"),
            ("socket.socket", "原始网络通信"),
        ]
        try:
            with open(py_path, "r", encoding="utf-8") as f:
                source = f.read()
            for pattern, desc in dangerous_patterns:
                if pattern in source:
                    warnings.append(f"⚠️ {desc}: 检测到 \"{pattern}\"")
        except OSError:
            warnings.append("⚠️ 无法读取源码进行安全扫描")
        return warnings

    def commit_import(self, analysis):
        """将校验通过的插件从临时目录复制到插件目录。

        Args:
            analysis: analyze_zip() 返回的 dict

        Returns:
            (success, message): 成功时 message 为插件 key
        """
        if not analysis.get("valid"):
            return (False, "校验未通过")
        temp_dir = analysis.get("temp_dir", "")
        if not temp_dir or not os.path.isdir(temp_dir):
            return (False, "临时目录不存在")

        key = analysis["key"]

        # 确定源目录（plugin.json 所在目录）
        json_path = os.path.join(temp_dir, "plugin.json")
        if not os.path.isfile(json_path):
            for name in os.listdir(temp_dir):
                candidate = os.path.join(temp_dir, name, "plugin.json")
                if os.path.isfile(candidate):
                    json_path = candidate
                    break

        src_dir = os.path.dirname(json_path)

        # 目标目录：plugins_root/key
        dest_dir = os.path.join(self.plugins_root, key)

        # 如果已存在同名插件，先删除
        if os.path.isdir(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)

        try:
            shutil.copytree(src_dir, dest_dir)
        except OSError as exc:
            return (False, f"复制失败: {exc}")

        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)

        # 重新扫描加载
        self.scan_plugins()

        return (True, key)

    def cleanup_temp(self, analysis):
        """清理 analyze_zip 创建的临时目录"""
        temp_dir = analysis.get("temp_dir", "")
        if temp_dir and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ============================================================
    # 删除
    # ============================================================

    def delete_plugin(self, key):
        """删除插件。

        Returns:
            (success, message)
        """
        info = self._plugins.get(key)
        if info is None:
            return (False, "插件不存在")

        # 停止定时器
        if info.timer is not None:
            info.timer.stop()

        # 删除目录
        try:
            shutil.rmtree(info.folder)
        except OSError as exc:
            return (False, str(exc))

        # 从内存移除
        del self._plugins[key]

        # 清理 sys.path 和 sys.modules
        if info.folder in sys.path:
            sys.path.remove(info.folder)
        if info.module_name in sys.modules:
            del sys.modules[info.module_name]

        return (True, key)

    # ============================================================
    # 关闭
    # ============================================================

    def shutdown(self):
        """停止所有定时器，清理资源"""
        self._stop_all_timers()


# ============================================================
# 让插件可以通过 'from plugin_manager import ContentPlugin' 导入
# ============================================================
sys.modules.setdefault('plugin_manager', sys.modules[__name__])


# ============================================================
# 单例
# ============================================================

_plugin_manager = None


def get_plugin_manager():
    """获取插件管理器单例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
