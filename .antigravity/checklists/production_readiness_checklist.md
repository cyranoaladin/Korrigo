# Production Readiness Checklist

## Checklist Complète Avant Mise en Production

Cette checklist doit être **100% complète** avant tout déploiement en production.

---

## 1. Configuration Django

### Settings Production

- [ ] `DEBUG = False` (OBLIGATOIRE)
- [ ] `SECRET_KEY` depuis variable d'environnement
- [ ] `SECRET_KEY` >50 caractères, aléatoire
- [ ] `ALLOWED_HOSTS` défini explicitement
- [ ] `DATABASES` PostgreSQL configuré (pas SQLite)
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] `SECURE_HSTS_SECONDS = 31536000`
- [ ] `SECURE_CONTENT_TYPE_NOSNIFF = True`
- [ ] `X_FRAME_OPTIONS = 'DENY'`
- [ ] `CSRF_TRUSTED_ORIGINS` configuré
- [ ] `CORS` configuré strictement (pas de wildcard)

### Validation Settings

```python
# settings.py
if not os.environ.get('SECRET_KEY'):
    raise ValueError("SECRET_KEY must be set")

if DEBUG:
    raise ValueError("DEBUG must be False in production")

if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['*']:
    raise ValueError("ALLOWED_HOSTS must be explicitly set")
```

- [ ] Validation settings implémentée
- [ ] Application crash si config invalide

---

## 2. Base de Données

### Configuration

- [ ] PostgreSQL en production (version 13+)
- [ ] Credentials depuis env vars
- [ ] Connection pooling configuré (`conn_max_age=600`)
- [ ] Backup automatique configuré (quotidien minimum)
- [ ] Backup testé (restore fonctionnel)
- [ ] Rétention backup 30 jours minimum
- [ ] Monitoring DB actif (CPU, mem, disk, connections)

### Migrations

- [ ] Toutes les migrations appliquées
- [ ] Migrations testées en staging
- [ ] Pas de migration en attente
- [ ] `python manage.py showmigrations` propre
- [ ] Backup DB avant migration

---

## 3. Sécurité

### CRITIQUE (Blocage si non)

- [ ] Scan sécurité Bandit sans High severity
- [ ] Scan dependencies Safety sans vulnérabilités
- [ ] Pas de secrets en dur dans le code
- [ ] `.env` dans `.gitignore`
- [ ] Git history scanné (TruffleHog)
- [ ] Permissions explicites sur TOUS les endpoints
- [ ] Pas de `AllowAny` sur endpoints sensibles (ou justifié)
- [ ] Rate limiting actif
- [ ] CSRF protection active
- [ ] XSS prevention validée

### Authentification

- [ ] Login professeur fonctionnel
- [ ] Login élève fonctionnel
- [ ] Timeout sessions configuré (4h)
- [ ] Logout effectif (invalidation session)
- [ ] Permissions testées (prof, élève, admin)
- [ ] Escalade privilèges impossible (testé)

---

## 4. SSL/HTTPS

