# S6 · 赞德福特 · 沙丘阴天

## 镜头 1 · 倾斜弯外侧低机位

**EN**
```
Camera at 0.9 meters on the outside of the banked corner, 45mm, static. The
track surface tilts 18 degrees away from the camera like the inside of a bowl.
The car runs high on the banking, body rolled into the slope. Sand blows across
the upper edge of the kerb in a thin horizontal stream.
```

**中文**
```
倾斜弯外侧 0.9 米机位，45mm 静态。赛道路面以 18 度向镜头外倾斜，像碗的内壁。赛车跑在倾斜面上高位，车身顺着坡滚转。沙粒在路肩上缘以细横向流掠过。
```

---

## 镜头 2 · 沙丘顶部俯拍

**EN**
```
Aerial static at 60 meters, 24mm, looking down at 40 degrees. The circuit snakes
between smooth sand dunes with sparse marram grass. The track is a dark ribbon
cutting through pale sand. Beyond the dunes, a flat grey North Sea horizon.
```

**中文**
```
60 米高空静态，24mm，下俯 40 度。赛道在平滑沙丘之间蜿蜒，沙丘上稀疏长着滨草。赛道是切过浅色沙地的一条深色带。沙丘之外是灰平的北海地平线。
```

---

## 镜头 3 · 侧面长焦，沙粒横穿

**EN**
```
Static 135mm side-on at 1.2 meters. The car passes left to right behind a
foreground of blowing sand. Grains streak horizontally across the frame,
partially obscuring the lower half of the car. Behind it, a solid orange wall
of spectators in the grandstand, softly out of focus.
```

**中文**
```
侧面 135mm 静态，高 1.2 米。赛车从左到右经过，前景是扬起的沙。沙粒横向拉成条纹穿过画面，遮住车身下半部分。车后是看台上一整面橙色观众墙，柔和失焦。
```

---

## 天气段（W4 阴天 + W10 侧风）

```
Overcast flat light, no directional shadows, 7000K. Cloud layer is a giant
softbox, contrast low, colours muted but saturated in the orange crowd.
Strong crosswind at 45 km/h from the sea, sand streaming low across the track
at ankle height. Visibility 12 kilometers, air slightly gritty.
```

```
阴天漫射光，无方向性阴影，7000K。云层是一块巨型柔光布，对比低，颜色发灰但人群的橙色仍然饱和。来自海面的 45 km/h 强侧风，沙粒贴地在脚踝高度横扫赛道。能见度 12 公里，空气略带颗粒感。
```

---

## 环境段（Zandvoort）

```
Circuit Zandvoort in the North Sea dunes, 4.26 kilometers. Smooth sand dunes
with marram grass on both sides, no trees. A banked corner tilted at 18 degrees.
Low grandstands packed with spectators dressed entirely in orange. Grey North
Sea sky, flat horizon. Sea breeze constant.
```

```
赞德福特赛道，位于北海沙丘之间，4.26 公里。两侧是平滑沙丘和滨草，没有树。一个 18 度倾斜弯。低矮看台挤满全身橙色的观众。灰白的北海天空，平直地平线。海风持续。
```

---

## 质量段

```
Photorealistic, 50mm, low contrast overcast palette, muted greens and greys
against saturated orange, fine sand grain in the air, natural film response.
```

---

## 视频模型补充

- 阴天场景的唯一救星是**色彩对比**：写明 `muted grey-green sand against saturated orange crowd`
- 沙粒要写 `at ankle height`，否则模型给沙尘暴
- 倾斜弯必须给角度 `18 degrees`，不写就是普通弯道
- 不要写 `dramatic sky`，阴天的价值就是没有戏剧性

## 已知失败模式

| 现象 | 原因 | 修法 |
|---|---|---|
| 画面发灰无重点 | 没有色彩锚 | 加橙色人群/橙色旗作为唯一高饱和元素 |
| 沙变沙尘暴 | 没限高度和浓度 | 写 `thin stream at ankle height` |
| 弯道看不出倾斜 | 机位与弯道平行 | 明确 `camera on the outside looking across the banking` |