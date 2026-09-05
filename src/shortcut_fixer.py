# -*- coding: utf-8 -*-
r"""
桌面快捷方式修复模块

MSIX 商店版每次更新后，安装目录路径中的版本号会变化
（例如 1.5.3.0 → 1.5.4.0），导致旧的桌面快捷方式指向的路径失效。

本模块在启动时检测桌面快捷方式是否失效，如果失效则重新创建，
指向 AppExecutionAlias 提供的稳定路径：

    %LOCALAPPDATA%\Microsoft\WindowsApps\DesktopWidget.exe

该路径不含版本号，更新后依然有效。

零外部依赖，仅使用 Python 标准库（os / subprocess）+ Windows 内置 PowerShell。
"""

import os
import subprocess


# ============================================================
# 检测
# ============================================================

def _is_store_version():
    """检测是否为 MSIX 商店版"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        ERROR_NO_PACKAGE = 15700
        length = ctypes.c_uint32(0)
        result = kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
        return result != ERROR_NO_PACKAGE
    except Exception:
        return False


def _get_desktop_path():
    """获取桌面文件夹路径"""
    return os.path.join(os.path.expanduser("~"), "Desktop")


def _get_shortcut_path():
    """获取桌面快捷方式路径"""
    return os.path.join(_get_desktop_path(), "DesktopWidget.lnk")


def _get_alias_path():
    """获取 AppExecutionAlias 稳定路径（不含版本号）"""
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(local_appdata, "Microsoft", "WindowsApps", "DesktopWidget.exe")


# ============================================================
# 快捷方式读写（通过 PowerShell WScript.Shell COM）
# ============================================================

def _read_shortcut_target(lnk_path):
    """读取快捷方式的目标路径，失败返回空字符串"""
    ps_script = (
        '$ws = New-Object -ComObject WScript.Shell; '
        '$lnk = $ws.CreateShortcut(\'' + lnk_path + '\'); '
        'Write-Output $lnk.TargetPath'
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _create_shortcut(lnk_path, target_path, icon_path=None, description=None):
    """创建快捷方式"""
    parts = [
        '$ws = New-Object -ComObject WScript.Shell',
        '$lnk = $ws.CreateShortcut(\'' + lnk_path + '\')',
        '$lnk.TargetPath = \'' + target_path + '\'',
    ]
    if icon_path:
        parts.append('$lnk.IconLocation = \'' + icon_path + '\'')
    if description:
        parts.append('$lnk.Description = \'' + description + '\'')
    parts.append('$lnk.Save()')
    ps_script = '; '.join(parts)

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True, timeout=10,
            creationflags=0x08000000
        )
    except Exception:
        pass


# ============================================================
# 主逻辑
# ============================================================

def fix_desktop_shortcut():
    """
    检测并修复桌面快捷方式。

    仅在 MSIX 商店版中执行。如果桌面快捷方式指向的路径已失效（文件不存在），
    则删除旧快捷方式并重新创建，指向 AppExecutionAlias 稳定路径。

    安全性：
    - 仅处理名为 "DesktopWidget.lnk" 的快捷方式
    - 仅当目标路径包含 "DesktopWidget" 且文件不存在时才修复
    - 如果 AppExecutionAlias 路径也不存在，则不创建（等待 alias 生效）
    """
    if not _is_store_version():
        return

    lnk_path = _get_shortcut_path()
    if not os.path.exists(lnk_path):
        return

    target = _read_shortcut_target(lnk_path)

    # 快捷方式仍然有效，无需修复
    if target and os.path.exists(target):
        return

    # 仅处理 DesktopWidget 相关的快捷方式
    if target and "DesktopWidget" not in target:
        return

    # 快捷方式失效，删除旧的
    try:
        os.remove(lnk_path)
    except OSError:
        return

    # 用 alias 稳定路径重新创建
    alias_path = _get_alias_path()
    if os.path.exists(alias_path):
        _create_shortcut(
            lnk_path,
            alias_path,
            icon_path=alias_path,
            description="DesktopWidget"
        )
