# Conclusion Development & Deployment Cookbook

本文档用于后续开发、测试、提交、接入 FengDock、部署和排障。架构原则见 [docs/fengdock-integration.md](docs/fengdock-integration.md)，功能拆分见 [docs/roadmap.md](docs/roadmap.md)。

## 基本原则

- Conclusion 参考 FengDock 的 `vendor/fire`，是 bundled app，不是独立部署服务。
- submodule 负责领域代码、SQLite 读写、CRUD API、Vue 前端和模块测试。
- FengDock 负责生产构建、根虚拟环境、进程启动、Caddy、持久化卷、首页入口和统一 MCP。
- 每次只完成一个可独立测试、独立提交的小功能。
- 先推送 Conclusion，再更新 FengDock 的 submodule 指针和集成代码。
- 不提交 SQLite 数据库、`.env`、密钥、缓存、虚拟环境、`node_modules` 或构建产物。

## 目录约定

接入 FengDock 后的标准位置：

```text
/Users/fenglin/Desktop/code/FengDock/
├── app/                         # FengDock API 和统一 MCP
├── deploy/Caddyfile
├── scripts/run_servers.py
└── vendor/conclusion/           # 本仓库 submodule
    ├── app/
    │   ├── main.py
    │   └── db.py
    ├── frontend/
    ├── data/                    # 运行数据，不提交
    ├── tests/
    ├── pyproject.toml
    └── uv.lock
```

在尚未接入 FengDock 时，也可以把 Conclusion 克隆到任意独立目录开发。

## 首次本地初始化

Python 使用 `uv`。本地可以拥有 Conclusion 自己的 `.venv`，但生产环境复用 FengDock 根 `/app/.venv`，不复制 submodule venv。

在 `pyproject.toml` 和 `uv.lock` 建立后运行：

```bash
cd /path/to/conclusion
uv sync --frozen
uv run python --version
```

前端骨架建立后运行：

```bash
cd /path/to/conclusion/frontend
npm ci
```

新增依赖时：

```bash
cd /path/to/conclusion
uv add <python-package>

cd frontend
npm install <frontend-package>
```

Python 依赖必须已能被 FengDock 根环境提供；如果新增生产依赖，还要在独立的 FengDock 提交中同步根 `pyproject.toml` 和 `uv.lock`。不要因为一个简单依赖就为 Conclusion 建生产 venv。

## 本地开发

后端建立后，在一个终端启动：

```bash
cd /path/to/conclusion
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8006
```

前端建立后，在另一个终端启动：

```bash
cd /path/to/conclusion/frontend
VITE_API_BASE=http://127.0.0.1:8006 npm run dev
```

本地数据库默认使用：

```text
data/conclusion.sqlite3
```

后端必须允许用环境变量覆盖数据库路径，建议变量名：

```text
CONCLUSION_DATABASE_PATH
```

不要使用生产数据库做日常开发和自动化测试。测试应使用临时目录中的独立 SQLite 文件。

## 数据库变更

MVP 使用标准库 `sqlite3`，建表和小型兼容迁移集中在 `app/db.py`，参考 `vendor/fire/app/db.py`。

每次 schema 变更必须：

1. 保持旧数据库可启动并自动升级。
2. 添加从旧 schema 升级的测试。
3. 添加全新数据库初始化测试。
4. 在部署前备份生产数据库。
5. 不在同一提交中混入无关 UI 功能。

生产备份应在部署主机的 FengDock 目录执行，并使用 Python 标准库的 SQLite online backup API（当前 backend 镜像不保证安装 `sqlite3` CLI）：

```bash
cd <FENGDOCK_DEPLOY_PATH>
BACKUP="conclusion-before-$(date +%Y%m%d-%H%M%S).sqlite3"
docker compose exec -e BACKUP="$BACKUP" backend python -c \
  'import os, sqlite3; p="/app/vendor/conclusion/data/"; s=sqlite3.connect(p+"conclusion.sqlite3"); d=sqlite3.connect(p+os.environ["BACKUP"]); s.backup(d); d.close(); s.close()'
```

备份文件属于运行数据，不提交 Git。

## 测试与完成条件

后端功能完成后运行：

```bash
cd /path/to/conclusion
uv run python -m pytest
uv run python -m compileall app
```

前端建立后运行：

```bash
cd /path/to/conclusion/frontend
npm test
npm run build
```

