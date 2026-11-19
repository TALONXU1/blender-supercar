# 天气预设库 W1–W10

同一个赛道换天气，等于换一部片子。这份表把"天气"拆成可以填进 Blender 和填进提示词的两组参数。

用法：`SCENE_OPTIONS.md` 里每个场景卡指定一个主天气预设，提示词里的天气段就从这里抄。

---

## 参数速查

| 编号 | 名称 | 太阳高度 | 色温 | 云量 | 能见度 | 路面 | 难度 |
|---|---|---|---|---|---|---|---|
| W1 | 正午硬光 | 60–70° | 5500–5800K | 0–1/8 | >20 km | 干、高温 | 低 |
| W2 | 黄金时刻 | 5–12° | 3200–4000K | 1–3/8 | >15 km | 干 | 低 |
| W3 | 蓝调时刻 | −2 至 −8° | 天光 9000–12000K + 灯 3200K | 2–4/8 | 8–15 km | 干 | 中 |
| W4 | 阴天漫射 | 云层遮蔽 | 6500–7500K | 7–8/8 | 10–20 km | 干、灰 | 低 |
| W5 | 阵雨 | 任意（通常低） | 6000–7000K | 8/8 | 300–800 m | 全湿、镜面 | 高 |
| W6 | 雨后初晴 | 20–40° | 4500–5500K | 3–5/8 | 5–10 km | 半湿、干湿线、蒸发雾 | 高 |
| W7 | 雷暴 | 云底 300–600 m | 5500K + 紫灰环境 | 8/8 积雨云 | <200 m | 积水、飞溅 | 极高 |
| W8 | 雾 | 任意 | 7000–8000K | 8/8 | 50–200 m | 湿冷 | 中高 |
| W9 | 夜间泛光 | 无太阳 | 灯 4000–6000K | 任意 | 1–8 km（湿则低） | 干或湿 | 中高 |
| W10 | 侧风扬尘 | 30–60° | 4800–5500K | 2–4/8 高云 | 1–3 km | 干、表面浮沙 | 中 |

---

## W1 · 正午硬光

**物理**：太阳接近天顶偏南，阴影短且边缘锐利。沥青表面 55–65°C，贴地 10–40 cm 有折射热浪。天空蓝到发白，地平线附近几乎无色。

**Blender（EEVEE）**：Sun 强度 4–6，角度 0.5–1.0°（越小阴影越硬），天空用物理天空或纯渐变 HDRI，关掉体积雾。热浪靠后期或一层极薄的折射介质。

**提示词关键词（EN）**
```
harsh overhead midday sun, hard-edged short shadows, 5500K neutral daylight,
bleached highlights on asphalt, visible heat shimmer above the tarmac,
deep blue sky fading to white at the horizon, high contrast, no fill light
```

---

## W2 · 黄金时刻

**物理**：太阳 5–12°，光穿更厚大气，短波被散射。阴影拉长到车长的 3–8 倍，边缘柔和。逆光时车身轮廓有一圈暖边，碳纤维表面高光呈铜色。

**Blender**：Sun 暖色 (1.0, 0.72, 0.45)，强度 3–4，天空半球光偏冷做补，阴影 openness 提高。

**提示词（EN）**
```
low golden-hour sun at 8 degrees, long soft shadows raking across the track,
warm 3600K rim light on every edge, copper highlights on carbon fibre,
backlit dust motes, amber haze near the horizon, cool blue shadows as fill
```

---

## W3 · 蓝调时刻（黄昏/黎明）

**物理**：太阳已落到地平线下，天光变成深蓝，人造光源开始主导。这是 F1 里最"电影"的时段——阿布扎比、巴林、卡塔尔都用它。

**Blender**：世界背景 9000–12000K 深蓝，太阳关或强度 0.1，泛光灯/看台灯 3200–4500K 点亮，曝光压在中间调偏暗。

**提示词（EN）**
```
blue hour, sun below the horizon, deep cobalt sky with a thin magenta band,
artificial floodlights at 3200K kicking in, mixed colour temperature,
long exposure feel, silhouetted grandstands, wet-looking sheen on the surface
```

---

## W4 · 阴天漫射

**物理**：云层当巨型柔光箱，无方向性硬影，对比度低，颜色饱和但灰。赞德福特、银石阴天的常态。**最容易渲，也最容易渲得没劲**——必须靠材质细节和构图救。

**Blender**：Sun 关掉，世界背景 7000K 均匀亮度 1.0–1.5，加一点天顶到地面的梯度。AO 拉高。

**提示词（EN）**
```
overcast flat light, giant softbox sky, no directional shadows,
muted desaturated palette, soft ambient occlusion in every crevice,
low contrast, matte surfaces, grey-white sky with subtle texture
```

---

## W5 · 阵雨

**物理**：雨滴 6–8 mm 直径，下落 8–9 m/s，风一吹就是斜的。路面水膜形成镜面，反射天空和尾灯。车后 2–15 m 是白色水雾锥，越长车速越高。能见度 300–800 m，远处物体溶进灰白。

