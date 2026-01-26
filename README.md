# Korrigo

**Korrigo** est une plateforme moderne de correction numérique d'examens scannés, conçue pour simplifier la gestion des copies A3, l'anonymisation et l'annotation vectorielle.

## 🚀 Aperçu
Ce projet permet aux établissements scolaires de numériser leur flux de correction : de l'ingestion des scans A3 à l'export des PDF corrigés, en passant par une interface de correction fluide et un éditeur de barème hiérarchique.

## 🏗 Architecture Technique
Le projet repose sur une stack robuste et conteneurisée :
*   **Backend** : Django 4.2 (Python 3.9) + Django REST Framework.
*   **Frontend** : Vue.js 3 (Composition API) + Pinia + Vite.
*   **Base de Données** : PostgreSQL 15.
*   **Files de Tâches** : Redis + Celery (pour le traitement d'images asynchrone).
*   **Vision & PDF** : OpenCV (découpage A3/A4) et PyMuPDF (génération PDF).

## 🛠 Installation

### Prérequis
*   Docker & Docker Compose

### Démarrage Rapide (Via Makefile)
```bash
make up
```
Cette commande construit les images et lance tous les services en arrière-plan.

### Démarrage Manuel
```bash
docker-compose up --build -d
```

## 📖 Guide Utilisateur (Pas à Pas)

### 1. Création de l'Administrateur
Pour accéder à l'administration Django, vous devez créer un super-utilisateur :
```bash
make superuser
# Ou: docker-compose exec backend python manage.py createsuperuser
```

### 2. Accès aux Interfaces
*   **Frontend (Application)** : [http://localhost:5173](http://localhost:5173)
*   **Backend (Admin)** : [http://localhost:8000/admin](http://localhost:8000/admin) (Logins créés à l'étape 1)
*   **API Root** : [http://localhost:8000/api/](http://localhost:8000/api/)

### 3. Workflow de Correction
1.  **Ingestion** : Sur la page d'accueil, cliquez sur "Créer Nouveaux Examens" et téléversez un PDF (ex: scans A3 en vrac).
2.  **Staging (Agrafeuse)** : L'IA découpe les pages. Sélectionnez les fascicules détectés et cliquez sur "Fusionner & Créer Copie" pour générer une copie anonyme.
3.  **Barème** : Cliquez sur le bouton "Éditeur" pour définir la structure de notation (Exercices, Questions, Points).
4.  **Correction (Grading Desk)** : Ouvrez la copie. Utilisez la souris pour dessiner des annotations rouges. Notez chaque question dans la barre latérale.
5.  **Export** : Une fois terminé, allez sur le "Tableau de Bord". Cliquez sur "Générer PDF Finaux" pour récupérer les copies avec annotations et relevé de notes, ou exportez le CSV pour Pronote.

## 🧪 Tests
Pour vérifier que tout fonctionne correctement (Tests E2E inclus) :
```bash
make test
```

## 📜 Crédits & Attribution
**Concepteur** : Aleddine BEN RHOUMA — Labo Maths ERT

