# V5 — 真实银石赛道整圈（90 s / 26 机位 / 广播级景深 / 遥测驱动视听全链路）

V4 的问题不是材质也不是运镜，是**赛道是手搓的**：1.8 km 两个弯，车速和曲率各写各的关键帧，弯心速度不受抓地力约束，观众说不出哪里假，但看着就是假。

V5 把这一步彻底换掉了：赛道几何、赛车线、每一帧的车速和曲率全部来自真实银石（OpenStreetMap `type=circuit` relation 51160，闭环 2 m 重采样）。车不是"按节奏摆出来的"，而是**被弯道半径和抓地力上限顶出来的**；同时全片 26 机位画面与 1.6L V6 涡轮混动引擎声浪均由同一份逐帧物理遥测同步驱动。

---

## 1. V4 → V5 核心升级

| 项目 | V4 | V5（最新增强版） |
|---|---|---|
| 赛道几何 | 手写曲率关键帧积分，1 779 m，2 个 90° 弯 | 真实银石，5 834 m，**18 个弯**，2 m 闭环采样 |
| 驱动变量 | 帧号均分 | **`t`（物理经过时刻插值）** |
| 朝向与轨迹 | 位移差反推 + 自积分轨迹 | 直接取 `heading_deg` + **`racing_xy` 赛车线** |
| 关键帧插值 | LINEAR | 全场景 Action（120 527+ 关键帧）显式强制 `LINEAR` |
| 片长与机位 | 30 s / 720 帧 / 10 机位 | **90.04 s / 2 161 帧 / 26 机位**（108 BPM 拍点切镜） |
| 广播级景深 | 估算距离对焦（追随镜头焦点偏前 3–4.6 m） | 独立焦点追踪器 **`V5_CamFocus`**（锁定 `Bone_Root + 0.45m Z`），长焦/近景 `f/2.8–f/4.0` 奶油虚化 |
| 车载机位 | 鼻锥最前端盲拍（看不到座舱与方向盘） | **F1 座舱 Halo / 防滚架机位**（`S02`/`S19`），实时展示方向盘转动（`9.5:1`）、15 颗三色换挡灯与前轮转向 |
| 遥测灯光与热辉光 | 瞬时刹车值无退火、雨灯与排气管材质混用 | 对流冷却热惯性碳陶刹车盘+卡钳红橙辉光；独立 **6 Hz 高频闪烁 FIA 尾部雨灯/ERS 回收灯** |
| 天空与光照 | 7 档顶点色穹顶（地平线分层条带） | **96×64 球体 + 连续像素级大气黄昏渐变与太阳方位角米氏散射**；`LGT_V5Car_*` Light Linking 覆盖全部 244 个赛车部件 |
| 赛道细节 | 基础沥青带 + 简单看台 | 13 处重刹双轨橡胶胎痕、离线橡胶碎屑、13 处弯心黄黑香肠路肩、防撞柱、DRS 牌、维修墙指挥台与出口绿灯 |
| 声音系统 | 仅有背景配乐 | **遥测同步 1.6L V6 混动合成器（`synth_sfx.py`）**：8 档转速、涡轮哨音、升档断火、降档补油、固定机位物理多普勒频移 |

---

## 2. 赛道数据与五条物理硬规则

数据包：`track_data/silverstone_track.json`（2 933 点，2 m 间距，闭环）。

| 指标 | 值 |
|---|---|
| 实测周长 | 5.834 km（官方 5.891 km，−0.97%） |
| 仿真单圈 | **90.34 s**（铺满 2 161 帧，`dt = 0.041824 s/帧`） |
| 平均 / 峰值 / 最低速度 | 232.5 / 331.2 / 54 km/h |
| 横向加速度峰值 | 6.38 g（上限模型 `15.0 + 0.00714 v²`，超限点 0） |

### 五条硬规则（写进 `v5_anim.py`，任何改动必须遵守）

1. **位置按 `t` 插值，不按帧均分** —— 按帧均分等于匀速跑。
2. **朝向取 `heading_deg`，不用位移差反推** —— 稀疏处差分会跳变抖动。
3. **位置走 `racing_xy`，不是中心线 `xy`** —— 外内外切弯心才符合真实赛车运动。
4. **关键帧插值强制 `LINEAR`** —— 严禁 Bezier 弯心过冲导致压出赛道或焦点漂移。
5. **`v²·κ <= 15.0 + 0.00714 v²`**，且保持 `Bone_Root.z = 0.012`、相机 `clip_start = 0.5`、`clip_end = 9000`。

