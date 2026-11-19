# V6 —《蜘蛛侠：纵横宇宙》3D 摩天海港立交赛道大片版（Neo-Monaco × Nueva York 2099 Sky-Harbor Edition）

> **与 V5 银石写实版 100% 隔离**：V6 彻底告别平面草地赛道，构建了全新的 **3.72 km 三维高差倾斜立交街道赛道（`track_data/spiderverse_circuit.json`）**，所有赛道几何、巨构建筑环境、湿滑霓虹镜面材质、三维漫画速度特效、24 机位大片运镜、`2.39:1` 银幕合成器、海报剧照与混音成片全部独立存放在 `v6_spiderverse/`、`renders_v6/` 与 `pipeline/v6_*` / `*_sv*`，`LATEST/v5_*` 与 `renders_v5/*` 零修改。

---

## 1. 全新三维立交超级赛道（Neo-Monaco × Nueva York 2099 Sky-Harbor）

| 指标 | 参数规格 |
|---|---|
| **单圈里程 / 采样** | `3,719.95 m`（`1,860` 个等弧长 `2.0 m` 闭合样条节点，横向宽度 `14.0 m`，近距霓虹护栏 `±8.2 m`） |
| **三维高差与坡度** | 最低点 `z = +0.15 m`（Eau-Rouge 谷底满载触底火花压坑）→ 最高点 `z = +42.50 m`（高架跨海大桥），最大爬坡 **`+13.5°`**，Corkscrew 螺旋俯冲 **`-13.9°`** |
| **最大外倾碗状倾角** | **`17.4°`（Carousel 碗状倾斜高架弯）**，共享三维正交标架 `(T, R, U)`，地面效应下压力支持峰值 **`6.35 G`** 贴壁飞驰 |
| **极速 / 单圈节拍** | 极速 **`341 km/h`**（赛博频闪隧道出弯），最低弯速 **`81 km/h`**（海港发卡弯），整圈 **`53.333 s` = `96` 拍 @ 108 BPM = `1,281` 帧 @ 24 fps** |

### 五大立体建筑奇观赛段（5 Architectural Set-Piece Zones）

1. **Zone 1 — 摩天峡谷发车格与连续 S 弯（`s = 0–596 m`, `f = 1–214`）**：两侧紧贴 `60–220 m` 赛博摩天楼幕墙、巨型全息广告牌、跨街高架轻轨桥与蒸气井盖，构图零空白地平线。
2. **Zone 2 — Eau-Rouge 谷底压坑火花与 `+42 m` 冲天陡坡（`s = 596–1,192 m`, `f = 215–428`）**：谷底 `z = +0.15 m` 极限垂向 G 力压迫底板迸射钛合金火花雨，随即沿 `+13.5°` 陡坡直冲云霄，盲顶剪影划过巨型半调圆月。
3. **Zone 3 — 632 m 双塔斜拉跨海天桥（`s = 1,192–1,824 m`, `f = 429–601`）**：悬空 `z = +42.3 m`，两座 `135 m` A 字巨塔与密集发光斜拉钢索以 310+ km/h 切割镜头前景。
4. **Zone 4 — `17.4°` 碗状倾斜飞墙弯与 Corkscrew 螺旋俯冲（`s = 1,824–2,520 m`, `f = 602–894`）**：外侧弧形透明霓虹防撞高墙紧贴尾翼，紧接 `-13.9°` 断崖式下坠直扑海港灯火。
5. **Zone 5 — 520 m 全封闭赛博频闪隧道与海港发卡弯终局（`s = 2,520–3,720 m`, `f = 895–1,281`）**：每 `16 m` 一道青/品红/紫外几何发光拱肋以 `341 km/h` 掠过座舱，出洞瞬间强光反差切入 `340 → 81 km/h` 海港龙门吊发卡弯重刹与湿滑镜面终点冲线。

---

## 2. 六维《蜘蛛侠：纵横宇宙》大片视听管线

