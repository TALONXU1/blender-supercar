# S4 · 蒙扎 · 正午硬光

## 镜头 1 · 直道尽头 300mm 迎车

**EN**
```
Static 300mm lens at barrier height, 1.0 meter. The car approaches head-on down
the main straight at 340 km/h, compressed against the treeline behind it. Heat
shimmer distorts the distant grandstand. The car grows from a dot to filling
frame in three seconds.
```

**中文**
```
护栏高度 1.0 米，300mm 静态长焦。赛车沿主直道以 340 km/h 迎面驶来，被压缩在身后的树林前。热浪让远处看台扭曲。车在三秒内从一个点长到占满画面。
```

---

## 镜头 2 · 弯心低机位横掠

**EN**
```
Camera at 0.7 meters, 70mm, static inside the first chicane. The car brakes hard
from 340 to 80 km/h, nose diving, then snaps left-right through the kerbs.
Heat distortion ripples in the foreground. Tyre marbles kick up and scatter.
```

**中文**
```
摄影机高 0.7 米，70mm，静态位于一号减速弯内侧。赛车从 340 硬刹到 80 km/h，车头下压，然后在路肩上左-右急转。前景有热浪波纹。轮胎碎屑被卷起飞散。
```

---

## 镜头 3 · 车顶跟拍直道极速

**EN**
```
Overhead follow camera 2.5 meters above the car, 24mm, tracking at full speed.
The straight stretches to a vanishing point between trees. The white line blurs
into a continuous streak. Grandstand roofs pass below as grey shapes.
```

**中文**
```
车顶上方 2.5 米跟拍，24mm，全速跟随。直道在树林之间延伸到消失点。白色边线糊成连续的拖影。看台顶棚以灰色块状从下方掠过。
```

---

## 天气段（W1 正午硬光）

```
Harsh overhead sun at 65 degrees, 5700K, cloudless. Short hard-edged shadows
directly beneath the car. Asphalt surface at 60 degrees, bleached highlights.
Heat shimmer rises in the first 40 centimeters above the tarmac, distorting
everything behind it. Sky deep blue at zenith, almost white at the horizon.
```

```
65 度正午硬光，5700K，无云。车底正下方是短促锐利的阴影。沥青表面 60 度，高光发白。贴地 40 厘米内有热浪升腾，扭曲其后方的一切。天顶深蓝，地平线附近近乎白。
```

---

## 环境段（Monza）

```
Autodromo Nazionale Monza inside the Royal Villa park. Long straights connected
by tight chicanes. Dense broadleaf woodland pressing against the barriers.
Old concrete grandstands with cantilevered roofs, faded red and grey. Trackside
trees casting dappled shadow across the kerbs. Tifosi crowds in red.
```

```
蒙扎国家赛车场，位于皇家别墅公园内。长直道由紧凑减速弯连接。茂密阔叶林紧贴护栏。老式混凝土看台带悬挑顶棚，褪色的红与灰。赛道边的树在路肩上投下斑驳阴影。穿红衣的 tifosi 人群。
```

---

## 质量段

```
Photorealistic, long telephoto compression, high contrast hard light, bleached
highlights, deep saturated shadows, visible heat distortion, 400 ASA film look.
```

---

## 视频模型补充

- 直道镜头必须给速度数值，`at 340 km/h` 比 `very fast` 有效十倍
- 热浪要写"高度"：`heat shimmer in the first 40 cm above the tarmac`，不写高度会糊全屏
- 减速弯镜头写 `nose dives under braking`，这是唯一能让模型表现出减速度的措辞
- 长焦镜头别写 `shallow depth of field`，会毁掉压缩感，写 `background compressed against the car`

## 已知失败模式

| 现象 | 原因 | 修法 |
|---|---|---|
| 车看起来只有 100 km/h | 没有速度参照物 | 加 `white line blurs into a continuous streak` |
| 热浪糊成噪点 | 没给空间范围 | 写 `first 40 cm above the tarmac` |
| 蒙扎变银石 | 只有树没有看台特征 | 加 `old concrete grandstands with cantilevered roofs` |