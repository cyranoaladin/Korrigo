# Guide de Référence Rapide - Korrigo

**Auteur** : Alaeddine BEN RHOUMA
**Date** : 23 Mars 2026

---

## 🎯 Accès Rapide

### URLs Production

- **Application** : https://korrigo.labomths.tn
- **Django Admin** : https://korrigo.labomths.tn/admin/
- **API Docs** : https://korrigo.labomths.tn/api/docs/
- **Health Check** : https://korrigo.labomths.tn/api/health/

### URLs Développement Local

- **Application** : http://localhost:8088
- **Django Admin** : http://localhost:8088/admin/
- **API** : http://localhost:8088/api/

---

## 👥 Comptes de Test (Local)

| Profil | Username | Password | Accès |
|--------|----------|----------|-------|
| **Admin** | test_admin | admin123 | Complet |
| **Professeur** | test_prof | prof123 | Correction |
| **Étudiant** | test_student | student123 | Consultation |
| **Étudiant** | eleve1 | eleve2025 | Consultation |

---

## 📂 Structure Documentation

```
documentation/
├── 00-INDEX-GENERAL.md                    ✅ CRÉÉ
│
├── 01-architecture/
│   ├── 01.1-Vue-Ensemble.md              ✅ CRÉÉ
│   ├── 01.2-Backend-Django.md
│   ├── 01.3-Frontend-Vue.md
│   ├── 01.4-Base-Donnees.md
│   └── 01.5-Infrastructure.md
│
├── 02-workflows/
│   ├── 02.1-Workflow-Admin-Creation-Examen.md  ✅ CRÉÉ
│   ├── 02.2-Workflow-Upload-Scans.md
│   ├── 02.3-Workflow-Traitement-PDF.md
│   ├── 02.4-Workflow-OCR-Identification.md
│   ├── 02.5-Workflow-Anonymisation.md
│   ├── 02.6-Workflow-Correction.md
│   ├── 02.7-Workflow-Finalisation.md
│   └── 02.8-Workflow-Consultation-Eleve.md
│
├── 03-api/
│   ├── 03.1-Authentification.md
│   ├── 03.2-API-Examens.md
│   ├── 03.3-API-Copies.md
│   ├── 03.4-API-Identification.md
│   ├── 03.5-API-Etudiants.md
│   └── 03.6-Codes-Erreur.md
│
├── 04-database/
│   ├── 04.1-Schema-Complet.md
│   ├── 04.2-Modeles-Core.md
│   ├── 04.3-Modeles-Exams.md
│   ├── 04.4-Modeles-Grading.md
│   ├── 04.5-Modeles-Students.md
│   ├── 04.6-Modeles-Processing.md
│   └── 04.7-Migrations.md
│
├── 05-frontend/
│   ├── 05.1-Architecture-Vue.md
│   ├── 05.2-Routes.md
│   ├── 05.3-Composants-Admin.md
│   ├── 05.4-Composants-Teacher.md
│   ├── 05.5-Composants-Student.md
│   └── 05.6-State-Management.md
│
├── 06-deployment/
│   ├── 06.1-Environnements.md
│   ├── 06.2-Installation-Locale.md
│   ├── 06.3-Deploiement-Production.md
│   ├── 06.4-Configuration-Nginx.md
│   └── 06.5-Monitoring.md
│
└── 07-annexes/
    ├── 07.1-Profils-Permissions.md
    ├── 07.2-Format-CSV.md
    ├── 07.3-Format-PDF.md
    ├── 07.4-OCR-Details.md
    ├── 07.5-Securite.md
    ├── 07.6-Performance.md
    ├── 07.7-Tests.md
    └── 07.8-Glossaire.md
```

---

## 🚀 Workflows Principaux

### 1. Créer un Examen (Admin)

```
1. Login admin
2. Dashboard → "Créer Examen"
3. Remplir formulaire (nom, date, barème)
4. Import CSV élèves
5. Upload PDF scans
6. Desk d'identification (si nécessaire)
7. Distribution aux correcteurs
```

