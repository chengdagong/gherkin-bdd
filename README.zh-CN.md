# Gherkin BDD

[English](README.md) | **中文**

一个供 Codex 与 Claude Code 共享的 Gherkin BDD 技能，外加一套同步机制，让每个安装了它的项目都指向同一条 BDD 规则：每个应用功能都由一个 `.feature` 文件来描述，且该 Gherkin 文件是应用行为的唯一事实来源。

包含的内容：

- `skills/gherkin-bdd/SKILL.md` —— Gherkin BDD 工作流（行为规格的起草、评审与实现）
- `skills/bdd-bootstrap/SKILL.md` —— 一个技能：在会话内为当前所处的 host 运行安装器
- `skills/code-to-gherkin/SKILL.md` —— 一个技能：阅读代码，把尚未被任何 `.feature` 文件描述的行为补写成 Gherkin
- `BDD.md` —— BDD 规则文本，唯一事实来源
- `scripts/check_bdd_sync.py` —— 在各 host 的指令文件中维护对规则的引用
- `scripts/gherkin_to_html.py` —— 把项目里所有 `.feature` 文件原样渲染成一个易读的 HTML 页面
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
| 技能（`gherkin-bdd`、`bdd-bootstrap`） | `.claude/skills/<name>/` | `.agents/skills/<name>/` |
| `SessionStart` hook | `.claude/settings.json` | `.codex/hooks.json` |
| 规则引用（受管区域） | `CLAUDE.md` | `AGENTS.md` |

安装是一份自包含的拷贝——**请把安装文件随项目一起提交**。这样协作者无需自己运行安装器，就能获得技能、会话 hook，以及 `CLAUDE.md` 中 import 所指向的文件。如果你把安装目录 gitignore 掉，`CLAUDE.md` 里的 `@`-import 会悬空（无害——只是规则不会自动载入），直到每个 clone 各自运行一次安装器。要获取本仓库的更新（包括 `BDD.md`），在项目里重新运行安装器即可。

本 CLI 只支持项目级安装，不会写入 `~/.claude`、`~/.codex`、`~/.agents` 或任何用户级位置。

## BDD 规则同步

`BDD.md` 是规则的唯一事实来源。同步机制不会把它的文本复制进你的项目，而是在 host 的规范指令文件（Claude Code 为 `CLAUDE.md`，Codex 为 `AGENTS.md`）中注入一个简短的**引用**，放在由 HTML 注释标记的受管区域内。引用因 host 而异：

- **Claude Code** 会展开 `@path` import，所以引用是 `@<BDD.md 的路径>`，`BDD.md` 会被自动载入上下文。
- **Codex** 不会展开 import，所以引用是一条要求 agent 必须阅读 `BDD.md` 的强制指令。

这一切由同一个脚本 `scripts/check_bdd_sync.py` 负责。安装器会运行它一次（喂给它与 hook 完全相同的 JSON payload），`SessionStart` hook 则在每次会话启动/恢复时运行**同一个**脚本。它会在规范文件缺失时创建该文件、刷新受管区域，引用已是最新时则什么也不做（幂等），且永不阻断会话。Claude Code 只从 `settings.json` 加载 hooks，不会从技能目录加载——这正是 hook 要放在 `.claude/settings.json` 里的原因。

## Gherkin 转 HTML

技能附带一个转换器，把项目里所有 `.feature` 文件**原样**（不概括、不省略）渲染成一个易读、可搜索的 HTML 页面，任何人都能直接读懂应用的行为，无需逐个打开文件：

```bash
python3 .claude/skills/gherkin-bdd/scripts/gherkin_to_html.py   # Codex 则为 .agents/skills/...
```

它默认生成 `docs/gherkin.html`，如果没有 `docs/` 目录会自动创建；也可以用 `--out` 改路径。输出是一个自包含的 Gherkin Reader 单文件页面，带 Gherkin 文件 tab、scenario 数量、标签徽章、scenario 折叠、Given/When/Then 阶段间距、表格美化、搜索过滤、中英文 UI 与展示层 Gherkin 关键字切换和三种本地主题。它当前支持英文 Gherkin 文件，也支持声明 `# language: zh-CN` 的简体中文 Gherkin 文件；其他本地化 Gherkin 语言不在当前支持范围内。展示语言可以本地化关键字，但不会改写源文件。离线可用，无需服务器，也不引用任何外部资源。依赖目录和隐藏目录会被跳过；无法按 Gherkin 解析的文件仍会列出，以纯文本加解析警告的方式显示。在会话里直接让 agent「把 gherkin 转成 HTML」即可，技能知道怎么做。

## 使用技能

在 Claude Code 中运行 `/gherkin-bdd`（或者直接描述 Gherkin 相关工作——技能描述会自动触发）。Codex 会自动列出项目技能，并在任务匹配时加载。重新安装后请重启会话（Claude Code 也可运行 `/reload-plugins`）。

`/bdd-bootstrap` 在会话内重新运行当前项目的安装器：它会识别自己运行在 Claude Code 还是 Codex 中，并传入对应的 host 参数。也可以显式指定 host（如 `/bdd-bootstrap codex`）来为另一个 host 安装。

`/code-to-gherkin` 让既有代码库变成 BDD 驱动：阅读代码，找出尚未被任何 `.feature` 文件描述的用户可见行为，把它**记录**成 Gherkin 场景——只记录代码今天实际做什么，绝不发明。可疑的行为会变成抛给你的问题，而不是被悄悄写成规格；补写的场景会配上「刻画测试」（characterization test），必须立即在当前代码上通过。存量覆盖是部分还是为零都适用，可安全重复运行。把非 BDD 项目转成 BDD 项目就是两步组合：先 `/bdd-bootstrap`，再 `/code-to-gherkin`。

## 开发本仓库

本仓库把自己的技能安装进了自己（dogfooding），但安装产物（`.claude/`）被 gitignore。因此 fresh clone 之后请先运行一次 `bin/bdd-bootstrap claude`；在此之前，`CLAUDE.md` 末尾的 `@`-import 处于悬空状态，BDD 规则不会自动载入。

`features/` 下的 `.feature` 文件就是可执行的测试套件（pytest-bdd）。安装并运行：

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

打了 `@agent` 标签的场景由真实 agent 会话驱动测试（实际调用 `claude` / `codex` CLI）；默认运行中被排除，按需在普通终端用 `pytest -m "agent and not todo"` 执行。
