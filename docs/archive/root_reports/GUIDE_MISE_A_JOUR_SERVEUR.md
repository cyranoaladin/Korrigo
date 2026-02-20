# Guide de Mise à Jour du Serveur Korrigo

## Prérequis

- Accès SSH au serveur
- Droits sudo
- Le serveur doit avoir Docker et Docker Compose installés

## Procédure de Mise à Jour Propre

### Étape 1 : Se connecter au serveur

```bash
ssh user@korrigo.labomaths.tn
```

### Étape 2 : Aller dans le répertoire du projet

```bash
cd /chemin/vers/Korrigo
```

### Étape 3 : Sauvegarder la base de données (IMPORTANT)

```bash
# Créer un backup de la base de données
docker compose exec db pg_dump -U korrigo_user korrigo_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Étape 4 : Arrêter les services proprement

```bash
# Arrêter tous les conteneurs
docker compose down
```

### Étape 5 : Nettoyer les caches et fichiers temporaires

```bash
# Supprimer les conteneurs arrêtés
docker container prune -f

# Supprimer les images non utilisées (optionnel, libère de l'espace)
docker image prune -f

# Supprimer les volumes orphelins (ATTENTION: ne pas supprimer les volumes de données)
docker volume prune -f --filter "label!=keep"

# Nettoyer le cache Python
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Nettoyer le cache npm/node_modules (si rebuild frontend nécessaire)
# rm -rf frontend/node_modules frontend/.nuxt frontend/.output
```

### Étape 6 : Récupérer les dernières modifications

```bash
# Vérifier l'état actuel
git status

# Sauvegarder les modifications locales si nécessaire
git stash

# Récupérer les dernières modifications
git fetch origin
git pull origin main

# Restaurer les modifications locales si nécessaire
# git stash pop
```

### Étape 7 : Reconstruire les images Docker

```bash
# Rebuild complet sans cache (recommandé après mise à jour majeure)
docker compose build --no-cache

# OU rebuild normal (plus rapide)
# docker compose build
```

### Étape 8 : Démarrer les services

```bash
# Démarrer en mode détaché
docker compose up -d
```

### Étape 9 : Appliquer les migrations de base de données

```bash
# Exécuter les migrations Django
docker compose exec backend python manage.py migrate --noinput
```

### Étape 10 : Collecter les fichiers statiques

```bash
# Collecter les fichiers statiques
docker compose exec backend python manage.py collectstatic --noinput
```

### Étape 11 : Vérifier le bon fonctionnement

```bash
# Vérifier l'état des conteneurs
docker compose ps

# Vérifier les logs
docker compose logs --tail=50

# Tester l'endpoint de santé
curl -s http://localhost:8000/api/health/live/

# Tester l'accès frontend
curl -s -o /dev/null -w "%{http_code}" https://korrigo.labomaths.tn/
```

### Étape 12 : Redémarrer Nginx si nécessaire

```bash
# Si Nginx est géré séparément
sudo systemctl reload nginx
```

---

## Commandes Utiles

### Voir les logs en temps réel
```bash
docker compose logs -f
```

### Voir les logs d'un service spécifique
```bash
docker compose logs -f backend
docker compose logs -f celery
docker compose logs -f nginx
```

### Redémarrer un service spécifique
```bash
docker compose restart backend
```

### Accéder au shell Django
```bash
docker compose exec backend python manage.py shell
```

### Créer un superuser
```bash
docker compose exec backend python manage.py createsuperuser
```

---

## En cas de problème

### Rollback vers la version précédente
```bash
# Arrêter les services
docker compose down

# Revenir au commit précédent
git checkout HEAD~1

# Reconstruire et redémarrer
docker compose build
docker compose up -d
```

### Restaurer la base de données
```bash
# Restaurer depuis le backup
cat backup_YYYYMMDD_HHMMSS.sql | docker compose exec -T db psql -U korrigo_user korrigo_db
```

### Vérifier les erreurs
```bash
# Logs du backend
docker compose logs backend --tail=100

# Logs Celery
docker compose logs celery --tail=100

# Logs Nginx
docker compose logs nginx --tail=100
```

---

## Script de Mise à Jour Automatique

Vous pouvez créer un script `update.sh` :

```bash
#!/bin/bash
set -e

echo "=== Mise à jour Korrigo ==="
echo "Date: $(date)"

# Backup
echo "1. Backup de la base de données..."
docker compose exec -T db pg_dump -U korrigo_user korrigo_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Stop
echo "2. Arrêt des services..."
docker compose down

# Pull
echo "3. Récupération des modifications..."
git pull origin main

# Build
echo "4. Reconstruction des images..."
docker compose build --no-cache

# Start
echo "5. Démarrage des services..."
docker compose up -d

# Migrate
echo "6. Migrations..."
docker compose exec -T backend python manage.py migrate --noinput

# Static
echo "7. Fichiers statiques..."
docker compose exec -T backend python manage.py collectstatic --noinput

# Health check
echo "8. Vérification..."
sleep 10
docker compose ps

echo "=== Mise à jour terminée ==="
```

Rendre exécutable : `chmod +x update.sh`

Exécuter : `./update.sh`
