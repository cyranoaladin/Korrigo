# Security Checklist

## Audit de Sécurité Complet

Cette checklist doit être utilisée pour auditer la sécurité du projet.

**Fréquence** : Mensuelle + Avant chaque déploiement production

---

## 0. Baseline Production (P0) - BLOQUANT

**Statut** : ✅ COMPLÉTÉ (2026-01-21)
**Référence** : `.claude/ETAPE_1_P0_BASELINE_SECURITY.md`

Cette section DOIT être validée à 100% avant tout déploiement ou développement de features.

### Settings Critiques

- [x] `SECRET_KEY` : Pas de fallback dangereux en production
  - ✅ `backend/core/settings.py:8-13` - Validation production obligatoire
  - ✅ Crash si `DJANGO_ENV=production` et `SECRET_KEY` non défini
  - ✅ Fallback dev uniquement (`django-insecure-dev-only-` + 50 chars)

- [x] `DEBUG` : Défaut sécurisé = `False`
  - ✅ `backend/core/settings.py:15` - Défaut `False`
  - ✅ Activation explicite requise (`DEBUG=true`)

- [x] `ALLOWED_HOSTS` : Pas de wildcard `*` en production
  - ✅ `backend/core/settings.py:17-20` - Défaut `localhost,127.0.0.1`
  - ✅ Crash si `*` en production (`DJANGO_ENV=production`)

### REST Framework - Default Deny

- [x] `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]`
  - ✅ `backend/core/settings.py:82-92` - Configuré
  - ❌ Plus de `AllowAny` par défaut

- [x] Tous les endpoints publics ont `permission_classes = [AllowAny]` explicite
  - ✅ `/api/auth/login/` - `core/views.py:10`
  - ✅ `/api/students/login/` - `students/views.py:10`
  - ✅ `/api/students/logout/` - `students/views.py:30`

- [x] Tous les autres endpoints ont permissions explicites
  - ✅ 13 endpoints protégés `[IsAuthenticated]` (Teacher/Admin)
  - ✅ 2 endpoints protégés `[IsStudent]` (Student only)
  - ✅ **Total : 18 endpoints, 100% avec permissions explicites**

### Cookies & Headers Sécurité

- [x] `SESSION_COOKIE_SECURE` : Conditionnel à `DEBUG` et `SSL_ENABLED`
  - ✅ Production SSL : `True`
  - ✅ Development : `False`
  - ✅ Pas de contradiction dans settings.py

- [x] `CSRF_COOKIE_SECURE` : Conditionnel à `DEBUG` et `SSL_ENABLED`
  - ✅ Production SSL : `True`
  - ✅ Development : `False`
  - ✅ Cohérent avec SESSION_COOKIE_SECURE

- [x] HSTS configuré en production (`SECURE_HSTS_SECONDS = 31536000`)
  - ✅ `backend/core/settings.py:39` - 1 an (31536000s)
  - ✅ `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
  - ✅ `SECURE_HSTS_PRELOAD = True`

- [x] Pas de contradiction entre blocs conditionnels
  - ✅ Structure if/else claire (lignes 33-60)
  - ✅ Aucun écrasement de valeurs

### Validation Déploiement

- [x] `python manage.py check --deploy` : 0 erreurs critiques
  - ✅ Exécuté : `docker-compose exec -T backend python manage.py check --deploy`
  - ✅ Résultat : 1 warning attendu (SECRET_KEY dev avec préfixe 'django-insecure-')
  - ✅ Environnement Docker : Tous conteneurs Up
  - 📅 Proof captured: 2026-01-21 10:30 UTC

- [x] Variables d'environnement production documentées
  - ✅ `DJANGO_ENV=production` (active validations)
  - ✅ `SECRET_KEY=<généré>` (obligatoire)
  - ✅ `DATABASE_URL=postgresql://...` (obligatoire)
  - ✅ `ALLOWED_HOSTS=domain.com` (obligatoire)
  - ✅ `DEBUG=False` (défaut sécurisé)
  - ✅ `SSL_ENABLED=True` (défaut sécurisé)

### Tests Fonctionnels

- [x] Test login professeur : ✅ Fonctionne
  - ✅ Testé : `POST /api/login/` (user: prof/test)
  - ✅ Résultat : HTTP 200 OK + {"message":"Login successful"}
  - ✅ Cookies : sessionid + csrftoken (SameSite=Lax)
  - 📅 Proof captured: 2026-01-21 10:31 UTC

