---
name: memory-distiller
description: 将 verbose 记忆文件浓缩为 token 高效版（headroom 原则）。当用户说"蒸馏记忆"、"压缩记忆"、"distill memory"或 save-memory 完成后自动触发。去重、去冗余、结构化。
---

# Memory Distiller — 记忆浓缩器

基于 headroom 的上下文压缩理念：**60-95% token 减少，信息无损**。

## 触发方式
- save-memory 完成后自动触发
- 用户说"蒸馏记忆"、"压缩记忆"、"mem-distill"
- 对话开始时检测到记忆文件变更

## 核心原则 (Headroom-inspired)

| 原则 | 做法 |
|------|------|
| **去重 (Dedup)** | 多条记忆重复信息只保留一次 |
| **压缩 (Compress)** | 叙述性段落 → 结构化短句 |
| **结构化 (Structure)** | 用 YAML/JSON 代替散落 prose |
| **分层 (Tier)** | 关键数据完整保留，说明文字移除 |
| **可逆 (Reversible)** | 原始记忆文件不删，蒸馏版为补充 |

## 执行流程

### Step 1: 扫描源文件
读取 `~/.config/opencode/memory/memory-*.md` 全部文件，以及 `github-pages-config.json`。

### Step 2: 提取关键数据
从每个文件提取：
- **用户信息**：身份、技能、偏好
- **项目信息**：名称、路径、URL、技术栈
- **配置信息**：SSH、API key 引用（不写实际密钥值）、路径约定
- **操作流程**：常用命令、工作流
- **更新日志**：合并去重的时间线

### Step 3: 去重合并
- 同一信息出现在多个文件中 → 只保留最新/最完整的版本
- 用户信息等静态数据只记录一次
- 更新日志合并为单一时间线

### Step 4: 生成蒸馏文件
写入 `~/.config/opencode/memory/memory-distilled.md`，格式如下：

```yaml
# 蒸馏记忆 v{N} | 生成: YYYY-MM-DD | 原始行数: N → 压缩: M | 压缩率: X%
```

```yaml
user:
  name: {github_username}
  email: {github_email}
  role: {身份}
  device:
    model: Honor 笔记本
    cpu: Intel Core Ultra 5 225H
    ram: 32GB LPDDR5x
    gpu: RTX 5060 Laptop 8GB

paths:
  ws: D:\项目session
  github: D:\项目session\github
  memory: ~/.config/opencode/memory/
  skills: ~/.config/opencode/skills/
  agents: ~/.config/opencode/agents/

projects:
  - name: {项目名}
    type: {类型}
    url: {URL or path}
    tech: [tech1, tech2]
    status: active|archived

github_repos:
  - name: {repo}
    url: {pages_url}
    deploy: push-auto|github-actions
    tech: [tech]

skills_installed:
  - name: {skill}
    desc: {一句话}

commands:
  - name: /cmd
    desc: {一句话}

workflows:
  update_site: |
    cd D:\项目session\github\{repo}
    git add -A; git commit -m "..." ; git push

timeline:
  - date: YYYY-MM-DD
    events: [event1, event2]
```

### Step 5: GitHub 专项蒸馏
同时生成 `~/.config/opencode/memory/github-distilled.md`：
- 仅 GitHub 相关：仓库、部署方式、URL、Git 命令
- 与 `github-pages-config.json` 互补（JSON 给程序读，md 给 LLM 读）

## 蒸馏规则

### 删除（安全丢弃）
- 教程/解释性段落（"就像给两台电脑拉了一根专属网线..."）
- 重复的列表示例
- 过时的状态信息（已被更新的取代）
- "你可以这样做"/"建议"类软性文字

### 保留（结构化存储）
- 用户名、邮箱、SSH 指纹
- 项目名 + URL + 路径 + 技术栈
- 命令和参数
- 关键决策记录
- 文件路径约定

### 压缩示例

**原始 (127 tokens):**
```
GitHub Pages 不能做什么（别把它当网盘）
| 能做 | 不能做 |
| 托管 HTML/CSS/JS 网页 | 存储大文件 |
| 支持 React/Vue 等项目 | 不能跑后端代码 |
| 免费 + HTTPS | 每个仓库不超过 1GB |
```

**蒸馏后 (30 tokens):**
```
limits:
  gh_pages: static_only | <100MB/file | <1GB/repo | no_backend
```

## 输出确认
完成后告知用户：
- 压缩率 (%)
- 原始行数 vs 蒸馏行数
- 蒸馏文件路径
