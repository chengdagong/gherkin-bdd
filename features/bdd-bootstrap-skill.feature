# language: zh-CN
功能: 引导安装技能
  用户可以在 agent 会话内调用 bdd-bootstrap 技能，为当前项目完成设置。
  技能会识别会话正在运行的 coding agent，并用匹配的 coding agent 参数运行安装器。

  @agent
  场景: 从 Claude Code 调用
    假如 一个运行在 Claude Code 中的会话
    当 用户调用 bdd-bootstrap 技能但没有指定 coding agent
    那么 安装器为当前项目运行 Claude Code 安装

  @agent
  场景: 从 Codex 调用
    假如 一个运行在 Codex 中的会话
    当 用户调用 bdd-bootstrap 技能但没有指定 coding agent
    那么 安装器为当前项目运行 Codex 安装

  @agent
  场景: 用户显式指定 coding agent
    假如 一个运行在 Claude Code 中的会话
    当 用户调用 bdd-bootstrap 技能并指定 Codex
    那么 安装器为当前项目运行 Codex 安装

  # TODO: 目前还无法搭建该状态，因为两个已支持的 coding agent 都能可靠识别自身身份。
  # 当后续支持无法可靠自识别的 coding agent 时解除阻塞。
  @agent @todo
  场景: 无法判断 coding agent
    假如 一个无法识别 coding agent 的会话
    当 用户调用 bdd-bootstrap 技能但没有指定 coding agent
    那么 用户被询问安装到哪个 coding agent，而不是让系统猜测

  @agent
  场景: 本地没有安装器源仓库
    假如 当前项目中找不到 gherkin-bdd 源仓库
    当 用户调用 bdd-bootstrap 技能
    那么 用户被询问 gherkin-bdd clone 的位置，或收到重新 clone 的建议

  场景: 安装时附带 bootstrap 技能
    假如 正在为某个 coding agent 安装 gherkin-bdd 的项目
    当 技能已安装
    那么 bdd-bootstrap 技能与 gherkin-bdd 技能安装在同一级目录
