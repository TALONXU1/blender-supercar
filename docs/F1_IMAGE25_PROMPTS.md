# F1 赛车 · Image 2.5 出图提示词包

对应本项目建模（`scifi_f1_2035_v4_racing.blend`）：哑光海军蓝 + 裸碳纤维，Red Bull Racing 2035 概念涂装语言 —— 低矮楔形单体壳、悬浮式细梁 Halo、筒状进气口、十辐锻造轮 + 金色中央锁止、双元素尾翼 + 竖直导风板、六片扩散器栅、底板边缘青色光带。

用法：每节提示词可直接整段复制。核心出图 = **【A 车体】+【B 涂装贴纸】+【C 环境】+【D 质量】** 四段拼接；单独要车、要贴图、要场景时用对应小节。英文版对 2.5 更稳，中文版便于你改关键词，两版语义等价。

---

## 0. 参数与拼装规则

| 项 | 建议 |
|---|---|
| 比例 | 3:2 或 16:9（车身侧掠 / 三分之四角）；1:1 只用于贴纸与局部细节 |
| 尺寸 | 1536×1024 起；需要印刷级贴图再上 2048 以上 |
| 投喂顺序 | 车体 → 涂装 → 环境 → 质量，后段永远压在前段之上 |
| 文字 | 2.5 文字渲染够用，但只在引号里放 **短字样**（≤3 词），长句必糊 |
| 改图指令 | "保持车身轮廓与透视不变，只把尾翼端板文字换成 'X'" |
| 抽卡 | 同一提示词连抽 4 张，选形体最正的那张做修改基底，别重写提示词 |

拼装示例（英文，最短可用版）：

```
[F1-BODY-EN] + [LIVERY-RB-EN] + [ENV-SUNSET-EN] + [QUALITY-EN]
```

---

## A. 车体外形

### A1 主视角 · 三分之四前侧（默认主图）

**EN**
```
A 2035 Formula 1 concept car, three-quarter front view, low camera at 1.1 meters, 50mm lens. Long low wedge monocoque: needle-thin high nosecone with four-element front wing, wide curved endplates carrying a thin glowing cyan strip along the top edge. Extremely slim sidepods with deep undercut and a narrow coke-bottle waist flowing into a compact rear. Floating thin-strut halo above the cockpit, single central pillar, pale cyan edge trim. Cylindrical airbox intake with a circular mouth ringed by a soft glowing cyan inner lip. Two-element rear wing with four vertical flow strakes and tall squared endplates. Six strake diffuser under the tail with one central round exhaust. Exposed carbon-fiber suspension pushrods, polished forged 10-spoke wheels with gold center-lock nuts, red anodized brake calipers behind carbon-ceramic discs, slick tires. A continuous cyan LED light band runs along the floor edge and behind each wheel arch. Matte navy blue body panels, bare 2x2 twill carbon fiber on all aero surfaces, satin clearcoat.
```

**中文**
```
2035 年 F1 概念赛车，三分之四前侧视角，1.1 米低机位，50mm 镜头。修长低矮楔形单体壳：极细高位鼻锥配四元素前翼，宽大弧形端板顶缘一条细青色发光带。极窄侧箱配深内切，收腰到紧凑车尾。座舱上方悬浮式细梁 Halo，单根中央支柱，淡青色边饰。筒状进气口带圆形开口，内缘一圈柔和青色发光环。双元素尾翼配四片竖直导流板与高方形端板。车尾下方六片导流栅扩散器，中央单出圆形排气。裸露碳纤维悬挂推杆，抛光十辐锻造轮 + 金色中央锁止螺母，碳陶刹车盘后红色阳极卡钳，光头胎。底板边缘与每个轮拱后方有连续青色 LED 光带。车身为哑光海军蓝，所有空气动力学面为裸 2x2 斜纹碳纤维，缎面清漆。
```

### A2 纯侧视（看比例，做涂装分布图）

**EN**
```
Strict side elevation of the same 2035 F1 concept car, orthographic feel, 85mm, camera at axle height. Wheelbase reads long and low; nose tip nearly at axle line; cockpit sits slightly ahead of center; sidepod upper surface slopes down toward the rear in one continuous line; floor edge dead straight with the cyan light band running its full length. Front and rear wheels identical diameter, rear tires visibly wider. Nothing but the car on a seamless light gray gradient background, soft studio light from top-left.
```

