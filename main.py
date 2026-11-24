#!/usr/bin/env python3
"""news-image-20261124 — sum up 24 November 2026 world news in one image.

Draws a 1024x1024 editorial front page in pure Python stdlib (zlib-based
PNG writer, no PIL, no network, no external files) and writes it to
<MAKEFUN_OUTPUT_DIR or /output>/entry.png. Fully deterministic: fixed
palette, fixed layout, no randomness, no timestamps — two runs produce
byte-identical output.

Stories covered (24 November 2026):
  COP31 collapse, Indonesia factory fire, Kyiv strikes, Nvidia CEO return,
  World Chess Championship, Alcaraz ATP Finals win, warship sunk off Libya,
  ICJ Rohingya genocide ruling.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
INK = (16, 24, 40)          # near-black navy
PAPER = (250, 246, 238)      # warm newsprint
NAVY = (13, 42, 84)         # header band
NAVY_LT = (28, 68, 128)
WHITE = (255, 255, 255)
RED = (198, 40, 32)
RED_LT = (232, 90, 70)
ORANGE = (232, 116, 24)
YELLOW = (244, 196, 48)
GREEN = (34, 139, 84)
GREEN_LT = (76, 175, 110)
TEAL = (18, 130, 130)
BLUE = (52, 120, 198)
BLUE_LT = (120, 178, 232)
SKY = (178, 216, 244)
GREY = (120, 124, 132)
GREY_DK = (74, 78, 88)
GREY_LT = (214, 216, 222)
BROWN = (122, 82, 42)
GOLD = (212, 160, 32)

# ---------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = c


def rect(x, y, w, h, c):
    for yy in range(y, y + h):
        base = (yy * W + x) * 3
        for xx in range(w):
            i = base + xx * 3
            buf[i], buf[i + 1], buf[i + 2] = c


def border(x, y, w, h, c, t=3):
    rect(x, y, w, t, c)
    rect(x, y + h - t, w, t, c)
    rect(x, y, t, h, c)
    rect(x + w - t, y, t, h, c)


def line(x0, y0, x1, y1, c):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        px(x0, y0, c)
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def circle(cx, cy, r, c, fill=True):
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            d = (xx - cx) ** 2 + (yy - cy) ** 2
            if fill:
                if d <= r * r:
                    px(xx, yy, c)
            else:
                if r * r - 2 * r <= d <= r * r:
                    px(xx, yy, c)


def ellipse(cx, cy, rx, ry, c):
    for yy in range(cy - ry, cy + ry + 1):
        for xx in range(cx - rx, cx + rx + 1):
            if ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0:
                px(xx, yy, c)


def triangle(x0, y0, x1, y1, x2, y2, c):
    # simple scanline fill
    min_y, max_y = min(y0, y1, y2), max(y0, y1, y2)
    for yy in range(min_y, max_y + 1):
        xs = []
        for (ax, ay), (bx, by) in (((x0, y0), (x1, y1)),
                                   ((x1, y1), (x2, y2)),
                                   ((x2, y2), (x0, y0))):
            if ay == by:
                continue
            if min(ay, by) <= yy <= max(ay, by):
                t = (yy - ay) / (by - ay)
                xs.append(ax + t * (bx - ax))
        if len(xs) >= 2:
            for xx in range(int(min(xs)), int(max(xs)) + 1):
                px(xx, yy, c)


# ------------------------------------------------------------- bitmap font
# 5x7 glyphs, each row a 5-bit integer (bit 4 = leftmost pixel).
def _g(*rows):
    return rows


FONT = {
    'A': _g(0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    'B': _g(0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    'C': _g(0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    'D': _g(0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    'E': _g(0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    'F': _g(0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    'G': _g(0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111),
    'H': _g(0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    'I': _g(0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    'J': _g(0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    'K': _g(0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    'L': _g(0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    'M': _g(0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    'N': _g(0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    'O': _g(0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    'P': _g(0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    'Q': _g(0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    'R': _g(0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    'S': _g(0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    'T': _g(0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    'U': _g(0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    'V': _g(0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    'W': _g(0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001),
    'X': _g(0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    'Y': _g(0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    'Z': _g(0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    '0': _g(0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    '1': _g(0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    '2': _g(0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111),
    '3': _g(0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110),
    '4': _g(0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    '5': _g(0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    '6': _g(0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    '7': _g(0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    '8': _g(0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    '9': _g(0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100),
    ' ': _g(0, 0, 0, 0, 0, 0, 0),
    '.': _g(0, 0, 0, 0, 0, 0b01100, 0b01100),
    ',': _g(0, 0, 0, 0, 0b01100, 0b00100, 0b01000),
    ':': _g(0, 0b01100, 0b01100, 0, 0b01100, 0b01100, 0),
    '-': _g(0, 0, 0, 0b01110, 0, 0, 0),
    '+': _g(0, 0b00100, 0b00100, 0b01110, 0b00100, 0b00100, 0),
    '%': _g(0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011),
    "'": _g(0b00100, 0b00100, 0b01000, 0, 0, 0, 0),
    '!': _g(0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0, 0b00100),
    '/': _g(0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000),
    '=': _g(0, 0, 0b01110, 0, 0b01110, 0, 0),
    '?': _g(0b01110, 0b10001, 0b00001, 0b00110, 0b00100, 0, 0b00100),
}


def text(x, y, s, scale, c):
    """Draw uppercase text; scale = pixel size multiplier."""
    s = s.upper()
    cx = x
    for ch in s:
        glyph = FONT.get(ch, FONT[' '])
        for row, bits in enumerate(glyph):
            for col in range(5):
                if bits & (1 << (4 - col)):
                    rect(cx + col * scale, y + row * scale, scale, scale, c)
        cx += 6 * scale


def text_w(s, scale):
    return len(s) * 6 * scale - scale


def text_center(cx, y, s, scale, c):
    text(cx - text_w(s, scale) // 2, y, s, scale, c)


# ---------------------------------------------------------------- panels
def panel(x, y, w, h, bg, headline, accent):
    rect(x, y, w, h, bg)
    border(x, y, w, h, INK, 3)
    rect(x, y, w, 34, accent)
    text(x + 10, y + 10, headline, 2, WHITE)


# ---------------------------------------------------------------- drawing
def draw_globe(cx, cy, r):
    circle(cx, cy, r, BLUE)
    circle(cx, cy, r, BLUE_LT, fill=False)
    # continents (stylised blobs)
    ellipse(cx - 38, cy - 42, 34, 22, GREEN)
    ellipse(cx + 42, cy - 30, 26, 18, GREEN)
    ellipse(cx - 18, cy + 38, 40, 20, GREEN_LT)
    ellipse(cx + 52, cy + 44, 20, 14, GREEN)
    ellipse(cx + 6, cy - 66, 22, 12, GREEN_LT)
    # latitude lines
    for dy, half in ((-r // 2, int(r * 0.86)), (0, r), (r // 2, int(r * 0.86))):
        for xx in range(cx - half, cx + half + 1):
            px(xx, cy + dy, BLUE_LT)
    # crack through the globe (COP31: a deal broken)
    pts = [(cx - 70, cy - 88), (cx - 30, cy - 44), (cx - 52, cy - 6),
           (cx - 8, cy + 30), (cx - 34, cy + 66), (cx + 4, cy + 92)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        line(ax, ay, bx, by, WHITE)
        line(ax + 1, ay, bx + 1, by, WHITE)


def draw_chairs(x, y, n, gap):
    """Row of empty chairs: seat + backrest, nobody sitting."""
    for i in range(n):
        cx = x + i * gap
        rect(cx, y + 26, 44, 8, BROWN)          # seat
        rect(cx, y, 8, 30, BROWN)              # backrest post
        rect(cx, y, 44, 8, BROWN)              # backrest top
        rect(cx + 4, y + 34, 6, 26, BROWN)     # legs
        rect(cx + 34, y + 34, 6, 26, BROWN)
        # small "empty" marker: a question mark dot above each chair
        circle(cx + 22, y - 16, 4, RED)


def draw_flames(x, y, w, h):
    # smoke, kept low so it never covers the sub-headline above
    for (sx, sy, sr) in ((x + 60, y + 34, 20), (x + 130, y + 26, 24),
                         (x + 200, y + 36, 18), (x + 258, y + 30, 20)):
        circle(sx, sy, sr, GREY)
        circle(sx + 6, sy + 5, sr - 7, GREY_DK)
    # factory block
    rect(x + 20, y + 90, w - 40, h - 100, GREY_DK)
    rect(x + 40, y + 60, 18, 40, GREY_DK)      # chimney
    rect(x + 230, y + 60, 18, 40, GREY_DK)
    # flames
    for (fx, fw, fh) in ((x + 60, 46, 90), (x + 130, 60, 110), (x + 210, 46, 84)):
        triangle(fx, y + h - 10, fx + fw // 2, y + h - 10 - fh,
                 fx + fw, y + h - 10, ORANGE)
        triangle(fx + 10, y + h - 10, fx + fw // 2, y + h - 10 - fh + 34,
                 fx + fw - 10, y + h - 10, YELLOW)


def draw_kyiv(x, y, w, h):
    rect(x, y, w, h, NAVY)
    # skyline
    for (bx, bw, bh) in ((10, 46, 90), (66, 36, 120), (112, 52, 76),
                         (174, 40, 110), (224, 48, 66), (282, 30, 96)):
        rect(x + bx, y + h - 10 - bh, bw, bh, INK)
        for wy in range(y + h - bh, y + h - 16, 18):
            for wx in range(x + bx + 8, x + bx + bw - 8, 14):
                rect(wx, wy, 5, 7, YELLOW)
    # explosions: starbursts in the sky
    for (ex, ey) in ((x + 60, y + 34), (x + 190, y + 22), (x + 270, y + 44)):
        circle(ex, ey, 12, YELLOW)
        for ang in range(0, 360, 45):
            dx = int(20 * math.cos(math.radians(ang)))
            dy = int(20 * math.sin(math.radians(ang)))
            line(ex, ey, ex + dx, ey + dy, ORANGE)


def draw_chip(x, y, w, h):
    rect(x, y, w, h, (10, 40, 28))
    # chip
    cx, cy = x + w // 2 - 30, y + 78
    rect(cx - 14, cy - 14, 88, 88, GREEN)
    rect(cx, cy, 60, 60, (8, 90, 50))
    rect(cx + 16, cy + 16, 28, 28, GREEN_LT)
    for i in range(5):  # pins
        rect(cx - 14 + i * 18, cy - 26, 8, 12, GOLD)
        rect(cx - 14 + i * 18, cy + 74, 8, 12, GOLD)
        rect(cx - 26, cy - 14 + i * 18, 12, 8, GOLD)
        rect(cx + 74, cy - 14 + i * 18, 12, 8, GOLD)
    # rising arrow
    pts = [(x + 20, y + 150), (x + 60, y + 110), (x + 95, y + 128),
           (x + 150, y + 70)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        line(ax, ay, bx, by, YELLOW)
        line(ax, ay + 2, bx, by + 2, YELLOW)
    triangle(x + 150, y + 70, x + 132, y + 72, x + 148, y + 92, YELLOW)
    text(x + w - 108, y + 34, "+31%", 4, YELLOW)


def draw_chess(x, y, w, h):
    """Board sized to fit the panel body; crown + GENEVA label at right."""
    rect(x, y, w, h, PAPER)
    bx, by, sq = x + 16, y + 6, 19
    for r in range(8):
        for c in range(8):
            col = WHITE if (r + c) % 2 == 0 else INK
            rect(bx + c * sq, by + r * sq, sq, sq, col)
    border(bx, by, 8 * sq, 8 * sq, INK, 2)
    # small crown at the right of the board
    cx = x + w - 62
    triangle(cx - 26, by + 44, cx - 26, by + 18, cx - 9, by + 32, GOLD)
    triangle(cx - 9, by + 32, cx, by + 10, cx + 9, by + 32, GOLD)
    triangle(cx + 9, by + 32, cx + 26, by + 18, cx + 26, by + 44, GOLD)
    rect(cx - 26, by + 42, 52, 7, GOLD)
    text(cx - 30, by + 66, "GENEVA", 2, INK)
    text(cx - 30, by + 86, "2026", 2, INK)


def draw_trophy(x, y, w, h):
    """Compact trophy sized to fit the panel body (~120px tall)."""
    rect(x, y, w, h, (24, 60, 96))
    cx = x + w // 2
    # cup
    triangle(cx - 44, y + 14, cx + 44, y + 14, cx, y + 78, GOLD)
    rect(cx - 48, y + 6, 96, 12, GOLD)
    rect(cx - 56, y + 16, 12, 26, GOLD)        # handles
    rect(cx + 44, y + 16, 12, 26, GOLD)
    rect(cx - 7, y + 78, 14, 26, GOLD)         # stem
    rect(cx - 28, y + 104, 56, 10, GOLD)       # base
    # tennis ball
    circle(x + 46, y + 92, 17, YELLOW)
    circle(x + 46, y + 92, 17, WHITE, fill=False)
    # confetti
    for (fx, fy, fc) in ((x + 26, y + 16, RED), (x + w - 36, y + 30, WHITE),
                         (x + 40, y + 60, YELLOW), (x + w - 52, y + 78, RED),
                         (x + 84, y + 96, WHITE)):
        rect(fx, fy, 7, 7, fc)


def draw_ship(x, y, w, h):
    rect(x, y, w, h, (14, 66, 110))
    # sea
    for i in range(6):
        line(x + 8 + i * 52, y + h - 46, x + 34 + i * 52, y + h - 46, SKY)
        line(x + 20 + i * 52, y + h - 30, x + 46 + i * 52, y + h - 30, SKY)
    # sinking ship: filled hull trapezoid (bow-down tilt) + deck line
    triangle(x + 60, y + 96, x + 240, y + 96, x + 210, y + 132, GREY_LT)
    triangle(x + 60, y + 96, x + 210, y + 132, x + 90, y + 132, GREY_LT)
    line(x + 60, y + 96, x + 240, y + 96, WHITE)
    line(x + 240, y + 96, x + 210, y + 132, WHITE)
    line(x + 210, y + 132, x + 90, y + 132, WHITE)
    line(x + 90, y + 132, x + 60, y + 96, WHITE)
    rect(x + 150, y + 52, 12, 46, WHITE)       # mast
    triangle(x + 162, y + 56, x + 162, y + 88, x + 196, y + 88, RED)  # flag
    # smoke plume
    for (sx, sy, sr) in ((x + 120, y + 40, 14), (x + 140, y + 26, 18),
                         (x + 164, y + 14, 12)):
        circle(sx, sy, sr, GREY)


# ---------------------------------------------------------------- compose
def compose():
    rect(0, 0, W, H, PAPER)

    # ---- header band
    rect(0, 0, W, 96, NAVY)
    rect(0, 92, W, 4, RED)
    text_center(W // 2, 16, "24 NOVEMBER 2026", 6, WHITE)
    text_center(W // 2, 66, "THE WORLD IN ONE IMAGE", 2, YELLOW)

    # ---- row 1: globe + COP31
    y1, h1 = 108, 300
    rect(16, y1, 344, h1, NAVY_LT)
    border(16, y1, 344, h1, INK, 3)
    text_center(188, y1 + 12, "ONE DAY ON EARTH", 2, WHITE)
    draw_globe(188, y1 + 170, 108)
    text_center(188, y1 + 268, "8 STORIES. 1 DAY.", 2, YELLOW)

    panel(376, y1, 632, h1, (226, 240, 228), "COP31 TALKS COLLAPSE", GREEN)
    text(392, y1 + 52, "NO DEAL ON FOSSIL", 3, INK)
    text(392, y1 + 86, "FUEL PHASE-OUT", 3, INK)
    draw_chairs(420, y1 + 170, 5, 108)
    text(392, y1 + 258, "EMPTY CHAIRS. NO DEAL.", 2, RED)

    # ---- row 2: fire / Kyiv / Nvidia
    y2, h2 = 420, 272
    pw = 322
    panel(16, y2, pw, h2, (253, 238, 222), "FACTORY FIRE", ORANGE)
    text(28, y2 + 46, "24 DEAD, 30 MISSING", 2, INK)
    draw_flames(28, y2 + 74, pw - 24, h2 - 86)

    panel(352, y2, pw, h2, (226, 232, 244), "KYIV UNDER ATTACK", RED)
    text(364, y2 + 46, "DRONES AND MISSILES", 2, INK)
    draw_kyiv(364, y2 + 74, pw - 24, h2 - 86)

    panel(688, y2, 320, h2, (222, 240, 226), "HUANG BACK AT NVIDIA", GREEN)
    text(700, y2 + 46, "CEO RETURNS", 2, INK)
    draw_chip(700, y2 + 74, 320 - 24, h2 - 86)

    # ---- row 3: chess / tennis / warship
    y3, h3 = 704, 204
    panel(16, y3, pw, h3, PAPER, "CHESS: GUKESH DEFENDS", NAVY)
    draw_chess(28, y3 + 44, pw - 24, h3 - 56)

    panel(352, y3, pw, h3, (238, 232, 244), "ALCARAZ WINS", GOLD)
    text(364, y3 + 46, "MAIDEN ATP FINALS TITLE", 2, INK)
    draw_trophy(364, y3 + 70, pw - 24, h3 - 82)

    panel(688, y3, 320, h3, (222, 234, 244), "WARSHIP SUNK", TEAL)
    text(700, y3 + 46, "OFF THE COAST OF LIBYA", 2, INK)
    draw_ship(700, y3 + 70, 320 - 24, h3 - 82)

    # ---- footer ticker: ICJ ruling
    rect(0, 920, W, 104, INK)
    rect(0, 920, W, 4, RED)
    text(24, 940, "ICJ: MYANMAR COMMITTED GENOCIDE", 3, WHITE)
    text(24, 978, "AGAINST THE ROHINGYA, TOP UN COURT RULES", 2, YELLOW)


# ---------------------------------------------------------------- PNG out
def chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = bytearray()
    for yy in range(H):
        raw.append(0)  # filter: none
        raw += buf[yy * W * 3:(yy + 1) * W * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    compose()
    path = os.path.join(out_dir, "entry.png")
    n = write_png(path)
    print(f"wrote {path}: {W}x{H}, {n} bytes")


if __name__ == "__main__":
    main()
