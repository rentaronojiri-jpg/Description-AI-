#!/usr/bin/env python3
"""
L型カウンター 組立設計図 DXF生成スクリプト
元データ: 設計図作成/組立設計図_カウンター_20260711.html
寸法: 平面外形 1000(D面)x1830(A面)mm、立上り高さ1100mm、板厚20mm
入隅コーナー位置: D面から450mm、A面から500mm
2面図: 平面図（L字） / 立面図（A・B・C・D面 展開）
"""

entities = []

# ── ヘルパー関数 ──────────────────────────────────────────────────────────

def line(layer, x1, y1, x2, y2):
    entities.append(
        f"  0\nLINE\n  8\n{layer}\n"
        f" 10\n{x1:.3f}\n 20\n{y1:.3f}\n 30\n0.000\n"
        f" 11\n{x2:.3f}\n 21\n{y2:.3f}\n 31\n0.000\n"
    )

def circle(layer, cx, cy, r):
    entities.append(
        f"  0\nCIRCLE\n  8\n{layer}\n"
        f" 10\n{cx:.3f}\n 20\n{cy:.3f}\n 30\n0.000\n 40\n{r:.3f}\n"
    )

def text(layer, x, y, h, s):
    entities.append(
        f"  0\nTEXT\n  8\n{layer}\n"
        f" 10\n{x:.3f}\n 20\n{y:.3f}\n 30\n0.000\n 40\n{h:.3f}\n  1\n{s}\n"
    )

def text_center(layer, x, y, h, s):
    entities.append(
        f"  0\nTEXT\n  8\n{layer}\n"
        f" 10\n{x:.3f}\n 20\n{y:.3f}\n 30\n0.000\n 40\n{h:.3f}\n  1\n{s}\n"
        f" 72\n1\n 11\n{x:.3f}\n 21\n{y:.3f}\n 31\n0.000\n"
    )

def polyline(layer, points, closed=True):
    for i in range(len(points) - (0 if closed else 1)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]
        line(layer, x1, y1, x2, y2)

def rect(layer, x0, y0, w, h):
    line(layer, x0,   y0,   x0+w, y0)
    line(layer, x0+w, y0,   x0+w, y0+h)
    line(layer, x0+w, y0+h, x0,   y0+h)
    line(layer, x0,   y0+h, x0,   y0)

# ── 寸法線ヘルパー ─────────────────────────────────────────────────────────
TICK = 25  # tick mark half-size (mm)

def dim_h(x1, x2, y, label, ext=60, th=45):
    """水平寸法線"""
    layer = "DIMENSION"
    line(layer, x1, y + ext * 0.1, x1, y - ext)
    line(layer, x2, y + ext * 0.1, x2, y - ext)
    line(layer, x1, y, x2, y)
    line(layer, x1 - TICK, y - TICK, x1 + TICK, y + TICK)
    line(layer, x2 - TICK, y - TICK, x2 + TICK, y + TICK)
    text_center(layer, (x1 + x2) / 2, y + 15, th, label)

def dim_v(x, y1, y2, label, ext=80, th=45):
    """垂直寸法線"""
    layer = "DIMENSION"
    line(layer, x - ext * 0.1, y1, x + ext, y1)
    line(layer, x - ext * 0.1, y2, x + ext, y2)
    line(layer, x, y1, x, y2)
    line(layer, x - TICK, y1 - TICK, x + TICK, y1 + TICK)
    line(layer, x - TICK, y2 - TICK, x + TICK, y2 + TICK)
    text("DIMENSION", x + 20, (y1 + y2) / 2 - th / 2, th, label)

# ═════════════════════════════════════════════════════════════════════════════
# 1. 平面図（PLAN VIEW）L字形状
# 外形: D面(1000, 上辺) / A面(1830, 左辺) / 入隅コーナー D面から450, A面から500
# 座標: 原点(0,0)を外形の左下(A面下端×D面左端)に置く
# ═════════════════════════════════════════════════════════════════════════════
PL_X, PL_Y = 0, 0

