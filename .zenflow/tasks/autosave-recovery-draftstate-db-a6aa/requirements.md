# Product Requirements Document (PRD)
## AUTOSAVE + RECOVERY (DraftState DB + localStorage)

**Task ID**: ZF-AUD-06  
**Created**: 2026-01-31  
**Status**: Requirements Phase  
**Priority**: P0 (Critical - Data Loss Prevention)

---

## Executive Summary

Ensure zero work loss for correctors through a robust autosave and recovery system that stores draft state in both the database (DraftState model) and browser localStorage, with automatic recovery on page reload.

**Objective**: Guarantee 100% reproducible recovery with zero illegitimate overwrites of finalized copies.

---

## Current State Analysis

### What Exists

#### Backend
- **DraftState Model** (`backend/grading/models.py:214-260`)
  - Fields: id, copy, owner, payload, lock_token, client_id, version, updated_at
  - Unique constraint: (copy, owner) - one draft per user per copy
  - Atomic version increment using Django F() expression
  
- **Draft API Endpoints** (`backend/grading/views_draft.py`)
  - `GET /api/grading/copies/<uuid:copy_id>/draft/` - retrieve draft
  - `PUT /api/grading/copies/<uuid:copy_id>/draft/` - save draft
  - `DELETE /api/grading/copies/<uuid:copy_id>/draft/` - delete draft
  - Lock token required for PUT operations
  - client_id conflict detection to prevent session overwrites

#### Frontend
- **Dual Autosave Strategy** (`frontend/src/views/admin/CorrectorDesk.vue:364-395`)
  - **localStorage**: 300ms debounce after each change
  - **Server API**: 2000ms (2s) debounce after each change
  - Unique client_id per browser session (crypto.randomUUID())
  
- **Recovery Logic** (`CorrectorDesk.vue:296-323`)
  - Checks both localStorage and server on mount
  - Prefers local draft if timestamp is newer
  - Restores draft to editor (not auto-saved to annotation list)
  - User must manually save after restoration

#### Protection Mechanisms
- **Lock System**: Soft locks with 30s heartbeat, token validation
- **Status Gates**: GRADED copies cannot be modified (`views.py:170-171`)
- **Conflict Detection**: client_id prevents multi-tab overwrites

### What's Missing

1. **Backend Unit Tests**: No tests for DraftState save/load/permissions
2. **GRADED Protection in Draft Endpoints**: No explicit status check in `views_draft.py`
3. **Frequency Documentation Mismatch**: Docs say 30s, implementation is 2s
4. **Anti-Spam Analysis**: No formal audit of API call frequency
5. **E2E Recovery Proof**: Existing test doesn't verify 100% state fidelity

---

## Requirements

### Functional Requirements

#### FR-1: Autosave Triggers
- **FR-1.1**: Autosave triggers on every change to draft annotation (content, type, score_delta)
- **FR-1.2**: localStorage save debounced at **300ms** to minimize writes
- **FR-1.3**: Server save debounced at **2000ms (2s)** to balance responsiveness and API load
- **FR-1.4**: Saves include full editor state: annotation rect, type, content, score_delta, page_index
- **FR-1.5**: No autosave during read-only mode (lock conflict or GRADED status)

#### FR-2: Storage Strategy
- **FR-2.1**: Dual storage: localStorage (fast, local-first) + DraftState DB (persistent, cross-device)
- **FR-2.2**: localStorage key format: `draft_{copyId}_{userId}` (stable across sessions)
- **FR-2.3**: Server payload includes: rect, type, content, score_delta, page_index, saved_at timestamp
- **FR-2.4**: client_id transmitted with every server save to detect session conflicts

#### FR-3: Recovery Workflow
- **FR-3.1**: On page load, check both localStorage and server for drafts
- **FR-3.2**: Compare timestamps: prefer local if `local.saved_at > server.updated_at`
- **FR-3.3**: Display restore banner if draft found (source: LOCAL or SERVER)
- **FR-3.4**: User chooses: "Restore" or "Discard"
- **FR-3.5**: Restore action:
  - Adopt server client_id if restoring from server
  - Navigate to correct page (page_index)
  - Open editor with draft content
  - User must manually save to persist

#### FR-4: Protection Against Overwrites
- **FR-4.1**: GRADED copies MUST NOT accept draft saves (status gate in backend)
- **FR-4.2**: Lock token required for all PUT /draft/ operations
- **FR-4.3**: client_id mismatch returns 409 Conflict
- **FR-4.4**: Draft save fails if user loses lock (409 Conflict)

#### FR-5: Draft Cleanup
- **FR-5.1**: localStorage cleared after successful annotation save
- **FR-5.2**: Server draft deleted after successful annotation save
- **FR-5.3**: User can manually discard draft from banner

### Non-Functional Requirements

#### NFR-1: Performance
- **NFR-1.1**: localStorage write < 10ms (synchronous, non-blocking)
- **NFR-1.2**: Server autosave debounced to max 1 request per 2s per copy
- **NFR-1.3**: No autosave during typing (debounce prevents spam)

#### NFR-2: Reliability
- **NFR-2.1**: 100% reproducible recovery (no data loss on refresh)
- **NFR-2.2**: Zero illegitimate overwrites of GRADED copies
- **NFR-2.3**: Atomic version increment prevents race conditions