**Temps** : 20-30 minutes
**Documentation** : [02.1-Workflow-Admin-Creation-Examen.md](./02-workflows/02.1-Workflow-Admin-Creation-Examen.md)

### 2. Corriger des Copies (Professeur)

```
1. Login professeur
2. Liste des copies assignées
3. Ouvrir copie
4. Annoter PDF (surlignage, commentaires, tampon V/X)
5. Attribuer notes par question (split view disponible)
6. Ajouter commentaires
7. Sauvegarder (auto-save)
8. Finaliser (lock)
```

**Temps** : 10-15 min par copie
**Documentation** : [02.6-Workflow-Correction.md](./02-workflows/02.6-Workflow-Correction.md)

### 3. Consulter sa Copie (Étudiant)

```
1. Portail élève → Login (email + date naissance)
2. Liste des examens
3. Cliquer sur examen
4. Visualiser copie corrigée
5. Voir annotations et notes
6. Télécharger PDF
```

**Temps** : 2-3 minutes
**Documentation** : [02.8-Workflow-Consultation-Eleve.md](./02-workflows/02.8-Workflow-Consultation-Eleve.md)

---

## 🔧 Commandes Utiles

### Docker Compose

```bash
# Démarrer tous les services
docker compose -f infra/docker/docker-compose.local-prod.yml up -d

# Voir les logs
docker compose -f infra/docker/docker-compose.local-prod.yml logs -f

# Arrêter
docker compose -f infra/docker/docker-compose.local-prod.yml down

# Rebuild
docker compose -f infra/docker/docker-compose.local-prod.yml up -d --build
```

### Django Management

```bash
# Shell Django
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend python manage.py shell

# Migrations
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend python manage.py migrate

# Create superuser
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend python manage.py createsuperuser

# Collect static
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend python manage.py collectstatic --noinput
```

### Tests

```bash
# Tous les tests
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend pytest

# Tests spécifiques
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend pytest processing/tests/test_batch_processor.py

# Avec coverage
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend pytest --cov
```

---

## 📊 APIs Principales

### Authentification

```http
POST /api/login/
{
  "username": "test_admin",
  "password": "admin123"
}
```

### Examens

```http
GET /api/exams/                    # Liste
POST /api/exams/                   # Créer
GET /api/exams/{id}/               # Détails
PUT /api/exams/{id}/               # Modifier
POST /api/exams/upload/            # Upload PDF
```

### Copies

```http
GET /api/grading/copies/                    # Liste
GET /api/grading/copies/{id}/               # Détails
PATCH /api/grading/copies/{id}/             # Modifier
POST /api/grading/copies/{id}/lock/         # Verrouiller
POST /api/grading/copies/{id}/force-unlock/ # Déverrouillage forcé (admin)
POST /api/grading/copies/{id}/reopen/       # Réouverture GRADED→READY (admin)
```

### Identification

```http
GET /api/identification/copies/{id}/ocr-candidates/     # Candidats OCR
POST /api/identification/copies/{id}/select-candidate/  # Sélectionner
```

**Documentation complète** : [Section 03 - API](./03-api/)

---

## 🗄️ Modèles Principaux

### Exam

```python
class Exam(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    date = models.DateField()
    pdf_source = models.FileField()
    is_processed = models.BooleanField(default=False)
    creator = models.ForeignKey(User)
```

### Copy

```python
class Copy(models.Model):
    id = models.UUIDField(primary_key=True)
    exam = models.ForeignKey(Exam)
    student = models.ForeignKey(Student, null=True)
    anonymous_id = models.CharField(max_length=20)
    corrector = models.ForeignKey(User, null=True)
    status = models.CharField(choices=Status.choices)
    is_identified = models.BooleanField(default=False)
```

### Grade

```python
class Grade(models.Model):
    copy = models.ForeignKey(Copy)
    question_id = models.CharField(max_length=10)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    comment = models.TextField(blank=True)
    graded_at = models.DateTimeField(auto_now_add=True)
```