**Blender**：粒子雨（或几何节点实例）+ 路面 roughness 0.05–0.15 + 屏幕空间反射打开 + 体积雾 density 0.01–0.03。水雾用 billboard 粒子在车后发射。

**提示词（EN）**
```
heavy rain, rain streaks angled 20 degrees by crosswind, mirror-wet asphalt
reflecting the sky and brake lights, thick white spray plume 10 meters behind
the car, visibility 500 meters, distant objects dissolving into grey,
dark storm light, water beading and streaming on bodywork
```

---

## W6 · 雨后初晴

**物理**：最上镜的状态。路面半干，赛车线已经被轮胎压干成深色带，线外仍湿亮。地表水蒸发形成 20–100 cm 高的薄雾，逆光下是金色的。天空还有残云，太阳角度低。

**Blender**：湿/干分区靠材质遮罩（沿赛车线 UV 做遮罩），蒸发雾用低密度体积 + 太阳光散射。

**提示词（EN）**
```
just after the rain, low sun breaking through broken clouds,
drying line down the middle of the track, dark dry racing line with wet
glossy edges, thin golden mist rising off the warm asphalt, backlit steam,
puddles holding sky reflections, saturated colours after rain
```

---

## W7 · 雷暴

**物理**：积雨云底 300–600 m，天空从铅灰到紫黑，光被压成侧向的黄色缝隙。雨强 >30 mm/h，能见度 <200 m，赛道积水反光成黑色镜面。闪电照亮整个云层。

**Blender**：天空用低亮度紫灰渐变，闪电靠一两帧的强点光/自发光面，雨量加倍，加水面涟漪。

**提示词（EN）**
```
severe thunderstorm, near-black purple cumulonimbus ceiling at 400 meters,
eerie yellow-green light leaking under the cloud base, torrential rain,
standing water on track reflecting nothing but darkness, lightning flash
illuminating the cloud interior, visibility under 200 meters
```

---

## W8 · 雾

**物理**：斯帕清晨/傍晚的招牌。能见度 50–200 m，200 m 外的车只剩两个红点。雾里光会形成光柱，颜色随太阳位置变。

**Blender**：体积雾 density 0.05–0.15 + 高度衰减，太阳光开体积散射。

**提示词（EN)**
```
dense fog, visibility 100 meters, trees fading into white nothing at 80 meters,
headlights and rain lights blooming into visible cones, sun a pale disc
through the murk, moisture on the lens, monochrome grey-green palette
```

---

## W9 · 夜间泛光

**物理**：F1 夜赛用高显色 LED 灯阵，4000–6000K，照度均匀到 2000+ lux。灯柱在湿空气里形成可见光柱。天空纯黑或深蓝，无星。车灯（尾灯雨灯）在长焦里爆成红色光斑。

**Blender**：多点光阵列（面光，尺寸大、强度低、数量多），曝光锁在灯下正确、天空自然压黑，bloom 适度。

**提示词（EN）**
```
night race under a grid of floodlight towers, 5000K even illumination,
visible light shafts cutting through humid air, pure black sky,
red tail lights blooming into bokeh, high contrast pools of light and shadow,
cool white highlights on carbon, spectators as dark silhouettes
```

---

## W10 · 侧风扬尘

**物理**：赞德福特海风、巴林沙漠风。沙粒贴地 0–2 m 横扫，能见度 1–3 km，整体偏暖黄，太阳变成可直视的橙盘。

**Blender**：世界背景加暖黄色偏，体积散射 + 地面粒子。远景用雾把地平线糊掉。

**提示词（EN）**
```
strong crosswind, sand and dust streaming low across the track at ankle height,
hazy warm yellow atmosphere, sun reduced to an orange disc, visibility 2 km,
flags whipping horizontal, grit visible against backlit surfaces
```

---

## 组合规则

- 一个场景**只用一个主预设**，不要"半雨半晴"这种糊状描述，模型会给出四不像。W6 是唯一允许的混合态，因为它有明确的物理依据（干湿分界）。
- 时段（太阳高度）和天气解耦：W5 阵雨可以配正午，也可以配黄昏，色温跟着太阳走。
- 夜间（W9）不与其他叠加，只加"湿"或"干"一个修饰。
- 提示词里天气段放在**镜头段之后、材质段之前**，先定空间再定光。

## 落到 Blender 的工作量

| 预设 | 只需改 | 需要新建 |
|---|---|---|
| W1 / W2 / W4 | 太阳角度、色温、世界背景 | 无 |
| W3 / W9 | 光照 + 曝光 + bloom | 灯柱几何、看台灯 |
| W5 / W6 / W7 | 材质 roughness、雾 | 雨粒子系统、水雾 billboard、积水遮罩 |
| W8 | 体积雾 | 无（可能要加强远景） |
| W10 | 世界背景 + 体积 | 地面粒子、风向旗 |

现有工程 `V5_07_Lighting` 只有一套太阳+补光，W1/W2/W4 是改参数就能出，其余属于环境层开发。
