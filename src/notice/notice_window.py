from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QIcon, QColor, QDesktopServices, QAction
import traceback
from ..utils import resource_path
from .notice_manager import NoticeManager


class NoticeWindow(QDialog):
    """公告窗口（左右分栏布局）- 窗口先打开，数据后填充"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("💬 公告")
        self.setFixedSize(500, 380)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowSystemMenuHint
        )
        self.setWindowIcon(QIcon(resource_path("icons/app.ico")))

        self._selected_id = None
        self._loading = False
        self._loaded = False
        self._data_callback_registered = False

        self._setup_ui()
        self._center_on_screen()

        # 窗口先显示，数据后填充
        self.hide()

        # ===== 立即显示占位（"加载中..."） =====
        self._show_loading_state()

        # ===== 注册数据更新回调（数据到达后自动刷新） =====
        self._register_data_callback()

        # ===== 检查数据是否已就绪 =====
        manager = NoticeManager.get_instance()
        if manager.is_data_loaded():
            # 数据已就绪，直接加载
            QTimer.singleShot(50, self._load_messages)
        else:
            # 数据未就绪，显示"加载中..."，等待回调
            print("⏳ 公告数据未就绪，等待数据到达...")

        # 延迟显示窗口（让 UI 先渲染）
        QTimer.singleShot(100, self._show_window)

    def _register_data_callback(self):
        """注册数据更新回调（避免重复注册）"""
        if self._data_callback_registered:
            return
        self._data_callback_registered = True

        manager = NoticeManager.get_instance()
        manager.register_callback("on_data_updated", self._on_data_updated)

        # 窗口销毁时注销回调
        self.destroyed.connect(self._unregister_data_callback)

    def _unregister_data_callback(self):
        """注销数据更新回调"""
        try:
            manager = NoticeManager.get_instance()
            manager.unregister_callback("on_data_updated", self._on_data_updated)
        except Exception:
            pass

    def _on_data_updated(self):
        """数据更新回调（由 NoticeManager 触发）"""
        print("📢 公告数据已更新，窗口自动刷新")
        QTimer.singleShot(50, self._load_messages)

    def _show_loading_state(self):
        """显示加载中占位状态"""
        self.content_title.setText("⏳ 加载中...")
        self.content_time.setText("")
        self.content_body.setText("正在加载公告，请稍候...")
        self.placeholder_label.hide()
        self.link_btn.hide()

        # 清空列表，显示"加载中..."
        self.list_widget.clear()
        loading_item = QListWidgetItem("⏳ 加载中...")
        loading_item.setFlags(Qt.ItemFlag.NoItemFlags)  # 不可点击
        self.list_widget.addItem(loading_item)

        bottom_info = self.findChild(QLabel, "bottom_info")
        if bottom_info:
            bottom_info.setText("加载中...")

    def _show_window(self):
        """显示窗口（由定时器触发）"""
        self.show()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left_panel = QWidget()
        left_panel.setFixedWidth(180)
        left_panel.setStyleSheet("background-color: #f5f5f5;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # ---------- 消息列表 ----------
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #fafafa;
                border: none;
                outline: none;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-bottom: 1px solid #eee;
                color: #333;
            }
            QListWidget::item:hover {
                background-color: #e8e8e8;
            }
            QListWidget::item:selected {
                background-color: #d0e4ff;
                color: #1677ff;
            }
        """)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)

        left_layout.addWidget(self.list_widget)

        bottom_info = QLabel("加载中...")
        bottom_info.setStyleSheet("font-size: 10px; color: #999; padding: 4px 10px; background-color: #f0f0f0;")
        bottom_info.setAlignment(Qt.AlignmentFlag.AlignRight)
        bottom_info.setObjectName("bottom_info")
        left_layout.addWidget(bottom_info)

        main_layout.addWidget(left_panel)

        # ---------- 右侧内容区 ----------
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: white;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #f0f0f0;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #ccc;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #aaa;
            }
        """)

        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: white;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)

        self.content_title = QLabel("加载中...")
        self.content_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1c344d;
        """)
        self.content_title.setWordWrap(True)
        content_layout.addWidget(self.content_title)

        self.content_time = QLabel("")
        self.content_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_time.setStyleSheet("""
            font-size: 11px;
            color: #999;
        """)
        content_layout.addWidget(self.content_time)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #e8e8e8; max-height: 1px;")
        content_layout.addWidget(line)

        self.content_body = QLabel("正在加载公告，请稍候...")
        self.content_body.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.content_body.setStyleSheet("""
            font-size: 13px;
            color: #333;
            line-height: 1.6;
        """)
        self.content_body.setWordWrap(True)
        content_layout.addWidget(self.content_body)

        content_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.link_btn = QPushButton("📎 查看详情")
        self.link_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 20px;
                font-size: 12px;
                border: 1px solid #1677ff;
                border-radius: 4px;
                background: #1677ff;
                color: white;
            }
            QPushButton:hover {
                background: #4096ff;
            }
        """)
        self.link_btn.clicked.connect(self._open_link)
        self.link_btn.hide()
        btn_layout.addWidget(self.link_btn)
        content_layout.addLayout(btn_layout)

        self.placeholder_label = QLabel("请选择一条消息")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("""
            font-size: 14px;
            color: #999;
        """)
        content_layout.addWidget(self.placeholder_label)

        scroll_area.setWidget(content_widget)
        right_layout.addWidget(scroll_area)
        main_layout.addWidget(right_panel)

    def _open_link(self):
        link = self.link_btn.property("link_url")
        if link:
            QDesktopServices.openUrl(QUrl(link))

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = (geometry.width() - self.width()) // 2
            y = (geometry.height() - self.height()) // 2
            self.move(x, y)

    def _load_messages(self):
        """加载消息列表（由数据回调或定时器触发）"""
        try:
            if self._loaded:
                return
            self._loaded = True

            manager = NoticeManager.get_instance()
            all_notices = manager.get_all_notices()

            bottom_info = self.findChild(QLabel, "bottom_info")
            self.list_widget.clear()

            if not all_notices:
                if bottom_info:
                    bottom_info.setText("共 0 条消息")
                self.content_title.setText("暂无公告")
                self.content_body.setText("")
                self.content_time.setText("")
                self.placeholder_label.show()
                self.link_btn.hide()
                return

            self.list_widget.blockSignals(True)
            count = 0

            for notice in all_notices:
                item = self._create_list_item(notice)
                self.list_widget.addItem(item)
                count += 1

            if bottom_info:
                bottom_info.setText(f"共 {count} 条消息")

            if self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(0)
                first_item = self.list_widget.item(0)
                if first_item:
                    self._display_notice_by_item(first_item)

        except Exception as e:
            print(f"❌ 加载消息列表异常: {e}")
            traceback.print_exc()
        finally:
            self.list_widget.blockSignals(False)

    def _create_list_item(self, notice: dict):
        try:
            timestamp = notice.get("timestamp", "")
            date_part = timestamp.split(" ")[0] if timestamp else "未知日期"
            title = notice.get("title", "无标题")
            title_part = title[:15] + "..." if len(title) > 15 else title
            display_text = f"{date_part}  {title_part}"

            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, notice.get("id"))
            return item
        except Exception as e:
            print(f"⚠️ 创建列表项异常: {e}")
            return QListWidgetItem("错误项")

    def _display_notice_by_item(self, item):
        try:
            if not item:
                return

            notice_id = item.data(Qt.ItemDataRole.UserRole)
            if not notice_id:
                return

            manager = NoticeManager.get_instance()
            all_notices = manager.get_all_notices()

            msg = None
            for n in all_notices:
                if n.get("id") == notice_id:
                    msg = n
                    break
            if not msg:
                self.content_title.setText("未找到公告")
                self.content_body.setText("")
                self.content_time.setText("")
                self.link_btn.hide()
                return

            self._selected_id = notice_id

            self.content_title.setText(msg.get("title", "无标题"))

            if msg.get("show_date", True):
                timestamp = msg.get("timestamp", "")
                self.content_time.setText(f"📅 {timestamp}")
            else:
                self.content_time.setText("")

            body_text = msg.get("content", "") or "（无内容）"
            self.content_body.setText(body_text)

            link = msg.get("link")
            if link:
                self.link_btn.setProperty("link_url", link)
                self.link_btn.show()
            else:
                self.link_btn.hide()

            self.placeholder_label.hide()
        except Exception as e:
            print(f"❌ 显示公告内容异常: {e}")
            traceback.print_exc()
            self.content_title.setText("显示错误")
            self.content_body.setText(f"无法显示公告内容: {e}")

    def _on_item_clicked(self, item):
        if not item:
            return

        try:
            notice_id = item.data(Qt.ItemDataRole.UserRole)
            if not notice_id:
                return

            manager = NoticeManager.get_instance()
            all_notices = manager.get_all_notices()
            for n in all_notices:
                if n.get("id") == notice_id and not n.get("is_read", False):
                    manager.mark_as_read(notice_id)
                    break

            self._display_notice_by_item(item)
        except Exception as e:
            print(f"❌ 点击列表项异常: {e}")
            traceback.print_exc()

    def select_notice_by_id(self, notice_id: str):
        if not self._loaded:
            # 如果还没加载完成，延迟重试
            QTimer.singleShot(200, lambda: self.select_notice_by_id(notice_id))
            return
        try:
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                item_id = item.data(Qt.ItemDataRole.UserRole)
                if item_id == notice_id:
                    self.list_widget.setCurrentRow(i)
                    self._on_item_clicked(item)
                    return
        except Exception as e:
            print(f"⚠️ 选择公告异常: {e}")

    # ===== 右键菜单 =====
    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return

        notice_id = item.data(Qt.ItemDataRole.UserRole)
        if not notice_id:
            return

        manager = NoticeManager.get_instance()
        all_notices = manager.get_all_notices()
        msg = next((n for n in all_notices if n.get("id") == notice_id), None)
        if not msg:
            return

        menu = QMenu(self)
        delete_action = QAction("🗑️ 删除此消息", self)
        delete_action.triggered.connect(lambda: self._delete_message(notice_id))
        menu.addAction(delete_action)

        menu.addSeparator()

        clear_action = QAction("🧹 清空消息", self)
        clear_action.triggered.connect(self._clear_history_messages)
        menu.addAction(clear_action)

        menu.exec(self.list_widget.mapToGlobal(pos))

    def _delete_message(self, notice_id: str):
        try:
            manager = NoticeManager.get_instance()
            all_notices = manager.get_all_notices()
            msg = next((n for n in all_notices if n.get("id") == notice_id), None)
            if not msg:
                return

            reply = QMessageBox.question(
                self,
                "确认删除",
                f'确定要删除 "{msg.get("title", "无标题")}" 吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            manager.delete_notice(notice_id)
            self._loaded = False  # 重置，允许重新加载
            self._load_messages()
            self._loaded = True
        except Exception as e:
            print(f"❌ 删除消息异常: {e}")

    def _clear_history_messages(self):
        try:
            manager = NoticeManager.get_instance()
            all_notices = manager.get_all_notices()
            count = len(all_notices)

            if count == 0:
                QMessageBox.information(self, "提示", "没有消息可清空")
                return

            reply = QMessageBox.question(
                self,
                "确认清空",
                f"确定要清空所有 {count} 条消息吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            manager.clear_all_notices()
            self._loaded = False
            self._load_messages()
            self._loaded = True
        except Exception as e:
            print(f"❌ 清空消息异常: {e}")