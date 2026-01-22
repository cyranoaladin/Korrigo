# CI Workflows

## Quality Gate Workflow (`quality_gate.yml`)

Triggers on `push` to `main` and all `pull_request` events.

### Jobs

1.  **Backend Quality**
    - **Lint**: `ruff check .`
    - **Typecheck**: `mypy .`
    - **Tests**: `pytest -W error` (Strict Mode)
    - **Deploy Check**: `python manage.py check --deploy`

2.  **Frontend Quality**
    - **Install**: `pnpm install --frozen-lockfile`
    - **Lint**: `pnpm lint`
    - **Typecheck**: `pnpm typecheck`
    - **Build**: `pnpm build` (Fail on warnings)

3.  **E2E (Prod-Like)**
    - **Setup**: Docker Compose Up.
    - **Run**: Playwright tests against `localhost:8080`.
    - **Artifacts**: Upload video/trace on failure.

### Acceptance Criteria
- All jobs MUST pass (Green).
- No skipped tests allowed without explicit exemption.
