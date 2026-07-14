# Repository Guidelines

- Keep each change limited to one independently reviewable feature.
- Add or update focused tests for every behavior change.
- Preserve the MVP boundaries documented in `README.md`; do not add AI summarization, vector search, rich text, complex permissions, or unrelated UI infrastructure unless explicitly requested.
- Keep Conclusion locally runnable, but follow FengDock's `vendor/fire` bundled-app production pattern. Do not add a separate production container, venv, MCP server, or deployment pipeline unless explicitly requested.
- Reuse the FengDock/Fire frontend stack: Vue 3, TypeScript, Vite, and Element Plus.
- Keep reusable read queries in `app/db.py`; FengDock's MCP facade may load these functions and open the SQLite database read-only, matching the existing Fire integration.
- Follow `COOKBOOK.md` for local development, two-repository publishing, FengDock integration, deployment verification, and rollback.
- Use UTC for persisted timestamps and keep persistence/Python names in `snake_case`.
- Do not commit SQLite database files, secrets, local environment files, caches, or generated build output.
