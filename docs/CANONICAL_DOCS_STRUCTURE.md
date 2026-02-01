# Canonical Documentation Structure

**Date**: 30 Janvier 2026  
**Purpose**: Define the target documentation structure for Korrigo PMF  
**Status**: Phase 2 - Canonicalization

---

## Design Principles

1. **Single Source of Truth**: No duplicate documents
2. **Logical Organization**: Docs grouped by audience and purpose
3. **Clear Naming**: Descriptive, consistent file names
4. **Maintainability**: Easy to keep synchronized with code
5. **Discoverability**: Intuitive structure for all users

---

## Proposed Directory Structure

```
/home/alaeddine/viatique__PMF/
│
├── README.md                           # Project overview + quick start
├── CHANGELOG.md                        # Version history
├── RELEASE_NOTES_v1.0.0.md            # Current release notes
│
├── docs/
│   ├── README.md                       # Documentation index
│   │
│   ├── user/                          # End-user documentation
│   │   ├── GUIDE_ADMINISTRATEUR.md    # Admin user guide
│   │   ├── GUIDE_ENSEIGNANT.md        # Teacher user guide
│   │   ├── GUIDE_SECRETARIAT.md       # Secretariat user guide
│   │   ├── GUIDE_ELEVE.md             # Student user guide
│   │   └── walkthrough.md             # Interactive walkthrough
│   │
│   ├── support/                       # Support & troubleshooting
│   │   ├── FAQ.md                     # Comprehensive FAQ
│   │   ├── DEPANNAGE.md               # Troubleshooting guide
│   │   └── SUPPORT.md                 # Support procedures
│   │
│   ├── technical/                     # Technical documentation
│   │   ├── ARCHITECTURE.md            # System architecture
│   │   ├── API_REFERENCE.md           # API documentation
│   │   ├── DATABASE_SCHEMA.md         # Database schema
│   │   ├── BUSINESS_WORKFLOWS.md      # Business process flows
│   │   ├── PDF_PROCESSING.md          # PDF processing pipeline
│   │   └── SECURITY.md                # Security architecture
│   │
│   ├── development/                   # Developer documentation
│   │   ├── DEVELOPMENT_GUIDE.md       # Dev environment setup
│   │   ├── CONTRIBUTION_GUIDE.md      # How to contribute
│   │   ├── CODING_STANDARDS.md        # Code style guide
│   │   └── TESTING_GUIDE.md           # Test strategy & execution
│   │
│   ├── deployment/                    # Deployment documentation
│   │   ├── DEPLOYMENT_GUIDE.md        # Complete deployment guide
│   │   ├── RUNBOOK_PRODUCTION.md      # Production runbook
│   │   ├── RUNBOOK_STAGING.md         # Staging runbook
│   │   └── DOCKER_GUIDE.md            # Docker-specific guide
│   │
│   ├── quality/                       # QA documentation
│   │   ├── TEST_PLAN.md               # Test plan
│   │   ├── CI_CD.md                   # CI/CD pipeline docs
│   │   └── QUALITY_GATES.md           # Quality criteria
│   │
│   ├── decisions/                     # Architecture Decision Records
│   │   ├── README.md                  # ADR index
│   │   ├── ADR-001-authentication.md
│   │   ├── ADR-002-pdf-coordinates.md
│   │   └── ADR-003-copy-state-machine.md
│   │
│   └── archive/                       # Historical documents
│       ├── PHASE1_SECURITY_CORRECTIONS.md
│       ├── PHASE2_PRODUCTION_IMPROVEMENTS.md
│       ├── PHASE3_QUALITY_AUDIT.md
│       └── audits/
│           └── [dated audit reports]
│
├── .antigravity/                      # AI assistant configuration (KEEP)
│   ├── README.md
│   ├── rules/
│   ├── workflows/
│   ├── skills/
│   └── checklists/
│
├── .zenflow/                          # Zenflow tooling (KEEP)
│   ├── rules/
│   └── workflows/
│
├── release/                           # Release artifacts
│   └── attestations/
│
├── scripts/
│   └── README.md                      # Scripts documentation
│
└── backend/
    └── SECURITY_SCANNING.md           # Backend-specific security docs
```

