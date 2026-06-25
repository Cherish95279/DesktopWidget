import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main_window import MainWindow
from src.notice import NoticeManager


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DesktopWidget")
    app.setOrganizationName("MyDesktopApp")

    window = MainWindow()
    notice_manager = NoticeManager.get_instance()

    # 定义回调函数（无延迟，信号本就在主线程）
    def safe_start_flash(notice):
        if window and hasattr(window, 'notice_bubble') and window.notice_bubble is not None:
            window.notice_bubble.start_flash()

    def safe_hide_bubble():
        if window and hasattr(window, 'notice_bubble') and window.notice_bubble is not None:
            window.notice_bubble.hide_bubble()

    # 注册回调
    notice_manager.register_callback("on_new_notice", safe_start_flash)
    notice_manager.register_callback("on_no_notice", safe_hide_bubble)
    print("✅ 公告回调注册成功")

    # 延迟启动公告检查
    def start_notice():
        notice_manager.start(interval_minutes=60)
        print("✅ 公告轮询已启动")

    QTimer.singleShot(500, start_notice)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()