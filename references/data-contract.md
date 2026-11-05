# 复习系统数据契约

## 核心状态

`answers[questionId]` 是题目掌握状态的唯一事实来源。推荐结构：

```js
{
  answer: 1,
  correct: false,
  confidence: "不确定",
  reason: "概念混淆",
  grading: "automatic",
  updatedAt: "2026-11-05T00:00:00.000Z",
  history: []
}
```

综合题使用：

```js
{
  writtenAnswer: "用户回答",
  revealed: true,
  criteria: [0, 2],
  score: 2,
  correct: false,
  grading: "self"
}
```

## 推导规则

- `isAnswered(choice)`：`correct` 必须是 boolean，且答案索引在选项范围内。
- `isAnswered(written)`：必须有回答文本、整数 `score` 和已完成要点自评。
- `needsReview(record)`：`correct === false`，或 `confidence` 为 `不确定/不会`。
- `completedUnits`：单元中所有题目满足 `isAnswered` 后自动生成。
- `progressPercent`：单元完成度；另行计算题目作答度，不混用。

## 迁移原则

1. 缺少字段时使用默认值，不覆盖已有答案。
2. 题目 ID 变更视为新题；如果只是题干或选项修订，应保留 ID 并记录版本。
3. 删除题目不应删除其他题目的回答历史。
4. 读取异常时回退到安全的空状态，同时保留页面可用性提示。
