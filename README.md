# blender-supercar

真实银石赛道整圈的 AI 程序化 F1 赛车全链路工程（Blender 5.3.0 / EEVEE 纯 CPU / 26 机位广播级运镜 + 遥测驱动 V6 混动引擎音效）。

## 目录

| 目录 | 内容 | 说明 |
|---|---|---|
| **[LATEST/](LATEST/)** | `v5_stage_anim.blend`、`v5_stage_env.blend`、`v5_stage_anim_clay.blend` | **最新工程，只放这三个**（彩色完整动画 / 纯环境 / 白模动画） |
| [pipeline/](pipeline/) | `gen_textures.py`、`v5_env.py`、`v5_anim.py`、`v5_clay.py`、`v5_stills.py`、`v5_viewport_fast.py`、`v5_preview.py`、`synth_sfx.py`、`render_v5.py`、`render_clay.py`、`mux_v5.sh`、`mux_clay.sh`、`v4_stage_rig.blend` | 现役全自动脚本管线；`v4_stage_rig.blend` 是模型+骨架输入 |
| [renders_v5/](renders_v5/) | 引擎混音成片 `*_sfx_1080p.mp4`、纯配乐成片 `*_1080p.mp4`、无声版 `*_silent.mp4`、`sfx_engine_90s.wav`、`audio_v5_sfx_mix_90s.m4a`、`stills/`、`clay_stills/`、`frames/`、`clay_frames/` | 最新视频、音轨与 26 镜头剧照产物 |
| [textures/](textures/) | 人群 / 车库楼 / 赞助广告板 / 刹车牌 / DRS 牌 / 实时计时大屏贴图 | 由 `pipeline/gen_textures.py`（Pillow）高清程序化生成 |
| [track_data/](track_data/) | Silverstone / Monza 的 json+csv+生成器 | **改赛道几何与速度规划就改这里** |
| [audio/](audio/) | `audio.wav`（原曲）、`beats.json`、`cue.json` | 108 BPM 拍点数据 |
| **[scenes/](scenes/)** | 场景库：历届赛历、天气预设、8 个精选场景卡、AI 提示词包 | **拍什么先看这里** |
| [docs/](docs/) | [docs/README_V5.md](docs/README_V5.md)（主技术文档）、`README_V4.md`、赛道数据说明 | 物理规则、机位表、材质/遥测/音效细节 |
| [archive/](archive/) | `blend/` 旧工程、`scripts/` 旧脚本、`renders/` 旧成片 | 只读归档，勿在此修改 |
| [_unrelated/](_unrelated/) | 不属于本项目的杂项 | 可删 |

## 成片矩阵（彩色 & 白模 × 引擎混音 / 纯配乐 / 无声）

| 版本 | 推荐主交付（音乐 + F1 V6 引擎遥测混音） | 纯配乐版（After Hours） | 用途 |
|---|---|---|---|
| **彩色正片**（黄昏光照 + 车漆碳纤 + 刹车盘红热辉光 + 广播级景深） | [renders_v5/f1_silverstone_lap_sfx_1080p.mp4](renders_v5/f1_silverstone_lap_sfx_1080p.mp4) | [renders_v5/f1_silverstone_lap_1080p.mp4](renders_v5/f1_silverstone_lap_1080p.mp4) | 最终视听成片 |
| **白模评审片**（统一雕塑灰模，`Standard` 防过曝曲线，保留 DOF 与运动模糊） | [renders_v5/f1_silverstone_clay_sfx_1080p.mp4](renders_v5/f1_silverstone_clay_sfx_1080p.mp4) | [renders_v5/f1_silverstone_clay_1080p.mp4](renders_v5/f1_silverstone_clay_1080p.mp4) | 评审形体、光影、运镜、剪辑节奏 |

- **遥测同步引擎声（[pipeline/synth_sfx.py](pipeline/synth_sfx.py)）**：读取 `silverstone_track.json` 与 `v5_anim.py` 的 26 个镜头轨迹，合成 48 kHz 立体声 1.6L V6 涡轮混动声浪（8 档无缝变速箱 `9,850–12,430 RPM`、MGU-H 涡轮哨音、升档断火爆震、降档补油、风噪、路肩震动，以及固定机位真实物理多普勒频移与立体声横掠声像），并与 *After Hours* 侧链动态混音（`-14.2 LUFS`，`TP <= -1.0 dBFS`）。

重新生成白模或刷新混音：

