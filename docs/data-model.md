# MVP 数据模型

## `conclusions`

| 字段 | SQLite 建议类型 | 约束/说明 |
| --- | --- | --- |
| `id` | `INTEGER` | 主键，自增 |
| `title` | `TEXT` | 必填，去除首尾空白后不可为空 |
| `question` | `TEXT` | 必填，普通文本 |
| `conclusion` | `TEXT` | 必填，简短纯文本；建议 1–2 句、最多 280 字符 |
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

## `decision_analyses`

决策推演与 Conclusion 是可选的一对一关系：

| 字段 | SQLite 类型 | 约束/说明 |
| --- | --- | --- |
| `conclusion_id` | `INTEGER` | 主键及外键，删除 Conclusion 时级联删除 |
| `schema_version` | `INTEGER` | 当前固定为 `1` |
| `analysis_json` | `TEXT` | 经过 API schema 校验的结构化模型回答 |

JSON 顶层包含 `version` 和 `models`。每次模型运行保存稳定的 `modelId`、`modelVersion` 和非空 `answers`；写入时校验模型版本及问题键确实存在。同一分析中不允许重复模型。空分析不写入该表，API 统一返回 `{ "version": 1, "models": [] }`。

## `decision_models`

决策模型注册表是网页和 MCP 的共同数据源：

| 字段 | SQLite 类型 | 约束/说明 |
| --- | --- | --- |
| `id` | `TEXT` | 稳定 slug，主键，创建后不复用 |
| `version` | `INTEGER` | 当前固定为 `1`，为后续版本历史预留 |
| `name` | `TEXT` | 展示名称 |
| `short_name` | `TEXT` | 紧凑英文或符号标识 |
| `description` | `TEXT` | 模型用途说明 |
| `prompts_json` | `TEXT` | 有序问题定义，每项包含稳定 key、label 和 placeholder |
| `source_name` | `TEXT` | 可选来源名称 |
| `source_url` | `TEXT` | 可选公网 HTTPS 来源 |
| `is_builtin` | `INTEGER` | `1` 为内置模型，`0` 为 API/MCP 创建模型 |
| `created_at` | `TEXT` | UTC ISO 8601 |
| `updated_at` | `TEXT` | UTC ISO 8601；当前不可变版本与创建时间相同 |

应用初始化时以 `INSERT ... ON CONFLICT DO NOTHING` 注册七个内置模型，不覆盖数据库中已有定义。MVP 支持列表、详情和创建，不支持覆盖或删除；模型修订将在后续通过新增版本完成。

## Markdown 和图片

`conclusion` 不使用 Markdown，确保核心决定足够短、可直接搜索和复用。`reason`、`tradeoffs`、`conditions` 使用常见 GFM 子集。原始 HTML 不属于支持契约；前端渲染时必须进行 XSS 防护，并且只渲染公网 `https://` 图片 URL。不提供上传、本地托管或附件表。

## 搜索范围

MVP 关键词搜索只匹配：

- `title`
- `question`
- `conclusion`
- `reason`

匹配方式先使用 SQLite 的大小写不敏感子串查询。标签和分类使用独立筛选参数，不引入全文索引或向量检索。

## 删除语义

MVP 使用硬删除。删除 Conclusion 时级联删除 `conclusion_tags` 关联；不自动删除已经没有关联的标签，标签清理由后续独立功能处理。
