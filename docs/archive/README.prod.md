# Korrigo - Guide de Déploiement Production

Ce guide détaille le déploiement et l'exploitation de Korrigo en environnement production.

## 📋 Prérequis

### Logiciels Requis
- **Docker** ≥ 24.0
- **Docker Compose** ≥ 2.20
- **Git** (pour récupérer le code)
- Accès réseau à GitHub Container Registry (GHCR)

### Système d'Exploitation
- Linux (Ubuntu 22.04 LTS recommandé)
- macOS (compatible, non recommandé pour production)
- Windows + WSL2 (déconseillé pour production)

### Ressources Serveur Minimum
- **CPU** : 2 cores (4 recommandés)
- **RAM** : 4 GB (8 GB recommandés)
- **Disque** : 20 GB (50 GB recommandés pour stockage des PDFs)
- **Réseau** : Bande passante stable pour uploads PDF

### Authentification GHCR (GitHub Container Registry)
Les images Docker sont hébergées sur GHCR. Pour les télécharger :

```bash
# Générer un Personal Access Token (PAT) sur GitHub avec scope read:packages
# Puis s'authentifier :
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin
```

**Note** : Si vous n'avez pas accès GHCR, vous pouvez builder localement les images (voir section Build Local).

---

## ⚙️ Configuration

### 1. Cloner le Dépôt
```bash
git clone https://github.com/cyranoaladin/Korrigo.git
cd Korrigo
```

### 2. Créer le Fichier .env Production
Le fichier `.env.prod.example` contient un template avec toutes les variables nécessaires.

```bash
cp .env.prod.example .env.prod
```

**Variables CRITIQUES à modifier** (liste exhaustive dans `.env.prod`) :

| Variable | Description | Exemple |
|----------|-------------|---------|
| `SECRET_KEY` | Clé secrète Django (≥50 chars aléatoires) | `openssl rand -base64 50` |
| `ALLOWED_HOSTS` | Domaines autorisés (séparés par virgules) | `korrigo.example.com,www.korrigo.example.com` |
| `POSTGRES_PASSWORD` | Mot de passe DB (fort) | `$(openssl rand -base64 32)` |
| `POSTGRES_USER` | Utilisateur DB | `korrigo_prod` |
| `POSTGRES_DB` | Nom de la DB | `korrigo_prod` |
| `SSL_ENABLED` | Activer HTTPS/HSTS | `true` (production HTTPS) |
| `CORS_ALLOWED_ORIGINS` | Origins autorisées | `https://korrigo.example.com` |
| `CSRF_TRUSTED_ORIGINS` | Origins de confiance CSRF | `https://korrigo.example.com` |
| `GITHUB_REPOSITORY_OWNER` | Owner GitHub pour images GHCR | `votre-org` |
| `KORRIGO_SHA` | Tag/SHA de l'image Docker | `v1.0.0` ou `abc1234` |

**⚠️ SÉCURITÉ** :
- **JAMAIS** committer `.env.prod` (déjà dans `.gitignore`)
- Générer `SECRET_KEY` aléatoire : `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- Utiliser des mots de passe forts pour `POSTGRES_PASSWORD`

### 3. Vérifier la Configuration
```bash
# Valider que docker-compose.prod.yml est bien formé
docker compose -f infra/docker/docker-compose.prod.yml config > /tmp/compose-validated.yml

# Vérifier qu'aucune erreur n'est affichée
echo $?  # Doit retourner 0
```

---

## 🚀 Déploiement en 3 Commandes

### Commande 1 : Démarrer les Services
```bash
# Depuis la racine du projet
./scripts/prod_up.sh
```

**Ce qui se passe** :
- Pull des images Docker depuis GHCR (ou build local si `--build`)
- Démarrage de 6 services : `db`, `redis`, `backend`, `celery`, `celery-beat`, `nginx`
- Health checks automatiques (attente que tous les services soient `healthy`)
- Volumes persistants créés pour DB, static files, media files

**Durée estimée** : 30-60 secondes (premier démarrage), 10-20 secondes (redémarrages)

### Commande 2 : Vérifier la Santé
```bash
# Health check liveness (doit toujours retourner 200)
curl http://localhost:8088/api/health/live/

# Health check readiness (retourne 200 si DB+Redis OK, 503 sinon)
curl http://localhost:8088/api/health/ready/

