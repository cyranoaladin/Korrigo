# CI Workflows - Korrigo PMF

## Deployable Gate Workflow (`korrigo-ci.yml`)

Triggers on `push` to `main`, `master`, `develop` and all `pull_request` events.

### Jobs

1.  **Likn (Backend)**
    - **Tools**: `flake8`
    - **Checks**: Syntax errors, cyclomatic complexity (<10), line length (<127).

2.  **Unit Tests (pytest)**
    - **Environment**: Python 3.9, Tesseract OCR installed.
    - **Scope**: All unit tests (`pytest -q`).
    - **Dependencies**: `requirements.txt`.

3.  **Security**
    - **Dependency Audit**: `pip-audit`.
    - **Static Analysis**: `bandit` (scans for security issues).

4.  **Integration (Gate)**
    - **Scope**: Critical Workflows (Grading, Workflow Complete, PDF Validators, Audit).
    - **Environment**: Python 3.9, Tesseract OCR.
    - **Cmd**: `pytest grading/tests/test_workflow_complete.py ...`

5.  **Packaging**
    - **Action**: Build Docker Image (`korrigo-backend:ci`).

6.  **Deployable Gate**
    - **Condition**: All previous jobs must pass.
    - **Output**: "DEPLOYABLE: all CI gates passed."

### Acceptance Criteria
- All jobs MUST pass (Green).
- Tests run on Python 3.9.
- No high-severity security vulnerabilities.
