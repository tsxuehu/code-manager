from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QTableWidget, QWidget

HOVER_ROW_COLOR = "#eaf4ff"


class RowHoverFilter(QObject):
    def __init__(self, table: QTableWidget) -> None:
        super().__init__(table)
        self.table = table
        self.viewport = table.viewport()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.viewport and event.type() == QEvent.Leave:
            try:
                clear_row_hover(self.table)
            except RuntimeError:
                return False
        return super().eventFilter(watched, event)


def install_row_hover_highlight(table: QTableWidget) -> None:
    table.setMouseTracking(True)
    table.viewport().setMouseTracking(True)
    hover_filter = RowHoverFilter(table)
    table.viewport().installEventFilter(hover_filter)
    table.setProperty("row_hover_filter", hover_filter)
    table.cellEntered.connect(lambda row, _column: set_hovered_row(table, row))


def set_hovered_row(table: QTableWidget, row: int) -> None:
    previous_row = table.property("hovered_row")
    if isinstance(previous_row, int) and previous_row != row:
        _paint_row(table, previous_row, highlighted=False)
    table.setProperty("hovered_row", row)
    _paint_row(table, row, highlighted=True)


def clear_row_hover(table: QTableWidget) -> None:
    previous_row = table.property("hovered_row")
    if isinstance(previous_row, int):
        _paint_row(table, previous_row, highlighted=False)
    table.setProperty("hovered_row", None)


def _paint_row(table: QTableWidget, row: int, highlighted: bool) -> None:
    if row < 0 or row >= table.rowCount():
        return
    brush = QBrush(QColor(HOVER_ROW_COLOR)) if highlighted else QBrush()
    for column in range(table.columnCount()):
        item = table.item(row, column)
        if item is not None:
            item.setBackground(brush)
        cell_widget = table.cellWidget(row, column)
        if cell_widget is not None:
            _set_widget_highlight(cell_widget, highlighted)


def _set_widget_highlight(widget: QWidget, highlighted: bool) -> None:
    widget.setAutoFillBackground(highlighted)
    widget.setStyleSheet(f"background-color: {HOVER_ROW_COLOR};" if highlighted else "")
