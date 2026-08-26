# -*- coding: utf-8 -*-
"""任务栏嵌入可行性探测模块（纯 ctypes，无第三方依赖）。

探测两个问题：
1. 当前进程能否"看见"任务栏窗口（FindWindow/EnumWindows）
2. 当前进程能否把一个临时窗口 SetParent 进 Shell_TrayWnd（写入验证，做完立即还原）

结果同时写入两个日志文件，并返回内容字符串。
所有写入操作完成后立即还原，不留任何副作用。
"""
import ctypes
from ctypes import wintypes
import os
import tempfile
import traceback


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


# 简单窗口类的 WNDPROC，只处理 WM_DESTROY
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


# 手动定义 WNDCLASSW（标准库 ctypes.wintypes 不提供）
class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWindowExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HANDLE),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


# ---------- 函数原型（use_last_error=True 保证错误码可靠）----------
user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

user32.FindWindowW.restype = wintypes.HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindow.restype = wintypes.HWND
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.SetParent.restype = wintypes.HWND
user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
user32.GetWindowLongPtrW.restype = ctypes.c_void_p
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongPtrW.restype = ctypes.c_void_p
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
user32.GetWindowLongW.restype = ctypes.c_long
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.DestroyWindow.restype = wintypes.BOOL
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DefWindowProcW.restype = ctypes.c_long
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.UnregisterClassW.restype = wintypes.BOOL
user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.RegisterClassW.restype = wintypes.ATOM
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                   wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, wintypes.HWND, wintypes.HMENU,
                                   wintypes.HINSTANCE, ctypes.c_void_p]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetCurrentPackageFullName.restype = wintypes.LONG
kernel32.GetCurrentPackageFullName.argtypes = [ctypes.POINTER(wintypes.UINT), wintypes.LPWSTR]

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]

GW_CHILD = 5
GW_HWNDNEXT = 2
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
HWND_MESSAGE = wintypes.HWND(-3)

def _log(lines, msg):
    lines.append(msg)