```bash
B="/d/APPs/steam/steamapps/common/Blender/blender.exe"
"$B" -b -P pipeline/v5_clay.py                # 生成白模工程 LATEST/v5_stage_anim_clay.blend
"$B" -b -P pipeline/render_clay.py            # 渲染 2161 帧白模（约 12 min）
python pipeline/synth_sfx.py                  # 生成 90.04s 遥测同步引擎声 sfx_engine_90s.wav（约 15 s）
bash pipeline/mux_clay.sh                     # 合成无声 + 纯配乐 + 引擎混音版（加 --sfx-only 仅快速重混音轨）
bash pipeline/mux_v5.sh --sfx-only            # 复用已有彩色视频流，快速更新引擎混音正片
```

## 打开哪个

打开 **[LATEST/v5_stage_anim.blend](LATEST/v5_stage_anim.blend)**。内含完整 F1 赛车、19 骨骼遥测绑定、银石赛道细节环境、2161 帧物理烘焙动画与 26 台摄影机。

`v5_stage_env.blend` 仅含环境与静态赛车，供修改环境使用（改完重跑 `v5_anim.py` 即可同步动画与机位）。

## 改东西的四条路

**1. 改单个物件**（挪看台、换广告板、调灯光）
直接打开 `LATEST/v5_stage_anim.blend`，根集合 `Scene Collection` 零散落对象，Outliner 按 9 个规范集合组织：

| 集合 | 内容 |
|---|---|
| `SCIFI_F1_2035` | `RIG_F1_Race` 骨架与全部 244 个车身/底盘/座舱方向盘/悬挂/车轮/贴花部件 |
| `V5_01_Road` | 主路面（含离线橡胶碎屑）、赛车线、13 处重刹胎痕带、边线、红白路肩、13 处弯心香肠路肩、pit lane |
| `V5_02_Terrain` | 地面、割草条纹草地缓冲带、砾石坑、外围灌篱环、平滑大气黄昏穹顶 `V5_SkyDome` |
| `V5_03_Barriers` | 混凝土护栏基座、金属护栏、青色灯带、防护网立柱 |
| `V5_04_Stands` | 6 座模块化看台（组件 Empty 父级 + 观众阶梯/顶棚/钢梁/旗杆） |
| `V5_05_Pit` | 维修墙、维修墙指挥台、出口绿灯信号柱、车库大楼、楼顶 VIP 看台 |
| `V5_06_Props` | 广告板、刹车距离牌、DRS 提示牌、弯心防撞柱、大屏、人行天桥、裁判点、机库、起跑龙门架 |
| `V5_07_Lighting` | 太阳、天空补光、3 盏随车柔光（Light Linking 专属绑定 `V5_CarLightReceivers`） |
| `V5_08_Cameras` | 26 台摄影机（`Cam_S01..Cam_S25`）+ 广播级景深焦点目标 `V5_CamFocus` |

**2. 改赛道形状或全链路重跑**
改 [track_data/](track_data/) 里的 json，然后按顺序执行管线：

```bash
B="/d/APPs/steam/steamapps/common/Blender/blender.exe"
python pipeline/gen_textures.py    # 生成高清程序化贴图
"$B" -b -P pipeline/v5_env.py      # 构建银石环境 -> LATEST/v5_stage_env.blend
"$B" -b -P pipeline/v5_anim.py     # 烘焙动画 + 26 机位 + 遮挡/物理自检 -> LATEST/v5_stage_anim.blend
"$B" -b -P pipeline/render_v5.py   # 终渲 2161 帧 1080p（约 30 min）
python pipeline/synth_sfx.py       # 合成遥测引擎音效
bash pipeline/mux_v5.sh            # 封装全部彩色 MP4 成片
```

**3. 快速重出全部 26 镜头 1080p 剧照与拼图（无需重渲 2161 帧，约 1 min）**

```bash
B="/d/APPs/steam/steamapps/common/Blender/blender.exe"
"$B" -b LATEST/v5_stage_anim.blend -P pipeline/v5_stills.py -- --render
# 输出 renders_v5/stills/shot_01_*.jpg .. shot_26_*.jpg 与带机位焦段/光圈标注的 contact_sheet.jpg

# 单帧快速抽检（输出至 renders_v5/test/）
"$B" -b -P pipeline/v5_anim.py -- --test 60,160,350,760,1120,1640,1730
```

## 视口流畅度加速

场景共 668 个对象（608 个网格）。通过 `v5_viewport_fast.py` 一键切换视口轻量化模式（仅改 `hide_viewport` 与网格 `display_type`，渲染不受任何影响）：