| 维度 | 技术落地方案 |
|---|---|
| **1. 湿滑黑曜石镜面沥青 + 美漫网点排线** | 开启 EEVEE **`SCREEN` 屏幕空间光线追踪反射**，雨夜黑曜石路面积水倒映两侧摩天霓虹、斜拉索、隧道光肋与碳陶刹车红热辉光；车身与建筑采用 `Diffuse -> ShaderToRGB` 三阶色阶、普鲁士深靛蓝暗部、1080p **Ben-Day 半调圆网点**与 **45° 交叉排线** |
| **2. 三维姿态绑定 + 安全 "On Twos" 12 fps 抽帧** | `RIG_F1_Race` 全三维姿态解算（`XYZ + Heading + Pitch + Bank Roll` 严格贴合三维倾斜路面法向 `U`）；世界位移与全部 24 台摄影机保持 **24 fps `LINEAR`** 丝滑跟拍，车身次级俯仰/侧倾、方向盘、悬挂及三维速度特效按 **2 帧一拍设为 `CONSTANT`（12 fps 手绘定格感）**，快门 `0.07` |
| **3. 升级版三维具象漫画速度特效（`V6_09_ComicFX`）** | 除翼尖螺旋涡流彩带与车轮残影弧外，新增换挡断火**紫青喷焰马赫环（Shock-Diamonds）**、Eau-Rouge/Corkscrew 谷底触底**锯齿钛合金火花雨（Plank Titanium Sparks）**与雨夜后轮**半调水雾羽流（Wet-Tire Spray Arcs）** |
| **4. 24 机位极限动作运镜 + 三维防遮挡射线自检** | 涵盖摩天楼垂直俯冲 FPV（`S01`）、距湿路面仅 `0.22 m` 的 `15 mm` 贴地刮擦斜角镜头（`S02`/`S06`/`S16`）、`300 mm` 盲顶奔月剪影（`S08`）、`17.4°` 碗状高墙贴翼轨道镜（`S12`）、`-13.9°` 俯冲 Halo 主观视角（`S15`）、`28→14 mm` 隧道吸入变焦（`S05`/`S17`）与 `341 km/h` 隧道 `180°` 甩镜急转（`S19`）；内置三维 `scene.ray_cast` 全帧遮挡自检 |
| **5. `2.39:1` 变形宽银幕高反差印刷合成器** | `CryptomatteV2` 精确抠出主角赛车与漫画特效（保持 **0 px 印刷错位**与 100% 锐度）；焦外背景按真实景深距离施加 **Red-Cyan 红青印刷错位**、**Anisotropic Kuwahara 水彩笔触**、7.5 px 半调网点、Kirsch/Sobel 双通道墨线、12 fps 沸腾放射速度线与 **`2.39:1` 宽银幕遮幅黑边** |
| **6. 三幕平行宇宙色彩剧本 + 双冲击帧 + 空间声学** | 单圈 `53.33 s` 跨越三大蜘蛛侠宇宙，嵌有两处次元撕裂色散故障与两处 **2 帧黑白赤红木刻版画冲击帧**；音轨同步摩天峡谷拍频回声、跨海大桥高空呼啸与赛博隧道箱体混响 + 高频拉链多普勒 |

---

## 3. 三幕平行宇宙时间轴与关键事件（1,281 帧 / 53.33 秒）

| 幕次 / 事件 | 帧范围 | 镜头范围 | `sv_dimension` | 视觉与声学高潮 |
|---|---|---|---|---|
| **Act I — Earth-1610（迈尔斯摩天峡谷）** | `1–427` | `S01..S08` | `0.0` | 绯红/电光青/琥珀钠灯雨夜峡谷；摩天楼垂直俯冲 → Eau-Rouge 谷底钛合金火花雨 → `+13.5°` 冲天陡坡 |
| **冲击帧 1 — Raidillon `+42 m` 坡顶爆闪** | **`413–414`** | `S08_MoonCrestTele300` | `0.0` | `300 mm` 盲顶跃起瞬间爆发双帧白/赤红/墨黑高反差版画剪影 |
| **次元穿越 1 → 2** | `426–429` | `S08 → S09` | `Glitch` | 全屏 `±20 px` 红青撕裂错位 + 磁带降采样音高撕裂切上跨海天桥 |
| **Act II — Earth-65（格温跨海天桥与倾斜飞墙）** | `428–894` | `S09..S16` | `1.0` | 青绿/品红/蜜桃水彩天空 + Kuwahara 画布笔触；`135 m` 斜拉桥塔 → `17.4°` 碗状飞墙弯 → `-13.9°` Corkscrew 螺旋俯冲 |
| **次元穿越 2 → 3** | `893–896` | `S16 → S17` | `Glitch` | 全屏 `±21 px` 纵向色散撕裂冲入封闭赛博隧道入口 |
| **Act III — Earth-928（2099 频闪隧道与海港终局）** | `895–1281` | `S17..S24` | `2.0` | 黑曜石/紫外/激光红赛博隧道；`341 km/h` 极速 `180°` 甩镜出洞 → 海港发卡弯重刹 → 湿滑霓虹镜面冲线 |
| **冲击帧 2 — 海港发卡弯 `340→81 km/h` 重刹震爆** | **`1067–1068`** | `S20_HarborBrakeImpact` | `2.0` | `f=1067` 白底赤红墨黑闪裂 → `f=1068` 黑底赤红白刃剪影，精准对齐 2099 警报嘶鸣与超低音下潜重击 |

---

## 4. 三段精选 4 秒高潮展示片段（3 × 96 帧 @ 24 fps = 12 秒大片集锦）

