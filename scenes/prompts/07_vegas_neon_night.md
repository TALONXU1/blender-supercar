# S7 · 维加斯 · 深夜干冷

## 镜头 1 · 直道尽头长焦，车从光海出来

**EN**
```
Static 400mm at 1.5 meters, looking down the Strip. The car emerges from a wall
of neon as a pure black silhouette, rimmed only by cyan and magenta spill. Giant
LED screens on both sides, content scrolling. The car resolves into detail only
in the last hundred meters.
```

**中文**
```
1.5 米高度 400mm 静态，沿 Strip 大道望去。赛车从一整面霓虹里浮出，先是纯黑的剪影，只有青与品红的光渗在边缘。两侧巨型 LED 屏在滚动内容。直到最后一百米车才显出细节。
```

---

## 镜头 2 · 高机位俯拍光带切过城市

**EN**
```
Aerial static at 120 meters, 35mm, looking down at 50 degrees. The circuit cuts
a bright band across a dark grid of streets. Desert blackness beyond the city
edge. A giant illuminated sphere structure glows at the frame edge. No clouds,
stars faintly visible.
```

**中文**
```
120 米高空静态，35mm，下俯 50 度。赛道像一条亮带切过深色的街道网格。城市边缘之外是沙漠的黑。画面边缘一座巨型发光球体建筑在亮。无云，能隐约看见星星。
```

---

## 镜头 3 · 车侧跟拍霓虹流动

**EN**
```
Tracking camera 2 meters beside the car, 50mm, matched speed. Neon reflections
slide across the carbon fibre and the matte bodywork, cyan then magenta then
white as the car passes each source. Cold 8 degree night air, no humidity,
therefore no light cones, crisp specular highlights.
```

**中文**
```
车侧 2 米跟拍，50mm，同速。霓虹反射在碳纤维与哑光车身上滑动，经过每个光源时依次是青、品红、白。8 度干冷夜，无湿度，因此没有光锥，高光锐利清晰。
```

---

## 天气段（W9 夜间，干冷）

```
Night, desert climate. Air 9 degrees, humidity 25 percent: no visible light
cones, crisp clean specular highlights. Sky pure black with faint stars.
Illumination from a floodlight grid at 5500K plus thousands of coloured
emissive sources from signage. No fog, no haze, visibility 20 kilometers.
```

```
夜，沙漠气候。气温 9 度，湿度 25%：没有可见光锥，高光锐利干净。天空纯黑，有微弱星光。照明来自 5500K 泛光灯阵，加上招牌的数千个彩色自发光源。无雾无霾，能见度 20 公里。
```

---

## 环境段（Las Vegas Strip）

```
Las Vegas Strip Circuit, 6.2 kilometers, 1.9 kilometers of it a straight down
the boulevard. Both sides lined with casino facades, giant LED billboards,
a spherical arena covered in LED panels, pedestrian bridges. Flat desert terrain
beyond. Concrete barriers close to the line, no run-off.
```

```
拉斯维加斯 Strip 赛道，6.2 公里，其中 1.9 公里是沿大道的直道。两侧是赌场立面、巨型 LED 广告牌、一座覆满 LED 面板的球体场馆、人行天桥。之外是平坦沙漠。混凝土护栏贴近赛车线，无缓冲区。
```

---

## 质量段

```
Photorealistic, 35mm, extreme dynamic range handled with deep blacks and
clipped neon, cold clean air rendering, sharp specular, subtle anamorphic flare
on the brightest sources.
```

---

## 视频模型补充

- 干冷夜的关键词是 `no humidity, therefore no light cones`——这个否定句能防止模型套用新加坡式的雾光
- 霓虹要写"色序"：`cyan then magenta then white as the car passes each source`，模型会做出流动感
- 长焦镜头写 `resolves into detail only in the last hundred meters`，控制形体的显现节奏
- 不要写 `glamorous`、`luxurious`，会得到广告片质感而不是赛车片

## 已知失败模式

| 现象 | 原因 | 修法 |
|---|---|---|
| 出现雾光 | 模型默认夜景加雾 | 明确 `humidity 25%, no light cones` |
| 霓虹糊成白团 | 没控制 bloom | 写 `clipped neon with deep blacks between` |
| 城市像贴图 | 立面缺结构 | 加 `pedestrian bridges, casino facades, a spherical LED arena` |