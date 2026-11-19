# S3 · 摩纳哥 · 港湾黄昏

## 镜头 1 · 高机位俯拍港湾与赛道

**EN**
```
High angle from 90 meters above the harbour, 35mm lens, static. The circuit
runs along the edge of the water. Dozens of white motor yachts packed into the
marina, their hulls softly lit by low sun. Apartment blocks climb the hillside
behind in stacked terraces. The track is a narrow grey band between barriers
and water, with no run-off anywhere.
```

**中文**
```
港湾上方 90 米高机位，35mm 静态。赛道沿水边延伸。数十艘白色游艇挤在码头，船体被低角度阳光柔化。身后山坡上的公寓楼层层叠叠成台地。赛道是护栏与水面之间的一条窄灰带，全程没有缓冲区。
```

---

## 镜头 2 · 贴地横移擦墙

**EN**
```
Camera at 0.4 meters, 28mm, tracking laterally at car speed, barrier in the
immediate foreground. The car fills the right third of frame, passing 30
centimeters from the wall. Sponsor decals on the barrier strobe past as
horizontal smears. Beyond the barrier, the sea catches low sun in broken
white glints.
```

**中文**
```
摄影机高 0.4 米，28mm，横移跟随车速，护栏就在极前景。车占画面右侧三分之一，距墙 30 厘米掠过。护栏上的赞助商贴纸以横向拖影频闪而过。护栏之外，海面在低阳下碎成白色亮点。
```

---

## 镜头 3 · 隧道出口逆光

**EN**
```
Inside the tunnel looking out at the exit, 50mm, static. The tunnel interior is
near black. The car exits into blown-out warm sunlight, its silhouette rimmed
in orange. For half a second the car is a shape, not an object. Light spills
back into the tunnel across the road surface.
```

**中文**
```
隧道内朝出口拍摄，50mm 静态。隧道内部近乎全黑。赛车冲进过曝的暖阳里，轮廓被橙光勾边。有半秒时间车只是一块形状，不是一个物体。光从出口倒灌回隧道，铺在路面上。
```

---

## 天气段（W2 黄金时刻）

```
Golden hour, sun at 9 degrees from the sea side, 3400K. Shadows stretch 6 to 8
times car length across the asphalt, soft-edged. Warm rim light on every
vertical edge. The harbour water breaks the sun into thousands of small white
glints. Sky clear, 1 okta, visibility 15 kilometers.
```

```
黄金时刻，太阳从海面方向以 9 度角射入，3400K。阴影横穿沥青，长度是车长的 6–8 倍，边缘柔和。每一条竖边都有暖色轮廓光。港湾水面把太阳碎成上千个白色亮点。天空晴朗，云量 1/8，能见度 15 公里。
```

---

## 环境段（Monaco）

```
Circuit de Monaco, 3.3 kilometers through the streets of Monte Carlo. Barriers
30 centimeters from the racing line on both sides. Steep hillside behind the
track covered in stacked apartment terraces with shuttered windows and balconies.
Marina with packed white yachts. A tunnel section cutting through a building.
Palm trees at the waterfront. No run-off area, no gravel.
```

```
摩纳哥赛道，3.3 公里穿行蒙特卡洛街道。两侧护栏距赛车线 30 厘米。赛道后方的陡坡上层层叠叠是带百叶窗和阳台的公寓楼。码头挤满白色游艇。一段隧道穿过建筑。水边有棕榈树。没有缓冲区，没有砾石。
```

---

## 质量段

```
Photorealistic, 40mm anamorphic, warm golden palette with cool shadow fill,
strong specular highlights on water, shallow depth of field on the foreground
barrier, fine grain.
```

---

## 视频模型补充

- 这个场景的核心是**空间压迫感**，提示词里必须出现 `barrier 30 centimeters away` 这类具体距离
- 俯拍镜头要写明 `no camera movement`，否则模型会自己飘
- 隧道镜头提示 `0.5 second silhouette`，让模型理解曝光过渡
- 不要写 "beautiful sunset over Monaco"，会得到明信片式的假画面，要写光的物理行为

## 已知失败模式

| 现象 | 原因 | 修法 |
|---|---|---|
| 街道变宽 | 没给墙距 | 加 `walls 30cm from the car` |
| 游艇糊成白块 | 只说 yachts | 写 `individual hulls, masts, mooring lines` |
| 隧道内外曝光不对 | 没描述过渡 | 加 `half a second of pure silhouette at the exit` |