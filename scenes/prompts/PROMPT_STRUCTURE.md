# 三类提示词的结构与分工

同一个镜头要过三道模型：**画风**定眼睛，**关键帧**定画面，**视频**定变化。三者写同一件事，但语法完全不同——混着写就是最常见的失分原因。

---

## 一、一句话分工

| 类型 | 回答的问题 | 作用域 | 长度 | 输入对象 |
|---|---|---|---|---|
| 画风提示词 | 用什么眼睛看 | **跨场景常量** | 20–40 词 | 全局，所有图共用 |
| 关键帧提示词 | 这一帧长什么样 | 单帧 | 120–220 词 | 文生图 / 图生图 |
| 视频提示词 | 从这一帧开始怎么变 | 单镜头 3–6 秒 | 40–80 词 | 图生视频（首帧=关键帧） |

**核心原则：视频提示词不是关键帧提示词的扩写，是差分量。** 图已经把画面定死了，视频模型只需要知道"哪里动、往哪动、多快"。

---

## 二、画风提示词

### 结构

```
[媒介与光学] + [色彩科学] + [对比与黑位] + [颗粒/缺陷] + [参考锚]
```

```
Shot on 35mm film, Kodak Vision3 500T stock. Warm highlights, cool shadows,
lifted blacks with visible grain structure. Mild halation around bright sources,
slight gate weave. Desaturated midtones, no digital sharpening.
```

### 三条规则

1. **画风是常量，只写一次**。抽成 `ST` 编号（见 [style_library.md](style_library.md)），在每张图里引用编号而不是重写句子。重写会让 24 张图之间产生微小的风格漂移——每张措辞略有不同，模型就给你 24 种略微不同的胶片。
2. **画风管"怎么看"，不管"看什么"**。写"35mm 胶片、暖高光冷阴影、可见颗粒"是画风；写"F1 赛车在雨中"是内容。混进去会让画风段喧宾夺主。
3. **画风不能和物理参数打架**。画风说"lifted blacks"，正文说"纯黑天空"——两个指令对着干，模型随机选一个。夜间场景要么换画风，要么把"纯黑"改成"deep shadows with faint detail"。

### 位置

画风段放**最前**（第一句就定眼睛），或者**最后紧挨限制词**。中间位置会被内容描写淹没。

---

## 三、关键帧提示词

### 结构（本项目已在用）

```
[画风 STn] + [镜头：高度/焦段/景别/机位] + [主体：位置/朝向/状态]
+ [环境：3–5 个识别符号] + [光照：太阳高度/色温/云量/能见度/路面状态]
+ [材质细节] + [质量] + [限制尾巴]
```

### 关键点

- **镜头参数是构图指令，必须在前**。高度 1.1 m、50mm——这两个数字决定了画面像不像赛车片，比任何形容词都重要。
- **识别符号要 3–5 个，不能多**。多到 8 个，模型会平均分配注意力，每个都画得不彻底。
- **光照写物理量不写情绪**。`30 degrees, 4800K, 4 oktas` 有效；`dramatic lighting` 无效。
- **限制词在最后**，三层装配（core 62 / scene 23–46 / full 112 返工用）。

### 常见错误

把"要动起来"的意图写进关键帧——`the car is accelerating`、`spray flying backwards`。图是静止的，这些词会让模型画出运动模糊以外的怪东西。**运动属于视频提示词。**

---

## 四、视频提示词

### 结构（按 animator 方法论）

```
[主体动作 + 方向] + [次要动态 1–2 个] + [镜头运动] + [速度/节奏]
+ [时长] + [保持项] + [禁止项]
```

```
The car tracks left to right across frame at speed, body staying level
through the corner. Wheel spray trails behind and thins out. Camera tracks
parallel at matched speed, foreground grass sweeping past. Fast, constant
pace. 5 seconds. Keep the wet asphalt and the grey grandstand behind.
No text, no extra vehicles, no camera shake.
```

### 五条硬规则

