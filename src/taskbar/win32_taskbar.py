# -*- coding: utf-8 -*-
"""Win32 任务栏窗口操作封装（纯 ctypes，无第三方依赖）。

仅封装查询与窗口关系操作，不包含 Qt 逻辑。
所有写操作（SetParent/SetWindowLong/SetWindowPos）都应被 embedder 调度。
"""
import ctypes
from ctypes import wintypes


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


user32 = ctypes.WinDLL('user32', use_last_error=True)

user32.FindWindowW.restype = wintypes.HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.GetWindow.restype = wintypes.HWND
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.SetParent.restype = wintypes.HWND
user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
user32.GetWindowLongW.restype = ctypes.c_long
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
user32.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.COLORREF, ctypes.c_byte, wintypes.DWORD]
user32.SetWindowPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]

GW_CHILD = 5
GW_HWNDNEXT = 2
GWL_STYLE = -16
GWL_EXSTYLE = -20

WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_CLIPSIBLINGS = 0x04000000
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOP = 0
HWND_TOPMOST = wintypes.HWND(-1)

WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008

LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002

# 色键透明：用浅灰 RGB(210,210,211) 作为透明色（接近浅色任务栏，抗锯齿毛边不明显）
# COLORREF 格式 0x00BBGGRR: RGB(210,210,211) = B=211,G=210,R=210 = 0x00D3D2D2
COLORKEY_RGB = 0x00D3D2D2


def _class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def find_taskbar():
    """返回 Shell_TrayWnd 的 HWND，找不到返回 None。"""
    hwnd = user32.FindWindowW("Shell_TrayWnd", None)
    return hwnd if hwnd else None


def find_tray_notify(taskbar_hwnd):
    """在任务栏子窗口中查找 TrayNotifyWnd，返回 HWND 或 None。"""
    if not taskbar_hwnd:
        return None
    child = user32.GetWindow(taskbar_hwnd, GW_CHILD)
    while child:
        if _class_name(child) == "TrayNotifyWnd":
            return child
        child = user32.GetWindow(child, GW_HWNDNEXT)
    return None


def find_xaml_bridge(taskbar_hwnd):
    """查找任务栏中的 DesktopWindowXamlSource 窗口（Win11 XAML 合成层）。"""
    if not taskbar_hwnd:
        return None
    child = user32.GetWindow(taskbar_hwnd, GW_CHILD)
    while child:
        if _class_name(child) == "Windows.UI.Composition.DesktopWindowContentBridge":
            return child
        child = user32.GetWindow(child, GW_HWNDNEXT)
    return None


def is_window(hwnd):
    return bool(user32.IsWindow(hwnd)) if hwnd else False


def get_rect(hwnd):
    """返回 (left, top, right, bottom)，失败返回 None。"""
    if not hwnd:
        return None
    r = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    return r.left, r.top, r.right, r.bottom


def get_hwnd(qwidget):
    """获取 Qt 控件的 HWND（强制创建）。"""
    wid = qwidget.winId()
    return int(wid) if wid else 0


def set_parent(child_hwnd, parent_hwnd):
    """SetParent，返回旧父窗口 HWND。"""
    return user32.SetParent(child_hwnd, parent_hwnd)


def get_style(hwnd):
    return user32.GetWindowLongW(hwnd, GWL_STYLE) & 0xFFFFFFFF


def make_child(hwnd):
    """设置窗口样式：保持 WS_POPUP（TrafficMonitor 同款，不改 WS_CHILD），加 WS_EX_LAYERED。

    保持 popup 而非 child 的原因：WS_CHILD 子窗口会被 Win11 任务栏的 XAML 合成层遮挡，
    而 WS_POPUP 窗口独立渲染，SetParent 仅用于"钉"在任务栏上，不被合成层吞掉。
    """
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    style = (style & ~WS_CAPTION & ~WS_THICKFRAME) | WS_POPUP | WS_VISIBLE
    user32.SetWindowLongW(hwnd, GWL_STYLE, style)
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ex = ex | WS_EX_LAYERED | WS_EX_TOOLWINDOW
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
    # 色键透明：paintEvent 填充 COLORKEY_RGB 的区域变透明，文字保留
    user32.SetLayeredWindowAttributes(hwnd, COLORKEY_RGB, 0, LWA_COLORKEY)


def restore_top_level(hwnd):
    """还原为顶层窗口样式（移除 WS_CHILD，加回 WS_POPUP）。"""
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    style = (style & ~WS_CHILD) | WS_POPUP | WS_VISIBLE
    user32.SetWindowLongW(hwnd, GWL_STYLE, style)


def set_window_pos(hwnd, x, y, w, h):
    """定位并调整窗口大小，提到兄弟窗口顶部。"""
    flags = SWP_NOACTIVATE | SWP_SHOWWINDOW
    return bool(user32.SetWindowPos(hwnd, HWND_TOP, x, y, w, h, flags))


def bring_to_top(hwnd):
    """仅置顶窗口（不改坐标和大小），对抗 XAML 合成层覆盖。"""
    flags = 0x0001 | 0x0002 | 0x0010 | 0x0040  # NOSIZE|NOMOVE|NOACTIVATE|SHOWWINDOW
    return bool(user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0, flags))


SW_HIDE = 0x0000
SW_SHOWNOACTIVATE = 0x0004


def show_window(hwnd, show):
    """显示/隐藏窗口（不激活）。"""
    user32.ShowWindowAsync(hwnd, SW_SHOWNOACTIVATE if show else SW_HIDE)
