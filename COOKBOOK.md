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

### 1. 先解决私有仓库读取权限

`L1nwatch/conclusion` 当前是 private。FengDock 的默认 `GITHUB_TOKEN` 通常不能读取另一个私有仓库，VPS 也需要对应权限。

可选方案：

- 保持 private：为 GitHub Actions 配置只读 fine-grained PAT/GitHub App token，并为 VPS 配置只读 Git 凭据。
- 将代码仓库设为 public：数据库和 `.env` 已被忽略，个人 Conclusion 数据仍不会进入 Git。这是维护成本最低的方案，但必须先确认代码公开是可接受的。

保持 private 时，最简单的 Actions 方案是创建仅覆盖 `L1nwatch/FengDock` 和 `L1nwatch/conclusion`、只有 Contents read 权限的 fine-grained PAT，保存为 FengDock secret `SUBMODULE_TOKEN`，并让 checkout 使用它：

```yaml
- name: Checkout
  uses: actions/checkout@v4
  with:
    token: ${{ secrets.SUBMODULE_TOKEN }}
```

现有 workflow 后续执行的 `git submodule update` 会复用 checkout 持久化的 GitHub 凭据。VPS 也要给实际执行部署脚本的用户配置 Conclusion 只读凭据，并在合入前无交互验证：

```bash
GIT_TERMINAL_PROMPT=0 git ls-remote \
  https://github.com/L1nwatch/conclusion.git refs/heads/main
```

在权限未验证前，不要把 private submodule 合入 FengDock `main`。

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
7. 最后逐个接入三个只读 MCP 工具。

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

- 参考 FengDock 现有 Fire loader，加载 `vendor/conclusion/app/db.py`。
- 使用 SQLite URI `mode=ro`，绝不让 MCP 创建或修改数据。
- 复用 FengDock 现有 `read_only` annotations、`ToolError`、分页和结果上限逻辑。
- `list_conclusions`、`search_conclusions`、`get_conclusion` 分别提交和测试。
- 列表/搜索必须有明确上限；详情不存在时返回稳定、可理解的错误。
- MCP 工具复用 `app/db.py` 的查询函数，不在父仓库复制 SQL。

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
- MCP 是否只读打开了正确的数据库文件。

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
