# 限制词库 · Sunburst 版

Sunburst 没有独立 negative prompt 字段，所有限制都写在正文里。这决定了两个写法：

1. **禁令要成句**，不能只写一个词。`no text` 弱，`No text anywhere in the frame, no letters, no numbers, no signage copy` 强。
2. **锁定用肯定句**。要精确控制的东西，写成 `exactly and only: <字符串>`，比一堆 no 有效。

Sunburst 的三个固有倾向，限制词就是针对它们写的：

- 把提示词当**创作简报**读，会补上你没要求的东西（宣传语、边框、装饰金箔、换掉你指定的底座形状）
- 往**写实**漂（即使你要风格化），材质细节越堆越多
- **弧线/艺术字排版容易出乱码**，平面直排反而更准

---

## 一、三层装配

限制词不是越长越好，也不是越短越好——**要分层**。全量塞进去，24 个场景每条都是 180 词，模型开始对着禁令画；只给一句 `no text`，Sunburst 会在角落给你签名并自创一句宣传语。

| 层 | 词数 | 内容 | 何时用 |
|---|---|---|---|
| `core` | 62（硬上限 65） | 文字/品牌/边框/单车体/不添加 | **每张必带** |
| `scene` | 23–46（硬上限 50） | 这张最容易画错的那 3–4 条 | 每张按场景配 |
| `full` | 112 | 人群/构图/输出卫生/风格漂移 | 出图不合格时才追加 |

装配：`positive + "\n\n" + core + " " + scene`，返工时再加 `full`。

**为什么设绝对值上限而不是比例**：正文只有 120 词时，62 词 core 天然占 52%，这个数字不说明任何问题。真正有意义的信号是 core 有没有膨胀、scene 有没有把 full 层的东西提前塞进来。比例只做统计参考，超 70% 时说明正文偏短，抽卡时要留意画面是否被限制词带偏。

---

## N0 · 通用四句（每张都带）

```
No text, letters, numbers, watermarks, signatures, logos, or UI elements anywhere
in the frame. No borders, frames, or decorative graphic elements added by the
renderer. Single continuous photographic frame, not a collage or split panel.
```

```
画面任何位置都没有文字、字母、数字、水印、签名、标识或界面元素。不添加边框、画框或渲染器自创的装饰元素。单张连续影像，不是拼贴或分屏。
```

这四句是底裤。少了它们，Sunburst 会在角落给你签个名。

---

## N1 · 文字与标识（F1 场景重灾区）

赛车场天然布满广告，模型会**自己编赞助商**。这是最容易毁图的一条，也是唯一必须逐图检查的一条。

**全禁版**（默认用这个，后期在 Blender/PS 里贴真广告）
```
No sponsor logos, no brand marks, no invented signage copy. Barrier advertising
panels are present as blank coloured panels only, with no readable characters.
No banner text on grandstand roofs, no numbers on cars except a single plain
race number.
```

**锁定版**（必须出现文字时）
```
Exactly and only these three strings appear, verbatim, in plain sans-serif:
"SCENE 01", "LAP 12", "SECTOR 2". No other copy, no taglines, no subtitles,
no captions, no additional signage text.
```

**要点**
- 别用 `no logos` 了事——写清楚"广告板是纯色空板"，模型才知道该画什么替代
- 弧面/曲面上的文字一律禁止（Sunburst 弧排必乱码），要文字就放平面
- 中文/艺术字在 Sunburst 上不稳定，要就单独出图再合成

---

## N2 · 品牌与身份

```
No real Formula 1 team liveries, no real constructor branding, no real driver
likeness or helmet design, no real sponsor trademarks, no identifiable
real-world championship logos. The car is an original generic single-seater
design, not a reproduction of any existing car.
```

```
不使用任何真实 F1 车队涂装、制造商标识、车手肖像或头盔设计、真实赞助商商标、可辨识的赛事标志。车辆为原创通用单座赛车设计，不复刻任何现役车型。
```

要的就是"看起来是 F1 但不是某支车队"。这条同时解决版权和一致性两个问题。

---

## N3 · 车辆形体

