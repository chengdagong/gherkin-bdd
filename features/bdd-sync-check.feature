# language: zh-CN
功能: BDD 规则同步
  BDD.md 是规则的唯一事实来源。插件会在 host 的规范指令文件中维护
  对它的引用：Claude Code 使用 CLAUDE.md，Codex 使用 AGENTS.md。
  安装时和每次会话启动时都会同步该引用，引用位于插件拥有的受管区域内。

  场景: Claude Code 获得导入引用
    假如 一个 Claude Code 项目
    当 为 claude host 运行 BDD 同步
    那么 CLAUDE.md 的受管区域包含对 BDD.md 的 @ 导入
    而且 没有创建 AGENTS.md

  场景: Codex 获得必读指令
    假如 一个 Codex 项目
    当 为 codex host 运行 BDD 同步
    那么 AGENTS.md 在受管区域中要求 agent 读取 BDD.md
    而且 没有创建 CLAUDE.md

  场景: 保留周边内容
    假如 一个 CLAUDE.md 中已有用户笔记的项目
    当 为 claude host 运行 BDD 同步
    那么 受管区域被加入且用户笔记保持不变

  场景: 刷新过期的受管区域
    假如 一个受管区域内容已过期的项目
    当 运行 BDD 同步
    那么 受管区域被当前引用重写
    而且 它只出现一次

  场景: 引用已经是最新
    假如 一个受管区域已经包含当前引用的项目
    当 运行 BDD 同步
    那么 指令文件保持不变

  场景: 安装会为选定 host 放置技能
    假如 正在为某个 host 安装 gherkin-bdd 的项目
    当 技能已安装
    那么 技能、BDD 规则和技能脚本被放入 host 的项目技能目录
    而且 项目中没有新增其他内容

  场景: 安装会运行同一个同步逻辑
    假如 正在为某个 host 安装 gherkin-bdd 的项目
    当 技能已安装
    那么 host 的规范指令文件引用 BDD.md
    而且 注册了一个稍后运行同一同步脚本的 session-start hook

  场景: 重新运行安装器会原地刷新
    假如 正在为某个 host 安装 gherkin-bdd 的项目
    当 技能已安装
    而且 技能再次安装
    那么 只存在一个 session-start hook 条目和一个受管区域