---

## File Consolidation Map

### Root Level Cleanup

**KEEP**:
- `README.md` - Main project README (UPDATE with current info)
- `CHANGELOG.md` - Standard changelog
- `RELEASE_NOTES_v1.0.0.md` - Current release notes

**MERGE**:
- `README.prod.md` → Merge into `docs/deployment/DEPLOYMENT_GUIDE.md`
- `RUNBOOK_PROD.md` → Rename to `docs/deployment/RUNBOOK_PRODUCTION.md`
- `RUNBOOK_STAGING.md` → Move to `docs/deployment/RUNBOOK_STAGING.md`

**ARCHIVE** (move to `docs/archive/`):
- `CAHIER_CHARGES_FINALISATION.md`
- `COHERENCE_REPORT.md`
- `DELIVERABLES_v1.0.0-rc1.md`
- `FINAL_VERDICT.md`
- `GAP_ANALYSIS.md`
- `PRODUCTION_CHECKLIST.md`
- `PRODUCTION_READINESS_FINAL.md`
- `PRODUCTION_READINESS_STATUS.md`
- `PRODUCTION_READY_REPORT.md`
- `PROOFS.md`
- `RELEASE_GATE_REPORT_2026-01-28.md`
- `RELEASE_GATE_REPORT_v1.0.0-rc1.md`
- `REPORT.md`
- `test_analysis.md`
- `verification_report.md`

**DELETE**:
- `task.md` - Temporary task file
- `TEST_PLAN.md` - Duplicate of `docs/quality/TEST_PLAN.md`
- `HIGH_RISK_AREAS.md` - Outdated risk assessment
- `SECURITY_PERMISSIONS_INVENTORY.md` - Merge into `docs/technical/SECURITY.md`

### docs/ Root Consolidation

**Technical Documentation**:
- `docs/ARCHITECTURE.md` → `docs/technical/ARCHITECTURE.md` (UPDATE)
- `docs/API_REFERENCE.md` → `docs/technical/API_REFERENCE.md` (UPDATE)
- `docs/DATABASE_SCHEMA.md` → `docs/technical/DATABASE_SCHEMA.md` (UPDATE)
- `docs/BUSINESS_WORKFLOWS.md` → `docs/technical/BUSINESS_WORKFLOWS.md` (UPDATE)
- `docs/ADVANCED_PDF_VALIDATORS.md` + `docs/PDF_VALIDATORS_IMPLEMENTATION.md` → `docs/technical/PDF_PROCESSING.md` (MERGE + UPDATE)
- `docs/TECHNICAL_MANUAL.md` → Review and distribute to appropriate technical/ files

**Development Documentation**:
- `docs/DEVELOPMENT_GUIDE.md` → `docs/development/DEVELOPMENT_GUIDE.md` (UPDATE)
- `docs/SPEC.md` → `docs/development/SPECIFICATION.md` or archive

**Deployment Documentation**:
- `docs/DEPLOYMENT_GUIDE.md` → `docs/deployment/DEPLOYMENT_GUIDE.md` (UPDATE)
- `docs/DEPLOY_PRODUCTION.md` → MERGE into `docs/deployment/DEPLOYMENT_GUIDE.md`

**User Documentation**:
- `docs/walkthrough.md` → `docs/user/walkthrough.md` (UPDATE)
- Create role-specific guides in `docs/user/` (extract from FAQ if needed)

**Archive**:
- `docs/FINAL_100_PERCENT_REPORT.md` → `docs/archive/`
- `docs/PHASE1_SECURITY_CORRECTIONS.md` → `docs/archive/`
- `docs/PHASE2_PRODUCTION_IMPROVEMENTS.md` → `docs/archive/`
- `docs/PHASE3_QUALITY_AUDIT.md` → `docs/archive/`
- `docs/PRODUCTION_RELEASE_CHECKLIST.md` → `docs/archive/`
- `docs/RELEASE_GATE_ONESHOT_VALIDATION_REPORT.md` → `docs/archive/`
- `docs/RELEASE_NOTES_STEP3.md` → `docs/archive/`
- `docs/audits/` → `docs/archive/audits/`

