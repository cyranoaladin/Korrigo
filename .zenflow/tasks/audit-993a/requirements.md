# Audit de Production - Korrigo PMF
## Requirements Document (PRD)

**Date**: 27 janvier 2026  
**Auditeur**: Zenflow  
**Contexte**: Application de correction numérique d'examens pour environnement scolaire (AEFE/Éducation Nationale)  
**Criticité**: **MAXIMALE** - Données sensibles (notes élèves, conformité RGPD/CNIL)

---

## 1. Contexte et Objectifs

### 1.1 Nature de l'Application

**Korrigo PMF** est une plateforme de correction dématérialisée d'examens scannés permettant:
- Numérisation de copies A3 (scans massifs)
- Identification des copies via OCR assisté
- Correction numérique avec annotations vectorielles
- Export vers Pronote (notes/relevés)
- Consultation élève (portail dédié)

### 1.2 Enjeux Critiques

- **Données sensibles**: Notes élèves, informations personnelles (INE, noms)
- **Conformité**: RGPD/CNIL, traçabilité obligatoire
- **Intégrité**: Zéro tolérance aux erreurs de notation ou perte de données
- **Disponibilité**: Multi-utilisateurs (enseignants, administration, élèves)
- **Sécurité**: Séparation stricte des rôles (Admin/Teacher/Student)

### 1.3 Objectif de l'Audit

Conduire un **audit indépendant et exhaustif** pour valider la production readiness avec une approche de **tolérance zéro aux risques** compte tenu des enjeux académiques.

**Cet audit ne valide PAS les audits précédents** - il repart de zéro avec une grille d'évaluation stricte et méthodique.

---

## 2. Périmètre de l'Audit

### 2.1 Architecture & Workflows (Scope A)

#### A.1 Architecture Globale
- **Stack technique**: Django 4.2 + Vue.js 3 + PostgreSQL 15 + Redis + Celery
- **Conteneurisation**: Docker Compose (dev, prod, prodlike, e2e)
- **Infrastructure**: Nginx, Gunicorn, volumes persistants
- **Séparation**: Frontend SPA, Backend API REST, Workers asynchrones

**Points de vérification**:
- [ ] Configuration Docker isolée et sécurisée
- [ ] Volumes critiques identifiés et protégés (postgres_data, media_volume)
- [ ] Séparation réseau (backend interne, frontend exposé)
- [ ] Variables d'environnement sécurisées (secrets)

#### A.2 Flux Critiques
1. **Import copies**: Upload PDF → Split A3/A4 → Rasterization → Booklets
2. **Identification**: OCR assisté → Matching Student → Validation humaine → Copy.is_identified
3. **Correction**: Lock copy → Annotations → Autosave → Finalize → PDF flatten
4. **Verrouillage**: READY → LOCKED (CopyLock) → GRADED (release lock)
5. **Finalisation**: Calcul score → Génération PDF final → Export CSV Pronote
6. **Portail élève**: Login student → Liste copies GRADED → Download PDF final

**Points de vérification**:
- [ ] Machine à états Copy (STAGING → READY → LOCKED → GRADED) cohérente
- [ ] Transitions atomiques et sécurisées
- [ ] Rollback possible en cas d'erreur
- [ ] Traçabilité complète (GradingEvent)

#### A.3 Concurrence Multi-Enseignants
- **Verrous optimistes**: CopyLock avec token + expiration
- **Conflit resolution**: Premier arrivé = propriétaire du lock
- **Idempotence**: Retry safe pour toutes les opérations critiques
- **Cohérence transactionnelle**: `@transaction.atomic` sur services critiques

**Points de vérification**:
- [ ] Race conditions impossibles (tests de concurrence)
- [ ] Locks expirés nettoyés automatiquement
- [ ] Détection de locks volés/expirés côté client
- [ ] Transactions atomiques sur toutes les mutations multi-tables

---

### 2.2 Sécurité & Conformité (Scope B)

#### B.1 Authentification & Autorisation

**Modèle RBAC**:
- **Admin**: Accès complet (import, identification, exports, gestion utilisateurs)
- **Teacher**: Correction uniquement (copies, annotations, finalisation)
- **Student**: Lecture seule (ses propres copies GRADED)

**Mécanisme**:
- Session-based auth (Django sessions)
- Groups: `admin`, `teacher`, `student`
- Permissions: `IsAdmin`, `IsTeacher`, `IsStudent`, `IsAdminOrTeacher`

