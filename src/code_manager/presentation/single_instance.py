from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from PySide6.QtNetwork import QLocalServer, QLocalSocket

ACTIVATE_MESSAGE = b"activate"


def single_instance_server_name() -> str:
    unique = f"code-manager:{Path.home()}"
    return f"code-manager-{hashlib.sha256(unique.encode()).hexdigest()}"


class SingleInstanceGuard:
    def __init__(
        self,
        on_activate: Callable[[], None],
        server_name: str | None = None,
    ) -> None:
        self.server_name = server_name or single_instance_server_name()
        self.on_activate = on_activate
        self._server: QLocalServer | None = None

    def try_acquire(self) -> bool:
        if self._notify_running_instance():
            return False

        QLocalServer.removeServer(self.server_name)
        server = QLocalServer()
        if not server.listen(self.server_name):
            return False

        server.newConnection.connect(self._handle_new_connection)
        self._server = server
        return True

    def _notify_running_instance(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if not socket.waitForConnected(500):
            return False

        socket.write(ACTIVATE_MESSAGE)
        socket.flush()
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        return True

    def _handle_new_connection(self) -> None:
        if self._server is None:
            return

        socket = self._server.nextPendingConnection()
        if socket is None:
            return

        socket.waitForReadyRead(100)
        socket.readAll()
        socket.disconnectFromServer()
        self.on_activate()
