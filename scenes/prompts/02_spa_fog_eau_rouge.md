# S2 · 斯帕 · 雾中上山

## 镜头 1 · Eau Rouge 底部仰拍

**EN**
```
Camera at 0.6 meters, tilted up 15 degrees, 85mm lens, static on the grass
beside the barrier. The car bursts out of white fog at the bottom of the hill
and climbs away from camera through the Eau Rouge right-left. Fog pours over
the crest behind it. Red rain lights burn soft halos in the murk.
```

**中文**
```
摄影机高 0.6 米，上仰 15 度，85mm 静态架在护栏外草地上。赛车从坡底的白雾中冲出，沿 Eau Rouge 右-左弯爬坡远离镜头。雾气从身后坡顶倾倒下来。红色尾灯在昏暗里晕成柔光团。
```

---

## 镜头 2 · 无人机上升跟随落差

**EN**
```
Aerial rising shot, 24mm, 40 meters altitude climbing to 90 meters, following
the car up the hillside. Dense pine forest below, a narrow ribbon of wet asphalt
cutting through it. The elevation drop of 40 meters becomes visible as the
camera rises. Fog banks sit in the valleys between trees.
```

**中文**
```
无人机上升镜头，24mm，从 40 米升至 90 米，跟随赛车爬坡。下方是密集松林，一条湿沥青窄带穿过林间。随镜头升高，40 米落差显现。雾团滞留在树间的谷地里。
```

---

## 镜头 3 · 车载视角前车只剩雾团

**EN**
```
Onboard camera behind the halo, 18mm, wide. The car ahead is 15 meters away
and reduced to a diffuse red glow inside the fog. Wipers not active but the
visor is beaded. Trees pass as dark vertical smears. The road surface is wet
and featureless.
```

**中文**
```
Halo 后方车载机位，18mm 广角。前车在 15 米外，只剩雾中一团弥散的红光。雨刷未启动，面罩上有水珠。树木以深色竖条掠过。路面湿滑、细节不可辨。
```

---

## 天气段（W8 雾 + W5 湿）

```
Dense fog with visibility 100 meters. Sun reduced to a pale disc at 7000K,
no hard shadows. Light shafts angle down through gaps in the pine canopy.
Everything beyond 80 meters dissolves into white-grey. Track surface fully wet,
reflecting only diffuse sky. Air temperature 12 degrees, high humidity.
```

```
浓雾，能见度 100 米。太阳被削弱成苍白圆盘，7000K，无硬影。光柱沿松树冠的缝隙斜射下来。80 米外的一切溶进灰白。路面全湿，只反射漫射天光。气温 12 度，高湿度。
```

---

## 环境段（Spa）

```
Circuit de Spa-Francorchamps in the Belgian Ardennes, 7 kilometers through pine
forest and steep elevation change. No grandstands in most sections, only grass
banks and trees. Guardrails dark with moisture. The track climbs 40 meters
through the Eau Rouge and Raidillon sequence, then drops through the forest.
```

```
斯帕-弗朗科尔尚赛道，位于比利时阿登森林，7 公里穿越松林与陡峭落差。大部分路段没有看台，只有草坡和树。护栏被水汽浸成深色。赛道在 Eau Rouge–Raidillon 段爬升 40 米，然后穿过森林下降。
```

---

## 质量段

```
Photorealistic, 35mm anamorphic, cool desaturated palette, deep atmospheric
perspective, volumetric fog with correct light scattering, fine film grain.
```

---

## 视频模型补充

- 雾的**梯度**必须写：`fog thick at ground level, thinning above 3 meters`，否则模型给全屏白墙
- 长焦镜头里车要 "emerge from the fog" 而不是 "appear"，动词决定过渡质量
- 无人机镜头必须给起止高度，否则模型给一个悬停画面
- 不要写 "cinematic drone shot" 这种空词，直接给高度和焦段

## 已知失败模式

| 现象 | 原因 | 修法 |
|---|---|---|
| 全屏白 | 雾没写梯度也没写能见度 | 补 `visibility 100m` + 高度衰减 |
| 坡不够陡 | 只写 hill 没写数值 | 写 `40 meter elevation change over 400 meters` |
| 森林像贴图 | 没说树种的疏密 | 加 `dense pine forest, trunks visible, canopy closed` |