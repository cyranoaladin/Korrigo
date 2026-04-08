# Nettoyage serveur de production — korrigo.labomaths.tn

**Date de rédaction** : 8 avril 2026
**Serveur** : `root@88.99.254.59` — `/var/www/labomaths/korrigo`

> ⚠️ Toutes les commandes ci-dessous doivent être exécutées **manuellement** par
> l'opérateur, après avoir vérifié chaque étape. Ne pas scripter en bloc.

---

## Pré-requis — Backup complet

```bash
# 1. Backup de la base PostgreSQL
cd /var/www/labomaths/korrigo/infra/docker
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U $POSTGRES_USER $POSTGRES_DB > /root/backup_pre_cleanup_$(date +%Y%m%d).sql

# 2. Backup du filesystem (hors backups automatiques et venv)
tar czf /root/korrigo_fs_backup_$(date +%Y%m%d).tar.gz \
  --exclude='./backups/automated' \
  --exclude='./overlay/.venv' \
  -C /var/www/labomaths/korrigo .
```

---

## 1. Supprimer le fichier artéfact malformé

```bash
rm -f '/var/www/labomaths/korrigo/infra/docker/{info[new_uuid]})'
```

## 2. Supprimer la base SQLite de dev dans le overlay

```bash
rm -f /var/www/labomaths/korrigo/overlay/backend/db.sqlite3
```

## 3. Nettoyer les `__pycache__` du overlay

```bash
find /var/www/labomaths/korrigo/overlay -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find /var/www/labomaths/korrigo/overlay -name "*.pyc" -delete 2>/dev/null
```

## 4. Supprimer les backups docker-compose obsolètes

```bash
rm -f /var/www/labomaths/korrigo/infra/docker/docker-compose.prod.yml.backup-*
rm -f /var/www/labomaths/korrigo/infra/docker/docker-compose.prod.yml.bak_*
rm -f /var/www/labomaths/korrigo/infra/docker/.env.bak*
```

## 5. Supprimer les fichiers `.bak` du overlay

```bash
rm -f /var/www/labomaths/korrigo/overlay/exams/models.py.bak_*
rm -f /var/www/labomaths/korrigo/overlay/grading/views_my_students.py.bak_*
rm -f /var/www/labomaths/korrigo/overlay/core/auth.py.bak
rm -f /var/www/labomaths/korrigo/overlay/exams/urls.py.bak
rm -f /var/www/labomaths/korrigo/overlay/exams/views.py,cover
```

## 6. Supprimer le virtualenv parasite

```bash
rm -rf /var/www/labomaths/korrigo/overlay/.venv
rm -rf /var/www/labomaths/korrigo/overlay/.pytest_cache
rm -f /var/www/labomaths/korrigo/overlay/.coverage
rm -f /var/www/labomaths/korrigo/overlay/.bandit
```

## 7. Supprimer la migration dupliquée fantôme

```bash
# Le chemin overlay/backend/core/ n'est jamais monté — seul overlay/core/ est utilisé
rm -rf /var/www/labomaths/korrigo/overlay/backend/
```

## 8. Unifier les fichiers `.env`

Vérifier que les deux fichiers `.env` sont cohérents :
```bash
diff /var/www/labomaths/korrigo/.env /var/www/labomaths/korrigo/infra/docker/.env
```
Si identiques, supprimer le doublon et créer un symlink :
```bash
rm /var/www/labomaths/korrigo/infra/docker/.env
ln -s /var/www/labomaths/korrigo/.env /var/www/labomaths/korrigo/infra/docker/.env
```

## 9. Auditer le overlay avant suppression future

**CRITIQUE** : Avant de supprimer le overlay, comparer chaque fichier avec le repo Git
pour identifier les patches locaux non commitées :
```bash
# Depuis le serveur, pour chaque fichier du overlay :
for f in $(find /var/www/labomaths/korrigo/overlay -name "*.py" -not -path "*__pycache__*"); do
    rel=${f#/var/www/labomaths/korrigo/overlay/}
    echo "=== $rel ==="
    diff "$f" "/path/to/repo/backend/$rel" 2>/dev/null || echo "(file missing in repo)"
done
```
Les différences doivent être commitées dans le repo ou documentées.

---

## Vérification post-nettoyage

```bash
cd /var/www/labomaths/korrigo
find . -maxdepth 1 -not -name '.' | sort
# Attendu :
# ./backups
# ./.env
# ./frontend
# ./infra
# ./overlay
# ./scripts
```

```bash
# Vérifier que les services fonctionnent toujours
cd infra/docker
docker compose -f docker-compose.prod.yml ps
curl -s http://localhost:8088/api/health/ | python3 -m json.tool
```