| 片段文件 | 帧区间 | 时间轴起点 | 内容亮点 |
|---|---|---|---|
| [renders_v6/clip1_miles_1610.mp4](../renders_v6/clip1_miles_1610.mp4) | **`f = 269..364`** | `11.167 s` | **Act I 迈尔斯宇宙（Eau-Rouge 冲天陡坡）**：`15 mm` 贴地 `0.22 m` 迎面拍谷底满载钛合金火花雨（`S06`），切入 `+13.5°` 仰拍环绕直冲摩天云霄（`S07`） |
| [renders_v6/clip2_gwen_65.mp4](../renders_v6/clip2_gwen_65.mp4) | **`f = 585..680`** | `24.333 s` | **Act II 格温水彩宇宙（天桥入 `17.4°` 飞墙碗弯）**：`+42 m` 跨海斜拉桥追随（`S11`）切入 `17.4°` 倾斜碗弯外侧弧形高墙距翼尖 `0.8 m` 贴壁飞驰（`S12`），背景水彩染洗 |
| [renders_v6/clip3_2099_impact.mp4](../renders_v6/clip3_2099_impact.mp4) | **`f = 993..1088`** | `41.333 s` | **Act III 2099 赛博隧道 + 冲击帧**：`341 km/h` 频闪隧道 `180°` 甩镜急转（`S19`）→ `f=1042` 强光出洞重刹（`S20`）→ **`f=1067..1068`** 黑白赤红版画冲击帧震爆 |
| **[renders_v6/v6_spiderverse_showcase_12s.mp4](../renders_v6/v6_spiderverse_showcase_12s.mp4)** | 三段合辑 | `12.0 s` | 三幕立体赛道精华合辑（切点带次元撕裂故障音效衔接，`-14 LUFS`，`TP <= -1.0 dBFS`） |

---

## 5. V6 专属文件与一键复现命令

| 文件 | 职责 |
|---|---|
| `pipeline/v6_build_circuit.py` | 生成 3.72 km 三维高差倾斜立交赛道与速度/G 力遥测 `track_data/spiderverse_circuit.json` + `.csv` |
| `pipeline/v6_sv_textures.py` | 生成 `v6_spiderverse/textures/` 赛博全息广告牌、漫画半调网点与纸纹贴图 |
| `pipeline/v6_sv_env.py` | 构建三维倾斜湿滑镜面沥青赛道、五大巨构建筑赛段、丁达尔体积光柱与 `V6_09_ComicFX` → 输出 `v6_spiderverse/v6_stage_lookdev.blend` |
| `pipeline/v6_sv_comp.py` | 三维姿态绑定 + 12 fps On-Twos 抽帧 + 24 大片机位（含三维防遮挡自检）+ `2.39:1` `Comp_V6_SpiderVerse` 合成器 → 输出 `v6_spiderverse/v6_stage_anim_sv.blend` 与 `v6_shots_manifest.json` |
| `pipeline/v6_sv_stills.py` | 渲染全部 24 张 1080p `2.39:1` 剧照、`contact_sheet_v6.jpg` 与斜切分镜漫画海报 `comic_page_sheet.jpg` |
| `pipeline/render_v6_sv.py` | 开启 EEVEE `SCREEN` 湿路面光线追踪反射，支持 `--range START-END --outdir DIR` 并行分段渲染与 `--all` 全片 1,281 帧渲染 |
| `pipeline/synth_sfx_sv.py` | 合成 53.38 s 空间声学平行宇宙引擎音效 `sfx_spiderverse_53s.wav`（峡谷回声 / 天桥风啸 / 隧道混响 + 冲击重低音） |
| `pipeline/mux_v6_sv.sh` | 封装 `--clips`（3 段 4s 片段 + 12s 合辑）与 `--full`（全片 MP4） |

### 复现命令

```bash
B="/d/APPs/steam/steamapps/common/Blender/blender.exe"

# 1. 生成三维赛道数据 + 风格化贴图 + 巨构环境 Lookdev + 24 机位与 2.39:1 合成器工程
python pipeline/v6_build_circuit.py
python pipeline/v6_sv_textures.py
"$B" -b -P pipeline/v6_sv_env.py
"$B" -b -P pipeline/v6_sv_comp.py

# 2. 渲染全部 24 张 1080p 剧照 + 6x4 三幕总览表 + 漫画分镜海报页
"$B" -b -t 8 -P pipeline/v6_sv_stills.py -- --render

# 3. 双进程并行渲染 3 段 4 秒（各 96 帧）高潮展示片段
"$B" -b -t 8 -P pipeline/render_v6_sv.py -- --range 269-364 --outdir renders_v6/clips_frames/clip1_miles_1610
"$B" -b -t 8 -P pipeline/render_v6_sv.py -- --range 585-680 --outdir renders_v6/clips_frames/clip2_gwen_65
"$B" -b -t 8 -P pipeline/render_v6_sv.py -- --range 993-1088 --outdir renders_v6/clips_frames/clip3_2099_impact

# 4. 合成三维赛段空间声学平行宇宙音效并封装 MP4
python pipeline/synth_sfx_sv.py
bash pipeline/mux_v6_sv.sh --clips
```
