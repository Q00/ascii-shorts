"""winter_v3.py - typed build: each line of code completes part of the scene.

The editor types SCRIPT line by line; when a line finishes, the matching
element appears in the terminal. Scene pieces come from winter_scene.
"""
import math

import winter_scene as W
from winter_scene import (Buf, art, line, h, ground_y, RUDOLPH, LEGS, SANTA,
                          SACK, SLEIGH, COLS, ROWS)

T0, CPS, PAUSE = 0.6, 50.0, 0.18       # typing start, chars/sec, line pause
SCRIPT = [
    "from winter import *",
    "canvas = Terminal(96, 72)",
    "add(Stars(130, twinkle=2.2))",
    "add(Moon(col=82, row=7))",
    "add(Aurora([green, cyan, purple]))",
    "add(Snow(320, depth=3))",
    "ground = add(Ground(drifts=2))",
    "ground += Pine(8), Pine(88)",
    'ground += House(30, lights="warm")',
    'ground += House(58, lights="warm")',
    "santa = Sleigh(SANTA, toy_sack=SACK)",
    "rudolph = Reindeer(nose=RED, glow=True)",
    "santa.hitch(rudolph)",
    "santa.decorate(FAIRY_LIGHTS)",
    "santa.launch(vx=14.2, bob=1.8)",
    "santa.trail(MagicDust(26))",
    "santa.drop_gifts(at=(2.5, 4.0, 5.5))",
    "schedule(Meteor, at=(4.0, 12.0, 17.0))",
    'msg = Typewriter("MERRY CHRISTMAS")',
    "msg.rainbow(speed=2.5)",
    "schedule(Firework, times=BURSTS)",
    "run(fps=30)",
]


def line_end_times():
    ts, t = [], T0
    for ln in SCRIPT:
        t += len(ln) / CPS
        ts.append(t)
        t += PAUSE
    return ts


TAU = line_end_times()
TL = TAU[14]                              # launch completes
MSG_T0, MSG_RATE = 19.2, 7
MSG = "MERRY CHRISTMAS"
METEORS = (4.0, 12.0, 17.0)
BURST0, BURST_STEP = 22.4, 0.8
BCOL = ("gold", "red", "cyan", "purple", "green", "pink")
PARK_X, FLIGHT_DUR, FLIGHT_COLS = -20.0, 9.0, 128.0


def typed(t):
    """-> (completed line count, partial text of the line being typed)."""
    rem = t - T0
    if rem <= 0:
        return 0, ""
    for i, ln in enumerate(SCRIPT):
        need = len(ln) / CPS + PAUSE
        if rem >= need:
            rem -= need
        else:
            return i, ln[:min(len(ln), int(rem * CPS))]
    return len(SCRIPT), ""


def char_times():
    """Key-click times: one per typed char, one heavier per line return."""
    ev, enters = [], []
    t = T0
    for ln in SCRIPT:
        for i in range(len(ln)):
            ev.append(t + i / CPS)
        t += len(ln) / CPS
        enters.append(t)
        t += PAUSE
    return ev, enters


def sx_at(t):
    if t <= TL:
        return PARK_X
    return PARK_X + FLIGHT_COLS * min(1.0, (t - TL) / FLIGHT_DUR)


def sy_at(t):
    return 30 + 1.8 * math.sin(t * 4.4) + 0.9 * math.sin(t * 8.2 + 1)


def rudolph_v3(b, x, y, t, gallop):
    r0, c0 = int(y) - 16, int(x)
    ov = {"o": "white", "*": "red"}
    rows = {0: "tan", 1: "tan", 2: "tan"}
    art(b, r0, c0, RUDOLPH, "brown", ov, rows)
    phase = int(t * 7) % 2 if gallop else 0
    art(b, r0 + 10, c0, LEGS[phase], "brown")
    pulse = 0.55 + 0.35 * math.sin(t * 6)
    for dr in (-2, -1, 0, 1, 2):
        for dc in (-1, 0, 1, 2):
            if dr * dr + dc * dc <= 4:
                b.put(r0 + 3 + dr, c0 + 11 + dc, max(0.2, pulse), "red")


