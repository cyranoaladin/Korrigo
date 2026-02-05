# Korrigo Production Readiness Checklist

## Metadata
- **Date**: 2026-02-02
- **Timestamp**: 2026-02-02_1408
- **Branch**: main (ONLY)
- **Target**: korrigo.labomaths.tn

---

## PRD Validation Table

| PRD | Description | Commands | Proofs | Commit | Status |
|-----|-------------|----------|--------|--------|--------|
| PRD-01 | Baseline + Checklist | `git pull --ff-only`, `git status` | `.antigravity/proofs/prd/2026-02-02_1408/PRD-01/` | - | PENDING |
| PRD-02 | Docker Compose prod config | `docker compose config` | `.antigravity/proofs/prd/2026-02-02_1408/PRD-02/` | - | PENDING |
| PRD-03 | Docker Compose local-prod config | `docker compose -f local-prod config` | `.antigravity/proofs/prd/2026-02-02_1408/PRD-03/` | - | PENDING |
| PRD-04 | Build images (no-cache) | `docker compose build --no-cache` | `.antigravity/proofs/prd/2026-02-02_1408/PRD-04/` | - | PENDING |
| PRD-05 | Boot stack + services healthy | `docker compose up -d`, `docker ps` | `.antigravity/proofs/prd/2026-02-02_1408/PRD-05/` | - | PENDING |
| PRD-06 | Migrations applied | `python manage.py migrate` | `.antigravity/proofs/prd/2026-02-02_1408/PRD-06/` | - | PENDING |
| PRD-07 | Collectstatic + nginx | `collectstatic`, nginx config | `.antigravity/proofs/prd/2026-02-02_1408/PRD-07/` | - | PENDING |
| PRD-08 | Seed deterministic + idempotent | `seed_e2e.py`, DB counts | `.antigravity/proofs/prd/2026-02-02_1408/PRD-08/` | - | PENDING |
| PRD-09 | Backend tests 100% pass | `pytest` | `.antigravity/proofs/prd/2026-02-02_1408/PRD-09/` | - | PENDING |
| PRD-10 | Frontend build prod | `npm run build` | `.antigravity/proofs/prd/2026-02-02_1408/PRD-10/` | - | PENDING |
| PRD-11 | Frontend lint/typecheck | `npm run lint` | `.antigravity/proofs/prd/2026-02-02_1408/PRD-11/` | - | PENDING |
| PRD-12 | E2E tests 100% pass | `npx playwright test` | `.antigravity/proofs/prd/2026-02-02_1408/PRD-12/` | - | PENDING |
| PRD-13 | Auth/Lockout TTL validation | Rate limit test | `.antigravity/proofs/prd/2026-02-02_1408/PRD-13/` | - | PENDING |
| PRD-14 | Workflow métier complet (A3 scan) | Upload + process + identify + correct | `.antigravity/proofs/prd/2026-02-02_1408/PRD-14/` | - | PENDING |
| PRD-15 | Restart resilience | `docker compose restart` | `.antigravity/proofs/prd/2026-02-02_1408/PRD-15/` | - | PENDING |
| PRD-16 | Security headers nginx | `curl -I` | `.antigravity/proofs/prd/2026-02-02_1408/PRD-16/` | - | PENDING |
| PRD-17 | Observability + no PII | Log grep | `.antigravity/proofs/prd/2026-02-02_1408/PRD-17/` | - | PENDING |
| PRD-18 | Runbook + Risk Register | File check | `.antigravity/proofs/prd/2026-02-02_1408/PRD-18/` | - | PENDING |
| PRD-19 | Gate final (fresh clone) | Full rebuild + retest | `.antigravity/proofs/prd/2026-02-02_1408/PRD-19/` | - | PENDING |

---

## PRD-A3: Scan A3 Recto/Verso - Critères d'Acceptation

### Contexte
Les scans A3 recto/verso contiennent 2 pages A4 côte à côte par page PDF:
- Page 1 du scan: P1 (gauche) + P4 (droite) - RECTO
- Page 2 du scan: P2 (gauche) + P3 (droite) - VERSO

### Critères d'Acceptation

| Critère | Mesure | Attendu | Réel | Status |
|---------|--------|---------|------|--------|
| Détection A3 automatique | Ratio largeur/hauteur > 1.2 | Oui | - | PENDING |
| Découpage A3 → 2×A4 | Nb pages A4 = 2 × nb pages A3 | - | - | PENDING |
| Reconstruction ordre livret | P1,P2,P3,P4 par copie | Correct | - | PENDING |
| Nb copies créées | Total pages A4 / 4 | - | - | PENDING |
| Pages par copie | 4 pages ordonnées | Correct | - | PENDING |
| Détection en-tête | HeaderDetector sur P1 | Oui | - | PENDING |
| Identification possible | Desk affiche copies | Oui | - | PENDING |

### Implémentation Requise

1. **ExamUploadView** (`backend/exams/views.py`):
   - Détecter si PDF contient des pages A3 (ratio > 1.2 ou dimensions)
   - Si A3: utiliser A3Splitter au lieu de PDFSplitter
   - Reconstruire l'ordre des pages par copie

2. **A3Splitter** (`backend/processing/services/splitter.py`):
   - Déjà implémenté pour découpage A3 → A4
   - Déjà implémenté pour détection recto/verso

3. **Tests**:
   - Test unitaire A3Splitter (existant)
   - Test intégration upload A3 (à ajouter)

---

## Commits Log

| Hash | Message | PRD Covered |
|------|---------|-------------|
| - | - | - |

---

## Notes

- Les fichiers PDF avec données élèves ne sont PAS commités
- Les preuves contiennent uniquement: hashes, compteurs, captures anonymisées
- PRD-19 doit être 100% vert avant déclaration "prod-ready"

---

*Last updated: 2026-02-02 14:08*