def _class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _win_text(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def _rect(hwnd):
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def _hex(h):
    return hex(h) if h else str(h)


def _walk(hwnd, lines, depth=0):
    cls = _class_name(hwnd)
    txt = _win_text(hwnd)
    l, t, r, b = _rect(hwnd)
    vis = bool(user32.IsWindowVisible(hwnd))
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    indent = "  " * depth
    txt_s = ' text="%s"' % txt if txt else ""
    _log(lines, "%sHWND=%s class=%s%s rect=(%d,%d,%d,%d) size=%dx%d vis=%s pid=%d"
         % (indent, _hex(hwnd), cls, txt_s, l, t, r, b, r - l, b - t, vis, pid.value))

    child = user32.GetWindow(hwnd, GW_CHILD)
    while child:
        _walk(child, lines, depth + 1)
        child = user32.GetWindow(child, GW_HWNDNEXT)


def run_probe():
    """运行完整探测，返回 (lines_list, path1, path2)。"""
    lines = []
    try:
        _run_probe_inner(lines)
    except Exception:
        _log(lines, "")
        _log(lines, "===== 探测异常 =====")
        _log(lines, traceback.format_exc())
    return _finish(lines)


def _run_probe_inner(lines):
    _log(lines, "=" * 60)
    _log(lines, "DesktopWidget 任务栏嵌入可行性探测")

    # ===== Phase 0: 环境身份（确认是否在 MSIX 沙箱内）=====
    _log(lines, "")
    _log(lines, "===== Phase 0: 运行环境身份 =====")
    try:
        from .updater import is_store_version
        is_store = is_store_version()
    except Exception as e:
        is_store = "unknown(%s)" % e
    _log(lines, "is_store_version() = %s" % is_store)

    pkg_len = wintypes.UINT(0)
    ret_pkg = kernel32.GetCurrentPackageFullName(ctypes.byref(pkg_len), None)
    if ret_pkg == 0 and pkg_len.value > 0:
        buf = ctypes.create_unicode_buffer(pkg_len.value)
        kernel32.GetCurrentPackageFullName(ctypes.byref(pkg_len), buf)
        _log(lines, "PackageFullName = %s" % buf.value)
    else:
        _log(lines, "PackageFullName = (无，非 MSIX 容器)  ret=%d" % ret_pkg)

    # ===== Phase 1: 只读探测 =====
    _log(lines, "")
    _log(lines, "===== Phase 1: 只读探测（看得见任务栏吗）=====")

    # 1.1 EnumWindows 计数
    all_wins = []

    def _enum_cb(hwnd, lp):
        all_wins.append(hwnd)
        return True

    user32.EnumWindows(EnumWindowsProc(_enum_cb), 0)
    _log(lines, "EnumWindows 顶级窗口数: %d" % len(all_wins))

    # 1.2 FindWindow Shell_TrayWnd
    shell = user32.FindWindowW("Shell_TrayWnd", None)
    _log(lines, "FindWindow(Shell_TrayWnd) = %s" % _hex(shell))
    if shell:
        l, t, r, b = _rect(shell)
        _log(lines, "  Shell_TrayWnd rect=(%d,%d,%d,%d) size=%dx%d" % (l, t, r, b, r - l, b - t))
        _log(lines, "  Shell_TrayWnd 子窗口树:")
        _walk(shell, lines, 1)

    # 1.3 找 TrayNotifyWnd
    tray_notify = None
    if shell:
        child = user32.GetWindow(shell, GW_CHILD)
        while child:
            if _class_name(child) == "TrayNotifyWnd":
                tray_notify = child
                break
            child = user32.GetWindow(child, GW_HWNDNEXT)
    _log(lines, "TrayNotifyWnd HWND = %s" % _hex(tray_notify))
    if tray_notify:
        l, t, r, b = _rect(tray_notify)
        _log(lines, "  TrayNotifyWnd rect=(%d,%d,%d,%d) size=%dx%d" % (l, t, r, b, r - l, b - t))

    if not shell or not tray_notify:
        _log(lines, "")
        _log(lines, "[结论] Phase 1 失败：无法找到任务栏或通知区域窗口。")
        _log(lines, "        沙箱隔离，嵌入无望。建议降级为悬浮贴边方案。")
        return

    # ===== Phase 2: 最小写入验证 =====
    _log(lines, "")
    _log(lines, "===== Phase 2: 最小写入验证（能嵌入吗，做完立即还原）=====")

    # 2.1 注册一个临时窗口类（类名加随机后缀，避免重复注册冲突）
    import random
    cls_name = "DwProbeTmp_%d" % random.randint(100000, 999999)
    wc = WNDCLASSW()
    wc.lpfnWndProc = WNDPROC(lambda h, m, w, l: user32.DefWindowProcW(h, m, w, l))
    wc.lpszClassName = cls_name
    wc.hInstance = kernel32.GetModuleHandleW(None)
    atom = user32.RegisterClassW(ctypes.byref(wc))
    if atom == 0:
        _log(lines, "[FAIL] RegisterClassW 返回 0, GetLastError=%d" % ctypes.get_last_error())
        return
    _log(lines, "[OK] RegisterClassW atom=%d cls=%s" % (atom, cls_name))

    # 2.2 创建临时窗口（0x0，不显示）
    tmp_hwnd = user32.CreateWindowExW(
        0, cls_name, "", WS_POPUP, 0, 0, 0, 0, None, None, wc.hInstance, None)
    if not tmp_hwnd:
        _log(lines, "[FAIL] CreateWindowExW 返回 0, GetLastError=%d" % ctypes.get_last_error())
        return
    _log(lines, "[OK] CreateWindowExW tmp_hwnd=%s" % _hex(tmp_hwnd))

    try:
        # 2.3 记录原始父窗口
        old_parent = user32.GetWindowLongPtrW(tmp_hwnd, -8)  # GWLP_HWNDPARENT
        _log(lines, "原始 GWLP_HWNDPARENT = %s" % _hex(old_parent))

        # 2.4 SetParent 到 Shell_TrayWnd —— 关键一步
        ret = user32.SetParent(tmp_hwnd, shell)
        err = ctypes.get_last_error()
        if ret:
            _log(lines, "[OK] SetParent 成功, 返回旧父=%s" % _hex(ret))
        else:
            _log(lines, "[FAIL] SetParent 返回 0, GetLastError=%d" % err)
            _log(lines, "      （Error 5=拒绝访问 → MSIX 沙箱拒绝写入）")

        # 2.5 读取并修改窗口样式（加 WS_CHILD）
        style = user32.GetWindowLongW(tmp_hwnd, GWL_STYLE)
        _log(lines, "当前 style = 0x%08X" % (style & 0xFFFFFFFF))
        new_style = (style & ~WS_POPUP) | WS_CHILD
        prev = user32.SetWindowLongW(tmp_hwnd, GWL_STYLE, new_style)
        err2 = ctypes.get_last_error()
        if prev != 0 or new_style == user32.GetWindowLongW(tmp_hwnd, GWL_STYLE):
            _log(lines, "[OK] SetWindowLong(WS_CHILD) 成功, prev=0x%08X" % (prev & 0xFFFFFFFF))
        else:
            _log(lines, "[FAIL] SetWindowLong 失败, GetLastError=%d" % err2)

        # 2.6 SetWindowPos 定位
        ok = user32.SetWindowPos(tmp_hwnd, None, 1600, 1040, 80, 28, SWP_NOZORDER | SWP_NOACTIVATE)
        _log(lines, "[%s] SetWindowPos 返回 %s" % ("OK" if ok else "FAIL", ok))

        # 2.7 立即还原
        user32.SetParent(tmp_hwnd, None)
        _log(lines, "[还原] SetParent(tmp, None) 已执行")

    finally:
        user32.DestroyWindow(tmp_hwnd)
        user32.UnregisterClassW(cls_name, wc.hInstance)
        _log(lines, "[还原] DestroyWindow + UnregisterClass 完成")

    _log(lines, "")
    _log(lines, "===== 结论 =====")
    if ret:
        _log(lines, "Phase 2 写入验证通过：SetParent 成功，MSIX 沙箱允许嵌入。")
        _log(lines, "正式实现把握较高，可进入开发阶段。")
    else:
        _log(lines, "Phase 2 写入验证失败：SetParent 被拒绝。")
        _log(lines, "MSIX 版嵌入不可行，需降级方案。")

    return


def _finish(lines):
    """写入日志文件，返回 (lines, path1, path2)。至少写一个，尽量写两个。"""
    content = "\n".join(str(x) for x in lines) + "\n"
    paths = []
    # 候选位置：TEMP、LOCALAPPDATA、模块所在目录、当前工作目录
    candidates = [
        os.path.join(tempfile.gettempdir(), "dw_taskbar_probe.log"),
        os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "dw_taskbar_probe.log"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "dw_taskbar_probe.log"),
        os.path.join(os.getcwd(), "dw_taskbar_probe.log"),
    ]
    for p in candidates:
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            paths.append(p)
            if len(paths) >= 2:
                break  # 两个就够了
        except Exception:
            pass
    while len(paths) < 2:
        paths.append(None)
    return lines, paths[0], paths[1]