- [x] Test login élève : ✅ Fonctionne
  - ✅ Testé : `POST /api/students/login/` (INE: 12345, Nom: DUPONT)
  - ✅ Résultat : HTTP 200 OK + {"message":"Login successful","role":"Student"}
  - ✅ Cookies : sessionid (HttpOnly, SameSite=Lax)
  - 📅 Proof captured: 2026-01-21 10:31 UTC

- [x] Test endpoint sans auth : ❌ Refusé (403)
  - ✅ Testé : `GET /api/exams/` sans cookie session
  - ✅ Résultat : HTTP 403 Forbidden
  - ✅ Message : {"detail":"Informations d'authentification non fournies."}
  - 📅 Proof captured: 2026-01-21 10:31 UTC

- [x] Test endpoint avec auth : ✅ Accessible
  - ✅ Testé : `GET /api/exams/` avec cookie prof
  - ✅ Résultat : HTTP 200 OK + liste vide (aucun exam créé)
  - ✅ Default Deny fonctionne : Sans auth → 403, Avec auth → 200
  - 📅 Proof captured: 2026-01-21 10:31 UTC

### Conformité Gouvernance

- [x] Règles `.claude/rules/01_security_rules.md` respectées
  - ✅ § 1.1.1 - Default Deny obligatoire
  - ✅ § 1.3 - Settings production validation
  - ✅ § 1.4 - Cookies secure conditionnels

- [x] Documentation mise à jour
  - ✅ `.claude/ETAPE_1_P0_BASELINE_SECURITY.md` créé
  - ✅ `.claude/rules/01_security_rules.md` enrichi (§ 1.3, 1.4)
  - ✅ `.claude/checklists/security_checklist.md` section P0 ajoutée

**🚨 BLOQUANT** : Aucune feature ne peut être développée tant que cette section n'est pas 100% validée.

---

## 0.5 Étape 2 - Pipeline PDF & Workflow Correction (Testé)

**Statut** : ✅ COMPLÉTÉ (2026-01-21)
**Référence** : `.claude/ETAPE_2_PDF_PIPELINE.md`

### Services Implémentés

- [x] PDFSplitter : Découpe PDF exam → booklets → pages PNG
  - ✅ Idempotent (skip si booklets existent)
  - ✅ Loggable (logger.info/debug/error)
  - ✅ DPI configurable (default 150)
  - 📅 Runtime proof: 2026-01-21 10:42 UTC

- [x] PDFFlattener (corrigé) : Copy → PDF annoté + scores
  - ✅ Sauvegarde copy.final_pdf
  - ✅ Mise à jour status=GRADED
  - 📅 Runtime proof: 2026-01-21 10:43 UTC

### Endpoints Testés

- [x] POST /api/exams/upload/ : Upload PDF + split auto
  - ✅ HTTP 201 + booklets_created=2
  - 📅 Runtime proof: 2026-01-21 10:42 UTC

- [x] GET /api/exams/ : Liste examens
  - ✅ HTTP 200 + count=1
  - 📅 Runtime proof: 2026-01-21 10:43 UTC

- [x] GET /api/exams/<exam_id>/booklets/ : Liste booklets
  - ✅ HTTP 200 + count=2 (pages 1-4, 5-8)
  - 📅 Runtime proof: 2026-01-21 10:43 UTC

- [x] GET /api/exams/<exam_id>/copies/ : Liste copies
  - ✅ HTTP 200 + count=2 (status=STAGING)
  - 📅 Runtime proof: 2026-01-21 10:43 UTC

- [x] POST /api/exams/<id>/export_all/ : Flatten toutes copies
  - ✅ HTTP 200 + "2 copies traitées"
  - 📅 Runtime proof: 2026-01-21 10:43 UTC

- [x] GET /api/exams/<id>/csv/ : Export CSV scores
  - ✅ HTTP 200 + CSV généré (AnonymousID,Total)
  - 📅 Runtime proof: 2026-01-21 10:44 UTC

### Invariants Validés

- [x] Idempotence : PDFSplitter skip si booklets existent
- [x] Déterminisme : PNG extraits avec DPI fixe, noms ordonnés
- [x] Pas de perte : booklet.pages_images stocke tous chemins
- [x] State Machine : Copies créées en STAGING (ADR-003)

### Migrations Appliquées

- [x] Migration 0004 : header_image et final_pdf → blank=True, null=True
  - ✅ Appliquée sans erreur
  - 📅 Applied: 2026-01-21 10:42 UTC

