"""gen_autumn.py - composite hwadam_scene frames + synth music for the Short.

Usage:
  python3 gen_autumn.py frames START END   # render build frames to frames_v5/
  python3 gen_autumn.py audio              # write music_v4.wav + music_v5.wav
  python3 gen_autumn.py panel              # write panel_src.png
"""
import math
import os
import re
import struct
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import hwadam_scene as W
import hwadam_build as V4

FPS = W.FPS
DUR = V4.DUR
COLS, ROWS = W.COLS, W.ROWS
CW, CH = 11, 15                      # terminal cell px
TX, TY = 12, 40                      # terminal origin
BAR_Y0, BAR_Y1 = 1144, 1188          # editor tab bar
CODE_Y = BAR_Y1                      # code region start
W_PX, H_PX = 1080, 1920
BG = (16, 12, 14)

COLORS = {
    "white": (255, 255, 255), "dim": (120, 110, 115), "red": (255, 60, 55),
    "gold": (255, 210, 60), "pink": (255, 110, 200),
    "dusk1": (150, 70, 180), "dusk2": (230, 95, 125), "dusk3": (255, 135, 75),
    "dusk4": (255, 190, 100), "sun": (255, 220, 110), "cloud": (255, 195, 180),
    "ridge1": (185, 95, 105), "ridge2": (135, 75, 110),
    "rust": (225, 105, 45), "amber": (255, 200, 55),
    "crimson": (255, 45, 55), "orange": (255, 150, 25),
    "leaf_yellow": (255, 235, 95),
    "water": (75, 145, 205), "water_hi": (155, 220, 250),
    "pane": (45, 70, 105), "maple_red": (240, 25, 45),
    "leaf_green": (110, 190, 70),
    "wood": (215, 150, 80), "rail": (190, 180, 185), "cream": (255, 245, 215),
    "cream_sh": (205, 182, 140),
    "koi1": (255, 155, 55), "koi2": (250, 245, 235),
}

FONT_TERM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 15)
FONT_BAR = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 15)
FONT_CODE = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf", 17)
CODE_LH = 24
GUTTER = 52

_atlas = {}


def glyph(ch, color):
    key = (ch, color)
    tile = _atlas.get(key)
    if tile is None:
        im = Image.new("RGB", (CW, CH), BG)
        d = ImageDraw.Draw(im)
        d.text((1, -3 if ch == '_' else 1), ch, font=FONT_TERM, fill=COLORS[color])
        tile = np.asarray(im)
        _atlas[key] = tile
    return tile


def terminal_image(t):
    img = np.full((ROWS * CH, COLS * CW, 3), BG, dtype=np.uint8)
    rows, colors = V4.frame(t)
    for r in range(ROWS):
        row_ch, row_col = rows[r], colors[r]
        for c in range(COLS):
            col = row_col[c]
            if col is not None:
                img[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW] = glyph(row_ch[c], col)
    return img


# --- source panel with syntax highlighting ----------------------------------
KW = ("def for in if else elif return import from as while not and or None "
      "True False class self continue break").split()
BUILTINS = ("len int float range min max abs print enumerate zip str".split())
TOKEN = re.compile(
    r"(?P<comment>\#.*)|(?P<string>\"[^\"]*\"|'[^']*')|"
    r"(?P<number>\b\d+\.?\d*\b)|(?P<name>\b[A-Za-z_][A-Za-z0-9_]*\b)|"
    r"(?P<other>.)", re.S)
HL = {"comment": (106, 153, 85), "string": (206, 145, 120),
      "number": (181, 206, 168), "kw": (197, 134, 192),
      "builtin": (78, 201, 176), "defname": (220, 220, 170),
      "default": (212, 212, 212)}


def highlight_line(line):
    runs, want_def = [], False
    for m in TOKEN.finditer(line):
        kind = m.lastgroup
        s = m.group()
        if kind == "comment":
            color = HL["comment"]
        elif kind == "string":
            color = HL["string"]
        elif kind == "number":
            color = HL["number"]
        elif kind == "name":
            if s in KW:
                color = HL["kw"]
                want_def = s == "def"
            elif s in BUILTINS:
                color = HL["builtin"]
            elif want_def:
                color = HL["defname"]
                want_def = False
            else:
                color = HL["default"]
        else:
            color = HL["default"]
        runs.append((s, color))
    return runs


