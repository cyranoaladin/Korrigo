# Déploiement Korrigo

## Pré-requis

- Docker + Docker Compose v2
- Accès SSH au serveur `88.99.254.59`
- Fichier `.env` configuré sur le serveur (voir variables obligatoires ci-dessous)

### Variables `.env` obligatoires

```
SECRET_KEY=...
ALLOWED_HOSTS=korrigo.labomaths.tn
POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
DEFAULT_PASSWORD=...
CORS_ALLOWED_ORIGINS=https://korrigo.labomaths.tn
CSRF_TRUSTED_ORIGINS=https://korrigo.labomaths.tn
KORRIGO_SHA=...
GITHUB_REPOSITORY_OWNER=cyranoaladin
```

---

## Build des images

```bash
# Depuis la racine du repo
docker build -t ghcr.io/cyranoaladin/korrigo-backend:$(git rev-parse --short HEAD) backend/
docker build -t ghcr.io/cyranoaladin/korrigo-nginx:$(git rev-parse --short HEAD) -f infra/nginx/Dockerfile .
```

## Push des images

```bash
docker push ghcr.io/cyranoaladin/korrigo-backend:$(git rev-parse --short HEAD)
docker push ghcr.io/cyranoaladin/korrigo-nginx:$(git rev-parse --short HEAD)
```

## Déploiement sur le serveur

```bash
ssh root@88.99.254.59
cd /var/www/labomaths/korrigo/infra/docker
export KORRIGO_SHA=<commit_sha>
# Update .env with new SHA
sed -i "s|^KORRIGO_SHA=.*|KORRIGO_SHA=${KORRIGO_SHA}|" ../../.env
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f --tail 50
```

## Vérification

```bash
curl -s https://korrigo.labomaths.tn/api/health/ | python3 -m json.tool
```

## Rollback

```bash
export KORRIGO_SHA=<previous_sha>
sed -i "s|^KORRIGO_SHA=.*|KORRIGO_SHA=${KORRIGO_SHA}|" ../../.env
docker compose -f docker-compose.prod.yml up -d
```

---

## CI/CD automatique

Le workflow `.github/workflows/deploy.yml` exécute automatiquement sur push `main` :
1. Frontend lint + build
2. Backend tests (pytest)
3. Build & push des images Docker (GHCR)
4. Déploiement SSH sur le serveur (si les secrets `VPS_*` sont configurés)
5. Health check post-déploiement

### Secrets GitHub requis (Settings > Environments > production)

| Secret | Description |
|--------|-------------|
| `VPS_HOST` | IP du serveur (88.99.254.59) |
| `VPS_USER` | Utilisateur SSH (root) |
| `VPS_SSH_KEY` | Clé SSH privée |
| `VPS_PATH` | Chemin déploiement (/var/www/labomaths/korrigo) |
