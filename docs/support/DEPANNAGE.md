# Guide de Dépannage - Korrigo PMF

> **Version**: 1.1.0  
> **Date**: 10 Mars 2026  
> **Public**: Administrateurs techniques, Support IT  
> **Langue**: Français (technique)

Guide de résolution des problèmes techniques pour la plateforme Korrigo PMF.

---

## 📋 Table des Matières

1. [Procédures de Diagnostic](#procédures-de-diagnostic)
2. [Problèmes Courants](#problèmes-courants)
3. [Problèmes d'Authentification](#problèmes-dauthentification)
4. [Problèmes de Traitement PDF](#problèmes-de-traitement-pdf)
5. [Problèmes de Correction](#problèmes-de-correction)
6. [Problèmes de Performance](#problèmes-de-performance)
7. [Problèmes de Données](#problèmes-de-données)
8. [Procédures d'Urgence](#procédures-durgence)

---

## Procédures de Diagnostic

### Vérification de l'État du Système

**Health Check Complet** :
```bash
# Se connecter au serveur
ssh admin@serveur-korrigo
cd /opt/korrigo

# Vérifier l'état des conteneurs
docker-compose ps

# Tous les services doivent afficher "Up"
# Si un service est "Exit" ou "Restarting", il y a un problème
```

**Résultat attendu** :
```
NAME                SERVICE    STATUS       PORTS
korrigo-backend     backend    Up 2 hours   0.0.0.0:8000->8000/tcp
korrigo-frontend    frontend   Up 2 hours   0.0.0.0:8080->8080/tcp
korrigo-db          db         Up 2 hours   5432/tcp
korrigo-redis       redis      Up 2 hours   6379/tcp
korrigo-celery      celery     Up 2 hours   
korrigo-nginx       nginx      Up 2 hours   0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

### Analyse des Logs

**Logs en temps réel** :
```bash
# Tous les services
docker-compose logs -f

# Service spécifique
docker-compose logs -f backend
docker-compose logs -f celery
docker-compose logs -f db

# Avec limite de lignes
docker-compose logs --tail=100 backend
```

**Recherche d'erreurs** :
```bash
# Erreurs backend (dernières 24h)
docker-compose logs --since 24h backend | grep -i error

# Erreurs Django
docker-compose logs --since 1h backend | grep -i "exception\|traceback\|error"

# Erreurs Celery
docker-compose logs --since 1h celery | grep -i "failed\|error\|exception"
```

### Vérification des Services

**PostgreSQL** :
```bash
# Connexion à la base de données
docker-compose exec db psql -U postgres -d korrigo

# Vérifier les connexions actives
SELECT count(*) FROM pg_stat_activity;

# Taille de la base
SELECT pg_size_pretty(pg_database_size('korrigo'));

# Tables principales
\dt

# Quitter
\q
```

**Redis** :
```bash
# Connexion Redis CLI
docker-compose exec redis redis-cli

# Test de fonctionnement
PING
# Doit retourner: PONG

# Statistiques
INFO stats

# Nombre de clés
DBSIZE

# Mémoire utilisée
INFO memory

# Quitter
exit
```

**Celery** :
```bash
# Workers actifs
docker-compose exec backend celery -A backend inspect active

# Workers enregistrés
docker-compose exec backend celery -A backend inspect registered

# Tasks en attente
docker-compose exec backend celery -A backend inspect reserved

# Statistiques
docker-compose exec backend celery -A backend inspect stats
```

### Vérification Réseau

**Connectivité** :
```bash
# Depuis le serveur
curl -I http://localhost:8088

# Depuis le backend vers la DB
docker-compose exec backend nc -zv db 5432

# Depuis le backend vers Redis
docker-compose exec backend nc -zv redis 6379

# DNS
docker-compose exec backend nslookup google.com
```

### Utilisation des Ressources

**Ressources Docker** :
```bash
# Vue d'ensemble
docker stats --no-stream

# CPU et mémoire par conteneur
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Espace disque
docker system df
```

**Ressources système** :
```bash
# CPU
top -bn1 | head -20

# Mémoire
free -h

# Disque
df -h

# Inodes (parfois le problème n'est pas l'espace mais le nombre de fichiers)
df -i
```

---

## Problèmes Courants

### Problème : Les services ne démarrent pas

**Symptômes** :
- `docker-compose up` échoue
- Un ou plusieurs conteneurs en status "Exit"

**Diagnostic** :
```bash
# Voir les logs de démarrage
docker-compose logs backend
docker-compose logs db
```

**Causes et Solutions** :

#### 1. Port déjà utilisé
**Erreur** : `Bind for 0.0.0.0:8080 failed: port is already allocated`

**Solution** :
```bash
# Identifier le processus utilisant le port
sudo lsof -i :8080

# Tuer le processus
sudo kill -9 <PID>

# Ou changer le port dans docker-compose.yml
```

#### 2. Problème de permissions
**Erreur** : `Permission denied` dans les logs

**Solution** :
```bash
# Vérifier les permissions des volumes
ls -la /opt/korrigo/media
ls -la /opt/korrigo/staticfiles

# Corriger les permissions
sudo chown -R 1000:1000 /opt/korrigo/media
sudo chown -R 1000:1000 /opt/korrigo/staticfiles
```

#### 3. Mémoire insuffisante
**Erreur** : `Cannot allocate memory`

**Solution** :
```bash
# Vérifier la mémoire disponible
free -h

# Arrêter les services non essentiels
sudo systemctl stop <service>

# Ou augmenter la RAM du serveur
```

#### 4. Base de données non initialisée
**Erreur** : `database "korrigo" does not exist`

**Solution** :
```bash
# Créer la base
docker-compose exec db psql -U postgres -c "CREATE DATABASE korrigo;"

# Appliquer les migrations
docker-compose exec backend python manage.py migrate
```

### Problème : Erreur de connexion à la base de données

**Symptômes** :
- Message : "OperationalError: could not connect to server"
- Backend ne démarre pas

**Diagnostic** :
```bash
# Vérifier que PostgreSQL est up
docker-compose ps db

# Vérifier les logs PostgreSQL
docker-compose logs db | tail -50
```

**Solutions** :

#### 1. PostgreSQL n'est pas démarré
```bash
# Redémarrer
docker-compose restart db

# Vérifier
docker-compose ps db
```

#### 2. Mauvaises credentials
**Vérifier** `.env` :
```bash
cat .env | grep DB
```

**Doit contenir** :
```env
DB_NAME=korrigo
DB_USER=postgres
DB_PASSWORD=<votre_password>
DB_HOST=db
DB_PORT=5432
```

#### 3. Base de données corrompue
```bash
# Restaurer depuis backup
docker-compose exec backend python manage.py restore_backup /backups/latest.sql.gz

# Ou recréer (⚠️ perte de données)
docker-compose down -v
docker-compose up -d
docker-compose exec backend python manage.py migrate
```

### Problème : Redis connection refused

**Symptômes** :
- Backend logs : "Error connecting to Redis"
- Celery ne démarre pas

**Diagnostic** :
```bash
# Vérifier Redis
docker-compose ps redis
docker-compose logs redis

# Tester la connexion
docker-compose exec backend python -c "import redis; r=redis.Redis(host='redis', port=6379); print(r.ping())"
```

**Solutions** :

#### 1. Redis n'est pas démarré
```bash
docker-compose restart redis
```

#### 2. Mémoire Redis pleine
```bash
# Vérifier
docker-compose exec redis redis-cli INFO memory

# Vider (⚠️ perd toutes les tasks en cache)
docker-compose exec redis redis-cli FLUSHALL

# Ou augmenter la limite dans docker-compose.yml
```

#### 3. Configuration réseau
**Vérifier** `backend/settings.py` :
```python
CELERY_BROKER_URL = 'redis://redis:6379/0'
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
    }
}
```

### Problème : Celery tasks ne s'exécutent pas

**Symptômes** :
- PDF uploads ne sont pas traités
- Rasterization bloquée
- Tasks en status "PENDING" indéfiniment

**Diagnostic** :
```bash
# Vérifier les workers Celery
docker-compose exec backend celery -A backend inspect active

# Vérifier les tasks en attente
docker-compose exec redis redis-cli LLEN celery

# Logs Celery
docker-compose logs celery | tail -100
```

**Solutions** :

#### 1. Worker Celery arrêté
```bash
# Redémarrer
docker-compose restart celery

# Vérifier
docker-compose logs celery | grep -i "ready"
```

#### 2. Worker bloqué sur une task
**Symptôme** : Une task prend des heures

**Solution** :
```bash
# Identifier la task bloquée
docker-compose exec backend celery -A backend inspect active

# Tuer le worker
docker-compose kill celery

# Relancer
docker-compose up -d celery

# Purger les tasks corrompues
docker-compose exec backend celery -A backend purge
```

#### 3. Trop de tasks en attente
```bash
# Nombre de tasks
docker-compose exec redis redis-cli LLEN celery

# Augmenter le nombre de workers
# Modifier docker-compose.yml:
#   celery:
#     command: celery -A backend worker -l info --concurrency=8
```

### Problème : Migrations échouent

**Symptômes** :
- `python manage.py migrate` retourne une erreur
- Système inutilisable après mise à jour

**Diagnostic** :
```bash
# Voir les migrations appliquées
docker-compose exec backend python manage.py showmigrations

# Voir l'historique
docker-compose exec backend python manage.py showmigrations --plan
```

**Solutions** :

#### 1. Migration dépendante manquante
**Erreur** : `Migration dependencies not satisfied`

**Solution** :
```bash
# Identifier la dépendance
docker-compose exec backend python manage.py migrate --plan

# Appliquer manuellement l'ordre
docker-compose exec backend python manage.py migrate <app_name> <migration_number>
```

#### 2. Conflit de migration
**Erreur** : `Conflicting migrations detected`

**Solution** :
```bash
# Merger les migrations
docker-compose exec backend python manage.py makemigrations --merge

# Puis appliquer
docker-compose exec backend python manage.py migrate
```

#### 3. Rollback nécessaire
```bash
# Annuler la dernière migration
docker-compose exec backend python manage.py migrate <app_name> <previous_migration_name>

# Exemple
docker-compose exec backend python manage.py migrate exams 0012_previous_migration
```

#### 4. Restauration complète
**Si tout échoue** :
```bash
# 1. Sauvegarder les données (export CSV)
docker-compose exec backend python manage.py dumpdata > backup.json

# 2. Restaurer backup DB avant migration
docker-compose exec backend python manage.py restore_backup /backups/<date>.sql.gz

# 3. Ne pas appliquer la migration problématique (rester sur ancienne version)
```

---

## Problèmes d'Authentification

### Problème : Impossible de se connecter

**Symptômes** :
- Credentials corrects mais connexion refusée
- Message : "Invalid username or password"

**Diagnostic** :
```bash
# Vérifier que l'utilisateur existe
docker-compose exec backend python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.filter(username='teacher1').exists()
True
>>> u = User.objects.get(username='teacher1')
>>> u.is_active
True
```

**Solutions** :

#### 1. Compte désactivé
```python
# Django shell
>>> u.is_active = True
>>> u.save()
```

#### 2. Mot de passe oublié/incorrect
```bash
# Réinitialiser le mot de passe
docker-compose exec backend python manage.py changepassword <username>
```

#### 3. Session corrompue
```bash
# Côté client : Vider les cookies du navigateur
# Ou côté serveur : Vider les sessions
docker-compose exec backend python manage.py clearsessions
```

### Problème : Élèves ne peuvent pas se connecter sur mobile

**Symptômes** :
- Message "Trop de tentatives de connexion" sur mobile (4G, WiFi école)
- Plusieurs élèves bloqués simultanément

**Cause** :
Les élèves sur le même réseau (WiFi école, opérateur mobile) partagent la même adresse IP publique (NAT). Le rate limiter compte toutes les tentatives de tous les élèves comme provenant d'une seule source.

**Limites actuelles** :
- `/api/students/login/` : 30 tentatives / 15 minutes par IP
- Réponse HTTP 429 avec message français clair

**Solutions** :

#### 1. Attente
- Le rate limit se réinitialise automatiquement après **15 minutes**
- Demandez aux élèves de patienter et réessayer

#### 2. Vérification
```bash
# Vérifier les logs backend pour le rate limiting
docker-compose logs backend | grep -i "rate_limited\|429\|limited"

# Vérifier l'IP source
docker-compose logs nginx | grep "students/login" | tail -20
```

#### 3. Désactivation temporaire (urgence uniquement)
```python
# Dans settings.py (NE PAS LAISSER EN PRODUCTION)
RATELIMIT_ENABLE = False  # Désactive tout rate limiting
```

> ⚠️ **Important** : Toujours réactiver le rate limiting après l'urgence.

---

### Problème : Erreur CSRF token

**Symptômes** :
- POST requests échouent avec "CSRF verification failed"
- Frontend affiche une erreur 403

**Diagnostic** :
```bash
# Vérifier les logs backend
docker-compose logs backend | grep -i csrf

# Vérifier la configuration CORS
docker-compose exec backend python manage.py shell
>>> from django.conf import settings
>>> settings.CSRF_TRUSTED_ORIGINS
```

**Solutions** :

#### 1. Mauvaise configuration CORS
**Vérifier** `backend/settings.py` :
```python
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8088',
    'http://127.0.0.1:8088',
    'https://korrigo.example.com',
]

CORS_ALLOWED_ORIGINS = [
    'http://localhost:8088',
    'https://korrigo.example.com',
]

CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False  # Important pour axios
```

#### 2. Cookies bloqués
**Côté client** :
- Vérifier que les cookies sont activés
- Vérifier que le domaine frontend = domaine backend (ou CORS bien configuré)

#### 3. Proxy/Load balancer
**Si derrière un proxy** :
```python
# settings.py
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
```

### Problème : Permission denied

**Symptômes** :
- Utilisateur authentifié mais ne peut pas accéder à une ressource
- Message : "You do not have permission to perform this action"

**Diagnostic** :
```bash
# Vérifier les permissions de l'utilisateur
docker-compose exec backend python manage.py shell
>>> from django.contrib.auth.models import User
>>> u = User.objects.get(username='teacher1')
>>> u.groups.all()
>>> u.user_permissions.all()
```

**Solutions** :

#### 1. Mauvais rôle
```python
# Assigner le bon groupe
>>> from django.contrib.auth.models import Group
>>> teacher_group = Group.objects.get(name='Teacher')
>>> u.groups.add(teacher_group)
```

#### 2. Vérifier les permissions API
**Consulter** `docs/SECURITY_PERMISSIONS_INVENTORY.md` pour les permissions requises par endpoint.

---

## Problèmes de Traitement PDF

### Problème : Upload de PDF échoue

**Symptômes** :
- Upload reste bloqué à "Uploading..."
- Erreur 413 ou 500

**Diagnostic** :
```bash
# Vérifier les logs nginx
docker-compose logs nginx | grep -i "413\|error"

# Vérifier les logs backend
docker-compose logs backend | grep -i "upload"
```

**Solutions** :

#### 1. Fichier trop volumineux
**Erreur** : 413 Request Entity Too Large

**Solution** - Augmenter les limites :

**nginx.conf** :
```nginx
client_max_body_size 100M;
```

**Django settings.py** :
```python
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600
```

**Redémarrer** :
```bash
docker-compose restart nginx backend
```

#### 2. Timeout
**Erreur** : Gateway Timeout (504)

**Solution** - Augmenter les timeouts :

**nginx.conf** :
```nginx
proxy_read_timeout 300s;
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
```

#### 3. Espace disque insuffisant
```bash
# Vérifier l'espace
df -h /opt/korrigo/media

# Nettoyer les fichiers temporaires
docker-compose exec backend python manage.py cleanup_temp_files
```

### Problème : Rasterization PDF bloquée

**Symptômes** :
- Task `rasterize_exam` en status STARTED depuis des heures
- PDF uploadé mais pas de booklets générés

**Diagnostic** :
```bash
# Vérifier les tasks Celery
docker-compose exec backend celery -A backend inspect active

# Logs Celery
docker-compose logs celery | grep -i "rasterize"

# Vérifier les ressources
docker stats celery
```

**Solutions** :

#### 1. PDF corrompu ou trop complexe
```bash
# Tester manuellement
docker-compose exec backend python manage.py shell
>>> from backend.exams.tasks import rasterize_exam
>>> rasterize_exam('<exam_id>')
# Observer les erreurs
```

**Solution** : Recréer le PDF avec une compression plus agressive ou découper en plusieurs fichiers.

#### 2. Mémoire insuffisante
**Symptôme** : `MemoryError` dans les logs

**Solution** :
```yaml
# docker-compose.yml - Augmenter la mémoire du worker
celery:
  deploy:
    resources:
      limits:
        memory: 4G
```

#### 3. Worker bloqué
```bash
# Tuer et relancer
docker-compose kill celery
docker-compose up -d celery

# Relancer la task manuellement
docker-compose exec backend python manage.py retry_failed_tasks
```

### Problème : OCR ne fonctionne pas

**Symptômes** :
- Identification ne suggère aucun nom
- Erreur lors de l'OCR

**Diagnostic** :
```bash
# Vérifier Tesseract
docker-compose exec backend tesseract --version

# Tester OCR manuellement
docker-compose exec backend python manage.py shell
>>> from backend.copies.ocr import extract_text_from_image
>>> extract_text_from_image('/path/to/test/image.jpg')
```

**Solutions** :

#### 1. Tesseract non installé
```bash
# Vérifier le Dockerfile backend
# Doit contenir:
RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-fra

# Reconstruire l'image
docker-compose build backend
```

#### 2. Mauvaise qualité de scan
**Symptôme** : OCR retourne du charabia

**Solutions** :
- Rescanner avec une résolution plus haute (300 DPI minimum)
- Vérifier le contraste
- Utiliser identification manuelle pour ce lot

#### 3. Zone OCR mal configurée
**Vérifier** `backend/copies/ocr.py` - Coordonnées de la zone d'en-tête :
```python
# Ajuster les coordonnées selon le template utilisé
HEADER_BBOX = (50, 50, 500, 150)  # (x1, y1, x2, y2)
```

### Problème : Booklet detection rate faible

**Symptômes** :
- Découpage A3→A4 crée trop ou pas assez de booklets
- Pages dans le mauvais ordre

**Diagnostic** :
```bash
# Vérifier les paramètres de découpage
docker-compose exec backend python manage.py shell
>>> from backend.exams.models import Exam
>>> exam = Exam.objects.get(id='<exam_id>')
>>> exam.split_config
```

**Solutions** :

#### 1. Mauvaise détection de format
**Modifier** la configuration de découpage :
```python
# Admin interface > Exam > Split Config
{
  "mode": "A3_to_A4",  # ou "A4_single", "custom"
  "pages_per_booklet": 4,
  "split_horizontal": true
}
```

#### 2. Découpage manuel
```bash
# Utiliser l'outil de découpage manuel
docker-compose exec backend python manage.py manual_split_exam <exam_id>
```

---

## Problèmes de Correction

### Problème : Impossible de verrouiller une copie

**Symptômes** :
- Bouton "Verrouiller" ne fonctionne pas
- Message : "Copy already locked"

**Diagnostic** :
```bash
# Vérifier le statut de la copie
docker-compose exec backend python manage.py shell
>>> from backend.copies.models import Copy
>>> copy = Copy.objects.get(id='<copy_id>')
>>> copy.status
'LOCKED'
>>> copy.locked_by
<User: teacher1>
>>> copy.locked_at
datetime.datetime(2026, 1, 30, 10, 30, 0)
```

**Solutions** :

#### 1. Lock expiré non libéré
```python
# Forcer le déverrouillage
>>> copy.status = 'READY'
>>> copy.locked_by = None
>>> copy.locked_at = None
>>> copy.save()
```

**Ou via commande** :
```bash
docker-compose exec backend python manage.py unlock_expired_copies
```

#### 2. Lock par un autre enseignant (encore actif)
**Contactez l'enseignant** ou attendez l'expiration (30 minutes).

**Forcer le déverrouillage (admin uniquement)** :
```bash
docker-compose exec backend python manage.py force_unlock_copy <copy_id>
```

### Problème : Annotations ne se sauvegardent pas

**Symptômes** :
- Annotations disparaissent après rafraîchissement
- Icône "Saving..." reste rouge

**Diagnostic** :
```javascript
// Console navigateur (F12)
// Vérifier les erreurs réseau
// Onglet Network > Filtrer par "annotations"
```

**Solutions** :

#### 1. Problème réseau/CORS
**Vérifier** les headers CORS (voir section CSRF ci-dessus)

#### 2. Serialization error côté backend
```bash
# Logs backend
docker-compose logs backend | grep -i "annotation"

# Si erreur de validation, vérifier les données envoyées
```

#### 3. Session expirée
**Solution** : Reconnexion de l'utilisateur

#### 4. Base de données pleine
```bash
# Vérifier l'espace disque
df -h

# Vérifier la taille de la DB
docker-compose exec db psql -U postgres -d korrigo -c "SELECT pg_size_pretty(pg_database_size('korrigo'));"
```

### Problème : Finalisation de copie échoue

**Symptômes** :
- Bouton "Finaliser" ne fonctionne pas
- Erreur lors de la génération du PDF final

**Diagnostic** :
```bash
# Logs backend
docker-compose logs backend | grep -i "finalize\|generate_pdf"

# Vérifier les tasks Celery
docker-compose exec backend celery -A backend inspect active | grep -i "generate"
```

**Solutions** :

#### 1. Score calculation error
**Erreur** : "Cannot calculate total score"

**Cause** : Barème mal configuré ou annotations invalides

**Solution** :
```python
# Django shell
>>> from backend.copies.models import Copy
>>> copy = Copy.objects.get(id='<copy_id>')
>>> copy.calculate_total_score()  # Voir l'erreur exacte
```

#### 2. PDF generation timeout
**Augmenter le timeout** :
```python
# backend/copies/tasks.py
@app.task(soft_time_limit=600)  # 10 minutes
def generate_final_pdf(copy_id):
    ...
```

#### 3. Annotations corrompues
```python
# Vérifier les annotations
>>> copy.annotations.all()
# Identifier celles avec des données invalides
>>> copy.annotations.filter(data__isnull=True).delete()
```

---

## Problèmes de Performance

### Problème : Interface lente

**Symptômes** :
- Chargement des pages > 5 secondes
- PDF rendering lent

**Diagnostic** :
```bash
# Vérifier les ressources serveur
docker stats

# Analyser les requêtes lentes (PostgreSQL)
docker-compose exec db psql -U postgres -d korrigo
=# SELECT query, calls, mean_exec_time, max_exec_time 
   FROM pg_stat_statements 
   ORDER BY mean_exec_time DESC 
   LIMIT 10;
```

**Solutions** :

#### 1. Base de données non optimisée
```sql
-- Analyser les tables
VACUUM ANALYZE;

-- Reconstruire les index
REINDEX DATABASE korrigo;
```

#### 2. Cache Redis non utilisé
**Vérifier** que le cache est activé :
```python
# Django shell
>>> from django.core.cache import cache
>>> cache.set('test', 'value')
>>> cache.get('test')
'value'
```

**Configurer le cache des vues** :
```python
# backend/views.py
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # 5 minutes
def expensive_view(request):
    ...
```

#### 3. Trop de requêtes N+1
**Identifier** avec Django Debug Toolbar ou logs SQL :
```python
# settings.py (DEV uniquement)
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
        }
    }
}
```

**Optimiser** avec `select_related` / `prefetch_related` :
```python
# Avant
copies = Copy.objects.all()
for copy in copies:
    print(copy.exam.name)  # N+1 query

# Après
copies = Copy.objects.select_related('exam').all()
for copy in copies:
    print(copy.exam.name)  # 1 query
```

#### 4. PDF trop volumineux
**Compresser les PDF sources** :
```bash
# Ghostscript
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH -sOutputFile=output.pdf input.pdf
```

**Limiter la résolution de rasterization** :
```python
# backend/exams/tasks.py
RASTERIZATION_DPI = 150  # Au lieu de 300
```

### Problème : Mémoire saturée

**Symptômes** :
- `docker stats` montre 90%+ de mémoire utilisée
- Conteneurs redémarrent (OOM - Out Of Memory)

**Diagnostic** :
```bash
# Mémoire par conteneur
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Logs du système
dmesg | grep -i "out of memory"
```

**Solutions** :

#### 1. Limiter la mémoire par conteneur
**docker-compose.yml** :
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
```

#### 2. Augmenter la RAM du serveur
**Ou** : Migrer vers un serveur plus puissant

#### 3. Optimiser Celery
```yaml
# Réduire la concurrence
celery:
  command: celery -A backend worker -l info --concurrency=2 --max-tasks-per-child=100
```

#### 4. Configurer le swap
```bash
# Créer un fichier swap (8 GB)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Rendre permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Problème : Disque plein

**Symptômes** :
- Erreur "No space left on device"
- Uploads échouent

**Diagnostic** :
```bash
# Espace disque
df -h

# Grands répertoires
du -sh /opt/korrigo/* | sort -h

# Logs Docker
docker system df
```

**Solutions** :

#### 1. Nettoyer les fichiers temporaires
```bash
# Fichiers temporaires Korrigo
docker-compose exec backend python manage.py cleanup_temp_files

# Nettoyer Docker
docker system prune -a --volumes
```

#### 2. Nettoyer les logs
```bash
# Limiter la taille des logs Docker
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}

# Redémarrer Docker
sudo systemctl restart docker
```

#### 3. Archiver les anciens examens
```bash
# Exporter et supprimer les examens de l'année précédente
docker-compose exec backend python manage.py archive_old_exams --year=2025 --export=/backups/archive_2025.tar.gz
```

#### 4. Déplacer les media vers un NAS
**Modifier** `docker-compose.yml` :
```yaml
volumes:
  - /mnt/nas/korrigo-media:/app/media
```

---

## Problèmes de Données

### Problème : Données incohérentes

**Symptômes** :
- Copies sans exam
- Annotations orphelines
- Scores incorrects

**Diagnostic** :
```bash
# Script de vérification d'intégrité
docker-compose exec backend python manage.py check_data_integrity
```

**Solutions** :

#### 1. Copies orphelines
```python
# Django shell
>>> from backend.copies.models import Copy
>>> orphaned_copies = Copy.objects.filter(exam__isnull=True)
>>> orphaned_copies.delete()
```

#### 2. Recalculer les scores
```bash
docker-compose exec backend python manage.py recalculate_all_scores
```

#### 3. Réindexer les données
```bash
docker-compose exec backend python manage.py rebuild_index
```

### Problème : Import CSV échoue

**Symptômes** :
- Import de students depuis Pronote échoue
- Erreur "Invalid CSV format"

**Diagnostic** :
```bash
# Logs d'import
docker-compose logs backend | grep -i "import"

# Vérifier le fichier CSV
head -10 students.csv
file students.csv  # Vérifier l'encodage
```

**Solutions** :

#### 1. Encodage incorrect
```bash
# Convertir en UTF-8
iconv -f ISO-8859-1 -t UTF-8 students.csv > students_utf8.csv
```

#### 2. Format de colonnes incorrect
**Vérifier le header** :
```csv
INE,Nom,Prenom,Classe,Email
```

**Colonnes requises** : INE, Nom, Prenom, Classe

#### 3. Données invalides
**Validation** :
```bash
# Valider le CSV avant import
docker-compose exec backend python manage.py validate_student_csv /path/to/students.csv
```

### Problème : Données supprimées accidentellement

**Symptômes** :
- Un admin a supprimé un exam ou des copies par erreur

**Solutions** :

#### 1. Restauration depuis backup
```bash
# Lister les backups disponibles
ls -lh /backups/

# Restaurer (⚠️ écrase les données actuelles)
docker-compose exec backend python manage.py restore_backup /backups/backup_2026-01-29.sql.gz
```

#### 2. Récupération depuis les logs d'audit
```python
# Si soft-delete est activé
>>> from backend.copies.models import Copy
>>> deleted_copies = Copy.objects.filter(deleted=True)
>>> for copy in deleted_copies:
>>>     copy.deleted = False
>>>     copy.save()
```

#### 3. Export partiel avant restauration
```bash
# Exporter les données récentes avant d'écraser avec le backup
docker-compose exec backend python manage.py dumpdata > current_state.json
```

---

## Procédures d'Urgence

### Urgence : Système complètement down

**Procédure** :

1. **Évaluation rapide** (2 min)
```bash
# Vérifier que le serveur est accessible
ping serveur-korrigo

# SSH
ssh admin@serveur-korrigo

# État des conteneurs
docker-compose ps
```

2. **Redémarrage complet** (5 min)
```bash
cd /opt/korrigo

# Arrêt propre
docker-compose down

# Redémarrage
docker-compose up -d

# Vérifier les logs
docker-compose logs -f
```

3. **Si échec : Mode dégradé** (10 min)
```bash
# Démarrer uniquement les services essentiels
docker-compose up -d db redis backend

# Vérifier
curl http://localhost:8000/api/health
```

4. **Communication** :
- Informer les utilisateurs (email, Pronote)
- Estimer le temps de résolution
- Tenir informé régulièrement

5. **Escalade** :
- Si non résolu sous 1 heure : Contacter le support Korrigo
- Si critique (période d'examens) : Téléphone d'urgence

### Urgence : Suspicion de faille de sécurité

**Procédure** :

1. **Isolation immédiate** (1 min)
```bash
# Bloquer l'accès externe (firewall)
sudo ufw deny from any to any port 80
sudo ufw deny from any to any port 443

# Ou arrêter nginx
docker-compose stop nginx
```

2. **Capture de preuves** (5 min)
```bash
# Logs
docker-compose logs > /tmp/incident_logs_$(date +%Y%m%d_%H%M%S).txt

# État système
docker ps -a > /tmp/incident_containers.txt
netstat -tuln > /tmp/incident_network.txt
```

3. **Analyse** (15 min)
```bash
# Logs d'audit
docker-compose exec backend python manage.py export_audit_logs --since=24h > /tmp/audit.csv

# Connexions suspectes
docker-compose logs nginx | grep -E "POST|PUT|DELETE" | tail -1000
```

4. **Notification** :
- Informer le DPO du lycée
- Informer la direction
- Si fuite de données : CNIL (72 heures)

5. **Restauration sécurisée** :
```bash
# Changer tous les secrets
# .env : Générer nouveau SECRET_KEY, DB_PASSWORD, etc.

# Révoquer toutes les sessions
docker-compose exec backend python manage.py clearsessions

# Forcer reconnexion
docker-compose exec redis redis-cli FLUSHDB
```

### Urgence : Perte de données (pas de backup)

**Procédure** :

1. **Arrêter immédiatement** les écritures
```bash
# Passer en mode lecture seule
docker-compose exec db psql -U postgres -d korrigo -c "ALTER DATABASE korrigo SET default_transaction_read_only = on;"
```

2. **Récupération PostgreSQL**
```bash
# Vérifier les WAL (Write-Ahead Logs)
docker-compose exec db ls -lh /var/lib/postgresql/data/pg_wal/

# Tenter une récupération PITR (Point-In-Time Recovery)
# Nécessite WAL archiving activé
```

3. **Récupération filesystem**
```bash
# Si suppression récente (< 24h)
sudo extundelete /dev/sda1 --restore-directory /opt/korrigo/media
```

4. **Communication transparente** :
- Informer les utilisateurs de la perte
- Quantifier les données perdues
- Proposer solutions de restitution (papier)

5. **Post-mortem** :
- Analyser la cause
- Mettre en place backups automatiques
- Tester les restaurations régulièrement

### Urgence : Rollback après mauvaise mise à jour

**Procédure** :

1. **Restaurer l'ancienne version** (5 min)
```bash
cd /opt/korrigo

# Arrêter
docker-compose down

# Revenir à l'ancienne version (Git)
git log --oneline  # Identifier le commit précédent
git checkout <commit_hash>

# Ou depuis backup de version
tar -xzf /backups/korrigo_v1.2.tar.gz -C /opt/korrigo/
```

2. **Rollback de la base de données** (10 min)
```bash
# Restaurer backup avant migration
docker-compose exec backend python manage.py restore_backup /backups/pre_migration_backup.sql.gz

# Ou annuler les migrations
docker-compose exec backend python manage.py migrate <app_name> <previous_migration>
```

3. **Redémarrer** (2 min)
```bash
docker-compose up -d

# Vérifier
curl http://localhost:8088/api/health
```

4. **Validation** :
- Tester les fonctions critiques
- Vérifier que les utilisateurs peuvent se connecter
- Vérifier les copies en cours de correction

5. **Communication** :
- Informer les utilisateurs du rollback
- Expliquer la situation
- Donner le planning de nouvelle tentative de mise à jour

---

## Checklist de Dépannage Rapide

### Problème général : Suivre cette checklist

- [ ] **Logs** : `docker-compose logs -f` - Identifier l'erreur
- [ ] **Services** : `docker-compose ps` - Tous en "Up" ?
- [ ] **Réseau** : `curl http://localhost:8088` - Accessible ?
- [ ] **DB** : `docker-compose exec db psql -U postgres -c "SELECT 1"` - Connecté ?
- [ ] **Redis** : `docker-compose exec redis redis-cli PING` - Répond "PONG" ?
- [ ] **Ressources** : `docker stats` - CPU/RAM/Disk OK ?
- [ ] **Redémarrage** : `docker-compose restart <service>` - Résout le problème ?
- [ ] **Documentation** : Consulter [FAQ](FAQ.md) et ce guide
- [ ] **Escalade** : Si non résolu sous 2h, contacter support

---

## Ressources Supplémentaires

**Documentation liée** :
- [FAQ](FAQ.md) - Questions fréquentes
- [Support](SUPPORT.md) - Procédures de support
- [Guide Administrateur](../admin/GUIDE_UTILISATEUR_ADMIN.md) - Administration complète
- [Manuel de Sécurité](../security/MANUEL_SECURITE.md) - Incident response
- [Deployment Guide](../DEPLOYMENT_GUIDE.md) - Installation et configuration

**Commandes de diagnostic** :
```bash
# Health check complet
docker-compose exec backend python manage.py check --deploy

# Tests
docker-compose exec backend python manage.py test

# Statistiques DB
docker-compose exec db psql -U postgres -d korrigo -c "SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size FROM pg_tables WHERE schemaname='public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

---

## Historique des Versions

| Version | Date | Modifications |
|---------|------|---------------|
| 1.0.0 | 30/01/2026 | Création initiale du guide de dépannage |

---

**En cas de problème persistant, consultez** [Support](SUPPORT.md).
