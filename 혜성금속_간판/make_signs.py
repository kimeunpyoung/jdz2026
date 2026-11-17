#!/usr/bin/env python3
"""혜성금속 플렉스 간판 3종 생성 스크립트 (벡터 PDF, 글자는 모두 윤곽선 처리).

사용법:  python3 make_signs.py <폰트폴더> <출력폴더>
폰트폴더에는 BlackHanSans-Regular.ttf, GothicA1-Black.ttf 가 있어야 합니다(둘 다 OFL 무료 폰트).
단위는 전부 mm, 원점은 간판 좌측 하단입니다.
"""
import math
import sys
from pathlib import Path

from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

FONT_DIR = Path(sys.argv[1])
OUT_DIR = Path(sys.argv[2])
OUT_DIR.mkdir(parents=True, exist_ok=True)

NONZERO = 1

# ---- 색상 -------------------------------------------------------------
BLUE_TOP = HexColor("#1976d2")
BLUE_BOT = HexColor("#0a3a8c")
NAVY = HexColor("#06255e")
WHITE = HexColor("#ffffff")
YELLOW = HexColor("#ffd500")
SHADOW = HexColor("#041a45")
STEEL_LINE = HexColor("#2c343b")

# 스테인리스 광택(파이프 몸통 단면 방향 그라데이션)
METAL = [
    (0.00, "#4b555e"), (0.10, "#8d98a2"), (0.28, "#e9eef2"), (0.36, "#ffffff"),
    (0.48, "#c3ccd3"), (0.66, "#8a959f"), (0.84, "#b9c2ca"), (1.00, "#56606a"),
]
METAL_DARK = [
    (0.00, "#3d464e"), (0.25, "#7c8791"), (0.50, "#aab4bd"), (0.75, "#737e88"), (1.00, "#3a434b"),
]
FACE = [(0.0, "#f4f7f9"), (0.5, "#c9d1d8"), (1.0, "#8d98a2")]
HOLE = [(0.0, "#0e1318"), (0.6, "#2a333b"), (1.0, "#66717b")]


def grad(c, path, p0, p1, stops):
    """path 안쪽을 p0→p1 선형 그라데이션으로 채운다."""
    c.saveState()
    c.clipPath(path, stroke=0, fill=0, fillMode=NONZERO)
    c.linearGradient(p0[0], p0[1], p1[0], p1[1],
                     [HexColor(h) for _, h in stops], [t for t, _ in stops], extend=True)
    c.restoreState()


def poly(c, pts):
    p = c.beginPath()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    return p


# ---- 글자(윤곽선) --------------------------------------------------------
class PathPen(BasePen):
    def __init__(self, glyphset, path, ox):
        super().__init__(glyphset)
        self.p, self.ox = path, ox

    def _moveTo(self, pt):
        self.p.moveTo(pt[0] + self.ox, pt[1])

    def _lineTo(self, pt):
        self.p.lineTo(pt[0] + self.ox, pt[1])

    def _curveToOne(self, a, b, d):
        self.p.curveTo(a[0] + self.ox, a[1], b[0] + self.ox, b[1], d[0] + self.ox, d[1])

    def _closePath(self):
        self.p.close()


class Font:
    def __init__(self, filename):
        self.tt = TTFont(str(FONT_DIR / filename))
        self.gs = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap()
        self.upm = self.tt["head"].unitsPerEm

    def layout(self, text, tracking=0.0):
        """[(glyphname, x)] 와 잉크 영역(xmin, ymin, xmax, ymax)을 폰트 단위로 돌려준다."""
        x, items = 0.0, []
        bx0 = by0 = 1e18
        bx1 = by1 = -1e18
        for ch in text:
            g = self.cmap.get(ord(ch))
            if g is None:
                raise ValueError(f"폰트에 글자 없음: {ch!r}")
            bp = BoundsPen(self.gs)
            self.gs[g].draw(bp)
            if bp.bounds:
                bx0 = min(bx0, bp.bounds[0] + x); by0 = min(by0, bp.bounds[1])
                bx1 = max(bx1, bp.bounds[2] + x); by1 = max(by1, bp.bounds[3])
            items.append((g, x))
            x += self.gs[g].width + tracking * self.upm
        return items, (bx0, by0, bx1, by1)


