# Markdown Files Inventory & Classification

**Date**: 30 Janvier 2026  
**Repository**: `/home/alaeddine/viatique__PMF`  
**Purpose**: Documentation cleanup - Phase 1 inventory

---

## Classification Legend

- **KEEP**: File is current, accurate, and needed
- **UPDATE**: File is needed but requires factual corrections
- **MERGE**: Content should be merged into another file
- **DELETE**: Obsolete, duplicate, or irrelevant
- **MOVE**: Should be relocated to different directory

---

## Root Level Documentation

| File | Size | Classification | Action/Notes |
|------|------|----------------|--------------|
| `README.md` | - | **UPDATE** | Main project README - verify accuracy |
| `README.prod.md` | - | **REVIEW** | Production README - check if duplicate of deployment docs |
| `CHANGELOG.md` | - | **KEEP** | Project changelog - standard file |
| `CAHIER_CHARGES_FINALISATION.md` | - | **REVIEW** | Specification document - assess if current |
| `COHERENCE_REPORT.md` | - | **REVIEW** | Assessment report - check date/relevance |
| `DELIVERABLES_v1.0.0-rc1.md` | - | **REVIEW** | Release deliverables - verify if superseded |
| `FINAL_VERDICT.md` | - | **REVIEW** | Assessment - check if still relevant |
| `GAP_ANALYSIS.md` | - | **REVIEW** | Gap analysis - dated? |
| `HIGH_RISK_AREAS.md` | - | **REVIEW** | Risk assessment - merge into security docs? |
| `PRODUCTION_CHECKLIST.md` | - | **REVIEW** | Deployment checklist - consolidate |
| `PRODUCTION_READINESS_FINAL.md` | - | **REVIEW** | Production readiness - consolidate |
| `PRODUCTION_READINESS_STATUS.md` | - | **REVIEW** | Production readiness - consolidate |
| `PRODUCTION_READY_REPORT.md` | - | **REVIEW** | Production readiness - consolidate |
| `PROOFS.md` | - | **REVIEW** | Evidence document - archive? |
| `RELEASE_GATE_REPORT_2026-01-28.md` | - | **REVIEW** | Release report - archive |
| `RELEASE_GATE_REPORT_v1.0.0-rc1.md` | - | **REVIEW** | Release report - archive |
| `RELEASE_NOTES_v1.0.0.md` | - | **KEEP** | Release notes - standard file |
| `REPORT.md` | - | **REVIEW** | Generic report - what is this? |
| `RUNBOOK_PROD.md` | - | **UPDATE** | Production runbook - verify commands |
| `RUNBOOK_STAGING.md` | - | **UPDATE** | Staging runbook - verify commands |
| `SECURITY_PERMISSIONS_INVENTORY.md` | - | **REVIEW** | Security inventory - move to docs/? |
| `task.md` | - | **DELETE** | Temporary task file |
| `test_analysis.md` | - | **REVIEW** | Test analysis - dated? |
| `TEST_PLAN.md` | - | **REVIEW** | Test plan - duplicate of docs/quality/TEST_PLAN.md? |
| `verification_report.md` | - | **REVIEW** | Verification report - dated? |

---

## docs/ Directory

### docs/ Root Files