```bash
B="/d/APPs/steam/steamapps/common/Blender/blender.exe"

# 快速模式：看台/道具/地形集合视口隐藏，重网格切换为 BOUNDS 包围盒并自动保存
"$B" -b LATEST/v5_stage_anim.blend -P pipeline/v5_viewport_fast.py -- fast

# 恢复默认实体贴图显示并保存
"$B" -b LATEST/v5_stage_anim.blend -P pipeline/v5_viewport_fast.py -- normal
```

UI 常用快捷键：`Z` → Solid、`Numpad /` 局部独显选中、`Numpad .` 聚焦选中、Outliner 点击集合眼睛开关。

## 复现环境

Blender 5.3.0，无独立 GPU（Cycles compute device = NONE），EEVEE 纯 CPU 光线追踪，1080p 32 samples 单帧约 2.0–2.8 s。

---

## V6《蜘蛛侠：纵横宇宙》3D 摩天海港立交赛道大片版（Sky-Harbor 2099 Stylized Edition）

在 100% 保留 V5 银石写实工程不动的前提下，新增独立的 **V6 三维立交超级赛道 + 平行宇宙漫画大片全链路**（详见 [docs/README_V6_SPIDERVERSE.md](docs/README_V6_SPIDERVERSE.md)）：

- **全新 3.72 km 三维高差倾斜立交赛道（`track_data/spiderverse_circuit.json`）**：`ΔZ = +42.35 m` 垂直高差、`+13.5°` Eau-Rouge 冲天陡坡、`632 m` 双塔斜拉跨海天桥、`17.4°` 碗状倾斜飞墙弯、`-13.9°` Corkscrew 螺旋俯冲与 `520 m` 全封闭赛博频闪隧道（`341 km/h` 极速，`53.33 s` = `1,281` 帧 @ 24 fps）。
- **工程文件**：`v6_spiderverse/v6_stage_lookdev.blend`（五大立体巨构赛段 + 湿滑黑曜石霓虹镜面沥青 + 美漫半调网点材质 + `V6_09_ComicFX` 马赫环喷焰/钛合金火花雨/翼尖涡流彩带）、`v6_spiderverse/v6_stage_anim_sv.blend`（全三维姿态绑定 + 12 fps On-Twos 抽帧 + 24 极限大片机位 + `2.39:1` `Comp_V6_SpiderVerse` 合成器）。
- **核心视听特性**：
  - **三维姿态 + 安全 12 fps On-Twos 抽帧**：世界轨迹与 24 台摄影机保持 24 fps 丝滑跟拍，车身局部次级姿态、方向盘、悬挂与三维漫画特效按 2 帧一拍设为 `CONSTANT`；
  - **三幕平行宇宙切换 + 双冲击帧**：Act I 迈尔斯摩天峡谷（`E-1610`）→ Act II 格温 Kuwahara 水彩跨海天桥与 `17.4°` 飞墙弯（`E-65`）→ Act III 2099 频闪隧道与海港终局（`E-928`），嵌有 `f=413..414` 与 `f=1067..1068` 双帧黑白赤红版画冲击帧；
  - **`2.39:1` 宽银幕印刷错位与湿滑镜面光追**：EEVEE `SCREEN` 光追反射倒映两侧摩天霓虹，Cryptomatte 锁定主角赛车 0 px 错位，焦外背景红青色散偏移；
  - **赛段空间声学混音（`pipeline/synth_sfx_sv.py`）**：F1 V6 引擎声融合摩天峡谷回声、跨海大桥高空风啸、赛博隧道混响多普勒与 2099 超低音冲击震爆。
- **V6 专属产物（`renders_v6/`）**：
  - 24 张 `2.39:1` 大片剧照 `renders_v6/stills/shot_*.jpg`、`6×4` 三幕总览 `contact_sheet_v6.jpg`、斜切分镜漫画海报 **[renders_v6/stills/comic_page_sheet.jpg](renders_v6/stills/comic_page_sheet.jpg)**；
  - 三段 4 秒高潮展示片段 `clip1_miles_1610.mp4`（`269–364`）、`clip2_gwen_65.mp4`（`585–680`）、`clip3_2099_impact.mp4`（`993–1088`）及 12 秒合辑 **[renders_v6/v6_spiderverse_showcase_12s.mp4](renders_v6/v6_spiderverse_showcase_12s.mp4)**。