### Fichiers Générés (Smoke Test)

- [x] 8 PNG extraits : media/booklets/{exam_id}/{booklet_id}/page_XXX.png
- [x] 2 PDF finaux : media/copies/final/copy_{copy_id}_corrected.pdf
- [x] 1 CSV export : exam_{exam_id}_results.csv

**📌 Note** : Étape 2 complète, prête pour Étape 3 (Annotation frontend + grading workflow).

---

## 0.6 Étape 3 - Backend Annotation & Grading (Testé)

**Statut** : ✅ COMPLÉTÉ (2026-01-21)
**Référence** : `.claude/ETAPE_3_ANNOTATION_GRADING.md`

### Modèles Implémentés

- [x] Annotation (refactor complet ADR-002)
  - ✅ Coordonnées normalisées [0,1] : x, y, w, h
  - ✅ page_index (0-based) au lieu de page_number
  - ✅ content, type (enum), score_delta, created_by
  - ✅ Suppression vector_data et page_number
  - 📅 Migration 0002: 2026-01-21 11:04 UTC

- [x] GradingEvent (nouveau modèle audit log)
  - ✅ Actions: VALIDATE, LOCK, UNLOCK, GRADE, FINALIZE
  - ✅ Traçabilité: copy, actor, timestamp, metadata
  - 📅 Migration 0002: 2026-01-21 11:04 UTC

- [x] Score (supprimé - redondant avec score_delta)
  - ✅ Migration 0002: Suppression complète
  - 📅 Applied: 2026-01-21 11:04 UTC

- [x] Copy (traçabilité ajoutée)
  - ✅ validated_at, locked_at, locked_by, graded_at
  - 📅 Migration 0005: 2026-01-21 11:04 UTC

### Services Métier

- [x] AnnotationService
  - ✅ add_annotation(copy, payload, user) : READY uniquement
  - ✅ update_annotation() : READY uniquement
  - ✅ delete_annotation() : READY uniquement
  - ✅ list_annotations() : tous statuts
  - ✅ validate_coordinates([0,1]) : ADR-002
  - 📅 Runtime proof: 2026-01-21 11:06 UTC

- [x] GradingService
  - ✅ compute_score(copy) : somme score_delta
  - ✅ validate_copy() : STAGING → READY
  - ✅ lock_copy() : READY → LOCKED
  - ✅ unlock_copy() : LOCKED → READY
  - ✅ finalize_copy() : LOCKED → GRADED + PDF
  - 📅 Runtime proof: 2026-01-21 11:06 UTC

### Endpoints Testés (IsTeacherOrAdmin)

- [x] GET /api/copies/<copy_id>/annotations/
  - ✅ Liste annotations d'une copie
  - 📅 Proof captured: 2026-01-21 11:06 UTC

- [x] POST /api/copies/<copy_id>/annotations/
  - ✅ Crée annotation si READY → HTTP 201
  - ✅ Refus si STAGING/LOCKED/GRADED → HTTP 400
  - 📅 Proof captured: 2026-01-21 11:06 UTC

- [x] PATCH /api/annotations/<id>/
  - ✅ Modifie annotation si READY → HTTP 200
  - ✅ Refus si LOCKED/GRADED → HTTP 400
  - 📅 Proof captured: 2026-01-21 11:06 UTC

- [x] DELETE /api/annotations/<id>/
  - ✅ Supprime annotation si READY → HTTP 204
  - ✅ Refus si LOCKED/GRADED → HTTP 400
  - 📅 Proof captured: 2026-01-21 11:06 UTC

- [x] POST /api/copies/<id>/lock/
  - ✅ READY → LOCKED → HTTP 200
  - 📅 Proof captured: 2026-01-21 11:06 UTC

- [x] POST /api/copies/<id>/unlock/
  - ✅ LOCKED → READY → HTTP 200
  - 📅 Proof captured: 2026-01-21 11:06 UTC

- [x] POST /api/copies/<id>/finalize/
  - ✅ LOCKED → GRADED + PDF généré → HTTP 200
  - ✅ final_score calculé et retourné
  - 📅 Proof captured: 2026-01-21 11:06 UTC

### Permissions

- [x] IsTeacherOrAdmin (nouveau)
  - ✅ Appliqué sur TOUS les endpoints Étape 3
  - ✅ Vérifie: is_authenticated AND is_staff
  - ✅ Aucun accès élève
  - 📅 Tested: 2026-01-21 11:06 UTC

### Machine d'État (ADR-003)

