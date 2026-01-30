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

## 📚 Documentation

Korrigo dispose d'une documentation exhaustive couvrant tous les aspects du système : administratif, utilisateur, technique, légal et sécurité.

### 📖 Accès à la Documentation

**👉 [INDEX PRINCIPAL DE LA DOCUMENTATION](docs/INDEX.md)** - Point d'entrée unique pour toute la documentation

### Documentation par Public

#### 🏫 **Direction et Administration du Lycée**
- [Guide Administrateur Lycée](docs/admin/GUIDE_ADMINISTRATEUR_LYCEE.md) - Vue d'ensemble exécutive (non-technique)
- [Guide Utilisateur Admin](docs/admin/GUIDE_UTILISATEUR_ADMIN.md) - Manuel administrateur technique
- [Gestion des Utilisateurs](docs/admin/GESTION_UTILISATEURS.md) - Procédures de gestion des comptes
- [Procédures Opérationnelles](docs/admin/PROCEDURES_OPERATIONNELLES.md) - Opérations quotidiennes

#### 👥 **Utilisateurs de la Plateforme**
- [Guide Enseignant](docs/users/GUIDE_ENSEIGNANT.md) - Workflow de correction pour enseignants
- [Guide Secrétariat](docs/users/GUIDE_SECRETARIAT.md) - Identification et gestion des copies
- [Guide Étudiant](docs/users/GUIDE_ETUDIANT.md) - Consultation des copies corrigées
- [Navigation UI](docs/users/NAVIGATION_UI.md) - Référence complète de l'interface

#### 🔒 **Sécurité et Conformité**
- [Politique RGPD](docs/security/POLITIQUE_RGPD.md) - Conformité RGPD/CNIL complète
- [Manuel de Sécurité](docs/security/MANUEL_SECURITE.md) - Sécurité technique
- [Gestion des Données](docs/security/GESTION_DONNEES.md) - Cycle de vie des données
- [Audit de Conformité](docs/security/AUDIT_CONFORMITE.md) - Procédures d'audit

#### ⚖️ **Documentation Légale**
- [Politique de Confidentialité](docs/legal/POLITIQUE_CONFIDENTIALITE.md) - Politique utilisateur
- [Conditions d'Utilisation](docs/legal/CONDITIONS_UTILISATION.md) - CGU de la plateforme
- [Accord de Traitement des Données](docs/legal/ACCORD_TRAITEMENT_DONNEES.md) - DPA contractuel
- [Formulaires de Consentement](docs/legal/FORMULAIRES_CONSENTEMENT.md) - Modèles de consentement

#### 🆘 **Support et Assistance**
- [FAQ](docs/support/FAQ.md) - Questions fréquentes par rôle
- [Dépannage](docs/support/DEPANNAGE.md) - Guide de résolution de problèmes
- [Support](docs/support/SUPPORT.md) - Procédures de support

#### 🔧 **Documentation Technique (Développeurs)**
- [Architecture](docs/ARCHITECTURE.md) - Architecture technique du système
- [API Reference](docs/API_REFERENCE.md) - Documentation complète de l'API REST
- [Database Schema](docs/DATABASE_SCHEMA.md) - Schéma PostgreSQL
- [Business Workflows](docs/BUSINESS_WORKFLOWS.md) - Workflows métier
- [Development Guide](docs/DEVELOPMENT_GUIDE.md) - Guide de développement local
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Guide de déploiement

### 🚀 Démarrage Rapide Documentation

**Nouveau sur Korrigo ?** Consultez le [Guide de Navigation Rapide](docs/INDEX.md#-guide-de-navigation-rapide) dans l'index principal.

**Mise en Production ?** Voir la [Checklist de Conformité](docs/INDEX.md#-documents-requis-pour-mise-en-production).

## 📜 Crédits & Attribution
**Concepteur** : Aleddine BEN RHOUMA — Labo Maths ERT

