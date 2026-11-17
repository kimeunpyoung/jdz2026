#!/usr/bin/env python3
"""혜성금속 전면간판 B안: 검정 바탕 + 사선 메탈 띠 + 원형/각 파이프 더미.

사용법:  python3 make_signs_B.py <폰트폴더> <출력폴더>
"""
import math
import random

from reportlab.lib.colors import HexColor

import make_signs as M
from make_signs import GOT, HAN, grad, poly, text

BG_TOP, BG_BOT = HexColor("#0b1226"), HexColor("#02040a")
SILVER = [(0.0, "#ffffff"), (0.45, "#e9edf1"), (0.55, "#b9c2ca"), (1.0, "#f4f6f8")]
BAND_METAL = [(0.0, "#2a2f38"), (0.18, "#8c949d"), (0.36, "#f2f4f6"), (0.5, "#a9b0b8"),
              (0.66, "#4a5059"), (0.82, "#d5d9de"), (1.0, "#6b727b")]
BAND_STEEL = [(0.0, "#1a1f29"), (0.3, "#6d7580"), (0.5, "#c9ced4"), (0.72, "#565d67"), (1.0, "#20252e")]
BAND_NAVY = [(0.0, "#0c1430"), (0.5, "#1c2a55"), (1.0, "#0a1024")]
BAND_DIM = [(0.0, "#070b18"), (0.5, "#111a36"), (1.0, "#070b18")]
TAN = math.tan(math.radians(38))


def band(c, xb, w, stops, y0=0.0, y1=1000.0):
    """바닥(y=0) 기준 xb에서 출발해 38도로 올라가는 폭 w의 사선 띠. y0~y1 구간만 그린다."""
    f = lambda y: xb + y / TAN
    pts = [(f(y0), y0), (f(y0) + w, y0), (f(y1) + w, y1), (f(y1), y1)]
    grad(c, poly(c, pts), pts[0], pts[3], stops)


def text_grad(c, font, s, box, stops, shadow=0.0, anchor="c"):
    """글자를 위→아래 은색 그라데이션으로 채운다."""
    x, y, w, h = box
    items, (bx0, by0, bx1, by1) = font.layout(s)
    k = min(h / (by1 - by0), w / (bx1 - bx0))
    iw, ih = (bx1 - bx0) * k, (by1 - by0) * k
    tx = {"l": x, "c": x + (w - iw) / 2, "r": x + w - iw}[anchor]
    ty = y + (h - ih) / 2
    for dx, col in ((shadow, HexColor("#000000")), (0, None)):
        if col is None or shadow:
            c.saveState()
            c.translate(tx + dx - bx0 * k, ty - dx - by0 * k)
            c.scale(k, k)
            p = c.beginPath()
            for g, gx in items:
                font.gs[g].draw(M.PathPen(font.gs, p, gx))
            if col is not None:
                c.setFillColor(col)
                c.drawPath(p, stroke=0, fill=1, fillMode=M.NONZERO)
            else:
                grad(c, p, (0, by1), (0, by0), stops)
            c.restoreState()
    return tx, ty, tx + iw, ty + ih


def pile(c, x0, x1, floor, peak, sizes, d, seed):
    """x0~x1 폭, 높이 peak 의 둔덕 모양으로 크고 작은 원형/각 파이프 단면을 빽빽하게 쌓는다."""
    rnd = random.Random(seed)
    xc, hw = (x0 + x1) / 2, (x1 - x0) / 2
    top = lambda x: floor + (peak - floor) * max(0.0, 1 - ((x - xc) / hw) ** 2) ** 0.55
    placed = []  # (kind, cx, cy, r)
    for r in sizes:
        while True:
            best = None
            for _ in range(500):
                cx = rnd.uniform(x0 + r, x1 - r)
                cy = rnd.uniform(floor + r, peak - r)
                if best and cy >= best[1]:
                    continue
                if cy + r > top(cx):
                    continue
                if all(math.hypot(cx - q[1], cy - q[2]) >= r + q[3] + r * 0.05 for q in placed):
                    best = (cx, cy)
            if not best:
                break
            kind = "s" if (r >= 45 and rnd.random() < 0.28) else "r"
            placed.append((kind, best[0], best[1], r))
    L = math.hypot(*d)
    placed.sort(key=lambda q: (q[1] * d[0] + q[2] * d[1]) / L)
    for kind, cx, cy, r in placed:
        if kind == "r":
            M.round_body(c, cx, cy, r, d)
        else:
            M.square_body(c, cx, cy, r * 0.72, r * 0.72, d)
    for kind, cx, cy, r in placed:
        if kind == "r":
            M.round_face(c, cx, cy, r, r * 0.14)
        else:
            M.square_face(c, cx, cy, r * 0.72, r * 0.72, r * 0.11)
    return len(placed)