- [x] STAGING → aucune annotation autorisée
  - ✅ Création refusée → HTTP 400
  - 📅 Test 2 passed: 2026-01-21 11:06 UTC

- [x] READY → annotations autorisées
  - ✅ Création/modification/suppression OK
  - 📅 Test 1, 5b passed: 2026-01-21 11:06 UTC

- [x] LOCKED → lecture seule
  - ✅ Modification refusée → HTTP 400
  - 📅 Test 4 passed: 2026-01-21 11:06 UTC

- [x] GRADED → lecture seule + immutable
  - ✅ Modification refusée → HTTP 400
  - 📅 Test 6b passed: 2026-01-21 11:06 UTC

### PDFFlattener Adapté (ADR-002)

- [x] Lecture annotations via x, y, w, h (au lieu de vector_data)
  - ✅ Dénormalisation: x_pdf = x * page_width
  - 📅 Tested: 2026-01-21 11:06 UTC

- [x] Utilisation page_index 0-based
  - ✅ Au lieu de page_number 1-based
  - 📅 Tested: 2026-01-21 11:06 UTC

- [x] Dessin annotations avec couleurs par type
  - ✅ COMMENT: Bleu, ERROR: Rouge, BONUS: Vert, HIGHLIGHT: Jaune
  - 📅 Tested: 2026-01-21 11:06 UTC

- [x] Page de synthèse avec score total
  - ✅ Détail par annotation + score_delta
  - ✅ Score total calculé
  - 📅 Tested: 2026-01-21 11:06 UTC

### Tests Runtime (6 OBLIGATOIRES)

**User**: admin (staff)
**Date**: 2026-01-21 11:06 UTC

- [x] Test 1: Créer annotation READY → 201 Created
- [x] Test 2: Créer annotation STAGING → 400 Bad Request
- [x] Test 3: Lock READY → 200 + status LOCKED
- [x] Test 4: Modifier LOCKED → 400 Bad Request
- [x] Test 5: Unlock + modifier → 200 OK
- [x] Test 6: Finalize + modifier GRADED → 400 Bad Request

**Résultat**: 6/6 tests passés ✅

### Invariants Validés

- [x] Coordonnées [0,1] : validation stricte avant création
- [x] Machine d'état : transitions strictes (ValueError si invalide)
- [x] LOCKED = lecture seule pour annotations
- [x] Traçabilité : GradingEvent créé à chaque transition
- [x] Atomicité : @transaction.atomic sur tous services
- [x] Permissions : IsTeacherOrAdmin sur tous endpoints

**📌 Note** : Étape 3 complète, backend annotation & grading fonctionnel. Prochaine étape selon cahier.

---

## 1. Authentification et Autorisation

### Django Backend

- [ ] `DEBUG = False` en production
- [ ] `SECRET_KEY` depuis variable d'environnement (pas hardcodé)
- [ ] `SECRET_KEY` suffisamment long (>50 caractères)
- [ ] `ALLOWED_HOSTS` explicitement défini (pas `['*']`)
- [ ] Permissions explicites sur TOUS les endpoints API
- [ ] Pas de `AllowAny` sur endpoints sensibles (ou justifié et documenté)
- [ ] Sessions/JWT sécurisés (HTTPS, secure cookies)
- [ ] Timeout sessions configuré (<=4h)
- [ ] Rate limiting actif sur login endpoints
- [ ] Brute force protection configurée

### Permissions Custom

- [ ] `IsProfessor` permission testée
- [ ] `IsStudent` permission testée
- [ ] `IsOwnerStudent` permission testée (élève voit uniquement ses copies)
- [ ] Permissions object-level implémentées où nécessaire
- [ ] Tests de permissions pour tous les endpoints critiques

### Accès Élève

- [ ] Élèves utilisent session custom (PAS Django User)
- [ ] Session élève contient uniquement `student_id`
- [ ] Timeout court (4h maximum)
- [ ] Accès READONLY uniquement
- [ ] Filtrage strict par `student_id` sur tous les endpoints
- [ ] Copies GRADED uniquement accessibles
- [ ] Pas d'accès aux copies d'autres élèves
- [ ] Pas d'énumération possible

---

## 2. Protection des Données

### Données Élèves

