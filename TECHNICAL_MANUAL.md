# Manuel Technique - OpenViatique PMF

> **Version:** 1.1.0
> **Date:** Janvier 2026
> **Public:** Développeurs & Mainteneurs

Ce document est la référence technique absolue du projet. Il détaille l'architecture, le modèle de données, la configuration et les algorithmes critiques.

---

## 1. Structure du Projet

L'architecture suit une séparation stricte entre la logique métier, le traitement d'images et l'interface utilisateur.

### 1.1. Backend (`backend/`)
*   **`core/`** : Configuration globale Django (Settings, URLConf, WSGI/ASGI).
*   **`exams/`** : Logique métier administrative (Cycle de vie Examen/Fascicule/Copie).
*   **`grading/`** : Logique de correction haute fréquence (Annotations, Scores).
*   **`processing/`** : Services "Stateless" de Vision et Manipulation PDF (OpenCV, PyMuPDF, splitting).
    *   *Note:* Ce module est découplé des modèles Django pour faciliter les tests et la réutilisation.

### 1.2. Frontend (`frontend/`)
*   **Stack** : Vue 3, Vite, Pinia.
*   **`src/stores/`** : `examStore.js` centralise l'état (données d'examen, fascicules en staging).
*   **`src/views/`** : Vues principales (`StagingArea`, `CorrectorDesk`, `Dashboard`).

---

## 2. Configuration & Variables d'Environnement

Le projet utilise `python-dotenv` et les variables d'environnement Docker.

### Variables Clés (`.env`)
Voici les variables supportées par l'application (valeurs par défaut indiquées) :

| Variable | Description | Défaut (Dev) |
| :--- | :--- | :--- |
| `SECRET_KEY` | Clé cryptographique Django | `django-insecure...` |
| `DEBUG` | Mode Debug Django | `True` |
| `ALLOWED_HOSTS` | Hôtes autorisés (liste CSV) | `*` |
| `DATABASE_URL` | URL de connexion PostgreSQL | `postgres://user:pass@db:5432/db` |
| `CELERY_BROKER_URL` | URL de connexion Redis | `redis://redis:6379/0` |
| `VITE_API_URL` | URL du Backend pour le Frontend | `http://localhost:8000` |

### Configuration Docker Compose
Le fichier `docker-compose.yml` fournit une configuration "Batteries Included" pour le développement :
*   **db** : PostgreSQL 15 (Port 5435 sur hôte).
*   **redis** : Redis 7 (Port 6385 sur hôte).
*   **backend** : Django (Port 8000). Utilise `manage.py runserver`.
*   **celery** : Worker asynchrone pour le traitement d'images.
*   **frontend** : Serveur dev Vite (Port 5173).

---

## 3. Infrastructure & Persistance

L'intégrité des données repose sur des volumes Docker persistants.

### Volumes Critiques
1.  **`postgres_data`** : Monté sur `/var/lib/postgresql/data`. Contient toute la base relationnelle (Examens, Notes, Utilisateurs).
2.  **`media_volume`** (Implémenté via bind-mount `./backend/media` en Dev) :
    *   `exams/source/` : PDF originaux téléversés.
    *   `booklets/headers/` : Images d'en-têtes pour validation manuelle.
    *   `copies/final/` : PDF finaux générés après correction.

> **⚠️ ATTENTION : Commandes de Cycle de Vie**
> *   `make down` (ou `docker-compose down`) : Arrête et supprime les conteneurs. **Les données sont conservées.**
> *   `docker-compose down -v` : Arrête les conteneurs ET **DÉTRUIT les volumes (Base de données perdue).**

---

## 4. Workflow de Traitement d'Image (Vision Pipeline)

Ce module (`backend/processing/`) est le cœur critique de l'application.

### 4.1. Ingestion & Référentiel de Coordonnées
Pour garantir l'indépendance vis-à-vis de la résolution d'écran ou du scan :
*   **Frontend (CanvasLayer)** : Enregistre les annotations en **coordonnées normalisées (0.0 à 1.0)** relatives au viewport.
    *   `x_rel = x_pixel / width_canvas`
    *   `y_rel = y_pixel / height_canvas`
*   **Backend (PDFFlattener)** : Projette ces coordonnées sur la taille réelle de la page PDF.
    *   `x_pdf = x_rel * page.rect.width`
    *   `y_pdf = y_rel * page.rect.height`

### 4.2. Algorithme de Split (`services/splitter.py`)
1.  **Entrée** : Image A3 (JPEG/PNG issue de `pdf2image`).
2.  **Découpe** : Scission verticale stricte au milieu (50%).
3.  **Détection Recto/Verso** : Analyse de la moitié DROITE par `HeaderDetector`.
    *   *Header Présent* = RECTO (Page 1 à droite, Page 4 à gauche).
    *   *Header Absent* = VERSO (Page 3 à droite, Page 2 à gauche).
4.  **Reconstruction** : Les pages sont stockées dans `Booklet.pages_images` dans l'ordre logique de lecture : `[P1, P2, P3, P4]`.

---

## 5. Modèle de Données (Schéma simplifiée)

*   `Exam` (UUID) : `grading_structure` (JSON Array récursif).
*   `Booklet` (UUID) : Liste d'images ordonnée (`pages_images`).
*   `Copy` (UUID) :
    *   `score` (JSONField via modèle `Score`) : `{'q1': 5, 'total': 18}`.
    *   `annotations` (JSONField via modèle `Annotation`) : `[{'type': 'path', 'points': [...]}]`.
    *   `anonymous_id` : Généré à la fusion.

---

## 6. Référence API & Sécurité

### Authentification & Permissions
*   **Authentification** : Session (Cookie `sessionid`).
*   **Permissions** : Par défaut, les endpoints critiques nécessitent `IsAuthenticated` (Configurable dans `settings.py` -> `REST_FRAMEWORK`).
*   *Note Dev :* En mode dev actuel, `AllowAny` est souvent activé pour faciliter les tests E2E.

### Endpoints Critiques
*   `POST /api/exams/upload/` : Ingestion asynchrone.
*   `POST /api/exams/{id}/merge/` : Fusion des fascicules (Staging -> Copy).
*   `PATCH /api/exams/{id}/` : Mise à jour du barème (`grading_structure`). Sécurisé par validation JSON stricte.
*   `POST /api/exams/{id}/export_all/` : Déclenche le `PDFFlattener` (Génération PDF annotés + CSV).

---

FIN DU MANUEL TECHNIQUE
