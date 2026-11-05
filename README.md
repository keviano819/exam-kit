# exam-kit

显示名称：**Exam Kit**；调用名称：`$exam-kit`。仓库名与安装目录建议同为 `exam-kit`。

把课程材料变成深入讲解、知识排查、错题闭环和可分享的复习工作台。

## 特点

- 深度课程正文：问题、前置知识、概念关系、机制、例子、误区、考试识别和迁移。
- 题库与反馈闭环：答案、把握程度、错因、重做、综合题自评和复习记录导出。
- 两种交付：本地自包含 HTML，或手机/分享用 Vercel 静态包。
- 内置学习核心：普通用户不需要另行安装 `ko-lesson`。
- 包内包含 Markdown/Obsidian 学习规则；无需下载其他 skill，也不会自动安装 `ko-lesson`。

## 安装

下载仓库完整内容，将目录命名为 `exam-kit`，交给支持技能安装的 AI 助手安装。不要只下载 `SKILL.md`。可以向助手提供以下请求，并填入本仓库实际地址：

```text
请检查并安装这个仓库中的 exam-kit skill：<本仓库的 GitHub 地址>。
SKILL.md 在仓库根目录，请保留 references、assets、scripts、examples、agents 和 licenses。
不需要另行安装 ko-lesson。安装后告诉我如何调用。
```

安装位置和技能发现方式以所用 AI 客户端为准。建议完整保留以下结构：

```text
SKILL.md
README.md
THIRD_PARTY_NOTICES.md
agents/
references/
assets/workbench/
scripts/
examples/
licenses/
```

## 使用

```text
使用 exam-kit，读取 ./materials 下的课程材料，生成一套期末复习工作台。
```

开始生成工作台时，skill 会让用户选择：

1. `local-html`：生成可直接打开的单文件 HTML。
2. `vercel`：生成 Vercel 发布文件夹、ZIP 和从注册到上传/更新的中文教程。

## 内容与模板分离

`assets/workbench/` 是稳定的产品界面模板，课程内容使用安全的 `course.json` 数据契约。不要为每门课复制一份 UI；应复用模板并替换课程数据。深度正文在构建时合入 `data.js`，Vercel 包默认不需要独立的 `lesson-details.js`。

用构建脚本生成：

```bash
python3 scripts/build_workbench.py \
  --course path/to/course.json \
  --mode local-html \
  --output output/local-v1
```

Vercel 包：

```bash
python3 scripts/build_workbench.py \
  --course path/to/course.json \
  --mode vercel \
  --output output/vercel-v1
```

构建由 AI 在具备 Python 3.9+ 的环境执行，仅使用标准库。`--output` 指向尚不存在的新目录，不是 HTML 文件名；模板路径已内置。用户打开最终网页不需要 Python。完整数据契约见 `references/workbench-build.md`。

包内原创示例和自检：

```bash
python3 scripts/build_workbench.py --course examples/course.json --mode local-html --output output/demo-local
python3 scripts/verify_package.py
```

自检不联网、不安装依赖、不修改真实学习记录；Node.js 可用时额外检查 JavaScript 语法和状态逻辑。自动化检查不能替代真实浏览器验收。

Vercel 上传由用户在浏览器中完成。skill 负责检查文件、生成教程和验收，不默认代替用户处理登录、验证码或最终发布。

## 使用边界

静态工作台支持选择题判分、主观题要点自评、错题回看和记录导出。它不直接调用AI，尚不提供记录导入、账号系统或跨设备同步；补讲与生成新题需要把记录交回AI。课程内容需要基于用户有权使用的材料审核，不能保证考试成绩或替代官方范围说明。

本仓库只分发通用模板、脚本和原创结构示例，不包含实际课程PDF、个人背景或真实作答记录。生成的课程输出不应提交到本仓库。

## 改名兼容

本包原名 `exam-review`，现在统一为 `exam-kit`。为兼容既有课程，浏览器存储键及离线缓存命名空间中的旧前缀保留，不作为用户调用名。不要为了改品牌机械替换这些字段，也不要更改现有课程ID、题目ID或本地HTML位置；这些变动可能影响旧记录的读取。既有网页不需要仅因skill改名重新部署。

## 许可与上游说明

本 skill 的上游借鉴和许可说明见 `THIRD_PARTY_NOTICES.md` 与 `licenses/ko-lesson-MIT.txt`。公开仓库发布前，请为本 skill 自己的内容选择并添加合适的许可证。
