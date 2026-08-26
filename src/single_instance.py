"""单实例锁：保证同时只有一个 DesktopWidget 进程在运行。

启动时调用 check_or_listen()：
- 若已有实例在运行，返回 None，并已通知已有实例显示窗口；
- 若自己是第一个实例，返回 SingleInstanceServer，由调用方持有
  （通常作为 QApplication 的子对象，随主进程退出自动销毁）。
"""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

# 全局唯一的本地套接字名称，同一台机器上的不同用户互不干扰
SOCKET_NAME = "DesktopWidgetSingleInstanceSocket"


class SingleInstanceServer(QObject):
    """第一个实例持有，监听后续实例的唤起请求。"""

    activated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)
        self._clients = []

    def start(self):
        # 清理上次进程异常退出残留的套接字
        QLocalServer.removeServer(SOCKET_NAME)
        if not self._server.listen(SOCKET_NAME):
            print(f"[SingleInstance] 监听失败: {self._server.errorString()}")
            return False
        return True

    def _on_new_connection(self):
        while self._server.hasPendingConnections():
            client = self._server.nextPendingConnection()
            if client is None:
                continue
            # 保活，避免被 GC
            self._clients.append(client)
            client.readyRead.connect(lambda c=client: self._read(c))
            client.disconnected.connect(lambda c=client: self._discard(c))
            # 连接建立时数据可能已到达，立即处理一次
            if client.bytesAvailable() > 0:
                self._read(client)

    def _read(self, client):
        data = bytes(client.readAll()).decode("utf-8", errors="replace")
        if data.strip() == "activate":
            self.activated.emit()
        # 读完后主动断开这个短连接
        if client.state() != QLocalSocket.LocalSocketState.UnconnectedState:
            client.disconnectFromServer()

    def _discard(self, client):
        if client in self._clients:
            self._clients.remove(client)
        client.deleteLater()


def _notify_existing_instance():
    """尝试连接到已运行的实例并发送唤起信号。成功返回 True。"""
    client = QLocalSocket()
    client.connectToServer(SOCKET_NAME)
    # 等待连接建立（短超时即可，本地通信很快）
    if not client.waitForConnected(1000):
        return False
    client.write(b"activate")
    client.flush()
    client.waitForBytesWritten(1000)
    client.disconnectFromServer()
    return True


def check_or_listen(parent=None):
    """返回 SingleInstanceServer 或 None。

    返回 None 表示已有实例在运行，当前进程应立即退出。
    """
    if _notify_existing_instance():
        print("[SingleInstance] 检测到已运行的实例，已通知其显示窗口，当前进程退出。")
        return None

    server = SingleInstanceServer(parent)
    if not server.start():
        # 极少数情况下监听失败（权限/残留），退化为允许多开
        print("[SingleInstance] 无法建立单实例监听，跳过单实例保护。")
        return None
    print("[SingleInstance] 单实例服务已启动。")
    return server
