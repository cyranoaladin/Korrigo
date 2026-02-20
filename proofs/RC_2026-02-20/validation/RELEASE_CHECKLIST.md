# RELEASE CHECKLIST — RC_2026-02-20

## A. Pré-requis
- [x] Baseline collectée (proofs/baseline/*)
- [x] Secrets redacted (env/logs)
- [x] Dump DB réalisé + hash (proofs/backups/db_2026-02-20.dump — SHA256: d1ec1b10...)
- [x] Preuve de restauration (proofs/backups/restore_proof.txt — 213 copies match)

## B. Audit & plan
- [x] AUDIT_REPORT.md rédigé selon structure imposée
- [x] Risques identifiés + STOP conditions définies
- [x] Rollback écrit: git revert 421306e + redeploy overlay from backup

## C. Correctifs P0
- [x] P0-2 Rapports : DB→API→UI→Export cohérents (scores, remarks, appreciation, PDF tous présents)
  - Note: BB_J2 results_released_at=None — étudiants BB_J2 ne voient pas encore leurs copies (release admin requise)
- [x] P0-3 Stats : endpoint 200 OK (BB_J1 mean=13.49, BB_J2 mean=13.52) + auto-affichage dès graded>0
- [x] P0-4 "Locked" : supprimé UI + backend + routes (commit 9fbdfe9). 0 CopyLock, 0 LOCKED. Compat OK.
- [x] P0-5 Francisation : 21 chaînes anglaises traduites (grading/views.py, exams/views.py, students/views.py)
- [x] P0-6 RBAC : refus backend prouvé (curl: 403 student→teacher, 401 teacher→student)

## D. Tests
- [x] E2E tests pass: 17/18 (T6 GRADING_FAILED expected — test copy sans pages)
- [x] RBAC proofs sauvegardés (validation/p0-6_*.txt)
- [x] Francisation vérifiée par inspection source (T10-T12)
- [x] Entity counts inchangés post-deploy (T17: 213/544/105/1075/220)
- [x] Zero orphan records (T18)

## E. Déploiement
- [x] Commit SHA: 421306e (fix(RC): P0-2/P0-3/P0-5)
- [x] Commit SHA: 9fbdfe9 (refactor: suppression Locked)
- [x] Backend déployé via overlay (grading/views.py, exams/views.py, students/views.py, services.py, urls.py, views_draft.py)
- [x] Frontend build + deploy to nginx
- [x] docker-backend-1 + docker-celery-1 recreated (healthy)
- [x] DB cleanup: 0 CopyLock rows, 0 LOCKED copies, audit events préservés (2221)

## F. Décision
- [x] **GO PROD** — Tous les P0 couverts, tests passent, données intactes
