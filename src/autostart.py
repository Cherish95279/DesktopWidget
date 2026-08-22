"""
开机自启动功能模块
- 商店版（MSIX）：通过 StartupTask API
- exe版：通过 Windows 注册表
"""
import os
import sys


# StartupTask ID，必须与 AppxManifest.xml 中声明的一致
_STARTUP_TASK_ID = "DesktopWidgetStartup"


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


# ============================================================
# 注册表方式（exe版）
# ============================================================

def _set_autostart_reg(enabled: bool) -> bool:
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "DesktopWidget"
    if getattr(sys, "frozen", False):
        command = f'"{sys.executable}"'
    else:
        script_path = os.path.abspath(sys.argv[0])
        command = f'"{sys.executable}" "{script_path}"'
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except (PermissionError, OSError):
        return False


def _get_autostart_status_reg() -> bool:
    import winreg
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


# ============================================================
# StartupTask 方式（商店版 MSIX）
# ============================================================

def _wait_async(async_op, timeout=10):
    """同步等待 winsdk 异步操作完成"""
    import threading
    done = threading.Event()
    box = {}

    def _on_completed(op, status):
        try:
            box["result"] = op.get_results()
        except Exception as e:
            box["error"] = e
        done.set()

    async_op.completed = _on_completed
    done.wait(timeout=timeout)
    if not done.is_set():
        return ("error", "timeout")
    if "error" in box:
        return ("error", str(box["error"]))
    return box.get("result")


def _set_autostart_startup_task(enabled: bool) -> bool:
    try:
        from winsdk.windows.applicationmodel import StartupTask, StartupTaskState

        op = StartupTask.get_async(_STARTUP_TASK_ID)
        task = _wait_async(op)
        if isinstance(task, tuple) and task[0] == "error":
            return False

        if enabled:
            # 请求开启自启（用户可能看到系统提示）
            enable_op = task.request_enable_async()
            result = _wait_async(enable_op)
            if isinstance(result, tuple) and result[0] == "error":
                return False
            return result == StartupTaskState.ALLOWED or result == StartupTaskState.ENABLED_BY_POLICY or result == StartupTaskState.ENABLED
        else:
            task.disable()
            return True
    except Exception:
        return False


def _get_autostart_status_startup_task() -> bool:
    try:
        from winsdk.windows.applicationmodel import StartupTask, StartupTaskState

        op = StartupTask.get_async(_STARTUP_TASK_ID)
        task = _wait_async(op)
        if isinstance(task, tuple) and task[0] == "error":
            return False

        state = task.state
        return state == StartupTaskState.ENABLED or state == StartupTaskState.ENABLED_BY_POLICY
    except Exception:
        return False


# ============================================================
# 统一接口
# ============================================================

def set_autostart(enabled: bool) -> bool:
    """
    设置开机自启动
    enabled: True 开启，False 关闭
    """
    if _is_store_version():
        return _set_autostart_startup_task(enabled)
    else:
        return _set_autostart_reg(enabled)


def get_autostart_status() -> bool:
    """
    获取开机自启动状态
    返回 True 表示已开启，False 表示未开启
    """
    if _is_store_version():
        return _get_autostart_status_startup_task()
    else:
        return _get_autostart_status_reg()
