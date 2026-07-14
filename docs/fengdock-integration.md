# FengDock 集成方式

## 参考实现

Conclusion 主要参考 FengDock 的 `vendor/fire`：

- submodule 内保留完整的后端领域代码和 Vue 前端源码
- FengDock Dockerfile 构建前端并复制后端代码
- FengDock 使用根 `/app/.venv/bin/uvicorn` 启动 submodule FastAPI app
- 所有进程运行在同一个 backend 容器中
- Caddy 去掉模块路径前缀后反向代理到容器内端口
- SQLite 数据目录挂载到 FengDock 的持久化 volume
- FengDock MCP 复用 submodule 的数据库读写函数

`TriggerToDo` 的独立 venv 是因为它有更多专属依赖，不是简单模块的默认做法。Conclusion 的 MVP 依赖已被 FengDock 根环境覆盖，因此不复制该模式。

## Conclusion 仓库负责

- `app/main.py`：FastAPI app、CRUD 路由、前端 fallback
- `app/db.py`：建表、写入、列表、搜索和详情查询
- `frontend/`：Vue 3 + TypeScript + Vite + Element Plus 页面
- 模块自己的单元测试
- 本地开发所需的最小 `pyproject.toml` 和前端包配置

数据库默认放在仓库内的 `data/conclusion.sqlite3`；`data/` 中的运行数据不提交 Git。

## FengDock 仓库负责

接入时分别以小提交完成：

1. 添加 `vendor/conclusion` submodule
2. 在根 Dockerfile 中增加 Conclusion 前端 builder，并复制 `app/` 和前端构建产物
3. 在 `scripts/run_servers.py` 中用根 venv 启动 Conclusion；建议内部端口 `8006`
4. 在 Caddy 中把 `/conclusion` 和 `/conclusion/*` 去前缀后代理到 `backend:8006`
5. 把 `backend_db` 挂载到 `/app/vendor/conclusion/data`
6. 在主页增加 Conclusion 入口
7. 在统一 MCP 中加载 `vendor/conclusion/app/db.py` 的读写函数

## 前端子路径

生产构建应与 Fire 一样同时设置两处路径：

- Vite base：`/conclusion/`
- API base：`/conclusion`

模块内部 API 仍使用 `/api/...`，Caddy 负责外部路径前缀。

## MCP 边界

MCP 工具只放在 FengDock，不在 Conclusion 中启动第二个 MCP server。Conclusion 提供可复用且有测试的数据库函数：

- 列出最近或全部 Conclusion（有上限）
- 按关键词、分类和标签搜索
- 按 ID 读取单条详情
- 新增 Conclusion
- 按 ID 更新 Conclusion
- 列出和按 ID 读取决策模型
- 新增自定义决策模型

Conclusion 写入时会校验 `decisionAnalysis` 引用的模型 ID、版本和问题键。FengDock MCP 不重复维护模型常量，直接调用 `list_decision_models`、`get_decision_model` 和 `create_decision_model` 数据库函数。模型更新必须等版本历史实现后再开放，MVP 不原地覆盖被历史 Conclusion 引用的模型。

FengDock 的读取工具以 SQLite `mode=ro` 打开数据库；新增和更新工具使用普通事务连接。所有工具继续复用现有 MCP OAuth、错误处理和 annotations，列表/搜索继续使用分页和结果上限。MVP 不通过 MCP 删除 Conclusion。
