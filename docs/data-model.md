# MVP 数据模型

## `conclusions`

| 字段 | SQLite 建议类型 | 约束/说明 |
| --- | --- | --- |
| `id` | `INTEGER` | 主键，自增 |
| `title` | `TEXT` | 必填，去除首尾空白后不可为空 |
| `question` | `TEXT` | 必填 |
| `conclusion` | `TEXT` | 必填 |
| `reason` | `TEXT` | 必填 |
| `tradeoffs` | `TEXT` | MVP 使用普通文本，默认空字符串 |
| `category` | `TEXT` | 必填；先允许自由输入，不做固定枚举 |
| `confidence` | `TEXT` | 必须为 `High`、`Medium`、`Low` 之一 |
| `created_at` | `DATETIME` | UTC，创建时写入 |
| `updated_at` | `DATETIME` | UTC，创建及每次修改时写入 |

API 输出可将时间字段序列化为 `createdAt` 和 `updatedAt`，数据库与 Python 内部保持 `snake_case`。

## 标签

标签采用简单的多对多结构，避免把逗号分隔字符串当作数据：

- `tags(id, name)`，其中规范化后的 `name` 唯一
- `conclusion_tags(conclusion_id, tag_id)`，联合主键

标签名称在写入时去除首尾空白；是否区分大小写在实现标签功能的提交中通过测试固定下来。

## 搜索范围

MVP 关键词搜索只匹配：

- `title`
- `question`
- `conclusion`
- `reason`

匹配方式先使用 SQLite 的大小写不敏感子串查询。标签和分类使用独立筛选参数，不引入全文索引或向量检索。

## 删除语义

MVP 使用硬删除。删除 Conclusion 时级联删除 `conclusion_tags` 关联；不自动删除已经没有关联的标签，标签清理由后续独立功能处理。

