from PyQt6.QtCore import QTimer
from ..updater import UpdateChecker


class UpdateMixin:
    """自动更新管理混入"""

    def __init__(self):
        super().__init__()
        # ===== 新增：记录本次启动的更新检查状态 =====
        self.update_check_status = "idle"  # idle / checking / success / failed / no_update

    def check_for_updates_auto(self):
        self.update_check_status = "checking"
        self.update_checker = UpdateChecker()
        self.update_checker.check_finished.connect(self.on_update_check_finished)
        self.update_checker.start()

    def on_update_check_finished(self, result):
        if "error" in result:
            self.update_check_status = "failed"
            self.has_update = False
            print(f"更新检查失败: {result['error']}")
            return
        if result.get("has_update", False):
            self.has_update = True
            self.latest_version_info = result
            self.update_check_status = "success"  # 检查成功且有更新
        else:
            self.has_update = False
            self.update_check_status = "no_update"  # 检查成功但无更新

    def get_latest_version_info(self):
        return self.latest_version_info if self.has_update else None