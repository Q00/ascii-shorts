"""winter_v4.py - time-lapse typing of the real winter_scene.py source.

The panel fast-types the actual implementation file top to bottom; when
the typing passes each effect's def, that element appears in the scene.
Launch happens when the file is fully typed.
"""
import math
import os
import re

import winter_scene as W
from winter_scene import Buf, COLS, ROWS

T0 = 0.5
TYPING_END = 12.5                       # 'if __name__' completes here

with open(os.path.join(os.path.dirname(__file__), "winter_scene.py")) as f:
    SRC_LINES = f.read().rstrip("\n").split("\n")

ANCHORS = [
    (r"def aurora\(", "aurora"),
    (r"def stars\(", "stars"),
    (r"def moon\(", "moon"),
    (r"def snowfall\(", "snow"),
    (r"def ground_fill\(", "ground"),
    (r"def pines\(", "pines"),
    (r"def house\(", "houses"),
    (r"def reindeer\(", "rudolph"),
    (r"def sleigh_art\(", "sleigh"),
    (r"def lights\(", "lights"),
    (r"def meteors\(", "meteors"),
    (r"def gifts\(", "gifts"),
    (r"def greeting\(", "greeting"),
    (r"def fireworks\(", "fireworks"),
    (r"if __name__", "run"),
]

def _first_line(pat):
    for i, ln in enumerate(SRC_LINES):
        if re.match(pat, ln):
            return i
    return len(SRC_LINES)


# Non-visual stretches type faster so the scene is never near-empty:
# the preamble before the first effect at 4x, big sprite data blocks at 2x.
SPEED_ZONES = [
    (0, _first_line(r"def aurora\("), 4.0),
    (_first_line(r"HOUSE = \["), _first_line(r"def house\("), 2.0),
    (_first_line(r"RUDOLPH = \["), _first_line(r"def reindeer\("), 2.0),
    (_first_line(r"SLEIGH = \["), _first_line(r"def sleigh_art\("), 2.0),
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
FLIGHT_DUR, FLIGHT_COLS, PARK_X = 8.5, 128.0, -20.0
MSG_T0 = TL + FLIGHT_DUR + 0.3
BURST0, BURST_STEP, N_BURSTS = MSG_T0 + 3.4, 0.65, 7
METEOR_TIMES = (6.0, 11.0, 16.5)
DROP_AT = (2.5, 4.0, 5.5)


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


def sx_at(t):
    if t <= TL:
        return PARK_X
    return PARK_X + FLIGHT_COLS * min(1.0, (t - TL) / FLIGHT_DUR)


def sy_at(t):
    return 30 + 1.8 * math.sin(t * 4.4) + 0.9 * math.sin(t * 8.2 + 1)


def pos(t):
    return sx_at(t), sy_at(t)


def pos_airborne(tp):
    return pos(tp) if tp > TL else (-999.0, -999.0)


def burst_list():
    xs = (20, 48, 72, 34, 60, 82, 50)
    return tuple((BURST0 + j * BURST_STEP, xs[j]) for j in range(N_BURSTS))


def frame(t):
    on = active(t)
    b = Buf()
    if "aurora" in on:
        W.aurora(b, t)
    if "stars" in on:
        W.stars(b, t)
    if "moon" in on:
        W.moon(b)
    if "snow" in on:
        W.snowfall(b, t)
    if "ground" in on:
        W.ground_fill(b)
    if "pines" in on:
        W.pines(b)
    if "houses" in on:
        W.house(b, t, 30, 0)
        W.house(b, t, 58, 1)
    x, y = pos(t)
    if "sleigh" in on:
        W.sleigh_art(b, x, y)
    if "rudolph" in on:
        W.reindeer(b, x + 25, y, t, gallop=t > TL)
    if "lights" in on:
        W.reins(b, x, y)
        W.lights(b, x, y, t)
    if "run" in on and t > TL:
        W.dust(b, t, pos_airborne)
    if "gifts" in on and t > TL:
        W.gifts(b, t, pos, drops=tuple(TL + d for d in DROP_AT))
    if "meteors" in on:
        streaks = tuple((t0, 6 + (int(t0) % 3) * 2, 30 + (int(t0) * 7) % 40)
                        for t0 in METEOR_TIMES)
        W.meteors(b, t, streaks=streaks)
    if "greeting" in on:
        W.greeting(b, t, msg_t0=MSG_T0, rainbow=True)
    if "fireworks" in on:
        W.fireworks(b, t, bursts=burst_list())
    if "stars" in on:
        W.hud(b, t, dist_from=TL)
    return W.grid(b)


DUR = BURST0 + (N_BURSTS - 1) * BURST_STEP + 3.4
