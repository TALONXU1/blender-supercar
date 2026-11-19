# Project: personal-env

## Tech Stack
- OS: Windows (PowerShell 5.1)
- Runtime: Node.js v24, Bun (preferred)
- Config: ~/.config/opencode/opencode.jsonc

## Conventions
- Use PowerShell cmdlets (Get-ChildItem, Set-Content, etc.)
- Prefer `; if ($?) { }` for sequential commands
- Use double quotes for interpolation, single quotes for verbatim
- AVOID `cd`; use `workdir` parameter instead

## AI Models Available (priority order)
1. deepseek:deepseek-chat (primary)
2. deepseek:deepseek-reasoner (reasoning tasks)
3. google:antigravity-gemini-3-flash (vision/image tasks)
4. google:antigravity-claude-sonnet-4-6 (coding tasks)
5. ollama:llama3 (offline fallback)

## Skills Loaded
- stock-market, valuation-analysis, macro-monitor
- humanizer, save-memory, memory-distiller
- github-manager, grill-me
- research, research-deep, research-report
- export-pdf, word-docx
- design-taste-frontend, brandkit
- industrial-brutalist-ui, minimalist-ui
- customize-opencode, full-output-enforcement

## Memory Files
- ~/.config/opencode/memory/*.md

## Commands
- /daily: daily-autorun macro monitor
- /save: save memory context
- /wealth: wealth-advisor analysis

## MCP Servers
- vision: python -m opencode_vision (localhost)


<!-- === VISION_SKILL_START === -->


# Claude Code Visual Inspection Configuration

## Front-end Page Check Workflow (mandatory)

When checking front-end page layout / UI, **do not** infer layout problems merely by reading code — you must actually look at the rendered screenshot:

1. Make sure the dev server is running, and get the page URL
2. Take a screenshot with `browser-harness`:
   - `new_tab(url)` to open the page
   - `wait_for_load()` to wait for loading
   - `time.sleep(2)` to wait for animations/rendering to finish
   - `capture_screenshot` for a full-page screenshot
   - Scroll to different positions and capture 2-3 more screenshots to cover all content
3. Analyze each screenshot for layout issues: alignment, spacing, overflow, whitespace, truncation, empty areas, etc.
   If you cannot understand the screenshot content directly, you must process it with an available image-understanding tool before continuing the analysis.
4. If the output is garbled, decode as GBK: `open(path, 'rb').read().decode('gbk')`
5. Summarize the analysis results from all screenshots and list the complete set of issues

<!-- === VISION_SKILL_END === -->
<!-- === CET4_TOOLS_START === -->

## 英语四级备考（本地安装 / 文件位置）

**原则：程序与数据一律放 D 盘，不占 C 盘。**

### cet-practice · 英语研习室（本地真题交互练习器）— 已安装 ✔
- 项目：https://github.com/o-Sakurajimamai-o/cet-practice （自定义许可，题库版权归原持有者，仅个人学习用）
- 版本：v1.5.0，Windows x64，**WithAudio 版**（含听力音频，`release.json` 的 `audio_edition` 为 `WithAudio`）
- 解压包：`D:\APPs\CET-Practice\CET-Practice-v1.5.0-Windows-x64-WithAudio.zip`（788 MB，SHA256 `56e28651…6e51cbd2` 已校验通过）
- 程序目录：`D:\APPs\CET-Practice\CET-Practice\`（约 1.1 GB，其中 `resources\` 839 MB 为听力音频）
- 音频分布：磁盘共 76 个 `.m4a`；四级 46 套**全部有音频**，六级 76 套中 49 套有音频 / 27 套无（上游就这样，不是下载缺失）
- 音频接口：`GET /api/audio/{paper_key}`，**必须用 GET，HEAD 一律 404**；实测四级 46/46、六级 49/49 均返回 200 且 >100 KB
- 启动：`D:\APPs\CET-Practice\CET-Practice\Start.bat` 或同目录 `CET-Practice.exe`
- 退出：同目录 `Stop.bat`（会输出 “Shutdown requested. Your saved answers are retained.”）
- 运行方式：本地 HTTP 服务 + WebView2，端口写在 `data\server.json`（默认 8765，含 token）
- 数据/备份：全部在 `data\` 内 —— `cet6.db`（个人库，约 128 MB，含 papers/questions/wrong_book/favorites/notes）、`instance.lock`、`server.json`；升级时保留此目录
- 题库规模：`data\cet6.db` 内 168 套试卷、8341 道题（四级+六级+考研合计）
- 限制：题库为第三方参考答案，可能有来源分歧；正确率不等于考试分

### 网络环境事实（本机）
- 系统代理 `127.0.0.1:17891`；**代理软件开着时直连 GitHub Release 可达 1.5 MB/s**，这是首选通道
- 代理未开时：`release-assets.githubusercontent.com` 直连失败，只能走镜像前缀 `https://ghproxy.net/https://github.com/...`
- 镜像对超大文件（>~700 MB）返回 500，且代理开着时反而不通，别混用
- 需要代理的下载：`DL_PROXY=http://127.0.0.1:17891` + Python 分段 Range 下载器（16 线程，787 MB 约 4 分钟）
- 下载后必须比对官方 `SHA256SUMS.txt`；曾出现“大小一致、哈希不符”的静默空洞文件
- `aria2c` 已从本机 winget 目录移除，PATH 里的残留路径无效，别再用

### 在线（免安装）备选
- 真题在线阅读（含听力）：https://catteacher0515.github.io/cet4-download/papers/
- 单词打字冲刺 wordrush（纯前端）：`https://cdn.jsdelivr.net/gh/Box611/wordrush@main/index.html`
- 词汇详解读本：https://word.vxiaozhi.com/2025/02/11/cet4-a/

<!-- === CET4_TOOLS_END === -->
