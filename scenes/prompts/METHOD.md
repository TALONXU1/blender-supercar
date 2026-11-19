# 方法论 · F1 场景提示词

沉淀到能直接用的程度：一套赛道真实规则、两段常驻提示词、一个填空模板。24 个场景库留作参考，日常只需要这几页。

---

## 一、三层，不多不少

| 层 | 作用 | 词数 | 变不变 |
|---|---|---|---|
| 常驻头 | 摄影与质感 | 53 | **永不变** |
| 正文 | 这一帧是什么 | 90–150 | 每次写 |
| 常驻尾 | 限制 | 51 | **永不变** |

常驻头尾复制粘贴，只写正文。这是唯一能保证 24 张图风格一致的做法——每张重写画风句，模型给你 24 种略微不同的胶片。

---

## 二、常驻头（质感）

放最前，一字不改。

```
35mm cinema camera, natural colour science, physically plausible light.
Surfaces carry real wear: brake dust on the wheel rims, rubber marbles scattered
off the racing line, stone chips on the nosecone, scuffed paint on the barriers,
fabric wrinkles in the sponsor banners, asphalt patches and tar seams. Fine film
grain, 180 degree shutter.
```

**为什么是这些词**：质感不来自"highly detailed"这类空话，来自**具体的劣化痕迹**。刹车粉尘、橡胶屑、石击坑、护栏掉漆、广告布褶皱、沥青补丁——六个具体物件，比二十个形容词管用。

**别改的理由**：它描述的是"所有赛道都有"的东西。改一处就要重测全部场景。

---

## 三、常驻尾（限制）

放最后，一字不改。

```
No text, logos, watermarks or added graphics. Sponsor panels are blank coloured
surfaces, no invented branding, no real team livery or driver likeness. Single
continuous photographic frame, one car, four wheels, halo present, no closed
cockpit. No plastic sheen, no HDR oversaturation, no melted or duplicated parts.
Add nothing not requested.
```

**五条各管一件事**：文字与水印 / 品牌与版权 / 单帧单车主形体 / 材质不做假 / 防它自作主张加设计。

第五句最容易被省，也最贵——Sunburst 会把提示词当创作简报读，省了它就在角落给你加边框和宣传语。

---

## 四、赛道真实规则 R1–R10

这十条是"懂不懂 F1"的分界线。每条都是模型最容易画错的点。

### R1 沥青不是均匀的灰

赛车线上有压黑的橡胶带，越靠弯心越黑；路面有补丁、裂缝、沥青灌缝。

```
dark rubbered racing line, asphalt patches, tar-filled seams
```
反面：`smooth grey asphalt`（像停车场）

---

### R2 路肩是聚氨酯块，不是白线

白红或白黑交替的凸起块，带螺丝孔，边缘被磨圆、有破损。

```
alternating white and red raised kerb blocks, worn rounded edges, bolt holes
```
反面：`white line`（那是标线不是路肩）

---

### R3 护栏是波形钢或混凝土块

Armco 波形钢或 Tecpro 混凝土块，约 1 米高，掉漆露金属，有撞击凹痕。

```
wave-profile steel barrier at one metre height, paint chipped to bare metal,
impact dents
```
反面：`white wall`（像围墙）

---

### R4 防护网只在需要的地方

立柱加钢丝网，3.5 米以上，顶部后倾 45 度。只在有观众的弯道外侧。

```
catch fencing on steel posts, four metres tall, angled back at the top,
visible mesh pattern against the sky
```
反面：绕整圈赛道挂网（真实赛道大部分没有）

---

### R5 广告是布，不是印刷

帆布或网格布绷在护栏上，有褶皱、被轮胎擦黑、边缘起毛、下缘被水泡皱。

```
stretched vinyl banners with visible wrinkles, scuffed black along the lower
edge, frayed hem
```
反面：`sponsor logos on barriers`（会画成平面贴图，还会自己编品牌）

---

### R6 缓冲区只有两种，不能混

草地（割痕、泥点、车辙）或砾石坑（米色石子、轮胎印、边缘排水沟）。一条赛道用哪种是固定的。

