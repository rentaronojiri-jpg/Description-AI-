#!/usr/bin/env python3
"""
AXISロゴ（会社情報/AXIS_logo.png）を画像トレースしてDXF化するスクリプト
- ダーク（オリーブ色）と オレンジ の2色を輪郭抽出し、それぞれ別レイヤーの
  ①HATCH（ソリッド塗りつぶし・実測ブランドカラーの正確な色）
  ②LWPOLYLINE（太め線幅の輪郭・くっきり表示用）
  として出力する
- 文字の抜き穴（例: 小文字の R・e・D などの内側の輪）はcv2の輪郭階層から検出し、
  HATCHの内側境界（穴）として正しく塗り抜く
- タグライン下の淡いダッシュ2本は元画像で透明度が極端に低くトレースで拾えないため、
  実測位置に矩形として手動で補完している
- 出力サイズ: 幅 300mm（元画像 560px を 300mm に換算、縦横比維持）
- DXF形式: AutoCAD 2010 (AC1024) — HATCH・真色(true color, R2004以降が必要)を使うため
"""

import cv2
import numpy as np
from PIL import Image
import ezdxf
from ezdxf.colors import rgb2int

SRC_PNG = r"C:\Users\renta\OneDrive\Desktop\AI事務\会社情報\AXIS_logo.png"
OUT_DXF = r"C:\Users\renta\OneDrive\Desktop\AI事務\CADデータ\AXISロゴ.dxf"
LOGO_WIDTH_MM = 300.0   # 出力する図面上でのロゴ幅
OUTLINE_WIDTH_MM = 1.0  # 輪郭線の太さ（「くっきり」させるための線幅）

# ── 1. 画像読み込み・色分離（曲線を滑らかにするため高解像度にアップサンプル） ──
UPSCALE = 6  # 元画像を何倍に拡大してからトレースするか（大きいほど曲線が滑らか）

src_img = Image.open(SRC_PNG).convert("RGBA")
ORIG_W, ORIG_H = src_img.size
img = src_img.resize((ORIG_W * UPSCALE, ORIG_H * UPSCALE), Image.LANCZOS)
arr = np.array(img)
IMG_H, IMG_W = arr.shape[:2]
alpha = arr[:, :, 3]
rgb = arr[:, :, :3].astype(int)
maxc = rgb.max(axis=2)

opaque = alpha > 90
fg = opaque & (maxc < 235)

# 薄いアンチエイリアス部（ダッシュ・プラス記号）を繋ぐための軽いクロージング
fg_u8 = (fg.astype(np.uint8)) * 255
close_k = max(2, UPSCALE // 2)
fg_u8 = cv2.morphologyEx(fg_u8, cv2.MORPH_CLOSE, np.ones((close_k, close_k), np.uint8))
fg = fg_u8 > 0

r = rgb[:, :, 0]
b = rgb[:, :, 2]
orange_mask = fg & ((r - b) > 40)
dark_mask = fg & ~((r - b) > 40)

# タグライン（小さい文字・+記号）の帯: 元絵では非常に小さく、マスクの輪郭自体が
# ピクセル単位でギザギザ（ノイズ）になっている。ポリライン簡略化だけでは
# 「粗すぎて字が潰れる」か「細かすぎてギザギザが残る」の両極端になってしまうため、
# この帯だけモルフォロジー処理（オープン→クローズ）でマスク自体のノイズを除去する
BAND_Y0, BAND_Y1 = 183, 212  # 元画像px（帯の上下）
band_y0_up, band_y1_up = BAND_Y0 * UPSCALE, BAND_Y1 * UPSCALE
_band_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (UPSCALE + 1, UPSCALE + 1))


def denoise_band(mask, y0, y1, k):
    band = (mask[y0:y1, :].astype(np.uint8)) * 255
    band = cv2.morphologyEx(band, cv2.MORPH_OPEN, k)
    out = mask.copy()
    out[y0:y1, :] = band > 0
    return out


dark_mask = denoise_band(dark_mask, band_y0_up, band_y1_up, _band_k)
orange_mask = denoise_band(orange_mask, band_y0_up, band_y1_up, _band_k)


def extract_shapes(mask, eps_px=1.0, min_area=1.5):
    """輪郭階層を見て外形＋穴のペアを返す: [{"outer": poly, "holes": [poly, ...]}]
    eps_pxは絶対ピクセル許容誤差（小さいほど曲線に沿った点が多く残り滑らかになる）。
    """
    m = (mask.astype(np.uint8)) * 255
    contours, hierarchy = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []
    hierarchy = hierarchy[0]

    def simplify(cnt):
        area = cv2.contourArea(cnt)
        if area < min_area:
            return None
        approx = cv2.approxPolyDP(cnt, eps_px, True)
        pts = approx.reshape(-1, 2)
        if len(pts) < 3:
            return None
        return pts.tolist()

    shapes = {}
    for i, cnt in enumerate(contours):
        if hierarchy[i][3] == -1:
            poly = simplify(cnt)
            if poly:
                shapes[i] = {"outer": poly, "holes": []}
    for i, cnt in enumerate(contours):
        parent = hierarchy[i][3]
        if parent != -1 and parent in shapes:
            poly = simplify(cnt)
            if poly:
                shapes[parent]["holes"].append(poly)
    return list(shapes.values())


EPS_PX = UPSCALE * 1.1  # 曲線の滑らかさ（アップサンプル後のピクセル単位）
dark_shapes = extract_shapes(dark_mask, eps_px=EPS_PX, min_area=1.5 * UPSCALE ** 2)
orange_shapes = extract_shapes(orange_mask, eps_px=EPS_PX, min_area=6 * UPSCALE ** 2)


