#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
非正式成绩单（unofficial transcript）生成器
输出 out/transcript.jpg —— 比在读证明更难被模板化判定：表格、课程行、GPA 计算天然不一致
"""
import os, math, hashlib
from PIL import Image, ImageDraw

from build_kit import (OUT, paper_base, scan_finish, make_seal, draw_signature,
                       SERIF, SERIF_B, SERIF_I, SANS, SANS_B, MONO, MONO_B, tl, load_cfg)

W, H = 2480, 3508
M = 200

GRADE_PTS = {'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
             'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D': 1.0, 'F': 0.0}

TERMS = [
    ("FALL 2025", "Charleston Campus", [
        ("CIT 110", "Beginning Computer Applications", 3.0, "A"),
        ("CIT 129", "Introduction to Programming", 3.0, "B+"),
        ("ENG 101", "Composition I", 3.0, "A-"),
        ("MATH 120", "Fundamentals of College Mathematics", 3.0, "B"),
    ]),
    ("SPRING 2026", "Charleston Campus", [
        ("CIT 130", "Beginning Java", 4.0, "A-"),
        ("CIT 151", "Beginning Web Development", 3.0, "A"),
        ("ENG 102", "Composition II", 3.0, "B+"),
        ("PSY 101", "General Psychology", 3.0, "A"),
    ]),
    ("FALL 2026", "Charleston Campus  (IN PROGRESS)", [
        ("CIT 114", "Introduction to Linux", 3.0, "A"),
        ("CIT 180", "Database Concepts", 3.0, "A-"),
        ("IS 101", "Introduction to Information Systems", 3.0, "A"),
        ("COM 101", "Public Speaking", 3.0, "B+"),
    ]),
]


def build(cfg):
    col = tuple(cfg["school_color"])
    ink = (26, 28, 32)
    grey = (110, 116, 124)
    rule = (150, 156, 164)

    img = paper_base(W, H, tint=(253, 253, 251))
    d = ImageDraw.Draw(img)
    y = 190

    # ---------- 页眉 ----------
    d.text((W / 2, y), cfg["school_name"].upper(), font=SERIF_B(74), fill=col, anchor="ma")
    y += 92
    d.text((W / 2, y), cfg["school_addr"], font=SERIF(34), fill=(70, 70, 70), anchor="ma")
    y += 46
    d.text((W / 2, y), "  |  ".join([cfg["school_phone"], cfg["school_web"]]),
           font=SERIF(34), fill=(70, 70, 70), anchor="ma")
    y += 58
    d.line([(M, y), (W - M, y)], fill=col, width=5)
    d.line([(M, y + 11), (W - M, y + 11)], fill=col, width=2)

    # ---------- 标题 ----------
    y += 92
    d.text((W / 2, y), "ACADEMIC TRANSCRIPT", font=SERIF_B(60), fill=(20, 20, 20), anchor="ma")
    y += 78
    d.text((W / 2, y), "U N O F F I C I A L", font=SANS_B(30), fill=(170, 40, 46), anchor="ma")
    y += 40
    d.text((W - M, y - 118), "Issued: %s" % cfg["letter_date"], font=SERIF(28), fill=grey, anchor="ra")
    d.text((W - M, y - 84), "Page 1 of 1", font=SERIF(28), fill=grey, anchor="ra")
    ref = "%s-TR-%s" % (cfg["school_short"], hashlib.md5(cfg["student_id"].encode()).hexdigest()[:6].upper())
    d.text((W - M, y - 50), "Ref: %s" % ref, font=SERIF(28), fill=grey, anchor="ra")

    # ---------- 学生信息框 ----------
    y += 60
    box_top = y
    rows = [
        ("NAME", cfg["student_name"], "STUDENT ID", cfg["student_id"]),
        ("DATE OF BIRTH", cfg["dob"], "ADMISSION TERM", "Fall 2025"),
        ("PROGRAM", "Associate of Science — Computer Information Technology", "", ""),
        ("CAMPUS", "Charleston Campus", "ACADEMIC STATUS", "Active — Good Standing"),
    ]
    lx, vx, rx, vx2 = M + 40, M + 330, M + 1150, M + 1480
    for k1, v1, k2, v2 in rows:
        d.text((lx, y), k1, font=SANS_B(20), fill=grey)
        d.text((vx, y - 6), v1, font=SANS(30), fill=ink)
        if k2:
            d.text((rx, y), k2, font=SANS_B(20), fill=grey)
            d.text((vx2, y - 6), v2, font=SANS(30), fill=ink)
        y += 62
    box_bottom = y + 6
    d.rectangle([M, box_top - 16, W - M, box_bottom], outline=rule, width=3)

    # ---------- 课程表 ----------
    y = box_bottom + 80
    d.text((M, y), "COURSE WORK", font=SANS_B(28), fill=col)
    d.line([(M, y + 46), (W - M, y + 46)], fill=col, width=2)
    y += 78

    C_CODE, C_TITLE, C_CR, C_GR, C_PT = M + 10, M + 200, M + 1500, M + 1650, M + 1850

    total_cr = 0.0
    total_pts = 0.0

    for term_name, campus, courses in TERMS:
        # 学期条
        d.rectangle([M, y - 10, W - M, y + 52], fill=(238, 241, 246))
        d.text((M + 14, y + 2), term_name, font=SANS_B(28), fill=col)
        d.text((W - M - 14, y + 8), campus, font=SANS(22), fill=(90, 96, 104), anchor="ra")
        y += 78

        # 列头
        for label, x, anchor in [("COURSE", C_CODE, "la"), ("TITLE", C_TITLE, "la"),
                                 ("CR", C_CR, "ra"), ("GRADE", C_GR, "ra"), ("PTS", C_PT, "ra")]:
            d.text((x, y), label, font=SANS_B(19), fill=grey, anchor=anchor)
        y += 34
        d.line([(M, y), (W - M, y)], fill=rule, width=1)
        y += 16

        tcr = 0.0
        tpts = 0.0
        for i, (code, title, cr, gr) in enumerate(courses):
            if i % 2 == 1:
                d.rectangle([M, y - 8, W - M, y + 44], fill=(249, 250, 252))
            pts = GRADE_PTS[gr] * cr
            tcr += cr
            tpts += pts
            d.text((C_CODE, y), code, font=MONO_B(27), fill=ink)
            d.text((C_TITLE, y), title, font=SERIF(30), fill=ink)
            d.text((C_CR, y), "%.1f" % cr, font=MONO(27), fill=ink, anchor="ra")
            d.text((C_GR, y), gr, font=MONO_B(27), fill=ink, anchor="ra")
            d.text((C_PT, y), "%.2f" % pts, font=MONO(25), fill=(80, 86, 94), anchor="ra")
            y += 52

        tgpa = tpts / tcr
        y += 4
        d.line([(M, y), (W - M, y)], fill=rule, width=1)
        y += 14
        d.text((C_TITLE, y), "Term Credits: %.1f" % tcr, font=SANS_B(24), fill=(60, 66, 74))
        d.text((C_PT, y), "Term GPA: %.2f" % tgpa, font=SANS_B(24), fill=(60, 66, 74), anchor="ra")
        y += 78

        total_cr += tcr
        total_pts += tpts

    # ---------- 汇总 ----------
    cgpa = total_pts / total_cr
    y += 20
    d.rectangle([M, y, W - M, y + 300], fill=(246, 248, 251), outline=rule, width=2)
    yy = y + 34
    d.text((M + 30, yy), "TRANSCRIPT SUMMARY", font=SANS_B(26), fill=col)
    yy += 56
    summary = [
        ("Credits Attempted", "%.1f" % total_cr),
        ("Credits Earned", "%.1f" % total_cr),
        ("Transfer Credits Accepted", "12.0"),
        ("Cumulative GPA", "%.2f" % ((total_pts + 12 * 3.8) / (total_cr + 12))),
        ("Total Credits Toward Degree", "%.1f" % (total_cr + 12)),
    ]
    left, right = M + 40, M + 1180
    for i, (k, v) in enumerate(summary):
        x = left if i < 3 else right
        row = i if i < 3 else i - 3
        d.text((x, yy + row * 54), k, font=SANS(26), fill=(80, 86, 94))
        d.text((x + 560, yy + row * 54), v, font=MONO_B(28), fill=ink, anchor="ra")
    y += 330

    # ---------- 页脚 ----------
    fy = H - 500
    d.line([(M, fy), (W - M, fy)], fill=rule, width=2)
    d.text((M, fy + 24), "*** UNOFFICIAL TRANSCRIPT — NOT VALID FOR OFFICIAL PURPOSES ***",
           font=SANS_B(26), fill=(170, 40, 46))
    d.text((M, fy + 72), "Printed from the student self-service portal. Coursework in progress is "
                         "subject to change.", font=SERIF(26), fill=grey)
    d.text((M, fy + 114), "Grade point average is computed on a 4.00 scale. Only courses numbered "
                          "100 or above apply toward the degree.", font=SERIF(26), fill=grey)

    # 签名块：右下，独立区域不压正文
    sx, sy = W - M - 760, H - 300
    d.text((sx, sy - 24), "Registrar", font=SANS_B(18), fill=grey)
    d.line([(sx, sy + 34), (sx + 520, sy + 34)], fill=(60, 60, 60), width=2)
    draw_signature(img, sx + 18, sy - 96, cfg["registrar"], size=92)
    d.text((sx, sy + 46), cfg["registrar"], font=SERIF(26), fill=(40, 40, 40))
    d.text((sx, sy + 84), cfg["registrar_title"], font=SERIF(22), fill=grey)

    raw = os.path.join(OUT, "transcript_raw.png")
    img.save(raw, dpi=(300, 300))
    jpg = os.path.join(OUT, "transcript.jpg")
    scan_finish(img, jpg, angle=0.38, noise=3.4, blur=0.45, quality=87)
    return raw, jpg


if __name__ == "__main__":
    cfg = load_cfg()
    print("OK", build(cfg))