### 构建自动自检（`v5_anim.py` 每次运行必过）

```text
[check] 最坏横向 62.58 m/s^2 (6.38 g) @ frame 1774, t=74.2 s
[check] 超限帧 0 -> PASS
[check] 航向跳变帧(>6.9deg) 0 -> PASS
[check] v_max 331.2 km/h, lap 90.34 s, 帧数 2161
[check] camera occlusion: 0 blocked frames (min_cam_z=0.48 m) -> PASS
[check] root Scene Collection direct objects: 0 -> PASS
```

---

## 3. 程序化银石赛道环境（`pipeline/v5_env.py` + `pipeline/gen_textures.py`）

全部由赛道中心线、曲率与速度剖面程序化生成，Outliner 按 `V5_01_Road`..`V5_07_Lighting` 严格归类，零孤立数据块：

| 部件 | 生成规则与细节 |
|---|---|
| 主路面与离线碎屑 | `V5_Track` 14 m 宽（`z=0.010`），横向 5 列 `OffLine` 属性驱动赛车线外侧灰尘与橡胶颗粒（Marbles） |
| 赛车线与重刹胎痕 | `V5_RacingLine`（±1.7 m 橡胶带）+ `V5_SkidMarks`（Village、Brooklands、Stowe、Vale 等 13 处慢弯前羽化双轨重刹胎痕）；全部路面材质 `Specular IOR Level <= 0.025` |
| 路肩与香肠路肩 | 20 段弯道红白交替路肩（`V5_Kerb_*`）+ 13 处慢弯/连续弯内侧 FIA 黄黑香肠路肩（`V5_Kerb_Sausage`）与柔性防撞柱（`V5_ApexBollards`，距赛车线 ≥2.15 m） |
| 缓冲区与护栏 | 16 m 割草条纹草地缓冲带、13 处慢弯外侧砾石坑、连续混凝土基座+金属护栏+青色灯带+防护网立柱 |
| 6 座模块化看台 | 28 m 分块阶梯（贴 `crowd_silverstone.png`）、前低后高斜顶棚、横向钢桁架、VIP 灯带、物理线性色值彩旗；每座绑定组件 Empty 父级 |
| 维修区（Pit Lane） | 360 m 主直道内侧：维修墙 + 双工程师指挥台（`V5_PitWallTiming`）+ 出口双绿灯信号柱（`V5_PitExitSignal`）+ 56 车位划线 + 6 车队循环卷帘门车库楼（`pit_garage.png`）+ 楼顶看台 |
| 赛道道具与远景 | 赞助广告板（`ad_boards.png`）、150/100/50 m 刹车距离牌、Wellington 与 Hangar 直道前 `DRS` 提示牌、2 块实时计时大屏（`bigscreen.png`）、2 座过街天桥、7 个裁判点、外围机库（距赛道 ≥403 m）与灌篱环（半径 ≥1540 m） |
| 天空穹顶与光照 | `V5_SkyDome`（96×64 球体，4 200 m）采用连续程序化大气黄昏渐变 + 对齐 `LGT_V5Sun` 的暖色方位角散射，彻底消除地平线色阶条带 |

---

## 4. 赛车遥测动力学与动态灯光（`RIG_F1_Race`）

骨架 `RIG_F1_Race`（归入 `SCIFI_F1_2035`）及车体材质全部由逐帧物理量驱动：