| File | Classification | Action/Notes |
|------|----------------|--------------|
| `docs/ADVANCED_PDF_VALIDATORS.md` | **REVIEW** | Technical implementation - verify accuracy |
| `docs/API_REFERENCE.md` | **UPDATE** | API reference - must match actual endpoints |
| `docs/ARCHITECTURE.md` | **UPDATE** | Architecture doc - verify alignment with code |
| `docs/BUSINESS_WORKFLOWS.md` | **UPDATE** | Workflow documentation - verify accuracy |
| `docs/DATABASE_SCHEMA.md` | **UPDATE** | Database schema - verify against models |
| `docs/DEPLOYMENT_GUIDE.md` | **UPDATE** | Deployment guide - verify commands |
| `docs/DEPLOY_PRODUCTION.md` | **MERGE** | Merge with DEPLOYMENT_GUIDE.md |
| `docs/DEVELOPMENT_GUIDE.md` | **UPDATE** | Dev setup guide - verify commands |
| `docs/FINAL_100_PERCENT_REPORT.md` | **REVIEW** | Assessment report - archive? |
| `docs/PDF_VALIDATORS_IMPLEMENTATION.md` | **REVIEW** | Implementation details - verify |
| `docs/PHASE1_SECURITY_CORRECTIONS.md` | **REVIEW** | Historical doc - archive? |
| `docs/PHASE2_PRODUCTION_IMPROVEMENTS.md` | **REVIEW** | Historical doc - archive? |
| `docs/PHASE3_QUALITY_AUDIT.md` | **REVIEW** | Historical doc - archive? |
| `docs/PRODUCTION_RELEASE_CHECKLIST.md` | **REVIEW** | Checklist - consolidate with root checklists |
| `docs/RELEASE_GATE_ONESHOT_VALIDATION_REPORT.md` | **REVIEW** | Release report - archive |
| `docs/RELEASE_NOTES_STEP3.md` | **REVIEW** | Incremental release notes - archive? |
| `docs/SPEC.md` | **UPDATE** | Project specification - verify current |
| `docs/TECHNICAL_MANUAL.md` | **UPDATE** | Technical manual - verify accuracy |
| `docs/walkthrough.md` | **UPDATE** | User walkthrough - verify screenshots/steps |

### docs/support/ (Phase 5 Deliverables)

| File | Classification | Action/Notes |
|------|----------------|--------------|
| `docs/support/FAQ.md` | **KEEP** | ✅ Phase 5 deliverable - comprehensive FAQ |
| `docs/support/DEPANNAGE.md` | **KEEP** | ✅ Phase 5 deliverable - troubleshooting guide |
| `docs/support/SUPPORT.md` | **KEEP** | ✅ Phase 5 deliverable - support procedures |

### docs/quality/

| File | Classification | Action/Notes |
|------|----------------|--------------|
| `docs/quality/CI_WORKFLOWS.md` | **UPDATE** | CI documentation - verify workflows exist |
| `docs/quality/RUNBOOK_LOCAL_PRODLIKE.md` | **UPDATE** | Local prod runbook - verify commands |
| `docs/quality/TEST_PLAN.md` | **UPDATE** | Test plan - verify test framework |

### docs/audits/

| File | Classification | Action/Notes |
|------|----------------|--------------|
| `docs/audits/AUDIT_20260126_ANTIGRAVITY.md` | **REVIEW** | Audit report - archive? |
| `docs/audits/DOCS_AUDIT_LOCAL_ONLY_REPORT.md` | **REVIEW** | Audit report - archive? |
| `docs/audits/SYNC_ON_NETWORKED_MACHINE.md` | **REVIEW** | Sync documentation - still relevant? |

### docs/tasks/

| File | Classification | Action/Notes |
|------|----------------|--------------|
| `docs/tasks/TODO_APP_COMPLETION.md` | **REVIEW** | TODO list - is this current? |

---

## .antigravity/ Directory

**Status**: AI assistant configuration directory  
**Classification**: **KEEP** (operational tooling)

### .antigravity/ Files

| File | Classification | Notes |
|------|----------------|-------|
| `.antigravity/README.md` | **KEEP** | Antigravity docs |
| `.antigravity/ANTIGRAVITY_SYNC_REPORT.md` | **KEEP** | Sync report |
| `.antigravity/PHASE3_FRONTEND_MANUAL_CHECKLIST.md` | **KEEP** | Checklist |
| `.antigravity/SUPERVISION_RULES.md` | **KEEP** | Rules |

### .antigravity/rules/

| Files | Classification | Notes |
|-------|----------------|-------|
| All rule files (00-06, api_error_contract, coding-guidelines, project-architecture) | **KEEP** | AI coding rules - operational |

### .antigravity/workflows/

| Files | Classification | Notes |
|-------|----------------|-------|
| All workflow files | **KEEP** | AI workflow definitions - operational |

### .antigravity/skills/

