# Conclusion

Conclusion 是一个个人决策知识库，用来保存“已经想清楚的最终结论”。它让自己和 AI 在再次遇到相似问题时直接复用已有决定、理由和适用条件，而不是重新分析一遍。

仓库当前处于 MVP 设计阶段。它将作为独立模块开发，达到可运行状态后再以 Git submodule 接入 FengDock。

## MVP 目标

- 记录最终决定及其原因
- 保留关键取舍和适用条件
- 支持关键词搜索和标签筛选
- 提供基础的新增、查看、编辑和删除能力
- 后续通过 FengDock 的只读 MCP 服务供 ChatGPT 查询

## MVP 数据

每条 Conclusion 包含：

- `id`：稳定的唯一标识
- `title`：标题
- `question`：原始问题
- `conclusion`：最终结论
- `reason`：主要原因
- `tradeoffs`：接受的缺点或放弃的方案
- `category`：分类，如投资、健康、生活、学习
- `tags`：标签集合
- `confidence`：`High`、`Medium` 或 `Low`
- `createdAt`：创建时间
- `updatedAt`：最后更新时间

具体持久化约定见 [docs/data-model.md](docs/data-model.md)。

## MVP 页面

1. Conclusion 列表页
2. 新增 Conclusion
3. Conclusion 详情页
4. 编辑和删除
5. 简单关键词搜索和标签筛选

## 技术方向

- Python 3.12、FastAPI、SQLAlchemy、SQLite
- 模块独立拥有数据库和 CRUD API
- 前端优先使用轻量静态页面，不在 MVP 引入复杂 UI 框架
- 预留 `/conclusions` 作为 FengDock 对外路径
- 预留 `8006` 作为 FengDock 容器内服务端口
- 预留 `/app/data/conclusion.db` 作为部署数据库路径

这些集成值在真正接入 FengDock 时再落到父仓库配置中，避免独立开发阶段与 FengDock 强耦合。

## 后续 MCP

MCP 由 FengDock 的统一、只读 MCP 服务对外提供：

- `list_conclusions`
- `search_conclusions`
- `get_conclusion`

Conclusion 模块提供稳定的只读 API；FengDock MCP 调用该 API，不直接依赖模块内部表结构。

## 暂时不做

- 向量数据库
- 自动 AI 总结
- 复杂关联图
- 富文本编辑器
- 复杂权限系统
- 过度设计 UI

## 开发方式

优先保证数据结构和基本 CRUD 可用。每次开发只完成一个可独立测试、独立提交的小功能，建议顺序见 [docs/roadmap.md](docs/roadmap.md)。