| 遥测通道 / 材质 | 物理模型与驱动公式 | 视觉效果 |
|---|---|---|
| `Bone_Root` / `Bone_Heading` | `racing_xy`（`z=0.012`），`yaw = heading - 90°` | 轮胎精准贴合沥青路面，切弯航向零跳变 |
| `Bone_Body` 姿态 | 俯仰 `clamp(acc·0.085, -1.9..1.4)° - 0.16·换挡脉冲`；侧倾 `clamp(-lat_signed·0.26, ±2.2)°` | 制动点头、出弯抬头、换挡顿挫与弯道侧倾 |
| 转向与方向盘（`steer`） | 阿克曼角 `deg(κ·3.6 m)`，传动比 `steer_ratio = 9.5` 驱动 `Bone_Steering_Wheel` | 前轮转向与座舱方向盘、拨片、仪表屏实时联动 |
| 15 颗换挡提示灯 | `Mat_ShiftLED_Green/Yellow/Red` 按 8 档内转速比依次点亮，升档瞬间高频闪烁 | `S02_Onboard` 与 `S19_Onboard3` 座舱细节鲜活 |
| 碳陶刹车盘与卡钳热辉光 | 热惯性积分：`-acc > 1.8 m/s²` 快速升温，松刹按对流时间常数 `τ = 1.25..1.75 s` 指数退火 | 驱动 `Mat_Brake_HeatGlow`、`Mat_BrakeDisc_CarbonCeramic` 环形红橙辉光与 `Mat_Caliper_Anodized` 余热，持续亮入弯心并平滑消退 |
| FIA 尾部雨灯 / ERS 灯 | 独立材质 `Mat_FIA_RainLight`：`acc < -2.5 m/s²` 时 **6.0 Hz 高频红闪**，其余常亮暗红微光 | 重刹与高速收油能量回收时呈现真实 F1 尾灯爆闪 |
| `drs` 尾翼襟翼 | 直道（`|κ|<0.0016` 且 `v>240 km/h`）全开 `1.0`，入弯自动关闭 `0.0` | Hangar / Wellington 大直道尾翼自动平放减阻 |
| 随车三点补光 | `LGT_V5Car_0..2` 通过 `V5_CarLightReceivers` 精准绑定全部 244 个车身/轮组/Halo 对象 | 车漆清漆与碳纤维立体通透，地面零多余光斑 |

---

## 5. 26 机位分镜与广播级景深（`V5_08_Cameras`）

切点严格吸附 108 BPM 拍点（`1 拍 = 13.333 帧`，共 162 拍）。新增独立动画焦点 `V5_CamFocus` 全程追踪车身中心（`Bone_Root + 0.45m Z`），消除追随/固定镜头的焦点偏移；弯道镜头加入平滑横向 G 力地平线微倾耦合与路肩高频微振：

