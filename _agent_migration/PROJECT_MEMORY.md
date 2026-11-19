# `blender-supercar` 全量工程与多智能体记忆交接档案（PROJECT MEMORY）

> **归档时间**：2026-11-19 10:35 (`UTC+8`)
> **源设备工作区**：`D:\项目session\blender-supercar`（Windows 11 / Blender 5.3.0 EEVEE CPU / Python 3.12 / FFmpeg）
> **GitHub 私有仓库**：`https://github.com/TALONXU1/blender-supercar`（`PRIVATE`）
> **主控 Coordinator 会话 ID**：`1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8`（含完整 Swarm 消息板 `#1..#52`、`v6_spiderverse_plan.md` 与全量工具调用轨迹）

---

## 1. 工程全景与双分支隔离架构（V5 写实银石 + V6 纵横宇宙立体海港）

本项目包含两套 **100% 物理与文件级隔离** 的 Blender 5.3.0 全自动程序化 F1 视听工程：

### A. V5 银石整圈广播级写实版（100% 完工 & `57/57` SHA256 锁定验证通过）
- **核心工程（`LATEST/`，只读封存，严禁 V6 脚本覆盖）**：
  - `LATEST/v5_stage_env.blend`：银石赛道完整三维环境（9 大规范集合、`Scene Collection` 零散落对象、6 座看台、维修站大楼、路肩/胎痕/砾石坑、大气黄昏穹顶）。
  - `LATEST/v5_stage_anim.blend`：19 骨骼遥测驱动绑定（`RIG_F1_Race` 244 部件）、`2,161` 帧（`90.04 s` @ `24 fps`）整圈物理烘焙动画、26 台广播级机位 + 零视线遮挡验证。
  - `LATEST/v5_stage_anim_clay.blend`：雕塑灰模评审版（保留景深与运动模糊）。
- **核心成片（`renders_v5/`）**：
  - 彩色引擎混音主交付：`renders_v5/f1_silverstone_lap_sfx_1080p.mp4`（`-14.2 LUFS`, `TP <= -1.0 dBFS`）
  - 彩色纯配乐 / 无声版：`f1_silverstone_lap_1080p.mp4` / `f1_silverstone_lap_silent.mp4`
  - 白模引擎混音 / 纯配乐 / 无声版：`f1_silverstone_clay_sfx_1080p.mp4` / `f1_silverstone_clay_1080p.mp4` / `f1_silverstone_clay_silent.mp4`
  - 全部 `2,161` 帧彩色序列（`renders_v5/frames/`）、`2,161` 帧白模序列（`renders_v5/clay_frames/`）及 26 镜头剧照与总览表（`renders_v5/stills/`、`clay_stills/`）。

### B. V6《蜘蛛侠：纵横宇宙》3D 摩天海港立交赛道大片版（`v6_spiderverse/` + `renders_v6/`）
- **赛道规格（`track_data/spiderverse_circuit.json` + `pipeline/v6_build_circuit.py`）**：
  - 全新 **3.72 km（`3,719.95 m`）** 闭合三维高差倾斜立交街道赛道（Neo-Monaco × Nueva York 2099 Sky-Harbor），`1,860` 个等弧长 `2.0 m` 节点，全三维正交标架 `(T, R, U)`。
  - **垂直高差与坡度**：最低点 `z = +0.15 m`（Eau-Rouge 谷底触底钛合金火花压坑）→ 最高点 `z = +42.50 m`（`632 m` 双塔斜拉跨海天桥），最大爬坡 **`+13.5°`**，最大碗状外倾角 **`+17.4°`**（峰值 `6.35 G`），Corkscrew 螺旋俯冲 **`-13.9°`**，极速 **`341 km/h`**（`520 m` 全封闭赛博频闪隧道），单圈 **`53.333 s` = `96` 拍 @ 108 BPM = `1,281` 帧 @ 24 fps**。
- **24 机位 `2.39:1` Cinema-Scope 三幕平行宇宙结构（`v6_spiderverse/v6_shots_manifest.json`）**：
  - **Act I（`f = 1..427`, `S01..S08`, Earth-1610 迈尔斯摩天峡谷）**：普鲁士深靛蓝暗部 + 布鲁克林绯红/琥珀街灯 + 电光青/绯红相机空间双侧轮廓光；`f = 413..414` 盲顶奔月双帧版画冲击帧；`f = 426..429` 斜切漫画裂口次元穿越。
  - **Act II（`f = 428..894`, `S09..S16`, Earth-65 格温水彩跨海天桥与 `17.4°` 飞墙碗弯）**：薄荷青绿/蜜桃粉表现主义水彩天空 + 焦外 Anisotropic Kuwahara 水彩笔触与红青印刷错版；`f = 893..896` 斜切漫画裂口次元穿越。
  - **Act III（`f = 895..1281`, `S17..S24`, Earth-928 2099 频闪隧道与海港终局）**：黑曜石紫外暗部 + 激光赤红拱肋；`341 km/h` `180°` 甩镜出洞 → **`f = 1067..1068`** 海港重刹双帧正反相黑白赤红冲击帧 → 湿滑霓虹镜面冲线。

