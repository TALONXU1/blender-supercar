# 画风库 ST1–ST6

画风是**跨场景常量**：定一次，所有图共用。写进每张图会让 24 张之间产生微小的风格漂移。

用法：选一个 ST 编号，把它的 EN 段放在关键帧提示词最前。同一个序列里不换编号。

---

## ST1 · 写实电影（默认）

**一句话**：现代数字电影机的干净写实，最不容易出错，也最不容易出彩。

```
Shot on a modern large-format digital cinema camera, 35mm equivalent framing.
Natural colour science, neutral white balance. Deep but detailed shadows, no
crushed blacks. Fine grain, no digital sharpening, mild highlight rolloff.
Physically plausible light response.
```

| 项 | 值 |
|---|---|
| 适用 | 全部 8 个场景，尤其是要"像转播画面升级版"的时候 |
| 不适用 | 想要年代感或强烈情绪时 |
| 失效表现 | 容易渲成"商业图库风"，缺乏记忆点 |
| 与限制词冲突 | 无 |

---

## ST2 · 纪录片 / 赛事转播

**一句话**：长焦多、机位远、有小瑕疵，像真的在看比赛。

```
Documentary sports coverage look. Long telephoto compression, camera
occasionally slightly off-level. Realistic broadcast colour grade, mild
chromatic aberration at frame edges, sensor dust specks, gentle vignetting.
Not colour-graded for beauty, graded for legibility.
```

| 项 | 值 |
|---|---|
| 适用 | S1 银石、S4 蒙扎、S6 赞德福特（这三站的"真实感"比"美"重要） |
| 不适用 | S3 摩纳哥、S7 维加斯（这两站靠美感） |
| 失效表现 | 容易画出"低清感"，需要盯住分辨率 |
| 与限制词冲突 | 与"no oversharpening"配合良好；与"no low-res artifacts"要平衡——写"camera imperfections, not compression artifacts" |

---

## ST3 · 胶片复古

**一句话**：颗粒、光晕、轻微晃动，给历史场景或情绪镜头。

```
Shot on 35mm film, Kodak Vision3 500T. Warm highlights, cool shadows, lifted
blacks with visible grain. Halation blooming around bright sources, slight gate
weave, soft corner falloff. Slightly desaturated midtones.
```

| 项 | 值 |
|---|---|
| 适用 | S8 英特拉格斯雷暴（情绪）、纽北/历史赛道、S2 斯帕雾（胶片拍雾最好看） |
| 不适用 | S5/S7 夜赛（halation 会让霓虹糊成白团） |
| 失效表现 | 颗粒过重导致细节丢失，车看起来像模型 |
| 与限制词冲突 | **"lifted blacks" 与 "pure black sky" 直接矛盾**，夜赛必须二选一 |

---

## ST4 · 冷调夜赛

**一句话**：为泛光灯下的一切准备，高对比、干净黑、锐利高光。

```
Night sports photography grade. Cool 5000–6000K white balance, deep clean
blacks with no lift, crisp specular highlights, controlled bloom on point
sources only. Slight anamorphic flare on the brightest lights. Minimal grain.
```

| 项 | 值 |
|---|---|
| 适用 | S5 新加坡、S7 维加斯 |
| 不适用 | 白天场景（会渲成阴天） |
| 失效表现 | 黑位压太狠导致车身失去轮廓 |
| 与限制词冲突 | 与"no HDR oversaturation"要配合写，否则霓虹会溢出 |

---

## ST5 · 阴天低饱和

**一句话**：为 W4 阴天/雾准备，靠材质和构图撑，不靠光。

```
Overcast documentary grade. Low contrast, muted palette, no colour push.
Neutral 7000K white balance, soft ambient occlusion in every crevice,
matte surfaces. Detail carried by texture and shape rather than by light.
```

| 项 | 值 |
|---|---|
| 适用 | S2 斯帕雾、S6 赞德福特阴天 |
| 不适用 | 需要色彩冲击的场景 |
| 失效表现 | 渲成"没打光的灰"，画面没有焦点 |
| 抢救 | 保留一个高饱和元素（S6 的橙色人群），其余全部压低 |

---

## ST6 · 高对比商业

**一句话**：为车身特写和主视觉准备，饱和、锐利、有意图。

```
High-end automotive commercial grade. Punchy contrast, saturated but accurate
colour, razor-sharp specular detail on painted and carbon surfaces, controlled
highlights, clean blacks. Every reflection deliberate.
```

| 项 | 值 |
|---|---|
| 适用 | S7-03 车侧霓虹、任何 3:2 车身特写、封面图 |
| 不适用 | 广角环境镜头（会显得假） |
| 失效表现 | 塑料感、过饱和，像游戏渲染 |
| 与限制词冲突 | 与"no plastic sheen"正面冲突，必须同时写"paint reads as automotive lacquer with clearcoat, not vinyl" |

---

## 场景推荐表

| 场景 | 主画风 | 备选 | 理由 |
|---|---|---|---|
| S1 银石阵雨 | ST2 | ST1 | 英国赛事的真实感大于美感 |
| S2 斯帕雾 | ST3 | ST5 | 胶片拍雾的层次最好 |
| S3 摩纳哥黄昏 | ST1 | ST6 | 黄金时刻本身就是滤镜 |
| S4 蒙扎正午 | ST2 | ST1 | 硬光+长焦=转播感 |
| S5 新加坡夜雨 | ST4 | ST1 | 必须干净黑，否则霓虹糊 |
| S6 赞德福特阴天 | ST5 | ST2 | 阴天只靠材质和橙色人群 |
| S7 维加斯深夜 | ST4 | ST6 | 干冷夜赛 + 车身特写用 ST6 |
| S8 英特拉格斯雷暴 | ST3 | ST1 | 情绪的片子用胶片 |

---

## 三条使用规则

1. **一个序列一个编号**。S1 三张图都用 ST2，不要 01 用 ST2、02 用 ST1——剪在一起会跳。
2. **画风不重复写进图里**。图上只引用 `ST2` 这个标记（在文件名和 JSON 的 `style` 字段里），实际句子由编译脚本注入一次。
3. **换画风就换前缀**，不要覆盖旧文件。`ST2_S1_01.png` 和 `ST3_S1_01.png` 并存，方便对比。

---

## 画风与限制词的三处冲突（必须处理）

| 冲突 | 现象 | 处理 |
|---|---|---|
| ST3 `lifted blacks` × 正文 `pure black sky` | 夜景变成灰雾 | 夜赛禁用 ST3，或把正文改成 `deep shadows with faint detail` |
| ST6 `saturated` × 限制词 `no HDR oversaturation` | 车身颜色失真 | 写 `saturated but accurate colour`，两个词一起给 |
| ST6 `razor-sharp detail` × 限制词 `no oversharpening halos` | 边缘出现白边 | 写 `optically sharp, not digitally sharpened` |

这三处不是文字游戏，是模型真的会按字面执行。冲突指令的结果是随机二选一。