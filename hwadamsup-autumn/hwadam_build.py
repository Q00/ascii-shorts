"""hwadam_build.py - time-lapse typing of the real hwadam_scene.py source.

The panel fast-types the actual implementation file top to bottom; when
the typing passes each effect's def, that element appears in the scene.
The monorail launches when the file is fully typed.
"""
import math
import os
import re

import hwadam_scene as W
from hwadam_scene import Buf, COLS, ROWS

T0 = 0.5
TYPING_END = 12.5                       # 'if __name__' completes here

with open(os.path.join(os.path.dirname(__file__), "hwadam_scene.py")) as f:
    SRC_LINES = f.read().rstrip("\n").split("\n")

ANCHORS = [
    (r"def foliage_base\(", "base"),
    (r"def canopy\(", "canopy"),
    (r"def track\(", "track"),
    (r"def monorail\(", "car"),
    (r"def leaf_wake\(", "wake"),
    (r"def falling_leaves\(", "leaves"),
    (r"def greeting\(", "greeting"),
    (r"def leafburst\(", "leafburst"),
    (r"if __name__", "run"),
]

def _first_line(pat):
    for i, ln in enumerate(SRC_LINES):
        if re.match(pat, ln):
            return i
    return len(SRC_LINES)


# Non-visual stretches type faster so the scene is never near-empty:
# the preamble before the first effect at 4x, big sprite/data blocks at 2x.
SPEED_ZONES = [
    (0, _first_line(r"def foliage_base\("), 4.0),
    (_first_line(r"BIG_FONT = \{"), _first_line(r"def _letter_slot\("), 2.0),
    (_first_line(r"def grid\("), _first_line(r"def frame\("), 2.0),
]


def _line_mult(i):
    for a, b_, m in SPEED_ZONES:
        if a <= i < b_:
            return m
    return 1.0


_chars_at_line_start = [0]
_weight_at_line_start = [0.0]
for i, ln in enumerate(SRC_LINES):
    _chars_at_line_start.append(_chars_at_line_start[-1] + len(ln) + 1)
    _weight_at_line_start.append(
        _weight_at_line_start[-1] + (len(ln) + 1) / _line_mult(i))
TOTAL_CHARS = _chars_at_line_start[-1]
TOTAL_WEIGHT = _weight_at_line_start[-1]

_anchor_chars = {}
for pat, key in ANCHORS:
    for i, ln in enumerate(SRC_LINES):
        if re.match(pat, ln):
            _anchor_chars[key] = _chars_at_line_start[i] + len(ln) + 1
            break

CPS = TOTAL_WEIGHT / (TYPING_END - T0)


def _weight_to_chars(w):
    import bisect
    i = max(0, bisect.bisect_right(_weight_at_line_start, w) - 1)
    i = min(i, len(SRC_LINES) - 1)
    line_w = (len(SRC_LINES[i]) + 1) / _line_mult(i)
    frac = (w - _weight_at_line_start[i]) / line_w if line_w else 0
    return _chars_at_line_start[i] + min(1.0, max(0.0, frac)) * (
        len(SRC_LINES[i]) + 1)
TL = TYPING_END + 0.4                   # launch right after the file ends
LOOP, RUN = 8.6, 7.6                    # approach loop: far -> at camera
MSG_T0 = TL + 8.8
BURST0, BURST_STEP, N_BURSTS = MSG_T0 + 3.4, 0.65, 7


def typed_chars(t):
    w = max(0.0, min(TOTAL_WEIGHT, (t - T0) * CPS))
    return _weight_to_chars(w)


def typed_pos(t):
    """-> (line index being typed, chars typed into that line)."""
    n = int(typed_chars(t))
    for i in range(len(SRC_LINES)):
        if n < _chars_at_line_start[i + 1]:
            return i, min(len(SRC_LINES[i]), n - _chars_at_line_start[i])
    return len(SRC_LINES) - 1, len(SRC_LINES[-1])


def active(t):
    n = typed_chars(t)
    return {key for key, need in _anchor_chars.items() if n >= need}


def _anchor_time(key):
    """Time when the anchor's def finishes typing (invert typed_chars)."""
    need = _anchor_chars[key]
    lo, hi = T0, TYPING_END
    for _ in range(40):
        mid = (lo + hi) / 2
        if typed_chars(mid) < need:
            lo = mid
        else:
            hi = mid
    return hi


LAUNCH_T = _anchor_time("car")            # car rolls out once its def is typed


def approach(t):
    """-> car depth p in [0, 1], or -1 while the car is off-screen."""
    if t <= LAUNCH_T:
        return -1.0
    u = (t - LAUNCH_T) % LOOP
    if u > RUN:
        return -1.0                         # just passed the camera
    return (u / RUN) ** 1.3                 # slow far away, fast up close


def burst_list():
    xs = (20, 48, 72, 34, 60, 82, 50)
    return tuple((BURST0 + j * BURST_STEP, xs[j]) for j in range(N_BURSTS))


def frame(t):
    on = active(t)
    b = Buf()
    if "base" in on:
        W.foliage_base(b, t)
    if "canopy" in on:
        W.canopy(b, t)
    if "track" in on:
        W.track(b)
    p = approach(t)
    if "car" in on and p >= 0:
        W.monorail(b, t, p)
    if "wake" in on and p >= 0:
        W.leaf_wake(b, t, p)
    if "leaves" in on:
        W.falling_leaves(b, t)
    if "greeting" in on:
        W.greeting(b, t, msg_t0=MSG_T0, rainbow=True)
    if "leafburst" in on:
        W.leafburst(b, t, bursts=burst_list())
    if "base" in on:
        W.hud(b, t, dist_from=TL)
    return W.grid(b)


DUR = BURST0 + (N_BURSTS - 1) * BURST_STEP + 3.4
