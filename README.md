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

Conclusion 采用 FengDock 现有 `vendor/fire` 的 bundled-app 模式，不另起一套部署架构：

- 后端使用 Python 3.12、FastAPI 和标准库 `sqlite3`
- 前端复用 Vue 3、TypeScript、Vite 和 Element Plus
- 仓库拥有领域代码、SQLite 读写函数、CRUD API 和前端源码
- 生产环境复用 FengDock 根虚拟环境、单个 backend 容器、进程管理和持久化卷
- 不为 Conclusion 创建独立生产 venv、独立容器或独立部署流水线
- FengDock 接入时使用 `/conclusion` 作为对外路径，并在构建时注入相同的前端 base/API base

父子仓库的具体职责见 [docs/fengdock-integration.md](docs/fengdock-integration.md)。

## 后续 MCP

MCP 由 FengDock 的统一、只读 MCP 服务对外提供：

- `list_conclusions`
- `search_conclusions`
- `get_conclusion`

Conclusion 的 `app/db.py` 提供可复用的只读查询函数。FengDock MCP 像读取 `vendor/fire/app/db.py` 一样加载这些函数，并以只读方式打开 Conclusion SQLite 数据库，避免重复实现查询逻辑和内部 HTTP 客户端。

## 暂时不做

- 向量数据库
- 自动 AI 总结
- 复杂关联图
- 富文本编辑器
- 复杂权限系统
- 过度设计 UI

## 开发方式

优先保证数据结构和基本 CRUD 可用。每次开发只完成一个可独立测试、独立提交的小功能，建议顺序见 [docs/roadmap.md](docs/roadmap.md)。
