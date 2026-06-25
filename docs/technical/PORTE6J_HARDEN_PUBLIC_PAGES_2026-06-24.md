# Porte 6J-HARDEN - Public Korrigo pages hardening

Date UTC: 2026-06-24

## Context

Porte 6J centralized the four public Korrigo pages in:

- `frontend/src/features/korrigo/content/korrigoPublicContent.js`
- `frontend/src/features/korrigo/components/KorrigoPublicPage.vue`

The deployment remains blocked until Porte 6H-C validates the automatic encrypted backup after `20260624T124211Z` and the following StorageBox sync. This hardening pass is local only.

## Scope

Routes reviewed:

- `/korrigo`
- `/korrigo/guide-enseignant`
- `/korrigo/guide-eleve`
- `/korrigo/direction`

No production deployment, Docker build, restart, SQL, migration, manual backup, manual sync, cleanup, or GitHub action was performed.

## Decisions

### Copy statuses

The public status labels keep the technical codes `READY`, `IN_PROGRESS`, and `FINALIZED` because they match the backend source of truth:

- `backend/exams/models.py`, `Copy.Status`
- backend schema contract already checks the same live choices

The frontend contract now parses `Copy.Status` from the backend model and fails if public status codes drift from the backend enum.

### Public workflow

The workflow remains descriptive and bounded. It explains the correction lifecycle without exposing private counts, student data, media paths, exam content, or authenticated details.

### Direction access

The direction public page no longer points to the generic portal `/`.

Decision: direction users authenticate through the existing admin login route and are redirected by authenticated role logic to the direction dashboard. The public CTA is now:

- label: `Accès authentifié`
- route: `/admin/login`

This avoids implying a separate public direction login route that does not exist.

### Icons

All icons referenced by public page content and public login links are now checked against `frontend/src/icons/iconRegistry.js`.

Correction made:

- replaced the unregistered `list` icon with registered `clipboard`

## Route Contract

The router now consumes the central public route source for legacy redirects:

- `/guide-enseignant` redirects to `KORRIGO_PUBLIC_ROUTE_BY_KEY.teacherGuide.path`
- `/guide-eleve` redirects to `KORRIGO_PUBLIC_ROUTE_BY_KEY.studentGuide.path`
- `/direction` redirects to `KORRIGO_PUBLIC_ROUTE_BY_KEY.direction.path`

The test contract rejects full public Korrigo route paths hardcoded outside the central content source.

## Scan Results

Global frontend scan command was run with email redaction.

Summary:

- total redacted match lines: 614
- public page/content scope match lines: 22

Public scope findings:

- matches are test guard patterns such as `TODO`, `fake`, `dummy`, `anonymous_id`, email regexes, and `guide-enseignanthttps`
- `Navbar.vue` matches are Vue event directives such as `@click`
- no public page content match required correction after this hardening pass

Matches outside public scope are in authenticated application screens, test fixtures, or generic frontend code and were not modified in this page hardening pass.

## Tests

Targeted contract:

```text
cd frontend
npm test -- --run tests/unit/korrigoPublicContent.contract.test.ts
```

Result:

```text
11 tests passed
```

Build:

```text
cd frontend
npm run build
```

Result:

```text
vite build PASS
```

Targeted Playwright public pages:

```text
E2E_BASE_URL=http://127.0.0.1:5173 npm run test:e2e -- tests/e2e/korrigo-public-pages.spec.ts
```

Result:

```text
5 tests passed
```

The targeted Playwright run used:

- Vite local on `127.0.0.1:5173`
- Django local SQLite backend on an ephemeral local port
- no production data
- no production credentials

## Local Playwright Audit

Audit directory:

```text
/tmp/korrigo_pages_harden_local_audit_20260624T172806Z
```

Captured:

- route status
- final URL
- title
- H1
- headings
- visible text
- links
- console errors
- network errors
- screenshots

Results:

```text
LOCAL_AUDIT_CONSOLE_ERROR_COUNT=0
LOCAL_AUDIT_NETWORK_ERROR_COUNT=0
LOCAL_AUDIT_EMAIL_COUNT=0
LOCAL_AUDIT_ANONYMOUS_ID_COUNT=0
LOCAL_AUDIT_PLACEHOLDER_COUNT=0
```

## Non-Exposure

The public pages do not include:

- real email addresses
- real names
- `anonymous_id`
- media paths
- copy contents
- public counters
- invented statistics
- unsupported AI/OCR/LLM claims
- the typo `guide-enseignanthttps`

## Verdict

`PAGES_HARDENED_READY_AFTER_6HC`

The code is locally hardened and testable, but must not be deployed until Porte 6H-C is closed.

## Next Step

Close Porte 6H-C after the automatic backup/sync cycle is observed. Only then may a direct deployment of the page changes be considered, followed later by Porte 6I Docker cleanup if all observation gates remain clean.