F1 车是最容易被模型改坏的对象——多一个轮子、前翼少一片、进气口消失。

```
Single car only, no other vehicles in frame. Four wheels, correct open-wheel
layout, one front wing with two endplates, one rear wing, one halo. No closed
cockpit, no fenders, no roof, no doors, no road-car proportions. Bodywork is
symmetric and continuous, no melting or duplicated parts, wheels not detached
or duplicated, no visible driver body outside the cockpit opening.
```

```
画面中只有一辆车，没有其他车辆。四个轮子，正确的开轮布局，一个前翼带两个端板，一个尾翼，一个 Halo。没有封闭座舱、挡泥板、车顶、车门，不是民用车比例。车身对称连续，没有融解或重复部件，轮子不脱落不重影，座舱开口之外看不到车手身体。
```

**动态场景追加**（有速度感时）
```
Wheels remain circular and attached under motion blur. No ghosting of separate
car silhouettes. Motion blur applies to background and wheels only, the car body
stays sharp.
```

---

## N4 · 赛道与环境

模型会把所有赛道画成同一条"通用赛道"。必须用识别符号顶住。

```
The circuit layout shown must match the described corner sequence: <具体的弯/地形描述>.
No generic oval, no stadium circuit, no kart track, no public road with
lane markings. No painted centre line, no traffic signs, no street lamps except
where specified, no road markings other than white track-limit lines and kerbs.
```

```
所画赛道形状必须对应描述中的弯道序列：<填具体弯>. 不是通用椭圆、不是体育场环道、不是卡丁车道、不是带车道线的公路。除白色赛道边线和路肩外，没有其他路面标线、没有交通标志、没有路灯（除非指定）。
```

**场景专属替换**（把 `<...>` 换掉）
| 场景 | 顶住识别的说法 |
|---|---|
| S1 银石 | `airfield-derived long straights with wide grass run-off, no gravel traps` |
| S2 斯帕 | `40 meter elevation change through a continuous uphill left-right, pine forest on both sides, no grandstands` |
| S3 摩纳哥 | `3.3 km street circuit, barriers 30 cm from the line, no run-off anywhere, a tunnel section` |
| S4 蒙扎 | `long straights joined by tight chicanes, woodland pressing against barriers` |
| S5 新加坡 | `street circuit at night under floodlight towers, wet asphalt, high-rise facades on both sides` |
| S6 赞德福特 | `sand dunes on both sides, one banked corner at 18 degrees, no trees` |
| S7 维加斯 | `1.9 km straight down a boulevard lined with LED billboards, flat desert beyond` |
| S8 英特拉格斯 | `track sits below surrounding terrain, viewed from above, counter-clockwise downhill left-right` |

---

## N5 · 人群与看台

```
Crowd is rendered as a dense mass of individual small figures with varied poses
and clothing colours, not as a repeated texture tile, not as a flat painted band.
No visible individual faces at distance, no duplicated identical figures in a
row, no mannequins, no empty grandstands where spectators are described.
```

```
人群是密集的个体小人，姿态和衣着颜色各异，不是重复贴图，不是一条平面画带。远处看不到个人的脸，没有一排完全相同的重复人形，不是模特假人，描述有观众的地方不能是空看台。
```

---

## N6 · 光与材质

```
Lighting follows the specified sun elevation and colour temperature exactly.
No plastic or vinyl sheen on painted surfaces. No HDR over-saturation, no
bloom on every highlight, no lifted blacks, no uniform studio lighting.
Carbon fibre reads as woven twill, not as flat grey. Wet surfaces show
sharp specular reflections of the sky and light sources, not a uniform gloss.
```

```
光照严格服从指定的太阳高度角与色温。漆面没有塑料或乙烯基反光。没有 HDR 过饱和，不是每个高光都发光，黑位不下压，不是均匀的影棚布光。碳纤维是可见的斜纹编织，不是平灰。湿表面锐利反射天空和光源，不是一层均匀的亮漆。
```

**抗"塑料感"的补充**（Sunburst 常见病）
```
Surface response is physically plausible: rough where the material is rough,
with micro-scratches, dust in crevices, tyre rubber laid down on the racing line.
```

---