def rect_poly(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


# タグライン両脇のダッシュは元画像の透明度が低くトレース結果が歪んだ細い断片に
# なるため取り除き、実測位置のクリーンな矩形に置き換える
DASH_NOISE_BOXES = [(35, 100, 190, 205), (455, 515, 190, 205)]  # (x0,x1,y0,y1) 元px


def in_dash_noise_zone(outer_poly):
    xs = [p[0] / UPSCALE for p in outer_poly]
    ys = [p[1] / UPSCALE for p in outer_poly]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    return any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, x1, y0, y1 in DASH_NOISE_BOXES)


orange_shapes = [s for s in orange_shapes if not in_dash_noise_zone(s["outer"])]

# タグライン両脇の淡いダッシュ（元画像で実測した位置、px単位 → アップサンプル座標に変換）
orange_shapes.append({
    "outer": rect_poly(47 * UPSCALE, 195 * UPSCALE, 90 * UPSCALE, 201 * UPSCALE),
    "holes": [],
})
orange_shapes.append({
    "outer": rect_poly(464 * UPSCALE, 195 * UPSCALE, 507 * UPSCALE, 201 * UPSCALE),
    "holes": [],
})

# ブランドカラーをマスク内部（縁のアンチエイリアスを避けて収縮）から実測
def representative_color(mask, fallback):
    er = cv2.erode((mask.astype(np.uint8)) * 255, np.ones((3 * UPSCALE, 3 * UPSCALE), np.uint8))
    px = rgb[er > 0]
    if len(px) == 0:
        return fallback
    m = px.mean(axis=0)
    return tuple(int(round(v)) for v in m)


DARK_COLOR = representative_color(dark_mask, (40, 48, 32))
ORANGE_COLOR = representative_color(orange_mask, (230, 120, 20))

# ── 2. px → mm 変換（アップサンプル座標 → 元画像基準のmm、Y反転） ─────────
SCALE = LOGO_WIDTH_MM / ORIG_W


def to_mm(poly):
    return [(x / UPSCALE * SCALE, (IMG_H - y) / UPSCALE * SCALE) for x, y in poly]


# ── 3. DXF構築（ezdxf, AutoCAD 2000形式） ────────────────────────────────
doc = ezdxf.new("R2010")
doc.header["$INSUNITS"] = 4  # mm
msp = doc.modelspace()

doc.layers.add("LOGO_DARK", true_color=rgb2int(DARK_COLOR))
doc.layers.add("LOGO_ORANGE", true_color=rgb2int(ORANGE_COLOR))
doc.layers.add("TEXT", color=7)


def add_shape(shape, layer, color):
    outer_mm = to_mm(shape["outer"])
    holes_mm = [to_mm(h) for h in shape["holes"]]

    hatch = msp.add_hatch(dxfattribs={"layer": layer})
    hatch.set_solid_fill(color=7, style=0, rgb=color)
    hatch.paths.add_polyline_path(outer_mm, is_closed=True)
    for hole in holes_mm:
        hatch.paths.add_polyline_path(hole, is_closed=True)

    # 太い一定幅の輪郭線は、図形が小さい（帯の中の小さい文字など）と鋭い凹角で
    # 極端なマイター（尖ったスパイク）が出てしまうため、図形サイズに応じて細くする
    xs = [p[0] for p in outer_mm]
    ys = [p[1] for p in outer_mm]
    shape_size = min(max(xs) - min(xs), max(ys) - min(ys))
    width = min(OUTLINE_WIDTH_MM, max(shape_size * 0.10, 0.12))

    msp.add_lwpolyline(
        outer_mm, close=True,
        dxfattribs={"layer": layer, "const_width": width,
                    "true_color": rgb2int(color)},
    )
    for hole in holes_mm:
        msp.add_lwpolyline(
            hole, close=True,
            dxfattribs={"layer": layer, "const_width": width * 0.5,
                        "true_color": rgb2int(color)},
        )


for shp in dark_shapes:
    add_shape(shp, "LOGO_DARK", DARK_COLOR)
for shp in orange_shapes:
    add_shape(shp, "LOGO_ORANGE", ORANGE_COLOR)

logo_h_mm = ORIG_H * SCALE
msp.add_text(
    "AXIS LOGO - VECTOR TRACE (DXF, filled)",
    dxfattribs={"layer": "TEXT", "height": 6, "insert": (0, logo_h_mm + 22)},
)
msp.add_text(
    f"WIDTH={LOGO_WIDTH_MM:.0f}mm  SOURCE: AXIS_logo.png",
    dxfattribs={"layer": "TEXT", "height": 4, "insert": (0, logo_h_mm + 12)},
)

try:
    doc.saveas(OUT_DXF)
except PermissionError:
    # AutoCAD等で開いていてロックされている場合は別名で保存する
    alt = OUT_DXF.replace(".dxf", "_new.dxf")
    doc.saveas(alt)
    OUT_DXF = alt
    print(f"※ 元ファイルがロックされていたため別名で保存: {alt}")

print(f"生成完了: {OUT_DXF}")
print(f"ダーク図形: {len(dark_shapes)}（穴あり {sum(1 for s in dark_shapes if s['holes'])}） "
      f"/ オレンジ図形: {len(orange_shapes)}")
print(f"ダーク色 RGB{DARK_COLOR} / オレンジ色 RGB{ORANGE_COLOR}")