提交前统一检查：

```bash
cd /path/to/conclusion
git diff --check
git status --short
git diff
```

行为变化必须有聚焦测试。UI 变化还要手动验证本次流程和至少一个相邻流程。

## README 截图

参考 CELPIP 的可复现截图方式，但复用 FengDock 已有的 Playwright/Chromium 栈。第一个 UI 页面完成时，应同时加入：

- `scripts/seed_demo_data.py`：只生成固定的假 Conclusion 数据。
- `scripts/capture_screenshots.py`：访问本地运行页面并写入 `screenshots/*.png`。
- README 中对应的 Markdown 图片引用。
- 验证截图不包含生产数据的测试或明确检查。

目标截图和命名见 [screenshots/README.md](screenshots/README.md)。脚本建立后，标准调用形式应保持为：

```bash
uv run playwright install chromium
uv run python scripts/capture_screenshots.py \
  --base-url http://127.0.0.1:8006 \
  --output-dir screenshots
```

截图固定为 `1440x900` viewport，并等待页面和 API 数据完成加载后再捕获。脚本还会使用 `390x844` viewport 检查新增页面是否出现横向溢出。不要手工从生产站点截图，也不要把真实投资、健康、购物或生活决策写入 demo seed。

## 小步开发和提交

每个任务使用独立分支：

```bash
cd /path/to/conclusion
git switch main
git pull --ff-only origin main
git switch -c codex/<small-feature>
```

只提交当前功能涉及的文件：

```bash
git add <changed-files>
git commit -m "<focused message>"
git push -u origin codex/<small-feature>
```

合入 `main` 前再次运行相关测试。不要把数据库模型、完整 CRUD、全部页面和 MCP 一次性塞进一个提交。

## 首次接入 FengDock

只有当 Conclusion 后端、前端和模块测试已经能独立运行时，才开始父仓库集成。

### 1. 公开代码，隔离私人数据

`L1nwatch/conclusion` 是 public，和 FengDock 的其他 submodule 一样可以被 CI 与 VPS 匿名拉取，不需要额外 PAT 或 `SUBMODULE_TOKEN`。

Public 仓库只包含代码、文档、公开安全截图和固定 fake seed。真实 Conclusion 数据只保存在 SQLite 和 FengDock 生产 volume 中；`.env`、`*.db`、`*.sqlite*`、备份、缓存和构建产物均由 `.gitignore` 排除。提交前可无认证验证：

```bash
git ls-remote https://github.com/L1nwatch/conclusion.git refs/heads/main
```

### 2. 添加 submodule

```bash
cd /Users/fenglin/Desktop/code/FengDock
git switch -c codex/add-conclusion-submodule
git submodule add -b main https://github.com/L1nwatch/conclusion.git vendor/conclusion
git submodule status
git diff --submodule
```

提交 `.gitmodules` 和 gitlink：

```bash
git add .gitmodules vendor/conclusion
git commit -m "Add Conclusion submodule"
```

新环境初始化：

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

### 3. 分步接入 FengDock

下列项目应拆分为可验证的小提交：

1. Dockerfile 增加 Conclusion 前端 builder，并复制 `app/` 和构建产物。
2. `scripts/run_servers.py` 使用 `/app/.venv/bin/uvicorn` 在端口 `8006` 启动 Conclusion。
3. `docker-compose.yml` 把持久化 volume 挂载到 `/app/vendor/conclusion/data`。
4. Caddy 将 `/conclusion` 去前缀后代理到 `backend:8006`。
5. FengDock 首页增加入口。
6. 增加父仓库集成测试。
7. 最后逐个接入三个读取 MCP 工具和两个写入 MCP 工具。

生产前端构建必须同时设置 Vite base 和 API base：

```bash
VITE_API_BASE=/conclusion npm run build -- --base=/conclusion/
```

Caddy 路由形态：

```caddyfile
@conclusion_app path /conclusion /conclusion/*
handle @conclusion_app {
    uri strip_prefix /conclusion
    reverse_proxy backend:8006
}
```

## MCP 接入

MCP 只改 FengDock 的 `app/mcp_server.py`，Conclusion 不启动自己的 MCP server。

实现要求：