def sleigh_art(b, x, y):
    art(b, int(y) - 6, int(x) - 10, SACK, "green", {"~": "gold"})
    art(b, int(y) - 1, int(x) - 12, SLEIGH, "red",
        {"_": "gold", "~": "gold", "=": "gold"})
    art(b, int(y) - 8, int(x) - 4, SANTA, "red",
        {"*": "white", "o": "white", "~": "white", "(": "skin",
         ")": "skin"})


def lights(b, x, y, t):
    bulbs = ("red", "green", "gold")
    for i, c in enumerate(range(-10, 11, 2)):
        b.put(y - 2, x + c, 0.96, bulbs[(i + int(t * 4)) % 3], ch="*")
    cols = ("red", "green", "gold", "cyan")
    for i in range(1, 7):
        u = i / 7
        sag = math.sin(u * math.pi) * 0.8
        col = cols[(i + int(t * 4)) % 4]
        b.put(y - 3.3 + (y - 5.1 - (y - 3.3)) * u + sag, x + 11 + 13 * u,
              0.95, col, ch="*")


def dust(b, t):
    if t <= TL:
        return
    for k in range(26):
        age = k * 0.055
        tp = t - age
        px = sx_at(tp) + (h(k, 1) - 0.5) * 10
        py = sy_at(tp) + (h(k, 2) - 0.5) * 7 + age * 3
        fade = 1 - age / 1.5
        if fade > 0 and tp > TL:
            b.put(py, px, 0.75 * fade, "gold" if k % 3 else "white")


GIFTS_AT = (2.5, 4.0, 5.5)


def gifts_v3(b, t):
    for k, dt0 in enumerate(GIFTS_AT):
        t0 = TL + dt0
        if t < t0:
            continue
        x = sx_at(t0) + (h(k, 9) - 0.5) * 6
        y0 = sy_at(t0)
        gy = ground_y(x) - 1.6
        y = min(y0 + 3 + 4.6 * (t - t0) ** 2, gy)
        col = ("red", "gold", "blue")[k]
        for dr in range(2):
            for dc in range(3):
                b.put(y + dr, x - 1 + dc, 0.9, col)
        b.put(y - 1, x, 1.0, "white")
        if y >= gy:
            for s in range(3):
                if math.sin(t * 4 + s * 2.1 + k) > 0.5:
                    b.put(y - 2 - (s % 2), x - 2 + s * 2, 0.8,
                          "white" if s % 2 else "gold", ch="*")


def meteors_v3(b, t):
    for t0 in METEORS:
        dt = t - t0
        if not 0 <= dt < 0.9:
            continue
        r0, c0 = 6 + (int(t0) % 3) * 2, 30 + (int(t0) * 7) % 40
        for k in range(12):
            age = dt - k * 0.018
            if age < 0:
                continue
            b.put(r0 + age * 9, c0 + age * 26, max(0.1, 0.95 - k * 0.08),
                  "white" if k < 3 else "star")


def fireworks_v3(b, t):
    for j in range(7):
        t0 = BURST0 + j * BURST_STEP
        cx = (20, 48, 72, 34, 60, 82, 50)[j]
        dt = t - t0
        if not 0 <= dt < 3.2:
            continue
        apex = 12 + (j % 3) * 4
        col = BCOL[j % 6]
        gy = ground_y(cx)
        if dt < 1.1:
            rr = gy - (gy - apex) * (dt / 1.1)
            for k in range(4):
                b.put(rr + k * 1.5, cx, 0.9 - k * 0.18,
                      "white" if k == 0 else col)
        else:
            e = dt - 1.1
            for k in range(54):
                ang = 2 * math.pi * k / 54
                spd = 6 + 5 * h(j, k)
                rr = apex + math.sin(ang) * spd * e * 0.8 + 2.2 * e * e
                cc = cx + math.cos(ang) * spd * e * 1.6
                fade = 1 - e / 2.1
                if fade > 0:
                    v = 0.95 * fade
                    ch = "*" if fade > 0.55 else None
                    b.put(rr, cc, v, col if k % 4 else "white", ch=ch)
                    if fade > 0.55:
                        b.put(rr + 1, cc, v * 0.5, col)


