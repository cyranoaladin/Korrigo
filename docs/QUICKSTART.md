# Guide de Démarrage Rapide Korrigo

> **Objectif**: Lancer Korrigo en moins de 5 minutes  
> **Public**: Développeurs, Administrateurs  
> **Prérequis**: Docker + Docker Compose installés

---

## 🚀 Installation en 3 Étapes

### Étape 1: Cloner le Projet

```bash
git clone <repository-url>
cd viatique__PMF
```

### Étape 2: Configuration

```bash
# Copier le fichier d'environnement
cp .env.example .env

# Éditer .env si nécessaire (optionnel pour développement local)
# Les valeurs par défaut fonctionnent pour un démarrage rapide
```

### Étape 3: Lancer l'Application

```bash
# Construire et démarrer tous les services
docker-compose up --build

# Attendre que tous les services soient prêts (environ 1-2 minutes)
# Vous verrez: "Listening at: http://0.0.0.0:8088" (backend)
#              "Local: http://localhost:5173/" (frontend)
```

---

## 🌐 Accès à l'Application

Une fois les services démarrés, accédez à:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | Interface utilisateur principale |
| **Backend API** | http://localhost:8088/api/ | API REST |
| **Admin Django** | http://localhost:8088/admin/ | Interface d'administration Django |
| **API Docs** | http://localhost:8088/api/docs/ | Documentation Swagger interactive |

---

## 👤 Créer le Premier Utilisateur

```bash
# Créer un superutilisateur (Admin)
docker-compose exec backend python manage.py createsuperuser

# Suivre les instructions:
# - Username: admin
# - Email: admin@example.com
# - Password: (votre mot de passe sécurisé)
```

---

## 📝 Premier Examen - Workflow Complet

### 1. Connexion

1. Ouvrez http://localhost:5173
2. Cliquez sur **"Admin"**
3. Connectez-vous avec les identifiants créés ci-dessus

### 2. Créer un Examen

