from __future__ import annotations

import math

RESULT_KEYS = ("N", "V", "M", "d", "u", "ux", "uz")


def interpolate_plot(plot, x):
    """Interpolate a cached member result at local coordinate x.

    Exact discontinuity coordinates prefer the right-side result when present.
    This keeps point-load shear jumps deterministic for hover/readout labels.
    """
    rows = sorted(plot or [], key=lambda row: (float(row.get("x", 0.0)), 0 if row.get("side") == "left" else 1))
    if not rows:
        return {"x": float(x), **{key: 0.0 for key in RESULT_KEYS}}
    x = max(float(rows[0]["x"]), min(float(rows[-1]["x"]), float(x)))
    exact = [row for row in rows if math.isclose(float(row["x"]), x, rel_tol=0.0, abs_tol=1e-10)]
    if exact:
        preferred = next((row for row in exact if row.get("side") == "right"), exact[-1])
        return {key: (float(preferred.get(key, 0.0)) if key != "side" else preferred.get(key)) for key in ("x",) + RESULT_KEYS + ("side",)}

    left = rows[0]
    right = rows[-1]
    for a, b in zip(rows, rows[1:]):
        xa, xb = float(a["x"]), float(b["x"])
        if xa <= x <= xb and xb - xa > 1e-12:
            left, right = a, b
            break
    xa, xb = float(left["x"]), float(right["x"])
    t = 0.0 if xb - xa <= 1e-12 else (x - xa) / (xb - xa)
    out = {"x": x, "side": "right"}
    for key in RESULT_KEYS:
        a = float(left.get(key, 0.0))
        b = float(right.get(key, 0.0))
        out[key] = a + (b - a) * t
    return out


def sample_plot(plot, length, count):
    count = max(0, int(count))
    if count <= 0:
        return []
    if count == 1:
        xs = [0.5 * float(length)]
    else:
        xs = [float(length) * i / (count - 1) for i in range(count)]
    return [interpolate_plot(plot, x) for x in xs]


def signed_interval_parts(v0, v1):
    """Return [(start_t, end_t, sign)] split at a linear zero crossing."""
    v0 = float(v0)
    v1 = float(v1)
    eps = 1e-14
    if abs(v0) <= eps and abs(v1) <= eps:
        return []
    s0 = 1 if v0 >= 0 else -1
    s1 = 1 if v1 >= 0 else -1
    if s0 == s1 or abs(v0) <= eps or abs(v1) <= eps:
        sign = s1 if abs(v0) <= eps else s0
        return [(0.0, 1.0, sign)]
    t = abs(v0) / (abs(v0) + abs(v1))
    return [(0.0, t, s0), (t, 1.0, s1)]
