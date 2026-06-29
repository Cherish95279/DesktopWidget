from PyQt6.QtCore import QTimer
from ..updater import UpdateChecker


class UpdateMixin:
    """自动更新管理混入"""

    def check_for_updates_auto(self):
        self.update_checker = UpdateChecker()
        self.update_checker.check_finished.connect(self.on_update_check_finished)
        self.update_checker.start()

    def on_update_check_finished(self, result):
        if result.get("has_update", False):
            self.has_update = True
            self.latest_version_info = result
        else:
            self.has_update = False

    def get_latest_version_info(self):
        return self.latest_version_info if self.has_update else None