1. Dans le tableau de bord Admin, cliquez **"Créer Nouvel Examen"**
2. Remplissez:
   - Nom: "Mathématiques - Bac Blanc"
   - Date: (aujourd'hui)
   - Pages par fascicule: 4
3. Cliquez **"Créer"**

### 3. Importer des Copies

1. Cliquez sur **"Importer Copies"** pour l'examen créé
2. Téléversez un fichier PDF (scans de copies)
3. Le système va automatiquement:
   - Rasteriser le PDF en images
   - Détecter les fascicules
   - Créer les copies

### 4. Valider les Copies (Staging)

1. Accédez à **"Agrafeuse"** (Staple View)
2. Vérifiez les fascicules détectés
3. Fusionnez si nécessaire
4. Validez chaque copie (STAGING → READY)

### 5. Créer le Barème

1. Cliquez sur **"Éditeur de Barème"**
2. Ajoutez des exercices et questions
3. Définissez les points pour chaque question
4. Sauvegardez

### 6. Corriger une Copie

1. Retournez au tableau de bord
2. Cliquez sur **"Corriger"** pour une copie
3. Interface de correction:
   - Dessinez des annotations (rouge)
   - Notez chaque question dans la barre latérale
   - Ajoutez une appréciation globale
4. Cliquez **"Finaliser"**

### 7. Exporter les Résultats

1. Tableau de bord → **"Export Pronote"**
2. Téléchargez le fichier CSV
3. Importez dans Pronote

---

## 🎓 Workflow Élève

### 1. Importer des Élèves

```bash
# Créer un fichier CSV: students.csv
# Format: Nom et Prénom,Date de naissance,Email,Classe,EDS,Groupe
# Exemple:
# DUPONT Jean,2005-03-15,jean.dupont@example.com,TS1,Maths-Physique,Groupe A
```

```bash
# Importer via l'admin Django
docker-compose exec backend python manage.py shell
```

```python
from students.services import StudentService
StudentService.import_from_csv('/path/to/students.csv')
```

### 2. Identifier les Copies

1. Admin Dashboard → **"Identification"**
2. Pour chaque copie:
   - Vérifiez le nom détecté par OCR
   - Associez à l'élève correct
   - Validez

### 3. Accès Élève

1. Élève ouvre http://localhost:5173
2. Clique **"Élève"**
3. Se connecte avec :
   - **Email** : adresse email scolaire (ex: `prenom.nom-e@ert.tn`)
   - **Mot de passe** : date de naissance au format JJMMAAAA (par défaut)
4. À la première connexion, changement de mot de passe obligatoire
5. Consulte ses copies corrigées avec bannière de transparence

---

## 🛠️ Commandes Utiles

### Gestion des Services

```bash
# Arrêter tous les services
docker-compose down

# Redémarrer un service spécifique
docker-compose restart backend

# Voir les logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Accéder au shell backend
docker-compose exec backend python manage.py shell

# Accéder au shell PostgreSQL
docker-compose exec db psql -U korrigo -d korrigo
```

### Migrations Base de Données

```bash
# Créer des migrations
docker-compose exec backend python manage.py makemigrations

# Appliquer les migrations
docker-compose exec backend python manage.py migrate

# Voir l'état des migrations
docker-compose exec backend python manage.py showmigrations
```

### Tests

```bash
# Tests backend (pytest)
docker-compose exec backend pytest

# Tests E2E (Playwright)
cd frontend
npx playwright test

# Tests avec interface UI
npx playwright test --ui
```

### Nettoyage

```bash
# Arrêter et supprimer les conteneurs (GARDE LES VOLUMES)
docker-compose down

# ⚠️ ATTENTION: Supprimer TOUT (conteneurs + volumes + données)
docker-compose down -v

# Reconstruire les images
docker-compose build --no-cache
```

---

## 📊 Données de Démonstration

Pour tester rapidement avec des données fictives:

```bash
# Charger des données de démonstration
docker-compose exec backend python manage.py loaddata seed_demo.json

# Ou utiliser le script de seed
docker-compose exec backend python seed_demo_exam.py
```

Cela créera:
- 1 examen de démonstration
- 5 copies avec annotations
- 10 élèves fictifs
- 3 utilisateurs (admin, teacher, student)

---

## 🔍 Dépannage Rapide

### Le frontend ne se connecte pas au backend

**Symptôme**: Erreurs CORS ou "Network Error"

**Solution**:
```bash
# Vérifier que le backend est démarré
docker-compose logs backend | grep "Listening"

# Vérifier les variables d'environnement
docker-compose exec backend env | grep CORS
```

### Erreur "Port already in use"

**Symptôme**: `Error starting userland proxy: listen tcp4 0.0.0.0:5173: bind: address already in use`

**Solution**:
```bash
# Trouver le processus utilisant le port
lsof -i :5173

# Tuer le processus
kill -9 <PID>

# Ou changer le port dans docker-compose.yml
```

### Base de données corrompue

**Symptôme**: Erreurs de migration ou données incohérentes

**Solution**:
```bash
# Réinitialiser complètement (⚠️ PERTE DE DONNÉES)
docker-compose down -v
docker-compose up --build

# Recréer le superuser
docker-compose exec backend python manage.py createsuperuser
```

### Celery worker ne démarre pas

**Symptôme**: Tâches asynchrones ne s'exécutent pas

**Solution**:
```bash
# Vérifier les logs Celery
docker-compose logs celery

# Redémarrer Celery
docker-compose restart celery

# Vérifier Redis
docker-compose exec redis redis-cli ping
# Devrait répondre: PONG
```

---

## 📚 Prochaines Étapes

Maintenant que vous avez Korrigo en fonctionnement:

1. **Comprendre l'Architecture**: [ARCHITECTURE.md](technical/ARCHITECTURE.md)
2. **Développement Local**: [DEVELOPMENT_GUIDE.md](development/DEVELOPMENT_GUIDE.md)
3. **Déploiement Production**: [DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md)
4. **Documentation API**: http://localhost:8088/api/docs/
5. **Guide Utilisateur**: [INDEX.md](INDEX.md)

---

## 💡 Conseils

### Pour le Développement

- Utilisez `docker-compose logs -f` pour suivre les logs en temps réel
- Les modifications du code backend nécessitent un redémarrage: `docker-compose restart backend`
- Les modifications du code frontend sont appliquées automatiquement (hot reload)
- Utilisez Django Debug Toolbar en développement (déjà configuré)

### Pour la Production

- **NE JAMAIS** utiliser `docker-compose.yml` en production
- Utilisez `infra/docker/docker-compose.prod.yml`
- Configurez SSL/TLS (voir [DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md))
- Configurez les backups automatiques
- Activez le monitoring (Prometheus + Grafana)

---

## 🆘 Besoin d'Aide?

- **FAQ**: [FAQ.md](support/FAQ.md)
- **Dépannage Complet**: [DEPANNAGE.md](support/DEPANNAGE.md)
- **Support**: [SUPPORT.md](support/SUPPORT.md)

---

**Dernière mise à jour**: 10 mars 2026  
**Version**: 1.1