| # | 机位 | 帧范围 | t (s) | 类型 | 光圈 / 景深 | 镜头语言说明 |
|---|---|---|---|---|---|---|
| 1 | `Cam_S01_RearChase` | 1–108 | 0.0–4.5 | 追随 | `f/4.0` | 主直道 300 km/h 车尾低角度拉升跟拍 |
| 2 | `Cam_S02_Onboard` | 109–201 | 4.5–8.4 | 车载 | `f/11` 超焦距 | **座舱 Halo 肩部视角**：Abbey/Farm 高速弯实时方向盘转动、换挡灯与前轮切弯 |
| 3 | `Cam_S03_ChaseRise` | 202–294 | 8.4–12.3 | 追随 | `f/4.0` | 后方升起侧移切入 Village 制动区 |
| 4 | `Cam_S04_Hairpin` | 295–401 | 12.3–16.7 | 固定 | **`f/3.5` DOF** | 发夹弯内侧迎面定焦，碳陶刹车盘红热辉光 + 远景刹车牌奶油虚化 |
| 5 | `Cam_S05_ChaseAintree` | 402–481 | 16.8–20.1 | 追随 | `f/4.0` | Aintree 出弯贴地加速跟拍 |
| 6 | `Cam_S06_Orbit1` | 482–561 | 20.1–23.4 | 环绕 | `f/3.6` | 104°→52° 动态绕车展示车身侧面流线 |
| 7 | `Cam_S07_ChaseAccel` | 562–641 | 23.5–26.8 | 追随 | `f/4.0` | Wellington 直道 DRS 打开加速尾随 |
| 8 | `Cam_S08_FastPan` | 642–734 | 26.8–30.7 | 固定 | **`f/4.0` DOF** | 高速外侧 14 m 快速摇摄（多普勒横掠） |
| 9 | `Cam_S09_WheelMacro` | 735–788 | 30.7–32.9 | 轮组微距 | **`f/2.8` DOF** | 前轮悬挂/卡钳特写 + 速度/路肩高频微振 + 浅景深背景分离 |
| 10 | `Cam_S09b_ChaseFast` | 789–841 | 33.0–35.1 | 追随 | `f/3.2` | 30→27 mm 广角贴地高速跟拍 |
| 11 | `Cam_S10_OrbitBrooklands` | 842–894 | 35.2–37.4 | 环绕 | `f/3.4` | Brooklands 重刹入弯绕拍，前后刹车盘炽热发光 |
| 12 | `Cam_S11_Luffield` | 895–1001 | 37.4–41.8 | 固定 | **`f/3.8` DOF** | Luffield 长慢弯外侧定焦跟摇 |
| 13 | `Cam_S12_ChaseWoodcote` | 1002–1081 | 41.9–45.2 | 追随 | `f/4.0` | Woodcote 全油门出弯横向 G 力微倾跟拍 |
| 14 | `Cam_S13_WoodcoteTele` | 1082–1161 | 45.2–48.5 | 固定长焦 | **`f/4.0` DOF** | 长焦空间压缩迎面冲刺，背景看台柔化虚化 |
| 15 | `Cam_S14_HeliDrop` | 1162–1241 | 48.6–51.9 | 直升机 | `f/5.6` | 28→12.5 m 高空俯冲追击 |
| 16 | `Cam_S15_OrbitCopse` | 1242–1334 | 51.9–55.8 | 环绕 | `f/3.4` | Copse 高速弯前 108°→48° 环绕 |
| 17 | `Cam_S16_ChaseCopse` | 1335–1414 | 55.8–59.1 | 追随 | `f/4.0` | Copse 高 G 弯心尾随 + 6 Hz 雨灯闪烁 |
| 18 | `Cam_S17_Maggotts` | 1415–1508 | 59.1–63.0 | 固定 | `f/4.0` | Maggotts-Becketts 高速 S 弯高台无遮挡摇摄 |
| 19 | `Cam_S18_ChaseRise2` | 1509–1601 | 63.1–66.9 | 追随 | `f/4.0` | Chapel 出弯拉升驶入 Hangar 大直道 |
| 20 | `Cam_S19_Onboard3` | 1602–1681 | 67.0–70.3 | 车载 | `f/11` 超焦距 | **座舱中央防滚架视角**：325 km/h 极速冲刺，换挡灯攀升与微幅修舵 |
| 21 | `Cam_S20_StoweTele` | 1682–1788 | 70.3–74.7 | 固定长焦 | **`f/4.0` DOF** | Hangar 末端至 Stowe 重刹入弯无遮挡长焦压缩 + 刹车辉光 |
| 22 | `Cam_S21_OrbitStowe` | 1789–1881 | 74.8–78.6 | 环绕 | `f/3.4` | Stowe 弯心至出弯绕拍（刹车余热平滑消退） |
| 23 | `Cam_S22_ChaseLow` | 1882–1961 | 78.7–82.0 | 追随 | `f/3.2` | Vale 前低角度跟拍 + FIA 尾灯爆闪 |
| 24 | `Cam_S23_HeliReveal` | 1962–2054 | 82.0–85.9 | 直升机 | `f/6.3` | 22→44 m 高空拉升俯瞰银石全景 |
| 25 | `Cam_S24_Club` | 2055–2121 | 85.9–88.7 | 固定 | **`f/3.5` DOF** | 最后一弯 Club 外侧近景定焦摇摄 |
| 26 | `Cam_S25_AerialOut` | 2122–2161 | 88.7–90.3 | 航拍收尾 | `f/4.5` | 3→11 m 斜向拉升冲线 + 末 16 帧平滑压暗淡出 |

---

## 6. 音乐卡点与遥测驱动 F1 V6 混动音效（`pipeline/synth_sfx.py`）

