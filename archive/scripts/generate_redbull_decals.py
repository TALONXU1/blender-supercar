# -*- coding: utf-8 -*-
"""
High-Precision Sponsor Decal Generator for Oracle Red Bull Racing F1 Livery
Optimized for maximum contrast, scale and racing presence
Author: TalonX (Visual Communication Design Standard)
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

TEX_DIR = r"D:\项目session\blender-supercar\textures"
os.makedirs(TEX_DIR, exist_ok=True)

# 字体加载
FONT_PATH = r"C:\Windows\Fonts\bahnschrift.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"

def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()

# 官方色彩空间 (Oracle Red Bull Racing)
COLOR_RED = (235, 10, 0, 255)         # Vibrant Racing Crimson
COLOR_YELLOW = (255, 210, 0, 255)    # Solar Golden Yellow
COLOR_YELLOW_DARK = (235, 165, 0, 255)
COLOR_WHITE = (255, 255, 255, 255)   # Pure High-Contrast White
COLOR_NAVY = (15, 22, 38, 255)       # Matte Midnight Navy
COLOR_MOBIL_BLUE = (0, 75, 160, 255) # Mobil Blue

# 精密西班牙公牛动态剪影 (已通过 test_bull_perfect 审美校验)
BULL_COORDS = [
    # Top of Horn 1
    (-140, -130), (-115, -85), (-80, -45),
    # Forehead & Brow
    (-95, -30), (-125, -10), (-135, 10),
    # Snout & Muzzle
    (-145, 30), (-130, 45), (-110, 45),
    # Lower Jaw & Throat
    (-90, 50), (-80, 65),
    # Dewlap & Powerful Muscular Chest
    (-65, 85), (-50, 115),
    # Foreleg 1 (Reaching forward)
    (-40, 145), (-30, 175), (-15, 175), (-20, 135),
    # Foreleg 2 (Bent backward in gallop)
    (5, 120), (25, 145), (40, 140), (20, 95),
    # Ribcage & Tapered Waist (Coke bottle waist of bull)
    (10, 65), (45, 55), (75, 60),
    # Hind Leg 1 (Coiled thrust)
    (105, 95), (135, 145), (155, 140), (130, 85),
    # Hind Leg 2 (Trailing behind)
    (150, 110), (180, 165), (195, 160), (165, 60),
    # Flank & Rump
    (150, 20), (145, -20),
    # Tail (Whipping S-Curve with tuft)
    (160, -40), (185, -75), (195, -110), (180, -115), (165, -85), (140, -45), (125, -30),
    # Spine sloping down from hump
    (100, -35), (60, -45), (20, -60),
    # Powerful Muscular Shoulder Hump (Withers)
    (-20, -85), (-45, -80), (-65, -60),
    # Horn base & Top of Horn 1
    (-75, -45), (-115, -85), (-140, -130)
]

HORN1_COORDS = [(-75, -45), (-115, -85), (-140, -130), (-110, -75), (-75, -45)]
HORN2_COORDS = [(-60, -55), (-90, -100), (-115, -135), (-95, -95), (-60, -55)]

def draw_spanish_bull(draw, center_x, center_y, scale=1.0, flip_x=False):
    """绘制高保真红牛冲刺公牛（含双金角与阴影层）"""
    sign = -1.0 if flip_x else 1.0
    
    # 红色公牛身躯
    pts = [(center_x + px * scale * sign, center_y + py * scale) for px, py in BULL_COORDS]
    draw.polygon(pts, fill=COLOR_RED)
    
    # 金黄双角
    h2_pts = [(center_x + px * scale * sign, center_y + py * scale) for px, py in HORN2_COORDS]
    draw.polygon(h2_pts, fill=COLOR_YELLOW_DARK)
    
    h1_pts = [(center_x + px * scale * sign, center_y + py * scale) for px, py in HORN1_COORDS]
    draw.polygon(h1_pts, fill=COLOR_YELLOW)


# =========================================================================
# 1. 侧箱巨幅 ORACLE + 赛车拉花 (decal_sidepod_oracle.png)
# =========================================================================
img_side = Image.new("RGBA", (2048, 640), (0, 0, 0, 0))
d_side = ImageDraw.Draw(img_side)

# 动态红黄两色流线赛道拉花 (Speed Dynamic Chevrons)
pts_ribbon_red = [(20, 520), (2020, 520), (1960, 580), (0, 580)]
d_side.polygon(pts_ribbon_red, fill=COLOR_RED)

pts_ribbon_yellow = [(60, 480), (2040, 480), (2020, 520), (20, 520)]
d_side.polygon(pts_ribbon_yellow, fill=COLOR_YELLOW)

# 侧箱巨幅 "ORACLE" (加粗放大)
font_oracle = get_font(270)
d_side.text((60, 130), "ORACLE", font=font_oracle, fill=COLOR_WHITE)

# 右侧赞助商方阵: HRC / HONDA + Mobil 1
font_hrc = get_font(120)
font_honda = get_font(60)
d_side.text((1380, 145), "HRC", font=font_hrc, fill=COLOR_RED)
d_side.text((1380, 270), "HONDA", font=font_honda, fill=COLOR_WHITE)

# Mobil 1 经典色块标
d_side.text((1680, 165), "Mobil", font=get_font(95), fill=COLOR_WHITE)
d_side.text((1935, 150), "1", font=get_font(120), fill=COLOR_RED)

path_side = os.path.join(TEX_DIR, "decal_sidepod_oracle.png")
img_side.save(path_side)
print("Saved:", path_side)


# =========================================================================
# 2. 引擎罩巨幅金日冲刺牛 + Red Bull RACING (decal_engine_redbull_bull.png)
# =========================================================================
img_eng = Image.new("RGBA", (2048, 1024), (0, 0, 0, 0))
d_eng = ImageDraw.Draw(img_eng)

# 太阳圆盘 (饱满居左)
sun_cx, sun_cy, sun_r = 440, 500, 340
d_eng.ellipse([sun_cx - sun_r, sun_cy - sun_r, sun_cx + sun_r, sun_cy + sun_r], fill=COLOR_YELLOW)

# 冲刺公牛 (头部朝左前冲，加大比例)
draw_spanish_bull(d_eng, sun_cx + 80, sun_cy + 10, scale=2.35, flip_x=False)

# "Red Bull" 粗体红白双层立体标
font_rb = get_font(280)
# 红色立体阴影
d_eng.text((980, 190), "Red Bull", font=font_rb, fill=COLOR_RED)
# 白色高光文字
d_eng.text((970, 180), "Red Bull", font=font_rb, fill=COLOR_WHITE)

# "R A C I N G" 经典黄字
font_racing = get_font(130)
d_eng.text((980, 480), "R A C I N G", font=font_racing, fill=COLOR_YELLOW)

# 下方赞助商方阵: HONDA & BYBIT
font_sub = get_font(90)
d_eng.text((980, 660), "HONDA", font=font_sub, fill=COLOR_WHITE)
d_eng.text((1440, 660), "BYBIT", font=font_sub, fill=COLOR_YELLOW)

path_eng = os.path.join(TEX_DIR, "decal_engine_redbull_bull.png")
img_eng.save(path_eng)
print("Saved:", path_eng)


# =========================================================================
# 3. 机鼻专属流线涂装 + 维斯塔潘车号 1 (decal_nose_livery.png)
# =========================================================================
img_nose = Image.new("RGBA", (1024, 2048), (0, 0, 0, 0))
d_nose = ImageDraw.Draw(img_nose)

# 顶部双牛撞日圆徽 (前鼻尖处)
sun_n_cx, sun_n_cy, sun_n_r = 512, 260, 190
d_nose.ellipse([sun_n_cx - sun_n_r, sun_n_cy - sun_n_r, sun_n_cx + sun_n_r, sun_n_cy + sun_n_r], fill=COLOR_YELLOW)
# 左牛右冲，右牛左冲
draw_spanish_bull(d_nose, sun_n_cx - 95, sun_n_cy + 10, scale=1.25, flip_x=True)
draw_spanish_bull(d_nose, sun_n_cx + 95, sun_n_cy + 10, scale=1.25, flip_x=False)

# 冠军车号 "1" (维斯塔潘 Max Verstappen #1)
font_num = get_font(420)
d_nose.text((455, 475), "1", font=font_num, fill=COLOR_RED)
d_nose.text((440, 460), "1", font=font_num, fill=COLOR_WHITE)

# 纵向红黄赛车中轴流线
d_nose.rectangle([(500, 920), (514, 2020)], fill=COLOR_RED)
d_nose.rectangle([(514, 920), (524, 2020)], fill=COLOR_YELLOW)

# 醒目 ORACLE 标
font_nose_oracle = get_font(165)
d_nose.text((185, 960), "ORACLE", font=font_nose_oracle, fill=COLOR_WHITE)

# 赞助商方阵 (大字高对比)
font_sp = get_font(85)
d_nose.text((140, 1220), "HONDA", font=font_sp, fill=COLOR_WHITE)
d_nose.text((600, 1220), "BYBIT", font=font_sp, fill=COLOR_YELLOW)

d_nose.text((140, 1390), "Mobil 1", font=font_sp, fill=COLOR_WHITE)
d_nose.text((580, 1390), "PIRELLI", font=font_sp, fill=COLOR_RED)

d_nose.text((180, 1560), "TAG HEUER", font=font_sp, fill=COLOR_YELLOW)
d_nose.text((620, 1560), "SIEMENS", font=font_sp, fill=COLOR_WHITE)

path_nose = os.path.join(TEX_DIR, "decal_nose_livery.png")
img_nose.save(path_nose)
print("Saved:", path_nose)


# =========================================================================
# 4. 尾翼主片迎风面 ORACLE 标志 (decal_rearwing_front.png)
# =========================================================================
img_rw_f = Image.new("RGBA", (2048, 512), (0, 0, 0, 0))
d_rw_f = ImageDraw.Draw(img_rw_f)

# 左右侧红色切角装饰
d_rw_f.polygon([(0, 0), (320, 0), (0, 512)], fill=COLOR_RED)
d_rw_f.polygon([(2048, 0), (1728, 0), (2048, 512)], fill=COLOR_RED)

# 巨幅纯白 ORACLE
font_rw_oracle = get_font(310)
d_rw_f.text((380, 95), "ORACLE", font=font_rw_oracle, fill=COLOR_WHITE)

path_rw_f = os.path.join(TEX_DIR, "decal_rearwing_front.png")
img_rw_f.save(path_rw_f)
print("Saved:", path_rw_f)


# =========================================================================
# 5. 尾翼 DRS 翼片金黄 BYBIT 标 (decal_rearwing_bybit.png)
# =========================================================================
img_drs = Image.new("RGBA", (2048, 256), (0, 0, 0, 0))
d_drs = ImageDraw.Draw(img_drs)

font_drs = get_font(180)
d_drs.text((700, 25), "BYBIT", font=font_drs, fill=COLOR_YELLOW)
d_drs.rectangle([(0, 220), (2048, 256)], fill=COLOR_RED)

path_drs = os.path.join(TEX_DIR, "decal_rearwing_bybit.png")
img_drs.save(path_drs)
print("Saved:", path_drs)


# =========================================================================
# 6. 尾翼背面后视角度双层 Red Bull (decal_rearwing_back.png)
# =========================================================================
img_rw_b = Image.new("RGBA", (2048, 512), (0, 0, 0, 0))
d_rw_b = ImageDraw.Draw(img_rw_b)

# 左侧太阳圆盘 + 奔袭公牛
sun_b_cx, sun_b_cy, sun_b_r = 340, 256, 190
d_rw_b.ellipse([sun_b_cx - sun_b_r, sun_b_cy - sun_b_r, sun_b_cx + sun_b_r, sun_b_cy + sun_b_r], fill=COLOR_YELLOW)
draw_spanish_bull(d_rw_b, sun_b_cx + 40, sun_b_cy + 5, scale=1.30, flip_x=False)

# 右侧 Red Bull 双层字样
font_rwb = get_font(230)
d_rw_b.text((610, 125), "Red Bull", font=font_rwb, fill=COLOR_RED)
d_rw_b.text((600, 115), "Red Bull", font=font_rwb, fill=COLOR_YELLOW)

path_rw_b = os.path.join(TEX_DIR, "decal_rearwing_back.png")
img_rw_b.save(path_rw_b)
print("Saved:", path_rw_b)


# =========================================================================
# 7. Halo 顶部钛合金保护环 ORACLE 贴纸 (decal_halo_oracle.png)
# =========================================================================
img_halo = Image.new("RGBA", (1024, 256), (0, 0, 0, 0))
d_halo = ImageDraw.Draw(img_halo)

font_halo = get_font(130)
d_halo.text((250, 60), "ORACLE", font=font_halo, fill=COLOR_WHITE)
d_halo.ellipse([790, 95, 845, 150], fill=COLOR_RED)

path_halo = os.path.join(TEX_DIR, "decal_halo_oracle.png")
img_halo.save(path_halo)
print("Saved:", path_halo)


# =========================================================================
# 8. 翼端板垂直赞助商标 (decal_endplate_mobil1.png)
# =========================================================================
img_ep = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
d_ep = ImageDraw.Draw(img_ep)

# Mobil 1 醒目标志
d_ep.text((140, 140), "Mobil", font=get_font(200), fill=COLOR_WHITE)
d_ep.text((720, 115), "1", font=get_font(250), fill=COLOR_RED)

# 分隔红线
d_ep.rectangle([(100, 420), (924, 440)], fill=COLOR_RED)

# PIRELLI 标志
d_ep.text((140, 490), "PIRELLI", font=get_font(170), fill=COLOR_YELLOW)

# TAG HEUER
d_ep.text((140, 730), "TAG HEUER", font=get_font(125), fill=COLOR_WHITE)

path_ep = os.path.join(TEX_DIR, "decal_endplate_mobil1.png")
img_ep.save(path_ep)
print("Saved:", path_ep)

print("=== ALL 8 RED BULL DECALS RE-GENERATED WITH MAXIMUM RACING CONTRAST ===")
