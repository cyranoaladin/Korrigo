# PRD-19 Workflow Métier Validation

**Date**: 2026-02-02 22:06
**Phase**: End-to-End Workflow Validation

## Objective

Validate complete workflow: Upload batch PDF + CSV → Identification → Dispatch → Correction → Student Portal → CSV Export

## Validation Checklist

### 1. Upload & Processing ⏳

**Standard A4 Upload**:
- [ ] Upload PDF via /admin/exams/new
- [ ] System detects A4 format
- [ ] Creates copies with correct page count
- [ ] Generates booklets

**Batch A3 Upload** (Critical for PRD-19):
- [ ] Upload A3 recto/verso PDF
- [ ] System detects A3 format → triggers BatchA3Processor
- [ ] A3→A4 split executed correctly
- [ ] Page reconstruction follows [P1,P2,P3,P4] order
- [ ] Multi-sheet fusion works (same student → 1 Copy)
- [ ] Page count invariant maintained (multiple of 4)
- [ ] Header crops extracted for all first pages
- [ ] CSV whitelist matching attempted (OCR-assisted)

### 2. Identification ⏳

- [ ] Navigate to /identification
- [ ] See unidentified copies (status: STAGING)
- [ ] Manual identification via /api/booklets/<id>/header/ works
- [ ] Copy transitions STAGING → READY after identification
- [ ] Student assigned correctly

### 3. Dispatch ⏳

- [ ] Navigate to /admin/exams/<id>
- [ ] Assign correctors to exam
- [ ] Dispatch copies to correctors
- [ ] Copies transition READY → LOCKED
- [ ] assigned_corrector field populated
- [ ] dispatch_run_id recorded for traceability

### 4. Correction ⏳

- [ ] Teacher logs in
- [ ] Navigate to /corrector/desk
- [ ] See assigned copies
- [ ] Open copy → canvas renders PDF
- [ ] Add annotation (drag on canvas)
- [ ] Editor opens
- [ ] Save annotation → API persists
- [ ] Autosave works (draft_state)
- [ ] Finalize copy → generates final_pdf
- [ ] Copy transitions LOCKED → GRADED

### 5. Student Portal Access ⏳

- [ ] Student logs in (email + last name)
- [ ] Navigate to /student-portal
- [ ] See graded copies only
- [ ] LOCKED/READY copies hidden
- [ ] Cannot see other students' copies
- [ ] Download PDF → 200 response
- [ ] PDF contains annotations (flattened)
- [ ] Logout works

### 6. CSV Export ⏳

- [ ] Navigate to /admin/exams/<id>
- [ ] Click "Export CSV"
- [ ] CSV downloaded successfully
- [ ] Contains all expected columns (student, score, etc.)
- [ ] Data matches copies in system

## Known Limitations (MVP)

1. **OCR Identification**: Tesseract fails on handwritten CMEN v2 forms
   - Impact: Multi-sheet fusion for batch A3 requires manual identification
   - Mitigation: Manual identification desk remains functional
   - Future: Multi-layer OCR approach (user requirement for production)

2. **E2E Seed Data**: E2E-READY copy lacks booklet data
   - Impact: 1 E2E test fails (corrector flow annotation test)
   - Mitigation: Backend tests prove functionality works
   - Fix: Seed script needs update

## Validation Method

This validation will be performed manually through the UI, with screenshots/logs captured as proof.

---

**Status**: Checklist created, manual validation pending
