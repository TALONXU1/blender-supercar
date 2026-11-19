# S5 · 新加坡 · 夜雨霓虹

## 镜头 1 · 低机位仰拍灯柱阵列

**EN**
```
Camera at 0.5 meters tilted up 35 degrees, 20mm wide. Floodlight towers march
into the black sky in a receding line. Every tower throws a visible cone of
light through the humid air. The car passes through pools of white light,
alternately lit and dark. Water on the asphalt doubles every light source.
```

**中文**
```
摄影机高 0.5 米，上仰 35 度，20mm 广角。泛光灯柱在黑色天空里排成递进的一列。每根灯柱都在湿空气里投出可见的光锥。赛车穿过一池池白光，明暗交替。沥青上的积水把每个光源都翻倍。
```

---

## 镜头 2 · 长焦压缩楼群与车

**EN**
```
Static 180mm from across the track. The car slides through frame left to right,
sharp. Behind it, the financial district towers fill the background, hundreds
of lit windows, neon signage in cyan and magenta bleeding onto the wet bodywork.
The city reflects off the car's carbon surfaces.
```

**中文**
```
赛道对面 180mm 静态长焦。赛车从左到右滑过画面，清晰。身后金融区高楼填满背景，数百扇亮着的窗，青与品红的霓虹招牌渗到湿车身上。城市倒映在车的碳纤维表面上。
```

---

## 镜头 3 · 车后跟拍，城市倒过来

**EN**
```
Camera 4 meters behind and 1 meter above, 30mm, following. The wet track acts
as a mirror: the entire skyline is inverted on the road surface below the car.
Rain streaks cross the frame at 20 degrees. Steam rises from the hot diffuser.
Red tail lights bloom into soft bokeh spheres.
```

**中文**
```
摄影机在车后 4 米、高 1 米，30mm 跟随。湿路面成了镜子：整片天际线倒映在车下方的路面上。雨丝以 20 度斜穿画面。热气从炙热的扩散器升起。红色尾灯散成柔和的光斑球。
```

---

## 天气段（W9 夜间泛光 + 湿）

```
Night race under a grid of floodlight towers, 5000K even illumination at 2000
lux. Air temperature 29 degrees, humidity 82 percent: the air itself is visible,
every light source throws a soft cone. Sky pure black, no stars. Heavy rain,
streaks angled 20 degrees by wind. Track surface mirror-wet.
```

```
泛光灯阵下的夜赛，5000K，照度均匀 2000 lux。气温 29 度，湿度 82%：空气本身可见，每个光源都投出柔和光锥。天空纯黑，无星。大雨，雨丝被风吹成 20 度斜角。路面镜面湿滑。
```

---

## 环境段（Marina Bay）

```
Marina Bay Street Circuit, 4.9 kilometers through Singapore's downtown. Concrete
barriers 50 centimeters from the racing line. Towering glass and steel facades
on both sides, office towers, hotel balconies, a triple-tower hotel with a
roof deck spanning them. Sponsor banners strung between light towers. Palm trees
at the pit exit. Spectators in soaked shirts packed behind the barriers.
```

```
滨海湾街道赛道，4.9 公里穿行新加坡市区。混凝土护栏距赛车线 50 厘米。两侧是高耸的玻璃与钢立面、写字楼、酒店阳台、一座横跨三塔的屋顶平台建筑。灯柱之间拉着赞助商横幅。维修区出口有棕榈树。湿透的观众挤在护栏后。
```

---

## 质量段

```
Photorealistic, anamorphic 40mm, high contrast night photography, visible
volumetric light cones, specular streaks on wet asphalt, controlled bloom on
point sources, deep blacks with no lifted shadows.
```

---

## 视频模型补充

- 夜赛必须写明 `湿度` 和 `光锥`，否则模型给一个干净的黑夜，像停车场
- `mirror-wet` 是关键词，能同时触发反射和雨
- 车尾灯写 `bloom into soft bokeh spheres`，不写就是两个死红点
- 不要写 `neon city lights` 这种笼统词，要写具体颜色和材质（`cyan signage bleeding onto wet carbon`）

## 已知失败模式

| 现象 | 原因 | 修法 |
|---|---|---|
| 夜赛变黑糊 | 没给照度 | 加 `2000 lux even illumination` |
| 光柱不出现 | 没写湿度 | 加 `humidity 82%, the air itself is visible` |
| 城市像布景板 | 立面没有层次 | 写 `hundreds of lit windows, balconies, signage` |