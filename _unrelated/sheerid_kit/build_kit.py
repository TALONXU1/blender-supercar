#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SheerID 材料生成套件
产出：
  out/enrollment_letter.docx      可编辑在读证明信（Word）
  out/enrollment_letter_raw.png   300dpi 渲染稿
  out/enrollment_letter.jpg       扫描质感稿（直传）
  out/id_front_raw.png / id_back_raw.png
  out/id_front.jpg / id_back.jpg  扫描质感稿
  out/id_combined.jpg             正反拼合
用法：改 fields.json（或直接改下面 CFG）后 python build_kit.py
"""
import os, json, math, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "out")
os.makedirs(OUT, exist_ok=True)
FONT_DIR = "C:/Windows/Fonts"

# ----------------------------------------------------------------------------
# 字段配置：提交前必须与 SheerID 表单里填的一字不差
# ----------------------------------------------------------------------------
CFG = {
    "school_name":    "Northgate Community College",
    "school_short":   "NORTHGATE",
    "school_color":   [18, 52, 96],       # 学校主色 RGB
    "school_addr":    "1400 Northgate Parkway, Springfield, IL 62704",
    "school_phone":   "Tel (217) 555-0182",
    "school_web":     "www.northgate.edu",
    "school_email":   "registrar@northgate.edu",

    "student_name":   "ALEX R. MORGAN",
    "student_id":     "NCC-2026-08817",
    "program":        "Associate of Applied Science in Computer Information Systems",
    "faculty":        "Division of Business & Information Technology",
    "level":          "full-time undergraduate",
    "term":           "Fall 2026",
    "term_start":     "August 24, 2026",
    "term_end":       "December 11, 2026",
    "expected_grad":  "May 2028",
    "letter_date":    "November 10, 2026",
    "valid_thru":     "08/2028",
    "issue_date":     "08/2026",
    "registrar":      "D. Whitfield",
    "registrar_title":"University Registrar",
    "ref_prefix":     "NCC-REG",

    "photo":          "",                 # 可选：证件照路径，留空用剪影
    "dob":            "03/14/2004",
}


def load_cfg():
    p = os.path.join(BASE, "fields.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            CFG.update(json.load(f))
    return CFG


# ----------------------------------------------------------------------------
# 字体
# ----------------------------------------------------------------------------
_FCACHE = {}


def F(cands, size):
    key = (tuple(cands), size)
    if key in _FCACHE:
        return _FCACHE[key]
    for c in cands:
        p = os.path.join(FONT_DIR, c)
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            _FCACHE[key] = f
            return f
    f = ImageFont.load_default()
    _FCACHE[key] = f
    return f


SERIF      = lambda s: F(["times.ttf", "georgia.ttf", "arial.ttf"], s)
SERIF_B    = lambda s: F(["timesbd.ttf", "georgiab.ttf", "arialbd.ttf"], s)
SERIF_I    = lambda s: F(["timesi.ttf", "georgiai.ttf", "ariali.ttf"], s)
SANS       = lambda s: F(["arial.ttf", "calibri.ttf"], s)
SANS_B     = lambda s: F(["arialbd.ttf", "calibrib.ttf"], s)
MONO       = lambda s: F(["cour.ttf", "consola.ttf", "arial.ttf"], s)
MONO_B     = lambda s: F(["courbd.ttf", "consolab.ttf", "arialbd.ttf"], s)


def tl(draw, text, font):
    return draw.textlength(text, font=font)


def monogram(name):
    parts = [w for w in name.replace(",", "").split() if w and w[0].isupper()]
    return "".join(p[0] for p in parts)[:3] or "UNI"


# ----------------------------------------------------------------------------
# 纸张纹理 / 扫描质感
# ----------------------------------------------------------------------------
def paper_base(w, h, tint=(255, 254, 250)):
    a = np.ones((h, w, 3), dtype=np.float32) * np.array(tint, dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    grain = np.random.normal(0, 1.6, (h, w, 1))
    fiber = (np.sin(xx / 3.1) * 0.7 + np.sin(yy / 5.7) * 0.5)[..., None]
    a = a + grain + fiber
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def scan_finish(img, out, angle=0.55, noise=4.2, blur=0.55, quality=84,
                dpi=(300, 300), tint=(1.0, 0.998, 0.982)):
    img = img.convert("RGB")
    w, h = img.size
    rot = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(252, 251, 247))
    a = np.asarray(rot).astype(np.float32) * np.array(tint, dtype=np.float32)
    a += np.random.normal(0, noise, a.shape)
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2.0, h / 2.0
    r = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2)
    vig = 1.0 - 0.09 * np.clip(r - 0.45, 0, 1)
    a *= vig[..., None]
    out_img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if blur:
        out_img = out_img.filter(ImageFilter.GaussianBlur(blur))
    out_img.save(out, "JPEG", quality=quality, dpi=dpi, subsampling=1)
    return out


# ----------------------------------------------------------------------------
# 圆形公章（沿弧排字）
# ----------------------------------------------------------------------------
def draw_signature(img, x, y, text, size=126, color=(22, 26, 42), angle=-3.2):
    """手写体签名：脚本字体 + 轻微倾斜 + 复写叠墨，模拟钢笔压力"""
    f = F(["FRSCRIPT.TTF", "segoesc.ttf", "LHANDW.ttf", "Inkfree.ttf"], size)
    pad = size * 2
    tmp = Image.new("RGBA", (int(size * len(text) * 1.3 + pad), int(size * 2.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.text((pad / 2, tmp.size[1] * 0.55), text, font=f, fill=color + (232,), anchor="lm")
    bb = tmp.getbbox()
    if not bb:
        return
    tmp = tmp.crop(bb)
    # 复写叠墨
    ink = Image.new("RGBA", (tmp.size[0] + 3, tmp.size[1] + 3), (0, 0, 0, 0))
    ink.alpha_composite(tmp, (0, 0))
    t2 = tmp.copy()
    t2.putalpha(t2.split()[3].point(lambda v: int(v * 0.42)))
    ink.alpha_composite(t2, (2, 2))
    ink = ink.rotate(angle, resample=Image.BICUBIC, expand=True)
    img.paste(ink, (int(x), int(y)), ink)


def make_seal(size, school, center_text, color=(186, 26, 42), alpha=205,
              sub_text="OFFICIAL SEAL"):
    S = size * 4  # 超采样
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2
    ring_w = int(S * 0.022)
    d.ellipse([c - S * 0.47, c - S * 0.47, c + S * 0.47, c + S * 0.47],
              outline=color + (alpha,), width=ring_w)
    d.ellipse([c - S * 0.430, c - S * 0.430, c + S * 0.430, c + S * 0.430],
              outline=color + (alpha,), width=max(2, ring_w // 3))

    # 上弧主文字：字符按弧长均匀分布，不按序号均分角度
    text = school.upper()
    r_arc = S * 0.372
    # 字号随字数自适应，保证首尾不重叠
    target_arc = math.pi * 0.92 * r_arc          # 可用弧长
    fsize = max(10, int(min(S * 0.078, target_arc / max(1, len(text)) * 1.28)))
    f_arc = SERIF_B(fsize)
    widths = [max(1e-6, tl(d, ch, f_arc)) for ch in text]
    total_w = sum(widths) + fsize * 0.16 * max(0, len(text) - 1)
    arc_len = total_w
    start_a = -math.degrees(arc_len / 2.0 / r_arc)
    acc = 0.0
    for ch, w in zip(text, widths):
        a = start_a + math.degrees((acc + w / 2.0) / r_arc)
        acc += w + fsize * 0.16
        if ch == " ":
            continue
        rad = math.radians(a)
        x = c + r_arc * math.sin(rad)
        y = c - r_arc * math.cos(rad)
        pad = int(fsize * 2.2)
        tmp = Image.new("RGBA", (pad, pad), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        td.text((pad / 2, pad / 2), ch, font=f_arc, fill=color + (alpha,), anchor="mm")
        tmp = tmp.rotate(-a, resample=Image.BICUBIC, expand=False)
        img.alpha_composite(tmp, (int(x - pad / 2), int(y - pad / 2)))

    # 中间主文字 + REGISTRAR
    d = ImageDraw.Draw(img)
    f_mid = SERIF_B(int(S * 0.092))
    d.text((c, c - S * 0.045), center_text, font=f_mid, fill=color + (alpha,), anchor="mm")
    f_sm = SANS_B(int(S * 0.036))
    d.text((c, c + S * 0.070), "REGISTRAR", font=f_sm, fill=color + (alpha,), anchor="mm")
    for sgn in (-1, 1):
        dx = c + sgn * S * 0.300
        dy = c + S * 0.070
        d.polygon([(dx, dy - S * 0.016), (dx + S * 0.012, dy),
                   (dx, dy + S * 0.016), (dx - S * 0.012, dy)], fill=color + (alpha,))
    # 下弧文字改为水平排，避免倒字
    f_bot = SANS_B(int(S * 0.034))
    d.text((c, c + S * 0.285), sub_text, font=f_bot, fill=color + (alpha,), anchor="mm")
    d.line([(c - S * 0.235, c + S * 0.285), (c - S * 0.135, c + S * 0.285)],
           fill=color + (alpha,), width=max(1, int(S * 0.006)))
    d.line([(c + S * 0.135, c + S * 0.285), (c + S * 0.235, c + S * 0.285)],
           fill=color + (alpha,), width=max(1, int(S * 0.006)))

    return img.resize((size, size), Image.LANCZOS)


# ----------------------------------------------------------------------------
# 在读证明信 A4 300dpi
# ----------------------------------------------------------------------------
def build_letter(cfg):
    W, H = 2480, 3508
    M = 250
    col = tuple(cfg["school_color"])
    img = paper_base(W, H)
    d = ImageDraw.Draw(img)

    y = 210
    # 校名
    f_school = SERIF_B(96)
    school = cfg["school_name"]
    d.text((W / 2, y), school, font=f_school, fill=col, anchor="ma")
    y += 118
    f_addr = SERIF(38)
    d.text((W / 2, y), cfg["school_addr"], font=f_addr, fill=(70, 70, 70), anchor="ma")
    y += 52
    line2 = "  |  ".join([cfg["school_phone"], cfg["school_web"], cfg["school_email"]])
    d.text((W / 2, y), line2, font=f_addr, fill=(70, 70, 70), anchor="ma")
    y += 62
    d.line([(M, y), (W - M, y)], fill=col, width=5)
    d.line([(M, y + 11), (W - M, y + 11)], fill=col, width=2)

    # 参考编号 + 日期
    y += 90
    ref = "%s-%s" % (cfg["ref_prefix"],
                     hashlib.md5((cfg["student_id"] + cfg["term"]).encode()).hexdigest()[:8].upper())
    f_small = SERIF(34)
    d.text((M, y), "Ref: %s" % ref, font=f_small, fill=(90, 90, 90))
    d.text((W - M, y), cfg["letter_date"], font=SERIF(40), fill=(30, 30, 30), anchor="ra")

    # 标题
    y += 130
    d.text((M, y), "TO WHOM IT MAY CONCERN", font=SERIF_B(46), fill=(20, 20, 20))
    y += 96
    d.text((M, y), "CERTIFICATE OF ENROLLMENT", font=SERIF_B(52), fill=col)
    d.line([(M, y + 78), (M + 1180, y + 78)], fill=col, width=3)

    # 正文
    y += 165
    f_body = SERIF(44)
    lead = 68
    maxw = W - 2 * M

    def para(text, indent=0, after=34, font=None, justify_line=None):
        nonlocal y
        font = font or f_body
        words = text.split()
        lines, cur = [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if tl(d, t, font) <= maxw - indent:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        for i, ln in enumerate(lines):
            d.text((M + indent, y), ln, font=font, fill=(25, 25, 25))
            y += lead
        y += after

    para("This letter is issued by the Office of the Registrar of %s in response to a "
         "request for verification of enrollment status." % cfg["school_name"])

    para("This is to certify that %s, Student Identification Number %s, is currently "
         "enrolled as a %s student in the %s at %s."
         % (cfg["student_name"], cfg["student_id"], cfg["level"],
            cfg["program"], cfg["school_name"]))

    para("The student is registered for the %s term, which began on %s and is scheduled "
         "to conclude on %s. The student's current academic status is Active / In Good "
         "Standing, and the student is carrying a full-time course load."
         % (cfg["term"], cfg["term_start"], cfg["term_end"]))

    para("The student is a candidate for graduation in %s. The academic programme is "
         "administered by the %s." % (cfg["expected_grad"], cfg["faculty"]))

    para("This certification is issued at the request of the student for purposes of "
         "third-party verification. Questions concerning the authenticity of this "
         "document may be directed to the Office of the Registrar at %s."
         % cfg["school_email"], after=90)

    # 落款：左对齐签名块，公章压在签名线右端
    y += 50
    sx = M
    d.text((sx, y), "Sincerely,", font=f_body, fill=(25, 25, 25))
    y += 210
    sig_y = y
    d.line([(sx, sig_y), (sx + 600, sig_y)], fill=(40, 40, 40), width=3)
    draw_signature(img, sx + 26, sig_y - 132, cfg["registrar"], size=132)
    y += 26
    d.text((sx, y), cfg["registrar"], font=SERIF_B(46), fill=(20, 20, 20))
    y += 62
    d.text((sx, y), cfg["registrar_title"], font=SERIF(40), fill=(60, 60, 60))
    y += 52
    d.text((sx, y), "Office of the Registrar", font=SERIF(40), fill=(60, 60, 60))
    y += 52
    d.text((sx, y), cfg["school_name"], font=SERIF(40), fill=(60, 60, 60))

    # 公章：签名块右侧，轻微倾斜 + 低透明度，只压白区不压正文
    seal_size = 470
    seal = make_seal(seal_size, cfg["school_name"], cfg["valid_thru"], alpha=200)
    seal = seal.rotate(-7, resample=Image.BICUBIC, expand=False)
    img.paste(seal, (int(sx + 700), int(sig_y - seal_size * 0.62)), seal)

    # 页脚
    fy = H - 300
    d.line([(M, fy), (W - M, fy)], fill=(180, 180, 180), width=2)
    d.text((M, fy + 26),
           "Issued by the Office of the Registrar. Any alteration renders this document void.",
           font=SERIF(30), fill=(110, 110, 110))
    d.text((M, fy + 72),
           "%s  ·  %s  ·  Document Ref %s" % (cfg["school_name"], cfg["school_web"], ref),
           font=SERIF(30), fill=(110, 110, 110))

    raw = os.path.join(OUT, "enrollment_letter_raw.png")
    img.save(raw, dpi=(300, 300))
    jpg = os.path.join(OUT, "enrollment_letter.jpg")
    scan_finish(img, jpg, angle=0.42, noise=3.6, blur=0.5, quality=86)
    return raw, jpg


# ----------------------------------------------------------------------------
# 学生证 正/反 CR80 @300dpi = 1012 x 638
# ----------------------------------------------------------------------------
CW, CH = 1012, 638


def _barcode(d, x, y, w, h, seed_str, color=(20, 20, 20)):
    hh = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    cx = x
    while cx < x + w:
        hh = (hh * 1103515245 + 12345) & 0x7FFFFFFF
        bw = 2 + (hh >> 8) % 5
        if cx + bw > x + w:
            bw = x + w - cx
        if (hh >> 3) % 2 == 0:
            d.rectangle([cx, y, cx + bw, y + h], fill=color)
        cx += bw + 2 + (hh >> 5) % 3


def _portrait(size, path=None):
    w, h = size
    if path and os.path.exists(path):
        im = Image.open(path).convert("RGB")
        # cover crop
        s = max(w / im.width, h / im.height)
        im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
        left = (im.width - w) // 2
        top = int((im.height - h) * 0.35)
        return im.crop((left, top, left + w, top + h))
    # 剪影占位
    im = Image.new("RGB", (w, h), (206, 210, 216))
    d = ImageDraw.Draw(im)
    d.ellipse([w * 0.33, h * 0.16, w * 0.67, h * 0.50], fill=(158, 164, 172))
    d.pieslice([w * 0.14, h * 0.54, w * 0.86, h * 1.20], 180, 360, fill=(158, 164, 172))
    return im


def build_id(cfg):
    col = tuple(cfg["school_color"])
    light = tuple(min(255, int(c * 0.35 + 170)) for c in col)
    ink = (26, 28, 32)

    # ---------------- 正面 ----------------
    front = paper_base(CW, CH, tint=(252, 252, 250))
    d = ImageDraw.Draw(front)
    # 顶部色带
    d.rectangle([0, 0, CW, 96], fill=col)
    d.text((34, 26), cfg["school_name"].upper(), font=SANS_B(30), fill=(255, 255, 255))
    d.text((34, 62), "STUDENT IDENTIFICATION CARD", font=SANS(17), fill=(200, 214, 232))
    # 校徽占位圆
    d.ellipse([CW - 96, 14, CW - 22, 88], outline=(255, 255, 255), width=3)
    d.text((CW - 59, 51), monogram(cfg["school_name"]), font=SANS_B(22),
           fill=(255, 255, 255), anchor="mm")

    # 照片
    pw, ph = 226, 286
    px, py = 44, 138
    front.paste(_portrait((pw, ph), cfg.get("photo") or None), (px, py))
    d.rectangle([px, py, px + pw, py + ph], outline=(160, 166, 174), width=2)

    # 字段
    fx = px + pw + 46
    fy = 142
    fields = [
        ("NAME", cfg["student_name"], SANS_B(30)),
        ("STUDENT ID", cfg["student_id"], MONO_B(30)),
        ("PROGRAM", cfg["program"], SANS(19)),
        ("VALID THRU", cfg["valid_thru"], MONO_B(26)),
    ]
    for label, val, font in fields:
        d.text((fx, fy), label, font=SANS_B(13), fill=(120, 126, 134))
        fy += 20
        # 手动换行
        maxw = CW - fx - 40
        words = str(val).split()
        lines, cur = [], ""
        for w_ in words:
            t = (cur + " " + w_).strip()
            if tl(d, t, font) <= maxw:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w_
        if cur:
            lines.append(cur)
        for ln in lines[:2]:
            d.text((fx, fy), ln, font=font, fill=ink)
            fy += font.size + 8
        fy += 12

    # 底部条码
    _barcode(d, 44, CH - 108, CW - 250, 54, cfg["student_id"])
    d.text((CW - 190, CH - 100), cfg["student_id"], font=MONO(20), fill=ink)
    d.text((CW - 190, CH - 76), "ISSUED %s" % cfg["issue_date"], font=SANS(14), fill=(120, 126, 134))
    d.rectangle([0, CH - 34, CW, CH], fill=light)
    d.text((44, CH - 26), "PROPERTY OF %s · NON-TRANSFERABLE"
           % cfg["school_name"].upper(), font=SANS(12), fill=(80, 86, 94))

    # ---------------- 背面 ----------------
    back = paper_base(CW, CH, tint=(251, 251, 249))
    db = ImageDraw.Draw(back)
    db.rectangle([0, 0, CW, 118], fill=(28, 28, 30))          # 磁条
    db.rectangle([0, 118, CW, 126], fill=col)
    db.text((44, 150), cfg["school_name"], font=SANS_B(26), fill=ink)
    db.text((44, 184), cfg["school_addr"], font=SANS(17), fill=(80, 86, 94))
    db.text((44, 210), cfg["school_phone"], font=SANS(17), fill=(80, 86, 94))
    db.text((44, 252), "TERM OF ISSUE", font=SANS_B(13), fill=(120, 126, 134))
    db.text((44, 272), "%s  (%s – %s)" % (cfg["term"], cfg["term_start"], cfg["term_end"]),
            font=SANS(19), fill=ink)
    _barcode(db, 44, 330, CW - 290, 62, cfg["student_id"] + "B")
    db.text((CW - 216, 340), cfg["student_id"], font=MONO(18), fill=ink)
    db.text((CW - 216, 366), "DOB %s" % cfg["dob"], font=MONO(16), fill=ink)
    # 磁条编码带模拟
    for i in range(26):
        x = 44 + i * 23
        db.line([(x, 430), (x + 12, 430)], fill=(90, 92, 96), width=2)
    db.text((44, 448), "IF FOUND, PLEASE RETURN TO THE OFFICE OF THE REGISTRAR.",
            font=SANS(15), fill=(60, 64, 70))
    db.text((44, 472), "This card remains the property of the College and must be "
                       "surrendered on request.", font=SANS(13), fill=(110, 116, 124))
    db.rectangle([0, CH - 34, CW, CH], fill=light)
    db.text((44, CH - 26), cfg["school_web"] + "/registrar", font=SANS(12), fill=(80, 86, 94))

    f_raw = os.path.join(OUT, "id_front_raw.png")
    b_raw = os.path.join(OUT, "id_back_raw.png")
    front.save(f_raw, dpi=(300, 300))
    back.save(b_raw, dpi=(300, 300))

    f_jpg = os.path.join(OUT, "id_front.jpg")
    b_jpg = os.path.join(OUT, "id_back.jpg")
    scan_finish(front, f_jpg, angle=0.35, noise=4.0, blur=0.5, quality=85, dpi=(300, 300))
    scan_finish(back, b_jpg, angle=-0.28, noise=3.8, blur=0.5, quality=85, dpi=(300, 300))

    # 正反拼合（桌面背景，模拟手机拍两张）
    pad = 60
    comb = Image.new("RGB", (CW * 2 + pad * 3, CH + pad * 2), (232, 230, 226))
    comb.paste(Image.open(f_jpg), (pad, pad))
    comb.paste(Image.open(b_jpg), (pad * 2 + CW, pad))
    cjpg = os.path.join(OUT, "id_combined.jpg")
    comb.save(cjpg, "JPEG", quality=84)
    return (f_raw, b_raw), (f_jpg, b_jpg), cjpg


# ----------------------------------------------------------------------------
# Word 版信件
# ----------------------------------------------------------------------------
def build_docx(cfg):
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(0.9)
    sec.bottom_margin = Inches(0.9)
    sec.left_margin = Inches(1.0)
    sec.right_margin = Inches(1.0)

    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(11.5)

    def p(text="", size=11.5, bold=False, align="left", space_after=6, color=None):
        par = doc.add_paragraph()
        par.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT,
                         "center": WD_ALIGN_PARAGRAPH.CENTER,
                         "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        par.paragraph_format.space_after = Pt(space_after)
        r = par.add_run(text)
        r.font.size = Pt(size)
        r.bold = bold
        r.font.name = "Times New Roman"
        if color:
            r.font.color.rgb = RGBColor(*color)
        return par

    p(cfg["school_name"].upper(), 20, True, "center", 2, cfg["school_color"])
    p(cfg["school_addr"], 9, False, "center", 0, (70, 70, 70))
    p("  |  ".join([cfg["school_phone"], cfg["school_web"], cfg["school_email"]]),
      9, False, "center", 8, (70, 70, 70))

    ref = "%s-%s" % (cfg["ref_prefix"],
                     hashlib.md5((cfg["student_id"] + cfg["term"]).encode()).hexdigest()[:8].upper())
    p("Ref: %s" % ref, 9, False, "left", 0, (90, 90, 90))
    p(cfg["letter_date"], 11, False, "right", 14)

    p("TO WHOM IT MAY CONCERN", 11.5, True, "left", 14)
    p("CERTIFICATE OF ENROLLMENT", 14, True, "left", 16, cfg["school_color"])

    body = [
        "This letter is issued by the Office of the Registrar of %s in response to a request "
        "for verification of enrollment status." % cfg["school_name"],
        "This is to certify that %s, Student Identification Number %s, is currently enrolled "
        "as a %s student in the %s at %s."
        % (cfg["student_name"], cfg["student_id"], cfg["level"], cfg["program"], cfg["school_name"]),
        "The student is registered for the %s term, which began on %s and is scheduled to "
        "conclude on %s. The student's current academic status is Active / In Good Standing, "
        "and the student is carrying a full-time course load."
        % (cfg["term"], cfg["term_start"], cfg["term_end"]),
        "The student is a candidate for graduation in %s. The academic programme is "
        "administered by the %s." % (cfg["expected_grad"], cfg["faculty"]),
        "This certification is issued at the request of the student for purposes of "
        "third-party verification. Questions concerning the authenticity of this document "
        "may be directed to the Office of the Registrar at %s." % cfg["school_email"],
    ]
    for b in body:
        par = doc.add_paragraph()
        par.paragraph_format.space_after = Pt(10)
        par.paragraph_format.line_spacing = 1.15
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r = par.add_run(b)
        r.font.size = Pt(11.5)

    p("Sincerely,", 11.5, False, "left", 40)
    p("______________________________", 11.5, False, "left", 2)
    p(cfg["registrar"], 11.5, True, "left", 0)
    p(cfg["registrar_title"], 10.5, False, "left", 0)
    p("Office of the Registrar", 10.5, False, "left", 16)
    p("Valid through %s" % cfg["valid_thru"], 9, False, "left", 0, (110, 110, 110))

    out = os.path.join(OUT, "enrollment_letter.docx")
    doc.save(out)
    return out


def main():
    cfg = load_cfg()
    d = build_docx(cfg)
    raw, jpg = build_letter(cfg)
    _, idj, comb = build_id(cfg)
    print("OK")
    for p in [d, raw, jpg, idj[0], idj[1], comb]:
        print("  ", p)


if __name__ == "__main__":
    main()