**Points de vérification**:
- [ ] Séparation stricte des endpoints par rôle
- [ ] Permissions par défaut: `IsAuthenticated` (deny by default)
- [ ] Object-level permissions (student ne voit que ses copies)
- [ ] Tests 403/404 exhaustifs pour tentatives d'accès illégitimes
- [ ] Session expiration configurée et sécurisée
- [ ] Rate limiting sur login (5 tentatives/15min)

#### B.2 OWASP Top 10

| Risque | Protection | Vérification |
|--------|------------|--------------|
| **A01 - Broken Access Control** | RBAC strict + object-level perms | Tests 403 systématiques |
| **A02 - Cryptographic Failures** | SECRET_KEY obligatoire, sessions httpOnly | Config prod guards |
| **A03 - Injection** | ORM Django (SQL safe), validation inputs | Aucun raw SQL, sanitization |
| **A04 - Insecure Design** | Machine à états, transactions atomiques | Architecture review |
| **A05 - Security Misconfiguration** | DEBUG=False, ALLOWED_HOSTS strict | Settings prod guards |
| **A06 - Vulnerable Components** | Dépendances à jour | Scan CVE |
| **A07 - Identification Failures** | Rate limiting, audit trail | Tests brute force |
| **A08 - Data Integrity Failures** | CSRF, validation fichiers | Tests upload malicieux |
| **A09 - Security Logging** | AuditLog + GradingEvent | Traçabilité complète |
| **A10 - SSRF** | Aucun fetch externe | Code review |

**Points de vérification**:
- [ ] Validation exhaustive des uploads PDF (extension, MIME, taille, intégrité PyMuPDF)
- [ ] Protection CSRF active et testée
- [ ] XSS impossible (pas de `v-html`, CSP stricte)
- [ ] IDOR impossible (queryset filtré par user/role)
- [ ] Logs ne contiennent pas de données sensibles

#### B.3 Configuration Production

**Settings critiques** (`backend/core/settings.py`):
```python
# Guards obligatoires
if DJANGO_ENV == "production":
    if DEBUG:
        raise ValueError("DEBUG must be False in production")
    if SECRET_KEY == default:
        raise ValueError("SECRET_KEY must be set")
    if "*" in ALLOWED_HOSTS:
        raise ValueError("ALLOWED_HOSTS cannot contain '*'")
    if not RATELIMIT_ENABLE and not E2E_TEST_MODE:
        raise ValueError("RATELIMIT_ENABLE cannot be False")
```

**Points de vérification**:
- [ ] Guards empêchent démarrage si config dangereuse
- [ ] SSL_ENABLED contrôle HTTPS strict (prod) vs HTTP (prodlike E2E)
- [ ] CORS origins explicites (pas de wildcard)
- [ ] CSP headers configurés (script-src, style-src, img-src)
- [ ] Session cookies: Secure, HttpOnly, SameSite=Lax

#### B.4 Traçabilité & Audit

**Modèles**:
- **AuditLog**: Authentification, accès données, actions système
- **GradingEvent**: Workflow correction (IMPORT, LOCK, FINALIZE, etc.)

**Points de vérification**:
- [ ] Tous les événements critiques loggés
- [ ] IP client capturée (get_client_ip)
- [ ] Rétention 12 mois minimum (conformité CNIL)
- [ ] Logs exploitables pour investigation
- [ ] Aucune donnée sensible en clair dans les logs

---

### 2.3 Robustesse & Fiabilité (Scope C)

#### C.1 Gestion des Erreurs

**Stratégie**:
- Exceptions métier explicites (ValueError, PermissionDenied)
- Retry logic sur opérations I/O (Celery tasks)
- Timeouts configurés (requests, Celery)
- Résilience aux échecs partiels

**Points de vérification**:
- [ ] Erreurs API retournent codes HTTP corrects (400/403/404/500)
- [ ] Messages d'erreur exploitables mais non verbeux (pas de stack trace en prod)
- [ ] Rollback automatique sur transactions échouées
- [ ] Retry configuré sur tâches Celery critiques

#### C.2 Traitements Lourds

**Pipelines critiques**:
1. **PDF Split**: Rasterization, extraction pages, détection headers
2. **PDF Flatten**: Overlays annotations sur PDF source
3. **Génération finale**: PDF + annotations + révélation identité élève

**Points de vérification**:
- [ ] Timeout configuré sur processing PDF (éviter blocage)
- [ ] Gestion mémoire (limite taille PDF: 50MB, 500 pages)
- [ ] Nettoyage fichiers temporaires
- [ ] Détection et gestion PDFs corrompus

