# -*- coding: utf-8 -*-
"""生成 Mercedes-AMG PETRONAS 风格贴花（透明底 PNG）"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = r"D:\项目session\blender-supercar\textures"
FONTS = r"C:\Windows\Fonts"
os.makedirs(OUT, exist_ok=True)

PETROL = (0, 210, 190, 255)      # Petronas 青绿
WHITE = (255, 255, 255, 255)
SILVER = (198, 202, 208, 255)
BLACK = (10, 11, 13, 255)

def font(name, size):
    for f in (name, "arialbd.ttf", "seguisb.ttf", "arial.ttf"):
        p = os.path.join(FONTS, f)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def star(d, cx, cy, r, color=WHITE, w=None):
    """奔驰三叉星简化图形"""
    w = w or max(3, r // 12)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=w)
    import math
    for a in (90, 210, 330):
        rad = math.radians(a)
        d.line([cx, cy, cx + r * 0.92 * math.cos(rad), cy - r * 0.92 * math.sin(rad)], fill=color, width=w)

# ---------------- 1. 侧箱贴花 ----------------
W, H = 2048, 640
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
# 青绿斜条（右上→左下）
d.polygon([(W * 0.52, 0), (W * 0.66, 0), (W * 0.40, H), (W * 0.26, H)], fill=PETROL)
d.polygon([(W * 0.72, 0), (W * 0.78, 0), (W * 0.52, H), (W * 0.46, H)], fill=PETROL)
d.text((150, 150), "PETRONAS", font=font("arialbd.ttf", 250), fill=WHITE)
d.text((160, 430), "TeamViewer", font=font("seguisb.ttf", 96), fill=WHITE)
d.text((900, 440), "Snapdragon", font=font("seguisb.ttf", 88), fill=SILVER)
img.save(os.path.join(OUT, "merc_sidepod.png"))

# ---------------- 2. 引擎盖贴花（数字 + 星徽 + 赞助）----------------
W, H = 2048, 1024
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.text((120, 60), "12", font=font("arialbd.ttf", 420), fill=WHITE)
star(d, 1250, 300, 200)
d.text((1050, 560), "Microsoft", font=font("seguisb.ttf", 120), fill=WHITE)
d.text((1080, 720), "SOLERA", font=font("arialbd.ttf", 96), fill=SILVER)
d.text((150, 640), "Mercedes-AMG", font=font("arialbd.ttf", 130), fill=SILVER)
d.text((150, 800), "PETRONAS", font=font("arialbd.ttf", 110), fill=PETROL)
img.save(os.path.join(OUT, "merc_engine.png"))

# ---------------- 3. 鼻锥涂装（银色渐变 + 青条）----------------
W, H = 1024, 2048
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
# 银色渐变块（前端）
for i in range(H):
    a = int(190 * max(0.0, 1.0 - i / (H * 0.75)))
    if a > 0:
        d.line([(0, i), (W, i)], fill=(200, 204, 210, a))
d.polygon([(W * 0.30, H * 0.30), (W * 0.42, H * 0.30), (W * 0.34, H), (W * 0.22, H)], fill=PETROL)
d.polygon([(W * 0.52, H * 0.55), (W * 0.60, H * 0.55), (W * 0.52, H), (W * 0.44, H)], fill=PETROL)
star(d, W * 0.5, H * 0.16, 110)
img.save(os.path.join(OUT, "merc_nose.png"))

# ---------------- 4. Halo 贴花 ----------------
W, H = 1024, 256
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.text((60, 40), "PETRONAS", font=font("arialbd.ttf", 150), fill=WHITE)
d.text((720, 70), "Mercedes", font=font("seguisb.ttf", 90), fill=PETROL)
img.save(os.path.join(OUT, "merc_halo.png"))

# ---------------- 5. 尾翼贴花 ----------------
W, H = 2048, 512
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rectangle([0, 150, W, 200], fill=PETROL)
d.text((120, 20), "PETRONAS", font=font("arialbd.ttf", 170), fill=WHITE)
d.text((1180, 60), "IWC", font=font("arialbd.ttf", 150), fill=SILVER)
d.text((1450, 70), "Ineos", font=font("seguisb.ttf", 110), fill=WHITE)
img.save(os.path.join(OUT, "merc_rearwing.png"))

# ---------------- 6. 尾翼端板（青色条 + 白字）----------------
W, H = 1024, 1024
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rectangle([0, 0, W, 120], fill=PETROL)
d.text((90, 300), "PETRONAS", font=font("arialbd.ttf", 130), fill=WHITE)
d.text((120, 520), "Mercedes", font=font("seguisb.ttf", 110), fill=SILVER)
d.text((120, 700), "CrowdStrike", font=font("seguisb.ttf", 96), fill=WHITE)
img.save(os.path.join(OUT, "merc_endplate.png"))

# 预览拼图
prev = Image.new("RGBA", (1100, 620), (18, 18, 20, 255))
tiles = [("merc_sidepod.png", (0, 0, 1000, 312)), ("merc_engine.png", (0, 316, 700, 300))]
for name, box in tiles:
    im = Image.open(os.path.join(OUT, name)).convert("RGBA")
    im.thumbnail((box[2], box[3]))
    prev.alpha_composite(im, (box[0] + 10, box[1] + 4))
prev.convert("RGB").save(os.path.join(OUT, "_merc_preview.png"))
print("decal set generated:", sorted(f for f in os.listdir(OUT) if f.startswith("merc_")))