#### NFR-3: Security
- **NFR-3.1**: Only draft owner can read/write their draft
- **NFR-3.2**: Lock token validated on every PUT operation
- **NFR-3.3**: GRADED status immutable via draft API

---

## Acceptance Criteria

### AC-1: Autosave Frequency Audit
- [ ] Document actual autosave frequency (2s server, 300ms local)
- [ ] Verify no API spam (max 1 server request per 2s)
- [ ] Confirm debounce logic prevents rapid-fire requests
- [ ] Update business documentation to match implementation

### AC-2: Backend Unit Tests
- [ ] **Test: Save draft with valid lock** → 200 OK, version incremented
- [ ] **Test: Load draft as owner** → 200 OK, payload returned
- [ ] **Test: Load non-existent draft** → 204 No Content
- [ ] **Test: Save without lock token** → 403 Forbidden
- [ ] **Test: Save with wrong lock owner** → 409 Conflict
- [ ] **Test: Save to GRADED copy** → 400 Bad Request (NEW)
- [ ] **Test: client_id conflict** → 409 Conflict
- [ ] **Test: Unauthorized access** → 403 Forbidden

### AC-3: E2E Recovery Test
- [ ] Corrector opens copy, acquires lock
- [ ] Corrector creates draft annotation (draw + partial text)
- [ ] Wait 3s for server autosave
- [ ] Hard refresh page (F5)
- [ ] Verify restore banner appears (source: SERVER or LOCAL)
- [ ] Click "Restore"
- [ ] Verify editor opens with exact state (rect, content, score, page)
- [ ] Save annotation
- [ ] Verify annotation persisted to list
- [ ] Verify draft cleared (localStorage + server)

### AC-4: GRADED Protection
- [ ] Backend: PUT /draft/ on GRADED copy returns 400 Bad Request
- [ ] Frontend: Read-only mode when status=GRADED (no autosave)
- [ ] E2E: Attempt restore on GRADED copy → discard draft, show read-only warning

### AC-5: Documentation
- [ ] Create `audit.md` with:
  - Autosave frequency analysis (2s server, 300ms local)
  - API call patterns (debounce proof)
  - Anti-spam verification
  - Recovery workflow diagram
- [ ] Update `docs/technical/BUSINESS_WORKFLOWS.md` line 368: "2s server + 300ms local"

---

## Out of Scope

1. **Multi-device sync**: Not implemented (DraftState allows it, but not priority)
2. **Offline mode**: No ServiceWorker/PWA (localStorage is offline-capable but not full offline)
3. **Draft history**: Only latest draft stored (no versioning UI)
4. **Conflict resolution UI**: Simple 409 error, no merge UI
5. **Autosave for remarks/appreciation**: Separate feature (already implemented with 1s debounce)

---

## Success Metrics

1. **Zero data loss incidents** in production (6 months monitoring)
2. **100% E2E recovery test pass rate**
3. **Backend unit test coverage** for DraftState endpoints: 100%
4. **API autosave rate** ≤ 0.5 requests/second per active user

---

## Technical Constraints

1. **Django ORM**: F() expression for atomic version increment
2. **PostgreSQL**: Unique constraint on (copy, owner)
3. **Vue 3 Composition API**: watch() with deep: true for reactive autosave
4. **Lock dependency**: Draft save requires active lock
5. **Status immutability**: GRADED copies read-only

---

## Assumptions

1. Users work on one copy at a time (single-tab corrector flow)
2. Network failures are transient (localStorage failover)
3. Lock expires before draft expires (30s heartbeat keeps both alive)
4. User can manually refresh if restore fails (no auto-retry loop)

---

## Dependencies

- **Existing**: DraftState model, views_draft.py, CorrectorDesk.vue autosave logic
- **Required**: pytest (backend), playwright (E2E)
- **Blocked by**: None

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| localStorage quota exceeded | Medium | Low | Clear old drafts on annotation save |
| Multi-tab conflict | High | Medium | client_id prevents overwrites (409 error) |
| Server autosave fails | High | Low | localStorage failover + retry logic |
| GRADED overwrite | Critical | Low | Status gate in backend (NEW requirement) |

---

## Open Questions

**Q1**: Should we add autosave for QuestionRemarks and GlobalAppreciation to DraftState?  
**A1**: Out of scope - they already have 1s debounce autosave to server.

**Q2**: What happens if user opens same copy in 2 tabs?  
**A2**: Second tab gets 409 Conflict on lock acquire → read-only mode. Draft save fails with 409.

**Q3**: Should we show "last saved" indicator for drafts?  
**A3**: Already exists - `lastSaveStatus` shows "Sauvegardé (Local/Serveur) à HH:MM:SS" (line 587-596).

**Q4**: Should draft survive lock expiration?  
**A4**: Yes - DraftState persists independently. User can restore after re-acquiring lock.

---

## Next Steps

1. **Technical Specification** → Define test scenarios, API contracts, validation logic
2. **Implementation Plan** → Break down into tasks (backend tests, GRADED gate, E2E, docs)
3. **Validation** → Run full test suite, verify recovery in staging environment