- [ ] Certificat SSL valide (Let's Encrypt ou autre)
- [ ] HTTPS forcé (redirect 80 → 443)
- [ ] Certificat expire dans >30 jours
- [ ] Renouvellement auto configuré (Certbot)
- [ ] HSTS configuré (31536000 secondes)
- [ ] TLS 1.2+ uniquement
- [ ] SSL Labs test A ou A+

Test:
```bash
curl -I https://viatique.example.com | grep -i strict-transport-security
```

---

## 5. Nginx Configuration

- [ ] Nginx seul exposé (ports 80, 443)
- [ ] Backend pas accessible directement
- [ ] Security headers configurés
- [ ] Client max body size 50M
- [ ] Timeouts appropriés (30-60s)
- [ ] Rate limiting actif
- [ ] Static files servis par Nginx
- [ ] Media files servis par Nginx
- [ ] Logs accessibles
- [ ] Gzip compression activée

Test:
```bash
curl -I https://viatique.example.com | grep -i "x-frame-options\|x-content-type\|strict-transport"
```

---

## 6. Static et Media Files

- [ ] `STATIC_URL` et `STATIC_ROOT` configurés
- [ ] `MEDIA_URL` et `MEDIA_ROOT` configurés
- [ ] `python manage.py collectstatic` exécuté
- [ ] Static files accessibles (CSS, JS)
- [ ] Media files accessibles (PDFs, images)
- [ ] Permissions fichiers correctes
- [ ] Cache headers configurés (longue durée pour static)

---

## 7. Celery et Redis

- [ ] Redis fonctionnel et accessible
- [ ] Celery worker démarré
- [ ] Celery beat démarré (si tasks périodiques)
- [ ] Tasks testées (process PDF, emails)
- [ ] Monitoring Celery actif
- [ ] Dead letter queue configurée
- [ ] Retry policy configurée
- [ ] Timeout tasks approprié

Test:
```bash
docker-compose exec backend celery -A core inspect active
docker-compose exec redis redis-cli ping
```

---

## 8. Email (si applicable)

- [ ] SMTP configuré (`EMAIL_HOST`, etc.)
- [ ] Credentials email depuis env vars
- [ ] Email de test envoyé et reçu
- [ ] Templates email fonctionnels
- [ ] SPF/DKIM configurés (si domain propre)
- [ ] Rate limiting envoi emails

---

## 9. Logging et Monitoring

### Logging

- [ ] Logs structurés (JSON)
- [ ] Niveau logs approprié (INFO/WARNING/ERROR)
- [ ] Pas de secrets dans logs
- [ ] Logs centralisés (stdout/stderr Docker)
- [ ] Rotation logs configurée
- [ ] Logs accessibles pour debug

### Monitoring

- [ ] Health check endpoint fonctionnel (`/health/`)
- [ ] Sentry ou équivalent configuré
- [ ] Alertes erreurs 500 configurées
- [ ] Métriques système (CPU, mem, disk)
- [ ] Uptime monitoring (UptimeRobot, Pingdom, etc.)
- [ ] Alertes email/Slack configurées

Test:
```bash
curl -f https://viatique.example.com/health/
```

---

## 10. Tests

### Tests Backend

- [ ] Tous les tests unitaires passent
- [ ] Tests d'intégration passent
- [ ] Tests de permissions passent
- [ ] Coverage >70% (code critique)
- [ ] Pas de tests skippés sans justification

```bash
pytest backend/ --cov --cov-report=term-missing
```

### Tests Frontend

- [ ] Tests unitaires passent
- [ ] Tests composants passent
- [ ] Pas d'erreurs console
- [ ] Build production réussit

```bash
npm run test
npm run build
```

### Tests E2E (si applicable)

- [ ] Workflow login professeur
- [ ] Workflow correction copie
- [ ] Workflow login élève
- [ ] Workflow visualisation copie élève

---

## 11. Performance

- [ ] Queries DB optimisées (pas de N+1)
- [ ] Select related / prefetch related utilisés
- [ ] Pagination configurée
- [ ] Celery pour tâches longues (>5s)
- [ ] Caching configuré (si applicable)
- [ ] Frontend lazy loading actif
- [ ] Images optimisées
- [ ] Bundle size raisonnable (<500kb)

Test:
```bash
# Backend
python manage.py debugsqlshell  # Analyser queries

# Frontend
npm run build --report  # Analyser bundle size
```

---

## 12. Backup et Recovery

- [ ] Backup DB automatique quotidien
- [ ] Backup media files régulier
- [ ] Backup testé (restore réussi)
- [ ] Rétention 30 jours minimum
- [ ] Backup hors site (offsite)
- [ ] Script restore documenté
- [ ] Recovery Time Objective (RTO) défini
- [ ] Recovery Point Objective (RPO) défini

Test:
```bash
# Backup
./backup.sh

# Restore test sur staging
./restore.sh backup_20260121.sql.gz
```

---

## 13. Documentation

- [ ] README à jour
- [ ] Architecture documentée (.claude/)
- [ ] Variables env documentées (.env.example)
- [ ] Procédure déploiement documentée
- [ ] Procédure rollback documentée
- [ ] Runbook incidents documenté
- [ ] Contact équipe technique défini
- [ ] Procédure backup/restore documentée

---

## 14. Infrastructure

### Docker

- [ ] Toutes les images buildent sans erreur
- [ ] Images utilisent users non-root
- [ ] Health checks containers configurés
- [ ] Restart policy `always` en production
- [ ] Volumes pour persistence
- [ ] Network isolation appropriée
- [ ] Docker compose prod testé

### Serveur

- [ ] Firewall configuré (seulement 80, 443, 22)
- [ ] SSH key-based auth (pas password)
- [ ] Fail2ban configuré
- [ ] Monitoring ressources (CPU, mem, disk)
- [ ] Alertes disk space low
- [ ] Auto-updates sécurité activées (ou planifiées)
- [ ] Backup serveur complet (si bare metal)

---

## 15. Workflows Métier Testés

### Workflow Correction

- [ ] Upload PDF examen
- [ ] Split et détection booklets
- [ ] Validation staging area
- [ ] Création copies
- [ ] Lock copie pour correction
- [ ] Ajout annotations
- [ ] Notation questions
- [ ] Finalisation correction
- [ ] Génération PDF final avec annotations
- [ ] PDF final accessible

### Workflow Élève

- [ ] Login élève (INE + code)
- [ ] Liste copies élève (GRADED uniquement)
- [ ] Visualisation PDF final avec annotations
- [ ] Consultation note et appréciation
- [ ] Pas d'accès copies autres élèves (testé)
- [ ] Logout

### Workflow Admin

- [ ] Accès Django Admin
- [ ] CRUD examens
- [ ] CRUD copies
- [ ] CRUD élèves
- [ ] Import élèves (CSV)
- [ ] Export notes (Pronote)

---

## 16. Compliance et Légal

- [ ] RGPD respecté (si UE)
- [ ] Privacy policy publiée
- [ ] Terms of service publiés
- [ ] Cookies consent (si cookies non essentiels)
- [ ] Conformité CNIL (France)
- [ ] Protection données élèves mineurs
- [ ] Accord établissement obtenu
- [ ] DPO désigné (si requis)

---

## 17. Smoke Tests Production

Après déploiement, tester manuellement :

### Backend

- [ ] `/health/` retourne 200
- [ ] `/admin/` accessible (login admin)
- [ ] `/api/` accessible (login prof)
- [ ] API retourne données valides

### Frontend

- [ ] Page d'accueil charge
- [ ] Login professeur fonctionne
- [ ] Dashboard accessible
- [ ] Login élève fonctionne
- [ ] Pas d'erreurs console
- [ ] CSS chargé correctement

### Workflows Critiques

- [ ] Créer examen test
- [ ] Créer copie test
- [ ] Annoter copie test
- [ ] Finaliser copie test
- [ ] Accès élève copie test
- [ ] Visualiser PDF final

---

## 18. Rollback Plan

- [ ] Procédure rollback documentée
- [ ] Backup DB récent (<24h)
- [ ] Git tag version stable précédente
- [ ] Procédure testée en staging
- [ ] Contacts équipe définis
- [ ] Fenêtre de rollback définie (<30 min)

---

## 19. Communication

### Pré-Déploiement

- [ ] Équipe technique notifiée
- [ ] Utilisateurs notifiés (si downtime)
- [ ] Fenêtre maintenance définie (si applicable)
- [ ] Status page mise à jour

### Post-Déploiement

- [ ] Équipe notifiée (succès)
- [ ] Utilisateurs notifiés (disponibilité)
- [ ] Changelog publié
- [ ] Documentation mise à jour

---

## 20. Checklist Rapide (Go/No-Go)

### BLOCKERS CRITIQUES (No-Go si Non)

- [ ] `DEBUG = False`
- [ ] `SECRET_KEY` sécurisé
- [ ] HTTPS actif et certificat valide
- [ ] Backup DB récent (<24h)
- [ ] Tous les tests passent
- [ ] Scan sécurité sans vulnérabilité critique
- [ ] Health check fonctionnel
- [ ] Smoke tests passent

### Si UN seul blocker : **NO-GO**

---

## 21. Post-Déploiement (J+1 à J+7)

- [ ] Monitoring quotidien (J+1 à J+3)
- [ ] Pas d'erreurs 500 non gérées
- [ ] Performance acceptable (temps réponse)
- [ ] Backup automatique fonctionne
- [ ] Alertes configurées fonctionnent
- [ ] Feedback utilisateurs collecté
- [ ] Hotfix appliqués si nécessaire

---

## Validation Finale

**Je certifie que** :
- [ ] Tous les items de cette checklist sont validés
- [ ] Aucun blocker critique non résolu
- [ ] Backup et rollback plan prêts
- [ ] Équipe technique informée et disponible
- [ ] Production ready à 100%

**Signé par** : _________________
**Date** : _________________
**Version** : _________________

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : OBLIGATOIRE avant production
