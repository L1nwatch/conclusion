# 小步开发路线

每一项对应一个可独立测试和提交的功能。除非确有依赖，不把相邻项目合并为一个大提交。

1. 建立最小 FastAPI app 和健康检查
2. 建立 `sqlite3` 连接、数据库初始化和 Conclusion 表
3. 实现新增 Conclusion 数据库函数和 API
4. 实现列表与详情数据库函数和 API
5. 实现编辑数据库函数和 API
6. 实现删除数据库函数和 API
7. 实现标签表、关联表与写入
8. 实现关键词搜索、分类和标签筛选
9. 建立与 Fire 相同栈的 Vue/Vite 前端骨架
10. 实现列表页
11. 实现新增页
12. 实现详情页
13. 实现编辑和删除交互
14. 在 FengDock 中加入 `vendor/conclusion` submodule
15. 在 FengDock 中接入前端构建、根 venv 子进程、Caddy 路由和数据卷
16. 在 FengDock MCP 中加入 `list_conclusions`
17. 在 FengDock MCP 中加入 `search_conclusions`
18. 在 FengDock MCP 中加入 `get_conclusion`
19. 在 FengDock MCP 中加入 `create_conclusion`
20. 在 FengDock MCP 中加入 `update_conclusion`
21. 在 FengDock MCP 中加入 `list_decision_models`
22. 在 FengDock MCP 中加入 `get_decision_model`
23. 在 FengDock MCP 中加入 `create_decision_model`
24. 实现不可变模型版本历史，再加入 `update_decision_model`

## 每个提交的完成条件

- 只解决一个清晰问题
- 新行为有对应测试
- README 或接口文档在行为变化时同步更新
- 本地测试通过
- 不顺手加入与当前功能无关的重构
