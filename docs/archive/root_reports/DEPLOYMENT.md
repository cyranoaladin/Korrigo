# 🚀 Guide de Déploiement Korrigo

## 📍 Serveur de Production

- **URL** : https://korrigo.labomaths.tn
- **Serveur** : moneyfactory-core (88.99.254.59)
- **Répertoire** : `/var/www/labomaths/korrigo/`
- **Docker Compose** : `docker-compose.labomaths.yml`

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Nginx (Host) :443 → korrigo.labomaths.tn              │
│         ↓                                                │
│  Docker: frontend_nginx :4000                           │
│         ↓                                                │
│  Docker: backend :8000 (Gunicorn + Django)              │
│         ↓                                                │
│  Docker: db (PostgreSQL) + redis + celery               │
└─────────────────────────────────────────────────────────┘
```

## 📦 Services Docker

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `korrigo-backend-1` | Custom Django | 8000 (interne) | API Backend |
| `korrigo-frontend_nginx-1` | Custom Nginx | 4000 → 80 | Frontend Vue.js |
| `korrigo-db-1` | postgres:15-alpine | 5432 (interne) | Base de données |
| `korrigo-redis-1` | redis:7-alpine | 6379 (interne) | Cache & Celery |
| `korrigo-celery-1` | Custom Django | - | Worker async |

## 🔧 Déploiement

### Méthode 1 : Script Automatique (Recommandé)

```bash
# Sur le serveur
ssh mf
cd /var/www/labomaths/korrigo
./deploy_korrigo.sh
```

Le script effectue automatiquement :
1. ✅ Backup de la base de données
2. ✅ Pull des dernières modifications Git
3. ✅ Rebuild des images Docker
4. ✅ Application des migrations
5. ✅ Collecte des fichiers statiques
6. ✅ Vérifications post-déploiement

### Méthode 2 : Déploiement Manuel

```bash
# 1. Connexion au serveur
ssh mf
cd /var/www/labomaths/korrigo

# 2. Backup de la base de données
docker exec korrigo-db-1 pg_dump -U korrigo_user korrigo > /var/backups/korrigo/backup_$(date +%Y%m%d_%H%M%S).sql

# 3. Mise à jour du code
git pull origin main

# 4. Rebuild et redémarrage
docker compose -f docker-compose.labomaths.yml down
docker compose -f docker-compose.labomaths.yml build --no-cache
docker compose -f docker-compose.labomaths.yml up -d

# 5. Migrations et static
docker exec korrigo-backend-1 python manage.py migrate
docker exec korrigo-backend-1 python manage.py collectstatic --noinput
```

## 🔍 Commandes Utiles

### Logs

```bash
# Logs backend
docker logs -f korrigo-backend-1

# Logs frontend
docker logs -f korrigo-frontend_nginx-1

# Logs celery
docker logs -f korrigo-celery-1

# Logs base de données
docker logs -f korrigo-db-1

# Tous les logs
docker compose -f docker-compose.labomaths.yml logs -f
```

### Gestion des Services

```bash
# Statut des conteneurs
docker compose -f docker-compose.labomaths.yml ps

# Redémarrer un service
docker compose -f docker-compose.labomaths.yml restart backend

# Redémarrer tous les services
docker compose -f docker-compose.labomaths.yml restart

# Arrêter tous les services
docker compose -f docker-compose.labomaths.yml down

# Démarrer tous les services
docker compose -f docker-compose.labomaths.yml up -d
```

### Base de Données

```bash
# Accéder au shell PostgreSQL
docker exec -it korrigo-db-1 psql -U korrigo_user -d korrigo

# Backup manuel
docker exec korrigo-db-1 pg_dump -U korrigo_user korrigo > backup.sql

# Restaurer un backup
cat backup.sql | docker exec -i korrigo-db-1 psql -U korrigo_user -d korrigo
```

### Django Management

```bash
# Shell Django
docker exec -it korrigo-backend-1 python manage.py shell

# Créer un superuser
docker exec -it korrigo-backend-1 python manage.py createsuperuser

# Migrations
docker exec korrigo-backend-1 python manage.py makemigrations
docker exec korrigo-backend-1 python manage.py migrate