#### C.3 Observabilité

**Logs**:
- Django logging configuré (WARNING en prod, DEBUG en dev)
- Celery logs persistants
- Nginx access/error logs

**Métriques**:
- Health check endpoint (`/api/health/`)
- Readiness/Liveness (si orchestrateur K8s)

**Points de vérification**:
- [ ] Logs structurés et exploitables
- [ ] Health check fonctionnel
- [ ] Pas de logs verbeux en production
- [ ] Métriques critiques disponibles (copies count, locks actifs)

#### C.4 Reprise Après Incident

**Scénarios**:
- Redémarrage brutal (crash container)
- Corruption base de données
- Perte volume media (PDF)

**Points de vérification**:
- [ ] Jobs Celery interrompus re-tryables
- [ ] Locks expirés auto-nettoyés au redémarrage
- [ ] Migrations DB réversibles
- [ ] Backup/restore testé et documenté

---

### 2.4 Tests & Preuves (Scope D)

#### D.1 Tests Backend (pytest)

**Existant**:
- 36 fichiers de tests backend
- Tests unitaires: grading, exams, identification
- Tests d'intégration: API endpoints
- Tests concurrence: CopyLock, transactions

**Points de vérification**:
- [ ] Tous les tests passent (`pytest -v`)
- [ ] Couverture critique ≥ 80% (services, views, permissions)
- [ ] Tests de sécurité (403, CSRF, rate limiting)
- [ ] Tests de concurrence (race conditions)
- [ ] Tests PDF validators (5 couches)

#### D.2 Tests Frontend (lint/typecheck)

**Existant**:
- 5 fichiers de tests frontend
- ESLint configuré
- TypeScript typechecking

**Points de vérification**:
- [ ] `npm run lint` passe sans erreur
- [ ] `npm run typecheck` passe sans erreur
- [ ] Pas de `any` abusifs, typage strict
- [ ] Pas de `v-html` (XSS risk)

#### D.3 Tests E2E (Playwright)

**Workflow "Gate 4"** (student portal):
1. Student login → Copies list → PDF download
2. Validation: Seules copies GRADED visibles
3. Validation: PDF final contient annotations

**Workflow "Teacher Correction"**:
1. Teacher login → Lock copy → Add annotations → Finalize
2. Validation: Lock concurrent impossible
3. Validation: PDF final généré avec annotations

**Workflow "Admin Identification"**:
1. Admin login → List booklets → Merge → Identify student
2. Validation: Copy transitions STAGING → READY
3. Validation: Anonymous_id généré

**Points de vérification**:
- [ ] Seed E2E déterministe (au moins 2 étudiants, copies variées)
- [ ] Tests passent en environnement propre (DB vierge)
- [ ] Retries configurés (2x, trace on failure)
- [ ] **Formulation canonique** si flaky local:
  > "E2E (Playwright): logic compliant (tests fixed + deterministic seed). Execution may be flaky on local runner; CI/container is the reference environment (retries=2, trace=on-first-retry)."

#### D.4 Conformité P0/P1 Précédente

**Vérifications** (ne pas régresser):
- [ ] CSV import fonctionnel (students)
- [ ] Settings guards actifs (DEBUG, SECRET_KEY, ALLOWED_HOSTS)
- [ ] Seed E2E déterministe (2+ students, graded/locked/ready copies)

---

### 2.5 Production Readiness & Exploitation (Scope E)

#### E.1 Docker Compose Production

**Configurations**:
- `docker-compose.yml`: Dev (hot reload, DEBUG=True)
- `docker-compose.prod.yml`: Prod (Gunicorn, Nginx, SSL)
- `docker-compose.prodlike.yml`: Tests prod-like (HTTP, E2E)
- `docker-compose.e2e.yml`: Tests E2E (minimal stack)

**Points de vérification**:
- [ ] Prod config valide et testable
- [ ] Nginx sert static/media correctement
- [ ] SSL configurable (SSL_ENABLED)
- [ ] Variables env sécurisées (pas de hardcoded secrets)
- [ ] Volumes persistants déclarés et documentés

#### E.2 Stratégie de Déploiement

**Migrations**:
- Migrations Django versionnées
- Compatibilité ascendante (rollback safe)

**Rollback**:
- Capacité à revenir version N-1 sans corruption

**Points de vérification**:
- [ ] Migrations testées (up + down)
- [ ] Pas de destructive migrations sans backup
- [ ] Documentation procédure de rollback