def text(c, font, s, box, color, anchor="c", tracking=0.0, shadow=0.0, valign="m", max_h=None):
    """box=(x, y, w, h) 안에 잉크 높이를 h(또는 max_h)에 맞추고 폭이 넘치면 줄여서 넣는다.
    돌려주는 값: 실제 잉크 영역 (x0, y0, x1, y1) mm."""
    x, y, w, h = box
    items, (bx0, by0, bx1, by1) = font.layout(s, tracking)
    k = min((max_h or h) / (by1 - by0), w / (bx1 - bx0))
    iw, ih = (bx1 - bx0) * k, (by1 - by0) * k
    tx = {"l": x, "c": x + (w - iw) / 2, "r": x + w - iw}[anchor]
    ty = {"b": y, "m": y + (h - ih) / 2, "t": y + h - ih}[valign]

    def draw(dx, dy, col):
        c.saveState()
        c.translate(tx + dx - bx0 * k, ty + dy - by0 * k)
        c.scale(k, k)
        p = c.beginPath()
        for g, gx in items:
            font.gs[g].draw(PathPen(font.gs, p, gx))
        c.setFillColor(col)
        c.drawPath(p, stroke=0, fill=1, fillMode=NONZERO)
        c.restoreState()

    if shadow:
        draw(shadow, -shadow, SHADOW)
    draw(0, 0, color)
    return tx, ty, tx + iw, ty + ih


# ---- 파이프 일러스트 ------------------------------------------------------
def round_body(c, cx, cy, r, d):
    dx, dy = d
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    p = poly(c, [(cx + nx * r, cy + ny * r), (cx + dx + nx * r, cy + dy + ny * r),
                 (cx + dx - nx * r, cy + dy - ny * r), (cx - nx * r, cy - ny * r)])
    p.circle(cx + dx, cy + dy, r)
    # 광택은 위쪽이 밝게 오도록 법선 방향을 맞춘다
    if ny < 0:
        nx, ny = -nx, -ny
    grad(c, p, (cx + nx * r, cy + ny * r), (cx - nx * r, cy - ny * r), METAL)
    c.setStrokeColor(STEEL_LINE)
    c.setLineWidth(r * 0.03)
    for s in (1, -1):
        c.line(cx + s * nx * r, cy + s * ny * r, cx + dx + s * nx * r, cy + dy + s * ny * r)


def round_face(c, cx, cy, r, wall):
    p = c.beginPath(); p.circle(cx, cy, r)
    grad(c, p, (cx - r, cy + r), (cx + r, cy - r), FACE)
    ri = r - wall
    p = c.beginPath(); p.circle(cx, cy, ri)
    grad(c, p, (cx - ri, cy + ri), (cx + ri, cy - ri), HOLE)
    c.setStrokeColor(STEEL_LINE)
    c.setLineWidth(r * 0.035)
    c.circle(cx, cy, r, stroke=1, fill=0)
    c.setLineWidth(r * 0.02)
    c.circle(cx, cy, ri, stroke=1, fill=0)


TOP_FACE = [(0.0, "#f1f4f6"), (0.35, "#d3d9de"), (1.0, "#a3adb6")]
SIDE_FACE = [(0.0, "#7f8993"), (0.4, "#69737d"), (1.0, "#4c555e")]


def square_body(c, cx, cy, a, b, d):
    """a, b = 가로/세로 반폭. d = 몸통이 뒤로 뻗는 화면상 벡터(dy > 0).
    윗면과 옆면을 각각 평평한 면으로 칠해 꺾인 모서리가 또렷하게 보이게 한다."""
    dx, dy = d
    x0, x1, y0, y1 = cx - a, cx + a, cy - b, cy + b
    top = [(x0, y1), (x1, y1), (x1 + dx, y1 + dy), (x0 + dx, y1 + dy)]
    xs = x1 if dx > 0 else x0
    side = [(xs, y0), (xs, y1), (xs + dx, y1 + dy), (xs + dx, y0 + dy)]
    # 면마다 길이 방향으로만 살짝 어두워지는 평면 톤
    grad(c, poly(c, top), (x0, y1), (x0 + dx * 0.6, y1 + dy * 0.6), TOP_FACE)
    grad(c, poly(c, side), (xs, y0), (xs + dx * 0.6, y0 + dy * 0.6), SIDE_FACE)
    m = min(a, b)
    c.setLineJoin(2)  # 뾰족한 모서리에서 선이 삐져나오지 않게 베벨 처리
    c.setLineCap(0)
    c.setStrokeColor(STEEL_LINE)
    c.setLineWidth(m * 0.035)
    c.drawPath(poly(c, top), stroke=1, fill=0)
    c.drawPath(poly(c, side), stroke=1, fill=0)
    # 윗면과 옆면이 만나는 꺾인 모서리: 밝은 선으로 강조
    c.setStrokeColor(HexColor("#ffffff"))
    c.setLineWidth(m * 0.03)
    c.line(xs, y1, xs + dx, y1 + dy)