def bg(c, W, H):
    c.saveState()
    c.linearGradient(0, H, 0, 0, [BG_TOP, BG_BOT], extend=True)
    c.restoreState()


# ---- 전면간판 큰 것 6000 x 1000 (B안) -------------------------------------
def front_big_b(c, W, H):
    bg(c, W, H)
    for xb, w in ((-700, 420), (350, 180), (1500, 520), (2550, 140)):   # 글자 뒤 은은한 띠
        band(c, xb, w, BAND_DIM)
    band(c, 3180, 330, BAND_NAVY)
    band(c, 3560, 90, BAND_STEEL, 0, 620)
    band(c, 3700, 260, BAND_METAL)
    band(c, 4020, 60, BAND_STEEL, 300, 1000)
    band(c, 4150, 420, BAND_NAVY)
    band(c, 4620, 200, BAND_METAL, 150, 1000)
    band(c, 4900, 110, BAND_STEEL)
    band(c, 5100, 520, BAND_METAL)
    band(c, 5700, 300, BAND_NAVY)

    n = pile(c, 4330, 5780, 45, 800, [150, 135, 120, 105, 90, 78, 66, 55, 45, 36, 28], (1700, 300), seed=7)
    print("pipes:", n)

    x0, x1 = 230, 3930
    cell = (x1 - x0) / 4
    for i, ch in enumerate("혜성금속"):
        text_grad(c, HAN, ch, (x0 + cell * i, 330, cell, 580), SILVER, shadow=12)
    c.setFillColor(M.YELLOW)
    c.rect(x0 + 60, 262, x1 - x0 - 330, 9, stroke=0, fill=1)
    y, h = 62, 150
    left = text(c, GOT, "절단가공", (x0 + 60, y, 700, h), M.YELLOW, anchor="l", max_h=140)
    fax = text(c, GOT, "FAX. 02-953-2122", (x1 - 1620, y, 1200, h), M.WHITE, anchor="r", max_h=118)
    text(c, GOT, "TEL. 02-953-2110", (left[2], y, fax[0] - left[2], h), M.WHITE, max_h=118)


# ---- 전면간판 작은 것 3000 x 1000 (B안) ------------------------------------
def front_small_b(c, W, H):
    bg(c, W, H)
    for xb, w in ((-600, 380), (300, 150), (900, 420)):
        band(c, xb, w, BAND_DIM)
    band(c, 1380, 250, BAND_NAVY)
    band(c, 1680, 70, BAND_STEEL, 0, 560)
    band(c, 1800, 200, BAND_METAL)
    band(c, 2060, 330, BAND_NAVY)
    band(c, 2430, 130, BAND_STEEL, 200, 1000)
    band(c, 2600, 380, BAND_METAL)

    n = pile(c, 2030, 2930, 45, 640, [118, 104, 90, 76, 64, 53, 43, 34, 26], (1100, 230), seed=12)
    print("pipes:", n)

    x, w = 130, 1790
    text(c, HAN, "절단가공 전문", (x, 655, w, 245), M.YELLOW, anchor="l", shadow=7, max_h=245)
    c.setFillColor(HexColor("#c9d1d8"))
    c.rect(x, 590, 1560, 9, stroke=0, fill=1)
    text(c, GOT, "스텐판 / 각파이프 / 파이프 / 배관", (x, 370, w, 150), M.WHITE, anchor="l", max_h=150)
    text(c, GOT, "앵글 / 평철 / 환봉 / 각종부속", (x, 130, w, 150), M.WHITE, anchor="l", max_h=150)


M.make("B안_1_전면간판_큰것", 6000, 1000, front_big_b)
M.make("B안_2_전면간판_작은것", 3000, 1000, front_small_b)