| Files | Classification | Notes |
|-------|----------------|-------|
| All skill files | **KEEP** | AI skills - operational |

### .antigravity/checklists/

| Files | Classification | Notes |
|-------|----------------|-------|
| All checklist files | **KEEP** | AI checklists - operational |

---

## .claude/ Directory

**Status**: Legacy AI assistant configuration  
**Classification**: **EVALUATE** - May be duplicate of .antigravity/

### .claude/ Files

| File | Classification | Notes |
|------|----------------|-------|
| `.claude/README.md` | **COMPARE** | Compare with .antigravity/README.md |
| `.claude/SUPERVISION_RULES.md` | **COMPARE** | Compare with .antigravity version |
| `.claude/ETAPE_1_P0_BASELINE_SECURITY.md` | **REVIEW** | Historical? |
| `.claude/ETAPE_2_PDF_PIPELINE.md` | **REVIEW** | Historical? |
| `.claude/ETAPE_3_ANNOTATION_GRADING.md` | **REVIEW** | Historical? |
| `.claude/PHASE2_TEST_REPORT.md` | **REVIEW** | Historical? |
| `.claude/PREUVES_ETAPE_1_P0.md` | **REVIEW** | Historical? |

### .claude/rules/

| Files | Classification | Notes |
|-------|----------------|-------|
| All rule files (00-06) | **COMPARE** | Compare with .antigravity/rules/ - likely duplicates |

### .claude/workflows/

| Files | Classification | Notes |
|-------|----------------|-------|
| All workflow files | **COMPARE** | Compare with .antigravity/workflows/ - likely duplicates |

### .claude/skills/

| Files | Classification | Notes |
|-------|----------------|-------|
| All skill files | **COMPARE** | Compare with .antigravity/skills/ - likely duplicates |

### .claude/decisions/

| Files | Classification | Notes |
|-------|----------------|-------|
| `ADR-001-student-authentication-model.md` | **KEEP** | Architecture decision record |
| `ADR-002-pdf-coordinate-normalization.md` | **KEEP** | Architecture decision record |
| `ADR-003-copy-status-state-machine.md` | **KEEP** | Architecture decision record |
| `decisions/README.md` | **KEEP** | ADR index |

### .claude/checklists/

| Files | Classification | Notes |
|-------|----------------|-------|
| All checklist files | **COMPARE** | Compare with .antigravity/checklists/ - likely duplicates |

---

## Summary Statistics

**Total .md files found in repository**: ~160 files  
**Breakdown**:
- Root level: 24 files
- docs/: 29 files
- .antigravity/: 27 files
- .claude/: 28 files (potential duplicates)
- .zenflow/tasks/: 42 files (historical artifacts)
- Other directories: ~10 files

---

## Immediate Actions Required

### Priority 1: Duplication Resolution
- **Compare .claude/ vs .antigravity/** - Likely full duplication, decide which to keep
- **Consolidate production readiness docs** - 4+ files with similar names in root
- **Merge deployment guides** - DEPLOYMENT_GUIDE.md vs DEPLOY_PRODUCTION.md

### Priority 2: Factual Verification
- Verify all commands in runbooks work
- Check API_REFERENCE.md matches actual API
- Validate ARCHITECTURE.md reflects current code
- Confirm DATABASE_SCHEMA.md matches models

### Priority 3: Archive Historical Documents
- Move .zenflow/tasks/ artifacts to archive or delete
- Review all PHASE*.md, ETAPE*.md documents
- Archive dated audit reports

### Priority 4: Reorganization
- Consider moving all reports to docs/reports/
- Move historical docs to docs/archive/ or delete
- Clean up root directory clutter

---

## Next Steps (Phase 2)

1. **Canonicalization**: Define target documentation structure
2. **Diff .claude/ vs .antigravity/**: Determine which to keep
3. **Consolidate duplicates**: Merge similar documents
4. **Verify factual accuracy**: Test all commands, check API docs
5. **Archive or delete**: Remove obsolete files
6. **Update cross-references**: Fix all broken links
7. **Final validation**: Ensure documentation matches code 100%
