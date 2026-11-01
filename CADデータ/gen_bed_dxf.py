#!/usr/bin/env python3
"""
整体ベッド（施術台）DXF 生成スクリプト
寸法: 長さ 1900 x 幅 600 x 高さ 700mm
3面図: 平面図 / 側面図 / 正面図（頭部端）
"""

import math

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

def rect(layer, x0, y0, w, h):
    line(layer, x0,   y0,   x0+w, y0)
    line(layer, x0+w, y0,   x0+w, y0+h)
    line(layer, x0+w, y0+h, x0,   y0+h)
    line(layer, x0,   y0+h, x0,   y0)

# ── 寸法線ヘルパー ─────────────────────────────────────────────────────────
TICK = 25  # tick mark half-size (mm)

def dim_h(x1, x2, y, label, ext=60, th=55):
    """水平寸法線"""
    layer = "DIMENSION"
    # 引き出し線
    line(layer, x1, y + ext * 0.1, x1, y - ext)
    line(layer, x2, y + ext * 0.1, x2, y - ext)
    # 寸法線
    line(layer, x1, y, x2, y)
    # 矢印（tick marks）
    line(layer, x1 - TICK, y - TICK, x1 + TICK, y + TICK)
    line(layer, x2 - TICK, y - TICK, x2 + TICK, y + TICK)
    # テキスト
    text_center(layer, (x1 + x2) / 2, y + 15, th, label)

def dim_v(x, y1, y2, label, ext=80, th=55):
    """垂直寸法線"""
    layer = "DIMENSION"
    line(layer, x - ext * 0.1, y1, x + ext, y1)
    line(layer, x - ext * 0.1, y2, x + ext, y2)
    line(layer, x, y1, x, y2)
    line(layer, x - TICK, y1 - TICK, x + TICK, y1 + TICK)
    line(layer, x - TICK, y2 - TICK, x + TICK, y2 + TICK)
    text("DIMENSION", x + 20, (y1 + y2) / 2 - th / 2, th, label)

# ═════════════════════════════════════════════════════════════════════════════
# 1. 平面図（PLAN VIEW）: X[0..1900], Y[1050..1650]
# ═════════════════════════════════════════════════════════════════════════════
PL_X, PL_Y = 0, 1050       # 底辺左 (頭部端・手前)
PL_L, PL_W = 1900, 600     # 長さ、幅

# 外形線
rect("BODY", PL_X, PL_Y, PL_L, PL_W)

