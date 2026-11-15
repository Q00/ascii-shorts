"""hwadam_scene.py - ASCII autumn: the Hwadam forest monorail in 3D view.

A top-down corridor of dense maple foliage fills the whole frame; the
monorail track runs from a vanishing point toward the viewer and the car
rides it straight at the camera, growing as it approaches. Every piece
is a small function that draws into a sparse character grid. frame(t)
composes the full scene; each piece can also be drawn on its own, which
is how the typed-build cut assembles the world piece by piece.
Pure math, no state: everything is a function of t.
"""
import math

FPS = 30
DURATION = 33.0
COLS, ROWS = 96, 72
RAMP = " .':-~=+*#%@"

MSG = "HELLO AUTUMN"
MSG_LINES = (("HELLO", 8), ("AUTUMN", 22))
MSG_T0 = 22.0                         # greeting starts typing
N_LEAVES = 260
BURSTS = ((25.4, 20), (26.05, 48), (26.7, 72), (27.35, 34), (28.0, 60),
          (28.65, 82), (29.3, 50))
BCOL = ("crimson", "orange", "amber", "leaf_yellow", "rust", "pink")
LEAF_COLS = ("crimson", "orange", "amber", "leaf_yellow", "rust")

VP_R = 12                             # vanishing point row (col 48)


def h(n, k=0):
    """Stable pseudo-random float in [0, 1) from integers."""
    x = math.sin(n * 127.1 + k * 311.7) * 43758.5453
    return x - math.floor(x)


class Buf:
    """Sparse grid: (row, col) -> [fill, color, char]."""
    def __init__(self):
        self.cell = {}

    def put(self, r, c, v, color, ch=None):
        if 0 <= r < ROWS and 0 <= c < COLS:
            key = (int(r), int(c))
            cur = self.cell.get(key)
            if cur is None or v >= cur[0]:
                self.cell[key] = [v, color, ch]


def text(b, r, c, s, color):
    for i, ch in enumerate(s):
        b.put(r, c + i, 0.95, color, ch=ch)


def ellipse(b, cx, cy, rx, ry, color, k=1.0):
    for r in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for c in range(int(cx - rx) - 1, int(cx + rx) + 2):
            v = 1.0 - ((c - cx) / rx) ** 2 - ((r - cy) / ry) ** 2
            if v > 0:
                b.put(r, c, v * k, color)


def line(b, x0, y0, x1, y1, color, v=0.9):
    steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    for i in range(steps + 1):
        u = i / steps
        b.put(y0 + (y1 - y0) * u, x0 + (x1 - x0) * u, v, color)


# --- corridor geometry -------------------------------------------------------


def track_center(r):
    """Column of the track centerline at row r; gentle S-curve."""
    if r <= VP_R:
        return 48.0
    return 48.0 + 9.0 * math.sin((r - VP_R) / 26.0)


def corridor_hw(r):
    """Half width of the open corridor at row r (widens toward viewer)."""
    return 1.2 + max(0.0, r - VP_R) * 0.52


def rail_gauge(r):
    """Half distance between the rails at row r."""
    return 0.6 + max(0.0, r - VP_R) * 0.15


# --- foliage -----------------------------------------------------------------


def zone_color(r, c, i):
    """Autumn palette by screen zone, like the photo: crimson upper-left,
    pink-red right, orange top, yellow-green bottom."""
    if r < 26:
        pair = ("crimson", "maple_red") if c < 40 else (
            ("orange", "amber") if c < 60 else ("pink", "crimson"))
    elif r < 48:
        pair = ("maple_red", "orange") if c < 34 else (
            ("orange", "amber") if c < 62 else ("pink", "orange"))
    else:
        pair = ("leaf_yellow", "orange") if c < 40 else (
            ("leaf_green", "amber") if c < 62 else ("leaf_green", "orange"))
    return pair[i % 2]


def foliage_base(b, t):
    """Warm base wash over every cell: no black anywhere in the frame."""
    for r in range(ROWS):
        for c in range(COLS):
            v = 0.48 + 0.06 * math.sin(t * 0.8 + (r * 7 + c) * 0.13)
            in_corridor = r > VP_R and abs(c - track_center(r)) < corridor_hw(r)
            col = "rust" if in_corridor else zone_color(r, c, int(r + c))
            b.put(r, c, v, col, ch="'")


