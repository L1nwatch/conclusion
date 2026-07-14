# MVP 数据模型

## `conclusions`

| 字段 | SQLite 建议类型 | 约束/说明 |
| --- | --- | --- |
| `id` | `INTEGER` | 主键，自增 |
| `title` | `TEXT` | 必填，去除首尾空白后不可为空 |
| `question` | `TEXT` | 必填，普通文本 |
| `conclusion` | `TEXT` | 必填，保存 GFM Markdown 原文 |
| `reason` | `TEXT` | 必填，保存 GFM Markdown 原文 |
| `tradeoffs` | `TEXT` | 保存 GFM Markdown 原文，默认空字符串 |
| `conditions` | `TEXT` | 适用和重新评估条件，保存 GFM Markdown 原文，默认空字符串 |
| `category` | `TEXT` | 必填；先允许自由输入，不做固定枚举 |
| `confidence` | `TEXT` | 必须为 `High`、`Medium`、`Low` 之一 |
| `created_at` | `TEXT` | UTC ISO 8601，创建时写入 |
| `updated_at` | `TEXT` | UTC ISO 8601，创建及每次修改时写入 |

API 输出可将时间字段序列化为 `createdAt` 和 `updatedAt`，数据库与 Python 内部保持 `snake_case`。

## 标签

标签采用简单的多对多结构，避免把逗号分隔字符串当作数据：

- `tags(id, name, normalized_name)`，其中 Unicode case-fold 后的 `normalized_name` 唯一
- `conclusion_tags(conclusion_id, tag_id, position)`，保留每条 Conclusion 的标签顺序

标签名称在写入时去除首尾空白、不能为空、最长 50 个字符；单条 Conclusion 最多 20 个标签。标签使用 Unicode case-fold 去重，保留首次出现的显示形式。

## Markdown 和图片

Markdown 使用常见 GFM 子集。原始 HTML 不属于支持契约；前端渲染时必须进行 XSS 防护，并且只渲染公网 `https://` 图片 URL。不提供上传、本地托管或附件表。

## 搜索范围

MVP 关键词搜索只匹配：

- `title`
- `question`
- `conclusion`
- `reason`

匹配方式先使用 SQLite 的大小写不敏感子串查询。标签和分类使用独立筛选参数，不引入全文索引或向量检索。

## 删除语义

MVP 使用硬删除。删除 Conclusion 时级联删除 `conclusion_tags` 关联；不自动删除已经没有关联的标签，标签清理由后续独立功能处理。