# Collecte des fichiers statiques
docker exec korrigo-backend-1 python manage.py collectstatic --noinput
```

## 🐛 Dépannage

### Le site ne répond pas

```bash
# Vérifier l'état des conteneurs
docker compose -f docker-compose.labomaths.yml ps

# Vérifier les logs
docker logs korrigo-backend-1 --tail 100
docker logs korrigo-frontend_nginx-1 --tail 100

# Redémarrer les services
docker compose -f docker-compose.labomaths.yml restart
```

### Erreur 502 Bad Gateway

```bash
# Vérifier que le backend est accessible
docker exec korrigo-frontend_nginx-1 curl http://backend:8000/api/health/

# Vérifier les logs backend
docker logs korrigo-backend-1 --tail 50
```

### Base de données inaccessible

```bash
# Vérifier l'état de PostgreSQL
docker exec korrigo-db-1 pg_isready -U korrigo_user -d korrigo

# Redémarrer la base de données
docker compose -f docker-compose.labomaths.yml restart db
```

### Migrations échouées

```bash
# Voir l'état des migrations
docker exec korrigo-backend-1 python manage.py showmigrations

# Appliquer une migration spécifique
docker exec korrigo-backend-1 python manage.py migrate students 0005

# Fake une migration (si déjà appliquée manuellement)
docker exec korrigo-backend-1 python manage.py migrate students 0005 --fake
```

## 🔐 Sécurité

### Variables d'Environnement Sensibles

Les variables suivantes sont définies dans `docker-compose.labomaths.yml` :

- `SECRET_KEY` : Clé secrète Django (à changer en production)
- `POSTGRES_PASSWORD` : Mot de passe PostgreSQL
- `DATABASE_URL` : URL de connexion à la base de données

**⚠️ Important** : Ne jamais commit ces valeurs dans Git !

### SSL/TLS

Le certificat SSL est géré par Let's Encrypt via Nginx (host) :
- Certificat : `/etc/letsencrypt/live/nsi.labomaths.tn/fullchain.pem`
- Clé privée : `/etc/letsencrypt/live/nsi.labomaths.tn/privkey.pem`

Renouvellement automatique via certbot.

## 📊 Monitoring

### Health Checks

```bash
# Backend health
curl https://korrigo.labomaths.tn/api/health/

# Vérifier les health checks Docker
docker inspect korrigo-backend-1 --format='{{.State.Health.Status}}'
docker inspect korrigo-db-1 --format='{{.State.Health.Status}}'
```

### Métriques

```bash
# Utilisation des ressources
docker stats

# Espace disque des volumes
docker system df -v
```

## 📝 Backups

Les backups automatiques sont créés dans `/var/backups/korrigo/` :
- Format : `korrigo_db_YYYYMMDD_HHMMSS.sql`
- Rétention : 10 derniers backups
- Fréquence : À chaque déploiement

### Backup Manuel

```bash
# Créer un backup
mkdir -p /var/backups/korrigo
docker exec korrigo-db-1 pg_dump -U korrigo_user korrigo > /var/backups/korrigo/manual_$(date +%Y%m%d_%H%M%S).sql

# Restaurer un backup
docker exec -i korrigo-db-1 psql -U korrigo_user -d korrigo < /var/backups/korrigo/backup.sql
```

## 🔄 Rollback

En cas de problème après déploiement :

```bash
# 1. Revenir au commit précédent
git log --oneline -5
git reset --hard <commit_hash>

# 2. Rebuild
docker compose -f docker-compose.labomaths.yml build --no-cache
docker compose -f docker-compose.labomaths.yml up -d

# 3. Restaurer le backup si nécessaire
cat /var/backups/korrigo/korrigo_db_YYYYMMDD_HHMMSS.sql | docker exec -i korrigo-db-1 psql -U korrigo_user -d korrigo
```

## 📞 Support

En cas de problème :
1. Vérifier les logs : `docker compose -f docker-compose.labomaths.yml logs`
2. Vérifier l'état des services : `docker compose -f docker-compose.labomaths.yml ps`
3. Consulter ce guide de dépannage
4. Contacter l'équipe technique

---

**Dernière mise à jour** : 5 février 2026
