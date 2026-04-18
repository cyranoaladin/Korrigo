---
description: Build + déploie le frontend en prod (inclut fix nginx image bakée)
---

# Deploy Frontend en Production

Ce workflow build le frontend Vue, le synchronise sur le serveur, et
**force nginx à servir le nouveau bundle** (car l'image `korrigo-nginx`
contient `dist/` bakée au build — un simple `rsync` sur le host ne suffit pas).

## Étapes

### 1. Build du frontend
// turbo
```bash
cd frontend && npm run build
```

### 2. Récupérer le hash du nouveau bundle (pour vérification)
// turbo
```bash
NEW_BUNDLE=$(ls -t frontend/dist/assets/index-*.js | head -1 | xargs basename)
echo "Nouveau bundle: $NEW_BUNDLE"
```

### 3. Synchroniser dist/ sur le serveur
// turbo
```bash
rsync -az --delete frontend/dist/ root@88.99.254.59:/var/www/labomaths/korrigo/frontend/dist/
```

### 4. Copier dist/ dans le conteneur nginx (CRUCIAL)
// turbo
```bash
ssh root@88.99.254.59 "docker cp /var/www/labomaths/korrigo/frontend/dist/. docker-nginx-1:/usr/share/nginx/html/ && docker exec docker-nginx-1 nginx -s reload"
```

### 5. Vérifier que nginx sert le nouveau bundle
// turbo
```bash
sleep 2
SERVED=$(curl -s "https://korrigo.labomaths.tn/?t=$(date +%s)" | grep -oE 'index-[A-Za-z0-9_-]+\.js' | head -1)
echo "Nginx sert: $SERVED"
echo "Attendu:    $NEW_BUNDLE"
[ "$SERVED" = "$NEW_BUNDLE" ] && echo "✅ Déploiement OK" || echo "❌ MISMATCH - vérifier"
```

### 6. Smoke tests prod (optionnel)
// turbo
```bash
curl -s -o /dev/null -w "/api/health/ -> %{http_code}\n" https://korrigo.labomaths.tn/api/health/
ssh root@88.99.254.59 "docker exec docker-db-1 psql -U korrigo_user -d korrigo_db -c 'SELECT (SELECT COUNT(*) FROM exams_copy) AS copies, (SELECT COUNT(*) FROM students_student) AS students;'"
```

## Notes

- **Ne jamais** faire `docker compose up -d nginx` pour déployer du nouveau
  frontend : cela recrée le conteneur depuis l'ancienne image (sans les
  derniers changements). Utiliser `docker cp` + `nginx -s reload`.
- Pour persister le changement (si on veut survivre à un `docker compose up`),
  il faut rebuilder l'image nginx : `docker compose build nginx && docker compose up -d nginx`.
- Le volume `docker_postgres_data` n'est jamais touché par ce workflow.