- [ ] Données élèves protégées par authentification
- [ ] Anonymat maintenu jusqu'à publication résultats
- [ ] `anonymous_id` non devinable (UUID ou équivalent)
- [ ] Traçabilité levée d'anonymat
- [ ] Pas d'exposition INE complet dans logs
- [ ] RGPD respecté (consentement, droit à l'oubli)

### Filtrage Données

- [ ] Queryset filtré par utilisateur dans ViewSets
- [ ] Pas d'énumération d'IDs possible
- [ ] UUIDs utilisés pour IDs publics
- [ ] Serializers n'exposent pas champs sensibles
- [ ] `read_only_fields` définis sur serializers

---

## 3. Validation des Entrées

### Backend

- [ ] Toutes les entrées utilisateur validées
- [ ] Serializers DRF utilisés pour validation
- [ ] Type checking sur tous les inputs
- [ ] Length limits respectés
- [ ] Sanitization avant stockage si HTML
- [ ] Pas de raw SQL (ORM Django utilisé)
- [ ] Parameterized queries si raw SQL nécessaire

### Frontend

- [ ] Validation côté client (UX)
- [ ] Validation côté serveur OBLIGATOIRE (sécurité)
- [ ] Pas de confiance en validation client
- [ ] XSS prevention (pas de `v-html` avec input utilisateur)
- [ ] DOMPurify utilisé si HTML nécessaire

### File Uploads

- [ ] Extension validée (`.pdf` uniquement pour examens)
- [ ] MIME type validé
- [ ] Taille limitée (50 MB)
- [ ] Scan antivirus si possible
- [ ] Fichiers stockés hors webroot
- [ ] Fichiers servis via Django (pas directement par Nginx)
- [ ] Pas d'exécution de fichiers uploadés

---

## 4. Configuration Sécurité Django

### HTTPS / SSL

- [ ] `SECURE_SSL_REDIRECT = True` (production)
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] `SECURE_HSTS_SECONDS = 31536000` (1 an)
- [ ] `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
- [ ] `SECURE_HSTS_PRELOAD = True`
- [ ] Certificat SSL valide (Let's Encrypt ou autre)
- [ ] Renouvellement auto certificat configuré

### Headers Sécurité

- [ ] `SECURE_CONTENT_TYPE_NOSNIFF = True`
- [ ] `SECURE_BROWSER_XSS_FILTER = True`
- [ ] `X_FRAME_OPTIONS = 'DENY'`
- [ ] CSP headers configurés (si applicable)

### CSRF / CORS

- [ ] CSRF protection activée
- [ ] `CSRF_COOKIE_SAMESITE = 'Strict'` ou `'Lax'`
- [ ] `CSRF_TRUSTED_ORIGINS` explicite
- [ ] CORS configuré strictement (pas `CORS_ALLOW_ALL_ORIGINS`)
- [ ] `CORS_ALLOWED_ORIGINS` liste blanche uniquement

---

## 5. Secrets et Configuration

### Secrets

- [ ] Aucun secret en dur dans le code
- [ ] Variables d'environnement pour tous les secrets
- [ ] `.env` dans `.gitignore`
- [ ] `.env.example` versionné (SANS valeurs réelles)
- [ ] Rotation secrets <90 jours
- [ ] Secrets production différents de dev/staging

### Scan Secrets

- [ ] `git-secrets` installé et configuré
- [ ] Scan du repo effectué (pas de secrets détectés)
- [ ] Pre-commit hooks configurés
- [ ] History Git scanné (TruffleHog ou équivalent)

---

## 6. Logging et Monitoring

### Logging

- [ ] Tentatives login loggées (succès + échec)
- [ ] Accès données sensibles loggé
- [ ] Modifications permissions loggées
- [ ] Pas de secrets dans logs (passwords, tokens, keys)
- [ ] Pas de données personnelles complètes dans logs
- [ ] Logs structurés (JSON)
- [ ] Niveau approprié (INFO en prod, DEBUG en dev)

### Monitoring

- [ ] Détection tentatives brute force
- [ ] Alertes sur accès interdits répétés
- [ ] Monitoring erreurs 403/401
- [ ] Sentry ou équivalent configuré
- [ ] Alertes email/Slack sur erreurs critiques

---

## 7. Database Sécurité

- [ ] PostgreSQL en production (pas SQLite)
- [ ] Credentials DB depuis env vars
- [ ] DB pas exposée publiquement
- [ ] Firewall DB configuré (whitelist IPs)
- [ ] Backup DB chiffrés
- [ ] Accès DB limité (principe moindre privilège)
- [ ] Migrations testées avant prod
- [ ] Backup avant migration destructive

---

## 8. Rate Limiting

- [ ] Rate limiting sur login (5 tentatives/15min)
- [ ] Rate limiting sur API publique (100 req/min par IP)
- [ ] Throttling utilisateurs authentifiés (1000 req/min)
- [ ] Rate limiting côté Nginx ET Django

---

## 9. Tests Sécurité

### Tests Automatisés

- [ ] Test escalade privilèges (élève → prof)
- [ ] Test accès sans authentification
- [ ] Test CSRF protection
- [ ] Test injection SQL
- [ ] Test XSS
- [ ] Test file upload validation
- [ ] Tests permissions tous les endpoints

### Scan Automatique

```bash
# Bandit (Python)
bandit -r backend/ -f json