---

## 2. Swarm 编组名册与全部 16 个会话 ID 映射表

本仓库 `_agent_migration/antigravity/` 完整封存了本项目相关的全部 **16** 个 Antigravity 会话（含 `brain/<cid>/` 产物/日志/Swarm 消息板与 `conversations/<cid>.db` Checkpointed SQLite 数据库）：

### 现役 V6 Swarm 核心编组（父会话：`1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8`）
| 角色名 (`agent_name`) | Conversation ID | 负责模块与最新状态 |
|---|---|---|
| **`coordinator`（主控）** | `1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8` | **主入口会话**：统筹 V5 收尾与 V6 Spider-Verse 全流程，内含 `v6_spiderverse_plan.md` 与 `.system_generated/swarm/` 消息板 `#1..#52` |
| **`track`** | `62527b59-0213-41b2-b3ab-ff115c915c3b` | `pipeline/v6_build_circuit.py` + `track_data/spiderverse_circuit.json`/`.csv`（3.72 km 三维倾斜立交赛道与遥测解算，100% 完工 `#32`） |
| **`env-2`** | `b13776a0-7d9f-4f63-9e67-c8ecc5f11412` | `pipeline/v6_sv_textures.py` + `pipeline/v6_sv_env.py` → `v6_spiderverse/v6_stage_lookdev.blend`（Iteration-2 美术升级 100% 完工并校验通过 `#45`） |
| **`anim`** | `a98b6c71-b658-48ee-9b28-e9a1c116099c` | `pipeline/v6_sv_comp.py` + `v6_sv_stills.py` + `render_v6_sv.py` → `v6_stage_anim_sv.blend`（Iteration-2 全部 24 剧照 + 海报 + 3×96f 序列帧已于 `#51` 全部落盘！） |
| **`sfx`** | `01e3331f-d103-4af9-90bc-a12f64086d33` | `pipeline/synth_sfx_sv.py` + `pipeline/mux_v6_sv.sh` → `sfx_spiderverse_53s.wav` + `audio_v6_sv_mix_53s.m4a`（Iteration-2 `+3 dB` 火花与斜拉索拟音已更新落盘，待执行 `--clips` 重封装） |
| **`verifier`** | `71c1ec74-2a73-43c2-80c2-96dffd9739a3` | 艺术总监级量化与技术 QA（已完成 Iteration-1 审查 `#41`，待对 Iteration-2 封装后的 3 段 MP4 执行 Round-2 复核） |
| **`monitor`** | `6e1acc3f-eaac-4bed-95a2-c4f90863575e` | Swarm 心跳巡检守护进程 |
| **`env`（早期 worker）** | `46b51757-eef7-4958-943d-57de1b64a881` | 早期 V6 环境探针会话（已由 `env-2` 接替） |

### 历史 V5 优化 / 整理 / 工具关联会话（共 8 个）
| 角色 / 标题 | Conversation ID | 说明 |
|---|---|---|
| Root: *Project Progress Review And Optimization* | `16b5f3cb-4bce-43d1-a09a-ebf98bd665b7` | V5 银石整圈工程审查与画质/物理优化主会话 |
| `env` (under `16b5f3cb`) | `f904dce7-b62b-4bab-b561-90c92d39c8a3` | V5 银石赛道材质与场景细节升级 |
| `verifier` (under `16b5f3cb`) | `d4f056b1-8bc5-4458-b96b-9d0293a59d65` | V5 全片质量与物理指标核验 |
| `tidy` (under `16b5f3cb`) | `4cc01d4d-c499-4f55-b213-878718617fe0` | 工作区目录规范化归档（`LATEST/`、`archive/`、`pipeline/`） |
| `monitor` (under `16b5f3cb`) | `f5adc3c6-00d5-45e7-919a-267af295b5d1` | V5 Swarm 巡检记录 |
| Root: *Project Cleanup and Progress Summary* | `80a8f1d5-652e-4a53-9931-da555b39f579` | 阶段性清理与进度总结 |
| Root: *Connect Open Design Motion* | `7ac4a8d6-66bf-47ac-b14f-dc6a6fd3deb0` | 动作与设计插件连接配置记录（已做敏感 Token 脱敏） |
| Root: *Antigravity 插件支持情况* | `8717e77d-a125-4b01-893b-0669d971d4d8` | Antigravity 插件与环境调研会话 |