#### E.3 Performance

**Latences acceptables**:
- API endpoints: < 200ms (hors processing lourds)
- PDF split: < 30s pour 100 pages
- PDF flatten: < 10s par copie
- Page load frontend: < 2s

**Points de vérification**:
- [ ] Pas de N+1 queries (ORM optimize)
- [ ] Pagination active (PAGE_SIZE=50)
- [ ] Cache configuré (Redis)
- [ ] Indexes DB sur colonnes critiques (copy_id, student_id)

#### E.4 Contraintes "Zéro Surprise"

**Principes**:
- Démarrage strict si config dangereuse → CRASH explicite
- Messages d'erreur clairs et actionnables
- Aucun comportement silencieux en cas de problème

**Points de vérification**:
- [ ] Settings guards déclenchent ValueError explicites
- [ ] Logs erreur contiennent contexte suffisant
- [ ] Pas de fallback silencieux cachant des erreurs

---

## 3. Méthodologie d'Audit

### 3.1 Phase 1: Inventaire (1-2h)

**Actions**:
1. Lire documentation: `docs/ARCHITECTURE.md`, `BUSINESS_WORKFLOWS.md`, `DATABASE_SCHEMA.md`
2. Cartographier routes:
   - Backend: `backend/*/urls.py`, `core/urls.py`
   - Frontend: `frontend/src/router/index.ts`
3. Identifier modèles critiques: `Exam`, `Copy`, `Student`, `Annotation`, `GradingEvent`, `CopyLock`
4. Lister services: `grading/services.py`, `processing/services/`
5. Inventorier permissions: `*/permissions.py`, `core/auth.py`

**Livrables**:
- Cartographie des flux Gate 4 (student login → PDF final)
- Cartographie teacher correction workflow
- Cartographie admin identification workflow
- Liste risques potentiels par catégorie

### 3.2 Phase 2: Audit par Risque (3-4h)

**Grille de priorisation**:
- **P0** (Blocant prod): Fail-open security, perte de données, crash critique, corruption
- **P1** (Sérieux): Dégradations, edge-cases fréquents, manque observabilité
- **P2** (Amélioration): DX, refactor, dette technique

**Template item de risque**:
```markdown
### [P0/P1/P2] - [Titre court]

**Symptôme**: [Scénario d'échec réel]
**Cause**: [Diagnostic technique]
**Preuve**: [Fichier:ligne + extrait code]
**Impact**: [Conséquences prod]
**Correction**: [Patch minimal proposé]
**Test**: [Méthode de validation]
```

**Catégories**:
1. Sécurité (AuthN/AuthZ, injection, XSS, CSRF, IDOR)
2. Intégrité données (transactions, concurrence, corruption)
3. Disponibilité (performance, timeouts, crashes)
4. Conformité (RGPD, traçabilité, retention)
5. Opérationnalité (logs, monitoring, rollback)

### 3.3 Phase 3: Corrections (2-3h si nécessaire)

**Règles**:
- ⚠️ **JAMAIS dans un worktree** - Uniquement dans le dossier principal du repo
- Commits atomiques et explicites
- Messages de commit clairs (format: `[AUDIT] Category: description`)
- Tests de non-régression avant commit

**Process**:
1. Vérifier emplacement: `pwd` doit être `/home/alaeddine/viatique__PMF` (repo principal)
2. Appliquer patch minimal
3. Tester localement
4. Commit + push
5. Vérifier CI passe

### 3.4 Phase 4: Preuve de Production Readiness (1h)

**Production Readiness Gate**:

Checklist exécutable:
```bash
# 1. Backend tests
cd backend
source .venv/bin/activate
pytest -v --tb=short
# Attendu: ALL PASS

# 2. Lint & Typecheck
cd ../frontend
npm run lint
npm run typecheck
# Attendu: 0 errors

# 3. Migrations check
cd ../backend
python manage.py makemigrations --check --dry-run
# Attendu: No changes detected

# 4. Settings prod simulation
DJANGO_ENV=production DEBUG=False python -c "from core import settings"
# Attendu: No ValueError

# 5. E2E sanity
cd ../frontend
npm run test:e2e
# Attendu: PASS (ou formulation canonique si flaky)
```

**Verdict Go/No-Go**:
- ✅ **GO**: Tous les tests passent, aucun P0/P1 non résolu
- ❌ **NO-GO**: Au moins un P0 non résolu OU tests critiques échouent

---

## 4. Livrables Attendus

### 4.1 Rapport d'Audit (`audit-993a/report.md`)

