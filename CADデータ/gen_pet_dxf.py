#!/usr/bin/env python3
"""
★現場ごと/小岩　図面案件/資料/01/S__62578709.jpg に写っている猫と犬を
リアルではなく簡略化した線画（アイコン風）でCAD図（DXF）にするスクリプト。

- 猫: 白地に黒グレーのぶち模様、丸い目、立ち耳（正面顔）
- 犬: ポメラニアン風の丸くふわふわした子犬（全身、ピンクのおもちゃ付き）
- 図形はすべて円・弧・ポリラインなど基本図形の組み合わせで作成（写真のトレースではない）
- DXF形式: AutoCAD 2010 (AC1024)、単位mm
"""

import math
import ezdxf
from ezdxf.colors import rgb2int

OUT_DXF = r"C:\Users\renta\OneDrive\Desktop\AI事務\★現場ごと\小岩　図面案件\資料\01\犬猫イラストCAD図.dxf"
OUT_PNG = r"C:\Users\renta\OneDrive\Desktop\AI事務\★現場ごと\小岩　図面案件\資料\01\犬猫イラストCAD図_プレビュー.png"

BLACK = (30, 30, 30)
GRAY = (150, 150, 150)
PINK = (230, 120, 150)
CREAM = (235, 220, 190)

doc = ezdxf.new("R2010")
doc.header["$INSUNITS"] = 4  # mm
msp = doc.modelspace()

doc.layers.add("OUTLINE", true_color=rgb2int(BLACK))
doc.layers.add("PATTERN", true_color=rgb2int(GRAY))
doc.layers.add("ACCENT", true_color=rgb2int(PINK))
doc.layers.add("TEXT", color=7)

LW = 0.6  # 輪郭線の線幅(mm)


def circle(cx, cy, r, layer="OUTLINE", width=LW):
    msp.add_circle((cx, cy), r, dxfattribs={"layer": layer, "lineweight": int(width * 100)})


def arc(cx, cy, r, a0, a1, layer="OUTLINE", width=LW):
    msp.add_arc((cx, cy), r, a0, a1, dxfattribs={"layer": layer, "lineweight": int(width * 100)})


def line(p0, p1, layer="OUTLINE", width=LW):
    msp.add_line(p0, p1, dxfattribs={"layer": layer, "lineweight": int(width * 100)})


def poly(pts, layer="OUTLINE", close=False, width=LW):
    msp.add_lwpolyline(pts, close=close, dxfattribs={"layer": layer, "const_width": width})


def filled(pts, layer, color):
    hatch = msp.add_hatch(dxfattribs={"layer": layer})
    hatch.set_solid_fill(color=7, style=0, rgb=color)
    hatch.paths.add_polyline_path(pts, is_closed=True)


def fuzzy_points(cx, cy, r, bumps, amp):
    """円周をゆるくギザギザ（ふわふわの毛並み）にした点列を返す"""
    pts = []
    n = bumps * 8
    for i in range(n):
        t = 2 * math.pi * i / n
        bump = amp * math.sin(bumps * t)
        rr = r + bump
        pts.append((cx + rr * math.cos(t), cy + rr * math.sin(t)))
    return pts


def scalloped_circle(cx, cy, r, bumps, amp, layer="OUTLINE", width=LW, fill=None):
    """円周をゆるくギザギザ（ふわふわの毛並み）にしたクローズドポリライン。fill指定でRGB塗りつぶし"""
    pts = fuzzy_points(cx, cy, r, bumps, amp)
    if fill is not None:
        filled(pts, layer, fill)
    poly(pts, layer=layer, close=True, width=width)


def filled_circle(cx, cy, r, layer, color, n=32):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    filled(pts, layer, color)


# ============================================================
# 猫（正面顔） ― 中心 (100, 220)
# ============================================================
CX, CY = 100, 230
HEAD_R = 55

# 頭
circle(CX, CY, HEAD_R)

# 耳（三角、外側）
line((CX - 46, CY + 34), (CX - 20, CY + 92), layer="OUTLINE")
line((CX - 20, CY + 92), (CX - 4, CY + 46), layer="OUTLINE")
line((CX - 4, CY + 46), (CX - 46, CY + 34), layer="OUTLINE")

line((CX + 46, CY + 34), (CX + 20, CY + 92), layer="OUTLINE")
line((CX + 20, CY + 92), (CX + 4, CY + 46), layer="OUTLINE")
line((CX + 4, CY + 46), (CX + 46, CY + 34), layer="OUTLINE")

# 耳の内側（グレー）
filled([(CX - 40, CY + 40), (CX - 22, CY + 82), (CX - 10, CY + 50)], "PATTERN", GRAY)
filled([(CX + 40, CY + 40), (CX + 22, CY + 82), (CX + 10, CY + 50)], "PATTERN", GRAY)

