# Runbook Backup/Restore - Korrigo Production

**Task ID**: ZF-AUD-12  
**Date**: 2026-02-04  
**Version**: 1.0  
**Statut**: Documentation Opérationnelle

---

## Table des Matières

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Prérequis et Accès](#2-prérequis-et-accès)
3. [Architecture et Composants](#3-architecture-et-composants)
4. [Procédures de Backup](#4-procédures-de-backup)
5. [Procédures de Restore](#5-procédures-de-restore)
6. [Tests et Validation](#6-tests-et-validation)
7. [Politique de Rétention](#7-politique-de-rétention)
8. [Troubleshooting](#8-troubleshooting)
9. [Référence Rapide](#9-référence-rapide)

---

## 1. Vue d'Ensemble

### 1.1 Objectif

Ce runbook documente les procédures complètes de sauvegarde et restauration de la plateforme Korrigo en environnement de production. Il couvre la protection des données critiques (base de données, fichiers média) et les procédures de récupération en cas d'incident.

### 1.2 Portée

**Ce qui est couvert** ✅:
- Sauvegarde de la base de données PostgreSQL
- Sauvegarde des fichiers média (uploads utilisateurs)
- Procédures de restauration complète
- Validation post-backup/restore
- Automatisation des backups (cron)

**Ce qui n'est PAS couvert** ❌:
- Fichiers statiques (régénérables via `collectstatic`)
- Cache Redis (données éphémères)
- Configuration Docker et nginx (versionnées dans Git)
- Variables d'environnement (documentées, contiennent des secrets)

### 1.3 Fréquence Recommandée

| Volume | Fréquence | Rétention | Priorité |
|--------|-----------|-----------|----------|
| **postgres_data** | Quotidienne (3h du matin) | 30 jours | P0 (Critique) |
| **media_volume** | Quotidienne (3h du matin) | 30 jours | P1 (Élevée) |
| **Configuration .env** | À chaque modification | Permanent (hors Git) | P0 (Critique) |

---

## 2. Prérequis et Accès

### 2.1 Accès Requis

Pour exécuter les procédures de backup/restore, vous devez disposer de:

- [x] Accès SSH au serveur de production
- [x] Droits sudo ou utilisateur dans le groupe `docker`
- [x] Accès en lecture/écriture au répertoire de backups
- [x] Variables d'environnement configurées (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)
- [x] Docker Compose installé et opérationnel

### 2.2 Outils Nécessaires

**Sur le serveur de production**:
```bash
docker --version          # >= 24.0
docker compose version    # >= 2.20
pg_dump --version         # PostgreSQL 15 (via container)
python3 --version         # >= 3.11 (via container)
```

**Espace disque requis** (estimations):
- Backup DB: ~50-500 MB (selon la volumétrie)
- Backup media: ~100 MB - 10 GB (selon nombre d'uploads)
- Marge de sécurité: 2x la taille des données

### 2.3 Variables d'Environnement

Les variables suivantes doivent être définies dans `.env` ou exportées:

```bash
# Credentials PostgreSQL (obligatoires)
POSTGRES_DB=viatique
POSTGRES_USER=viatique_user
POSTGRES_PASSWORD=<secret>

# Configuration optionnelle
BACKUP_DIR=backups                    # Répertoire de destination
BACKUP_RETENTION_DAYS=30              # Politique de rétention
```

---

## 3. Architecture et Composants

### 3.1 Volumes Docker Critiques

```yaml
volumes:
  postgres_data:     # ⚠️ CRITIQUE - Base de données PostgreSQL
  media_volume:      # ⚠️ IMPORTANT - Uploads utilisateurs
  static_volume:     # ℹ️ Régénérable - Fichiers statiques collectés
  redis_data:        # ℹ️ Cache - Données éphémères
```

### 3.2 Mapping Volumes → Containers

| Volume | Montage Container | Contenu | Taille Estimée |
|--------|------------------|---------|----------------|
| `postgres_data` | `db:/var/lib/postgresql/data` | Base de données complète | 50 MB - 5 GB |
| `media_volume` | `backend:/app/media` (RW)<br>`nginx:/app/media` (RO) | PDFs, images uploads | 100 MB - 20 GB |
| `static_volume` | `backend:/app/staticfiles` (RW)<br>`nginx:/app/staticfiles` (RO) | CSS, JS, assets | 10-50 MB |

### 3.3 Données Sensibles

⚠️ **ATTENTION - Secrets**:
- Les fichiers `.env` contiennent des secrets (SECRET_KEY, POSTGRES_PASSWORD, etc.)
- Ne JAMAIS versionner `.env` dans Git
- Sauvegarder `.env` de manière sécurisée (coffre-fort, gestionnaire de secrets)
- Restreindre l'accès aux backups (permissions 600)

---

## 4. Procédures de Backup

### 4.1 Checklist Pré-Backup

Avant toute sauvegarde, vérifier:

- [ ] Services Docker en cours d'exécution (`docker compose ps`)
- [ ] Base de données accessible (`docker compose exec db pg_isready`)
- [ ] Espace disque suffisant (`df -h`)
- [ ] Permissions d'écriture sur le répertoire de backup
- [ ] Aucune maintenance planifiée en cours

### 4.2 Méthode 1: Script Shell (Recommandé pour DB uniquement)

#### Description

Le script `scripts/backup_db.sh` crée une sauvegarde de la base de données PostgreSQL via `pg_dump` avec compression gzip.

**Avantages**:
- ✅ Rapide et léger
- ✅ Format SQL standard (portabilité maximale)
- ✅ Nettoyage automatique des backups > 30 jours
- ✅ Compatible avec tout outil PostgreSQL

**Limitations**:
- ❌ Base de données uniquement (pas de media)
- ❌ Nécessite accès Docker Compose

#### Commande d'Exécution

```bash
# Depuis la racine du projet
cd /path/to/korrigo

# Exécuter le script de backup
./scripts/backup_db.sh
```

#### Sortie Attendue

```
📦 Creating database backup: backups/db_backup_20260204_030000.sql
✅ Backup created: backups/db_backup_20260204_030000.sql.gz (2.3M)
🧹 Cleaned 0 old backups (>30 days)
📋 Available backups:
-rw-r--r-- 1 user user 2.3M Feb  4 03:00 backups/db_backup_20260204_030000.sql.gz
-rw-r--r-- 1 user user 2.1M Feb  3 03:00 backups/db_backup_20260203_030000.sql.gz
```

#### Détails Techniques

**Code source** (`scripts/backup_db.sh`):
```bash
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

# Création du dump PostgreSQL
docker compose -f infra/docker/docker-compose.prod.yml exec -T db \
  pg_dump -U ${POSTGRES_USER:-viatique_user} ${POSTGRES_DB:-viatique} \
  > $BACKUP_FILE

# Compression gzip
gzip $BACKUP_FILE

# Nettoyage automatique (>30 jours)
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete
```

**Format de sortie**:
- Fichier: `backups/db_backup_YYYYMMDD_HHMMSS.sql.gz`
- Format: SQL dump compressé gzip
- Contenu: Structure complète + données (DDL + DML)

#### Vérification du Backup

```bash
# Vérifier l'intégrité du fichier gzip
gzip -t backups/db_backup_20260204_030000.sql.gz && echo "✅ Backup OK"

# Vérifier la taille (doit être > 1 MB pour une DB avec données)
ls -lh backups/db_backup_20260204_030000.sql.gz

# Inspecter le contenu sans décompresser
zcat backups/db_backup_20260204_030000.sql.gz | head -50
```

---

### 4.3 Méthode 2: Django Management Command (Backup Complet)

#### Description

La commande Django `python manage.py backup` crée une sauvegarde complète incluant:
- Base de données (format JSON via Django serialization)
- Fichiers média (optionnel, via flag `--include-media`)
- Manifest JSON avec métadonnées

**Avantages**:
- ✅ Backup complet (DB + media en une commande)
- ✅ Format Django portable (indépendant du SGBD)
- ✅ Manifest pour validation
- ✅ Intégration avec l'ORM Django

**Limitations**:
- ❌ Plus lent que pg_dump pour grandes DB
- ❌ Format JSON moins compact que SQL binaire
- ❌ Nécessite accès au container backend

#### Commande d'Exécution

**Backup DB uniquement**:
```bash
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py backup --output-dir /tmp/backups
```

**Backup complet (DB + media)**:
```bash
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py backup \
    --output-dir /tmp/backups \
    --include-media
```

#### Sortie Attendue

```
Created temporary backup directory: /tmp/backups
Backing up database...
Backing up media files...
Successfully created backup at: /tmp/backups/korrigo_backup_20260204_030000
Backup manifest: {
  'timestamp': '20260204_030000',
  'includes_media': True,
  'database_backup': 'db_backup_20260204_030000.json',
  'media_backup': 'media_backup_20260204_030000.zip',
  'backup_dir': '/tmp/backups/korrigo_backup_20260204_030000'
}
```

#### Structure du Backup

```
backups/
└── korrigo_backup_20260204_030000/
    ├── manifest.json                    # Métadonnées du backup
    ├── db_backup_20260204_030000.json   # Base de données (JSON)
    └── media_backup_20260204_030000.zip # Fichiers média (ZIP)
```

#### Détails du Manifest

**Fichier `manifest.json`**:
```json
{
  "timestamp": "20260204_030000",
  "includes_media": true,
  "database_backup": "db_backup_20260204_030000.json",
  "media_backup": "media_backup_20260204_030000.zip",
  "backup_dir": "/tmp/backups/korrigo_backup_20260204_030000"
}
```

#### Vérification du Backup

```bash
# Vérifier la présence du manifest
BACKUP_DIR="/tmp/backups/korrigo_backup_20260204_030000"
cat $BACKUP_DIR/manifest.json | jq .

# Vérifier l'intégrité du JSON
jq empty $BACKUP_DIR/db_backup_20260204_030000.json && echo "✅ JSON valide"

# Vérifier l'archive ZIP
unzip -t $BACKUP_DIR/media_backup_20260204_030000.zip && echo "✅ ZIP OK"

# Compter les objets dans le backup
cat $BACKUP_DIR/db_backup_20260204_030000.json | jq 'length'
```

#### Copier le Backup Hors du Container

```bash
# Le backup est créé dans le container, il faut le copier sur l'hôte
BACKUP_NAME="korrigo_backup_20260204_030000"
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  tar -czf /tmp/${BACKUP_NAME}.tar.gz -C /tmp/backups $BACKUP_NAME

docker compose -f infra/docker/docker-compose.prod.yml cp \
  backend:/tmp/${BACKUP_NAME}.tar.gz ./backups/
```

---

### 4.4 Comparaison des Méthodes

| Critère | Méthode 1 (Shell) | Méthode 2 (Django) |
|---------|-------------------|-------------------|
| **Vitesse** | ⚡ Rapide (pg_dump natif) | 🐢 Plus lent (serialization Python) |
| **Taille** | 📦 Compact (gzip efficace) | 📦 Plus volumineux (JSON) |
| **Portabilité** | 🔧 PostgreSQL uniquement | 🔧 Indépendant du SGBD |
| **Media** | ❌ Non inclus | ✅ Optionnel (--include-media) |
| **Format** | SQL standard | JSON Django |
| **Use case** | Backup DB quotidien | Backup complet avant migration |

**Recommandation**:
- **Production quotidienne**: Méthode 1 (rapide, compact, DB seule)
- **Backup complet pré-migration**: Méthode 2 (DB + media)
- **Stratégie mixte**: Méthode 1 quotidienne + Méthode 2 hebdomadaire

---

### 4.5 Backup des Fichiers Média (Indépendant)

Si vous utilisez la Méthode 1 et souhaitez sauvegarder les médias séparément:

```bash
# Créer une archive tar des médias
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  tar -czf /tmp/media_backup_${TIMESTAMP}.tar.gz /app/media

# Copier l'archive sur l'hôte
docker compose -f infra/docker/docker-compose.prod.yml cp \
  backend:/tmp/media_backup_${TIMESTAMP}.tar.gz \
  ./backups/
```

**Alternative via volume direct**:
```bash
# Identifier le volume Docker
MEDIA_VOLUME=$(docker volume ls -q --filter name=media_volume)

# Backup via container temporaire
docker run --rm \
  -v ${MEDIA_VOLUME}:/data \
  -v $(pwd)/backups:/backup \
  alpine tar -czf /backup/media_backup_${TIMESTAMP}.tar.gz /data
```

---

### 4.6 Automatisation des Backups (Cron)

#### Configuration Cron (Utilisateur)

```bash
# Éditer la crontab
crontab -e

# Ajouter les tâches de backup
# Backup DB quotidien à 3h du matin
0 3 * * * cd /path/to/korrigo && ./scripts/backup_db.sh >> /var/log/korrigo_backup.log 2>&1

# Backup complet hebdomadaire (dimanche 4h)
0 4 * * 0 cd /path/to/korrigo && docker compose -f infra/docker/docker-compose.prod.yml exec -T backend python manage.py backup --output-dir /backups --include-media >> /var/log/korrigo_backup_full.log 2>&1
```

#### Configuration Cron (Systemd Timer - Recommandé)

**Fichier**: `/etc/systemd/system/korrigo-backup.service`
```ini
[Unit]
Description=Korrigo Database Backup
After=docker.service

[Service]
Type=oneshot
User=korrigo
WorkingDirectory=/opt/korrigo
ExecStart=/opt/korrigo/scripts/backup_db.sh
StandardOutput=journal
StandardError=journal
```

**Fichier**: `/etc/systemd/system/korrigo-backup.timer`
```ini
[Unit]
Description=Korrigo Backup Timer
Requires=korrigo-backup.service

[Timer]
OnCalendar=daily
OnCalendar=03:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Activation**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable korrigo-backup.timer
sudo systemctl start korrigo-backup.timer

# Vérifier le statut
sudo systemctl status korrigo-backup.timer
sudo systemctl list-timers | grep korrigo
```

---

### 4.7 Stockage et Archivage des Backups

#### 4.7.1 Stockage Local (Court Terme)

**Localisation recommandée**:
```
/opt/korrigo/backups/       # Backups récents (30 jours)
├── db_backup_20260204_030000.sql.gz
├── db_backup_20260203_030000.sql.gz
├── media_backup_20260204_040000.tar.gz
└── ...
```

**Permissions**:
```bash
chmod 700 /opt/korrigo/backups        # Accès restreint
chmod 600 /opt/korrigo/backups/*.gz   # Fichiers en lecture seule propriétaire
```

#### 4.7.2 Stockage Externe (Long Terme)

**Options recommandées**:

1. **Object Storage (S3, MinIO, etc.)**:
   ```bash
   # Avec AWS CLI
   aws s3 cp backups/db_backup_${TIMESTAMP}.sql.gz \
     s3://korrigo-backups/database/ \
     --storage-class STANDARD_IA
   ```

2. **Rsync vers serveur distant**:
   ```bash
   rsync -avz --delete \
     /opt/korrigo/backups/ \
     backup-server:/backups/korrigo/
   ```

3. **Duplicity (chiffré)**:
   ```bash
   duplicity --encrypt-key YOUR_GPG_KEY \
     /opt/korrigo/backups/ \
     rsync://backup-server//backups/korrigo/
   ```

#### 4.7.3 Stratégie 3-2-1

Recommandation professionnelle:
- **3 copies** des données (1 production + 2 backups)
- **2 supports différents** (disque local + cloud/NAS)
- **1 copie hors-site** (datacenter distant ou cloud)

---

### 4.8 Validation Post-Backup

#### Checklist de Validation

Après chaque backup, vérifier:

- [ ] **Fichier créé**: Le fichier de backup existe
- [ ] **Taille cohérente**: Taille > taille minimale attendue
- [ ] **Intégrité**: Compression testable (`gzip -t` ou `unzip -t`)
- [ ] **Contenu**: Inspection rapide du contenu (nombre d'objets)
- [ ] **Permissions**: Fichier protégé (600 ou 640)
- [ ] **Timestamp**: Horodatage récent (< 1h)
- [ ] **Espace disque**: Marge suffisante restante

#### Script de Validation Automatique

```bash
#!/bin/bash
# validate_backup.sh

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ Backup file not found: $BACKUP_FILE"
  exit 1
fi

# Test intégrité
if [[ "$BACKUP_FILE" =~ \.gz$ ]]; then
  gzip -t "$BACKUP_FILE" || { echo "❌ Corrupted gzip file"; exit 1; }
fi

# Test taille minimale (1 MB)
SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")
if [ $SIZE -lt 1048576 ]; then
  echo "⚠️ Warning: Backup size < 1 MB ($SIZE bytes)"
fi

# Test âge (< 24h)
AGE=$(($(date +%s) - $(stat -f%m "$BACKUP_FILE" 2>/dev/null || stat -c%Y "$BACKUP_FILE")))
if [ $AGE -gt 86400 ]; then
  echo "⚠️ Warning: Backup older than 24h ($((AGE/3600))h)"
fi

echo "✅ Backup validation passed: $BACKUP_FILE"
exit 0
```

**Usage**:
```bash
./scripts/validate_backup.sh backups/db_backup_20260204_030000.sql.gz
```

---

### 4.9 Notifications et Alerting

#### Notifications par Email (Postfix/Sendmail)

```bash
#!/bin/bash
# backup_with_notification.sh

EMAIL="ops@example.com"

if ./scripts/backup_db.sh; then
  echo "Backup successful at $(date)" | mail -s "✅ Korrigo Backup OK" $EMAIL
else
  echo "Backup FAILED at $(date)" | mail -s "❌ Korrigo Backup FAILED" $EMAIL
fi
```

#### Intégration Slack/Discord

```bash
# Webhook Slack
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"✅ Korrigo backup completed successfully"}' \
  $SLACK_WEBHOOK
```

#### Monitoring (Healthchecks.io)

```bash
# Ping healthchecks.io après backup réussi
HEALTHCHECK_URL="https://hc-ping.com/your-uuid"

if ./scripts/backup_db.sh; then
  curl -fsS --retry 3 $HEALTHCHECK_URL > /dev/null
fi
```

---

## 5. Procédures de Restore

*Cette section sera complétée dans le prochain step (Restore Procedures Documentation)*

---

## 6. Tests et Validation

*Cette section sera complétée après documentation des procédures de restore*

---

## 7. Politique de Rétention

### 7.1 Rétention par Type de Backup

| Type | Rétention Locale | Rétention Archive | Fréquence Tests |
|------|-----------------|-------------------|-----------------|
| **DB quotidienne** | 30 jours | 90 jours | Hebdomadaire |
| **DB complète + media** | 7 jours | 1 an | Mensuel |
| **Pre-deployment** | Permanent | Permanent | Avant chaque déploiement |

### 7.2 Nettoyage Automatique

**Intégré dans `backup_db.sh`**:
```bash
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete
```

**Script de nettoyage avancé**:
```bash
#!/bin/bash
# cleanup_old_backups.sh

BACKUP_DIR="backups"
RETENTION_DAYS=30

echo "🧹 Cleaning backups older than ${RETENTION_DAYS} days..."

# Compter les fichiers à supprimer
COUNT=$(find $BACKUP_DIR -name "*.sql.gz" -mtime +${RETENTION_DAYS} | wc -l)

if [ $COUNT -gt 0 ]; then
  find $BACKUP_DIR -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete
  echo "✅ Deleted $COUNT old backups"
else
  echo "ℹ️ No old backups to clean"
fi
```

### 7.3 Conservation Légale

⚠️ **Attention**: Selon les réglementations (RGPD, archives légales), certaines données peuvent nécessiter des périodes de conservation spécifiques. Consulter le DPO ou l'équipe légale.

---

## 8. Troubleshooting

*Cette section sera enrichie avec les cas d'erreur rencontrés lors des procédures de restore*

### 8.1 Erreurs Communes (Backup)

#### Erreur: "Permission denied"

**Symptôme**:
```
./scripts/backup_db.sh: Permission denied
```

**Solution**:
```bash
chmod +x scripts/backup_db.sh
```

#### Erreur: "No space left on device"

**Symptôme**:
```
gzip: backups/db_backup_20260204_030000.sql.gz: No space left on device
```

**Solution**:
```bash
# Vérifier l'espace disque
df -h

# Nettoyer les anciens backups
./scripts/cleanup_old_backups.sh

# Ou augmenter l'espace disque
```

#### Erreur: "docker compose: command not found"

**Symptôme**:
```
docker compose: command not found
```

**Solution**:
```bash
# Essayer avec docker-compose (ancienne version)
sed -i 's/docker compose/docker-compose/g' scripts/backup_db.sh
```

---

## 9. Référence Rapide

### 9.1 Commandes Essentielles

```bash
# Backup DB (rapide)
./scripts/backup_db.sh

# Backup complet (DB + media)
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py backup --output-dir /tmp/backups --include-media

# Lister les backups disponibles
ls -lht backups/ | head -10

# Vérifier intégrité d'un backup
gzip -t backups/db_backup_YYYYMMDD_HHMMSS.sql.gz

# Nettoyer anciens backups
find backups/ -name "*.sql.gz" -mtime +30 -delete
```

### 9.2 Checklist Backup Quotidien

- [ ] Backup DB exécuté (automatique via cron)
- [ ] Fichier créé et validé (taille, intégrité)
- [ ] Notification reçue (email/Slack)
- [ ] Espace disque suffisant (> 10% libre)
- [ ] Logs vérifiés (pas d'erreurs)

### 9.3 Points de Contact

| Rôle | Contact | Responsabilité |
|------|---------|----------------|
| **DevOps Lead** | devops@example.com | Configuration backups, troubleshooting |
| **DBA** | dba@example.com | Validation DB, optimisation pg_dump |
| **Ops Manager** | ops@example.com | Procédures, escalation incidents |

---

## Annexes

### A. Références

- **Documentation Django Backup**: `backend/core/management/commands/backup.py`
- **Script Shell Backup**: `scripts/backup_db.sh`
- **Audit Sécurité Volumes**: `.zenflow/tasks/hardening-prod-settings-headers-ac7f/audit.md` Section 6
- **Docker Compose Production**: `infra/docker/docker-compose.prod.yml`

### B. Historique des Révisions

| Version | Date | Auteur | Changements |
|---------|------|--------|-------------|
| 1.0 | 2026-02-04 | DevOps | Documentation initiale procédures backup |

---

**Document Status**: 🟡 Partiel - Sections Restore, Tests et Troubleshooting avancé à compléter

**Prochaines Étapes**:
1. Documenter procédures de restore (Section 5)
2. Compléter tests de validation (Section 6)
3. Enrichir troubleshooting avec cas réels (Section 8)
