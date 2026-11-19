#!/usr/bin/env python3
"""把 prompt_library.json 展开成可直接粘贴到 Sunburst 的成品提示词。

限制词分三层，按需装配：
    core    每张必带，62 词（文字/品牌/边框/单车体/不添加）
    scene   每镜头专属，23–46 词（这张最容易画错的那几条）
    full    加严包，出图不合格时才追加（人群/构图/输出卫生/风格漂移）

输出：
    compiled/          core + scene    默认用这个
    compiled/strict/   core + scene + full   返工用

阈值（查绝对值，不查比例）：
    core  ≤ 65 词        超了就是在抢注意力
    scene ≤ 50 词        超了说明你把 full 层的东西提前塞进来了

比例只统计不设闸。正文只有 120 词时，62 词 core 天然就占 50%，
这个数字本身不说明问题——有用的信号是 core 和 scene 的绝对词数。

用法：
    python scenes/prompts/build_prompts.py
    python scenes/prompts/build_prompts.py --check    # 只查不写文件
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIB = ROOT / "prompt_library.json"
OUT = ROOT / "compiled"

CORE_MAX = 65
SCENE_MAX = 50


def words(text: str) -> int:
    return len(text.split())


def expand(text: str, car: str, quality: str) -> str:
    """正文没提到车时补一句主体，避免出现两遍车辆描述。"""
    body = car if "concept car" in text.lower() else "A single 2035 Formula 1 concept car. " + car
    return text.replace("CINEMA_CAR", body).replace("CINEMA_QUALITY", quality)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只查预算，不写文件")
    args = ap.parse_args()

    data = json.loads(LIB.read_text(encoding="utf-8"))
    car, quality = data["car_block"], data["quality_block"]
    core, full = data["negative_core"], data["negative_full"]

    problems: list[str] = []
    if words(core) > CORE_MAX:
        problems.append(f"core {words(core)} 词 > 上限 {CORE_MAX}")

    if not args.check:
        (OUT / "strict").mkdir(parents=True, exist_ok=True)

    rows = []
    for shot in data["shots"]:
        positive = expand(shot["positive"], car, quality).strip()
        scene = shot["negative_scene"]
        neg_std = f"{core} {scene}"
        neg_strict = f"{neg_std} {full}"

        p, s = words(positive), words(scene)
        n_std = words(neg_std)
        ratio = n_std / p if p else 0.0

        if s > SCENE_MAX:
            problems.append(f"{shot['id']} scene {s} 词 > 上限 {SCENE_MAX}")

        rows.append((shot["id"], shot["aspect"], p, s, n_std, words(neg_strict), ratio))

        if not args.check:
            head = (
                f"# {shot['name']}\n"
                f"# 比例 {shot['aspect']}   限制词 {n_std} 词 / 正文 {p} 词 = {ratio:.0%}\n"
                f"# 备注 {shot['note']}\n\n"
            )
            (OUT / f"{shot['id']}.txt").write_text(
                head + f"{positive}\n\n{neg_std}\n", encoding="utf-8"
            )
            (OUT / "strict" / f"{shot['id']}.txt").write_text(
                head + f"{positive}\n\n{neg_strict}\n", encoding="utf-8"
            )

    print(f"{'ID':<8}{'比例':<7}{'正文':>6}{'场景':>6}{'合计':>6}{'加严':>6}{'占比':>7}")
    print("-" * 52)
    for sid, aspect, p, s, n_std, n_strict, ratio in rows:
        print(f"{sid:<8}{aspect:<7}{p:>6}{s:>6}{n_std:>6}{n_strict:>6}{ratio:>6.0%}")

    tp = sum(r[2] for r in rows)
    tn = sum(r[4] for r in rows)
    print("-" * 52)
    print(f"{'合计':<8}{'':<7}{tp:>6}{'':>6}{tn:>6}{'':>6}{tn/tp:>6.0%}")
    print(f"\ncore {words(core)} 词（上限 {CORE_MAX}），full {words(full)} 词")

    fat = [r for r in rows if r[6] > 0.70]
    if fat:
        print(f"\n{len(fat)} 条限制占比超 70%，正文偏短（<140 词），抽卡时留神是否被限制词带偏：")
        print("  " + "  ".join(r[0] for r in fat))

    if problems:
        print(f"\n{len(problems)} 项超阈值：")
        for line in problems:
            print("  " + line)
    else:
        print("\n全部在阈值内。")

    if not args.check:
        print(f"\n默认版 → {OUT}")
        print(f"加严版 → {OUT / 'strict'}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())