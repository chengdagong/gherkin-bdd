# language: zh-CN
功能: 代码转 Gherkin
  没有按行为优先方式构建的项目，也可以变成 BDD 驱动。code-to-gherkin
  技能会阅读代码，找出尚未被任何 Gherkin 文件描述的用户可见行为，
  并把它记录成 Gherkin 场景。无论项目已经有一部分 Gherkin 文件，
  还是完全没有 Gherkin 文件，这个过程都一样。

  @agent
  场景: 没有 Gherkin 文件的项目会记录现有行为
    假如 一个有可运行代码但没有 Gherkin 文件的项目
    当 用户调用 code-to-gherkin 技能
    那么 描述代码用户可见行为的 Gherkin 文件被创建

  @agent
  场景: 只补写尚未覆盖的行为
    假如 一个部分行为已经由 Gherkin 文件描述的项目
    当 用户调用 code-to-gherkin 技能
    那么 未覆盖的行为获得场景
    而且 已覆盖的行为不会被描述两次

  @agent
  场景: 场景捕捉行为而非实现
    假如 一个有可运行代码但没有 Gherkin 文件的项目
    当 用户调用 code-to-gherkin 技能
    那么 新场景描述用户可以观察到的结果
    而且 内部代码名不会出现在 Gherkin 文件中

  @agent
  场景: 可疑行为会被询问而不是写成规格
    假如 一个代码中包含疑似缺陷的项目
    当 用户调用 code-to-gherkin 技能
    那么 用户会被询问该行为是否符合预期
    而且 没有场景把缺陷结果记录成预期行为

  # TODO: 目前还无法作为单次探测稳定搭建。验证补写场景同时获得可通过的
  # characterization tests，需要 agent 在一次 headless 调用里搭建测试框架，
  # 对单次运行、无重试的 live 策略来说太慢且不稳定（ADR-0003）。
  # 当 live harness 有预装测试 runner 的 staging recipe 时解除阻塞。
  @agent @todo
  场景: 补写的场景会获得 characterization tests
    假如 一个有可运行代码但没有 Gherkin 文件的项目
    当 用户调用 code-to-gherkin 技能并接受其计划
    那么 每个补写场景都会获得一个能在当前代码上通过的测试

  场景: 安装时附带 code-to-gherkin 技能
    假如 正在为某个 host 安装 gherkin-bdd 的项目
    当 技能已安装
    那么 code-to-gherkin 技能与 gherkin-bdd 技能安装在同一级目录
