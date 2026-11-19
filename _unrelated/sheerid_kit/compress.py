#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把材料压到 SheerID 单文件上限以内（1 MiB，各家实现普遍卡 1MB）"""
import os
from PIL import Image
from build_kit import OUT, scan_finish

TARGET = 950 * 1024


def emit(src_png, out_jpg, target=TARGET):
    img = Image.open(src_png).convert("RGB")
    q = 90
    tmp = out_jpg + ".tmp.jpg"
    while q >= 50:
        scan_finish(img, tmp, angle=0.35, noise=3.2, blur=0.4, quality=q)
        sz = os.path.getsize(tmp)
        if sz <= target:
            os.replace(tmp, out_jpg)
            return sz, q, img.size
        q -= 5
    # 仍超标就等比缩小
    w, h = img.size
    for scale in (0.9, 0.8, 0.72):
        small = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        scan_finish(small, tmp, angle=0.35, noise=3.2, blur=0.4, quality=85)
        if os.path.getsize(tmp) <= target:
            os.replace(tmp, out_jpg)
            return os.path.getsize(tmp), 85, small.size
    os.replace(tmp, out_jpg)
    return os.path.getsize(out_jpg), 85, img.size


if __name__ == "__main__":
    for src, out in [("transcript_raw.png", "transcript_small.jpg"),
                     ("enrollment_letter_raw.png", "enrollment_letter_small.jpg")]:
        sz, q, size = emit(os.path.join(OUT, src), os.path.join(OUT, out))
        print(f"{out:32s} {sz/1024:7.1f} KB  q={q}  {size[0]}x{size[1]}")