def greeting_v3(b, t, rainbow):
    if t < MSG_T0:
        return
    shown = min(len(MSG), int((t - MSG_T0) * MSG_RATE))
    c0 = (COLS - len(MSG)) // 2
    cols = (("red", "gold", "green", "cyan", "purple", "pink") if rainbow
            else ("gold",))
    for i in range(shown):
        if MSG[i] == " ":
            continue
        col = cols[(i + int(t * 2.5)) % len(cols)] if rainbow else "gold"
        b.put(20, c0 + i, 0.85 + 0.25 * math.sin(t * 5 + i), col, ch=MSG[i])
    if shown < len(MSG) and int(t * 3) % 2 == 0:
        b.put(20, c0 + shown, 0.9, "dim", ch="_")
    if shown == len(MSG) and rainbow:
        for k in range(14):
            if math.sin(t * 3 + k * 1.7) > 0.55:
                b.put(18 + h(k, 1) * 5, c0 - 6 + h(k, 2) * (len(MSG) + 12),
                      0.6, "gold" if k % 2 else "white", ch="*")


def hud_v3(b, t):
    landed = int(max(0.0, t - TAU[5]) * 41)
    dist = max(0.0, t - TL) * 1.7
    W.text(b, ROWS - 1, 2, f"@jaegyu.world  snow {landed}  dist {dist:.1f}km",
           "dim")
    on = int(t * 2) % 2 == 0
    W.text(b, 1, COLS - 12, f"{'●' if on else ' '} t {t:05.2f}s",
           "red" if on else "dim")


def frame(t):
    done, _ = typed(t)
    b = Buf()
    if done > 2:
        W.stars(b, t)
    if done > 3:
        W.moon(b)
    if done > 4:
        W.aurora(b, t)
    if done > 5:
        W.snowfall(b, t)
    if done > 6:
        W.ground_fill(b)
    if done > 7:
        W.pines(b)
    if done > 8:
        W.house(b, t, 30, 0)
    if done > 9:
        W.house(b, t, 58, 1)
    x, y = sx_at(t), sy_at(t)
    if done > 10:
        sleigh_art(b, x, y)
    if done > 11:
        rudolph_v3(b, x + 25, y, t, gallop=done > 14 and t > TL)
    if done > 12:
        line(b, x + 11, y - 4.0, x + 24, y - 6.0, "gold")
        line(b, x + 11, y - 2.6, x + 24, y - 4.2, "gold")
    if done > 13:
        lights(b, x, y, t)
    if done > 15:
        dust(b, t)
    if done > 16:
        gifts_v3(b, t)
    if done > 17:
        meteors_v3(b, t)
    if done > 18:
        greeting_v3(b, t, rainbow=done > 19)
    if done > 20:
        fireworks_v3(b, t)
    if done > 1:
        hud_v3(b, t)
    rows, colors = [], []
    for r in range(ROWS):
        rc, cc = [], []
        for c in range(COLS):
            cell = b.cell.get((r, c))
            if cell is None:
                rc.append(" ")
                cc.append(None)
            else:
                v, col, ch = cell
                idx = min(int(v * (len(W.RAMP) - 1)), len(W.RAMP) - 1)
                rc.append(ch or W.RAMP[idx])
                cc.append(col)
        rows.append("".join(rc))
        colors.append(cc)
    return rows, colors
