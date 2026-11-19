# -*- coding: utf-8 -*-
"""
High-Resolution Realistic Asset Generator:
1. Pirelli P-Zero Formula 1 Sidewall Texture with Clockwise Radial Typography
2. Modern F1 Steering Wheel 4.3-inch Telemetry LCD Dashboard Display
Author: TalonX (Visual Communication Design & F1 Technical Precision)
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

TEX_DIR = r"D:\项目session\blender-supercar\textures"
os.makedirs(TEX_DIR, exist_ok=True)

FONT_PATH = r"C:\Windows\Fonts\bahnschrift.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"

def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()

# =========================================================================
# 1. 倍耐力 18寸 P-ZERO 软胎 (C3/C4 Soft) 环形胎侧贴图 (2048 x 2048)
# =========================================================================
size = 2048
img_tire = Image.new("RGBA", (size, size), (0, 0, 0, 0))
d_tire = ImageDraw.Draw(img_tire)
cx, cy = size // 2, size // 2

R_OUTER = 920  # 胎肩边缘
R_INNER = 630  # 轮辋边缘

COLOR_RED = (235, 15, 0, 255)       # Pirelli Soft Racing Crimson
COLOR_YELLOW = (255, 215, 0, 255)   # Pirelli Corporate Golden Yellow
COLOR_WHITE = (255, 255, 255, 255)  # Sidewall Lettering Pure White
COLOR_DARK_GREY = (45, 48, 55, 255) # Rubber Grooves

# A. 软胎标志性双重外圈红色环线 (Pirelli Soft Racing Stripes)
for w in range(16):
    r_str1 = R_OUTER - 18 - w
    d_tire.arc([cx - r_str1, cy - r_str1, cx + r_str1, cy + r_str1], 0, 360, fill=COLOR_RED)

for w in range(10):
    r_str2 = R_INNER + 22 + w
    d_tire.arc([cx - r_str2, cy - r_str2, cx + r_str2, cy + r_str2], 0, 360, fill=COLOR_RED)

# B. 细微径向橡胶排气槽纹理 (120组微细刻度线)
for i in range(120):
    ang = i * (360.0 / 120.0)
    rad = math.radians(ang)
    x1 = cx + math.cos(rad) * (R_INNER + 36)
    y1 = cy + math.sin(rad) * (R_INNER + 36)
    x2 = cx + math.cos(rad) * (R_INNER + 52)
    y2 = cy + math.sin(rad) * (R_INNER + 52)
    d_tire.line([(x1, y1), (x2, y2)], fill=COLOR_DARK_GREY, width=2)

def draw_radial_text_clockwise(base_img, text, font, radius, center_deg, fill):
    """
    顺时针沿圆周排列字符：
    字符从左到右阅读，字头朝外(径向向外)，字符切线方向沿顺时针排列
    在图像坐标系下：x = cx + r*cos(a), y = cy + r*sin(a)，a增加即顺时针
    """
    total_w = sum(font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in text)
    spacing = 1.15
    span_deg = (total_w * spacing / radius) * (180.0 / math.pi)
    start_deg = center_deg - (span_deg / 2.0)
    
    cur_deg = start_deg
    for ch in text:
        ch_w = font.getbbox(ch)[2] - font.getbbox(ch)[0]
        step_deg = (ch_w * spacing / radius) * (180.0 / math.pi)
        mid_deg = cur_deg + (step_deg / 2.0)
        rad = math.radians(mid_deg)
        
        tx = cx + math.cos(rad) * radius
        ty = cy + math.sin(rad) * radius
        
        # 字符字头朝向圆外：字符的向上矢量应该是 (cos(rad), sin(rad))
        # 旋转角度 = mid_deg + 90
        rot_angle = mid_deg + 90.0
        
        pad = int(font.size * 1.8)
        ch_canvas = Image.new("RGBA", (pad, pad), (0, 0, 0, 0))
        ch_d = ImageDraw.Draw(ch_canvas)
        bbox = font.getbbox(ch)
        ch_h = bbox[3] - bbox[1]
        ch_d.text((pad // 2 - ch_w // 2, pad // 2 - ch_h // 2), ch, font=font, fill=fill)
        
        rot_ch = ch_canvas.rotate(-rot_angle, resample=Image.Resampling.BICUBIC, expand=False)
        base_img.alpha_composite(rot_ch, (int(tx - pad // 2), int(ty - pad // 2)))
        cur_deg += step_deg

font_brand = get_font(130)
font_sub = get_font(60)

# 顶部 (-90°) 顺时针排列 "P ZERO"
draw_radial_text_clockwise(img_tire, "P ZERO", font_brand, radius=770, center_deg=-90, fill=COLOR_WHITE)

# 底部 (90°) 顺时针排列 "P ZERO"
draw_radial_text_clockwise(img_tire, "P ZERO", font_brand, radius=770, center_deg=90, fill=COLOR_WHITE)

# 右侧 (0°) 顺时针排列 "PIRELLI"
draw_radial_text_clockwise(img_tire, "PIRELLI", font_brand, radius=770, center_deg=0, fill=COLOR_YELLOW)

# 左侧 (180°) 顺时针排列 "PIRELLI"
draw_radial_text_clockwise(img_tire, "PIRELLI", font_brand, radius=770, center_deg=180, fill=COLOR_YELLOW)

# 四个对角点缀专业赛车标识
draw_radial_text_clockwise(img_tire, "F1 18-INCH", font_sub, radius=695, center_deg=-45, fill=COLOR_WHITE)
draw_radial_text_clockwise(img_tire, "SOFT C4", font_sub, radius=695, center_deg=45, fill=COLOR_RED)
draw_radial_text_clockwise(img_tire, "FIA HOMOLOGATED", font_sub, radius=695, center_deg=135, fill=COLOR_WHITE)
draw_radial_text_clockwise(img_tire, "ORBR #1", font_sub, radius=695, center_deg=-135, fill=COLOR_YELLOW)

# 动态旋转动平衡标记 (Red & Yellow Balancing Tape)
d_tire.rectangle([cx + 740, cy - 25, cx + 795, cy + 25], fill=COLOR_RED)
d_tire.rectangle([cx - 795, cy - 25, cx - 740, cy + 25], fill=COLOR_YELLOW)

tire_path = os.path.join(TEX_DIR, "tire_sidewall_pirelli.png")
img_tire.save(tire_path)
print("Saved Flawless Pirelli Tire Sidewall:", tire_path)

# =========================================================================
# 2. 现代 F1 赛车 4.3寸 LCD 遥测方向盘仪表盘 (1024 x 512)
# =========================================================================
img_dash = Image.new("RGBA", (1024, 512), (10, 12, 16, 255))
d_dash = ImageDraw.Draw(img_dash)

# A. 顶部换挡指示 LED 阵列 (Shift Indicator LEDs: 5 Green, 5 Red, 5 Blue)
led_colors = [
    (0, 240, 80, 255)] * 5 + [
    (250, 20, 20, 255)] * 5 + [
    (30, 150, 255, 255)] * 5

led_start_x = 100
for i in range(15):
    lx = led_start_x + (i * 56)
    ly = 35
    d_dash.ellipse([lx - 18, ly - 18, lx + 18, ly + 18], fill=(22, 26, 32, 255))
    d_dash.ellipse([lx - 14, ly - 14, lx + 14, ly + 14], fill=led_colors[i])

# B. 核心巨大当前档位 "7"
f_gear = get_font(210)
d_dash.text((455, 120), "7", font=f_gear, fill=(255, 255, 255, 255))
d_dash.text((485, 325), "GEAR", font=get_font(32), fill=(140, 150, 160, 255))

# C. 左侧时速 "318" & 转速条
f_speed = get_font(120)
d_dash.text((120, 150), "318", font=f_speed, fill=(255, 255, 255, 255))
d_dash.text((125, 265), "KM/H", font=get_font(36), fill=(0, 200, 255, 255))
d_dash.text((125, 320), "11,850 RPM", font=get_font(42), fill=(255, 204, 0, 255))

# D. 右侧 Delta 圈速与单圈排名
d_dash.rectangle([(680, 135), (940, 235)], fill=(0, 150, 65, 255))
d_dash.text((700, 145), "-0.248", font=get_font(75), fill=(255, 255, 255, 255))
d_dash.text((700, 250), "DELTA (LAP 42)", font=get_font(34), fill=(160, 255, 180, 255))

d_dash.text((700, 310), "P1  VER", font=get_font(52), fill=(255, 210, 0, 255))
d_dash.text((880, 320), "L42", font=get_font(38), fill=(255, 255, 255, 255))

# E. 底部遥测参数方阵: ERS, BIAS, DIFF, 胎温
d_dash.line([(60, 385), (964, 385)], fill=(45, 55, 65, 255), width=2)

f_telem = get_font(36)
d_dash.text((90, 420), "ERS: 86%", font=f_telem, fill=(0, 220, 255, 255))
d_dash.text((320, 420), "BB: 55.5%", font=f_telem, fill=(255, 255, 255, 255))
d_dash.text((560, 420), "DIFF: 4", font=f_telem, fill=(255, 204, 0, 255))
d_dash.text((770, 420), "TYRES: 102°C", font=f_telem, fill=(240, 80, 80, 255))

dash_path = os.path.join(TEX_DIR, "steering_display.png")
img_dash.save(dash_path)
print("Saved Realistic F1 Steering Telemetry LCD:", dash_path)

print("=== ALL ASSETS UPDATED PERFECTLY ===")
