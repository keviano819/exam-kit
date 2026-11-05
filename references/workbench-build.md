# 固定模板与构建流程

## 不重新设计 UI

`assets/workbench/index.html` 是从用户认可的工作台抽取的固定模板。保留侧栏、四个视图、浅色面板、深色主按钮、进度和深度讲解布局。每门课只生成 `course.json`，不要每次重写 HTML 或调用其他设计 skill。只有用户明确要求修改 UI 或实际测试发现错误时才改模板。

模板支持任意合法课程/单元/题目 ID、任意单元数量；不依赖 ENGE、Week 1–6、u1 起点、u5 统计公式、原始 PDF 路径或作者电脑目录。

新构建的数据入口为 `window.EXAM_KIT_DATA`，由构建器与模板配套生成。旧课程文件保持原样；`exam-review-` 存储键与缓存前缀作为兼容标识保留，不能在重命名时批量替换。同一课程更新要维持原域名／文件位置和课程ID，不能仅凭相同skill名称保证记录自动迁移。

## 输入

读取 `examples/course.json` 的完整格式。它是原创演示样例，不是深度或题量的上限。读取 `references/learning-core.md`，依据真实材料生成所有内容，然后按下列契约组织 JSON。

- 根部：`schemaVersion: 1`、字符串 `version`、`course`、非空 `units`。
- `course`：稳定的 `id`、`title`、`scope`、`mode`；可选 `shortTitle`、`brand`、`mark`、`subtitle`、`exclusions`、`errorReasons`。
- `unit`：`id`、`title`、`summary`、`source`、非空 `objectives`、`terms`、`lesson`、非空 `questions`。可提供 `zhTitle`、`week`（任意短章标签）、`difficulty`，否则构建器补默认值。
- `terms`：由 `[原词, 中文学术名称, 含义]` 三列组成的数组；没有术语时可为空数组。
- `lesson`：`question`、`provenance`、`prerequisites`、`conceptMap`、`sections`、`workedExample`、`transfer`。
- 每个深度 section：稳定的 `id`、`heading`、`why`、`body`、`points`、`example`、`pitfalls`、`examCue`、`source`。`body` 中双换行表示段落，不写任意 HTML。
- `example` 包括 `title`、至少两步 `steps`、`conclusion`；`workedExample` 包括 `scenario`、至少两步 `steps`、`conclusion`。
- 选择题：`id`、`type: "choice"`、`prompt`、`options`（至少两个）、零起始整数 `answer`、`explanation`、`source`、`sectionIds`，可选 `level`。
- 主观题：`type: "written"`，提供非空 `rubric`，其余同上。不用关键词匹配冒充 AI 批改。
- `sectionIds` 必须指向当前单元已存在的正文节；“回到讲解”使用第一个引用定位。
- ID 使用字母/数字开头，后续可用字母、数字、下划线和连字符，最长80字符；禁止对象原型保留名。各类 ID 分别在全课唯一。

全部主题数据作为文本处理，构建器不执行 JS 数据文件。复杂公式、原图和图表尚无专门字段：基础 Unicode 公式可直接解释展示；若任务需要排版数学或媒体，先明确扩展模板、验证离线资源，再交付。不要把原始 LaTeX/Markdown 当成已经渲染成功的正文。

## 构建

脚本由 AI 在支持文件读写的环境执行，需要 Python 3.9+ 标准库，不需 pip、Node.js 或账号。用户仅阅读成品时不需 Python。

在 skill 根目录运行（也可用脚本绝对路径）：

```bash
python3 scripts/build_workbench.py --course course.json --mode local-html --output output/local-v1
python3 scripts/build_workbench.py --course course.json --mode vercel --output output/vercel-v1
```

`--output` 必须是尚不存在的新目录。脚本拒绝覆盖已有产物，避免旧记录或旧文件混进发布包。选择用户要的一种模式即可，演示和回归检查时才同时构建两种。

本地版生成 HTML、使用说明和交付记录；HTML内嵌全部数据和交互，移除 manifest/Service Worker 外部引用。Vercel版生成包含四个文件的 `vercel-deploy/`、根部为 `index.html` 的 ZIP、针对本次清单的完整教程和交付记录。深度正文合入 `data.js`，不需要独立的 `lesson-details.js`。缓存名包含模板与数据的内容摘要，内容变化会更新缓存名；存储键仅依赖稳定课程 ID，不随内容版本变化。

## 验证与边界

构建器拒绝空单元、重复 ID、错误答案索引、断开的正文引用和缺失深度结构。它检查结构，不判断内容是否正确、是否讲透或允许公开。AI仍需进行材料覆盖与内容审核。

包内自检：

```bash
python3 scripts/verify_package.py
```

它在临时目录构建两种产物并检查安全嵌入、缓存更新、ZIP清单与无原课程残留；若有 Node.js，再执行脚本语法和状态逻辑检查。自检不能替代真实浏览器的 file://、移动端、刷新和离线验证。

当前模板保留记录导出，没有导入、用户账号或云同步。智能补讲由用户把导出记录交回 AI 后进行，静态页面不会自己调用模型。生成文档应如实描述这些边界。