| 模块 | 参数与技术实现 |
|---|---|
| 配乐基底 | *The Weeknd — After Hours*（108 BPM，240.814 s 起截取 90.04 s / 162 拍，`audio_v5_90s.m4a`） |
| F1 动力总成建模 | 8 档无缝变速箱（单圈 52 次升档 / 52 次降档，高速段维持 `9,850–12,430 RPM` 功率带）、`~45 ms` 升档断火爆震、`~58 ms` 制动降档自动补油（Rev-match blip） |
| 1.6L V6 涡轮混动音色 | 曲轴/半阶次谐波 + `f0..8f0` 排气谐波簇 + 非对称排气歧管饱和与多共振峰滤波 + MGU-H 涡轮高频哨音（`2.65–5.4 kHz`）+ MGU-K 电机啸叫 |
| 空气动力与路肩 | 随 `v²` 增长的高速风噪、硬过弯（`|κ| > 0.008`）锯齿路肩震动声 |
| 26 镜头声学透视 | AST 自动解析 `v5_anim.py` 的 `SHOTS`：`Onboard` 座舱进气嘶吼、`Fixed` 真实物理多普勒频移 `343 / (343 + v_radial)` 与立体声横掠声像、`Chase/Wheel` 尾部排气冲击、`Heli` 高空空气衰减；切镜处 `50 ms` 等功率交叉淡化零爆音 |
| 母带混音指标 | `audio_v5_sfx_mix_90s.m4a`（48 kHz 立体声 AAC 256k，EQ 让位 + 侧链动态闪避，综合响度 `-14.2 LUFS`，真峰值 `TP <= -1.0 dBFS`，末 1.5 s 淡出） |

---

## 7. 文件清单与一键复现

| 文件 | 说明 |
|---|---|
| `pipeline/gen_textures.py` | Pillow 程序化生成高清车库/广告板/大屏/刹车牌/DRS 贴图至 `textures/` |
| `pipeline/v5_env.py` | 银石环境与车体材质构建 → `LATEST/v5_stage_env.blend` |
| `pipeline/v5_anim.py` | 遥测烘焙 + 动态刹车热辉光/雨灯/换挡灯 + 26 机位与 DOF + 物理/遮挡自检 → `LATEST/v5_stage_anim.blend` |
| `pipeline/v5_clay.py` | 白模转换（精确识别 244 个赛车几何，保留 DOF/运动模糊，修正 `Standard` 曝光曲线防过曝）→ `LATEST/v5_stage_anim_clay.blend` |
| `pipeline/v5_stills.py` | 支持 `-- --render` 直接从 `.blend` 渲染全部 26 张 1080p 剧照并拼装高清标注版 `renders_v5/stills/contact_sheet.jpg` |
| `pipeline/v5_viewport_fast.py` | 视口轻量化开关（`-- fast` / `-- normal`，仅对 `MESH` 切换 `BOUNDS` 并写回保存） |
| `pipeline/synth_sfx.py` | 遥测同步 F1 V6 涡轮混动引擎声合成 → `renders_v5/sfx_engine_90s.wav` |
| `pipeline/render_v5.py` / `render_clay.py` | 彩色 / 白模 2 161 帧全片序列渲染 |
| `pipeline/mux_v5.sh` / `mux_clay.sh` | 封装无声版、纯配乐版与 `*_sfx_1080p.mp4` 引擎混音成片（支持 `--sfx-only` 快速重混） |

### 复现命令

```bash
B="/d/APPs/steam/steamapps/common/Blender/blender.exe"

# 1. 贴图 + 环境 + 动画 + 白模工程
python pipeline/gen_textures.py
"$B" -b -P pipeline/v5_env.py
"$B" -b -P pipeline/v5_anim.py
"$B" -b -P pipeline/v5_clay.py

# 2. 快速渲染全部 26 镜头 1080p 剧照与拼图（约 1 min，无需重渲 2161 帧）
"$B" -b LATEST/v5_stage_anim.blend -P pipeline/v5_stills.py -- --render
"$B" -b -P pipeline/v5_clay.py -- --render-stills

# 3. 合成遥测引擎声浪并封装成片
python pipeline/synth_sfx.py
bash pipeline/mux_v5.sh --sfx-only
bash pipeline/mux_clay.sh --sfx-only
```

---

## 8. 边界说明

- **平面高程**：OSM 赛道中心线 `z=0`；银石本身为二战机场改建赛道、地势平坦，如需厘米级起伏需额外叠加 LiDAR DEM 数据。
- **单车计时圈**：当前为单台 F1 飞驰排位圈（Qualifying Hotlap），不含多车缠斗与进站换胎动画。
- **遥测拟合精度**：速度剖面与 8 档引擎转速由真实弯道曲率与下压力抓地力包线推演，视听节奏与真实银石杆位车载高度吻合，但并非某一场官方 ECU 原始采样。
- **数据许可**：赛道中心线源自 OpenStreetMap（ODbL），公开发布请署名 `© OpenStreetMap contributors`。