**Documentation complète** : [Section 04 - Base de Données](./04-database/)

---

## 🔐 Permissions

### Matrice des Permissions

| Action | Admin | Teacher | Student |
|--------|-------|---------|---------|
| Créer examen | ✅ | ❌ | ❌ |
| Upload scans | ✅ | ❌ | ❌ |
| Identification | ✅ | ❌ | ❌ |
| Corriger copies | ✅ | ✅ | ❌ |
| Voir toutes copies | ✅ | Assignées | Propres |
| Finaliser examen | ✅ | ❌ | ❌ |
| Consulter résultats | ✅ | ✅ | ✅ |
| Django Admin | ✅ | ❌ | ❌ |

**Documentation complète** : [07.1-Profils-Permissions.md](./07-annexes/07.1-Profils-Permissions.md)

---

## 🎨 Stack Technique

### Backend

- **Python** : 3.9
- **Django** : 4.2.27
- **DRF** : 3.16.1
- **PostgreSQL** : 15
- **Redis** : 7
- **Celery** : 5.6.2
- **Gunicorn** : 23.0.0

### Frontend

- **Vue.js** : 3.x
- **Vue Router** : 4.x
- **Pinia** : 2.x
- **Axios** : 1.x
- **PDF.js** : 3.x
- **Vite** : 4.x

### OCR

- **Tesseract** : 5.5.0
- **EasyOCR** : 1.7.2
- **PaddleOCR** : 3.4.0
- **OpenCV** : 4.8.1

### Infrastructure

- **Docker** : 24.x
- **Docker Compose** : 2.x
- **Nginx** : 1.25
- **Certbot** : Let's Encrypt

**Documentation complète** : [01.1-Vue-Ensemble.md](./01-architecture/01.1-Vue-Ensemble.md)

---

## 📈 Monitoring

### Health Checks

```bash
# Backend alive
curl http://localhost:8088/api/health/live/

# Backend ready
curl http://localhost:8088/api/health/ready/

# Database status
curl http://localhost:8088/api/health/
```

### Métriques Prometheus

```bash
# Métriques (nécessite token)
curl -H "X-Metrics-Token: <token>" http://localhost:8088/api/metrics/
```

### Logs

```bash
# Logs backend
docker compose logs backend -f

# Logs nginx
docker compose logs nginx -f

# Logs celery
docker compose logs celery -f
```

**Documentation complète** : [06.5-Monitoring.md](./06-deployment/06.5-Monitoring.md)

---

## 🐛 Dépannage Rapide

### Problème : Login échoue (403)

**Solution** :
```bash
# Vérifier que l'utilisateur existe
docker compose exec backend python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> User.objects.filter(username='test_admin').exists()
```

### Problème : Upload PDF échoue

**Vérification** :
- Taille max : 100 MB (configurable dans nginx.conf)
- Format : PDF valide
- Permissions : /media/ writable

### Problème : OCR ne fonctionne pas

**Vérification** :
```bash
# Tesseract installé
docker compose exec backend tesseract --version

# Modèles OCR présents
docker compose exec backend ls -la /app/.cache/
```

### Problème : Celery tasks bloquées

**Solution** :
```bash
# Redémarrer worker
docker compose restart celery

# Vérifier queue Redis
docker compose exec redis redis-cli LLEN celery
```

---

## 📞 Support

**Responsable Technique** : Alaeddine BEN RHOUMA
**Email** : [contact]
**Documentation** : /home/alaeddine/viatique__PMF/documentation/

---

## 📝 Notes Importantes

1. **Backup quotidien** de la base de données (voir 06.3)
2. **SSL/TLS** obligatoire en production (voir 06.4)
3. **Monitoring** actif avec alertes (voir 06.5)
4. **Tests** avant chaque déploiement (voir 07.7)
5. **Audit trail** complet activé (voir 07.5)

---

**Document rédigé par :**
**Alaeddine BEN RHOUMA**
*Lead Senior Documentation & Architecture*
Date : 23 Mars 2026
