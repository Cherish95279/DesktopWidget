from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QPixmap
import os
from ..utils import resource_path


class DonationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_pay_type = "alipay"  # alipay / wechat

        self.setup_ui()
        self.load_qrcode()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 20, 15, 15)
        main_layout.setSpacing(12)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题
        title = QLabel("💖 捐赠支持")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # 二维码图片显示
        self.qrcode_label = QLabel()
        self.qrcode_label.setFixedSize(200, 200)
        self.qrcode_label.setStyleSheet("border: 1px solid #ddd; border-radius: 8px; background-color: white;")
        self.qrcode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.qrcode_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 提示文字
        tip = QLabel("❤️ 感谢您的支持，您的捐赠是我持续维护的动力！")
        tip.setStyleSheet("color: #888; font-size: 11px;")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip.setWordWrap(True)
        main_layout.addWidget(tip)

        # 切换按钮（支付宝 / 微信）
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.alipay_btn = QPushButton("💳 支付宝")
        self.alipay_btn.setFixedSize(90, 30)
        self.alipay_btn.setCheckable(True)
        self.alipay_btn.setChecked(True)
        self.alipay_btn.clicked.connect(lambda: self.switch_pay("alipay"))

        self.wechat_btn = QPushButton("💚 微信支付")
        self.wechat_btn.setFixedSize(90, 30)
        self.wechat_btn.setCheckable(True)
        self.wechat_btn.clicked.connect(lambda: self.switch_pay("wechat"))

        btn_layout.addWidget(self.alipay_btn)
        btn_layout.addWidget(self.wechat_btn)
        main_layout.addLayout(btn_layout)

        # 下方弹性空间
        main_layout.addStretch()

        # ===== 右下角“我已捐赠”按钮 =====
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.donated_btn = QPushButton("❤️ 我已捐赠")
        self.donated_btn.setFixedSize(100, 30)
        self.donated_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ff6b6b;
                border-radius: 15px;
                background: #fff5f5;
                color: #ff6b6b;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ff6b6b;
                color: white;
            }
        """)
        self.donated_btn.clicked.connect(self.on_donated_clicked)

        bottom_layout.addWidget(self.donated_btn)
        main_layout.addLayout(bottom_layout)

        # 更新按钮样式
        self.update_btn_style()

    def update_btn_style(self):
        """更新按钮选中样式"""
        alipay_style = """
            QPushButton {
                border: 2px solid #ccc;
                border-radius: 4px;
                background: #f5f5f5;
                color: #333;
                font-size: 12px;
            }
            QPushButton:checked {
                border: 2px solid #1677ff;
                background: #e6f4ff;
                color: #1677ff;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e6f4ff;
            }
        """
        wechat_style = """
            QPushButton {
                border: 2px solid #ccc;
                border-radius: 4px;
                background: #f5f5f5;
                color: #333;
                font-size: 12px;
            }
            QPushButton:checked {
                border: 2px solid #07c160;
                background: #e8f8ee;
                color: #07c160;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e8f8ee;
            }
        """
        self.alipay_btn.setStyleSheet(alipay_style)
        self.wechat_btn.setStyleSheet(wechat_style)

    def switch_pay(self, pay_type):
        """切换支付方式"""
        if pay_type == self.current_pay_type:
            return
        self.current_pay_type = pay_type
        self.alipay_btn.setChecked(pay_type == "alipay")
        self.wechat_btn.setChecked(pay_type == "wechat")
        self.load_qrcode()

    def load_qrcode(self):
        """加载二维码图片"""
        if self.current_pay_type == "alipay":
            filename = "Alipay.png"
        else:
            filename = "WeChatpay.png"

        path = resource_path(f"icons/{filename}")
        if os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                self.qrcode_label.setPixmap(scaled)
                self.qrcode_label.setScaledContents(True)
                return

        self.qrcode_label.setText("请将二维码图片\n放到 icons/ 目录\n\nAlipay.png\nWeChatpay.png")
        self.qrcode_label.setStyleSheet("border: 1px solid #ddd; border-radius: 8px; background-color: #fafafa; color: #999; font-size: 12px;")

    def on_donated_clicked(self):
        """我已捐赠 按钮点击事件 - 无声音"""
        QMessageBox.information(
            self,
            "❤️ 感谢捐赠",
            "非常感谢您的支持与鼓励！🙏\n\n"
            "您的每一份心意都是我持续维护的动力。\n"
            "我会继续努力，让 DesktopWidget 越来越好！💪\n\n"
            "—— Cherish"
        )