# L字外形ポリライン（HTML図の入隅コーナー(450,500)を再現）
# (0,0)-(1000,0)-(1000,500)-(450,500)-(450,1830)-(0,1830)-close
L_PTS = [
    (PL_X,       PL_Y),
    (PL_X+1000,  PL_Y),
    (PL_X+1000,  PL_Y+500),
    (PL_X+450,   PL_Y+500),
    (PL_X+450,   PL_Y+1830),
    (PL_X,       PL_Y+1830),
]
polyline("BODY", L_PTS, closed=True)

# 入隅コーナーマーカー
circle("BODY", PL_X+450, PL_Y+500, 8)
text("TEXT", PL_X+470, PL_Y+520, 30, "入隅コーナー(450,500)")

# 面ラベル
text("TEXT", PL_X-120, PL_Y+900, 40, "A面")          # 左辺（長さ1830）
text_center("TEXT", PL_X+500, PL_Y-60, 40, "D面")     # 下辺（長さ1000）
text("TEXT", PL_X+470, PL_Y+1150, 36, "B面")          # 内側縦辺（長さ1330）
text_center("TEXT", PL_X+725, PL_Y+560, 36, "C面")    # 内側横辺（長さ550）

# ─ 平面図 寸法 ─
dim_v(PL_X-150, PL_Y, PL_Y+1830, "1830 (A面)", ext=100, th=45)   # 全長（左）
dim_h(PL_X, PL_X+1000, PL_Y-150, "1000 (D面)", ext=60, th=45)    # 全幅（下）
dim_v(PL_X+520, PL_Y, PL_Y+500, "500 (C面)", ext=60, th=32)      # C面高さ
dim_h(PL_X+450, PL_X+1000, PL_Y+560, "550 (C面)", ext=40, th=32) # C面幅
dim_v(PL_X+380, PL_Y+500, PL_Y+1830, "1330 (B面)", ext=40, th=32) # B面

# ─ 平面図ラベル ─
text_center("TEXT", PL_X+500, PL_Y+2050, 65, "PLAN VIEW  (平面図・L型カウンター)")
text("TEXT", PL_X-150, PL_Y+2150, 32, "板厚20mm／天板までの立上り高さ1100mm（各面共通）")

# ═════════════════════════════════════════════════════════════════════════════
# 2. 立面図（ELEVATION）A・B・C・D 4面展開
# 高さ1100mm共通。A/D面下端に100mm見切り、B/C面下端に30mm段差（推定）
# ═════════════════════════════════════════════════════════════════════════════
EV_Y0 = -600          # 立面図の基準Y（平面図の下に配置しないよう別エリア）
EV_H  = 1100
faces = [
    ("A面", 1830, 100, "+100見切り"),
    ("B面", 1330, 30,  "+30段差"),
    ("C面", 550,  30,  "+30段差"),
    ("D面", 1000, 100, "+100見切り"),
]

ex = 2400  # 立面図エリアの開始X（平面図と干渉しないよう右側に配置）
gap = 200
for name, w, skirt, note in faces:
    rect("BODY", ex, EV_Y0, w, EV_H)
    rect("SECTION", ex, EV_Y0 - skirt, w, skirt)
    text_center("TEXT", ex + w/2, EV_Y0 + EV_H/2, 60, name)
    text_center("TEXT", ex + w/2, EV_Y0 + EV_H/2 - 80, 36, f"H{EV_H}")
    text_center("TEXT", ex + w/2, EV_Y0 - skirt - 40, 30, note)
    dim_h(ex, ex + w, EV_Y0 - skirt - 120, str(w), ext=40, th=32)
    dim_v(ex - 80, EV_Y0, EV_Y0 + EV_H, str(EV_H) if name == "A面" else "", ext=40, th=32)
    ex += w + gap

text_center("TEXT", (2400 + ex) / 2, EV_Y0 + EV_H + 150, 65,
            "ELEVATION  (立面図・展開4面 A/B/C/D)")