---

## 3. 精确断点恢复指南（EXACT RESUME CHECKPOINT）

### 已完成并落盘的进度（截至消息板 `#51` / `2026-11-19 10:31:45`）
1. **V6 Iteration-1**：100% 渲染、混音并完成审查（`#39`、`#40`、`#41`）。
2. **V6 Iteration-2 美术与音频升级（100% 落盘）**：
   - **Lookdev（`@env-2` `#45`）**：`v6_spiderverse/v6_stage_lookdev.blend`（`3.75 MB`，`0` 根散落对象，`1.49–1.85 s/frame`）已修复相机空间双侧轮廓光（`WORLD -> CAMERA` 法线变换）、隧道顶棚 `visible_shadow = False` 解锁漫反射、普鲁士深靛蓝车漆提亮、双极性 `±45°` 钢笔交叉排线（`DiagAnis = 1.21–1.46`）以及三幕平行宇宙显著 RGB 色彩分离；6 张预览图位于 `renders_v6/preview/`。
   - **空间声学混音（`@sfx`）**：`renders_v6/sfx_spiderverse_53s.wav` 与 `renders_v6/audio_v6_sv_mix_53s.m4a` 已于 `11-18 17:20` 完成 Iteration-2 升级（Eau-Rouge 钛合金火花刮擦 `f=276..308` 与跨海天桥斜拉索呼啸 `f=585..620` 提升 `+3 dB`）。
   - **合成器、24 剧照、海报与 3 段 96 帧序列（`@anim` `#51`）**：
     - 在用户暂停迁移前最后一刻（`10:31:45`），`@anim` 已将全部 Iteration-2 升级落盘：
       * `v6_spiderverse/v6_stage_anim_sv.blend`（`0` 遮挡、`pass_cryptomatte_depth = 6`、`8px` `0.06..0.94` 高对比半调网点、墨线后背景 Kuwahara 水彩、非黑键斜切次元裂口 `SV_PortalSlashTear.png`、发卡弯樱桃红刹车盘辉光）
       * `renders_v6/stills/`：全部 **24 张 Iteration-2 `2.39:1` 1080p 剧照**（`S21 P95=176.2 >= 175`，`S24 MeanL=74.8 >= 50`，`PopRatio` 最高 `4.38`）+ `contact_sheet_v6.jpg` + `comic_page_sheet.jpg`
       * `renders_v6/clips_frames/`：全部 **3 × 96 帧 Iteration-2 1080p 序列帧**均已渲染完毕！（`clip1_miles_1610/f_0269..0364.jpg`、`clip2_gwen_65/f_0585..0680.jpg`、`clip3_2099_impact/f_0993..1088.jpg`，最新时间戳 `2026-11-19 10:31:02`）
     - 注：若需核对 `shot_21..24` 或重出任意单帧，所有源工程与贴图均已就绪；当前 `renders_v6/*.mp4` 仍为 `11-18 17:14` 的 Iteration-1 视频封装，**只需立即运行一步 `mux_v6_sv.sh --clips` 即可生成 Iteration-2 最新展示成片！**

### 在新设备上恢复后的精确下一步动作（Step-by-Step）
1. **Step A — 封装 V6 Iteration-2 三段 4 秒展示片与 12 秒合辑（约 15 秒）**：
   ```bash
   bash pipeline/mux_v6_sv.sh --clips
   ```
   > 将 `renders_v6/clips_frames/` 下已渲好的 Iteration-2 帧序列与 Iteration-2 `audio_v6_sv_mix_53s.m4a` 封装为最新 `clip1_miles_1610.mp4`、`clip2_gwen_65.mp4`、`clip3_2099_impact.mp4` 与 `v6_spiderverse_showcase_12s.mp4`。

2. **Step B — `@verifier` Round-2 量化复核**：
   - 核验 Iteration-2 的 24 张剧照、漫画海报及新封装的 3 段 MP4 / 12 秒合辑（确认 `PopRatio >= 1.30`、`S21 P95 >= 175`、`S24 MeanL >= 50`、`Clip% < 8.5%`、响度 `-13..-14 LUFS`、`TP <= -1.0 dBFS`、`LATEST/` V5 哈希 100% 未动）。

