# FengDock MCP 契约

Conclusion 不启动独立 MCP server。FengDock 的统一 OAuth MCP 加载 `app/db.py`，网页 API 与 MCP 复用同一套 SQLite 函数和校验。

## 决策模型工具

### `list_decision_models`

- 副作用：无，使用只读连接
- 参数：无
- 返回：按固定顺序排列的全部模型；每个模型只有 `name` 和 `explanation` 两个业务字段，技术 ID 作为 map key
- 用途：用户要求“使用思考模型”时，必须逐个应用返回的全部模型，每个模型简析几句话

### `get_decision_model`

- 副作用：无，使用只读连接
- 参数：`model_id`
- 返回：单个模型的 `name` 和 `explanation`
- 用途：单独查看或解释某个模型；完整分析不需要逐个调用，`list_decision_models` 已返回全部解释

### `create_decision_model`

- 副作用：创建不可变模型，使用写连接
- 参数：技术 ID `model_id`，以及两个业务字段 `name`、`explanation`
- 返回：创建的 version 1 模型
- 约束：ID 稳定且唯一；解释保持简短，最多几句话和一个小例子；重复 ID 返回冲突

### `update_decision_model`（计划）

不得原地覆盖现有模型。实现版本历史后，该工具创建 `version + 1`，旧版本继续用于解释历史 Conclusion。

MVP 不提供 `delete_decision_model`。

## 推荐 AI 工作流

1. 调用一次 `list_decision_models`，按返回顺序使用全部模型，不自行筛选或跳过。
2. 到“经验之谈”时调用 `search_conclusions`；没有相关记录就明确写“暂无先例”，不要编造经验。
3. 每个模型只输出一小段具体分析；信息不足时明确标记假设，不虚构事实。
4. 七个模型全部分析完后，再把核心决定压缩成不超过 280 字符的 `conclusion`。
5. 把关键理由整理成 `reason`，每个模型的简析写入对应的 `decisionAnalysis.models[].answers.analysis`。
6. 只有用户明确要求保存时，才调用 `create_conclusion` 或带 `expectedUpdatedAt` 的 `update_conclusion`。

`decisionAnalysis.models[]` 写入格式：

```json
{
  "modelId": "time-horizons",
  "modelVersion": 1,
  "answers": {
    "analysis": "10 小时后可能仍有情绪波动；10 天后影响减弱；10 个月和 10 年后真正重要的是……"
  }
}
```

每个已分析模型只提交一个 `analysis`。数据库会拒绝不存在的模型、错误版本和未知 key；旧记录的历史问题 key 仍兼容。

## MCP annotations

- `list_decision_models`、`get_decision_model`：`readOnlyHint: true`
- `create_decision_model`：`readOnlyHint: false`、`destructiveHint: false`、`idempotentHint: false`
- `create_conclusion`、`update_conclusion` 同样属于写操作
- 删除工具在 MVP 中不存在
