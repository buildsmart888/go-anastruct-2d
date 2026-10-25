"""Small starter section library based on geometry, not manufacturer tables."""
from __future__ import annotations


def rect_section(section_id: str, b: float, h: float, kind: str = "RC") -> dict:
    if b <= 0 or h <= 0:
        raise ValueError("Section dimensions must be positive")
    return {
        "id": section_id,
        "kind": kind,
        "shape": "RECT",
        "b": float(b),
        "h": float(h),
        "A": float(b * h),
        "Iz": float(b * h**3 / 12.0),
    }


def rhs_section(section_id: str, b: float, h: float, t: float, kind: str = "Steel") -> dict:
    if min(b, h, t) <= 0 or 2 * t >= min(b, h):
        raise ValueError("Invalid RHS dimensions")
    bi, hi = b - 2 * t, h - 2 * t
    return {
        "id": section_id,
        "kind": kind,
        "shape": "RHS",
        "b": float(b),
        "h": float(h),
        "t": float(t),
        "A": float(b * h - bi * hi),
        "Iz": float((b * h**3 - bi * hi**3) / 12.0),
    }


STARTER_SECTIONS = [
    rect_section("RC200x400", 0.20, 0.40, "RC"),
    rect_section("RC300x500", 0.30, 0.50, "RC"),
    rhs_section("RHS100x50x3", 0.05, 0.10, 0.003, "Steel"),
    rhs_section("SHS100x100x4", 0.10, 0.10, 0.004, "Steel"),
]


def starter_sections() -> list[dict]:
    return [dict(row) for row in STARTER_SECTIONS]
