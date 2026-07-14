# Repository Guidelines

- Keep each change limited to one independently reviewable feature.
- Add or update focused tests for every behavior change.
- Preserve the MVP boundaries documented in `README.md`; do not add AI summarization, vector search, rich text, complex permissions, or unrelated UI infrastructure unless explicitly requested.
- Keep Conclusion independently runnable. FengDock integration belongs in the FengDock parent repository and must be handled as a separate change.
- Treat the Conclusion API as the integration boundary. FengDock MCP consumers should not depend directly on internal database tables.
- Use UTC for persisted timestamps and keep persistence/Python names in `snake_case`.
- Do not commit SQLite database files, secrets, local environment files, caches, or generated build output.

