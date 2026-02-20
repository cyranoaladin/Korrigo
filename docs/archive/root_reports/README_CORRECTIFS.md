# 🔧 Correctifs Korrigo - Guide Rapide

**Résumé** : Corrections appliquées pour résoudre les problèmes d'authentification (403) et d'upload (413).

---

## 🚀 Déploiement Rapide (3 commandes)

```bash
cd /home/alaeddine/viatique__PMF

# 1. Vérifier la configuration actuelle
bash scripts/check_config.sh

# 2. Déployer les correctifs (ou --dry-run pour simuler)
bash scripts/deploy_fixes.sh

# 3. Tester
bash scripts/diag_403.sh
```

---

## 📋 Qu'est-ce qui a été corrigé ?

### ✅ Correctif 1 : Cookies SameSite (CRITIQUE)
**Problème** : Après rechargement de page, `/api/me/` retourne 403 Forbidden.

**Cause** : `SESSION_COOKIE_SAMESITE` n'était pas réappliqué en production.

**Correction** :
- ✅ Modifié `backend/core/settings.py` ligne 119
- ✅ Créé `.env.labomaths` avec `SESSION_COOKIE_SAMESITE=None`

### ✅ Correctif 2 : Limite Upload (IMPORTANT)
**Problème** : Upload PDF > 100 MB échoue avec 413.

**Cause** : Limite Django à 100 MB.

**Correction** :
- ✅ Modifié `backend/core/settings.py` ligne 74 (1 GB)
- ⚠️ **Action manuelle requise** : Nginx externe (voir ci-dessous)

---

## ⚠️ Actions Manuelles Requises

### 1. Configuration .env

Éditer `.env` et remplacer les valeurs de template :

```bash
nano .env
```

**Variables à modifier** :
```bash
SECRET_KEY=CHANGE_THIS_TO_RANDOM_50_CHAR_STRING
DB_PASSWORD=CHANGE_THIS_TO_STRONG_PASSWORD
EMAIL_HOST_PASSWORD=CHANGE_THIS
```

**Générer une SECRET_KEY** :
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 2. Configuration Nginx Externe

Éditer la configuration Nginx externe :

```bash
sudo nano /etc/nginx/sites-available/labomaths_ecosystem
```

**Ajouter dans le bloc `server { ... }` pour `korrigo.labomaths.tn`** :

```nginx
server {
    listen 443 ssl http2;
    server_name korrigo.labomaths.tn;

    # ✅ AJOUTER CES LIGNES
    client_max_body_size 1G;
    client_body_timeout 3600s;
    proxy_connect_timeout 3600s;
    proxy_send_timeout 3600s;
    proxy_read_timeout 3600s;
    send_timeout 3600s;

    # Headers CRITIQUES pour cookies
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-Host $http_host;

    location / {
        proxy_pass http://localhost:8088;
    }
}
```

**Tester et recharger** :
```bash
sudo nginx -t
sudo systemctl reload nginx
```

**Configuration complète de référence** : `scripts/nginx_korrigo_config.conf`

---

## 🧪 Tests de Validation

### Test 1 : Vérifier la configuration
```bash
bash scripts/check_config.sh
```

**Résultat attendu** :
```
✅ SESSION_COOKIE_SAMESITE = None
✅ CSRF_COOKIE_SAMESITE = None
✅ SSL_ENABLED = true
✅ Fix SameSite présent dans settings.py
✅ DATA_UPLOAD_MAX_MEMORY_SIZE = 1GB
```

### Test 2 : Diagnostic complet
```bash
bash scripts/diag_403.sh
```

**Résultat attendu** :
```
✅ /api/me/ fonctionne avec curl + cookie jar.
Set-Cookie: sessionid=...; SameSite=None; Secure; HttpOnly
```

### Test 3 : Navigateur (manuel)

1. **Ouvrir** `https://korrigo.labomaths.tn`
2. **Login** avec vos identifiants
3. **Ouvrir DevTools** (F12) > Onglet **Application** > **Cookies**
4. **Vérifier** :
   - `sessionid` : **SameSite=None**, **Secure=✓**, **HttpOnly=✓**
   - `csrftoken` : **SameSite=None**, **Secure=✓**