## N7 · 构图与镜头

```
Single lens, single focal length as specified. No fisheye distortion unless
stated, no wide-angle edge stretching on the car, no forced perspective on the
trackside objects. Horizon level unless a dutch angle is specified. Subject
occupies the stated portion of frame, not centred by default.
```

```
单一镜头、指定焦段。除指定外不用鱼眼畸变，车身没有广角边缘拉伸，赛道边物体不夸张透视。除指定荷兰角外地平线水平。主体占画面指定比例，不默认居中。
```

---

## N8 · 输出卫生

```
No low-resolution upscaling artifacts, no JPEG blocking, no oversharpening
halos, no AI plastic skin on human faces, no melted fine detail, no repeated
identical texture patches, no visible generation seams.
```

```
没有低分辨率放大痕迹、JPEG 块状噪点、过度锐化光晕、人脸上的 AI 塑料皮肤、细节融解、重复的相同纹理块、可见的生成接缝。
```

---

## N9 · Sunburst 专属漂移（必带）

这一组是这次实测出来的，针对它"当简报读、自己加设计"的毛病。

```
Do not add any element not explicitly requested. Do not add decorative borders,
corner ornaments, metallic foil accents, framing lines, or graphic overlays.
Do not invent taglines, captions, credits, or copy of any kind. Do not change
the shape or material of any object that was specified. Do not shift the
rendering style away from what is described.
```

```
不添加任何未明确要求的元素。不加装饰边框、角饰、金属箔点缀、画框线、图形叠加层。不自创标语、字幕、署名或任何文案。不改变已指定物体的形状或材质。不偏离所描述的画面风格。
```

**为什么这三句必须带**：实测里 Sunburst 会给副标题加框线、给墨迹加金箔、把指定为矩形的底座换成圆形并按弧线排字排成乱码。它不是在"画错"，是在"做设计"。

---

## 十组速查表

| 组 | 内容 | 必带 | 典型失效 |
|---|---|---|---|
| N0 | 文字/水印/边框/拼贴 | ✓ 每张 | 角落出现签名 |
| N1 | 赞助商与广告文案 | ✓ F1 场景 | 编造不存在的品牌 |
| N2 | 真实车队/车手/商标 | ✓ | 画出可辨识的红牛涂装 |
| N3 | 车辆形体 | ✓ | 五个轮子、封闭座舱 |
| N4 | 赛道识别 | ✓ | 所有赛道变同一条 |
| N5 | 人群 | 有观众时 | 重复贴图人墙 |
| N6 | 光与材质 | ✓ | 塑料感、过饱和 |
| N7 | 构图与镜头 | 长焦/广角时 | 车身边缘拉伸 |
| N8 | 输出质量 | ✓ | 融解细节、锐化光晕 |
| N9 | Sunburst 漂移 | ✓ 每张 | 自创文案、换底座、加边框 |

---

## 二十四块场景专属限制（速查）

| 场景 | 必须禁止的 | 必须锁定的 |
|---|---|---|
| S1 银石 | 砾石坑、山地、干燥路面、蓝天无云 | 机场直边、草地缓冲区、干湿分界线 |
| S2 斯帕 | 看台、平地、晴朗天空、干燥路面 | 40 米落差、松林、能见度 100 m |
| S3 摩纳哥 | 缓冲区、砾石坑、宽赛道、现代玻璃塔 | 30 cm 墙距、游艇、隧道口 |
| S4 蒙扎 | 砾石坑、树林缺失、阴天、蓝调 | 减速弯、老混凝土看台、热浪高度 40 cm |
| S5 新加坡 | 日光、干燥路面、天空可见星星、无护栏 | 灯柱光锥、湿度 82%、镜面湿路面 |
| S6 赞德福特 | 树、山、饱和蓝天、平坦弯道 | 沙丘、18 度倾斜、橙色人群 |
| S7 维加斯 | 雾、湿度光锥、白天、植被 | 1.9 km 直道、LED 球体建筑、9 度干冷 |
| S8 英特拉格斯 | 平地赛道、蓝天、干燥、欧洲式看台 | 盆地俯视、云底 400 m、黄绿光渗 |