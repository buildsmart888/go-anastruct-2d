"""GO anaStruct extension toolbar, kept separate from the solver."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QRectF
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QToolBar


def _icon():
    """Draw at runtime so the Windows packaged build needs no SVG plugins."""
    pix = QPixmap(48, 48)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#143d70"))
    p.drawRoundedRect(QRectF(2, 2, 44, 44), 9, 9)
    p.setPen(QPen(QColor("#eef7ff"), 2.6))
    p.drawLine(9, 35, 39, 35)
    p.drawLine(13, 35, 13, 14)
    p.drawLine(36, 35, 36, 14)
    p.drawLine(13, 14, 36, 14)
    p.setPen(QPen(QColor("#45d5b5"), 2.8))
    p.drawLine(13, 18, 20, 23)
    p.drawLine(20, 23, 27, 13)
    p.drawLine(27, 13, 36, 22)
    p.end()
    return QIcon(pix)


def register_toolbar(app, panel, dock):
    """Install one stable, user-hideable QMainWindow toolbar."""
    win = app.window
    existing = win.findChild(QToolBar, "go_anastruct_2d_toolbar")
    if existing is not None:
        return existing
    toolbar = QToolBar("GO 2D Structural — anaStruct", win)
    toolbar.setObjectName("go_anastruct_2d_toolbar")
    toolbar.setIconSize(QSize(26, 26))
    toolbar.setMovable(True)
    show_action = toolbar.addAction(_icon(), "GO 2D anaStruct")
    show_action.setToolTip("Open GO 2D Structural — anaStruct")
    show_action.triggered.connect(lambda _checked=False: app.show_panel(dock))
    analyze_action = toolbar.addAction("Analyze")
    analyze_action.setToolTip("Analyze the GO anaStruct model (requires solver ready)")
    analyze_action.triggered.connect(lambda _checked=False: panel.run_analysis())
    win.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
    return toolbar
