"""
开机自启动功能模块
通过 Windows 注册表控制程序是否随系统启动
"""
import sys
import winreg


def set_autostart(enabled: bool) -> bool:
    """
    设置开机自启动
    enabled: True 开启，False 关闭
    """
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
    except (PermissionError, OSError):
        return False


def get_autostart_status() -> bool:
    """
    获取开机自启动状态
    返回 True 表示已开启，False 表示未开启
    """
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