3. **Step C — Round-3 全片 `1,281` 帧 1080p 终极母版渲染与封装**：
   > **重要性能经验（来自 `#49`）**：开启 `pass_cryptomatte_depth=6` 后，在核显/共享显存机器上**不要**同时开 2 个并发 Blender 进程（会导致 Vulkan 显存抖动退化到 `70 s/f`）；请使用**单进程多线程（如 `-t 12` 或新设备物理核心数）顺序跑满全片**（单帧稳定 `~2.3–2.8 s/f`，`1,281` 帧约 **50–60 分钟**；若新设备有独显则会更快！）：
   ```bash
   B="<NEW_BLENDER_EXECUTABLE>"
   "$B" -b -t 12 -P pipeline/render_v6_sv.py -- --all
   bash pipeline/mux_v6_sv.sh --full
   bash pipeline/mux_v6_sv.sh --split
   ```
   产出全片母版：
   - `renders_v6/v6_skyharbor_spiderverse_1080p.mp4`（及同名归档 `f1_silverstone_spiderverse_1080p.mp4`）
   - `renders_v6/f1_silverstone_spiderverse_silent.mp4`
   - `renders_v6/f1_silverstone_v5_vs_v6_split_1080p.mp4`（V5 vs V6 同屏对比大片）

---

## 4. 新设备硬编码路径清单与一键替换命令（Hardcoded Path Checklist）

源设备使用了以下 3 处本机路径，已全部接入 `_agent_migration/restore_context.py --rewrite-paths` 一键重写工具：

1. **项目根目录 `PROJ = r"D:\项目session\blender-supercar"`**（共 19 个脚本）：
   - Python 管线（16 个）：`pipeline/gen_textures.py`、`render_clay.py`、`render_v5.py`、`render_v6_sv.py`、`synth_sfx.py`、`synth_sfx_sv.py`、`v5_anim.py`、`v5_clay.py`、`v5_env.py`、`v5_preview.py`、`v5_stills.py`、`v6_sv_build.py`、`v6_sv_comp.py`、`v6_sv_env.py`、`v6_sv_stills.py`、`v6_sv_textures.py`
   - Bash 封装脚本（3 个，`PROJ="D:/项目session/blender-supercar"`）：`pipeline/mux_clay.sh`、`pipeline/mux_v5.sh`、`pipeline/mux_v6_sv.sh`
2. **Blender 可执行文件 `D:\APPs\steam\steamapps\common\Blender\blender.exe`**（Git-Bash 形式 `/d/APPs/steam/steamapps/common/Blender/blender.exe`）：
   - 出现在命令行调用与文档变量 `B="..."`（`README.md`、`docs/README_V4.md`、`docs/README_V5.md`、`docs/README_V6_SPIDERVERSE.md`）。
3. **FFmpeg 可执行文件 `C:\Users\86052\scoop\shims\ffmpeg.exe`**（Git-Bash 形式 `/c/Users/86052/scoop/shims/ffmpeg.exe`）：
   - Python 音频合成：`pipeline/synth_sfx_sv.py`（第 53 行 `FFMPEG = r"..."`）
   - Bash 视频混流：`pipeline/mux_clay.sh`、`pipeline/mux_v5.sh`、`pipeline/mux_v6_sv.sh`（顶部 `FF=...`）

### 新设备一键替换所有路径 + 恢复 Antigravity 会话命令
```bash
python _agent_migration/restore_context.py \
  --restore-antigravity \
  --rewrite-paths \
  --proj "<新设备项目绝对路径>" \
  --blender "<新设备 blender 可执行文件绝对路径>" \
  --ffmpeg "<新设备 ffmpeg 可执行文件绝对路径>"
```
> 提示：若在克隆后的仓库根目录直接运行，可省略 `--proj`（脚本会自动取当前仓库根目录，并同步更新 `~/.gemini/config/projects/b8f1cf42-d4c5-4e16-b789-f04062d11bb5.json` 与 `conversation_summaries.db` 中的工作区 URI）。

---

## 5. 关键防坑铁律（Agent Rules to Keep）
1. **严禁对二进制/媒体文件调用 `read_file`**：绝不对 `.jpg`、`.png`、`.mp4`、`.m4a`、`.wav`、`.blend`、`.db` 调用 `read_file`（避免撑爆上下文或触发 400 报错）；图像指标统一用 Python `PIL`/`numpy` 脚本检查，音视频统一用 `ffprobe` 检查。
2. **100% V5 隔离**：任何 V6 修改严禁覆写 `LATEST/v5_*.blend` 或 `renders_v5/*`。
3. **Python 依赖（系统 Python，非 Blender 内置 Python）**：运行 `pipeline/synth_sfx_sv.py` 或 `v6_sv_textures.py` 需确保系统 Python 安装了 `numpy`、`scipy`、`Pillow`（`pip install numpy scipy pillow`）。