def canopy(b, t):
    """Dense blob foliage over the whole frame, cut by the track corridor.
    Blobs grow toward the bottom of the frame for the 3D depth feel."""
    for i in range(280):
        r = h(i, 1) * ROWS
        c = h(i, 2) * COLS
        if r > VP_R and abs(c - track_center(r)) < corridor_hw(r) + 1:
            continue                              # keep the corridor open
        depth = r / ROWS
        rx = 1.6 + depth * 4.2 + h(i, 3) * 1.8
        ry = 1.2 + depth * 2.6 + h(i, 4) * 1.2
        col = zone_color(r, c, i)
        k = 0.68 + 0.30 * h(i, 5) + 0.10 * math.sin(t * 1.7 + i)
        ellipse(b, c, r, rx, ry, col, k=k)
    for i in range(1050):                         # leaf speckle texture
        r = h(i, 11) * ROWS
        c = h(i, 12) * COLS
        if r > VP_R and abs(c - track_center(r)) < corridor_hw(r):
            continue
        v = 0.50 + 0.35 * h(i, 13)
        ch = "'*"[(i % 2)] if i % 5 == 0 else None
        b.put(r, c, v, zone_color(r, c, i + 1), ch=ch)
    for i in range(90):                           # canopy glitter
        if math.sin(t * 5.2 + i * 2.4) > 0.45:
            r = h(i, 15) * ROWS
            c = h(i, 16) * COLS
            b.put(r, c, 0.96,
                  ("gold", "white", "leaf_yellow")[i % 3], ch="+")


# --- track and car -----------------------------------------------------------


def track(b):
    """Perspective monorail beam: twin rails converging on the vanishing
    point, ties across, and a warm glow where the tunnel of foliage ends."""
    ellipse(b, 48, VP_R + 1, 9, 3.5, "amber", k=0.5)
    ellipse(b, 48, VP_R + 1, 4.5, 2.0, "leaf_yellow", k=0.55)
    for r in range(VP_R + 1, ROWS):
        cc = track_center(r)
        hw = corridor_hw(r)
        for c in range(int(cc - hw * 0.85), int(cc + hw * 0.85) + 1):
            b.put(r, c, 0.36, "wood")             # gravel bed
        g = rail_gauge(r)
        if r % 3 == 0:                            # ties
            for c in range(int(cc - g - 1), int(cc + g + 1) + 1):
                b.put(r, c, 0.58, "wood", ch="=")
        b.put(r, cc - g, 0.9, "rail", ch="!")
        b.put(r, cc + g, 0.9, "rail", ch="!")


