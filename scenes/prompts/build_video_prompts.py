#!/usr/bin/env python3
"""把 video_library.json 展开成图生视频提示词。

和 build_prompts.py 的分工：
    图    build_prompts.py      → compiled/        首帧
    视频  本脚本                → compiled_video/  从首帧出发的变化

装配：motion + "Keep: ..." + "Avoid: ..."
阈值：motion 40–80 词（animator 方法论），超了就是又在写静态描述
      motion 里出现焦段/太阳高度/色温 → 报警，这些属于关键帧

用法：
    python scenes/prompts/build_video_prompts.py
    python scenes/prompts/build_video_prompts.py --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIB = ROOT / "video_library.json"
OUT = ROOT / "compiled_video"

MIN_W, MAX_W = 40, 80
# 这些词属于关键帧提示词，出现在视频提示词里说明写串了层
LEAKED = ["mm lens", "degrees", "kelvin", "f-stop", "oktas", "lut"]


def words(text: str) -> int:
    return len(text.split())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只检查，不写文件")
    args = ap.parse_args()

    data = json.loads(LIB.read_text(encoding="utf-8"))
    if not args.check:
        OUT.mkdir(parents=True, exist_ok=True)

    problems: list[str] = []
    rows = []

    for shot in data["shots"]:
        motion = shot["motion"].strip()
        n = words(motion)

        if not (MIN_W <= n <= MAX_W):
            problems.append(f"{shot['id']} motion {n} 词，应在 {MIN_W}–{MAX_W}")
        if not re.search(r"\b(left to right|right to left|toward camera|away from camera|"
                         r"forward|backward|tracks|follows|static|rises|slides|approaches|passes)\b", motion):
            problems.append(f"{shot['id']} 没写运动方向或主体/镜头区分")
        low = motion.lower()
        for bad in LEAKED:
            if bad in low:
                problems.append(f"{shot['id']} 含关键帧专属词「{bad}」")

        full = f"{motion}\n\nKeep: {shot['keep']}.\nAvoid: {shot['avoid']}."
        rows.append((shot["id"], shot["style"], shot["duration_s"], n, words(full)))

        if not args.check:
            head = (
                f"# {shot['name']}\n"
                f"# 画风 {shot['style']}   时长 {shot['duration_s']}s   "
                f"motion {n} 词\n"
                f"# 首帧 {shot['id']}.png（compiled/ 里对应的关键帧）\n\n"
            )
            (OUT / f"{shot['id']}_vid.txt").write_text(head + full + "\n", encoding="utf-8")

    print(f"{'ID':<8}{'画风':<6}{'时长':>5}{'motion':>8}{'合计':>6}")
    print("-" * 36)
    for sid, style, dur, n, total in rows:
        print(f"{sid:<8}{style:<6}{dur:>4}s{n:>8}{total:>6}")

    avg = sum(r[3] for r in rows) / len(rows)
    print("-" * 36)
    print(f"motion 平均 {avg:.0f} 词，区间 [{min(r[3] for r in rows)}, {max(r[3] for r in rows)}]")

    if problems:
        print(f"\n{len(problems)} 项有问题：")
        for line in problems:
            print("  " + line)
    else:
        print("\n全部合规：词数在区间内，方向已写，无关键帧词汇泄漏。")

    if not args.check:
        print(f"\n已写入 {len(rows)} 个文件 → {OUT}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())