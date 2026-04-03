# Runbook Production - Korrigo

**Date**: 3 avril 2026
**Version**: 3.1
**Statut**: Exploitation courante

---

## 1. Références de production

- URL publique : `https://korrigo.labomaths.tn`
- Serveur : `root@88.99.254.59`
- Répertoire : `/var/www/labomaths/korrigo`
- Compose : `infra/docker/docker-compose.prod.yml`
- Point de santé de référence : `https://korrigo.labomaths.tn/api/health/`

---

## 2. Services attendus

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Services attendus :
- `docker-nginx-1`
- `docker-backend-1`
- `docker-db-1`
- `docker-redis-1`
- `docker-celery-1`
- `docker-celery-beat-1`

---

## 3. Vérifications rapides

```bash
curl -fsS https://korrigo.labomaths.tn/api/health/
curl -I https://korrigo.labomaths.tn/
docker logs docker-celery-beat-1 --since 5m | tail -20
```

Résultats attendus :
- `{"status":"healthy","database":"connected"}`
- `HTTP/2 200`
- logs `celery-beat` sans crash loop

---

## 4. Déploiement applicatif

```bash
ssh root@88.99.254.59
cd /var/www/labomaths/korrigo
git pull origin main
docker exec docker-backend-1 python manage.py migrate
docker restart docker-backend-1 docker-celery-1 docker-celery-beat-1
```

Après déploiement :

```bash
curl -fsS https://korrigo.labomaths.tn/api/health/
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

## 5. Sauvegardes

Le flux en production n’utilise plus une rétention locale longue.

Script actif :
- `/var/www/labomaths/korrigo/scripts/korrigo_backup.sh`

Comportement :
- exécution toutes les 30 minutes via cron
- dump DB + export JSON + archive media
- envoi vers Hetzner StorageBox
- rétention distante de 24h
- suppression locale après succès
- conservation locale d’au plus 2 fallbacks en cas d’échec

Contrôles :

```bash
tail -50 /var/log/korrigo_backup.log
crontab -l | grep korrigo_backup
ssh -i /root/.ssh/storagebox_ed25519 -p 23 u554481@u554481.your-storagebox.de \
  "ls backups/korrigo_backups/ | tail -5"
```

Archives historiques externalisées :
- dossier distant `backups/korrigo_archives_historiques/`
- manifeste local de contrôle :
  [storagebox_korrigo_archives_historiques_manifest_2026-04-03.txt](/home/alaeddine/Bureau/KORRIGO/korrigo_v2_improved/storagebox_korrigo_archives_historiques_manifest_2026-04-03.txt)

Notes RGPD / sécurité :
- `copies_data.json` est pseudonymisé dans le flux de backup
- le dump PostgreSQL et l'archive media restent complets pour la restauration
- le transfert vers le StorageBox est chiffré via SSH
- le chiffrement au repos des backups n'est pas assuré par l'application

---

## 6. Incidents courants

| Incident | Action immédiate |
|----------|------------------|
| `docker-celery-beat-1` down | `docker restart docker-celery-beat-1` puis vérifier les logs |
| API non accessible | vérifier `docker-nginx-1` et `docker-backend-1`, puis `curl -fsS https://korrigo.labomaths.tn/api/health/` |
| copie abandonnée `IN_PROGRESS` | `docker exec docker-backend-1 python manage.py recover_stuck_copies` |
| échec backup | lire `/var/log/korrigo_backup.log`, vérifier l’accès StorageBox et les dossiers `fallback_*` |

---

## 7. Notes d’exploitation

- `overlay/media/` n’est pas le stockage live en production ; le média actif est le volume Docker `media_volume`.
- le point de santé opérationnel de référence est celui exposé derrière Nginx, pas un endpoint local brut sur `localhost:8000`.
- ne jamais lancer `docker compose down -v` en production.