def square_face(c, cx, cy, a, b, wall):
    """단면은 직각 모서리로 그려 몸통 모서리와 정확히 맞춘다."""
    p = c.beginPath(); p.rect(cx - a, cy - b, 2 * a, 2 * b)
    grad(c, p, (cx - a, cy + b), (cx + a, cy - b), FACE)
    ai, bi = a - wall, b - wall
    p = c.beginPath(); p.rect(cx - ai, cy - bi, 2 * ai, 2 * bi)
    grad(c, p, (cx - ai, cy + bi), (cx + ai, cy - bi), HOLE)
    c.setLineJoin(0)
    c.setStrokeColor(STEEL_LINE)
    c.setLineWidth(min(a, b) * 0.035)
    c.rect(cx - a, cy - b, 2 * a, 2 * b, stroke=1, fill=0)
    c.setLineWidth(min(a, b) * 0.02)
    c.rect(cx - ai, cy - bi, 2 * ai, 2 * bi, stroke=1, fill=0)


def bundle(c, pipes, d):
    """pipes: ('r', cx, cy, r) 또는 ('s', cx, cy, a, b). 아래 줄부터 몸통을 그리고 단면을 나중에 올린다."""
    order = sorted(pipes, key=lambda p: (p[2], -p[1] if d[0] > 0 else p[1]))
    for p in order:
        if p[0] == "r":
            round_body(c, p[1], p[2], p[3], d)
        else:
            square_body(c, p[1], p[2], p[3], p[4], d)
    for p in order:
        if p[0] == "r":
            round_face(c, p[1], p[2], p[3], p[3] * 0.13)
        else:
            square_face(c, p[1], p[2], p[3], p[4], min(p[3], p[4]) * 0.15)


def round_pyramid(x, y, r, rows=(3, 2, 1), g=1.0):
    """x = 맨 아랫줄 왼쪽 끝, y = 바닥."""
    out = []
    n0 = rows[0]
    for i, n in enumerate(rows):
        cy = y + r + i * r * math.sqrt(3) * g
        start = x + r + (n0 - n) * r
        out += [("r", start + 2 * r * j, cy, r) for j in range(n)]
    return out


# ---- 공통 --------------------------------------------------------------
def background(c, W, H, band=0.0):
    c.saveState()
    p = c.beginPath(); p.rect(0, band, W, H - band)
    c.clipPath(p, stroke=0, fill=0)
    c.linearGradient(0, H, 0, band, [BLUE_TOP, BLUE_BOT], extend=True)
    c.restoreState()
    if band:
        c.setFillColor(NAVY)
        c.rect(0, 0, W, band, stroke=0, fill=1)
        c.setFillColor(YELLOW)
        c.rect(0, band, W, H * 0.012, stroke=0, fill=1)


def make(name, W, H, draw):
    """실사이즈(1:1)와 1/10 축소 두 가지 벡터 PDF를 만든다."""
    for suffix, k in (("실사이즈", 1.0), ("10분의1축소", 0.1)):
        path = OUT_DIR / f"{name}_{W}x{H}mm_{suffix}.pdf"
        c = canvas.Canvas(str(path), pagesize=(W * mm * k, H * mm * k), pageCompression=1)
        c.setTitle(f"혜성금속 {name} {W}x{H}mm ({suffix})")
        c.scale(mm * k, mm * k)
        p = c.beginPath(); p.rect(0, 0, W, H)
        c.clipPath(p, stroke=0, fill=0)
        draw(c, W, H)
        c.save()
        print("saved", path)