# Health check legacy (inclut cache)
curl http://localhost:8088/api/health/
```

**Réponses attendues** :
```json
// /api/health/live/ (liveness - toujours 200)
{"status": "alive"}

// /api/health/ready/ (readiness - 200 si prêt, 503 sinon)
{"status": "ready", "database": "connected", "cache": "connected"}
```

**Si 503** : Les services ne sont pas encore prêts. Attendre 30s et réessayer.

### Commande 3 : Appliquer les Migrations
```bash
# Uniquement au premier déploiement ou après mise à jour avec migrations
docker compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py migrate
```

**Sortie attendue** :
```
Operations to perform:
  Apply all migrations: ...
Running migrations:
  Applying exams.0001_initial... OK
  Applying grading.0001_initial... OK
  ...
```

**⚠️ CRITIQUE** : Toujours faire un backup DB avant de lancer des migrations (voir section Migrations).

---

## ✅ Vérification Post-Déploiement

### 1. Services Running
```bash
docker compose -f infra/docker/docker-compose.prod.yml ps
```

**Tous les services doivent être `Up` et `healthy`** :
```
NAME                 STATUS
db                   Up (healthy)
redis                Up (healthy)
backend              Up (healthy)
celery               Up (healthy)
celery-beat          Up
nginx                Up (healthy)
```

### 2. Smoke Tests Automatiques
Nous fournissons 8 tests de smoke pour valider le déploiement :

```bash
# Depuis le conteneur backend
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  pytest -m smoke --tb=short -v

# Ou depuis l'hôte (si pytest installé localement)
source venv/bin/activate
cd backend
pytest -m smoke --tb=short
```

**Tests exécutés** :
1. ✅ `test_health_endpoints` - Liveness/readiness endpoints accessibles
2. ✅ `test_authentication_flow` - Login professeur fonctionne
3. ✅ `test_exam_creation_flow` - API création examen accessible
4. ✅ `test_copy_list_flow` - API listing copies accessible
5. ✅ `test_admin_accessible` - Django Admin répond
6. ✅ `test_static_files_configuration` - Settings STATIC/MEDIA configurés
7. ✅ `test_database_connection` - Connexion DB fonctionne
8. ✅ `test_critical_models_importable` - Modèles Django importables

**Résultat attendu** : `8 passed, 172 deselected`

### 3. Frontend Accessible
```bash
# Ouvrir dans un navigateur
xdg-open http://localhost:8088  # Linux
open http://localhost:8088      # macOS

# Ou via curl
curl -I http://localhost:8088
# Doit retourner HTTP 200
```

### 4. API Backend Accessible
```bash
# Test endpoint public
curl http://localhost:8088/api/health/live/

# Test endpoint authentifié (doit retourner 401/403 sans token)
curl http://localhost:8088/api/exams/
```

---

## 🗃 Gestion des Migrations

### Appliquer les Migrations
**⚠️ TOUJOURS FAIRE UN BACKUP AVANT** (voir section Backup)

```bash
# 1. Backup DB (OBLIGATOIRE)
./scripts/backup_db.sh  # Voir section Backup

# 2. Appliquer migrations
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py migrate

# 3. Vérifier état des migrations
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py showmigrations
```

### Rollback de Migration (Urgence)
Si une migration échoue ou cause des problèmes :

```bash
# 1. Identifier la migration à rollback
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py showmigrations

# 2. Rollback vers migration précédente
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py migrate <app_name> <migration_number>

# Exemple : rollback grading vers 0006
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py migrate grading 0006
```

### Créer un Backup Pré-Migration Automatique
```bash
# Script à exécuter avant toute migration
cat > scripts/migrate_with_backup.sh << 'EOF'
#!/bin/bash
set -euo pipefail

echo "📦 Creating backup before migration..."
./scripts/backup_db.sh

echo "🚀 Applying migrations..."
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py migrate

echo "✅ Migrations applied successfully"
EOF

chmod +x scripts/migrate_with_backup.sh
```

---

## 📊 Logs et Debugging

### Consulter les Logs

#### Tous les Services
```bash
# Logs en temps réel (tail -f)
docker compose -f infra/docker/docker-compose.prod.yml logs -f

# 100 dernières lignes
docker compose -f infra/docker/docker-compose.prod.yml logs --tail=100

