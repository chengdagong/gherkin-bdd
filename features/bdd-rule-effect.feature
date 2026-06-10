# language: zh-CN
功能: BDD 规则生效
  安装插件必须真的把 BDD 规则带进 agent 会话：Claude Code 通过
  CLAUDE.md 导入自动加载规则，Codex 在 AGENTS.md 指令要求下读取规则，
  项目中的已安装副本会保持冻结，直到重新运行安装器。

  @agent
  场景: Claude Code 通过导入自动加载规则
    假如 已安装的 Claude Code 项目，它的规则副本包含一行 canary
    当 无工具权限的 headless Claude 会话被询问 canary
    那么 返回 canary 行

  @agent
  场景: Codex 读取指令指向的规则
    假如 已安装的 Codex 项目，它的规则副本包含一行 canary
    当 headless Codex 会话被要求从必读规则中报告 canary
    那么 返回 canary 行

  @agent
  场景: 源规则更新在重新安装前不可见
    假如 已安装的 Claude Code 项目，它的规则副本包含一行 canary
    而且 源规则中的 canary 已经改变
    当 无工具权限的 headless Claude 会话被询问 canary
    那么 返回原始 canary 行，而不是更新后的 canary 行

  @agent
  场景: 重新安装会带入更新后的规则
    假如 已安装的 Claude Code 项目，它的规则副本包含一行 canary
    而且 源规则中的 canary 已经改变
    而且 在项目中重新运行安装器
    当 无工具权限的 headless Claude 会话被询问 canary
    那么 返回更新后的 canary 行