```
grass run-off with mowing stripes and mud flicked onto the surface
gravel trap of pale beige stones, tyre tracks crossing it, drainage grate at the edge
```
反面：草地下面接砾石（两种都画，两种都不像）

---

### R7 看台是脚手架搭的

钢管骨架、临时座椅、防水布、电缆。人是密集个体，颜色杂乱，没有空看台。

```
scaffold-framed grandstand, temporary seats, waterproof sheeting, dense crowd
as individual varied figures
```
反面：`stadium`（给你一个体育场）

---

### R8 赛道边有人，但不在赛道上

穿橙色连体服的裁判站在护栏后，持旗、灭火器、担架。

```
marshal in orange overalls behind the barrier, holding a yellow flag
```
反面：赛道上出现人（模型有时会加，必须靠限制尾巴压）

---

### R9 "真的在跑"的三个证据

刹车粉尘、橡胶屑、热浪。有这三样，静止画面也有速度感。

```
brake dust drifting, rubber marbles on the kerb, heat haze above the tarmac
```

---

### R10 不存在的东西（一票否决）

```
no traffic markings, no lane dividers, no traffic lights, no street lamps in
daylight, no pedestrians on track, no painted arrows
```

模型不知道赛道和公路的区别，它会加车道虚线、红绿灯、路牌。这是最常见的废图原因。

---

## 五、填空模板

```
[常驻头]

[镜头] 高度 _ m，_ mm，[运动方式]，主体在画面 _ 。
[主体] 车的位置、朝向、状态。
[环境] 2–3 个该赛道识别符号 + 1 条 R 规则。
[光照] 太阳 _ 度，_ K，云量 _ ，能见度 _ ，路面 _ 。

[常驻尾]
```

**现实约束**：识别符号 2–3 个，材质细节 1–2 个。写多了模型平均分配注意力，每个都画不彻底。

---

## 六、一次完整输入

以银石雨后为例，88 词正文 + 常驻头尾：

```
35mm cinema camera, natural colour science, physically plausible light. Surfaces
carry real wear: brake dust on the wheel rims, rubber marbles scattered off the
racing line, stone chips on the nosecone, scuffed paint on the barriers, fabric
wrinkles in the sponsor banners, asphalt patches and tar seams. Fine film grain,
180 degree shutter.

Tracking shot at 1.1 metres, 50mm, parallel with the car at matched speed. The
car exits a fast right-hander, three-quarters away from camera. Wide grass
run-off with mowing stripes, a grey scaffold grandstand behind, bare steel barrier
at one metre. Just after rain: sun at 30 degrees, 4800K, four oktas, thin mist
rising off the warm asphalt. The racing line is dark and drying, the edges still
hold standing water. Visibility eight kilometres.

No text, logos, watermarks or added graphics. Sponsor panels are blank coloured
surfaces, no invented branding, no real team livery or driver likeness. Single
continuous photographic frame, one car, four wheels, halo present, no closed
cockpit. No plastic sheen, no HDR oversaturation, no melted or duplicated parts.
Add nothing not requested.
```

数一下信息密度：镜头 3 个参数、环境 3 个符号 + R3/R5/R6 三条规则、光照 5 个物理量。没有一句形容词。

---

## 七、视频怎么接

图出来之后，别把上面那段粘进视频模型。视频只要三句：

```
The car tracks left to right through the corner, body staying level. Water sprays
off the rear tyres and thins out within fifteen metres. Camera tracks parallel at
matched speed. 5 seconds.

Keep: the wet asphalt, the dark racing line, the grey grandstand.
Avoid: no camera shake, no extra vehicles, no slow motion.
```

40–80 词，一个主动作，写清方向。**图写状态，视频写运动**——同样的雨，图里是"路面反光成镜面"，视频里是"雨丝斜落、水雾拖尾"。

---

## 八、交给模型前的四问

1. 有 R10 的禁项吗？（车道线、红绿灯、路人）
2. 路肩写的是块还是线？护栏写的是钢还是墙？
3. 质感靠的是六个具体劣化痕迹，还是"highly detailed"？
4. 常驻头尾还在吗？

四条过，出图合格率能到七成。剩下的三成靠场景专属限制，那是库里的活。