# ═════════════════════════════════════════════════════════════════════════════
# メインタイトル・自社情報タイトル欄
# ═════════════════════════════════════════════════════════════════════════════
text_center("TEXT", 1500, 2550, 100, "L型カウンター 組立設計図")
text_center("TEXT", 1500, 2400, 50, "元図面：カウンター製作図（2026.7.11）／板厚20mm／立上り高さ1100mm")
text("TEXT", 0, -1100, 45, "SCALE: 1:20   UNITS: mm")

# ── タイトル欄（会社名・住所・TEL・ロゴ参照） ──
TB_X, TB_Y, TB_W, TB_H = 0, -1500, 1500, 260
rect("TITLEBLOCK", TB_X, TB_Y, TB_W, TB_H)
line("TITLEBLOCK", TB_X, TB_Y + 170, TB_X + TB_W, TB_Y + 170)  # 会社名と住所欄の区切り
text("TEXT", TB_X + 30, TB_Y + 190, 70, "株式会社AXIS")
text("TEXT", TB_X + 30, TB_Y + 110, 34, "埼玉県草加市小山2-29-10（〒340-0045）")
text("TEXT", TB_X + 30, TB_Y + 60,  34, "TEL 090-9825-2087")
text("TEXT", TB_X + 30, TB_Y + 15,  26, "LOGO: 会社情報/AXIS_logo.png （※DXFは画像埋込非対応のため別途貼付）")

# ═════════════════════════════════════════════════════════════════════════════
# DXF 出力
# ═════════════════════════════════════════════════════════════════════════════
HEADER = """\
  0
SECTION
  2
HEADER
  9
$ACADVER
  1
AC1009
  9
$INSUNITS
 70
4
  9
$LIMMIN
 10
-500.0
 20
-1700.0
  9
$LIMMAX
 10
5200.0
 20
2700.0
  0
ENDSEC
"""

TABLES = """\
  0
SECTION
  2
TABLES
  0
TABLE
  2
LTYPE
 70
4
  0
LTYPE
  2
CONTINUOUS
 70
0
  3
Solid line
 72
65
 73
0
 40
0.0
  0
LTYPE
  2
DASHED
 70
0
  3
__ __ __ __
 72
65
 73
2
 40
0.75
 49
0.5
 49
-0.25
  0
LTYPE
  2
CENTER
 70
0
  3
____ _ ____ _
 72
65
 73
4
 40
2.0
 49
1.25
 49
-0.25
 49
0.25
 49
-0.25
  0
ENDTAB
  0
TABLE
  2
LAYER
 70
7
  0
LAYER
  2
BODY
 70
0
 62
7
  6
CONTINUOUS
  0
LAYER
  2
SECTION
 70
0
 62
5
  6
DASHED
  0
LAYER
  2
CENTER
 70
0
 62
1
  6
CENTER
  0
LAYER
  2
HIDDEN
 70
0
 62
8
  6
DASHED
  0
LAYER
  2
DIMENSION
 70
0
 62
3
  6
CONTINUOUS
  0
LAYER
  2
TEXT
 70
0
 62
7
  6
CONTINUOUS
  0
LAYER
  2
TITLEBLOCK
 70
0
 62
7
  6
CONTINUOUS
  0
LAYER
  2
0
 70
0
 62
7
  6
CONTINUOUS
  0
ENDTAB
  0
TABLE
  2
STYLE
 70
1
  0
STYLE
  2
STANDARD
 70
0
 40
0.0
 41
1.0
 50
0.0
 71
0
 42
0.2
  3
txt
  4

  0
ENDTAB
  0
ENDSEC
"""

output_path = r"c:\Users\renta\OneDrive\Desktop\AI事務\CADデータ\カウンター.dxf"

with open(output_path, "w", encoding="cp932", errors="replace") as f:
    f.write(HEADER)
    f.write(TABLES)
    f.write("  0\nSECTION\n  2\nBLOCKS\n  0\nENDSEC\n")
    f.write("  0\nSECTION\n  2\nENTITIES\n")
    for e in entities:
        f.write(e)
    f.write("  0\nENDSEC\n  0\nEOF\n")

print(f"生成完了: {output_path}")
print(f"エンティティ数: {len(entities)}")
