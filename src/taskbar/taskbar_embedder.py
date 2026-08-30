# -*- coding: utf-8 -*-
"""任务栏嵌入管理器：把 QWidget 嵌入 Windows 任务栏通知区域左侧。

职责：
- 找到 Shell_TrayWnd 与 TrayNotifyWnd
- SetParent + 改 WS_CHILD 完成嵌入
- 根据通知区域位置动态定位信息条（内容变化时自适应宽度）
- 检测 Explorer 重启，自动重新嵌入
"""
import os
import tempfile

from PyQt6.QtCore import QObject, QTimer

from . import win32_taskbar as wt

# 信息条与通知区域的水平间距（像素）
H_PADDING = 0
# 信息条内部左右留白（像素）
INNER_PADDING = 8
# 信息条高度比任务栏客户区小多少（上下各占一半，形成"药丸"外观）
HEIGHT_INSET = 8
# 信息条最小高度
MIN_HEIGHT = 24
# 右键点击热区额外宽度（仅左侧加，colorkey 透明，视觉不可见但可接收事件）
HIT_PADDING = 10


def _log(msg):
    """轻量日志，写到临时文件，仅在调用时记录。"""
    try:
        with open(os.path.join(tempfile.gettempdir(), "dw_taskbar_embed.log"),
                  "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except Exception:
        pass


class TaskbarEmbedder(QObject):
    """管理一个 QWidget 嵌入/脱离任务栏。"""

    def __init__(self, widget, parent=None):
        super().__init__(parent)
        self._widget = widget
        self._taskbar_hwnd = None
        self._tray_notify_hwnd = None
        self._parent_hwnd = None
        self._embedded = False
        self._last_geom = None  # 上次定位用的 (x, y, w, h)，避免重复 SetWindowPos
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

    # ---------- 对外接口 ----------
    def enable(self):
        """显示信息条。首次调用才真正嵌入，之后只控制显隐。"""
        if not self._embedded:
            if not self._attach():
                _log("enable 失败：无法附加到任务栏")
                return False
            self._timer.start(500)
        else:
            hwnd = wt.get_hwnd(self._widget)
            if hwnd:
                wt.show_window(hwnd, True)
                wt.bring_to_top(hwnd)
            self._timer.start(500)
        return True

    def disable(self):
        """隐藏信息条（不脱离任务栏，避免反复 embed/detach 损坏窗口状态）。"""
        self._timer.stop()
        if self._embedded:
            hwnd = wt.get_hwnd(self._widget)
            if hwnd:
                wt.show_window(hwnd, False)

    # ---------- 嵌入/脱离 ----------
    def _attach(self):
        """查找任务栏并嵌入 widget。"""
        self._taskbar_hwnd = wt.find_taskbar()
        if not self._taskbar_hwnd:
            _log("未找到 Shell_TrayWnd")
            return False
        self._tray_notify_hwnd = wt.find_tray_notify(self._taskbar_hwnd)
        if not self._tray_notify_hwnd:
            _log("未找到 TrayNotifyWnd")
            return False
        # 挂到 Shell_TrayWnd（TrafficMonitor 同款：WS_POPUP + SetParent）
        self._parent_hwnd = self._taskbar_hwnd

        # 先 show 以确保 HWND 已创建
        self._widget.show()
        hwnd = wt.get_hwnd(self._widget)
        if not hwnd:
            _log("无法获取 widget HWND")
            return False

        old_parent = wt.set_parent(hwnd, self._parent_hwnd)
        wt.make_child(hwnd)
        self._embedded = True
        _log("嵌入成功: taskbar=%s tray=%s hwnd=%s old_parent=%s"
             % (self._taskbar_hwnd, self._tray_notify_hwnd, hwnd, old_parent))
        self._last_geom = None
        self.reposition()
        return True

    def _detach(self):
        """还原为顶层窗口。"""
        hwnd = wt.get_hwnd(self._widget)
        if hwnd:
            wt.restore_top_level(hwnd)
            wt.set_parent(hwnd, 0)
            _log("脱离任务栏: hwnd=%s" % hwnd)
        self._embedded = False
        self._taskbar_hwnd = None
        self._tray_notify_hwnd = None
        self._last_geom = None

    # ---------- 定位 ----------
    def reposition(self):
        """根据任务栏与通知区域计算并应用位置/尺寸。"""
        if not self._embedded:
            return
        if not self._taskbar_hwnd or not wt.is_window(self._taskbar_hwnd):
            return
        tb = wt.get_rect(self._taskbar_hwnd)
        tn = wt.get_rect(self._tray_notify_hwnd)
        if not tb or not tn:
            return

        tb_h = tb[3] - tb[1]
        widget_w = self._widget.desired_width()
        widget_h = tb_h
        # 子窗口 SetWindowPos 用父窗口客户区相对坐标，需减去任务栏屏幕偏移
        x = tn[0] - H_PADDING - widget_w - tb[0]
        y = (tb_h - widget_h) // 2

        geom = (x, y, widget_w, widget_h)
        if geom == self._last_geom:
            return
        hwnd = wt.get_hwnd(self._widget)
        if hwnd:
            wt.set_window_pos(hwnd, x, y, widget_w, widget_h)
            self._last_geom = geom
            _log("定位: %s" % (geom,))

    # ---------- 轮询：Explorer 重启 + 位置变化 ----------
    def _poll(self):
        if not self._embedded:
            return
        # Explorer 重启检测
        if not wt.is_window(self._taskbar_hwnd):
            _log("任务栏 HWND 失效，尝试重新附加（Explorer 重启）")
            self._embedded = False
            self._last_geom = None
            # 稍等任务栏重建后重试
            QTimer.singleShot(1500, self._reattach)
            return
        # 重新置顶窗口（对抗 XAML 合成层覆盖），不改坐标
        hwnd = wt.get_hwnd(self._widget)
        if hwnd:
            wt.bring_to_top(hwnd)
        # 通知区域变化或内容宽度变化时重定位
        self.reposition()

    def _reattach(self):
        """Explorer 重启后重新嵌入。"""
        if self._attach():
            _log("重新附加成功")
            self._timer.start(1000)
        else:
            _log("重新附加失败，3秒后重试")
            QTimer.singleShot(3000, self._reattach)
