# 决策树

在 Conclusion 的 **Decision Trees** 中创建决策、搜索标题、编辑状态和背景描述，点击标题打开树。新建决策时根节点使用决策标题，之后可以单独编辑根节点文字。

- 拖动节点卡片会平移整条分支，包含折叠的后代节点。
- 拖动卡片上的 ⠿ 到目标节点中间，会把分支移到该节点下。放到目标上沿或下沿，会插入其前面或后面。节点的 ⋯ 菜单也可上下移动节点，菜单里的「节点属性」可切换父节点。
- 新增、移动、删除节点或节点换行改变高度时，会以根节点为锚点重新给各分支留出空间。母节点对齐首尾子节点的中点，只有一个子节点时两者水平对齐，多个子节点共用一条竖向分支线。「自动布局」可随时重排。
- 打开保存过的树时会沿用坐标。如果旧版的列布局中分支互相穿插，或 MCP 新增的节点尚无坐标，编辑器会先整理排布。
- 单击选中节点后，按 Tab 新建子节点，按 Enter 新建同级节点。新节点会立刻进入文字编辑。
- 双击节点或按 F2 可在卡片内直接输入。编辑时 Enter 完成、Shift+Enter 换行、Esc 恢复原文。类型和备注在 ⋯ 菜单的「节点属性」里编辑，条件表达式作为普通文本保存。
- 停止输入或操作 8 秒后，编辑器会批量保存树结构、同级顺序、坐标和折叠状态。持续编辑时，待保存的一批改动最长等待约 30 秒。通过应用内链接离开时，会先保存待提交的改动。「重新加载」会读取网页或 MCP 的最新保存结果。版本冲突时会保留当前页的修改，直到用户决定重新加载或离开页面。

## SQLite

应用启动时在现有的 Conclusion SQLite 文件中创建 `decisions` 表和更新时间索引。每条记录包含元信息、版本、根节点 ID 和以平面 JSON 数组保存的节点。节点的 ID 在同一决策内唯一，每组同级节点的顺序从 0 连续编号。树与决策在同一行保存，删除决策时整棵树随记录删除。

所有写入使用 SQLite 事务。元信息修改、树修改和删除都需要最后读到的版本。树的批量操作按顺序执行，任何操作失败时整批回滚。版本冲突返回当前版本。HTTP 返回 `409` 和 `currentVersion`，MCP 的错误文本包含 `currentVersion=<版本>`。

## HTTP 和 MCP

HTTP 使用现有的 Conclusion 路由，MCP 使用 FengDock 的 OAuth。读取需要 `fengdock:read`，写入需要 `fengdock:write`。

| HTTP | MCP | 用途 |
| --- | --- | --- |
| `GET /api/decisions` | `list_decisions` | 标题搜索、状态筛选和分页 |
| `POST /api/decisions` | `create_decision` | 创建决策和根节点，可传完整初始 `nodes` |
| `GET /api/decisions/{decision_id}` | `get_decision` | 返回元信息、`rootId` 和完整节点数组 |
| `PATCH /api/decisions/{decision_id}` | `update_decision` | 更新标题、描述或状态 |
| `PATCH /api/decisions/{decision_id}/tree` | `update_decision_tree` | 应用 `operations` 批次或替换整棵树的 `nodes` |
| `DELETE /api/decisions/{decision_id}` | `delete_decision` | 删除决策和整棵树 |

HTTP 使用 `expectedVersion`，删除时通过查询参数传入。MCP 使用 `expected_version`，并把元信息修改放在 `changes` 对象中。MCP 和 HTTP 的节点字段及结果都使用 camelCase。

初始或完整树的节点字段包括 `id`、`text`、`parentId` 和 `order`。根节点的 `parentId` 为 `null`。整树替换须保留现有根节点 ID，提交时去掉返回值中的 `decisionId`、`createdAt` 和 `updatedAt`。未设置的坐标由网页编辑器自动放置。

批次支持 `add`、`update`、`move` 和 `delete`。每个操作提供 `id`。新增节点需要 `parentId` 和 `text`，更新节点使用 `changes`，移动节点需要目标 `parentId`。新增和移动可指定从 0 开始的目标 `order`，默认追加到末尾，移动时的目标顺序以节点移出原位置后的序列为准。删除会移除节点和它的全部后代。

批次移动节点会保留其已保存的坐标。要调整坐标，可在同一批次更新 `positionX` 和 `positionY`，也可在网页执行自动布局。

下例可作为 `update_decision_tree` 的 MCP 参数。

```json
{
  "decision_id": 1,
  "expected_version": 2,
  "operations": [
    {"op": "add", "id": "check-again", "parentId": "draw", "text": "复查进度"},
    {"op": "add", "id": "next-step", "parentId": "check-again", "text": "记录下一步"},
    {"op": "update", "id": "check-again", "changes": {"type": "Action", "collapsed": true}}
  ]
}
```

[CELPIP / CEC 测试数据](../tests/fixtures/celpip-decision.json)可直接用作 `create_decision` 的参数，也可提交给 `POST /api/decisions`。
