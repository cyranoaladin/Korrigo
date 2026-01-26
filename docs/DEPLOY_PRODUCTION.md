# Korrigo Production Deployment Guide

## 🚀 Vue d'ensemble
Ce document décrit la procédure de déploiement en production de Korrigo.
L'architecture repose sur Docker Compose, avec images hébergées sur GHCR.

## 📋 Pré-requis Serveur (VPS)
1.  **OS**: Linux (Ubuntu 22.04+ recommandé)
2.  **Docker**: Engine 24+ & Compose Plugin
3.  **Ports**: 8088 (HTTP), 22 (SSH) ouverts

## 🛠 Installation Initiale
Sur le VPS :

```bash
# 1. Cloner le repo
git clone https://github.com/cyranoaladin/Korrigo.git /home/ubuntu/korrigo
cd /home/ubuntu/korrigo

# 2. Créer le fichier .env
cp .env.example .env
nano .env
# Remplir les variables critiques :
# - SECRET_KEY (Générer une clé forte)
# - POSTGRES_PASSWORD
# - DJANGO_ENV=production
# - ALLOWED_HOSTS=ip.du.serveur,domaine.com
# - CORS_ALLOWED_ORIGINS=http://ip.du.serveur:8088
```

## 🔄 Déploiement Continu (CI/CD)
Le déploiement est automatisé via GitHub Actions (`.github/workflows/deploy.yml`).
Chaque push sur `main` déclenche :
1.  Build des images Docker (Backend & Nginx).
2.  Push sur GHCR (GitHub Container Registry).
3.  Connexion SSH au VPS.
4.  Pull des nouvelles images.
5.  Migration de la base de données.
6.  Redémarrage des services (Zero-downtime partiel).

### Configuration Secrets GitHub
Dans `Settings > Secrets and variables > Actions` :
*   `GHCR_USER` : Username GitHub.
*   `GHCR_PAT` : Personal Access Token (read:packages, write:packages).
*   `VPS_HOST` : IP du serveur.
*   `VPS_USER` : Utilisateur SSH (ex: ubuntu).
*   `VPS_SSH_KEY` : Clé privée SSH (Format PEM).
*   `VPS_PATH` : Chemin absolu (ex: `/home/ubuntu/korrigo`).

## ✅ Checklist de Mise en Production (À exécuter avant ouverture)

### 1. Sécurité
- [ ] `DEBUG=False` dans le `.env`
- [ ] `SECRET_KEY` est unique et forte
- [ ] `ALLOWED_HOSTS` contient uniquement le domaine/IP de prod (pas `*`)
- [ ] Firewall activé (UFW allow 8088, 22)

### 2. Données
- [ ] Backup de la base de données initialisé
- [ ] Volume `media_volume` persistant vérifié

### 3. Application
- [ ] Création du premier superuser :
    ```bash
    docker compose -f infra/docker/docker-compose.prod.yml run --rm backend python manage.py createsuperuser
    ```
- [ ] Initialisation des données de base (Groupes) :
    ```bash
    docker compose -f infra/docker/docker-compose.prod.yml run --rm backend python manage.py init_pmf
    ```

## 🚨 Troubleshooting
En cas de problème :

**Voir les logs :**
```bash
docker compose -f infra/docker/docker-compose.prod.yml logs -f --tail=100
```

**Restart forcé :**
```bash
docker compose -f infra/docker/docker-compose.prod.yml down
docker compose -f infra/docker/docker-compose.prod.yml up -d
```

**Rollback :**
Si une version casse tout, repasser sur le hash précédent :
```bash
export KORRIGO_SHA=le_hash_precedent
docker compose -f infra/docker/docker-compose.prod.yml up -d
```