# Logs depuis 1h
docker compose -f infra/docker/docker-compose.prod.yml logs --since=1h
```

#### Service Spécifique
```bash
# Backend
docker compose -f infra/docker/docker-compose.prod.yml logs -f backend

# Celery worker
docker compose -f infra/docker/docker-compose.prod.yml logs -f celery

# Nginx
docker compose -f infra/docker/docker-compose.prod.yml logs -f nginx

# Base de données
docker compose -f infra/docker/docker-compose.prod.yml logs -f db
```

#### Filtrer par Niveau de Log
```bash
# Erreurs uniquement (grep)
docker compose -f infra/docker/docker-compose.prod.yml logs backend | grep ERROR

# Warnings et erreurs
docker compose -f infra/docker/docker-compose.prod.yml logs backend | grep -E "WARNING|ERROR"
```

### Logs Django Structurés
Les logs Django sont au format JSON (configuré dans `settings.py`) pour parsing facile :

```bash
# Parser JSON logs avec jq
docker compose -f infra/docker/docker-compose.prod.yml logs backend --since=10m \
  | grep -oP '\{.*\}' \
  | jq 'select(.levelname == "ERROR")'
```

### Debugging Interactif

#### Shell Django
```bash
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py shell
```

#### Shell Python
```bash
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python
```

#### Shell Bash
```bash
docker compose -f infra/docker/docker-compose.prod.yml exec backend bash
```

#### Inspecter la Base de Données
```bash
# Psql interactif
docker compose -f infra/docker/docker-compose.prod.yml exec db \
  psql -U ${POSTGRES_USER:-viatique_user} -d ${POSTGRES_DB:-viatique}

# Requête SQL directe
docker compose -f infra/docker/docker-compose.prod.yml exec db \
  psql -U viatique_user -d viatique -c "SELECT COUNT(*) FROM exams_exam;"
```

### Problèmes Fréquents

#### Service ne démarre pas
```bash
# Vérifier les healthchecks
docker compose -f infra/docker/docker-compose.prod.yml ps

# Inspecter les logs du service
docker compose -f infra/docker/docker-compose.prod.yml logs <service_name>

# Redémarrer un service spécifique
docker compose -f infra/docker/docker-compose.prod.yml restart <service_name>
```

#### Base de données inaccessible
```bash
# Vérifier que DB est healthy
docker compose -f infra/docker/docker-compose.prod.yml ps db

# Tester connexion
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py dbshell

# Vérifier variables d'env DB
docker compose -f infra/docker/docker-compose.prod.yml exec backend env | grep DATABASE
```

#### Celery tasks bloquées
```bash
# Inspecter celery workers
docker compose -f infra/docker/docker-compose.prod.yml exec celery \
  celery -A core inspect active

# Voir les tasks en attente
docker compose -f infra/docker/docker-compose.prod.yml exec celery \
  celery -A core inspect reserved

# Purger la queue (⚠️ perte des tasks en attente)
docker compose -f infra/docker/docker-compose.prod.yml exec celery \
  celery -A core purge
```

---

## 💾 Backup et Restauration

### Backup Base de Données

#### Backup Manuel
```bash
# Créer backup horodaté
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker compose -f infra/docker/docker-compose.prod.yml exec -T db \
  pg_dump -U ${POSTGRES_USER:-viatique_user} ${POSTGRES_DB:-viatique} \
  > backups/db_backup_${TIMESTAMP}.sql

# Compresser
gzip backups/db_backup_${TIMESTAMP}.sql
```

#### Script de Backup Automatique
```bash
cat > scripts/backup_db.sh << 'EOF'
#!/bin/bash
set -euo pipefail

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

mkdir -p $BACKUP_DIR

echo "📦 Creating database backup: $BACKUP_FILE"
docker compose -f infra/docker/docker-compose.prod.yml exec -T db \
  pg_dump -U ${POSTGRES_USER:-viatique_user} ${POSTGRES_DB:-viatique} \
  > $BACKUP_FILE

gzip $BACKUP_FILE
echo "✅ Backup created: ${BACKUP_FILE}.gz"

# Rétention : supprimer backups > 30 jours
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete
echo "🧹 Old backups cleaned (>30 days)"
EOF

chmod +x scripts/backup_db.sh
```

#### Cron Automatique (Backup Quotidien)
```bash
# Ajouter à crontab
crontab -e