**中文**
```
同一台 2035 F1 概念车的严格侧立面，正投影感，85mm，机位与轮轴等高。轴距显长显低；鼻尖几乎压在前轴线上；座舱略偏前；侧箱上表面一路下压到车尾；底板边缘一条笔直青色光带贯穿全长。前后轮同直径，后胎明显更宽。纯净浅灰渐变背景上只有车，左上柔光。
```

### A3 俯视（审空气动力学布局）

**EN**
```
Top-down orthographic view of the 2035 F1 concept car on flat dark asphalt. Front wing spans wider than the body with four visible elements, nose narrows to a point. Sidepods barely wider than the cockpit opening, hard undercut shadow line. Rear wing square and wide, four vertical strakes visible between the elements. Four wheels protrude clearly beyond the bodywork. Cyan light band traces the entire floor perimeter like a thin outline. Neutral overcast light, zero perspective distortion.
```

**中文**
```
俯视正投影，深色沥青地面。前翼比车身宽，可见四层元素，鼻锥收成尖端。侧箱几乎不比座舱开口宽，内切阴影线很硬。尾翼方正宽大，翼片间四片竖直导流板清晰。四轮明显凸出车体之外。青色光带沿底板整个周长勾出一圈细轮廓。中性阴天光，零透视畸变。
```

### A4 细节特写（轮组 / Halo / 尾翼 / 扩散器）

**轮组**
```
Extreme close-up of a Formula 1 front wheel, 100mm macro at f/2.0. Forged 10-spoke wheel with a slight turbine twist, polished outer lip catching a rim light, gold center-lock nut, red anodized six-piston caliper clamped on a drilled carbon-ceramic disc, carbon brake duct with visible weave, slick tire sidewall with a thin red circumferential line and embossed lettering. Shallow depth of field, cool shadow side, warm rim light from behind.
```

**Halo 与进气口**
```
Close-up low angle over the cockpit of the 2035 F1 concept: thin-strut halo with a pale cyan edge strip, single central pillar, cylindrical airbox behind with a circular intake mouth ringed by a glowing cyan lip, matte navy bodywork below, bare carbon above, blurred rear wing in the background. 35mm, f/2.8.
```

**尾部**
```
Rear three-quarter low angle of the 2035 F1 concept car, 24mm wide, camera 40cm off the ground. Two-element rear wing, four vertical strakes, tall endplate with a clean sponsor panel, six-strake diffuser under the tail, one central round exhaust with a faint warm orange glow inside, twin rain lights, cyan strip tracing the rear wing top edge, heat shimmer above the exhaust.
```

### A5 变形替代（同骨架换风格）

同一套几何只换气质，粘在 A1 后面即可：

| 变体 | 追加句（EN） |
|---|---|
| 硬核赛道版 | `Add a large multi-element front wing, complex bargeboards, vortex generators along the floor edge — maximum downforce trim.` |
| 低阻蒙扎版 | `Strip the wing elements down to two flat shallow blades front and rear, smallest possible endplates, sealed floor — minimum drag trim.` |
| 全碳裸车 | `No paint at all: entire body is exposed carbon fiber with visible twill direction changes per panel, no sponsor decals except tiny white markings.` |
| 军事灰 | `Flat military gray-green body, stenciled white numerals, no gloss, dust film on the lower surfaces.` |

---

## B. 赞助商贴纸与涂装

### B1 涂装总规则（每次出图都要带）

**EN**
```
Livery layout: matte navy blue base (#0E1B33) with a single confident red accent line (#C8102E) and pale cyan light trim. All graphics are conformal vinyl decals that wrap the body curvature — they bend with the surface, no floating cards, no flat stickers hovering in air. Text sits on genuine body panels: nose top, sidepod flank, engine cover, halo, rear wing mainplane, rear wing endplate, floor edge, tire sidewall. Typeface is a clean condensed grotesque, tight tracking, all caps except brand wordmarks. Every decal has a thin carbon or dark border so it reads as applied vinyl, not printed paint. Keep total graphic density low — F1 cars read as color blocks, not posters.
```

**中文**
```
涂装规则：哑光海军蓝底漆（#0E1B33）+ 一道克制的红色强调线（#C8102E）+ 淡青色光饰。所有图形都是顺着车身曲率包裹的乙烯基贴膜 —— 随曲面弯曲，不允许悬浮卡片、不允许贴纸飘在空中。文字必须落在真实车板面上：鼻锥顶面、侧箱侧翼、引擎盖、Halo、尾翼主翼、尾翼端板、底板边缘、轮胎侧壁。字体为干净压缩无衬线，字距收紧，全大写（品牌字标除外）。每张贴纸带一道细碳纤或深色描边，读起来是贴上去的膜而非喷漆。整体图形密度要低 —— F1 赛车读的是色块，不是海报。
```

