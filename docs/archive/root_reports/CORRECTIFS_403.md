# 🔧 Guide de Correction - Problème 403 Forbidden

## Problèmes Identifiés

### 1. Configuration Django settings.py (CRITIQUE)
**Problème** : Les variables `SESSION_COOKIE_SAMESITE` et `CSRF_COOKIE_SAMESITE` ne sont pas réappliquées en production.

**Correction appliquée** :
- ✅ Fichier `backend/core/settings.py` ligne ~119 : Ajout de la réassignation des valeurs SameSite

### 2. Configuration .env (CRITIQUE)
**Problème** : Les variables d'environnement pour les cookies SameSite ne sont pas définies.

**Correction requise** :
```bash
# Dans votre fichier .env de production (copier .env.labomaths)
SESSION_COOKIE_SAMESITE=None
CSRF_COOKIE_SAMESITE=None
CORS_ALLOWED_ORIGINS=https://korrigo.labomaths.tn
CSRF_TRUSTED_ORIGINS=https://korrigo.labomaths.tn
SSL_ENABLED=true
```

### 3. Nginx externe (CRITIQUE)
**Problème** : `client_max_body_size` potentiellement manquant ou trop petit.

**Correction requise** :
```nginx
server {
    listen 443 ssl http2;
    server_name korrigo.labomaths.tn;

    # AJOUTER CES LIGNES :
    client_max_body_size 1G;
    proxy_connect_timeout 3600s;
    proxy_send_timeout 3600s;
    proxy_read_timeout 3600s;

    # Headers CRITIQUES pour cookies
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-Host $http_host;

    location / {
        proxy_pass http://localhost:8088;  # Port de votre container frontend
    }
}
```

Fichier de référence : `scripts/nginx_korrigo_config.conf`

### 4. Limites Django (IMPORTANT)
**Problème** : `FILE_UPLOAD_MAX_MEMORY_SIZE` limité à 100 MB.

**Correction appliquée** :
- ✅ Fichier `backend/core/settings.py` ligne ~74 : Augmenté à 1 GB

---

## 🚀 Procédure de Déploiement

### Étape 1 : Backup
```bash
cd /home/alaeddine/viatique__PMF
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
```

### Étape 2 : Copier la nouvelle configuration
```bash
# Copier le template .env.labomaths et l'adapter
cp .env.labomaths .env

# IMPORTANT : Éditer .env et remplacer :
# - SECRET_KEY (générer avec: python -c "import secrets; print(secrets.token_urlsafe(50))")
# - DB_PASSWORD
# - EMAIL_* si nécessaire
nano .env
```

### Étape 3 : Redéployer le backend
```bash
# Si vous utilisez Docker Compose
docker-compose -f infra/docker/docker-compose.prod.yml down
docker-compose -f infra/docker/docker-compose.prod.yml build backend
docker-compose -f infra/docker/docker-compose.prod.yml up -d

# Vérifier les logs
docker-compose -f infra/docker/docker-compose.prod.yml logs -f backend
```

### Étape 4 : Vérifier la configuration Django
```bash
# Vérifier que les paramètres sont bien chargés
docker exec -it korrigo-backend-1 python manage.py shell

# Dans le shell Python :
from django.conf import settings
print(f"SESSION_COOKIE_SAMESITE = {settings.SESSION_COOKIE_SAMESITE}")
print(f"CSRF_COOKIE_SAMESITE = {settings.CSRF_COOKIE_SAMESITE}")
print(f"SESSION_COOKIE_SECURE = {settings.SESSION_COOKIE_SECURE}")
print(f"CORS_ALLOWED_ORIGINS = {settings.CORS_ALLOWED_ORIGINS}")
# Devrait afficher :
# SESSION_COOKIE_SAMESITE = None
# CSRF_COOKIE_SAMESITE = None
# SESSION_COOKIE_SECURE = True
```

### Étape 5 : Mettre à jour Nginx externe
```bash
# Sauvegarder la config actuelle
sudo cp /etc/nginx/sites-available/labomaths_ecosystem /etc/nginx/sites-available/labomaths_ecosystem.backup.$(date +%Y%m%d)

# Éditer la configuration
sudo nano /etc/nginx/sites-available/labomaths_ecosystem

# Ajouter les lignes du fichier scripts/nginx_korrigo_config.conf

# Tester la configuration
sudo nginx -t

# Si OK, recharger
sudo systemctl reload nginx
```

