# Repository Guidelines

- Keep each change limited to one independently reviewable feature.
- Add or update focused tests for every behavior change.
- Preserve the MVP boundaries documented in `README.md`; do not add AI summarization, vector search, rich text, complex permissions, or unrelated UI infrastructure unless explicitly requested.
- Keep Conclusion locally runnable, but follow FengDock's `vendor/fire` bundled-app production pattern. Do not add a separate production container, venv, MCP server, or deployment pipeline unless explicitly requested.
- Reuse the FengDock/Fire frontend stack: Vue 3, TypeScript, Vite, and Element Plus.
- Keep reusable read and write operations in `app/db.py`; FengDock's MCP facade may load them for Conclusion tools. Reads must use read-only connections, while create/update tools must use explicit transactions and write annotations.
- Do not expose MCP deletion unless explicitly requested. The initial writable MCP scope is create and update.
- Follow `COOKBOOK.md` for local development, two-repository publishing, FengDock integration, deployment verification, and rollback.
- Generate README screenshots from deterministic public-safe demo data with Playwright; never use production Conclusion data or synthetic images presented as real UI.
- Use UTC for persisted timestamps and keep persistence/Python names in `snake_case`.
- Do not commit SQLite database files, secrets, local environment files, caches, or generated build output.