# Backup tous les jours à 2h du matin
0 2 * * * cd /path/to/Korrigo && ./scripts/backup_db.sh >> /var/log/korrigo_backup.log 2>&1
```

### Restauration Base de Données

#### Restauration Complète
```bash
# 1. Arrêter backend/celery (pour éviter écritures pendant restore)
docker compose -f infra/docker/docker-compose.prod.yml stop backend celery celery-beat

# 2. Restaurer le backup
gunzip -c backups/db_backup_20260128_020000.sql.gz | \
  docker compose -f infra/docker/docker-compose.prod.yml exec -T db \
    psql -U ${POSTGRES_USER:-viatique_user} ${POSTGRES_DB:-viatique}

# 3. Redémarrer les services
docker compose -f infra/docker/docker-compose.prod.yml start backend celery celery-beat
```

#### Restauration dans une Nouvelle DB (Test)
```bash
# Créer une DB de test
docker compose -f infra/docker/docker-compose.prod.yml exec db \
  psql -U postgres -c "CREATE DATABASE viatique_restore_test;"

# Restaurer dans cette DB
gunzip -c backups/db_backup_20260128_020000.sql.gz | \
  docker compose -f infra/docker/docker-compose.prod.yml exec -T db \
    psql -U postgres viatique_restore_test
```

### Backup Media Files
```bash
# Backup du volume media
docker run --rm \
  -v $(docker volume inspect docker_media_volume -f '{{ .Mountpoint }}'):/source:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/media_backup_$(date +%Y%m%d).tar.gz -C /source .
```

---

## 🔄 Rollback et Déploiement de Version

### Rollback vers Version Précédente

#### 1. Identifier le SHA/Tag à Rollback
```bash
# Lister les tags git
git tag -l

# Ou commits récents
git log --oneline -10
```

#### 2. Mettre à Jour .env.prod
```bash
# Éditer .env.prod et changer KORRIGO_SHA
nano .env.prod

# Exemple : passer de v1.2.0 à v1.1.0
KORRIGO_SHA=v1.1.0
```

#### 3. Déployer la Version Précédente
```bash
# Pull de l'ancienne image
docker compose -f infra/docker/docker-compose.prod.yml pull

# Redémarrer avec l'ancienne version
docker compose -f infra/docker/docker-compose.prod.yml up -d

# Vérifier que les services sont healthy
docker compose -f infra/docker/docker-compose.prod.yml ps
```

#### 4. Rollback de Migration (si nécessaire)
```bash
# Si la nouvelle version avait appliqué des migrations
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py migrate <app> <migration_number>
```

### Procédure de Rollback Complète (Urgence)
En cas de problème critique en production :

```bash
#!/bin/bash
# rollback_emergency.sh

set -euo pipefail

echo "🚨 EMERGENCY ROLLBACK"
echo "This will restore the previous version and database backup"
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted"
  exit 1
fi

# 1. Arrêter les services
echo "⏸  Stopping services..."
docker compose -f infra/docker/docker-compose.prod.yml stop backend celery celery-beat

# 2. Restaurer le dernier backup DB
echo "💾 Restoring database backup..."
LAST_BACKUP=$(ls -t backups/db_backup_*.sql.gz | head -1)
echo "Using backup: $LAST_BACKUP"
gunzip -c $LAST_BACKUP | \
  docker compose -f infra/docker/docker-compose.prod.yml exec -T db \
    psql -U ${POSTGRES_USER:-viatique_user} ${POSTGRES_DB:-viatique}

# 3. Changer KORRIGO_SHA vers version stable
echo "🔄 Switching to previous version..."
sed -i 's/KORRIGO_SHA=.*/KORRIGO_SHA=v1.1.0/' .env.prod  # Ajuster version

# 4. Redémarrer avec ancienne version
echo "🚀 Starting services with previous version..."
docker compose -f infra/docker/docker-compose.prod.yml up -d

# 5. Vérifier santé
echo "✅ Checking health..."
sleep 10
curl -f http://localhost:8088/api/health/live/ || echo "⚠️  Health check failed"

echo "✅ Rollback completed"
```

---

## 🛑 Arrêt et Maintenance

### Arrêt Complet
```bash
# Arrêt propre (préserve volumes)
./scripts/prod_down.sh