# 頭のグレーぶち模様（頭頂部を覆う一つの丸いキャップ状、写真の柄をラフに再現）
cap_pts = []
n = 40
for i in range(n + 1):
    ang = math.pi * (0.08 + 0.84 * i / n)  # 0〜πの上半分だけ使う
    r_cap = HEAD_R * 0.92
    cap_pts.append((CX + r_cap * math.cos(ang), CY + r_cap * math.sin(ang) * 0.7 + HEAD_R * 0.18))
filled(cap_pts, "PATTERN", GRAY)

# 目（丸、緑がかった大きい瞳＋丸い黒目）
for sign in (-1, 1):
    ex = CX + sign * 24
    ey = CY + 3
    filled_circle(ex, ey, 12, "OUTLINE", (210, 225, 150))
    circle(ex, ey, 12)
    filled_circle(ex, ey, 5, "OUTLINE", BLACK)

# 鼻（小さい三角形、ピンク）
nose_pts = [(CX - 6, CY - 12), (CX + 6, CY - 12), (CX, CY - 20)]
filled(nose_pts, "ACCENT", PINK)
poly(nose_pts, close=True)

# 口（人中＋への字口）
line((CX, CY - 20), (CX, CY - 28))
arc(CX - 8, CY - 28, 8, 300, 90)
arc(CX + 8, CY - 28, 8, 90, 240)

# ひげ
for sign in (-1, 1):
    for dy in (-6, -14, -22):
        line((CX + sign * 20, CY - 16 + dy * 0.3), (CX + sign * 65, CY - 20 + dy))

# ============================================================
# 犬（ポメラニアン子犬、丸くふわふわした一塊のシルエット） ― 中心 (280, 190)
# ============================================================
DX, DY = 280, 190

# 耳（先に描いて本体の後ろに隠れるように、頭の上端から少しだけ覗かせる）
for sign in (-1, 1):
    scalloped_circle(DX + sign * 34, DY + 58, 16, bumps=6, amp=2, fill=CREAM)

# 本体（頭と胴を一体化した大きなふわふわの塊、写真の丸まった子犬のシルエット）
scalloped_circle(DX, DY, 58, bumps=11, amp=5, fill=CREAM)

# 頬のふくらみ（鼻まわりを丸く見せる、本体より少し明るいふち）
for sign in (-1, 1):
    scalloped_circle(DX + sign * 22, DY - 6, 14, bumps=6, amp=2, fill=CREAM)

# 目（黒い丸、まん丸でつぶらな瞳）
for sign in (-1, 1):
    filled_circle(DX + sign * 15, DY + 14, 6, "OUTLINE", BLACK)

# 鼻（黒い小さい丸）
filled_circle(DX, DY, 6, "OUTLINE", BLACK)

# 前足（本体の下端に少し覗く小さいふくらみ2つ）
for sign in (-1, 1):
    scalloped_circle(DX + sign * 20, DY - 56, 11, bumps=6, amp=2, fill=CREAM)

# おもちゃ（ピンクのボーン形、簡略化してダンベル型）
TX, TY = DX, DY - 74
filled([(TX - 22, TY - 5), (TX + 22, TY - 5), (TX + 22, TY + 5), (TX - 22, TY + 5)], "ACCENT", PINK)
poly([(TX - 22, TY - 5), (TX + 22, TY - 5), (TX + 22, TY + 5), (TX - 22, TY + 5)], close=True)
for sign in (-1, 1):
    filled_circle(TX + sign * 22, TY, 8, "ACCENT", PINK)
    circle(TX + sign * 22, TY, 8)

# ============================================================
# タイトル・注記
# ============================================================
msp.add_text(
    "PET ILLUSTRATION - SIMPLIFIED CAD DRAWING",
    dxfattribs={"layer": "TEXT", "height": 6, "insert": (10, 310)},
)
msp.add_text(
    "SOURCE: S__62578709.jpg (Koiwa project)  NOT TO SCALE / NON-REALISTIC ICON",
    dxfattribs={"layer": "TEXT", "height": 4, "insert": (10, 300)},
)
msp.add_text("CAT", dxfattribs={"layer": "TEXT", "height": 6, "insert": (CX - 12, CY - 90)})
msp.add_text("DOG", dxfattribs={"layer": "TEXT", "height": 6, "insert": (DX - 12, DY - 90)})

# 外枠
poly([(0, 0), (400, 0), (400, 330), (0, 330)], close=True, width=0.3)

try:
    doc.saveas(OUT_DXF)
except PermissionError:
    OUT_DXF = OUT_DXF.replace(".dxf", "_new.dxf")
    doc.saveas(OUT_DXF)

print(f"DXF生成完了: {OUT_DXF}")

# ── PNGプレビュー出力 ──────────────────────────────────────
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

fig = plt.figure(figsize=(10, 8))
ax = fig.add_axes([0, 0, 1, 1])
ctx = RenderContext(doc)
out = MatplotlibBackend(ax)
Frontend(ctx, out).draw_layout(msp, finalize=True)
fig.savefig(OUT_PNG, dpi=150, facecolor="white")
print(f"PNGプレビュー生成完了: {OUT_PNG}")
