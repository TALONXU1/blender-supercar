# S1 · 银石 · 阵雨转晴

拼接顺序：**镜头段 → 天气段 → 环境段 → 车体段 → 质量段**。车体段从 `docs/F1_IMAGE25_PROMPTS.md` 的 `[F1-BODY-EN]` 抄，不要重写。

---

## 镜头 1 · 低机位追车过弯（主图）

**EN**
```
Tracking shot at 1.1 meter height, 50mm lens, shallow depth of field on the
foreground grass. A single-seater race car exits a fast right-hander, camera
tracking parallel with the car at the same speed. Wet grass blades with water
droplets in the extreme foreground, out of focus. The car is sharp, mid-frame,
angling away from camera.
```

**中文**
```
1.1 米高度追车镜头，50mm 镜头，前景草叶浅景深。一辆单座赛车从高速右弯出弯，摄影机与车平行同速跟随。极前景是带水珠的湿草叶，失焦。车体清晰，位于画面中部，正背向镜头偏转。
```

---

## 镜头 2 · 长焦压缩穿越看台

**EN**
```
Static long lens at 200mm from grandstand level, heavy background compression.
The car approaches head-on and fills the frame. Behind it, the wet circuit
stretches back to a grey multi-storey grandstand. Heat has not yet returned;
the air is still clean after the rain.
```

**中文**
```
看台高度，200mm 静态长焦，强烈背景压缩。赛车迎面驶来占满画面。车后是湿亮的赛道延伸至灰色多层看台。热气尚未回来，雨后空气仍然干净。
```

---

## 镜头 3 · 车后 3 米跟拍水雾

**EN**
```
Camera 3 meters behind and 0.8 meters above the car, 35mm, following at speed.
A white spray plume erupts from both rear tyres, catching the low sun and
turning gold-white. The drying racing line is dark matte; the edges of the
track still hold standing water and mirror the sky.
```

**中文**
```
摄影机在车后 3 米、高 0.8 米，35mm，高速跟随。两条白色水雾锥从后轮喷出，被低角度阳光打成金白色。正在变干的赛车线是深色哑光，赛道边缘仍有积水并倒映天空。
```

---

## 天气段（W6 雨后初晴，直接拼在所有镜头后）

```
Just after the rain. Low sun at 30 degrees breaking through broken clouds,
4 oktas cover, 4800K. A thin golden mist rises off the warm asphalt and is
backlit into visible steam. Puddles hold sky reflections. Colours are
saturated, contrast medium-high. Visibility 8 kilometers.
```

```
雨后初晴。30 度低角度阳光穿过破碎云层，云量 4/8，4800K。薄金色雾气从温热沥青上蒸起，逆光下成为可见蒸汽。积水倒映天空。色彩饱和，中高对比。能见度 8 公里。
```

---

## 环境段（Silverstone）

```
Silverstone Circuit, a former WWII airfield in Northamptonshire. Long straight
edges inherited from runways, wide grass run-off areas instead of gravel,
low grey grandstands with fabric roofs, green rolling English countryside
beyond the fences. Flat terrain, no elevation change.
```

```
银石赛道，北安普敦郡一座二战机场改建。笔直的跑道边线、宽阔的草地缓冲区（没有砾石坑）、灰色织物顶棚的低矮看台、护栏外是起伏的英国绿野。地形平坦，无高差。
```

---

## 质量段

```
Photorealistic, 35mm cinema camera, natural colour science, fine grain,
no HDR oversaturation, physically plausible wet-surface reflectance,
motion blur matched to 180 degree shutter.
```

---

## 视频模型补充（动起来时加）

- 时长 5–8 s，单个动作，不要一镜多事件
- 明确"camera tracking parallel at same speed"，否则模型会让车冲出画面
- 水雾必须写 "plume trails behind the car and dissipates within 15 meters"，不写会糊成一片白
- 不要写 "slow motion"，速度和镜头距离的匹配比升格更重要

## 已知失败模式

| 现象 | 原因 | 修法 |
|---|---|---|
| 路面像塑料 | 只写了 reflective，没写 wet 的粗糙度层次 | 加 "mirror-wet in the puddles, matte on the drying line" |
| 车在漂 | 视频模型默认匀速 | 明确 "car decelerates into the corner, body rolls" |
| 雾糊满全屏 | 没给能见度上限 | 写 "visibility 8 km, mist only in the first 2 meters above ground" |