- 参考 FengDock 现有 Fire loader，加载 `vendor/conclusion/app/db.py`，不在父仓库复制 SQL。
- `list_conclusions`、`search_conclusions`、`get_conclusion` 使用 SQLite URI `mode=ro`。
- `create_conclusion`、`update_conclusion` 使用普通连接和显式事务，并返回写入后的完整记录。
- 读取与写入使用不同的 MCP annotations；不得把写工具错误标记为 `readOnlyHint=True`。
- 五个工具分别提交和测试。
- 列表/搜索必须有明确上限；详情不存在时返回稳定、可理解的错误。
- 写入失败必须完整回滚，并转换为稳定的 `ToolError`，不能留下部分标签关联。
- MCP 写入暂不包含删除；删除仍由 UI 明确确认。

## 两个仓库的发布顺序

先发布 Conclusion：

```bash
cd /Users/fenglin/Desktop/code/FengDock/vendor/conclusion
git status -sb
git switch main
git pull --ff-only origin main
git merge --ff-only codex/<small-feature>
git push origin main
git ls-remote origin refs/heads/main
git status -sb
```

再更新 FengDock：

```bash
cd /Users/fenglin/Desktop/code/FengDock
git status -sb
git diff --submodule
git add vendor/conclusion <related-fengdock-files>
git commit -m "Update Conclusion integration"
git push origin main
git ls-files -s vendor/conclusion
git ls-remote origin refs/heads/main
git status -sb
```

两个仓库都干净、远端 commit 已核对后，才能报告发布完成。

## CI 和部署验证

FengDock push 后检查精确 commit 的 Actions：

```bash
cd /Users/fenglin/Desktop/code/FengDock
git rev-parse HEAD
gh run list --repo L1nwatch/FengDock --commit "$(git rev-parse HEAD)" --limit 5
gh run watch --repo L1nwatch/FengDock
```

部署成功后执行冒烟检查：

```bash
curl -fsS https://watch0.top/conclusion/api/health
curl -fsSI https://watch0.top/conclusion/
```

服务器排障：

```bash
cd <FENGDOCK_DEPLOY_PATH>
git submodule status
docker compose ps
docker compose logs --tail=200 backend caddy
```

重点检查：

- submodule 是否是父仓库记录的 commit。
- Conclusion 子进程是否在 `8006` 正常启动。
- `/app/vendor/conclusion/data` 是否可写且持久化。
- 前端资源 URL 是否带 `/conclusion/` base。
- API 请求是否走 `/conclusion/api/...`。
- MCP 读取是否以只读方式打开正确数据库，新增/更新是否写入同一个持久化数据库。

## 回滚

优先使用 Git revert，不使用破坏性的 reset：

1. 回滚 FengDock 中引入问题的集成提交或 submodule 指针提交。
2. 等待 FengDock CI 重新构建和部署旧版本。
3. 如果涉及 schema 变更，先保留当前数据库，再按迁移兼容性决定是否恢复部署前备份。
4. 不要在未备份时删除、覆盖或手工修改生产 SQLite 文件。

仅回滚 Conclusion 远端 `main` 不会自动改变 FengDock 已记录的 gitlink；父仓库必须提交新的 submodule 指针并重新部署。

## 常见问题

### CI 在 `git submodule update` 报 404 或权限错误

private submodule token 没有 `L1nwatch/conclusion` 的 Contents read 权限，或 Actions 没有使用该 token。先修复只读凭据，不要反复重跑相同 workflow。

### 页面打开但静态资源 404

检查 Vite 是否使用 `--base=/conclusion/` 构建，以及 Caddy 是否先匹配 `/conclusion/*` 再去前缀代理。

### 页面正常但 API 404

检查 `VITE_API_BASE=/conclusion`、请求是否为 `/conclusion/api/...`，以及 Caddy 是否把前缀去掉后转发给 Conclusion。

### 本地正常但生产数据库为空

检查生产数据库路径和 compose volume 挂载。不要让代码默认写入容器的临时文件系统。

### MCP 读到了错误或旧数据

确认 FengDock MCP 配置的数据库路径与 Conclusion 实际写入路径相同，并确认读取使用 SQLite `mode=ro`。

### MCP 可以读取但不能新增或更新

确认写工具没有复用 `mode=ro` 连接，数据库 volume 对 backend 用户可写，并检查 SQLite busy/locked 错误。Conclusion 连接应启用 WAL 和 busy timeout，支持 API 与 MCP 进程并发访问。
