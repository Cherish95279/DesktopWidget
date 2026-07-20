import json
import traceback
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal, QSettings, QTimer
import requests
import certifi

from .notice_data import Notice


class NoticeChecker(QThread):
    """公告检查线程"""
    notice_received = pyqtSignal(object)
    notice_empty = pyqtSignal()
    check_failed = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            print(f"[Check] 开始检查公告: {self.url}")
            resp = requests.get(self.url, timeout=5, verify=certifi.where())
            if resp.status_code != 200:
                print(f"[ERROR] 公告请求失败，状态码: {resp.status_code}")
                self.check_failed.emit(f"HTTP {resp.status_code}")
                return

            data = resp.json()
            print(f"📄 解析到公告数据: {data}")
            notice = Notice.from_dict(data)

            if not notice.is_valid():
                print("[WARN] 公告数据无效")
                self.notice_empty.emit()
                return

            self.notice_received.emit(notice)

        except requests.exceptions.Timeout:
            print("⏱️ 公告请求超时")
            self.check_failed.emit("超时")
        except requests.exceptions.ConnectionError:
            print("[Network] 网络连接失败")
            self.check_failed.emit("网络连接失败")
        except Exception as e:
            print(f"[ERROR] 公告检查异常: {e}")
            traceback.print_exc()
            self.check_failed.emit(str(e))


