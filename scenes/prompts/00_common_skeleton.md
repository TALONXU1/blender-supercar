# 通用提示词骨架

任何场景都按这个顺序拼，不要乱序。模型对**前置的空间信息**服从度最高，对**后置的材质/质量词**服从度最低——所以重要的东西往前放。

---

## 五段式

```
[1 镜头段]  → [2 天气段] → [3 环境段] → [4 车体段] → [5 质量段]
```

| 段 | 必须包含 | 不要包含 |
|---|---|---|
| 镜头 | 高度（米）、焦段（mm）、运动方式、主体在画面中的位置 | "cinematic"、"epic"、"beautiful" |
| 天气 | 太阳高度角、色温、云量、能见度、路面状态 | 情绪词（"moody"、"dramatic"） |
| 环境 | 3–5 个该站独有的视觉符号 + 地形/植被/建筑类型 | 地名堆砌（模型对地名理解差，对结构理解好） |
| 车体 | 从 `docs/F1_IMAGE25_PROMPTS.md` 抄 `[F1-BODY-EN]` | 重新描述车型，会破坏已调好的形体 |
| 质量 | 画幅、胶片/数字感、颗粒、动态范围处理 | "8k, masterpiece, best quality" 这类无意义堆叠 |

---

## 镜头段速查

| 运动 | 英文写法 | 什么时候用 |
|---|---|---|
| 静态 | `static, camera locked off` | 长焦迎车、弯心横掠 |
| 平行跟随 | `tracking parallel at matched speed` | 侧面展示车身 |
| 车后跟随 | `following 3 meters behind at 0.8 meters height` | 展示水雾/尾灯/扩散器 |
| 摇 | `panning with the car, background streaking` | 快速过弯 |
| 升降 | `rising from 40 meters to 90 meters` | 展示地形落差 |
| 俯拍 | `static aerial at 90 meters looking down 50 degrees` | 展示赛道形状 |
| 车载 | `onboard behind the halo, 18mm` | 第一人称压迫感 |

**高度是赛车镜头最重要的参数**：0.4–1.5 m 是"贴地"，2–5 m 是"车高"，10–30 m 是"看台"，60–150 m 是"航拍"。写错高度，画面就不像赛车片。

---

## 焦段速查

| 焦段 | 效果 | 用途 |
|---|---|---|
| 18–24 mm | 广角，透视夸张，边缘拉伸 | 车载、仰拍灯柱、俯拍赛道 |
| 28–35 mm | 自然广角，有环境关系 | 贴地横移、隧道出口 |
| 50 mm | 接近人眼 | 通用跟拍 |
| 70–85 mm | 轻度压缩，主体突出 | 弯心、迎车 |
| 135–200 mm | 强压缩，背景贴到主体上 | 看台视角、跨赛道 |
| 300–400 mm | 极强压缩，空间被压平 | 直道尽头迎车 |

---

## 天气段公式

```
[时段 + 太阳高度] + [色温] + [云量] + [可见的大气现象] + [能见度] + [路面状态]
```

例：
```
Golden hour, sun at 9 degrees, 3400K, 1 okta cover, long soft shadows,
visibility 15 kilometers, dry surface.
```

不要写"天气很好"、"气氛紧张"，写**光的行为**。

---

## 三条硬规则

1. **一个镜头一个动作**。视频模型一次只能理解一件事，写两个动作会得到两个都做不好的结果。
2. **数字优先于形容词**。`340 km/h`、`18 degrees`、`30 centimeters`、`2000 lux` 都比"极快"、"很陡"、"很近"、"很亮"有效。
3. **不要否定模糊的肯定**。写 `no fog, no haze` 有效；写 `not too dark` 无效，模型不知道"too"是多少。

---

## 车体段（直接复制）

从 [../../docs/F1_IMAGE25_PROMPTS.md](../../docs/F1_IMAGE25_PROMPTS.md) 的 `A1 主视角` 取英文段。如果场景是远景/剪影，用精简版：

```
A 2035 Formula 1 concept car, matte navy blue with bare carbon fibre aero
surfaces, thin cyan LED strip along the floor edge, low wedge monocoque,
floating thin-strut halo, two-element rear wing with vertical strakes.
```

---

## 质量段（三选一）

**写实电影**
```
Photorealistic, 35mm cinema camera, natural colour science, fine grain,
180 degree shutter motion blur, physically plausible light response.
```

**写实但冷调**
```
Photorealistic, cool desaturated palette, deep shadows, fine film grain,
no digital sharpening.
```

**胶片感（复古场景用）**
```
Shot on 35mm film, Kodak Vision3 500T, halation on highlights, visible grain,
slight gate weave, soft corner falloff.
```