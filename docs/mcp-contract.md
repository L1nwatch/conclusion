# FengDock MCP 契约

Conclusion 不启动独立 MCP server。FengDock 的统一 OAuth MCP 加载 `app/db.py`，网页 API 与 MCP 复用同一套 SQLite 函数和校验。

## 决策模型工具

### `list_decision_models`

- 副作用：无，使用只读连接
- 参数：无
- 返回：模型数量及定义列表，包括 ID、版本、说明、问题、来源和是否内置
- 用途：开始分析前查看当前可用的思考维度

### `get_decision_model`

- 副作用：无，使用只读连接
- 参数：`model_id`
- 返回：单个模型完整定义
- 用途：取得有序问题列表，逐项分析用户的问题

### `create_decision_model`

- 副作用：创建不可变模型，使用写连接
- 参数：`id`、`name`、`short_name`、`description`、`prompts`，以及可选的 `source_name`、`source_url`
- 返回：创建的 version 1 模型
- 约束：ID 和问题 key 稳定且唯一；来源 URL 仅允许 HTTPS；重复 ID 返回冲突

### `update_decision_model`（计划）

不得原地覆盖现有模型。实现版本历史后，该工具创建 `version + 1`，旧版本继续用于解释历史 Conclusion。

MVP 不提供 `delete_decision_model`。

## 推荐 AI 工作流

1. 调用 `list_decision_models`，根据问题复杂度选择少量相关模型。
2. 如果选择 `precedent-review`，先调用 `search_conclusions`；没有相关记录就明确写“暂无先例”，不要编造经验。
3. 调用 `get_decision_model` 读取每个模型的具体问题。
4. 使用用户提供的信息逐项推演；信息不足时明确标记假设，不虚构事实。
5. 把核心决定压缩成不超过 280 字符的 `conclusion`。
6. 把关键理由整理成 `reason`，把原始模型回答写入 `decisionAnalysis`。
7. 调用 `create_conclusion` 或带 `expectedUpdatedAt` 的 `update_conclusion`。

`decisionAnalysis.models[]` 写入格式：

```json
{
  "modelId": "time-horizons",
  "modelVersion": 1,
  "answers": {
    "tenHours": "短期感受……",
    "tenYears": "长期影响……"
  }
}
```

只提交实际回答的问题。数据库会拒绝不存在的模型、错误版本和不属于该模型的问题 key。

## MCP annotations

- `list_decision_models`、`get_decision_model`：`readOnlyHint: true`
- `create_decision_model`：`readOnlyHint: false`、`destructiveHint: false`、`idempotentHint: false`
- `create_conclusion`、`update_conclusion` 同样属于写操作
- 删除工具在 MVP 中不存在
