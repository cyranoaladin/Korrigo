# Security Checklist

## Audit de Sécurité Complet

Cette checklist doit être utilisée pour auditer la sécurité du projet.

**Fréquence** : Mensuelle + Avant chaque déploiement production

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