HAN = Font("BlackHanSans-Regular.ttf")
GOT = Font("GothicA1-Black.ttf")


# ---- 1. 전면간판 큰 것 6000 x 1000 --------------------------------------
def front_big(c, W, H):
    band = 250
    background(c, W, H, band)

    # 왼쪽: 원형 파이프 묶음 / 오른쪽: 각파이프 묶음 (간판 바깥쪽으로 뻗어 나감)
    r = 118
    bundle(c, round_pyramid(330, 55, r), d=(-1400, 430))
    a = 112
    xs = W - 330 - 6 * a
    sq = [("s", xs + a + 2 * a * j, 55 + a, a, a) for j in range(3)]
    sq += [("s", xs + 3 * a + 2 * a * j, 55 + 3 * a, a, a) for j in range(2)]
    sq += [("s", xs + 5 * a, 55 + 5 * a, a, a)]
    bundle(c, sq, d=(1400, 430))

    tx0, tx1 = 1190, W - 1190
    # 상호: 네 글자를 같은 간격으로 넓게 배치
    n, cell = 4, (tx1 - tx0) / 4
    for i, ch in enumerate("혜성금속"):
        text(c, HAN, ch, (tx0 + cell * i, band + 75, cell, H - band - 135), WHITE, shadow=11)
    # 하단: 절단가공 / TEL / FAX
    y, h = 52, 150
    left = text(c, GOT, "절단가공", (tx0, y, 760, h), YELLOW, anchor="l")
    fax = text(c, GOT, "FAX. 02-953-2122", (tx1 - 1300, y, 1300, h), WHITE, anchor="r", max_h=128)
    # TEL은 절단가공과 FAX 사이 정중앙
    text(c, GOT, "TEL. 02-953-2110", (left[2], y, fax[0] - left[2], h), WHITE, max_h=128)


# ---- 2. 전면간판 작은 것 3000 x 1000 -------------------------------------
def front_small(c, W, H):
    background(c, W, H)
    # 오른쪽: 각파이프 위에 원형 파이프를 얹은 묶음
    a, r = 105, 105
    xs = W - 150 - 6 * a
    y0 = 70
    pipes = [("s", xs + a + 2 * a * j, y0 + a, a, a) for j in range(3)]
    pipes += [("r", xs + 2 * a + 2 * r * j, y0 + 2 * a + r, r) for j in range(2)]
    pipes += [("r", xs + 3 * a, y0 + 2 * a + r + r * math.sqrt(3), r)]
    bundle(c, pipes, d=(900, 330))

    x, w = 150, xs - 150 - 110
    text(c, HAN, "절단가공 전문", (x, 640, w, 250), YELLOW, shadow=6, max_h=250)
    c.setFillColor(WHITE)
    c.rect(x, 572, w, 10, stroke=0, fill=1)
    text(c, GOT, "스텐판 / 각파이프 / 파이프 / 배관", (x, 345, w, 160), WHITE, max_h=160)
    text(c, GOT, "앵글 / 평철 / 환봉 / 각종부속", (x, 110, w, 160), WHITE, max_h=160)


# ---- 3. 돌출간판 800 x 2000 ---------------------------------------------
def protruding(c, W, H):
    band = 400
    background(c, W, H, band)
    top, cell = H - 70, (H - 70 - band - 60) / 4
    for i, ch in enumerate("혜성금속"):
        text(c, HAN, ch, (110, top - cell * (i + 1) + 30, W - 220, cell - 60), WHITE, shadow=7)
    text(c, GOT, "절단가공", (90, 262, W - 180, 88), YELLOW, max_h=88)
    for label, num, y in (("TEL", "02-953-2110", 155), ("FAX", "02-953-2122", 50)):
        text(c, GOT, label, (60, y, 130, 72), YELLOW, anchor="l", max_h=50)
        text(c, GOT, num, (205, y, W - 265, 72), WHITE, anchor="r", max_h=72)


if __name__ == "__main__":
    make("1_전면간판_큰것", 6000, 1000, front_big)
    make("2_전면간판_작은것", 3000, 1000, front_small)
    make("3_돌출간판", 800, 2000, protruding)
