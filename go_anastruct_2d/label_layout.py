"""Screen-space collision avoidance for engineering overlay labels.

Display geometry only: changes never affect model coordinates or solver results.
"""
from __future__ import annotations

from dataclasses import dataclass
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPen


@dataclass
class _Label:
    point: QPointF
    text: str
    color: str
    priority: int
    index: int


class LabelLayout:
    """Place the highest-priority, readable annotations without overlap.

    Layout is recalculated from cached world geometry on each viewport repaint;
    it never recalculates forces and does not mutate the model or result cache.
    """

    def __init__(self):
        self._labels: list[_Label] = []

    def add(self, point, text, color="#25303b", priority=30):
        if point is None or not text:
            return
        self._labels.append(
            _Label(QPointF(float(point.x()), float(point.y())), str(text),
                   str(color), int(priority), len(self._labels))
        )

    def paint(self, painter, avoid_collisions=True):
        if not self._labels:
            return
        painter.save()
        try:
            fm = painter.fontMetrics()
            bounds = QRectF(painter.viewport())
            boxes: list[QRectF] = []
            # Preserve reactions/extrema first. Small tags and repeated labels
            # are dropped only from display, never from numerical results.
            ordered = sorted(self._labels, key=lambda l: (-l.priority, l.index))
            for item in ordered:
                width = float(fm.horizontalAdvance(item.text))
                ascent = float(fm.ascent())
                descent = float(fm.descent())
                if not width or not ascent:
                    continue
                x, y = item.point.x(), item.point.y()
                dx_options = (6.0, 6.0, -width - 9.0, -width - 9.0, -width / 2, -width / 2)
                dy_options = (-8.0, 17.0, -8.0, 17.0, -22.0, 31.0)
                candidates = [
                    (x + dx, y + dy)
                    for dx, dy in zip(dx_options, dy_options)
                ]
                if not avoid_collisions:
                    candidates = candidates[:1]
                for left, baseline in candidates:
                    rect = QRectF(left - 2.0, baseline - ascent - 2.0,
                                  width + 4.0, ascent + descent + 4.0)
                    if avoid_collisions and (
                        not bounds.contains(rect)
                        or any(rect.adjusted(-2, -2, 2, 2).intersects(other) for other in boxes)
                    ):
                        continue
                    # Subtle neutral label backing makes text readable when
                    # loads and force diagrams cross behind it.
                    if avoid_collisions:
                        painter.fillRect(rect, QColor(255, 255, 255, 228))
                    painter.setPen(QPen(QColor(item.color), 1))
                    painter.drawText(QPointF(left, baseline), item.text)
                    boxes.append(rect)
                    break
        finally:
            painter.restore()
