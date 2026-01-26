# Guide de Déploiement - Korrigo PMF

> **Version**: 1.2.0  
> **Date**: Janvier 2026  
> **Public**: DevOps, Administrateurs Système

Guide complet pour déployer Korrigo PMF en environnement de production.

---

## 📋 Table des Matières

1. [Prérequis Production](#prérequis-production)
2. [Configurations Docker](#configurations-docker)
3. [Variables d'Environnement](#variables-denvironnement)
4. [Procédures de Déploiement](#procédures-de-déploiement)
5. [Backup et Restauration](#backup-et-restauration)
6. [Monitoring et Logs](#monitoring-et-logs)
7. [Checklist Pre-Production](#checklist-pre-production)

---

## Prérequis Production

### Infrastructure Minimale

| Ressource | Minimum | Recommandé | Usage |
|-----------|---------|------------|-------|
| **CPU** | 2 cores | 4 cores | Backend + Celery |
| **RAM** | 4 GB | 8 GB | PostgreSQL + Redis |
| **Disque** | 50 GB | 200 GB | DB + Media files |
| **Bande passante** | 10 Mbps | 100 Mbps | Upload PDF |

### Logiciels Requis

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Nginx** 1.25+ (reverse proxy)
- **Certbot** (SSL/TLS)

---

## Configurations Docker

### 1. docker-compose.prod.yml

**Production complète avec Nginx**:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    restart: always
    networks:
      - backend

  redis:
    image: redis:7
    restart: always
    networks:
      - backend

  backend:
    build: ../../backend
    command: gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - media_volume:/app/media
      - static_volume:/app/staticfiles
    environment:
      - DATABASE_URL=postgres://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - CELERY_BROKER_URL=redis://redis:6379/0
      - DEBUG=false
      - SSL_ENABLED=true
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
    restart: always
    networks:
      - backend

  celery:
    build: ../../backend
    command: celery -A core worker -l info
    volumes:
      - media_volume:/app/media
    environment:
      - DATABASE_URL=postgres://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: always
    networks:
      - backend

  nginx:
    image: nginx:1.25
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ../../infra/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - static_volume:/app/staticfiles:ro
      - media_volume:/app/media:ro
      - ../../frontend/dist:/app/frontend:ro
      - certbot_certs:/etc/letsencrypt:ro
    depends_on:
      - backend
    restart: always
    networks:
      - backend

volumes:
  postgres_data:
  media_volume:
  static_volume:
  certbot_certs:

networks:
  backend:
```

### 2. Configuration Nginx

**`infra/nginx/nginx.conf`**:

```nginx
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name viatique.example.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name viatique.example.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/viatique.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/viatique.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Frontend (Vue.js SPA)
    location / {
        root /app/frontend;
        try_files $uri $uri/ /index.html;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Django Admin
    location /admin/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Static Files
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media Files
    location /media/ {
        alias /app/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Upload Limit
    client_max_body_size 50M;
}
```

---

## Variables d'Environnement

### Fichier `.env.prod`

```bash
# Django
SECRET_KEY=<générer avec: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DEBUG=false
DJANGO_ENV=production
ALLOWED_HOSTS=viatique.example.com
CSRF_TRUSTED_ORIGINS=https://viatique.example.com
CORS_ALLOWED_ORIGINS=https://viatique.example.com

# Database
DB_NAME=viatique_prod
DB_USER=viatique_user
DB_PASSWORD=<mot de passe fort>
DATABASE_URL=postgres://viatique_user:<password>@db:5432/viatique_prod

# Redis
CELERY_BROKER_URL=redis://redis:6379/0

# Security
SSL_ENABLED=true
RATELIMIT_ENABLE=true

# Email (optionnel)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=<password>
```

### Générer SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Procédures de Déploiement

### Déploiement Initial

#### 1. Préparer le Serveur

```bash
# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Installer Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Cloner le dépôt
git clone https://github.com/votre-org/viatique__PMF.git
cd viatique__PMF
```

#### 2. Configurer l'Environnement

```bash
# Copier template
cp .env.example .env.prod

# Éditer variables
nano .env.prod
```

#### 3. Build Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

#### 4. Démarrer Services

```bash
docker-compose -f infra/docker/docker-compose.prod.yml --env-file .env.prod up -d --build
```

#### 5. Initialiser Base de Données

```bash
# Migrations
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py migrate

# Collecter static files
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# Créer super-utilisateur
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py createsuperuser
```

#### 6. Configurer SSL (Let's Encrypt)

```bash
# Installer Certbot
sudo apt install certbot python3-certbot-nginx

# Obtenir certificat
sudo certbot --nginx -d viatique.example.com

# Auto-renouvellement
sudo certbot renew --dry-run
```

---

### Mise à Jour (Rolling Update)

#### 1. Sauvegarder

```bash
# Backup DB
docker-compose -f infra/docker/docker-compose.prod.yml exec db pg_dump -U viatique_user viatique_prod > backup_$(date +%Y%m%d).sql

# Backup media
tar -czf media_backup_$(date +%Y%m%d).tar.gz backend/media/
```

#### 2. Pull Nouveau Code

```bash
git pull origin main
```

#### 3. Build Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

#### 4. Rebuild Services

```bash
docker-compose -f infra/docker/docker-compose.prod.yml --env-file .env.prod up -d --build
```

#### 5. Migrations

```bash
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py migrate
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

#### 6. Vérifier

```bash
# Logs
docker-compose -f infra/docker/docker-compose.prod.yml logs -f backend

# Health check
curl https://viatique.example.com/api/
```

---

### Rollback

```bash
# 1. Revenir à version précédente
git checkout <commit-hash>

# 2. Rebuild
docker-compose -f infra/docker/docker-compose.prod.yml up -d --build

# 3. Restaurer DB si nécessaire
docker-compose -f infra/docker/docker-compose.prod.yml exec -T db psql -U viatique_user viatique_prod < backup_20260125.sql
```

---

### Backup Automatique
Cette procédure utilise la commande interne `manage.py backup` qui génère une archive complète (JSON DB + Media).

**Script `/root/backup_viatique.sh`**:
```bash
#!/bin/bash
# Backup complet via Django
docker-compose -f /opt/viatique/infra/docker/docker-compose.prod.yml exec -T backend python manage.py backup --include-media --output-dir /backups/viatique
```

### Restauration
⚠️ **ATTENTION**: La restauration écrase les données existantes.

```bash
# 1. Identifier le dossier de backup
BACKUP_PATH="/backups/viatique/korrigo_backup_20260126_120000"

# 2. Lancer la restauration
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py restore $BACKUP_PATH
```

### Alternative (Raw PostgreSQL)
Pour les administrateurs DBAG, `pg_dump` reste utilisable pour la base de données seule.
```bash
docker-compose exec -T db pg_dump -U viatique_user viatique_prod | gzip > db.sql.gz
```

---

## Monitoring et Logs

### Logs Docker

```bash
# Tous les services
docker-compose -f infra/docker/docker-compose.prod.yml logs -f

# Backend uniquement
docker-compose -f infra/docker/docker-compose.prod.yml logs -f backend

# Dernières 100 lignes
docker-compose -f infra/docker/docker-compose.prod.yml logs --tail=100 backend
```

### Logs Nginx

```bash
# Access logs
docker-compose -f infra/docker/docker-compose.prod.yml exec nginx tail -f /var/log/nginx/access.log

# Error logs
docker-compose -f infra/docker/docker-compose.prod.yml exec nginx tail -f /var/log/nginx/error.log
```

### Monitoring Ressources

```bash
# Stats containers
docker stats

# Espace disque
df -h

# Taille volumes
docker system df -v
```

---

## Checklist Pre-Production

### Sécurité

- [ ] `SECRET_KEY` généré aléatoirement
- [ ] `DEBUG=false`
- [ ] SSL/TLS activé (Let's Encrypt)
- [ ] Firewall configuré (ports 80, 443 uniquement)
- [ ] Rate limiting activé
- [ ] CORS configuré strictement
- [ ] Headers de sécurité (CSP, HSTS, X-Frame-Options)
- [ ] Mots de passe DB forts

### Configuration

- [ ] `ALLOWED_HOSTS` configuré
- [ ] `CSRF_TRUSTED_ORIGINS` configuré
- [ ] Variables d'environnement validées
- [ ] Backup automatique configuré
- [ ] Monitoring configuré
- [ ] Logs rotatifs activés

### Tests

- [ ] Tests backend passent (100%)
- [ ] Tests E2E passent (100%)
- [ ] Load testing effectué
- [ ] Backup/Restore testé
- [ ] Rollback testé

### Documentation

- [ ] Procédures déploiement documentées
- [ ] Contacts support définis
- [ ] Runbook incidents créé

---

## Références

- [ARCHITECTURE.md](file:///home/alaeddine/viatique__PMF/docs/ARCHITECTURE.md) - Architecture globale
- [DEVELOPMENT_GUIDE.md](file:///home/alaeddine/viatique__PMF/docs/DEVELOPMENT_GUIDE.md) - Guide développement
- [SECURITY_GUIDE.md](file:///home/alaeddine/viatique__PMF/docs/SECURITY_GUIDE.md) - Guide sécurité

---

**Dernière mise à jour**: 25 janvier 2026  
**Auteur**: Aleddine BEN RHOUMA  
**Licence**: Propriétaire - AEFE/Éducation Nationale