# Safety (dependencies)
safety check

# OWASP ZAP
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://viatique.example.com
```

- [ ] Bandit scan sans High severity
- [ ] Safety check sans vulnérabilités
- [ ] OWASP ZAP scan effectué
- [ ] Vulnérabilités identifiées corrigées

---

## 10. Nginx Configuration

- [ ] Nginx seul exposé (backend pas accessible directement)
- [ ] HTTPS forcé (redirect 80 → 443)
- [ ] SSL/TLS moderne (TLS 1.2+)
- [ ] Ciphers sécurisés configurés
- [ ] Security headers Nginx configurés
- [ ] Client max body size limité
- [ ] Timeouts appropriés
- [ ] Rate limiting Nginx actif
- [ ] Logs Nginx accessibles

---

## 11. Docker Sécurité

- [ ] Images de base officielles et à jour
- [ ] Utilisateurs non-root dans containers
- [ ] Pas de code/secrets dans images Docker
- [ ] Volumes appropriés (pas de bind mount root)
- [ ] Network isolation entre services
- [ ] Secrets via Docker secrets ou env vars
- [ ] Images scannées (Trivy ou équivalent)

---

## 12. Code Review Sécurité

### Backend

- [ ] Pas de `eval()`, `exec()`
- [ ] Pas de `pickle.loads()` sur input utilisateur
- [ ] Pas de `os.system()` avec input utilisateur
- [ ] Pas de raw SQL avec f-strings
- [ ] Désérialization sécurisée (JSON, pas pickle)

### Frontend

- [ ] Pas de `eval()`
- [ ] Pas de `dangerouslySetInnerHTML` (équivalent React)
- [ ] Pas de `v-html` avec input utilisateur
- [ ] localStorage sécurisé (pas de secrets)
- [ ] Cookies avec flags appropriés (Secure, HttpOnly, SameSite)

---

## 13. Incident Response

- [ ] Plan de réponse incident documenté
- [ ] Contacts équipe sécurité définis
- [ ] Procédure rollback documentée
- [ ] Backup/restore testé
- [ ] Communication incident préparée

---

## 14. Compliance

### RGPD (si applicable)

- [ ] Consentement collecte données
- [ ] Droit à l'oubli implémenté
- [ ] Export données personnelles possible
- [ ] DPO désigné (si requis)
- [ ] Privacy policy publiée

### Éducation

- [ ] Conformité CNIL
- [ ] Protection données élèves mineurs
- [ ] Accord parental si <15 ans
- [ ] Politique de sécurité établissement respectée

---

## Checklist Rapide Pre-Deployment

**CRITIQUE - Blocage si Non**

- [ ] `DEBUG = False`
- [ ] `SECRET_KEY` depuis env
- [ ] `ALLOWED_HOSTS` explicite
- [ ] HTTPS activé
- [ ] Cookies sécurisés
- [ ] Pas de `AllowAny` sur endpoints sensibles
- [ ] Scan sécurité sans vulnérabilité critique
- [ ] Backup DB récent

---

## Actions en Cas de Faille Détectée

1. **Évaluer la gravité**
   - CRITIQUE : Fuite données, accès non autorisé
   - HAUTE : Escalade privilèges possible
   - MOYENNE : Validation manquante
   - BASSE : Configuration sous-optimale

2. **Actions immédiates (CRITIQUE/HAUTE)**
   - Rollback si en production
   - Isoler système compromis
   - Notifier équipe/responsables
   - Analyser logs (accès malveillants ?)
   - Rotation secrets si compromis

3. **Correction**
   - Fix et tests
   - Security review
   - Redéploiement
   - Documentation incident

4. **Post-mortem**
   - Analyse cause racine
   - Amélioration processus
   - Formation équipe si nécessaire

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : CRITIQUE - Audit obligatoire mensuel + avant production
