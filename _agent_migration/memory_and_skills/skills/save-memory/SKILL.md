---
name: save-memory
description: 将当前对话的关键上下文自动写入记忆文件，增量追加，无需手动编辑。当用户说"保存记忆"或对话到达重要节点时调用。
---

# Save Memory - 自动记忆保存

## 触发方式
- 用户说"保存记忆"、"更新记忆"、"记下来"
- 或当前对话到达重要决策节点

## 执行流程

### Step 1: 定位 / 轮转记忆文件
在 `~/.config/opencode/memory/` 目录下查找编号最大的 `memory-*.md` 文件（记为 `memory-N.md`）：
- 若该文件 **< 130 行** → 追加写入此文件（当前文件）。
- 若该文件 **≥ 130 行** → 新建 `memory-{N+1}.md` 作为本次写入目标，并在新文件顶部写入基础头部：
  ```
  # 记忆 {N+1}

  ## 用户信息
  - 身份：湖北美术学院 视觉传达设计 大一新生
  - 对话日期：YYYY-MM-DD
  ```
  之后所有新内容写入新文件，避免单个文件无限膨胀、与 distilled 版本脱节。

### Step 2: 提取关键变更
扫描当前对话上下文，提取以下内容的增量变更：
- 项目方向/概念调整
- 新增的设计决策
- 新增的文件/素材路径
- 用户偏好更新

### Step 3: 增量写入
- 如果变更与已有内容重复，跳过（避免冗余）
- 如果是新内容，追加到文件的"更新日志"段落
- 每次写入前在文件末尾追加：
  ```
  ### 更新日志
  - YYYY-MM-DD: [变更摘要]
  ```

### Step 4: 确认
告知用户已保存的内容摘要。

### Step 5: 触发记忆蒸馏（自动）
保存完成后，**必须**立即加载 `memory-distiller` skill 并执行蒸馏流程：
1. 调用 `skill({ name: "memory-distiller" })` 加载蒸馏 skill
2. 按照蒸馏 skill 的流程，扫描所有记忆文件，生成 `memory-distilled.md` 和 `github-distilled.md`
3. 告知用户蒸馏压缩率

### Step 6: 自动同步到 GitHub（新增）
蒸馏完成后，**必须**立即加载 `config-sync` skill 并执行静默推送：
1. 调用 `skill({ name: "config-sync" })` 加载同步 skill
2. 执行静默 push（无需用户确认），提交信息格式：
   `auto: memory update YYYY-MM-DD HH:mm [machine: {hostname}]`
3. 告知用户同步状态（提交哈希 + 推送结果）
4. 如果 push 失败（网络问题等），静默跳过，下次 /sync push 时一起推送
