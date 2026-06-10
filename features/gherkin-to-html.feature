# language: zh-CN
功能: Gherkin 转 HTML
  使用 gherkin-bdd 的项目成员可以在不逐个打开 Gherkin 文件的情况下，
  阅读应用做了什么。技能附带的脚本会把项目中的每个 Gherkin 文件按原样渲染，
  不概括、不省略，生成一个易读、可搜索的 HTML 页面。

  场景: 项目中的每个 Gherkin 文件都出现在同一页面
    假如 一个在多个目录中都有 Gherkin 文件的项目
    当 用户将 gherkin 渲染为 HTML
    那么 单个 HTML 页面列出每个 Gherkin 文件及其来源文件
    而且 页面提供到每个 Gherkin 文件的导航

  场景: 场景读起来像规格
    假如 一个 Gherkin 文件包含标签、背景、场景大纲和步骤数据的项目
    当 用户将 gherkin 渲染为 HTML
    那么 页面显示功能名称和叙述
    而且 每个场景及其步骤按顺序出现
    而且 标签、背景步骤、examples 表格、步骤表格和 doc string 都保留在它们描述的对象旁边

  场景: 页面不需要服务器或网络
    假如 一个包含 Gherkin 文件的项目
    当 用户将 gherkin 渲染为 HTML
    那么 页面是单个自包含文件
    而且 页面默认写入 docs/gherkin.html
    而且 中文界面会本地化 Gherkin 关键字
    而且 页面不引用任何外部资源

  场景: 依赖目录和隐藏目录会被排除
    假如 一个依赖目录和隐藏目录中也包含 Gherkin 文件的项目
    当 用户将 gherkin 渲染为 HTML
    那么 只列出项目自己的 Gherkin 文件

  场景: 没有 Gherkin 文件的项目会得到诚实的空页面
    假如 一个没有 Gherkin 文件的项目
    当 用户将 gherkin 渲染为 HTML
    那么 页面说明还没有 Gherkin 文件

  场景: 无法解析的 Gherkin 文件仍会显示
    假如 一个包含无法解析文本的 Gherkin 文件的项目
    当 用户将 gherkin 渲染为 HTML
    那么 页面列出该文件、原始文本和解析警告

  场景: 安装时附带 gherkin-to-html 脚本
    假如 正在为某个 host 安装 gherkin-bdd 的项目
    当 技能已安装
    那么 gherkin-to-html 脚本被放入技能的 scripts 目录
