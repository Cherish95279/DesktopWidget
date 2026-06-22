import sys
import os
import subprocess

# ===== 关键：打包后强制隐藏所有子进程窗口（解决闪黑框） =====
# 必须在导入任何其他模块之前应用
if sys.platform == 'win32' and getattr(sys, 'frozen', False):
    _original_popen = subprocess.Popen
    def _popen_no_window(*args, **kwargs):
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = kwargs.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
        return _original_popen(*args, **kwargs)
    subprocess.Popen = _popen_no_window

# ---------- 正常导入 ----------
from PyQt6.QtWidgets import QApplication
from src.main_window import MainWindow

if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        #sys.stdout = open(os.devnull, 'w')
        #sys.stderr = open(os.devnull, 'w')
        os.environ['PYTHONWARNINGS'] = 'ignore'
        import logging
        logging.getLogger().setLevel(logging.ERROR)

    app = QApplication(sys.argv)
    app.setOrganizationName("MyDesktopApp")
    app.setApplicationName("WeatherSettings")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())