### Étape 6 : Tester avec le script de diagnostic
```bash
cd /home/alaeddine/viatique__PMF
bash scripts/diag_403.sh

# Vérifier dans la sortie :
# - "✅ /api/me/ fonctionne avec curl + cookie jar."
# - Set-Cookie doit contenir "SameSite=None; Secure"
```

### Étape 7 : Tester dans le navigateur
```bash
# 1. Ouvrir https://korrigo.labomaths.tn
# 2. Se connecter
# 3. Vérifier dans DevTools > Application > Cookies :
#    - sessionid : SameSite=None, Secure=true
#    - csrftoken : SameSite=None, Secure=true
# 4. Recharger la page (F5)
# 5. Vérifier que /api/me/ retourne 200 OK (DevTools > Network)
```

---

## 🔍 Diagnostic si le problème persiste

### Vérifier les cookies dans le navigateur

1. Ouvrir DevTools (F12)
2. Onglet **Application** > **Cookies** > `https://korrigo.labomaths.tn`
3. Vérifier :
   - ✅ `sessionid` : **SameSite=None**, **Secure=✓**, **HttpOnly=✓**
   - ✅ `csrftoken` : **SameSite=None**, **Secure=✓**, **HttpOnly=✗**

### Vérifier les headers de réponse

Dans DevTools > **Network** :
1. Après le login, vérifier la réponse de `/api/login/`
2. Onglet **Headers** > **Response Headers** :
   ```
   Set-Cookie: sessionid=...; Domain=korrigo.labomaths.tn; Path=/; Secure; HttpOnly; SameSite=None
   Set-Cookie: csrftoken=...; Domain=korrigo.labomaths.tn; Path=/; Secure; SameSite=None
   ```

### Logs Django

```bash
# Voir les logs du backend
docker-compose -f infra/docker/docker-compose.prod.yml logs -f backend | grep -i cookie
```

---

## 🐛 Problèmes courants et solutions

### Problème : "SameSite=Lax" au lieu de "SameSite=None"
**Cause** : Le .env n'est pas chargé ou les variables ne sont pas définies.
**Solution** : Vérifier que `SESSION_COOKIE_SAMESITE=None` est dans `.env` ET que le backend a été redémarré.

### Problème : Cookies non envoyés malgré SameSite=None
**Cause** : `Secure` n'est pas défini OU le navigateur ne détecte pas HTTPS.
**Solution** :
- Vérifier `SESSION_COOKIE_SECURE=True` dans Django
- Vérifier `proxy_set_header X-Forwarded-Proto https;` dans Nginx

### Problème : CORS error "credentials mode 'include'"
**Cause** : `CORS_ALLOW_CREDENTIALS` n'est pas activé ou `CORS_ALLOWED_ORIGINS` incorrect.
**Solution** :
- Vérifier `CORS_ALLOW_CREDENTIALS=True` dans settings.py (ligne 452)
- Vérifier `CORS_ALLOWED_ORIGINS=https://korrigo.labomaths.tn` dans .env

### Problème : 413 Request Entity Too Large
**Cause** : Nginx externe n'a pas `client_max_body_size 1G`.
**Solution** : Ajouter la directive dans le bloc server{} de Nginx externe.

---

## 📞 Support

Si les problèmes persistent après ces corrections :

1. **Exécuter le diagnostic complet** :
   ```bash
   bash scripts/diag_403.sh > diagnostic_$(date +%Y%m%d_%H%M%S).txt
   ```

2. **Collecter les logs** :
   ```bash
   docker-compose -f infra/docker/docker-compose.prod.yml logs backend > backend_logs.txt
   sudo tail -100 /var/log/nginx/korrigo_error.log > nginx_error.txt
   ```

3. **Vérifier la configuration Django** :
   ```bash
   docker exec korrigo-backend-1 python manage.py diffsettings | grep -E "COOKIE|CORS|CSRF"
   ```

---

## ✅ Checklist de validation

- [ ] `backend/core/settings.py` modifié (lignes ~119)
- [ ] `.env` créé avec `SESSION_COOKIE_SAMESITE=None`
- [ ] `backend/core/settings.py` modifié (ligne ~74, FILE_UPLOAD_MAX_MEMORY_SIZE=1GB)
- [ ] Backend redéployé et redémarré
- [ ] Nginx externe mis à jour avec `client_max_body_size 1G`
- [ ] Nginx externe reloadé (`sudo systemctl reload nginx`)
- [ ] Script `scripts/diag_403.sh` exécuté avec succès (✅)
- [ ] Test navigateur : login → rechargement → /api/me/ = 200 OK
- [ ] Test upload PDF > 100 MB réussi

---

**Auteur** : Audit Claude Code
**Date** : 2026-02-05
