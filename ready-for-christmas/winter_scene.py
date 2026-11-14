"""winter_scene.py - ASCII winter night: Rudolph & Santa over a snowy field.

Every scene piece is a small function that draws into a sparse character
grid. frame(t) composes the full scene; each piece can also be drawn on
its own, which is how the typed-build cut assembles the world piece by
piece. Pure math, no state: everything is a function of t.
"""
import math

FPS = 30
DURATION = 22.0
COLS, ROWS = 96, 72
RAMP = " .':-~=+*#%@"

SLEIGH_T0, SLEIGH_T1 = 2.5, 12.5      # flight window, seconds
MSG_T0 = 14.5                         # greeting starts typing
MSG = "MERRY CHRISTMAS"
N_SNOW, N_STARS = 320, 130
DROPS = (8.5, 10.0, 11.5)             # gift drop times
STREAKS = ((1.5, 8, 70), (6.5, 4, 30), (13.5, 6, 55))
BURSTS = ((16.6, 20), (17.4, 48), (18.2, 72), (19.0, 34), (19.8, 60),
          (20.6, 82), (21.2, 50))
BCOL = ("gold", "red", "cyan", "purple", "green", "pink")


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


def aurora(b, t):
    cols = ("green", "cyan", "purple", "blue")
    for c in range(COLS):
        for k in range(3):
            r = 3 + k * 3 + 2.0 * math.sin(c * 0.09 + t * 0.7 + k * 1.7) \
                + 1.5 * math.sin(c * 0.031 - t * 0.45 + k)
            v = 0.55 - k * 0.09 + 0.10 * math.sin(t * 1.3 + c * 0.2)
            b.put(r, c, max(0.16, v), cols[(c // 24 + k) % 4])


def stars(b, t):
    for i in range(N_STARS):
        c, r = h(i, 1) * COLS, h(i, 2) * ROWS * 0.72
        tw = 0.5 + 0.5 * math.sin(t * 2.2 + i * 1.3)
        col = ("star", "star", "gold", "cyan")[i % 4]
        b.put(r, c, 0.35 + 0.65 * tw, col)
    for i in range(46):                           # glitter pops
        if math.sin(t * 6 + i * 2.7) > 0.72:
            c, r = h(i, 5) * COLS, h(i, 6) * ROWS * 0.7
            b.put(r, c, 0.98, ("white", "gold", "cyan")[i % 3], ch="+")


def moon(b):
    ellipse(b, COLS - 14, 7, 4.6, 3.8, "moon")            # moon + halo
    ellipse(b, COLS - 14, 7, 6.6, 5.6, "moon", k=0.16)


def snowfall(b, t):
    for i in range(N_SNOW):                               # falling snow
        depth = h(i, 4)
        c = (h(i, 1) * COLS + 6 * math.sin(t * 0.7 + i)) % COLS
        r = (h(i, 2) * ROWS + t * (3 + 5 * depth)) % ROWS
        col = ("snow1", "snow2", "snow3")[int(depth * 2.99)]
        b.put(r, c, 0.35 + 0.5 * depth, col)
    for i in range(26):                           # glints on the drifts
        if math.sin(t * 5 + i * 3.1) > 0.78:
            c = h(i, 7) * COLS
            b.put(ground_y(c) + h(i, 8) * 4, c, 0.9, "white", ch="+")


def ground_y(c):
    return ROWS - 5 - 1.6 * math.sin(c * 0.15) - 1.2 * math.sin(c * 0.047 + 2)


def ground_fill(b):
    for c in range(COLS):
        gy = ground_y(c)
        for r in range(int(gy), ROWS):
            b.put(r, c, 0.18 + 0.3 * (r - gy) / 6, "snow3")
        b.put(int(gy), c, 0.85, "snow1")


def pines(b):
    for x0 in (8, COLS - 8):                              # pine trees
        gy = ground_y(x0)
        for i in range(7):
            line(b, x0 - i * 0.8, gy - 7 + i, x0 + i * 0.8, gy - 7 + i,
                 "green", v=0.45)
        line(b, x0, gy, x0, gy - 1, "brown")


HOUSE = [
    r"    /\    ",
    r"   /##\   ",
    r"  /####\  ",
    r"  | [] |  ",
    r"  |____|  ",
]


def art(b, r0, c0, lines, color, ov=None, rows=None):
    """Blit an ASCII-art sprite; ov overrides colors per character."""
    for r, ln in enumerate(lines):
        col = rows.get(r, color) if rows else color
        for c, ch in enumerate(ln):
            if ch == " ":
                continue
            cc = ov.get(ch, col) if ov else col
            v = 0.35 if ch == "." else 0.92
            b.put(r0 + r, c0 + c, v, cc, ch=ch)


def house(b, t, x0, j):
    gy = int(ground_y(x0 + 2))
    art(b, gy - 4, x0, HOUSE, "brown",
        {"#": "red", "/": "red", "\\": "red", "[": "gold", "]": "gold"})
    for k in range(3):                                    # chimney smoke
        ph = (t * 0.8 + k * 0.7 + j) % 2.4
        b.put(gy - 5 - ph, x0 + 8 + math.sin(ph * 2 + k),
              max(0.1, 0.5 - ph * 0.18), "dim",
              ch="o" if k == 0 else ".")


RUDOLPH = [
    r"  \ /   \ /   ",
    r"   V     V    ",
    r"   |     |    ",
    r"  ( o   )>*   ",
    r"   \    /     ",
    r"   |    |     ",
    r" _/      \___ ",
    r"/           \ ",
    r"|             |",
    r" \           / ",
]
LEGS = [
    ["   |  |  |    ", "   |  |  |    "],
    ["  /   |   \   ", " /    |    \  "],
]
SANTA = [
    r"     *     ",
    r"    /_\    ",
    r"   ( o o ) ",
    r"   ( ~~~ ) ",
    r"  _/|   |\_ ",
    r" (  |   |  )",
    r"  \ |___| / ",
]
SACK = [
    r"  (~~~)  ",
    r" ( ~~~ ) ",
    r"  \___/  ",
]
SLEIGH = [
    r"  ______________________   ",
    r" /......................\  ",
    r"  \____________________/   ",
    r"   ~===~~~===~~~===~~~ _/  ",
]


def reindeer(b, x, y, t, gallop=True):
    r0, c0 = int(y) - 16, int(x)
    ov = {"o": "white", "*": "red"}
    rows = {0: "tan", 1: "tan", 2: "tan"}
    art(b, r0, c0, RUDOLPH, "brown", ov, rows)
    phase = int(t * 7) % 2 if gallop else 0       # gallop swap
    art(b, r0 + 10, c0, LEGS[phase], "brown")
    pulse = 0.55 + 0.35 * math.sin(t * 6)         # nose glow
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
    bulbs = ("red", "green", "gold")              # fairy lights on hull
    for i, c in enumerate(range(-10, 11, 2)):
        b.put(y - 2, x + c, 0.96, bulbs[(i + int(t * 4)) % 3], ch="*")
    cols = ("red", "green", "gold", "cyan")       # string across reins
    for i in range(1, 7):
        u = i / 7
        sag = math.sin(u * math.pi) * 0.8
        b.put(y - 3.3 - 1.8 * u + sag, x + 11 + 13 * u, 0.95,
              cols[(i + int(t * 4)) % 4], ch="*")


def reins(b, x, y):
    line(b, x + 11, y - 4.0, x + 24, y - 6.0, "gold")
    line(b, x + 11, y - 2.6, x + 24, y - 4.2, "gold")


def sleigh_pos(t):
    u = (t - SLEIGH_T0) / (SLEIGH_T1 - SLEIGH_T0)
    x = -60 + (COLS + 100) * u
    y = 30 + 1.8 * math.sin(t * 4.4) + 0.9 * math.sin(t * 8.2 + 1)
    return x, y


def dust(b, t, pos):
    for k in range(26):                           # magic dust trail
        age = k * 0.055
        px, py = pos(t - age)
        px += (h(k, 1) - 0.5) * 10
        py += (h(k, 2) - 0.5) * 7 + age * 3
        fade = 1 - age / 1.5
        if fade > 0:
            b.put(py, px, 0.75 * fade, "gold" if k % 3 else "white")


def sleigh_group(b, t):
    x, y = sleigh_pos(t)
    sleigh_art(b, x, y)
    reindeer(b, x + 25, y, t)
    reins(b, x, y)
    lights(b, x, y, t)
    dust(b, t, sleigh_pos)


def meteors(b, t, streaks=STREAKS):
    for t0, r0, c0 in streaks:
        dt = t - t0
        if not 0 <= dt < 0.9:
            continue
        for k in range(12):
            age = dt - k * 0.018
            if age < 0:
                continue
            b.put(r0 + age * 9, c0 + age * 26, max(0.1, 0.95 - k * 0.08),
                  "white" if k < 3 else "star")


def gifts(b, t, pos, drops=DROPS):
    for k, t0 in enumerate(drops):
        if t < t0:
            continue
        x, y0 = pos(t0)
        x += (h(k, 9) - 0.5) * 6
        gy = ground_y(x) - 1.6
        y = min(y0 + 3 + 4.6 * (t - t0) ** 2, gy)
        col = ("red", "gold", "blue")[k % 3]
        for dr in range(2):
            for dc in range(3):
                b.put(y + dr, x - 1 + dc, 0.9, col)
        b.put(y - 1, x, 1.0, "white")             # bow
        if y >= gy:                               # landed: sparkle
            for s in range(3):
                if math.sin(t * 4 + s * 2.1 + k) > 0.5:
                    b.put(y - 2 - (s % 2), x - 2 + s * 2, 0.8,
                          "white" if s % 2 else "gold", ch="*")


BIG_FONT = {                                 # 3x5 pixel letters for greeting
    "M": ("#.#", "###", "#.#", "#.#", "#.#"),
    "E": ("###", "#..", "##.", "#..", "###"),
    "R": ("##.", "#.#", "##.", "#.#", "#.#"),
    "Y": ("#.#", "#.#", ".#.", ".#.", ".#."),
    "C": (".##", "#..", "#..", "#..", ".##"),
    "H": ("#.#", "#.#", "###", "#.#", "#.#"),
    "I": ("###", ".#.", ".#.", ".#.", "###"),
    "S": (".##", "#..", ".#.", "..#", "##."),
    "T": ("###", ".#.", ".#.", ".#.", ".#."),
    "A": (".#.", "#.#", "###", "#.#", "#.#"),
}
MSG_LINES = (("MERRY", 6), ("CHRISTMAS", 19))   # (text, top row)
SCALE = 2                                      # cells per font pixel


def _letter_slot(ord_):
    """Non-space letter ordinal in MSG -> (top row, left col, glyph) at 2x."""
    done = 0
    for word, top in MSG_LINES:
        w = len(word) * 4 * SCALE - 2 * SCALE
        c0 = (COLS - w) // 2
        for i, ch in enumerate(word):
            if done == ord_:
                return top, c0 + i * 4 * SCALE, BIG_FONT[ch]
            done += 1
    return None


def greeting(b, t, msg_t0=MSG_T0, rainbow=True):
    if t < msg_t0:
        return
    shown = min(len(MSG), int((t - msg_t0) * 7))
    cols = ("red", "gold", "green", "cyan", "purple", "pink")
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
        for k in range(26):
            if math.sin(t * 4 + k * 1.7) > 0.45:
                b.put(4 + h(k, 1) * 28, 6 + h(k, 2) * (COLS - 12),
                      0.7, ("gold", "white", "cyan")[k % 3], ch="*")


def fireworks(b, t, bursts=BURSTS):
    for j, (t0, cx) in enumerate(bursts):
        dt = t - t0
        if not 0 <= dt < 3.2:
            continue
        apex = 12 + (j % 3) * 4
        col = BCOL[j % 6]
        gy = ground_y(cx)
        if dt < 1.1:                              # rocket rising
            rr = gy - (gy - apex) * (dt / 1.1)
            for k in range(4):
                b.put(rr + k * 1.5, cx, 0.9 - k * 0.18,
                      "white" if k == 0 else col)
        else:                                     # burst
            e = dt - 1.1
            for k in range(72):
                ang = 2 * math.pi * k / 72
                spd = 7 + 5 * h(j, k)
                rr = apex + math.sin(ang) * spd * e * 0.8 + 2.2 * e * e
                cc = cx + math.cos(ang) * spd * e * 1.6
                fade = 1 - e / 2.1
                if fade > 0:
                    v = 0.95 * fade
                    ch = "*" if fade > 0.45 else None
                    b.put(rr, cc, v, col if k % 3 else "white", ch=ch)
                    if fade > 0.45:               # glow neighbor
                        b.put(rr + 1, cc, v * 0.6, col)
                        b.put(rr, cc + 1, v * 0.6, col)


def hud(b, t, dist_from=SLEIGH_T0):
    landed = int(max(0.0, t - 1) * 41)
    dist = max(0.0, t - dist_from) * 1.7
    text(b, ROWS - 1, 2, f"@jaegyu.world  snow {landed}  dist {dist:.1f}km",
         "dim")
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


def frame(t):
    b = Buf()
    aurora(b, t)
    stars(b, t)
    moon(b)
    snowfall(b, t)
    ground_fill(b)
    pines(b)
    for j, x0 in enumerate((30, 58)):
        house(b, t, x0, j)
    if SLEIGH_T0 - 1 < t < SLEIGH_T1 + 1.5:
        sleigh_group(b, t)
    gifts(b, t, sleigh_pos)
    meteors(b, t)
    fireworks(b, t)
    greeting(b, t)
    hud(b, t)
    return grid(b)


if __name__ == "__main__":
    import sys
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
    for row in frame(t)[0]:
        print(row)