| 规则 | 说明 |
|---|---|
| **一个主动作** | 写两个竞争动作（加速+转向+喷雾）模型三个都做不好。选一个。 |
| **明确方向** | `left to right` / `toward camera` / `background to foreground`。写"移动"等于没写。 |
| **时长服从物理** | 3 s：转头、避让、车从远处到近处；5 s：过弯、穿隧道；6 s：爬坡、穿越场景。跑 300 m 在 3 秒是不可能的。 |
| **区分主体与镜头** | 必写 `Camera static` 或 `Camera tracks at matched speed`。不写，模型自己摇。 |
| **不重复关键帧内容** | 静态描述压到 20 词以内，只留"锁住画面不漂"的最小信息。写满 150 词，模型会重构画面而不是让它动起来。 |

### 保持项与禁止项（视频版的限制词）

视频模型的失败模式和生图不同，禁止项也不同：

```
Keep: <2–3 个必须不变的东西>      例：the wet asphalt, the grey grandstand
Avoid: <2–3 个视频特有的漂移>      例：no camera shake, no morphing geometry,
                                       no extra vehicles, no slow motion,
                                       no scene change
```

**视频模型比生图模型更容易改掉画面**。它会把 3 秒里发生的事情当成一个完整叙事来重新编排——加一辆车、换个镜头、切个场景。禁止项就是用来钉住这些的。

---

## 五、信息分工表（哪个词该写在哪类里）

这是最容易搞混的部分。同一个信息在三类里出现时写法完全不同，或者根本不该出现。

| 信息 | 画风 | 关键帧 | 视频 | 说明 |
|---|---|---|---|---|
| 焦段 50mm | ✗ | **必写** | ✗ | 图里是构图，视频里提焦段会改构图 |
| 机位高度 1.1m | ✗ | **必写** | 只写"保持机位" | 视频模型不精确理解高度 |
| 太阳高度/色温 | ✗ | **必写** | ✗ | 视频模型改不了光照，写了白写 |
| 胶片颗粒 | **必写** | ✗ | ✗ | 画风常量，图里不重复 |
| 雨 | ✗ | 写"镜面湿路面" | 写"雨丝斜穿、水雾拖尾" | 图写状态，视频写运动 |
| 人群 | ✗ | 写"个体各异的人" | 写"人群轻微起伏" | 图写密度，视频写动态 |
| 限制词 | 1 条（不加装饰） | 三层装配 | 保持项+禁止项 | 三者都需要，但形态不同 |
| 时长 | ✗ | ✗ | **必写** | 只有视频有意义 |

---

## 六、交接协议

### 图 → 视频

```
画风 STn（常量）
   └→ 关键帧提示词（120–220 词）→ 出图 → 选定帧
                                          └→ 视频提示词（40–80 词，首帧=选定帧）
```

**规则**：视频提示词的头一句必须能接上关键帧的构图。"car tracks left to right" 只在关键帧里车是侧向构图时成立；如果关键帧是迎面来车，就得写 "car approaches and fills frame"。

**降级**：如果视频模型给的首帧和你的关键帧不一样（很多平台会重绘第一帧），把关键帧作为参考图喂进去，而不是指望文字描述。

### 命名

```
<画风ID>_<场景ID>_<机位ID>        ST1_S1_01
<画风ID>_<场景ID>_<机位ID>_vid    ST1_S1_01_vid
```

一个镜头的图、视频、返工版本都靠这个前缀串起来。换画风就换前缀，不覆盖旧的。

---

## 七、三个最常见的失败

| 现象 | 真实原因 | 修法 |
|---|---|---|
| 视频几乎静止 | 把关键帧提示词整段粘进视频模型，静态描述占 90% | 砍到 40–80 词，只留主动作 |
| 视频里车变了形状 | 没写保持项，模型重绘 | 加 `Keep: the car's silhouette and livery unchanged` |
| 24 张图风格不一致 | 每张重写了画风句 | 抽成 ST 编号，只引用 |

---

## 八、在本项目里的落地

| 层 | 文件 |
|---|---|
| 画风 | [style_library.md](style_library.md) — ST1–ST6，可叠加到任意场景 |
| 关键帧 | [prompt_library.json](prompt_library.json) → [compiled/](compiled/) 24 个 txt |
| 视频 | [video_library.json](video_library.json) → [compiled_video/](compiled_video/) 24 个 txt |
| 限制词 | [negative_library.md](negative_library.md) — 三层装配 |

装配脚本两个：`build_prompts.py`（图）、`build_video_prompts.py`（视频）。都带阈值检查。