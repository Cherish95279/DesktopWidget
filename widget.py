import sys
import os
from PyQt6.QtWidgets import QApplication
from src.main_window import MainWindow


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        os.environ['PYTHONWARNINGS'] = 'ignore'
        import logging
        logging.getLogger().setLevel(logging.ERROR)

    app = QApplication(sys.argv)
    app.setOrganizationName("MyDesktopApp")
    app.setApplicationName("WeatherSettings")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())