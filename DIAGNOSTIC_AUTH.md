# 🔍 DIAGNOSTIC - Problème d'Authentification 403

## 🚨 Symptômes
- Erreurs 403 sur `/api/me/` et `/api/students/me/`
- L'enseignant ne peut pas accéder à son profil après login
- Le changement de mot de passe échoue

## 🎯 Cause Probable

**Configuration CORS/Session incorrecte en production**

En production sur `korrigo.labomaths.tn` :
- Frontend et backend sont sur le **même domaine** (via Nginx)
- CORS n'est **pas nécessaire** (same-origin)
- Les cookies de session doivent être configurés correctement

## 🔧 Solution

### 1. Vérifier le fichier `.env` sur le serveur

```bash
# Sur le serveur
cat /var/www/labomaths/korrigo/.env
```

**Configuration requise :**

```bash
# Django Environment
DJANGO_ENV=production
DEBUG=False
SECRET_KEY=<votre_secret_key>

# Allowed Hosts
ALLOWED_HOSTS=korrigo.labomaths.tn,localhost,127.0.0.1

# CORS Configuration (VIDE car same-origin)
CORS_ALLOWED_ORIGINS=

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS=https://korrigo.labomaths.tn

# SSL Configuration
SSL_ENABLED=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SAMESITE=Lax

# Database
DB_NAME=korrigo_db
DB_USER=korrigo_user
DB_PASSWORD=<votre_password>
DB_HOST=db
DB_PORT=5432

# Metrics
METRICS_TOKEN=<votre_token>
```

### 2. Si le `.env` n'existe pas ou est incorrect

```bash
# Sur le serveur
cd /var/www/labomaths/korrigo

# Créer/éditer le .env
nano .env

# Copier la configuration ci-dessus
# Sauvegarder : Ctrl+O, Enter, Ctrl+X

# Redémarrer le backend
docker compose -f docker-compose.labomaths.yml restart backend

# Vérifier les logs
docker logs korrigo-backend-1 --tail 50
```

### 3. Vérifier que le backend charge le .env

```bash
# Sur le serveur
docker exec korrigo-backend-1 python manage.py shell -c "
import os
print('DJANGO_ENV:', os.environ.get('DJANGO_ENV'))
print('DEBUG:', os.environ.get('DEBUG'))
print('ALLOWED_HOSTS:', os.environ.get('ALLOWED_HOSTS'))
print('CORS_ALLOWED_ORIGINS:', os.environ.get('CORS_ALLOWED_ORIGINS'))
print('CSRF_TRUSTED_ORIGINS:', os.environ.get('CSRF_TRUSTED_ORIGINS'))
print('SSL_ENABLED:', os.environ.get('SSL_ENABLED'))
"
```

### 4. Tester l'authentification

```bash
# Test login
curl -v -X POST https://korrigo.labomaths.tn/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"HilbertGalois"}' \
  -c cookies.txt

# Test /api/me/ avec les cookies
curl -v https://korrigo.labomaths.tn/api/me/ \
  -b cookies.txt
```

**Résultat attendu :**
- Login retourne `200 OK` avec `Set-Cookie: sessionid=...`
- `/api/me/` retourne `200 OK` avec les données utilisateur (pas 403)

## 📋 Checklist de Vérification

- [ ] Le fichier `.env` existe sur le serveur
- [ ] `ALLOWED_HOSTS` contient `korrigo.labomaths.tn`
- [ ] `CSRF_TRUSTED_ORIGINS` contient `https://korrigo.labomaths.tn`
- [ ] `CORS_ALLOWED_ORIGINS` est **vide** (same-origin)
- [ ] `SSL_ENABLED=True` (car HTTPS)
- [ ] `SESSION_COOKIE_SECURE=True` (car HTTPS)
- [ ] Le backend redémarre après modification du `.env`
- [ ] Les cookies sont envoyés correctement par le navigateur

## 🔍 Logs à Vérifier

```bash
# Logs backend
docker logs korrigo-backend-1 --tail 100 | grep -i "403\|forbidden\|cors\|csrf"

# Logs Nginx
docker logs korrigo-frontend_nginx-1 --tail 100
```

## 🎯 Résolution Attendue

Après correction du `.env` :
1. Login enseignant → Session créée
2. Cookie `sessionid` envoyé au navigateur
3. Requêtes suivantes incluent le cookie
4. `/api/me/` retourne `200 OK` (pas 403)
5. Changement de mot de passe fonctionne

---

**Si le problème persiste après ces corrections, vérifiez :**
- Les logs du backend pour les erreurs de session
- La configuration Nginx (proxy_set_header)
- Les cookies dans les DevTools du navigateur