### B2 赞助位清单（本项目实际布局）

| 位号 | 位置 | 内容 | 视觉处理 |
|---|---|---|---|
| S1 | 尾翼端板（左右各一） | `Mobil 1` / `PIRELLI` / `TAG HEUER` 三行 | 深灰碳底竖排信息板，品牌间用细红线分隔，最下一行字号最小 |
| S2 | 尾翼主翼后缘面 | `Red Bull` 字标 + 红黄双牛徽标 | 暖橙红字，居中，右侧留白 |
| S3 | 尾翼主翼前缘面 | `BYBIT` | 金色字，单行，偏左 |
| S4 | 引擎盖 / 进气口两侧 | `Red Bull` 字标 + 牛徽 + `RACING` `HONDA` `BYBIT` 副行 | 主标最大，副行字号递降三级 |
| S5 | 侧箱侧翼 | `ORACLE` | 白色宽字距，占满侧箱纵向高度 60% |
| S6 | 鼻锥顶面 | 前翼赞助条 + 数字 `1` | 沿鼻锥中心线纵向排布，随曲率收窄 |
| S7 | Halo 上方 | `ORACLE` | 极细白字，沿 Halo 弧面弯曲 |
| S8 | 底板边缘 | 青色 LED 光带 + 微型技术标 | 光带在上，文字在下方暗区，几乎不可读 |
| S9 | 轮胎侧壁 | `PIRELLI` / `P ZERO` 环形 | 极坐标环形排布，红圈分隔，随胎侧弧度变形 |
| S10 | 前翼端板外侧 | 小型 `Mobil 1` + `PIRELLI` | 与尾翼端板同款信息板，尺寸缩至 45% |

要求模型做到的三件事：**贴纸随曲率包裹**、**端板信息板保持三行结构**、**轮胎环形字沿胎侧弧度变形**。

### B3 整车主图（把 B1+B2 折叠进一句）

**EN**
```
Apply this livery: navy base with red accent line and cyan light trim. Rear wing endplates carry a vertical dark-carbon sponsor panel reading "Mobil 1", a thin red rule, "PIRELLI", then "TAG HEUER" — three lines, decreasing size. Rear wing mainplane aft face shows the Red Bull wordmark with the charging-bull roundel in warm orange-red. The mainplane leading face shows "BYBIT" in gold. Engine cover flank carries "Red Bull RACING" with small "HONDA" and "BYBIT" lockups beneath. Sidepod flank reads "ORACLE" in wide-tracked white capitals. Number "1" on the nose top. "ORACLE" in hairline white type curving along the halo. Tire sidewalls show "PIRELLI" and "P ZERO" set on a circle, deformed to the sidewall bulge, separated by a thin red ring. All decals wrap the curvature, thin dark border on each, cyan LED strip along the floor edge.
```

**中文**
```
涂装：海军蓝底 + 红色强调线 + 青色光饰。尾翼端板为竖排深碳信息板，自上而下 "Mobil 1"、细红线、"PIRELLI"、"TAG HEUER"，三行字号递减。尾翼主翼后面为 Red Bull 字标 + 暖橙红公牛圆徽。主翼前缘面金色 "BYBIT"。引擎盖侧面 "Red Bull RACING"，下方小号 "HONDA" 与 "BYBIT" 组合标。侧箱侧翼宽字距白色 "ORACLE"。鼻锥顶面数字 "1"。Halo 上极细白字 "ORACLE" 沿弧面弯曲。轮胎侧壁 "PIRELLI" 与 "P ZERO" 环形排布、随胎侧鼓起变形、中间一道细红环分隔。全部贴纸包裹曲率并带细深色描边，底板边缘青色 LED 光带。
```

### B4 贴纸单品生成（做 decal 贴图素材用）

统一底：`flat vector decal sheet, pure white background, no perspective, no shadow, centered, 1:1, crisp edges`。每张单独出，再拿去 Blender 里贴。