def render_panel_source():
    with open(os.path.join(os.path.dirname(__file__), "hwadam_scene.py")) as f:
        lines = f.read().rstrip("\n").split("\n")
    n = len(lines)
    im = Image.new("RGB", (W_PX, n * CODE_LH + 12), (13, 17, 23))
    d = ImageDraw.Draw(im)
    for i, line in enumerate(lines):
        y = 6 + i * CODE_LH
        d.text((GUTTER - 8, y + 2), str(i + 1), font=FONT_CODE,
               fill=(86, 95, 110), anchor="ra")
        x = GUTTER + 14
        for s, color in highlight_line(line):
            d.text((x, y + 2), s, font=FONT_CODE, fill=color)
            x += d.textlength(s, font=FONT_CODE)
    return im, n


_PANEL = None


def panel_typed(t):
    global _PANEL
    if _PANEL is None:
        _PANEL = render_panel_source()
    full, n = _PANEL
    vis = H_PX - CODE_Y
    line_idx, col = V4.typed_pos(t)
    cur_y = 6 + line_idx * CODE_LH
    scroll = max(0, min(cur_y - int(vis * 0.55), full.height - vis))
    crop = full.crop((0, scroll, W_PX, scroll + vis)).copy()
    d = ImageDraw.Draw(crop)
    y = cur_y - scroll                                # current line in window
    d.rectangle([0, y, W_PX, vis], fill=(13, 17, 23))  # untyped: hide
    d.rectangle([0, y, W_PX, y + CODE_LH], fill=(21, 27, 35))
    d.text((GUTTER - 8, y + 2), str(line_idx + 1), font=FONT_CODE,
           fill=(86, 95, 110), anchor="ra")
    x = GUTTER + 14
    prefix = V4.SRC_LINES[line_idx][:col]
    for s, color in highlight_line(prefix):
        d.text((x, y + 2), s, font=FONT_CODE, fill=color)
        x += d.textlength(s, font=FONT_CODE)
    if int(t * 3) % 2 == 0:
        d.rectangle([x + 2, y + 4, x + 11, y + CODE_LH - 4],
                    fill=(200, 210, 220))
    return crop


# --- v5: cold-open hook on the finished scene, then the build ---------------
HOOK_DUR = 2.5          # seconds of finished-scene cold open
HOOK_T0 = V4.BURST0 + 0.7   # timeline moment the hook plays from (leaf bursts)
V5_DUR = HOOK_DUR + V4.DUR


def render_frame(i):
    g = i / FPS
    if g < HOOK_DUR:
        t_scene = HOOK_T0 + g
        t_panel = V4.TYPING_END + 1.0     # fully typed file
    else:
        t_scene = t_panel = g - HOOK_DUR
    full = np.full((H_PX, W_PX, 3), BG, dtype=np.uint8)
    full[TY:TY + ROWS * CH, TX:TX + COLS * CW] = terminal_image(t_scene)
    im = Image.fromarray(full)
    im.paste(panel_typed(t_panel), (0, CODE_Y))
    d = ImageDraw.Draw(im)
    d.rectangle([0, BAR_Y0, W_PX, BAR_Y1], fill=(22, 27, 34))
    d.rounded_rectangle([24, BAR_Y0 + 8, 252, BAR_Y1 - 8], radius=6,
                        fill=(13, 17, 23), outline=(45, 52, 62))
    d.text((42, BAR_Y0 + 13), "* hwadam_scene.py", font=FONT_BAR,
           fill=(230, 237, 243))
    if g < HOOK_DUR or t_scene > V4.TL:
        d.text((W_PX - 26, BAR_Y0 + 13), "● running · 30 fps", font=FONT_BAR,
               fill=(255, 123, 114), anchor="ra")
    else:
        d.text((W_PX - 26, BAR_Y0 + 13), "○ typing · fast-forward",
               font=FONT_BAR, fill=(139, 148, 158), anchor="ra")
    d.line([0, BAR_Y0, W_PX, BAR_Y0], fill=(45, 52, 62))
    return im


def cmd_frames(a, b):
    os.makedirs("frames_v5", exist_ok=True)
    for i in range(a, b):
        render_frame(i).save(f"frames_v5/{i:04d}.png", compress_level=1)
        if i % 60 == 0:
            print(f"frame {i}", flush=True)


# --- music: music-box bells + pad + soft shaker, original autumn loop -------
SR = 44100


def bell(freq, dur, amp=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.exp(-t * 3.2) * np.minimum(1, t / 0.004)
    sig = np.zeros(n)
    for mul, a in ((1, 1.0), (2.4, 0.32), (5.1, 0.1)):
        sig += a * np.sin(2 * np.pi * freq * mul * t)
    return amp * env * sig


def pad(freqs, dur, amp=0.06):
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.5)
    sig = np.zeros(n)
    for f in freqs:
        sig += np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.005 * t)
    return amp * env * sig / len(freqs)


