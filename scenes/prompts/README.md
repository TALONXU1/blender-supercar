# scenes/prompts/ — 提示词库

## 日常只看两个文件

| 文件 | 内容 |
|---|---|
| **[METHOD.md](METHOD.md)** | **方法论**：常驻头尾、赛道真实规则 R1–R10、填空模板、一次完整输入 |
| **[STANDING.txt](STANDING.txt)** | 常驻头/尾的纯文本版，复制粘贴用 |

其余都是参考库，需要时再翻。

---

目标模型 **Sunburst**（GPT Image 2.5 写实档）出关键帧，图生视频模型出动态。三类提示词分开写、分开存、分开装配。

## 三类提示词的入口

| 类型 | 回答的问题 | 长度 | 文件 |
|---|---|---|---|
| **画风** | 用什么眼睛看 | 20–40 词 | [style_library.md](style_library.md) ST1–ST6 |
| **关键帧** | 这一帧长什么样 | 120–220 词 | [prompt_library.json](prompt_library.json) → [compiled/](compiled/) |
| **视频** | 从这一帧怎么变 | 40–80 词 | [video_library.json](video_library.json) → [compiled_video/](compiled_video/) |

**先看 [PROMPT_STRUCTURE.md](PROMPT_STRUCTURE.md)** —— 三类提示词的结构模板、信息分工表、交接协议、三个最常见的失败。

## 全部文件

| 文件 | 内容 |
|---|---|
| [PROMPT_STRUCTURE.md](PROMPT_STRUCTURE.md) | **三类提示词的结构与分工**（总纲） |
| [style_library.md](style_library.md) | 画风库 ST1–ST6 + 场景推荐 + 三处冲突处理 |
| [negative_library.md](negative_library.md) | 限制词库：三层装配、N0–N9 十组、24 块场景专属 |
| [prompt_library.json](prompt_library.json) | 24 个机位的关键帧正文 + 分层限制词 |
| [video_library.json](video_library.json) | 24 个机位的 motion + Keep + Avoid |
| [build_prompts.py](build_prompts.py) | 关键帧装配，core ≤65 / scene ≤50 |
| [build_video_prompts.py](build_video_prompts.py) | 视频装配，motion 40–80 词 + 方向词检查 |
| [compiled/](compiled/) | **成品图提示词**，直接粘 |
| [compiled_video/](compiled_video/) | **成品视频提示词**，直接粘 |

人读版 8 个场景：[01](01_silverstone_after_rain.md) · [02](02_spa_fog_eau_rouge.md) · [03](03_monaco_golden_harbour.md) · [04](04_monza_midday_heat.md) · [05](05_singapore_night_rain.md) · [06](06_zandvoort_dune_overcast.md) · [07](07_vegas_neon_night.md) · [08](08_interlagos_thunderstorm.md) · [00 骨架](00_common_skeleton.md)

## 一条流水线

```
选画风(STn)  →  关键帧提示词  →  出图  →  选帧  →  视频提示词  →  出片
                 compiled/              首帧       compiled_video/
```

命名：`ST2_S1_01.png`（图）、`ST2_S1_01_vid.mp4`（视频）。换画风换前缀，不覆盖。

## 重跑

```bash
python scenes/prompts/build_prompts.py          # 关键帧，24 个 → compiled/
python scenes/prompts/build_video_prompts.py    # 视频，24 个 → compiled_video/
python scenes/prompts/build_video_prompts.py --check   # 只查
```

## 三条不能忘的

1. **画风只写一次**，抽成 ST 编号。每张重写会让 24 张之间风格漂移。
2. **视频提示词不是图提示词的扩写**，是差分量。40–80 词，一个主动作。
3. **别把图提示词粘进视频模型**，150 词里 90% 是静态描述，结果是抖动的静止图。