class NoticeManager:
    """公告管理器（单例）"""
    _instance = None

    # Gitee 和 GitHub 两个公告源
    _NOTICE_URLS = [
        "https://gitee.com/Cherish95279/DesktopWidget/raw/main/notice.json",
        "https://raw.githubusercontent.com/Cherish95279/DesktopWidget/main/notice.json"
    ]

    def __init__(self):
        self._timer = None
        self._checker = None
        self._all_notices: List[Dict[str, Any]] = []
        self._is_notifying = False
        self._data_loaded = False
        self._deleted_ids = set()  # 本地已删除公告 ID 集合
        self._check_handled = False  # 标记当前轮次是否已处理有效结果
        self._checkers: List[NoticeChecker] = []  # 当前正在运行的检查线程

        self._callbacks = {
            "on_new_notice": [],
            "on_no_notice": [],
            "on_check_failed": [],
            "on_data_updated": [],
        }

        self._load_history()
        self._load_deleted_ids()  # 加载已删除 ID 列表

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ---------- 历史公告缓存 ----------
    def _load_history(self):
        try:
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            history_json = settings.value("notice_history", "[]")
            history = json.loads(history_json) if history_json else []
            self._all_notices = []
            for item in history:
                # 兼容旧数据，补充缺失字段
                if "timestamp" not in item:
                    item["timestamp"] = "未知日期"
                item["is_read"] = True
                self._all_notices.append(item)
            print(f"[History] 加载 {len(self._all_notices)} 条历史公告")
            self._data_loaded = True
        except Exception as e:
            print(f"[WARN] 加载历史公告失败: {e}")
            self._all_notices = []
            self._data_loaded = True

    def _save_history(self):
        try:
            history = []
            for notice in self._all_notices:
                if notice.get("is_read", False):
                    history.append({
                        "id": notice.get("id"),
                        "title": notice.get("title"),
                        "content": notice.get("content"),
                        "link": notice.get("link"),
                        "timestamp": notice.get("timestamp"),
                        "show_date": notice.get("show_date", True),
                    })
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            settings.setValue("notice_history", json.dumps(history, ensure_ascii=False))
            settings.sync()
            print(f"💾 保存 {len(history)} 条历史公告")
        except Exception as e:
            print(f"[WARN] 保存历史公告失败: {e}")

    # ---------- 已删除公告 ID 持久化 ----------
    def _load_deleted_ids(self):
        """从 QSettings 加载已删除的公告 ID 列表"""
        try:
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            deleted_str = settings.value("deleted_notice_ids", "")
            if deleted_str:
                self._deleted_ids = set(deleted_str.split(","))
                print(f"[History] 加载 {len(self._deleted_ids)} 个已删除公告 ID")
            else:
                self._deleted_ids = set()
        except Exception as e:
            print(f"[WARN] 加载已删除 ID 失败: {e}")
            self._deleted_ids = set()

    def _save_deleted_ids(self):
        """保存已删除公告 ID 列表到 QSettings"""
        try:
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            settings.setValue("deleted_notice_ids", ",".join(self._deleted_ids))
            settings.sync()
            print(f"💾 已保存 {len(self._deleted_ids)} 个已删除公告 ID")
        except Exception as e:
            print(f"[WARN] 保存已删除 ID 失败: {e}")

    # ---------- 数据更新通知 ----------
    def _notify_data_updated(self):
        for cb in self._callbacks["on_data_updated"]:
            try:
                cb()
            except Exception as e:
                print(f"[WARN] 数据更新回调执行失败: {e}")

    # ---------- 轮询控制 ----------
    def start(self, interval_minutes: int = 60):
        self._stop_timer()
        try:
            self._check_now()
        except Exception as e:
            print(f"[WARN] 首次检查失败: {e}")
        self._timer = QTimer()
        self._timer.timeout.connect(self._check_now)
        self._timer.start(interval_minutes * 60 * 1000)

    def _stop_timer(self):
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    def _check_now(self):
        """同时从 Gitee 和 GitHub 两个源检查公告，先返回有效结果的优先使用"""
        try:
            print("[Check] 执行公告检查（双源并行）")
            # 重置本次检查的标志
            self._check_handled = False

            # 清理已完成的检查线程
            self._checkers = [c for c in self._checkers if c.isRunning()]

            # 启动两个源的同时检查
            for url in self._NOTICE_URLS:
                checker = NoticeChecker(url)
                checker.notice_received.connect(self._on_notice_received)
                checker.notice_empty.connect(self._on_no_notice)
                checker.check_failed.connect(self._on_check_failed)
                checker.start()
                self._checkers.append(checker)

        except Exception as e:
            print(f"[WARN] 启动检查线程失败: {e}")
            traceback.print_exc()
            self._on_check_failed(str(e))

    def refresh_notice(self):
        """手动刷新公告（由查看公告按钮触发）"""
        self._check_now()

    # ---------- 核心事件处理 ----------
    def _on_notice_received(self, notice: Notice):
        """处理成功返回的公告（只处理第一个有效结果）"""
        # 如果已经处理过有效结果，忽略后续
        if self._check_handled:
            print(f"ℹ️ 已处理过有效公告，忽略本次结果: {notice.id}")
            return

        try:
            # ===== 检查是否已被用户删除 =====
            if notice.id in self._deleted_ids:
                print(f"ℹ️ 公告 {notice.id} 已被用户删除，跳过")
                self._on_no_notice()
                return

            # 检查是否已存在
            for n in self._all_notices:
                if n.get("id") == notice.id:
                    print(f"[WARN] 公告 {notice.id} 已存在，跳过")
                    self._on_no_notice()
                    return

            # 检查是否已在历史缓存中（已读）
            settings = QSettings("MyDesktopApp", "WeatherSettings")
            history_json = settings.value("notice_history", "[]")
            try:
                history = json.loads(history_json) if history_json else []
            except:
                history = []
            for item in history:
                if item.get("id") == notice.id:
                    print(f"ℹ️ 公告 {notice.id} 已在历史中，视为已读")
                    notice_dict = {
                        "id": notice.id,
                        "title": notice.title,
                        "content": notice.content,
                        "link": notice.link,
                        "timestamp": notice.timestamp,
                        "is_read": True,
                        "show_date": notice.show_date,
                    }
                    self._all_notices.append(notice_dict)
                    self._notify_data_updated()
                    self._on_no_notice()
                    return

            # 新公告
            notice_dict = {
                "id": notice.id,
                "title": notice.title,
                "content": notice.content,
                "link": notice.link,
                "timestamp": notice.timestamp,
                "is_read": False,
                "show_date": notice.show_date,
            }
            self._all_notices.append(notice_dict)
            self._is_notifying = True
            # 标记已处理有效结果
            self._check_handled = True
            print(f"📢 新公告到达! (ID: {notice.id})")

            self._notify_data_updated()

            for cb in self._callbacks["on_new_notice"]:
                try:
                    cb(notice)
                except Exception as e:
                    print(f"[WARN] 回调执行失败: {e}")
        except Exception as e:
            print(f"[WARN] 处理新公告异常: {e}")
            traceback.print_exc()

    def _on_no_notice(self):
        """处理无公告的情况（只触发一次）"""
        if self._check_handled:
            return
        # 标记已处理（本次检查无公告）
        self._check_handled = True
        try:
            self._is_notifying = False
            self._notify_data_updated()
            for cb in self._callbacks["on_no_notice"]:
                try:
                    cb()
                except Exception as e:
                    print(f"[WARN] 回调执行失败: {e}")
        except Exception as e:
            print(f"[WARN] 处理无公告异常: {e}")

    def _on_check_failed(self, error_msg):
        """处理检查失败（不设置标志，允许其他源继续尝试）"""
        # 如果已经处理过有效结果，忽略失败
        if self._check_handled:
            return
        try:
            print(f"[ERROR] 公告检查失败: {error_msg}")
            for cb in self._callbacks["on_check_failed"]:
                try:
                    cb()
                except Exception as e:
                    print(f"[WARN] 回调执行失败: {e}")
        except Exception as e:
            print(f"[WARN] 处理检查失败异常: {e}")

    # ---------- 公开方法 ----------
    def mark_as_read(self, notice_id: str):
        try:
            for notice in self._all_notices:
                if notice.get("id") == notice_id and not notice.get("is_read", False):
                    notice["is_read"] = True
                    self._save_history()
                    print(f"[OK] 公告已读: {notice_id}")

                    self._notify_data_updated()

                    has_unread = any(not n.get("is_read", False) for n in self._all_notices)
                    if not has_unread:
                        self._is_notifying = False
                        self._on_no_notice()
                    return
        except Exception as e:
            print(f"[WARN] 标记已读异常: {e}")

    def mark_current_as_read(self):
        for notice in self._all_notices:
            if not notice.get("is_read", False):
                self.mark_as_read(notice.get("id"))
                return

    def get_all_notices(self) -> List[Dict[str, Any]]:
        try:
            sorted_notices = sorted(self._all_notices, key=lambda x: x.get("timestamp", ""), reverse=True)
            return sorted_notices
        except Exception as e:
            print(f"[WARN] 获取公告列表异常: {e}")
            return []

    def get_current_notice(self) -> Optional[Dict[str, Any]]:
        for notice in self._all_notices:
            if not notice.get("is_read", False):
                return notice
        return None

    def is_notifying(self) -> bool:
        return self._is_notifying

    def is_data_loaded(self) -> bool:
        return self._data_loaded

    # ---------- 回调管理 ----------
    def register_callback(self, event: str, callback):
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def unregister_callback(self, event: str, callback):
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)

    def clear_callbacks(self):
        for key in self._callbacks:
            self._callbacks[key].clear()
        print("🧹 所有公告回调已清除")

    # ---------- 删除操作（持久化已删除 ID） ----------
    def delete_notice(self, notice_id: str):
        try:
            # 标记为已删除（持久化）
            self._deleted_ids.add(notice_id)
            self._save_deleted_ids()

            # 从列表移除
            for i, notice in enumerate(self._all_notices):
                if notice.get("id") == notice_id:
                    self._all_notices.pop(i)
                    self._save_history()
                    self._notify_data_updated()
                    print(f"🗑️ 公告已删除: {notice_id}")

                    # 如果删除后没有未读公告了，触发无通知
                    has_unread = any(not n.get("is_read", False) for n in self._all_notices)
                    if not has_unread:
                        self._is_notifying = False
                        self._on_no_notice()
                    return
        except Exception as e:
            print(f"[WARN] 删除公告异常: {e}")

    def clear_all_notices(self):
        try:
            # 清空所有公告时，可以选择保留已删除列表或清空
            # 这里选择保留已删除列表（用户可能希望继续隐藏某些公告）
            # 如果你希望清空所有公告后也重置已删除列表，可以把下面这行注释掉
            # self._deleted_ids.clear()
            # self._save_deleted_ids()

            # 只保留未读公告（如果有）
            unread = [n for n in self._all_notices if not n.get("is_read", False)]
            self._all_notices = unread
            self._save_history()
            self._notify_data_updated()
            print("🧹 所有已读公告已清空")

            if not unread:
                self._is_notifying = False
                self._on_no_notice()
        except Exception as e:
            print(f"[WARN] 清空公告异常: {e}")

    def stop(self):
        self._stop_timer()
        # 停止所有正在运行的检查线程
        for checker in self._checkers:
            if checker.isRunning():
                checker.quit()
                checker.wait(6000)
        self._checkers.clear()
        if self._checker is not None:
            self._checker.quit()
            self._checker.wait(6000)
            self._checker = None