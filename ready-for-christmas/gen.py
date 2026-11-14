"""gen.py - composite winter_scene frames + synth music for the Short.

Usage:
  python3 gen.py frames START END   # render frames [START, END) to frames/
  python3 gen.py audio              # write music.wav
  python3 gen.py panel              # write panel_src.png (highlighted source)
"""
import math
import os
import re
import struct
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import winter_scene as W
import winter_v3 as V3
import winter_v4 as V4

FPS = W.FPS
DUR = W.DURATION
COLS, ROWS = W.COLS, W.ROWS
CW, CH = 11, 15                      # terminal cell px
TX, TY = 12, 40                      # terminal origin
BAR_Y0, BAR_Y1 = 1144, 1188          # editor tab bar
CODE_Y = BAR_Y1                      # code region start
W_PX, H_PX = 1080, 1920
BG = (10, 14, 20)

COLORS = {
    "snow1": (255, 255, 255), "snow2": (210, 220, 245), "snow3": (150, 165, 200),
    "star": (235, 240, 255), "moon": (255, 250, 210), "gold": (255, 210, 60),
    "red": (255, 60, 55), "green": (70, 255, 110), "white": (255, 255, 255),
    "brown": (185, 130, 75), "tan": (225, 185, 120), "skin": (255, 210, 170),
    "dim": (110, 120, 135), "blue": (100, 180, 255),
    "cyan": (60, 240, 255), "purple": (190, 120, 255), "pink": (255, 110, 220),
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
        d.text((1, 1), ch, font=FONT_TERM, fill=COLORS[color])
        tile = np.asarray(im)
        _atlas[key] = tile
    return tile


def terminal_image(t):
    img = np.full((ROWS * CH, COLS * CW, 3), BG, dtype=np.uint8)
    rows, colors = W.frame(t)
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
    runs, pos, want_def = [], 0, False
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
        pos = m.end()
    return runs


def render_panel_source():
    with open(os.path.join(os.path.dirname(__file__), "winter_scene.py")) as f:
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


def panel_crop(t):
    global _PANEL
    if _PANEL is None:
        _PANEL = render_panel_source()
    im, n = _PANEL
    vis = H_PX - CODE_Y
    scroll_max = im.height - vis
    p = min(1.0, t / (DUR - 2))
    p = p * p * (3 - 2 * p)                      # smoothstep
    scroll = int(scroll_max * p)
    crop = im.crop((0, scroll, W_PX, scroll + vis)).convert("RGBA")
    band = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    cur = scroll + int((im.height - vis - CODE_LH) * 0)  # highlight follows
    line_i = int(p * (n - vis // CODE_LH - 1))
    y = 6 + line_i * CODE_LH - scroll
    bd.rectangle([0, y, W_PX, y + CODE_LH], fill=(255, 255, 255, 12))
    return Image.alpha_composite(crop, band).convert("RGB")


def render_frame(i):
    t = i / FPS
    full = np.full((H_PX, W_PX, 3), BG, dtype=np.uint8)
    full[TY:TY + ROWS * CH, TX:TX + COLS * CW] = terminal_image(t)
    im = Image.fromarray(full)
    im.paste(panel_crop(t), (0, CODE_Y))
    d = ImageDraw.Draw(im)
    d.rectangle([0, BAR_Y0, W_PX, BAR_Y1], fill=(22, 27, 34))
    d.rounded_rectangle([24, BAR_Y0 + 8, 236, BAR_Y1 - 8], radius=6,
                        fill=(13, 17, 23), outline=(45, 52, 62))
    d.text((42, BAR_Y0 + 13), "* winter_scene.py", font=FONT_BAR,
           fill=(230, 237, 243))
    d.text((W_PX - 26, BAR_Y0 + 13), "● running · 30 fps", font=FONT_BAR,
           fill=(255, 123, 114), anchor="ra")
    d.line([0, BAR_Y0, W_PX, BAR_Y0], fill=(45, 52, 62))
    return im


def cmd_frames(a, b):
    os.makedirs("frames", exist_ok=True)
    for i in range(a, b):
        render_frame(i).save(f"frames/{i:04d}.png", compress_level=1)
        if i % 60 == 0:
            print(f"frame {i}", flush=True)


# --- v3: typed build ---------------------------------------------------------
V3_DUR = 30.0


def terminal_image_v3(t):
    img = np.full((ROWS * CH, COLS * CW, 3), BG, dtype=np.uint8)
    rows, colors = V3.frame(t)
    for r in range(ROWS):
        row_ch, row_col = rows[r], colors[r]
        for c in range(COLS):
            col = row_col[c]
            if col is not None:
                img[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW] = glyph(row_ch[c], col)
    return img


def panel_typing(t):
    done, partial = V3.typed(t)
    im = Image.new("RGB", (W_PX, H_PX - CODE_Y), (13, 17, 23))
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(V3.SCRIPT):
        y = 6 + i * CODE_LH
        if y + CODE_LH > im.height:
            break
        d.text((GUTTER - 8, y + 2), str(i + 1), font=FONT_CODE,
               fill=(86, 95, 110), anchor="ra")
        if i < done:
            text = ln
        elif i == done:
            text = partial
        else:
            continue
        if i == done:
            d.rectangle([0, y, W_PX, y + CODE_LH], fill=(21, 27, 35))
        x = GUTTER + 14
        for s, color in highlight_line(text):
            d.text((x, y + 2), s, font=FONT_CODE, fill=color)
            x += d.textlength(s, font=FONT_CODE)
        if i == done and int(t * 2.5) % 2 == 0:
            d.rectangle([x + 2, y + 4, x + 11, y + CODE_LH - 4],
                        fill=(200, 210, 220))
    return im


def render_frame_v3(i):
    t = i / FPS
    full = np.full((H_PX, W_PX, 3), BG, dtype=np.uint8)
    full[TY:TY + ROWS * CH, TX:TX + COLS * CW] = terminal_image_v3(t)
    im = Image.fromarray(full)
    im.paste(panel_typing(t), (0, CODE_Y))
    d = ImageDraw.Draw(im)
    d.rectangle([0, BAR_Y0, W_PX, BAR_Y1], fill=(22, 27, 34))
    d.rounded_rectangle([24, BAR_Y0 + 8, 252, BAR_Y1 - 8], radius=6,
                        fill=(13, 17, 23), outline=(45, 52, 62))
    d.text((42, BAR_Y0 + 13), "* build_winter.py", font=FONT_BAR,
           fill=(230, 237, 243))
    done, _ = V3.typed(t)
    if done >= len(V3.SCRIPT):
        d.text((W_PX - 26, BAR_Y0 + 13), "● running · 30 fps", font=FONT_BAR,
               fill=(255, 123, 114), anchor="ra")
    else:
        d.text((W_PX - 26, BAR_Y0 + 13), "○ editing", font=FONT_BAR,
               fill=(139, 148, 158), anchor="ra")
    d.line([0, BAR_Y0, W_PX, BAR_Y0], fill=(45, 52, 62))
    return im


def cmd_frames_v3(a, b):
    os.makedirs("frames_v3", exist_ok=True)
    for i in range(a, b):
        render_frame_v3(i).save(f"frames_v3/{i:04d}.png", compress_level=1)
        if i % 60 == 0:
            print(f"frame {i}", flush=True)


def cmd_audio_v3():
    beat = 60 / 92
    chords = [("C3 E3 G3 B3", "C4 E4 G4 B4"), ("A2 C3 E3 G3", "A3 C4 E4 G4"),
              ("F2 A2 C3 E3", "F3 A3 C4 E4"), ("G2 B2 D3 F3", "G3 B3 D4 F4")]
    melody = ["E5 G5", "E5 C5", "F5 A5", "G5 B5",
              "E5 G5", "A5 G5", "F5 E5", "D5 E5", "C5 C5",
              "E5 G5", "E5 C5", "F5 A5"]
    n_bars = 12
    total = int((V3_DUR + 1.0) * SR)
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
            place(bell(freq(name) / 2, 1.1, 0.16), t0 + j * beat / 2)
        for j, name in enumerate(melody[bar].split()):
            place(bell(freq(name), 1.6, 0.34), t0 + j * 2 * beat)
        for j in range(8):
            burst = rng.standard_normal(int(0.03 * SR))
            burst *= np.exp(-np.arange(len(burst)) / (0.006 * SR))
            place(0.05 * burst, t0 + (j + 0.5) * beat / 2)

    clicks, enters = V3.char_times()                # typing keys
    for ct in clicks:
        c = rng.standard_normal(int(0.008 * SR))
        c *= np.exp(-np.arange(len(c)) / (0.002 * SR))
        place(0.05 * c, ct)
    for et in enters:
        c = rng.standard_normal(int(0.02 * SR))
        c *= np.exp(-np.arange(len(c)) / (0.004 * SR))
        place(0.09 * c, et)

    rng2 = np.random.default_rng(11)                  # finale sparkle
    spark_notes = ["C6", "D6", "E6", "G6", "A6"]
    for j in range(20):
        name = spark_notes[int(rng2.integers(0, 5))]
        place(bell(freq(name), 0.8, 0.1), 19.5 + j * 0.45)
    for j in range(7):                                # firework booms
        t0 = V3.BURST0 + j * V3.BURST_STEP + 1.1
        n2 = int(0.6 * SR)
        tt = np.arange(n2) / SR
        place(0.3 * np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 6), t0)
    place(bell(freq("C5"), 3.5, 0.4), 29.0)

    mix = np.tanh(mix * 1.2)
    n = len(mix)
    fi, fo = int(0.3 * SR), int(2.0 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix /= max(1e-9, np.abs(mix).max()) * 1.02
    pcm = (mix * 32767).astype(np.int16)
    with wave.open("music_v3.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"music_v3.wav {n / SR:.2f}s")


# --- music: music-box bells + pad + sleigh bells, original loop -------------
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
    beat = 60 / 92
    chords = [("C3 E3 G3 B3", "C4 E4 G4 B4"), ("A2 C3 E3 G3", "A3 C4 E4 G4"),
              ("F2 A2 C3 E3", "F3 A3 C4 E4"), ("G2 B2 D3 F3", "G3 B3 D4 F4")]
    melody = ["E5 G5", "E5 C5", "F5 A5", "G5 B5",
              "E5 G5", "A5 G5", "F5 E5", "D5 E5", "C5 C5"]
    n_bars = 9
    total = int((n_bars * 4 * beat + 1.5) * SR)
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
            place(bell(freq(name) / 2, 1.1, 0.16), t0 + j * beat / 2)
        for j, name in enumerate(melody[bar].split()):
            place(bell(freq(name), 1.6, 0.34), t0 + j * 2 * beat)
        for j in range(8):                            # sleigh bells, offbeats
            burst = rng.standard_normal(int(0.03 * SR))
            burst *= np.exp(-np.arange(len(burst)) / (0.006 * SR))
            place(0.05 * burst, t0 + (j + 0.5) * beat / 2)
    place(bell(freq("C5"), 3.5, 0.4), n_bars * 4 * beat - beat)

    rng2 = np.random.default_rng(11)                  # finale sparkle
    spark_notes = ["C6", "D6", "E6", "G6", "A6"]
    for j in range(15):
        name = spark_notes[int(rng2.integers(0, 5))]
        place(bell(freq(name), 0.8, 0.1), 16.5 + j * 0.36)
    for t0 in (17.7, 18.5, 19.3, 20.1, 20.9, 21.7):   # firework booms
        n2 = int(0.6 * SR)
        tt = np.arange(n2) / SR
        place(0.3 * np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 6), t0)

    mix = np.tanh(mix * 1.2)
    n = len(mix)
    fi, fo = int(0.3 * SR), int(2.0 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix /= max(1e-9, np.abs(mix).max()) * 1.02
    pcm = (mix * 32767).astype(np.int16)
    with wave.open("music.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"music.wav {n / SR:.2f}s")


# --- v4: time-lapse typing of the real source -------------------------------
def terminal_image_v4(t):
    img = np.full((ROWS * CH, COLS * CW, 3), BG, dtype=np.uint8)
    rows, colors = V4.frame(t)
    for r in range(ROWS):
        row_ch, row_col = rows[r], colors[r]
        for c in range(COLS):
            col = row_col[c]
            if col is not None:
                img[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW] = glyph(row_ch[c], col)
    return img


def panel_typed_v4(t):
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


def render_frame_v4(i):
    t = i / FPS
    full = np.full((H_PX, W_PX, 3), BG, dtype=np.uint8)
    full[TY:TY + ROWS * CH, TX:TX + COLS * CW] = terminal_image_v4(t)
    im = Image.fromarray(full)
    im.paste(panel_typed_v4(t), (0, CODE_Y))
    d = ImageDraw.Draw(im)
    d.rectangle([0, BAR_Y0, W_PX, BAR_Y1], fill=(22, 27, 34))
    d.rounded_rectangle([24, BAR_Y0 + 8, 252, BAR_Y1 - 8], radius=6,
                        fill=(13, 17, 23), outline=(45, 52, 62))
    d.text((42, BAR_Y0 + 13), "* winter_scene.py", font=FONT_BAR,
           fill=(230, 237, 243))
    if t > V4.TL:
        d.text((W_PX - 26, BAR_Y0 + 13), "● running · 30 fps", font=FONT_BAR,
               fill=(255, 123, 114), anchor="ra")
    else:
        d.text((W_PX - 26, BAR_Y0 + 13), "○ typing · fast-forward",
               font=FONT_BAR, fill=(139, 148, 158), anchor="ra")
    d.line([0, BAR_Y0, W_PX, BAR_Y0], fill=(45, 52, 62))
    return im


def cmd_frames_v4(a, b):
    os.makedirs("frames_v4", exist_ok=True)
    for i in range(a, b):
        render_frame_v4(i).save(f"frames_v4/{i:04d}.png", compress_level=1)
        if i % 60 == 0:
            print(f"frame {i}", flush=True)


def cmd_audio_v4():
    beat = 60 / 92
    chords = [("C3 E3 G3 B3", "C4 E4 G4 B4"), ("A2 C3 E3 G3", "A3 C4 E4 G4"),
              ("F2 A2 C3 E3", "F3 A3 C4 E4"), ("G2 B2 D3 F3", "G3 B3 D4 F4")]
    melody = ["E5 G5", "E5 C5", "F5 A5", "G5 B5",
              "E5 G5", "A5 G5", "F5 E5", "D5 E5", "C5 C5",
              "E5 G5", "E5 C5", "F5 A5", "G5 B5"]
    n_bars = 13
    total = int((V4.DUR + 1.0) * SR)
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
            place(bell(freq(name) / 2, 1.1, 0.16), t0 + j * beat / 2)
        for j, name in enumerate(melody[bar].split()):
            place(bell(freq(name), 1.6, 0.34), t0 + j * 2 * beat)
        for j in range(8):
            burst = rng.standard_normal(int(0.03 * SR))
            burst *= np.exp(-np.arange(len(burst)) / (0.006 * SR))
            place(0.05 * burst, t0 + (j + 0.5) * beat / 2)

    rng2 = np.random.default_rng(11)                  # finale sparkle
    spark_notes = ["C6", "D6", "E6", "G6", "A6"]
    for j in range(20):
        name = spark_notes[int(rng2.integers(0, 5))]
        place(bell(freq(name), 0.8, 0.1), V4.MSG_T0 + 0.5 + j * 0.45)
    for j in range(V4.N_BURSTS):                      # firework booms
        t0 = V4.BURST0 + j * V4.BURST_STEP + 1.1
        n2 = int(0.6 * SR)
        tt = np.arange(n2) / SR
        place(0.3 * np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 6), t0)
    place(bell(freq("C5"), 3.5, 0.4), V4.DUR - 1.2)

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


# --- v5: cold-open hook on the finished scene, then the build ---------------
HOOK_DUR = 2.5          # seconds of finished-scene cold open
HOOK_T0 = 25.8          # v4 timeline moment the hook plays from (fireworks)
V5_DUR = HOOK_DUR + V4.DUR


def render_frame_v5(i):
    g = i / FPS
    if g < HOOK_DUR:
        t_scene = HOOK_T0 + g
        t_panel = V4.TYPING_END + 1.0     # fully typed file
    else:
        t_scene = t_panel = g - HOOK_DUR
    full = np.full((H_PX, W_PX, 3), BG, dtype=np.uint8)
    full[TY:TY + ROWS * CH, TX:TX + COLS * CW] = terminal_image_v4(t_scene)
    im = Image.fromarray(full)
    im.paste(panel_typed_v4(t_panel), (0, CODE_Y))
    d = ImageDraw.Draw(im)
    d.rectangle([0, BAR_Y0, W_PX, BAR_Y1], fill=(22, 27, 34))
    d.rounded_rectangle([24, BAR_Y0 + 8, 252, BAR_Y1 - 8], radius=6,
                        fill=(13, 17, 23), outline=(45, 52, 62))
    d.text((42, BAR_Y0 + 13), "* winter_scene.py", font=FONT_BAR,
           fill=(230, 237, 243))
    if g < HOOK_DUR or t_scene > V4.TL:
        d.text((W_PX - 26, BAR_Y0 + 13), "● running · 30 fps", font=FONT_BAR,
               fill=(255, 123, 114), anchor="ra")
    else:
        d.text((W_PX - 26, BAR_Y0 + 13), "○ typing · fast-forward",
               font=FONT_BAR, fill=(139, 148, 158), anchor="ra")
    d.line([0, BAR_Y0, W_PX, BAR_Y0], fill=(45, 52, 62))
    return im


def cmd_frames_v5(a, b):
    os.makedirs("frames_v5", exist_ok=True)
    for i in range(a, b):
        render_frame_v5(i).save(f"frames_v5/{i:04d}.png", compress_level=1)
        if i % 60 == 0:
            print(f"frame {i}", flush=True)


def cmd_audio_v5():
    with wave.open("music_v4.wav", "rb") as w:
        sr = w.getframerate()
        raw = w.readframes(w.getnframes())
    src = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    hook = src[int(HOOK_T0 * sr):int((HOOK_T0 + HOOK_DUR) * sr)]
    xf = int(0.05 * sr)
    out = np.zeros(len(hook) + len(src) - xf, dtype=np.float32)
    out[:len(hook) - xf] = hook[:-xf]
    ramp = np.linspace(0, 1, xf)
    out[len(hook) - xf:len(hook)] = hook[-xf:] * (1 - ramp) + src[:xf] * ramp
    out[len(hook):] = src[xf:]
    pcm = np.clip(out, -32767, 32767).astype(np.int16)
    with wave.open("music_v5.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"music_v5.wav {len(pcm) / sr:.2f}s")


if __name__ == "__main__":
    if sys.argv[1] == "frames":
        cmd_frames(int(sys.argv[2]), int(sys.argv[3]))
    elif sys.argv[1] == "v3frames":
        cmd_frames_v3(int(sys.argv[2]), int(sys.argv[3]))
    elif sys.argv[1] == "v4frames":
        cmd_frames_v4(int(sys.argv[2]), int(sys.argv[3]))
    elif sys.argv[1] == "v5frames":
        cmd_frames_v5(int(sys.argv[2]), int(sys.argv[3]))
    elif sys.argv[1] == "audio":
        cmd_audio()
    elif sys.argv[1] == "v3audio":
        cmd_audio_v3()
    elif sys.argv[1] == "v4audio":
        cmd_audio_v4()
    elif sys.argv[1] == "v5audio":
        cmd_audio_v5()
    elif sys.argv[1] == "panel":
        render_panel_source()[0].save("panel_src.png")