# Ou manuellement
docker compose -f infra/docker/docker-compose.prod.yml down
```

**⚠️ ATTENTION** : `prod_down.sh` utilise `-v` et **supprime les volumes** (perte de données DB).
Pour préserver les données, utiliser `docker compose down` **sans** `-v`.

### Arrêt d'un Service Spécifique
```bash
# Arrêter backend uniquement
docker compose -f infra/docker/docker-compose.prod.yml stop backend

# Redémarrer backend
docker compose -f infra/docker/docker-compose.prod.yml start backend
```

### Mise à Jour sans Downtime (Rolling Update)
```bash
# 1. Backup DB
./scripts/backup_db.sh

# 2. Pull nouvelle image
docker compose -f infra/docker/docker-compose.prod.yml pull backend

# 3. Restart backend uniquement (nginx continue de servir)
docker compose -f infra/docker/docker-compose.prod.yml up -d --no-deps backend

# 4. Vérifier health
curl http://localhost:8088/api/health/ready/

# 5. Si OK, restart celery workers
docker compose -f infra/docker/docker-compose.prod.yml restart celery celery-beat
```

---

## 🔐 Sécurité Production

### Checklist Sécurité (À vérifier avant mise en prod)

- [ ] `SECRET_KEY` généré aléatoirement (≥50 chars)
- [ ] `DEBUG=False` dans `.env.prod`
- [ ] `ALLOWED_HOSTS` configuré avec domaines exacts
- [ ] `SSL_ENABLED=true` (HTTPS obligatoire)
- [ ] `CORS_ALLOWED_ORIGINS` restreint au domaine frontend
- [ ] `CSRF_TRUSTED_ORIGINS` configuré
- [ ] Mots de passe DB forts (≥20 chars aléatoires)
- [ ] `.env.prod` jamais commité (dans `.gitignore`)
- [ ] Backups automatiques configurés (cron)
- [ ] Monitoring/alertes configurés (logs, erreurs)
- [ ] Certificat SSL valide (Let's Encrypt ou autre)
- [ ] Firewall configuré (ports 80/443 uniquement ouverts)
- [ ] Accès SSH sécurisé (clés uniquement, pas de password)
- [ ] Docker socket non exposé publiquement

### Rotation des Secrets
```bash
# Générer nouveau SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(50))"

# Générer nouveau mot de passe DB
openssl rand -base64 32

# Après rotation :
# 1. Mettre à jour .env.prod
# 2. Redémarrer services
docker compose -f infra/docker/docker-compose.prod.yml restart
```

---

## 🏗 Build Local (Alternative à GHCR)

Si vous n'avez pas accès à GHCR, vous pouvez builder les images localement :

### Backend
```bash
cd backend
docker build -t korrigo-backend:local .
```

### Frontend/Nginx
```bash
cd frontend
docker build -t korrigo-nginx:local .
```

### Modifier docker-compose.prod.yml
```yaml
# Remplacer les images GHCR par les images locales
backend:
  image: korrigo-backend:local  # Au lieu de ghcr.io/...
  # ...

nginx:
  image: korrigo-nginx:local    # Au lieu de ghcr.io/...
  # ...
```

---

## 📞 Support et Troubleshooting

### Contacts
- **Concepteur** : Aleddine BEN RHOUMA
- **Issues** : https://github.com/cyranoaladin/Korrigo/issues

### Ressources
- [README.md](README.md) - Documentation développement
- [.claude/rules/](.claude/rules/) - Règles du projet et architecture

### Problèmes Connus

#### "GITHUB_REPOSITORY_OWNER variable is not set"
**Solution** : Ajouter `GITHUB_REPOSITORY_OWNER=votre-org` dans `.env.prod`

#### "Service Unavailable (503)" sur /api/health/
**Cause** : Redis/cache non disponible
**Solution** : Vérifier que redis est `healthy` avec `docker compose ps`

#### Migrations échouent avec "database locked"
**Cause** : Backend/Celery accèdent à la DB pendant migration
**Solution** : Arrêter backend/celery avant migration, redémarrer après

---

## 📝 Changelog et Versions

Voir les [releases GitHub](https://github.com/cyranoaladin/Korrigo/releases) pour l'historique des versions.

**Version actuelle** : Vérifier avec `git describe --tags`

---

**Dernière mise à jour** : 2026-01-28
**Statut** : Production-ready ✅
