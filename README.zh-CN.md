# Gherkin BDD

[English](README.md) | **中文**

一个供 Codex 与 Claude Code 共享的 Gherkin BDD 技能，外加一套同步机制，让每个安装了它的项目都指向同一条 BDD 规则：每个应用功能都由一个 `.feature` 文件来描述，且该 Gherkin 文件是应用行为的唯一事实来源。

包含的内容：

- `skills/gherkin-bdd/SKILL.md` —— Gherkin BDD 工作流（行为规格的起草、评审与实现）
- `BDD.md` —— BDD 规则文本，唯一事实来源
- `scripts/check_bdd_sync.py` —— 在各 host 的指令文件中维护对规则的引用
- `bin/bdd-bootstrap` —— 项目级安装器

没有 plugin 包装：两个 host 都原生发现项目级技能，安装器只是放置文件并注册一条 hook。

## 安装

安装进**当前目录**，一次一个 host：

```bash
bin/bdd-bootstrap claude   # Claude Code
bin/bdd-bootstrap codex    # Codex
```

唯一的位置参数（`claude` 或 `codex`）是必填的。源就是携带 `bin/bdd-bootstrap` 的这个仓库；安装目标是你的当前工作目录——先 `cd` 进要配置的项目，再运行命令。重复运行是幂等的。

安装的内容——仅此而已：

|  | Claude Code | Codex |
|---|---|---|
| 技能（`SKILL.md` + `BDD.md` + 同步脚本） | `.claude/skills/gherkin-bdd/` | `.agents/skills/gherkin-bdd/` |
| `SessionStart` hook | `.claude/settings.json` | `.codex/hooks.json` |
| 规则引用（受管区域） | `CLAUDE.md` | `AGENTS.md` |

安装是一份自包含的拷贝——**请把安装文件随项目一起提交**。这样协作者无需自己运行安装器，就能获得技能、会话 hook，以及 `CLAUDE.md` 中 import 所指向的文件。如果你把安装目录 gitignore 掉，`CLAUDE.md` 里的 `@`-import 会悬空（无害——只是规则不会自动载入），直到每个 clone 各自运行一次安装器。要获取本仓库的更新（包括 `BDD.md`），在项目里重新运行安装器即可。

本 CLI 只支持项目级安装，不会写入 `~/.claude`、`~/.codex`、`~/.agents` 或任何用户级位置。

## BDD 规则同步

`BDD.md` 是规则的唯一事实来源。同步机制不会把它的文本复制进你的项目，而是在 host 的规范指令文件（Claude Code 为 `CLAUDE.md`，Codex 为 `AGENTS.md`）中注入一个简短的**引用**，放在由 HTML 注释标记的受管区域内。引用因 host 而异：

- **Claude Code** 会展开 `@path` import，所以引用是 `@<BDD.md 的路径>`，`BDD.md` 会被自动载入上下文。
- **Codex** 不会展开 import，所以引用是一条要求 agent 必须阅读 `BDD.md` 的强制指令。

这一切由同一个脚本 `scripts/check_bdd_sync.py` 负责。安装器会运行它一次（喂给它与 hook 完全相同的 JSON payload），`SessionStart` hook 则在每次会话启动/恢复时运行**同一个**脚本。它会在规范文件缺失时创建该文件、刷新受管区域，引用已是最新时则什么也不做（幂等），且永不阻断会话。Claude Code 只从 `settings.json` 加载 hooks，不会从技能目录加载——这正是 hook 要放在 `.claude/settings.json` 里的原因。

## 使用技能

在 Claude Code 中运行 `/gherkin-bdd`（或者直接描述 Gherkin 相关工作——技能描述会自动触发）。Codex 会自动列出项目技能，并在任务匹配时加载。重新安装后请重启会话（Claude Code 也可运行 `/reload-plugins`）。

## 开发本仓库

本仓库把自己的技能安装进了自己（dogfooding），但安装产物（`.claude/`）被 gitignore。因此 fresh clone 之后请先运行一次 `bin/bdd-bootstrap claude`；在此之前，`CLAUDE.md` 末尾的 `@`-import 处于悬空状态，BDD 规则不会自动载入。

运行测试：

```bash
python3 -m unittest discover -s tests
```