| 用途 | 提示词主体 |
|---|---|
| 尾翼端板板 | `A tall rectangular sponsor panel, dark satin carbon background, three stacked lines of condensed white sans-serif type: "Mobil 1", a thin red horizontal rule, "PIRELLI" in pale yellow, "TAG HEUER" in small white caps at the bottom. Clean margins, sharp corners, flat vector look.` |
| 牛徽 | `A minimal charging-bull silhouette badge, warm orange-red bull over a pale yellow circular disc, two bulls facing each other in negative space, no text, flat vector, high contrast, sticker die-cut with a thin white keyline.` |
| 侧箱字标 | `Wide-tracked white capital letters spelling "ORACLE" in a modern grotesque, flat vector, isolated on white, no effects.` |
| BYBIT 字标 | `The word "BYBIT" in metallic gold, geometric sans-serif, slightly extended, flat vector on white.` |
| 轮胎环字 | `A circular tire sidewall graphic: the words "PIRELLI" repeated around the ring in white condensed caps, "P ZERO" set at the top arc, thin red concentric ring separating the two, black rubber background, radial layout, no perspective.` |
| 号码 | `A bold italic numeral "1" in white with a thin red outline, racing style, flat vector on white.` |

### B5 涂装换色（同一台车出系列图）

把 B1 的首句替换即可，其余不变：

- 橙红主色：`matte burnt orange base (#D2401E) with white accent and dark carbon trim`
- 银黑：`liquid silver base with gloss black aero and a single neon yellow accent line`
- 深绿：`deep racing green base (#0B3B2E) with cream pinstripes and gold hardware`
- 全白测试车：`unpainted white test livery, matte, only black test-session codes and DHL-style yellow-red accents`

---

## C. 赛道环境

每个环境给"机位 + 光 + 场景"三件套，直接拼到 A1 后面。

### C1 黄昏沙漠赛道（对应本项目主场，推荐主图）

**EN**
```
Setting: a wide permanent racetrack in a desert basin at golden hour, sun 4.5 degrees above the horizon behind the car, warm low-angle key light raking across the asphalt, long soft shadows toward camera. Track surface is dark fresh asphalt with fine aggregate texture, painted white edge lines and a pale yellow run-off line, low concrete barriers with a continuous cyan LED strip along their top edge, kerbs in red-white blocks. Background: distant floodlight masts every 40 meters, a start gantry overhead with faint glowing signage, silhouetted tower blocks with scattered window lights, heat haze near the horizon. Sky: multi-scatter gradient from warm apricot at the horizon to deep teal overhead, thin cirrus streaks. Subtle dust particles suspended in the light.
```

**中文**
```
场景：荒漠盆地中的宽阔永久赛道，黄金时刻，太阳位于车后方地平线上 4.5 度，暖色低角度主光斜扫沥青，长而柔的阴影朝镜头方向拉出。路面为新铺深色沥青带细骨料质感，白色边线 + 浅黄缓冲区线，低矮混凝土护栏顶缘一条连续青色 LED 灯带，红白方块路肩。背景：每 40 米一根远景灯塔，头顶起跑龙门架带微弱发光标识，远处塔楼剪影零星窗光，地平线附近热浪扭曲。天空：暖杏色到高空深青的多重散射渐变，几缕卷云。光线中悬浮细微尘埃。
```

### C2 夜赛城市赛道

**EN**
```
Setting: a street circuit at night between glass towers. Cool blue-white LED floodlights on overhead gantries create hard pools of light on the asphalt with deep shadows between them, warm sodium spill from building windows, red taillight streaks from blurred traffic beyond the barriers. Wet-patched asphalt with mirror reflections of the light bars, painted lines glowing. Barriers are TecPro blocks and chain-link with sponsor banners softly out of focus. Light fog catches the floodlight beams. Camera sees the car lit mainly by a hard top light with cyan rim from the floor LED band.
```

**中文**
```
场景：夜间玻璃塔楼之间的街道赛道。头顶龙门架冷蓝白 LED 投光灯打出硬光斑，光斑之间是深阴影，建筑窗光溢出暖钠黄，护栏外车流尾灯拉成模糊红带。沥青有湿补丁，镜面反射灯条，标线发亮。护栏为 TecPro 缓冲块与铁丝网，赞助商横幅轻微失焦。薄雾让投光灯光束显形。车主要被顶部硬光打亮，底板青色光带勾出轮廓光。
```

### C3 雨战

**EN**
```
Setting: heavy rain on a permanent circuit. Asphalt is dark and fully wet, standing water in the low line, a wide spray plume torn off the rear tires and diffuser, water droplets beaded on every body panel and streaking backward along the airflow, brake discs glowing dull orange through the spray. Sky is flat graphite overcast, no sun, light comes from large diffused overhead sources plus faint red rain lights. Reflection of the cyan floor strip smears across the wet surface.
```