**Quality Documentation**:
- `docs/quality/TEST_PLAN.md` → KEEP (UPDATE)
- `docs/quality/CI_WORKFLOWS.md` → Rename to `docs/quality/CI_CD.md` (UPDATE)
- `docs/quality/RUNBOOK_LOCAL_PRODLIKE.md` → `docs/development/LOCAL_TESTING.md` (UPDATE)

**Support Documentation**:
- `docs/support/FAQ.md` → KEEP ✅
- `docs/support/DEPANNAGE.md` → KEEP ✅
- `docs/support/SUPPORT.md` → KEEP ✅

### AI Configuration Resolution

**.claude/ vs .antigravity/**:

**Decision**: Keep `.antigravity/` as primary, archive `.claude/`

**Rationale**:
- `.antigravity/` appears to be the current active configuration
- `.claude/` contains some different files (00, 01, 06 rules differ)
- ADRs in `.claude/decisions/` should be moved to `docs/decisions/`

**Actions**:
1. **Move ADRs**: `.claude/decisions/` → `docs/decisions/`
2. **Compare diff rules**: Determine which version is current
3. **Archive**: Move `.claude/` to `.claude.archive/` or delete
4. **Historical docs**: Move `.claude/ETAPE_*.md`, `.claude/PHASE*.md` to `docs/archive/`

### .zenflow/ Tasks

**Action**: Archive or delete
- `.zenflow/tasks/audit-993a/` → Historical execution artifacts
- `.zenflow/tasks/finalisation-6976/` → Historical execution artifacts

**Decision**: Delete (not needed for documentation)

---

## Documentation Index Structure

**Create**: `docs/README.md` - Master documentation index

```markdown
# Korrigo PMF Documentation

## For Users
- [Guide Administrateur](user/GUIDE_ADMINISTRATEUR.md)
- [Guide Enseignant](user/GUIDE_ENSEIGNANT.md)
- [Guide Secrétariat](user/GUIDE_SECRETARIAT.md)
- [Guide Élève](user/GUIDE_ELEVE.md)

## Support
- [FAQ](support/FAQ.md)
- [Guide de Dépannage](support/DEPANNAGE.md)
- [Procédures de Support](support/SUPPORT.md)

## For Developers
- [Development Guide](development/DEVELOPMENT_GUIDE.md)
- [API Reference](technical/API_REFERENCE.md)
- [Architecture](technical/ARCHITECTURE.md)

## For Operations
- [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)
- [Production Runbook](deployment/RUNBOOK_PRODUCTION.md)
- [Staging Runbook](deployment/RUNBOOK_STAGING.md)

## Architecture Decisions
- [ADR Index](decisions/README.md)
```

---

## Execution Plan

### Step 1: Create New Directory Structure
```bash
cd /home/alaeddine/viatique__PMF/docs
mkdir -p user support technical development deployment quality decisions archive archive/audits
```

### Step 2: Move Files to New Structure
- Execute moves as per consolidation map
- Update internal cross-references

### Step 3: Merge Duplicate Content
- Merge `DEPLOY_PRODUCTION.md` into `DEPLOYMENT_GUIDE.md`
- Merge PDF validators docs
- Consolidate production readiness reports

### Step 4: Resolve .claude/ vs .antigravity/
- Move ADRs to `docs/decisions/`
- Determine which rule versions are current
- Archive or delete `.claude/`

### Step 5: Archive Historical Documents
- Move all phase/audit reports to `docs/archive/`
- Clean up root directory

### Step 6: Update Documentation Index
- Create `docs/README.md`
- Update main `README.md` with link to docs

### Step 7: Verify Cross-References
- Scan all docs for broken links
- Update references to moved files

---

## Validation Criteria

✅ **No duplicate files**  
✅ **All active docs in logical directories**  
✅ **Clear separation of audience (user/dev/ops)**  
✅ **Historical docs archived, not deleted**  
✅ **All cross-references working**  
✅ **Documentation index complete**  
✅ **Clean root directory (< 5 .md files)**

---

## Next Phase

**Phase 3**: Factual Updates - Align all docs with actual code
