from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    item_finished = Signal(object)
    finished = Signal()


class BatchWorker(QRunnable):
    def __init__(
        self,
        items: Iterable[object],
        operation: Callable[[object], object],
        signal_parent: QObject | None = None,
    ) -> None:
        super().__init__()
        self.items = list(items)
        self.operation = operation
        self.signals = WorkerSignals(signal_parent)
        self.setAutoDelete(False)

    @Slot()
    def run(self) -> None:
        for item in self.items:
            result = self.operation(item)
            self.signals.item_finished.emit(result)
        self.signals.finished.emit()
