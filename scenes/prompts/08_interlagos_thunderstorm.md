# S8 · 英特拉格斯 · 雷暴

## 镜头 1 · 看台俯拍赛道在下方

**EN**
```
Camera at 14 meters in the grandstand, 70mm, static, looking down at 25 degrees.
The circuit sits below the surrounding ground level, so the viewer looks into a
basin. Rainwater sheets across the asphalt in moving films. Puddles connect into
standing lakes reflecting nothing but the black sky.
```

**中文**
```
看台 14 米高处，70mm 静态，下俯 25 度。赛道低于周边地面，观众是俯视一个盆地。雨水以流动水膜横扫沥青。积水连成静止的水面，只倒映黑色的天。
```

---

## 镜头 2 · 低机位逆光雨幕

**EN**
```
Camera at 0.8 meters directly in front of the car's path, 85mm. The car drives
into frame, headlights and rain light cutting white and red cones through the
downpour. Rain streaks fully visible against the dark. Spray from the front
wheels fans out to both sides.
```

**中文**
```
摄影机高 0.8 米，正对来车方向，85mm。赛车驶入画面，头灯与雨灯在暴雨中切出白与红的光锥。雨丝在暗背景上完全可见。前轮水花向两侧扇开。
```

---

## 镜头 3 · 长焦跟车过 Senna S，黑云翻滚

**EN**
```
Long lens 200mm tracking the car through the downhill left-right. Behind it,
the horizon is a wall of purple-black cumulonimbus, its underside at 400 meters,
a single yellow-green light leak under the cloud base. The car is a hard-edged
silhouette against that light.
```

**中文**
```
200mm 长焦跟随赛车通过下坡左-右弯。车后地平线是一整面积雨云墙，云底 400 米，云底之下漏出一道黄绿色的光。车在这道光前是硬边剪影。
```

---

## 天气段（W7 雷暴）

```
Severe thunderstorm. Cumulonimbus base at 400 meters, near-black with purple
tonality, a yellow-green light leak along the horizon under the cloud. No direct
sun. Torrential rain over 30 mm per hour, visibility under 200 meters. Standing
water on track. Air 22 degrees, saturated. Occasional lightning illuminates the
cloud interior for a single frame.
```

```
强雷暴。积雨云底 400 米，接近全黑偏紫，云底沿地平线漏出一道黄绿光。无直射阳光。暴雨每小时 30 毫米以上，能见度低于 200 米。赛道积水。气温 22 度，空气饱水。偶发闪电以单帧照亮云层内部。
```

---

## 环境段（Interlagos）

```
Autódromo José Carlos Pace in São Paulo, 4.3 kilometers, counter-clockwise,
built into a natural bowl so the track sits below the surrounding terrain.
Grandstands and embankments look down onto the circuit. Concrete walls and
chain-link fencing close to the line. Beyond the fence, dense hillside
neighbourhoods and Atlantic forest. No gravel traps, grass is saturated green.
```

```
英特拉格斯赛道，圣保罗，4.3 公里，逆时针，建在天然盆地中，赛道低于周边地形。看台与土坡都是俯视赛道。混凝土墙与铁丝网贴近赛车线。护栏外是密集的山坡住宅与大西洋雨林。没有砾石坑，草地饱和的绿。
```

---

## 质量段

```
Photorealistic, 35mm, high dynamic range under storm light, deep shadow detail,
rain rendered as physical streaks not noise, natural grain, cool green-grey
palette with a single warm light leak.
```

---

## 视频模型补充

- 雷暴的核心是**云底高度**和**光渗**：`cumulonimbus base at 400 meters, yellow-green light leak under the cloud`，这两句决定成不成
- 闪电写 `for a single frame`，否则模型给一整段闪光
- 逆光雨幕要写光源位置：`backlit by the light leak on the horizon`
- 盆地地形写 `the viewer looks down into a basin`，这是英特拉格斯唯一的空间签名

## 已知失败模式

| 现象 | 原因 | 修法 |
|---|---|---|
| 黑成一团 | 车和背景都没有轮廓光 | 必须给逆光或云底光渗 |
| 雨像噪点 | 没写雨的物理形态 | 写 `physical streaks, 30 mm per hour` |
| 变成普通雨战 | 缺盆地地形 | 加 `track below surrounding terrain, viewed from above` |