def monorail(b, t, p):
    """The car, front view, at approach depth p (0 far .. 1 at camera)."""
    rb = VP_R + 3 + p * (ROWS - 10 - VP_R)        # bottom row of the car
    cc = track_center(rb)
    w = 5.0 + 30.0 * p                            # full width in cols
    hgt = 3.0 + 15.0 * p                          # height in rows
    top = rb - hgt
    hw = w / 2.0
    V = 1.02                                      # car beats foliage
    d = max(1, int(hw * 0.32))                    # 3D depth offset
    # shadow on the beam under the car
    ellipse(b, cc + d * 0.5, rb + 1.2, hw * 1.05, 1.4, "dim", k=0.55)
    # right side face (parallelogram, shaded)
    for dc in range(1, d + 1):
        for r in range(int(top + dc), int(rb - hgt * 0.10) + 1):
            b.put(r, cc + hw + dc, V - 0.015, "cream_sh", ch="▒")
    for dc in range(1, d + 1):                    # side window band
        r = int(ws_row := top + hgt * 0.25) + dc // 2
        for rr in range(r, r + max(1, int(hgt * 0.2))):
            b.put(rr, cc + hw + dc, V - 0.015, "pane", ch="▒")
    # roof top face (slants up-right)
    for dr in range(1, d + 1):
        for c in range(int(cc - hw + dr), int(cc + hw + dr) + 1):
            b.put(top - dr, c, V - 0.005, "cream_sh", ch="=")
    # roof vent box
    for r in range(int(top), int(top + max(1, hgt * 0.12))):
        for c in range(int(cc - hw * 0.55), int(cc + hw * 0.55) + 1):
            b.put(r, c, V, "cream", ch="=")
    # roof line
    for c in range(int(cc - hw), int(cc + hw) + 1):
        b.put(top + hgt * 0.12, c, V, "cream", ch="-")
    # body sides
    body_top = top + hgt * 0.12
    for r in range(int(body_top), int(rb) + 1):
        b.put(r, cc - hw, V, "cream", ch="|")
        b.put(r, cc + hw, V, "cream", ch="|")
    # windshield
    ws0 = body_top + max(1, hgt * 0.06)
    ws1 = ws0 + hgt * 0.36
    for r in range(int(ws0), int(ws1)):
        for c in range(int(cc - hw) + 1, int(cc + hw)):
            b.put(r, c, V - 0.01, "pane", ch="▓")
    if p > 0.3:                                   # center pillar + wiper
        for r in range(int(ws0), int(ws1)):
            b.put(r, cc, V, "cream", ch="|")
        line(b, cc - hw * 0.3, ws1 - 1, cc + hw * 0.15, ws0 + 1, "cream",
             v=V)
    if p > 0.5:                                   # passengers inside
        for k in range(4):
            b.put(ws0 + 1 + (k % 2) * 2, cc - hw * 0.5 + k * hw * 0.33,
                  V - 0.02, "dim", ch="@")
    # destination band
    for c in range(int(cc - hw * 0.4), int(cc + hw * 0.4) + 1):
        b.put(ws0 - 1, c, V, "amber", ch="-")
    # cream panel under the glass
    for r in range(int(ws1), int(rb - hgt * 0.16)):
        for c in range(int(cc - hw) + 1, int(cc + hw)):
            b.put(r, c, V, "cream", ch="█")
    # orange skirt with the dark stripe
    for r in range(int(rb - hgt * 0.16), int(rb) + 1):
        for c in range(int(cc - hw) + 1, int(cc + hw)):
            b.put(r, c, V, "orange", ch="▬")
    for c in range(int(cc - hw * 0.5), int(cc + hw * 0.5) + 1):
        b.put(rb - hgt * 0.08, c, V, "dim", ch="▬")
    # headlights
    blink = 1.06 if int(t * 2.4) % 2 == 0 else 0.9
    b.put(rb - hgt * 0.12, cc - hw * 0.72, blink, "gold", ch="*")
    b.put(rb - hgt * 0.12, cc + hw * 0.72, blink, "gold", ch="*")
    # headlight glow spilling onto the beam ahead
    ellipse(b, cc, rb + 1.5, hw * 0.9, 2.2, "gold", k=0.3)


def leaf_wake(b, t, p):
    """Leaves kicked up around the car as it rides toward the camera."""
    rb = VP_R + 3 + p * (ROWS - 10 - VP_R)
    cc = track_center(rb)
    spread = 4 + 16 * p
    for k in range(26):
        ang = t * 3.0 + k * 2.4
        rr = rb - (k % 7) * (1 + 2 * p) - 1
        ccx = cc + math.sin(ang) * spread * (0.4 + h(k, 3))
        col = LEAF_COLS[k % 5]
        ch = "*" if k % 4 == 0 else None
        b.put(rr, ccx, 0.62 + 0.25 * h(k, 5), col, ch=ch)


def falling_leaves(b, t):
    for i in range(N_LEAVES):
        depth = h(i, 4)
        c = (h(i, 1) * COLS + 9 * math.sin(t * 0.6 + i)) % COLS
        r = (h(i, 2) * ROWS + t * (2.5 + 4 * depth)) % ROWS
        col = LEAF_COLS[i % 5]
        ch = "*" if i % 6 == 0 else None
        b.put(r, c, 0.42 + 0.5 * depth, col, ch=ch)
    for i in range(48):                           # twirl sparkles
        if math.sin(t * 4.5 + i * 2.9) > 0.5:
            c = (h(i, 21) * COLS + 6 * math.sin(t + i)) % COLS
            r = (h(i, 22) * ROWS + t * 5) % ROWS
            b.put(r, c, 0.95, ("gold", "white")[i % 2], ch="+")


BIG_FONT = {                                 # 3x5 pixel letters for greeting
    "H": ("# #", "# #", "###", "# #", "# #"),
    "E": ("###", "#  ", "###", "#  ", "###"),
    "L": ("#  ", "#  ", "#  ", "#  ", "###"),
    "O": ("###", "# #", "# #", "# #", "###"),
    "A": (" # ", "# #", "###", "# #", "# #"),
    "U": ("# #", "# #", "# #", "# #", "###"),
    "T": ("###", " # ", " # ", " # ", " # "),
    "M": ("# #", "###", "# #", "# #", "# #"),
    "N": ("# #", "###", "###", "# #", "# #"),
    " ": ("   ", "   ", "   ", "   ", "   "),
}
SCALE = 2                                      # cells per font pixel


