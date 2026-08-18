import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Fix console encoding for emoji support on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def create_desktop_shortcut():
    """首次运行时在桌面创建快捷方式（仅 Windows）"""
    import subprocess

    if sys.platform != 'win32':
        return

    desktop = os.path.join(
        os.environ.get("USERPROFILE", ""),
        "Desktop"
    )

    shortcut_path = os.path.join(
        desktop,
        "DesktopWidget.lnk"
    )

    if os.path.exists(shortcut_path):
        return

    if getattr(sys, 'frozen', False):
        target = sys.executable
        work_dir = os.path.dirname(sys.executable)
    else:
        target = sys.executable
        script = os.path.abspath(__file__)
        work_dir = os.path.dirname(script)

    ps_script = (
        "$WshShell = New-Object -ComObject WScript.Shell; "
        f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
        f"$Shortcut.TargetPath = '{target}'; "
        f"$Shortcut.WorkingDirectory = '{work_dir}'; "
        f"$Shortcut.IconLocation = '{target}'; "
        "$Shortcut.Save()"
    )

    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                ps_script
            ],
            capture_output=True,
            timeout=10,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, 'CREATE_NO_WINDOW')
                else 0
            )
        )
    except Exception:
        pass


from src.main_window import MainWindow
from src.notice import NoticeManager


def main():
    app = QApplication(sys.argv)

    app.setApplicationName("DesktopWidget")
    app.setOrganizationName("MyDesktopApp")

    # 首次运行时在桌面创建快捷方式
    QTimer.singleShot(
        3000,
        create_desktop_shortcut
    )

    # 创建主窗口
    # 统计上报、天气状态、更新状态以及30分钟周期上报
    # 均由 MainWindow 自己负责
    window = MainWindow()

    app.aboutToQuit.connect(window.shutdown)

    # 公告管理器
    notice_manager = NoticeManager.get_instance()

    # ============================================================
    # 公告回调
    # ============================================================

    def safe_start_flash(notice):
        if (
            window
            and hasattr(window, 'notice_bubble')
            and window.notice_bubble is not None
        ):
            window.notice_bubble.start_flash()

    def safe_hide_bubble():
        """安全隐藏气泡（含重试机制）"""

        def do_hide():
            if (
                window
                and hasattr(window, 'notice_bubble')
                and window.notice_bubble is not None
            ):
                window.notice_bubble.hide_bubble()
                print("✅ 气泡已隐藏")
            else:
                QTimer.singleShot(50, do_hide)

        do_hide()

    # 注册公告回调
    notice_manager.register_callback(
        "on_new_notice",
        safe_start_flash
    )

    notice_manager.register_callback(
        "on_no_notice",
        safe_hide_bubble
    )

    print("✅ 公告回调注册成功")

    # ============================================================
    # 延迟启动公告检查
    # ============================================================

    def start_notice():
        notice_manager.start(interval_minutes=30)
        print("✅ 公告轮询已启动")

    QTimer.singleShot(
        500,
        start_notice
    )

    # ============================================================
    # 启动 Qt 事件循环
    # ============================================================

    sys.exit(app.exec())


if __name__ == "__main__":
    main()