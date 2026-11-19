# 新设备 3 步无缝恢复指南（RESTORE ON NEW DEVICE）

本仓库已完整打包 **`blender-supercar` 全量工程文件（V5 银石整圈成片 + V6 纵横宇宙 3D 海港赛道）**、**全部 16 个 Antigravity 智能体会话与 Swarm 消息板数据库**，以及 **14 个自定义 Blender/导演/记忆技能包**。

在新电脑（Windows / macOS / Linux 均支持）上只需 **3 步** 即可无缝接续：

---

## 第 1 步：克隆私有仓库并安装基础依赖

确保新设备已安装 **Git**、**GitHub CLI (`gh`)**、**Blender 5.3+**、**FFmpeg** 以及 **Python 3.10+**（含 `numpy`、`scipy`、`pillow`）：

```bash
gh auth login
gh repo clone TALONXU1/blender-supercar
cd blender-supercar

# 安装音频合成与程序化贴图所需的轻量 Python 库
pip install numpy scipy pillow
```

---

## 第 2 步：一键恢复 Antigravity 会话/技能 + 自动修正新设备路径

> **注意**：执行恢复前请先**完全关闭**新电脑上的 Antigravity 客户端，避免 SQLite 数据库锁冲突（脚本会自动将新电脑 `~/.gemini/` 中任何同名旧文件备份到 `_backup_before_blender_supercar_<时间戳>/`，绝不覆盖丢失你新电脑上的其他对话）。

在克隆后的 `blender-supercar` 根目录下运行 **1 条命令**：

```bash
# Windows PowerShell / Git Bash 示例（请将 --blender 和 --ffmpeg 替换为你新电脑上的实际路径）：
python _agent_migration/restore_context.py \
  --restore-antigravity \
  --rewrite-paths \
  --proj "D:/blender-supercar" \
  --blender "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" \
  --ffmpeg "C:/scoop/shims/ffmpeg.exe"
```

<details>
<summary>macOS / Linux 一键命令示例（点击展开）</summary>

```bash
python3 _agent_migration/restore_context.py \
  --restore-antigravity \
  --rewrite-paths \
  --blender "/Applications/Blender.app/Contents/MacOS/Blender" \
  --ffmpeg "/opt/homebrew/bin/ffmpeg"
```
</details>

这条命令会自动完成：
1. 将全部 **16 个对话目录**（`brain/<cid>/`）与 **16 个 Checkpointed 数据库**（`conversations/<cid>.db`）恢复到 `~/.gemini/antigravity/`；
2. 将这 16 个对话摘要无损合并进新电脑的 `conversation_summaries.db`，并自动把工作区路径绑定到新电脑的仓库目录；
3. 安装项目配置 `b8f1cf42-d4c5-4e16-b789-f04062d11bb5.json`、`GEMINI.md`、`CLAUDE.md` 以及全部 **14 个自定义技能**（`blender-director`、`blender-lookdev`、`cinematic-director`、`vehicle-artist` 等）；
4. 将 `pipeline/*.py`、`pipeline/mux_*.sh` 与 `docs/*.md` 中的 `PROJ`、`Blender`、`FFmpeg` 硬编码路径全部重写为新电脑路径。

（可随时运行 `python _agent_migration/restore_context.py --status` 自检恢复结果与本机工具路径。）

---

## 第 3 步：打开 Antigravity 继续推进 V6 终渲

1. 启动 **Antigravity**，打开克隆下来的 `blender-supercar` 文件夹。
2. **方式 A（直接原会话续跑）**：在历史对话列表中打开主控会话 **`Continue Optimization and Refinement`（ID：`1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8`）**，直接输入：
   > `已切换到新设备并完成路径同步，请按 @_agent_migration/PROJECT_MEMORY.md 的断点继续完成 V6 Iteration-2 MP4 封装、Round-2 校验与 1,281 帧全片终渲！`
3. **方式 B（全新会话秒级接管）**：直接新建任意对话，输入：
   > `请先阅读 @_agent_migration/PROJECT_MEMORY.md ，接管当前断点继续推进！`

### 附：如果想直接在终端手动跑完剩余两步
因为暂停前 `@anim` 已将 V6 Iteration-2 的全部 24 张剧照与 3 段 96 帧序列帧渲染落盘，你在终端直接执行以下三条命令即可出齐 V6 全套成片：

```bash
# 1. 立即封装 Iteration-2 的 3 段 4s 展示片 + 12s 合辑（约 15 秒）
bash pipeline/mux_v6_sv.sh --clips

# 2. 渲染 V6 全片 1,281 帧 1080p 序列（单进程多线程，约 35–55 分钟）
"<你的blender路径>" -b -t 12 -P pipeline/render_v6_sv.py -- --all

# 3. 封装 53.38 秒全片母版 MP4 + V5/V6 左右分屏对比大片
bash pipeline/mux_v6_sv.sh --full
bash pipeline/mux_v6_sv.sh --split
```