**中文**
```
场景：永久赛道大雨。沥青深黑完全湿透，走线上有积水，后轮与扩散器撕出大片水雾，每一块车板上都挂着水珠并顺着气流向后拖出细痕，刹车盘透过水雾发出暗橙光。天空平板石墨色阴云，无太阳，光源为大面积柔散顶光加微弱红色雨灯。底板青色光带在湿地面上拖出拉长的反射。
```

### C4 发车格 / 维修区

**EN**
```
Setting: the starting grid five minutes before lights out. Painted grid box with a white bracket, tire warmers being pulled away, a mechanic's shadow crossing the frame edge, overhead start gantry with five red lights red and glowing, grandstand blur with thousands of small highlights behind the barriers, sea of team equipment in the far background. Flat overcast daylight, cool white balance, everything slightly desaturated except the car.
```

**中文**
```
场景：熄灯前五分钟的发车格。地面白框车位标记，暖胎毯正在被抽走，画框边缘扫过一名技师的影子，头顶起跑龙门架五盏红灯亮起，护栏后看台糊成一片密集小高光，远景是车队装备的海洋。平板阴天日光，冷白平衡，除车以外整体轻微降饱和。
```

### C5 高速弯动态（要动感时用）

**EN**
```
Setting: mid-corner at 250 km/h on a fast right-hander. Camera pans with the car at 1/60 shutter so the asphalt, kerbs and barrier lines streak horizontally while the car body stays sharp and only the wheel spokes blur into a disc. Front wheels show a few degrees of steering lock, body roll barely visible, suspension compressed on the loaded side, front wing endplate a hand's width off the kerb. Dust and small stones lifted at the apex.
```

**中文**
```
场景：250 km/h 通过高速右弯弯心。镜头跟车摇摄，1/60 秒快门，沥青、路肩、护栏线横向拉丝，车身保持锐利，只有轮辐糊成圆盘。前轮带几度转向角，侧倾几乎看不出，受载侧悬挂压缩，前翼端板离路肩一掌宽。弯心扬起尘土与小石子。
```

---

## D. 质量与镜头模块

### D1 通用质量串（每次都加）

**EN**
```
Photorealistic automotive photography, shot on a full-frame body with a 50mm prime, f/4, ISO 100, 1/500s. Physically based materials: matte paint with visible micro-roughness variation, anisotropic carbon-fiber twill with directional highlights, rubber with fine grain, machined aluminum with concentric tool marks. Cinematic HDR lighting with soft rolloff, subtle bloom on the LED strips, accurate lens vignetting and a faint chromatic aberration at the frame edges. Color science is film-like: deep but clean navy shadows, controlled highlights, no clipping, slightly muted midtones. Fine detail everywhere: panel gaps, bolt heads, exposed fastener rows, dirt film on the lower aero, tiny stone chips on the leading edges of the wing. Sharp focus on the car, natural depth of field falloff on the background. No text artifacts, no watermark, no border.
```

**中文**
```
照片级汽车摄影，全画幅机身 + 50mm 定焦，f/4，ISO 100，1/500s。物理正确材质：哑光漆面带可见微观粗糙度变化，各向异性碳纤维斜纹带方向性高光，橡胶细颗粒，机加工铝件带同心刀纹。电影感 HDR 布光，柔和高光滚降，LED 光带轻微泛光，准确暗角与画框边缘微弱色散。色彩科学偏胶片：深而干净的海军蓝暗部，高光可控不过曝，中间调略压。处处细节：板件缝隙、螺栓头、外露紧固件排、下部空力件上的积尘膜、翼片前缘的细小石击痕。焦点落在车上，背景自然虚化。无文字伪影、无水印、无边框。
```

### D2 镜头/焦段速查

| 想要 | 焦段 | 机位 | 效果 |
|---|---|---|---|
| 英雄主图 | 50mm | 1.1 m，前置 3/4 | 比例最准，变形最小 |
| 压迫感 | 24mm | 0.4 m，贴地 | 前翼夸张外扩，冲击力强 |
| 长焦压缩 | 135mm | 26 m 外，6.5 m 高 | 车身压扁成横条，背景更近 |
| 细节 | 100mm macro | 贴至轮组 | 材质与工艺说服力 |
| 跟拍 | 35mm + 摇摄 | 与车同速 | 横向拉丝，动态 |
| 俯视构图 | 50mm 垂直下压 | 上方 8 m | 看空力布局 |

### D3 负向提示词

