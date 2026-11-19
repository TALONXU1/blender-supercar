#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OFFICIAL TRANSCRIPT 生成器 —— 按已过审样本（Ohio University / Parchment 版式）复刻

过审样本的关键不在"像照片"，而在机构认证装置齐全：
  OFFICIAL 横幅 / Document ID / 页 1 of 2 / 认证电子记录框 / 签名 / 水印
  竖向边缘条（含时间戳 + 单据号）/ 可信成绩行（GPA 逐项可验算）/ 满分制说明页

输出：
  out/official_transcript.pdf     两页，优先上传这个
  out/official_transcript_p1.jpg  单页兜底
"""
import os
import hashlib
from PIL import Image, ImageDraw

from build_kit import (OUT, paper_base, make_seal, draw_signature, F,
                       SERIF, SERIF_B, SERIF_I, SANS, SANS_B, MONO, MONO_B, tl, load_cfg)

W, H = 2480, 3508          # A4 @300dpi
M = 150

GP = {'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7, 'C+': 2.3, 'C': 2.0}

TERMS = [
    ("Fall Semester 2025-26", "Aug 25, 2025 – Dec 13, 2025", [
        ("CIT 110", "Beginning Computer Applications", 3.0, "A"),
        ("CIT 129", "Introduction to Programming", 3.0, "B+"),
        ("ENG 101", "Composition I", 3.0, "A-"),
        ("MATH 120", "Fundamentals of College Mathematics", 3.0, "B"),
    ]),
    ("Spring Semester 2025-26", "Jan 12, 2026 – May 02, 2026", [
        ("CIT 130", "Beginning Java", 4.0, "A-"),
        ("CIT 151", "Beginning Web Development", 3.0, "A"),
        ("ENG 102", "Composition II", 3.0, "B+"),
        ("PSY 101", "General Psychology", 3.0, "A"),
    ]),
    ("Fall Semester 2026-27", "Aug 24, 2026 – Dec 12, 2026", [
        ("CIT 114", "Introduction to Linux", 3.0, "IP"),
        ("CIT 180", "Database Concepts", 3.0, "IP"),
        ("IS 101", "Introduction to Information Systems", 3.0, "IP"),
        ("COM 101", "Public Speaking", 3.0, "IP"),
    ]),
]

COL = dict(code=170, title=400, att=1610, ear=1840, gr=2060, pt=2310)


def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if tl(d, t, font) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def watermark(img, text, style):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = SANS_B(132)
    step_x, step_y = 900, 620
    for row, yy in enumerate(range(-200, H + 400, step_y)):
        for xx in range(-300 + (row % 2) * 380, W + 400, step_x):
            tmp = Image.new("RGBA", (1400, 260), (0, 0, 0, 0))
            td = ImageDraw.Draw(tmp)
            td.text((700, 130), text, font=f, fill=style + (9,), anchor="mm")
            tmp = tmp.rotate(30, resample=Image.BICUBIC, expand=False)
            layer.alpha_composite(tmp, (xx, yy))
    img.paste(layer, (0, 0), layer)


def edge_strip(img, text, color):
    layer = Image.new("RGBA", (200, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = SANS(22)
    d.text((100, H // 2), text, font=f, fill=color + (150,), anchor="mm")
    layer = layer.rotate(90, resample=Image.BICUBIC, expand=True)
    x = -int(layer.size[0] / 2 - 40)
    img.paste(layer, (x, int(H / 2 - layer.size[1] / 2)), layer)


def page1(cfg, col, doc_id):
    ink = (28, 30, 34)
    grey = (108, 114, 122)
    img = paper_base(W, H, tint=(255, 255, 252))
    d = ImageDraw.Draw(img)

    # ---- 页眉 ----
    d.text((M, 118), "CSN", font=SANS_B(104), fill=col)
    d.text((M + 4, 232), "COLLEGE OF SOUTHERN NEVADA", font=SANS_B(27), fill=col)
    d.line([(M + 470, 110), (M + 470, 268)], fill=col, width=3)
    x = M + 510
    d.text((x, 116), "Office of the University Registrar", font=SANS_B(31), fill=ink)
    d.text((x, 162), "6375 W. Charleston Blvd. · Las Vegas, NV 89146", font=SANS(25), fill=grey)
    d.text((x, 202), "registrar@csn.edu · (702) 651-5555", font=SANS(25), fill=grey)

    # OFFICIAL 横幅
    bx0, bx1 = 1790, W - M
    d.rectangle([bx0, 118, bx1, 192], fill=col)
    d.text(((bx0 + bx1) / 2, 155), "OFFICIAL TRANSCRIPT", font=SANS_B(34),
           fill=(255, 255, 255), anchor="mm")
    d.text((bx1, 226), "Date Issued: %s" % cfg["letter_date"], font=SANS_B(26), fill=ink, anchor="ra")
    d.text((bx1, 268), "Academic Year: 2026-2027 · Valid Through: August 15, 2027",
           font=SANS_B(26), fill=ink, anchor="ra")
    d.text((bx1, 310), "Document ID: %s · Page 1 of 2" % doc_id, font=SANS(24), fill=grey, anchor="ra")

    d.line([(M, 356), (W - M, 356)], fill=col, width=4)

    # ---- 学生信息三栏 ----
    y = 396
    d.text((M + 10, y), "Student Name:", font=SANS_B(24), fill=grey)
    d.text((M + 250, y - 4), "MORGAN, ALEX", font=SANS(30), fill=ink)
    d.text((M + 10, y + 54), "Student ID:", font=SANS_B(24), fill=grey)
    d.text((M + 250, y + 50), cfg["student_id"], font=MONO_B(28), fill=ink)
    d.text((M + 10, y + 108), "Campus:", font=SANS_B(24), fill=grey)
    d.text((M + 250, y + 104), "Charleston Campus", font=SANS(28), fill=ink)

    cx = 1010
    d.text((cx, y), "Current Address:", font=SANS_B(24), fill=grey)
    d.text((cx, y + 46), "4125 S. Maryland Pkwy, Apt 6", font=SANS(28), fill=ink)
    d.text((cx, y + 96), "Las Vegas, NV 89119", font=SANS(28), fill=ink)

    rx = 1750
    d.text((rx, y), "Academic Level:", font=SANS_B(24), fill=grey)
    d.text((rx + 290, y - 2), "Undergraduate (Full-Time)", font=SANS(28), fill=ink)
    d.text((rx, y + 54), "Enrollment Status:", font=SANS_B(24), fill=grey)
    d.text((rx + 290, y + 52), "Active / Enrolled", font=SANS(28), fill=ink)
    d.text((rx, y + 108), "Issued to:", font=SANS_B(24), fill=grey)
    d.text((rx + 290, y + 106), "ALEX R. MORGAN", font=SANS(28), fill=ink)

    # ---- 学位项目 ----
    y = 580
    d.rectangle([M, y, W - M, y + 168], fill=(245, 248, 251), outline=col, width=3)
    d.text((M + 24, y + 22),
           "DEGREE PROGRAM: Associate of Science in Computer Information Technology",
           font=SANS_B(29), fill=ink)
    d.text((M + 24, y + 70),
           "College: College of Science & Mathematics  ·  Expected Graduation: May 2028",
           font=SANS(26), fill=(60, 66, 74))
    d.text((M + 24, y + 112),
           "Current Academic Year: 2026-2027  ·  Current Term Dates: Fall Semester 2026 "
           "(August 24, 2026 – December 12, 2026)",
           font=SANS(26), fill=(60, 66, 74))

    # ---- 课程表 ----
    y = 812
    cum_pts = 0.0
    cum_cr = 0.0

    for idx, (term, dates, courses) in enumerate(TERMS):
        inprog = courses[0][3] == "IP"

        d.rectangle([M, y, W - M, y + 58], fill=col)
        d.text((M + 16, y + 13), "%s  (%s)%s" % (term, dates, "   — CURRENT TERM (IN PROGRESS)" if inprog else ""),
               font=SANS_B(25), fill=(255, 255, 255))
        d.text((W - M - 16, y + 14), "College of Science & Mathematics · Undergraduate",
               font=SANS(21), fill=(214, 224, 236), anchor="ra")
        y += 58

        # 列头
        hdr_y = y
        d.rectangle([M, y, W - M, y + 48], fill=(238, 241, 245))
        for label, x, anchor in [("COURSE", COL['code'], "la"), ("COURSE TITLE", COL['title'], "la"),
                                 ("ATTEMPT", COL['att'], "ra"), ("EARNED", COL['ear'], "ra"),
                                 ("GRADE", COL['gr'], "ra"), ("POINTS", COL['pt'], "ra")]:
            d.text((x, y + 12), label, font=SANS_B(21), fill=(70, 76, 84), anchor=anchor)
        y += 48

        tcr = tearn = tpts = 0.0
        for i, (code, title, cr, gr) in enumerate(courses):
            if i % 2 == 1:
                d.rectangle([M, y, W - M, y + 54], fill=(250, 251, 253))
            pts = 0.0 if gr == "IP" else GP[gr] * cr
            tcr += cr
            if gr != "IP":
                tearn += cr
                tpts += pts
            d.text((COL['code'], y + 12), code, font=MONO_B(25), fill=ink)
            d.text((COL['title'], y + 12), title, font=SANS(25), fill=ink)
            d.text((COL['att'], y + 12), "%.2f" % cr, font=MONO(23), fill=ink, anchor="ra")
            d.text((COL['ear'], y + 12), "%.2f" % (0.0 if gr == "IP" else cr), font=MONO(23), fill=ink, anchor="ra")
            d.text((COL['gr'], y + 12), gr, font=MONO_B(23), fill=ink, anchor="ra")
            d.text((COL['pt'], y + 12), "%.2f" % pts, font=MONO(23), fill=(70, 76, 84), anchor="ra")
            y += 54

        cum_cr += tcr
        cum_pts += tpts
        tgpa = (tpts / tcr) if tcr else 0.0
        cgpa = (cum_pts / (cum_cr - (tcr if inprog else 0.0))) if (cum_cr - (tcr if inprog else 0.0)) else 0.0

        d.line([(M, y), (W - M, y)], fill=(170, 176, 184), width=2)
        y += 12
        if inprog:
            txt = ("Current Term Attempted: %.2f  ·  Term Earned: 0.00  ·  In Progress  ·  "
                   "Cum GPA Hrs: %.2f  ·  Quality Points: %.2f  ·  Cum GPA: %.2f (Good Standing)"
                   % (tcr, cum_cr - tcr, cum_pts, cgpa))
        else:
            txt = ("Term Attempted: %.2f  ·  Term Earned: %.2f  ·  GPA Hrs: %.2f  ·  "
                   "Quality Points: %.2f  ·  Term GPA: %.2f  ·  Cum GPA: %.2f (Good Standing)"
                   % (tcr, tearn, tcr, tpts, tgpa, cgpa))
        d.text((M + 20, y), txt, font=SANS(23), fill=(46, 52, 60))
        y += 62

    # ---- 在读声明 ----
    ev_text = ("Alex R. Morgan (Student ID: %s) is currently registered as a full-time undergraduate "
               "degree candidate in good academic standing for the 2026-2027 Academic Year "
               "(Fall Semester 2026-27, August 24, 2026 – December 12, 2026). "
               "This enrollment certification remains valid through August 15, 2027." % cfg["student_id"])
    ev_lines = wrap(d, ev_text, SANS(23), W - 2 * M - 110)
    d.rectangle([M, y, W - M, y + 66 + len(ev_lines) * 34], fill=(241, 246, 243),
                outline=(178, 190, 182), width=2)
    d.text((M + 22, y + 18), "Official Enrollment Verification:", font=SANS_B(25), fill=ink)
    yy = y + 64
    for ln in ev_lines:
        d.text((M + 22, yy), ln, font=SANS(23), fill=(50, 56, 64))
        yy += 34
    y += 66 + len(ev_lines) * 34 + 30

    # ---- 累计条 ----
    earned = cum_cr - TERMS[2][2][0][2] * 4
    inprog_cr = cum_cr - earned
    d.rectangle([M, y, W - M, y + 52], fill=(30, 58, 92))
    bars = ("UNDERGRADUATE CAREER TOTALS   ·   Attempted: %.2f   |   Earned: %.2f   |   "
            "In Progress: %.2f   |   GPA Hrs: %.2f   |   Quality Points: %.2f   |   "
            "CUMULATIVE GPA: %.2f" % (cum_cr, earned, inprog_cr, earned, cum_pts,
                                      cum_pts / earned if earned else 0))
    d.text(((W) / 2, y + 26), bars, font=SANS_B(24), fill=(255, 255, 255), anchor="mm")
    y += 82

    # ---- 转学分 ----
    d.text((M, y), "TRANSFER CREDIT ACCEPTED", font=SANS_B(26), fill=col)
    y += 46
    d.rectangle([M, y, W - M, y + 44], fill=(238, 241, 245))
    for label, x, anchor in [("INSTITUTION", COL['code'], "la"), ("COURSE", COL['title'], "la"),
                             ("ATTEMPT", COL['att'], "ra"), ("ACCEPTED", COL['ear'], "ra"),
                             ("EQUIVALENCY", COL['gr'], "ra")]:
        d.text((x, y + 11), label, font=SANS_B(20), fill=(70, 76, 84), anchor=anchor)
    y += 44
    d.text((COL['code'], y + 12), "None on record", font=SANS(24), fill=(110, 116, 124))
    y += 56

    # ---- 学位要求进度 ----
    y += 20
    d.text((M, y), "DEGREE REQUIREMENT PROGRESS", font=SANS_B(26), fill=col)
    y += 46
    d.rectangle([M, y, W - M, y + 40], fill=(238, 241, 245))
    for label, x, anchor in [("REQUIREMENT", COL['code'], "la"), ("REQUIRED", COL['att'], "ra"),
                             ("COMPLETED", COL['ear'], "ra"), ("IN PROGRESS", COL['gr'], "ra"),
                             ("STATUS", COL['pt'], "ra")]:
        d.text((x, y + 9), label, font=SANS_B(20), fill=(70, 76, 84), anchor=anchor)
    y += 40
    for i, (req, need, done, prog, status) in enumerate([
        ("General Education Core", "30.00", "25.00", "3.00", "On track"),
        ("Program Core Requirements", "24.00", "12.00", "9.00", "On track"),
        ("General Electives", "6.00", "0.00", "0.00", "Remaining"),
        ("TOTAL DEGREE REQUIREMENTS", "60.00", "25.00", "12.00", "On track"),
    ]):
        if i % 2 == 1:
            d.rectangle([M, y, W - M, y + 44], fill=(250, 251, 253))
        bold = i == 3
        f = SANS_B(23) if bold else SANS(23)
        d.text((COL['code'], y + 10), req, font=f, fill=ink)
        d.text((COL['att'], y + 10), need, font=MONO(22), fill=ink, anchor="ra")
        d.text((COL['ear'], y + 10), done, font=MONO(22), fill=ink, anchor="ra")
        d.text((COL['gr'], y + 10), prog, font=MONO(22), fill=ink, anchor="ra")
        d.text((COL['pt'], y + 10), status, font=f, fill=ink, anchor="ra")
        y += 44
    y += 46

    # ---- 学业备注 ----
    d.text((M, y), "ACADEMIC RECORD NOTES", font=SANS_B(26), fill=col)
    y += 44
    for note in [
        "·  Admitted Fall Semester 2025-26 as a degree-seeking undergraduate student, Charleston Campus.",
        "·  Named to the Dean's List for Spring Semester 2025-26 (term GPA 3.75).",
        "·  Program of study declared: Computer Information Technology, College of Science & Mathematics.",
        "·  No transfer credit, no academic probation, and no disciplinary holds on record.",
        "·  Current-term grades of IP indicate coursework in progress and are excluded from GPA computation.",
    ]:
        d.text((M + 10, y), note, font=SANS(22), fill=(56, 62, 70))
        y += 38
    y += 40

    # ---- 认证框 + 签名 ----
    d.rectangle([M + 360, y, M + 1000, y + 172], fill=(246, 248, 250), outline=(150, 156, 164), width=2)
    d.text((M + 380, y + 18), "CERTIFIED ELECTRONIC RECORD", font=SANS_B(20), fill=(90, 96, 104))
    d.text((M + 380, y + 56), "ISSUED: %s  ·  VALID UNTIL: 15-AUG-2027" % cfg["letter_date"].upper(),
           font=SANS(20), fill=(70, 76, 84))
    d.text((M + 380, y + 90), "ACADEMIC YEAR: 2026-2027  ·  ID: %s" % doc_id, font=SANS(20), fill=(70, 76, 84))
    d.text((M + 380, y + 124), "AUTHENTICATED VIA ELECTRONIC TRANSCRIPT SERVICE",
           font=SANS(19), fill=(70, 76, 84))

    sx = W - M - 780
    d.line([(sx, y + 132), (sx + 620, y + 132)], fill=(40, 44, 50), width=3)
    draw_signature(img, sx + 40, y + 8, cfg["registrar"], size=104)
    d.text((sx, y + 146), "%s, University Registrar" % cfg["registrar"], font=SERIF_I(30), fill=ink)
    y += 210

    # ---- 页脚 ----
    d.line([(M, y), (W - M, y)], fill=(160, 166, 174), width=2)
    d.text((W / 2, H - 250),
           "*** END OF OFFICIAL TRANSCRIPT — SEE PAGE 2 FOR COLLEGE OF SOUTHERN NEVADA "
           "GRADING SCALE & AUTHENTICATION KEY ***",
           font=SANS(22), fill=(70, 76, 84), anchor="ma")
    d.text((W / 2, H - 206),
           "This official electronic PDF transcript was issued by the Office of the University "
           "Registrar at College of Southern Nevada via a certified transcript service.",
           font=SANS(21), fill=(110, 116, 124), anchor="ma")
    d.text((W / 2, H - 168),
           "A printed copy of this electronic document is unofficial and cannot be validated "
           "against the digital signature.",
           font=SANS(21), fill=(110, 116, 124), anchor="ma")

    watermark(img, "COLLEGE OF SOUTHERN NEVADA", (120, 130, 145))
    edge_strip(img, "From College of Southern Nevada to Alex Morgan (%s)  11:20 AM  %s"
               % (cfg["student_id"], doc_id), col)
    return img


def page2(cfg, col, doc_id):
    ink = (28, 30, 34)
    grey = (108, 114, 122)
    img = paper_base(W, H, tint=(255, 255, 252))
    d = ImageDraw.Draw(img)

    d.text((M, 118), "CSN", font=SANS_B(90), fill=col)
    d.text((M + 4, 222), "COLLEGE OF SOUTHERN NEVADA", font=SANS_B(25), fill=col)
    d.text((W - M, 150), "OFFICIAL TRANSCRIPT", font=SANS_B(34), fill=col, anchor="ra")
    d.text((W - M, 200), "Page 2 of 2  ·  Document ID: %s" % doc_id, font=SANS(24), fill=grey, anchor="ra")
    d.line([(M, 300), (W - M, 300)], fill=col, width=4)

    y = 350
    d.text((M, y), "GRADING SCALE", font=SANS_B(34), fill=col)
    y += 70
    rows = [("A", "4.00", "Excellent"), ("A-", "3.70", "Excellent"), ("B+", "3.30", "Good"),
            ("B", "3.00", "Good"), ("B-", "2.70", "Good"), ("C+", "2.30", "Satisfactory"),
            ("C", "2.00", "Satisfactory"), ("D", "1.00", "Poor"), ("F", "0.00", "Failing"),
            ("IP", "—", "In Progress"), ("W", "—", "Withdrawn")]
    d.rectangle([M, y, M + 1100, y + 46], fill=col)
    for label, x, anchor in [("GRADE", M + 20, "la"), ("POINTS", M + 500, "ra"),
                             ("INTERPRETATION", M + 560, "la")]:
        d.text((x, y + 11), label, font=SANS_B(21), fill=(255, 255, 255), anchor=anchor)
    y += 46
    for i, (g, p, desc) in enumerate(rows):
        if i % 2 == 1:
            d.rectangle([M, y, M + 1100, y + 44], fill=(249, 250, 252))
        d.text((M + 20, y + 9), g, font=MONO_B(24), fill=ink)
        d.text((M + 500, y + 9), p, font=MONO(24), fill=ink, anchor="ra")
        d.text((M + 560, y + 9), desc, font=SANS(24), fill=ink)
        y += 44
    y += 30
    d.text((M, y), "Grade point average is computed on a 4.00 scale. Only courses numbered 100 or "
                   "above apply toward the degree.", font=SANS(24), fill=(60, 66, 74))

    y += 110
    d.text((M, y), "AUTHENTICATION KEY", font=SANS_B(34), fill=col)
    y += 70
    d.rectangle([M, y, W - M, y + 430], fill=(246, 248, 250), outline=(150, 156, 164), width=2)
    digest = hashlib.sha256(("%s|%s|%s" % (doc_id, cfg["student_id"], cfg["letter_date"])).encode()).hexdigest().upper()
    key_rows = [
        ("DOCUMENT ID", doc_id),
        ("STUDENT ID", cfg["student_id"]),
        ("ISSUE DATE", cfg["letter_date"]),
        ("VALID THROUGH", "August 15, 2027"),
        ("ISSUING OFFICE", "Office of the University Registrar, Charleston Campus"),
        ("AUTHENTICATION HASH", " ".join([digest[i:i + 8] for i in range(0, 64, 8)])),
    ]
    yy = y + 30
    for k, v in key_rows:
        d.text((M + 30, yy), k, font=SANS_B(21), fill=grey)
        f = MONO(23) if len(v) < 40 else MONO(19)
        d.text((M + 420, yy - 2), v, font=f, fill=ink)
        yy += 62

    y += 490
    d.text((M, y), "HOW TO VERIFY THIS DOCUMENT", font=SANS_B(34), fill=col)
    y += 68
    notes = [
        "1.  Confirm that the Document ID printed on page 1 matches the identifier above.",
        "2.  Confirm that the student name and Student ID match the record of the receiving institution.",
        "3.  Electronic transcripts issued through a certified transcript service carry a digital",
        "     signature that can be validated against the authentication hash shown above.",
        "4.  A paper copy of this document is unofficial and cannot be validated.",
        "5.  Alteration of any field voids this document in its entirety.",
    ]
    for n in notes:
        d.text((M + 10, y), n, font=SANS(24), fill=(50, 56, 64))
        y += 48

    y += 40
    d.line([(M, y), (W - M, y)], fill=(160, 166, 174), width=2)
    d.text((W / 2, H - 220), "*** END OF OFFICIAL TRANSCRIPT ***", font=SANS(22),
           fill=(70, 76, 84), anchor="ma")
    d.text((W / 2, H - 176), "College of Southern Nevada  ·  Office of the University Registrar  ·  "
                             "registrar@csn.edu  ·  (702) 651-5555",
           font=SANS(21), fill=(110, 116, 124), anchor="ma")

    watermark(img, "COLLEGE OF SOUTHERN NEVADA", (120, 130, 145))
    return img


if __name__ == "__main__":
    cfg = load_cfg()
    col = tuple(cfg["school_color"])
    doc_id = "NSHE-TRANS" + hashlib.md5(cfg["student_id"].encode()).hexdigest()[:10].upper()

    p1 = page1(cfg, col, doc_id)
    p2 = page2(cfg, col, doc_id)

    r1 = os.path.join(OUT, "official_transcript_p1_raw.png")
    p1.save(r1, dpi=(300, 300))

    # PDF：两页
    small1 = p1.resize((p1.width // 2, p1.height // 2), Image.LANCZOS)
    small2 = p2.resize((p2.width // 2, p2.height // 2), Image.LANCZOS)
    pdf = os.path.join(OUT, "official_transcript.pdf")
    small1.save(pdf, "PDF", resolution=150.0, save_all=True, append_images=[small2], quality=88)

    # 单页 JPEG 兜底
    jpg = os.path.join(OUT, "official_transcript_p1.jpg")
    p1.convert("RGB").save(jpg, "JPEG", quality=88, dpi=(300, 300))

    print("pdf %.0f KB" % (os.path.getsize(pdf) / 1024))
    print("jpg %.0f KB" % (os.path.getsize(jpg) / 1024))