# 顔穴（頭部端中央、Ø160mm）
circle("BODY", PL_X + 150, PL_Y + PL_W // 2, 80)
text("TEXT", PL_X + 210, PL_Y + PL_W // 2 - 25, 35, "FACE HOLE Dia.160")

# セクション分割線（破線）
for sx in [500, 1050, 1550]:
    line("SECTION", PL_X + sx, PL_Y, PL_X + sx, PL_Y + PL_W)

# 中心線
line("CENTER", PL_X, PL_Y + PL_W / 2, PL_X + PL_L, PL_Y + PL_W / 2)

# 脚部（40x40mm 角管、4隅）
for lx, ly in [
    (PL_X + 80,        PL_Y + 70),
    (PL_X + 80,        PL_Y + PL_W - 110),
    (PL_X + PL_L - 120, PL_Y + 70),
    (PL_X + PL_L - 120, PL_Y + PL_W - 110),
]:
    rect("BODY", lx, ly, 40, 40)

# 横連結バー（隠れ線）
line("HIDDEN", PL_X + 100, PL_Y + 90,        PL_X + PL_L - 100, PL_Y + 90)
line("HIDDEN", PL_X + 100, PL_Y + PL_W - 90, PL_X + PL_L - 100, PL_Y + PL_W - 90)

# ─ 平面図 寸法 ─
# 全長 1900 （下）
dim_h(PL_X, PL_X + PL_L, PL_Y - 80, "1900", ext=50, th=55)
# 全幅 600 （右）
dim_v(PL_X + PL_L + 130, PL_Y, PL_Y + PL_W, "600", ext=80, th=55)
# セクション幅ラベル（上）
sec_labels = ["500", "550", "500", "350"]
sec_xs = [0, 500, 1050, 1550, 1900]
for i in range(4):
    mx = (sec_xs[i] + sec_xs[i + 1]) / 2
    text_center("TEXT", PL_X + mx, PL_Y + PL_W + 30, 38, sec_labels[i])

# ─ 平面図ラベル ─
text_center("TEXT", PL_X + PL_L / 2, PL_Y + PL_W + 120, 75, "PLAN VIEW  (平面図)")

# ═════════════════════════════════════════════════════════════════════════════
# 2. 側面図（SIDE ELEVATION）: X[0..1900], Y[0..780]
# 床 Y=0、テーブル天面 Y=700、天板上面 Y=780
# ═════════════════════════════════════════════════════════════════════════════
SV_FLOOR  = 0
SV_SURF   = 700   # テーブル天面（床から）
SV_TOP    = 780   # 天板上面（700+80）
SV_L      = 1900
LEG_W     = 40    # 脚幅
LEG_INSET = 100   # 頭・足端からの脚の距離

# 床線
line("BODY", -250, SV_FLOOR, SV_L + 300, SV_FLOOR)

# 天板
line("BODY", 0,    SV_TOP,  SV_L, SV_TOP)        # 上面
line("BODY", 0,    SV_SURF, SV_L, SV_SURF)        # 下面
line("BODY", 0,    SV_TOP,  0,    SV_SURF)         # 頭端
line("BODY", SV_L, SV_TOP,  SV_L, SV_SURF)        # 足端

# 頭部脚（X:80-120）
line("BODY", 80,  SV_FLOOR, 80,  SV_SURF)
line("BODY", 120, SV_FLOOR, 120, SV_SURF)
line("BODY", 80,  SV_FLOOR, 120, SV_FLOOR)

# 足部脚（X:1780-1820）
line("BODY", SV_L - 120, SV_FLOOR, SV_L - 120, SV_SURF)
line("BODY", SV_L - 80,  SV_FLOOR, SV_L - 80,  SV_SURF)
line("BODY", SV_L - 120, SV_FLOOR, SV_L - 80,  SV_FLOOR)

# 中間横バー（H フレーム連結）
line("BODY", 120,       310, SV_L - 120, 310)
line("BODY", 120,       350, SV_L - 120, 350)
line("BODY", 120,       310, 120,        350)
line("BODY", SV_L-120, 310, SV_L-120,   350)

# セクション仕切り（天板のみ点線で示す）
for sx in [500, 1050, 1550]:
    line("SECTION", sx, SV_SURF, sx, SV_TOP)

# 顔穴の位置（側面から見た隠れ線）
line("HIDDEN", 70, SV_TOP, 230, SV_TOP)

# 中心線
line("CENTER", 0, (SV_SURF + SV_TOP) / 2, SV_L, (SV_SURF + SV_TOP) / 2)

# ─ 側面図 寸法 ─
# 床→天面 700（左）
dim_v(-180, SV_FLOOR, SV_SURF, "700", ext=120, th=55)
# 天板厚み 80（右）
dim_v(SV_L + 220, SV_SURF, SV_TOP, "t=80", ext=120, th=40)
# 全長 1900（下）
dim_h(0, SV_L, SV_FLOOR - 100, "1900", ext=60, th=55)

# ─ 側面図ラベル ─
text_center("TEXT", SV_L / 2, SV_FLOOR - 270, 75, "SIDE ELEVATION  (側面図)")

# ═════════════════════════════════════════════════════════════════════════════
# 3. 正面図（END ELEVATION - 頭部端から見る）: X[2200..2800], Y[0..780]
# ═════════════════════════════════════════════════════════════════════════════
FV_X0 = 2200
FV_W  = 600

# 床線
line("BODY", FV_X0 - 150, SV_FLOOR, FV_X0 + FV_W + 150, SV_FLOOR)

# 天板
line("BODY", FV_X0,        SV_TOP,  FV_X0 + FV_W, SV_TOP)
line("BODY", FV_X0,        SV_SURF, FV_X0 + FV_W, SV_SURF)
line("BODY", FV_X0,        SV_TOP,  FV_X0,         SV_SURF)
line("BODY", FV_X0 + FV_W, SV_TOP,  FV_X0 + FV_W,  SV_SURF)

# 顔穴（天板断面中央に表示）
circle("BODY", FV_X0 + FV_W / 2, (SV_SURF + SV_TOP) / 2, 80)

# 左脚（X:2280-2320）
line("BODY", FV_X0 + 80,  SV_FLOOR, FV_X0 + 80,  SV_SURF)
line("BODY", FV_X0 + 120, SV_FLOOR, FV_X0 + 120, SV_SURF)
line("BODY", FV_X0 + 80,  SV_FLOOR, FV_X0 + 120, SV_FLOOR)

# 右脚（X:2680-2720）
line("BODY", FV_X0 + 480, SV_FLOOR, FV_X0 + 480, SV_SURF)
line("BODY", FV_X0 + 520, SV_FLOOR, FV_X0 + 520, SV_SURF)
line("BODY", FV_X0 + 480, SV_FLOOR, FV_X0 + 520, SV_FLOOR)

# 中間横バー
line("BODY", FV_X0 + 120, 310, FV_X0 + 480, 310)
line("BODY", FV_X0 + 120, 350, FV_X0 + 480, 350)
line("BODY", FV_X0 + 120, 310, FV_X0 + 120, 350)
line("BODY", FV_X0 + 480, 310, FV_X0 + 480, 350)

# 中心線
line("CENTER", FV_X0 + FV_W / 2, SV_FLOOR, FV_X0 + FV_W / 2, SV_TOP)

# ─ 正面図 寸法 ─
# 全幅 600（上）
dim_h(FV_X0, FV_X0 + FV_W, SV_TOP + 120, "600", ext=80, th=55)
# 高さ 700（右）
dim_v(FV_X0 + FV_W + 180, SV_FLOOR, SV_SURF, "700", ext=120, th=55)

# ─ 正面図ラベル ─
text_center("TEXT", FV_X0 + FV_W / 2, SV_FLOOR - 270, 75,
            "END ELEVATION  (正面図・頭部端)")

# ═════════════════════════════════════════════════════════════════════════════
# メインタイトル・仕様
# ═════════════════════════════════════════════════════════════════════════════
text_center("TEXT", 950, 2100, 110, "MASSAGE TABLE  (整体ベッド / 施術台)")
text_center("TEXT", 950, 1950, 65, "L=1900  W=600  H=700  (mm)   LEG: 40x40 SQ.TUBE")
text("TEXT",        0,  -450,  55, "SCALE: 1:20   UNITS: mm   (C) AXIS CO.,LTD.")

# 注記
text("TEXT", PL_X, PL_Y + PL_W + 220, 45, "* HEAD SECTION=500 / CHEST=550 / WAIST=500 / LEG=350")

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
-600.0
  9
$LIMMAX
 10
3200.0
 20
2300.0
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

output_path = r"c:\Users\renta\OneDrive\Desktop\AI事務\CADデータ\整体ベッド.dxf"

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
