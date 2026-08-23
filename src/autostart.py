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

def _wait_async(async_op, timeout=15):
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


def _get_startup_task():
    """获取 StartupTask 对象，失败返回 None"""
    try:
        from winsdk.windows.applicationmodel import StartupTask
        task = _wait_async(StartupTask.get_async(_STARTUP_TASK_ID))
        if isinstance(task, tuple) and task[0] == "error":
            return None
        return task
    except Exception:
        return None

def _state_enabled(state) -> bool:
    """判断某个 StartupTaskState 是否表示“已开启”（会随开机启动）"""
    try:
        from winsdk.windows.applicationmodel import StartupTaskState
        return state in (StartupTaskState.ENABLED, StartupTaskState.ENABLED_BY_POLICY)
    except Exception:
        return False

def _set_autostart_startup_task(enabled: bool) -> bool:
    try:
        task = _get_startup_task()
        if task is None:
            return False

        if enabled:
            # 请求开启自启（首次用户可能看到系统提示）
            result = _wait_async(task.request_enable_async())
            if isinstance(result, tuple) and result[0] == "error":
                # 超时/异常：请求可能已发出，回退读取真实状态
                return _state_enabled(task.state)
            return _state_enabled(result) or _state_enabled(task.state)
        else:
            task.disable()
            return True
    except Exception:
        return False


def _get_autostart_status_startup_task() -> bool:
    try:
        task = _get_startup_task()
        if task is None:
            return False
        return _state_enabled(task.state)
    except Exception:
        return False

def _is_blocked_by_user_startup_task() -> bool:
    """MSIX 下用户曾在系统层手动关闭，此时 App 自身无法再开启"""
    try:
        from winsdk.windows.applicationmodel import StartupTaskState
        task = _get_startup_task()
        if task is None:
            return False
        return task.state == StartupTaskState.DISABLED_BY_USER
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

def get_autostart_detail() -> dict:
    """
    返回开机自启的详细状态，供 UI 决定提示文案。

    - enabled: 当前是否真正会开机自启
    - available: 检测是否可用（MSIX 下 winsdk 异常时为 False）
    - blocked_by_user: MSIX 下被用户在系统层手动关闭，App 无法再开启
    """
    if not _is_store_version():
        return {
            "enabled": _get_autostart_status_reg(),
            "available": True,
            "blocked_by_user": False,
        }
    task = _get_startup_task()
    if task is None:
        return {"enabled": False, "available": False, "blocked_by_user": False}
    try:
        from winsdk.windows.applicationmodel import StartupTaskState
        state = task.state
        return {
            "enabled": _state_enabled(state),
            "available": True,
            "blocked_by_user": state == StartupTaskState.DISABLED_BY_USER,
        }
    except Exception:
        return {"enabled": False, "available": False, "blocked_by_user": False}

def is_autostart_blocked_by_user() -> bool:
    """是否被用户在系统层手动关闭（仅 MSIX 有意义）"""
    if not _is_store_version():
        return False
    return _is_blocked_by_user_startup_task()

def open_startup_settings() -> bool:
    """打开系统“启动应用”设置页，供用户手动开启被禁用的自启"""
    try:
        os.startfile("ms-settings:startupapps")
        return True
    except Exception:
        return False
