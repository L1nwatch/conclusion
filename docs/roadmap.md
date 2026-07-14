# 小步开发路线

每一项对应一个可独立测试和提交的功能。除非确有依赖，不把相邻项目合并为一个大提交。

1. 建立 FastAPI 应用和健康检查
2. 建立 SQLite/SQLAlchemy 数据模型和数据库初始化
3. 实现新增 Conclusion API
4. 实现列表与详情 API
5. 实现编辑 API
6. 实现删除 API
7. 实现标签数据模型与写入
8. 实现关键词搜索、分类和标签筛选
9. 实现列表页
10. 实现新增页
11. 实现详情页
12. 实现编辑和删除交互
13. 补齐 Docker 运行入口和持久化配置说明
14. 在 FengDock 中加入 `vendor/conclusion` submodule 并接入构建/路由
15. 在 FengDock 中逐个加入 `list_conclusions`、`search_conclusions`、`get_conclusion` MCP 工具

## 每个提交的完成条件

- 只解决一个清晰问题
- 新行为有对应测试
- README 或接口文档在行为变化时同步更新
- 本地测试通过
- 不顺手加入与当前功能无关的重构