5. **Recharger** la page (F5)
6. **Ouvrir DevTools** > Onglet **Network**
7. **Vérifier** : `/api/me/` → **200 OK** (pas 403)

### Test 4 : Upload PDF

1. **Aller dans** l'interface d'upload
2. **Uploader** un fichier PDF > 100 MB
3. **Vérifier** : Pas d'erreur 413

---

## 🐛 Dépannage

### Problème : 403 persiste après déploiement

**Vérifier** :
```bash
# 1. Configuration Django
docker exec $(docker ps | grep backend | awk '{print $1}') python -c "
from django.conf import settings
print(f'SESSION_COOKIE_SAMESITE = {settings.SESSION_COOKIE_SAMESITE}')
print(f'SESSION_COOKIE_SECURE = {settings.SESSION_COOKIE_SECURE}')
"

# 2. Cookies dans le navigateur (DevTools)
# sessionid doit avoir SameSite=None, Secure=✓

# 3. Headers de réponse (DevTools > Network > /api/login/)
# Set-Cookie doit contenir "SameSite=None; Secure"
```

**Solutions** :
- Si `SESSION_COOKIE_SAMESITE != None` → Vérifier `.env` et redémarrer backend
- Si cookies sans `Secure` → Vérifier Nginx `X-Forwarded-Proto: https`
- Si cookies avec `SameSite=Lax` → Redémarrer backend après modification `.env`

### Problème : 413 persiste

**Vérifier** :
```bash
# Nginx externe
sudo grep -r "client_max_body_size" /etc/nginx/sites-enabled/

# Doit afficher: client_max_body_size 1G;
```

**Solution** : Ajouter `client_max_body_size 1G;` dans Nginx externe et `sudo systemctl reload nginx`

### Problème : CORS error

**Vérifier** :
```bash
grep CORS_ALLOWED_ORIGINS .env
# Doit contenir: https://korrigo.labomaths.tn
```

**Solution** : Ajouter `CORS_ALLOWED_ORIGINS=https://korrigo.labomaths.tn` dans `.env` et redémarrer

---

## 📂 Fichiers Créés

| Fichier | Description |
|---------|-------------|
| `AUDIT_FINAL.md` | Rapport d'audit complet |
| `CORRECTIFS_403.md` | Guide de correction détaillé |
| `README_CORRECTIFS.md` | Ce document (guide rapide) |
| `.env.labomaths` | Template configuration production |
| `scripts/nginx_korrigo_config.conf` | Configuration Nginx de référence |
| `scripts/check_config.sh` | Script de vérification |
| `scripts/deploy_fixes.sh` | Script de déploiement |

---

## 📞 Support

**Documentation complète** : `AUDIT_FINAL.md`

**En cas de problème** :
1. Lire `CORRECTIFS_403.md`
2. Exécuter `bash scripts/check_config.sh`
3. Exécuter `bash scripts/diag_403.sh`
4. Vérifier les logs :
   ```bash
   docker-compose logs backend | tail -100
   sudo tail -100 /var/log/nginx/error.log
   ```

---

## ✅ Checklist Finale

- [ ] Exécuté `bash scripts/check_config.sh` → Tous les ✅
- [ ] Édité `.env` (SECRET_KEY, DB_PASSWORD)
- [ ] Configuré Nginx externe (`client_max_body_size 1G`)
- [ ] Redémarré backend (`docker-compose up -d --build`)
- [ ] Rechargé Nginx externe (`sudo systemctl reload nginx`)
- [ ] Exécuté `bash scripts/diag_403.sh` → ✅
- [ ] Testé dans navigateur (login + F5 + /api/me/ = 200 OK)
- [ ] Testé upload PDF > 100 MB → OK

---

**Version** : 1.0
**Date** : 2026-02-05
**Auteur** : Claude Code (Anthropic)