**Structure**:
1. **Résumé exécutif** (1 page)
   - Verdict final (GO/NO-GO)
   - Score global (/100)
   - Risques majeurs (P0/P1)
   - Recommandations immédiates

2. **Cartographie des flux** (2-3 pages)
   - Diagrammes workflows critiques
   - Points de contrôle sécurité
   - Dépendances externes

3. **Table des risques** (3-5 pages)
   - Liste exhaustive P0/P1/P2
   - Preuves (fichier:ligne + code)
   - Corrections proposées
   - Statut (résolu/en attente)

4. **Correctifs appliqués** (1-2 pages si applicable)
   - Patch détaillé
   - Justification technique
   - Tests de validation

5. **Preuves de production readiness** (1 page)
   - Commandes exécutées
   - Résultats attendus vs obtenus
   - Screenshots/logs si pertinent

### 4.2 Plan d'Action Priorisé (`audit-993a/action_plan.md`)

Si des P0/P1 restent non résolus:
- Liste ordonnée par criticité
- Effort estimé (heures)
- Dépendances
- Owner recommandé

### 4.3 État Merge-Ready

**Fichiers modifiés**:
```bash
git status
git diff --stat
```

**Tests à lancer avant merge**:
```bash
# Commandes exactes à exécuter
pytest -v
npm run lint && npm run typecheck
```

---

## 5. Contraintes Non Négociables

### 5.1 Emplacement des Modifications

⚠️ **CRITIQUE**: Toute modification de code DOIT être effectuée dans le dossier principal du repo (`/home/alaeddine/viatique__PMF`), **JAMAIS** dans un worktree.

**Vérification avant toute édition**:
```bash
pwd
# Attendu: /home/alaeddine/viatique__PMF
git rev-parse --show-toplevel
# Attendu: /home/alaeddine/viatique__PMF
```

### 5.2 Niveau d'Exigence

- **Ce n'est PAS un MVP** → Application production réelle
- **Zéro tolérance** → Enjeux académiques élevés (notes, conformité)
- **Robustesse maximale** → Multi-utilisateurs, données sensibles
- **Production-ready** → Déployable immédiatement

### 5.3 Interdictions

- ❌ Ne jamais conclure "OK" sans preuves vérifiables
- ❌ Ne jamais réduire l'enjeu en mode MVP
- ❌ Ne jamais travailler dans un worktree
- ❌ Ne jamais skipper les tests de non-régression

---

## 6. Critères de Succès

### 6.1 Audit Considéré Complet Si

- [x] Tous les scopes (A/B/C/D/E) audités exhaustivement
- [x] Risques P0/P1/P2 documentés avec preuves
- [x] Corrections P0 appliquées (si faisables en <3h) OU plan d'action détaillé
- [x] Production Readiness Gate exécuté et documenté
- [x] Rapport structuré et exploitable livré

### 6.2 Verdict "Production Ready" Si

- [ ] Aucun P0 non résolu
- [ ] P1 documentés avec workaround acceptable OU corrigés
- [ ] Tous les tests backend passent
- [ ] Lint/typecheck frontend OK
- [ ] E2E passent OU formulation canonique documentée
- [ ] Settings prod guards actifs
- [ ] Documentation déploiement à jour

---

## 7. Références

### 7.1 Documentation Projet

- `docs/ARCHITECTURE.md`: Stack technique, infrastructure
- `docs/BUSINESS_WORKFLOWS.md`: Workflows métier, rôles
- `docs/DATABASE_SCHEMA.md`: Modèles, relations, contraintes
- `docs/PHASE3_QUALITY_AUDIT.md`: Audit précédent (référence)
- `docs/FINAL_100_PERCENT_REPORT.md`: État "100/100" précédent

### 7.2 Règles Gouvernance

- `.antigravity/rules/01_security_rules.md`: Règles sécurité
- `.antigravity/rules/02_backend_patterns.md`: Patterns backend
- `.antigravity/rules/03_frontend_patterns.md`: Patterns frontend
- `CHANGELOG.md`: Historique versions

### 7.3 Configuration Critique

- `backend/core/settings.py`: Configuration Django
- `.env.example`: Variables environnement
- `docker-compose.prod.yml`: Configuration production
- `backend/requirements.txt`: Dépendances Python

---

**Note Finale**: Cet audit est conduit avec le niveau de rigueur attendu pour un système de gestion de notes d'examens en environnement scolaire. La moindre faille de sécurité ou corruption de données est inacceptable.
