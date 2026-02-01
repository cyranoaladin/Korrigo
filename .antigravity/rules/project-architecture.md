---
description: Project architecture and constraints for OpenViatique PMF
globs: "**/*"
alwaysApply: true
---

# Project Architecture Rules

This project strictly follows the architecture and constraints defined in the root `@SPEC.md` file.

## Critical Constraints

1.  **Technology Stack**:
    *   **Backend**: Django 4.2 LTS (Django REST Framework).
    *   **Frontend**: Vue.js 3 (Composition API, Pinia).
    *   **Database**: PostgreSQL 15+ (Required for concurrency and JSONB).
    *   **Infrastructure**: All deployment must be via Docker Compose.

2.  **Core Business Rules**:
    *   **Single PDF Import**: The system MUST ingest a single "Master" PDF containing all scans in bulk. Never suggest uploading individual student PDFs.
    *   **Anonymous Grading**: Strict anonymization is required between the student and the corrector. Correctors must never see the student's name during the correction phase.

## Reference
Refer to `@SPEC.md` for the "Bible" of this project. If a functionality is not in `@SPEC.md`, it does not exist.