def _letter_slot(ord_):
    """-> (top row, left col, glyph) of the ord_-th letter of MSG."""
    done = 0
    for word, top in MSG_LINES:
        width = len(word) * 4 * SCALE - SCALE
        c0 = (COLS - width) // 2
        for i, ch in enumerate(word):
            if done == ord_:
                return top, c0 + i * 4 * SCALE, BIG_FONT[ch]
            done += 1
    return None


def greeting(b, t, msg_t0=MSG_T0, rainbow=True):
    if t < msg_t0:
        return
    shown = min(len(MSG), int((t - msg_t0) * 7))
    cols = ("crimson", "orange", "amber", "leaf_yellow", "pink", "red")
    for i in range(shown):
        if MSG[i] == " ":
            continue
        ord_ = sum(1 for ch in MSG[:i] if ch != " ")
        top, left, glyph = _letter_slot(ord_)
        col = cols[(i + int(t * 2.5)) % 6] if rainbow else "gold"
        v = 0.85 + 0.25 * math.sin(t * 5 + i)
        for gy, row in enumerate(glyph):
            for gx, cell in enumerate(row):
                if cell != "#":
                    continue
                for dr in range(SCALE):
                    for dc in range(SCALE):
                        b.put(top + gy * SCALE + dr, left + gx * SCALE + dc,
                              v, col, ch="█")
    if shown < len(MSG) and MSG[shown] != " " and int(t * 3) % 2 == 0:
        ord_ = sum(1 for ch in MSG[:shown] if ch != " ")
        slot = _letter_slot(ord_)
        if slot:
            b.put(slot[0] + 5 * SCALE, slot[1], 0.9, "dim", ch="_")
    if shown >= len(MSG):                        # halo sparkles
        for k in range(44):
            if math.sin(t * 4 + k * 1.7) > 0.3:
                b.put(4 + h(k, 1) * 30, 6 + h(k, 2) * (COLS - 12),
                      0.7, ("gold", "white", "amber")[k % 3], ch="*")


def leafburst(b, t, bursts=BURSTS):
    for j, (t0, cx) in enumerate(bursts):
        dt = t - t0
        if not 0 <= dt < 3.2:
            continue
        apex = 14 + (j % 3) * 4
        col = BCOL[j % 6]
        gy = ROWS - 2
        if dt < 1.1:                              # rising leaf stream
            rr = gy - (gy - apex) * (dt / 1.1)
            for k in range(4):
                b.put(rr + k * 1.5, cx + math.sin(dt * 6 + k) * 1.5,
                      0.9 - k * 0.18, "gold" if k == 0 else col)
        else:                                     # burst of leaves
            e = dt - 1.1
            for k in range(96):
                ang = 2 * math.pi * k / 96
                spd = 7 + 5 * h(j, k)
                rr = apex + math.sin(ang) * spd * e * 0.8 + 2.2 * e * e
                cc = cx + math.cos(ang) * spd * e * 1.6 \
                    + math.sin(e * 5 + k) * 1.5
                fade = 1 - e / 2.1
                if fade > 0:
                    v = (0.35 + 0.65 * h(k, j + 3)) * fade
                    b.put(rr, cc, v, BCOL[(j + k) % 6],
                          ch="*" if k % 9 == 0 else None)


def hud(b, t, dist_from=0.0):
    fallen = int(max(0.0, t - 1) * 53)
    dist = max(0.0, t - dist_from) * 0.8
    text(b, ROWS - 1, 2,
         f"@jaegyu.world  leaves {fallen}  ride {dist:.1f}km", "dim")
    on = int(t * 2) % 2 == 0
    text(b, 1, COLS - 12, f"{'●' if on else ' '} t {t:05.2f}s",
         "red" if on else "dim")


def grid(b):
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
                idx = min(int(v * (len(RAMP) - 1)), len(RAMP) - 1)
                rc.append(ch or RAMP[idx])
                cc.append(col)
        rows.append("".join(rc))
        colors.append(cc)
    return rows, colors


def frame(t, p=0.62):
    b = Buf()
    foliage_base(b, t)
    canopy(b, t)
    track(b)
    monorail(b, t, p)
    leaf_wake(b, t, p)
    falling_leaves(b, t)
    greeting(b, t)
    leafburst(b, t)
    hud(b, t)
    return grid(b)


if __name__ == "__main__":
    import sys
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
    for row in frame(t)[0]:
        print(row)