NOTE = {n: 440 * 2 ** ((i - 9) / 12) for i, n in
        enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def freq(name):
    m = re.match(r"([A-G]#?)(\d)", name)
    return NOTE[m.group(1)] * 2 ** (int(m.group(2)) - 4)


def cmd_audio():
    beat = 60 / 88
    chords = [("A2 C3 E3 G3", "A3 C4 E4 G4"), ("F2 A2 C3 E3", "F3 A3 C4 E4"),
              ("C3 E3 G3 B3", "C4 E4 G4 B4"), ("G2 B2 D3 F3", "G3 B3 D4 F4")]
    melody = ["A5 C6", "B5 A5", "F5 A5", "E5 G5",
              "C5 E5", "D5 F5", "E5 C5", "G5 E5",
              "A5 F5", "G5 A5", "F5 E5", "D5 C5", "E5 A5"]
    n_bars = 13
    total = int((V4.DUR + 1.5) * SR)
    mix = np.zeros(total)
    rng = np.random.default_rng(7)

    def place(sig, at):
        i0 = int(at * SR)
        mix[i0:i0 + len(sig)] += sig[:max(0, min(len(sig), total - i0))]

    for bar in range(n_bars):
        bass, tones = chords[bar % 4]
        t0 = bar * 4 * beat
        place(pad([freq(x) for x in bass.split()], 4 * beat), t0)
        arp = tones.split()
        pat = [arp[0], arp[1], arp[2], arp[3], arp[2], arp[1], arp[0], arp[1]]
        for j, name in enumerate(pat):
            place(bell(freq(name) / 2, 1.1, 0.15), t0 + j * beat / 2)
        for j, name in enumerate(melody[bar].split()):
            place(bell(freq(name), 1.6, 0.32), t0 + j * 2 * beat)
        for j in range(8):                            # soft shaker, offbeats
            burst = rng.standard_normal(int(0.03 * SR))
            burst *= np.exp(-np.arange(len(burst)) / (0.006 * SR))
            place(0.04 * burst, t0 + (j + 0.5) * beat / 2)

    rng2 = np.random.default_rng(11)                  # finale sparkle
    spark_notes = ["A5", "C6", "D6", "E6", "G6"]
    for j in range(20):
        name = spark_notes[int(rng2.integers(0, 5))]
        place(bell(freq(name), 0.8, 0.1), V4.MSG_T0 + 0.5 + j * 0.45)
    for j in range(V4.N_BURSTS):                      # leaf-burst whooshes
        t0 = V4.BURST0 + j * V4.BURST_STEP + 1.1
        n2 = int(0.6 * SR)
        tt = np.arange(n2) / SR
        place(0.16 * np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 6), t0)
        whoosh = rng2.standard_normal(n2) * np.exp(-tt * 5)
        place(0.05 * whoosh, t0)
    place(bell(freq("A5"), 3.5, 0.4), V4.DUR - 1.2)

    mix = np.tanh(mix * 1.2)
    n = len(mix)
    fi, fo = int(0.3 * SR), int(2.0 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix /= max(1e-9, np.abs(mix).max()) * 1.02
    pcm = (mix * 32767).astype(np.int16)
    with wave.open("music_v4.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"music_v4.wav {n / SR:.2f}s")

    # hook: lift the finale slice to the front, crossfaded into the top
    src = pcm.astype(np.float32)
    hook = src[int(HOOK_T0 * SR):int((HOOK_T0 + HOOK_DUR) * SR)]
    xf = int(0.05 * SR)
    out = np.zeros(len(hook) + len(src) - xf, dtype=np.float32)
    out[:len(hook) - xf] = hook[:-xf]
    ramp = np.linspace(0, 1, xf)
    out[len(hook) - xf:len(hook)] = hook[-xf:] * (1 - ramp) + src[:xf] * ramp
    out[len(hook):] = src[xf:]
    pcm2 = np.clip(out, -32767, 32767).astype(np.int16)
    with wave.open("music_v5.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm2.tobytes())
    print(f"music_v5.wav {len(pcm2) / SR:.2f}s")


if __name__ == "__main__":
    if sys.argv[1] == "frames":
        cmd_frames(int(sys.argv[2]), int(sys.argv[3]))
    elif sys.argv[1] == "audio":
        cmd_audio()
    elif sys.argv[1] == "panel":
        render_panel_source()[0].save("panel_src.png")