**EN**
```
blurry, low resolution, jpeg artifacts, distorted proportions, cartoon, anime, toy car, plastic look, flat lighting, oversaturated, HDR halo, floating decals, decals not conforming to the body, mirrored or duplicated text, garbled text, extra wheels, wrong wheel count, asymmetric suspension, bent chassis, wing elements too thick, chunky aero, rubber-band tire sidewall, missing halo, driver visible, cockpit glass, doors, roof, headlights like a road car, license plate, wheel arches of a road car, multiple cars, crowd in front of the car, motion blur on the entire frame, watermark, signature, text overlay, frame border
```

**中文**
```
模糊、低分辨率、JPEG 压缩伪影、比例失真、卡通、动漫、玩具车、塑料感、平光、过饱和、HDR 光晕、贴纸悬浮、贴纸不贴合车身、文字镜像或重复、乱码文字、多余车轮、轮数错误、悬挂不对称、车架弯曲、翼片过厚、空力件臃肿、橡皮筋式胎侧、缺少 Halo、可见车手、座舱玻璃罩、车门、车顶、民用车大灯、车牌、民用车轮拱、多车、车前有人群、全画面运动模糊、水印、签名、叠加文字、画框
```

### D4 常见失败与修正指令

| 症状 | 追加/替换 |
|---|---|
| 文字糊成块 | 把长句换成 ≤3 词字样；加 `render the type sharply, vector-clean edges, no anti-alias fringing` |
| 贴纸像贴纸 | 加 B1 的 `conformal vinyl decals that wrap the body curvature`，再补 `each decal follows the surface normal, deformed by perspective` |
| 翼片变厚变蠢 | 加 `razor-thin wing elements, 8mm chord thickness, sharp trailing edge` |
| 长出民用车部件 | 负向里加倍写 `no doors, no roof, no windshield glass, no headlight housing, open cockpit only` |
| 轮毂变五辐 | 明确 `exactly ten forged spokes, gold center-lock nut` |
| 姿态不够低 | `camera 40cm above the ground, extreme low angle, wheels visually larger than the body height` |
| 光带过火 | `cyan LED strip is a thin discrete line, subtle, not a glowing tube, no lens flare from it` |
| 整体像游戏截图 | 换 D1 的胶片色彩科学段，加 `raw photo, no game-engine look, no exaggerated specular` |

---

## E. 成套出图清单（8 张出一组）

| # | 拼装 | 用途 |
|---|---|---|
| 1 | A1 + B3 + C1 + D1 | 主视觉海报 |
| 2 | A2 + B1 + C1 + D1 | 侧视涂装展示 |
| 3 | A3 + B3 + C5 + D1 | 俯视空力布局 |
| 4 | A4 轮组 + B4 环字 + C1 + D1 | 工艺细节图 |
| 5 | A4 尾部 + B2 + C2 + D1 | 夜赛尾部氛围 |
| 6 | A1 + B5(橙红) + C3 + D1 | 雨战变体 |
| 7 | A1 + B1 + C4 + D1 | 发车格叙事 |
| 8 | A5(全碳) + B1 + C2 + D1 | 测试车/概念稿 |

---

## F. 快速粘板（最短可用版）

懒得拼接时，这一段直接投：

```
A 2035 Formula 1 concept car in matte navy blue with bare carbon aero, three-quarter front view from 1.1m height on a 50mm lens at golden hour on a desert racetrack. Needle nose with four-element front wing, thin-strut floating halo, cylindrical airbox with a glowing cyan intake lip, slim undercut sidepods, two-element rear wing with four vertical strakes and tall endplates, six-strake diffuser, ten-spoke forged wheels with gold center-lock nuts, red calipers, slick tires, cyan LED strip along the floor edge. Livery: Red Bull wordmark and roundel on the engine cover, "ORACLE" on the sidepod, vertical "Mobil 1 / PIRELLI / TAG HEUER" panel on the rear wing endplate, "BYBIT" in gold on the mainplane, "PIRELLI" and "P ZERO" set circularly on the tire sidewalls, all decals conformal to the body curvature with thin dark borders. Warm low sun raking the fresh asphalt, cyan barrier light strips, distant floodlight masts, apricot-to-teal gradient sky, faint dust in the air. Photorealistic automotive photography, full-frame 50mm f/4, physically based materials, anisotropic carbon weave, film-like color science, cinematic HDR, sharp focus on the car, natural background falloff. No floating decals, no garbled text, no extra wheels, no cartoon look, no watermark.
```
