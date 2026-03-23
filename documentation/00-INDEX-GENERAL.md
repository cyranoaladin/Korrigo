# KORRIGO - Documentation Technique Complète

**Plateforme de Correction d'Examens Numériques**

---

## 📋 Informations du Document

| Propriété | Valeur |
|-----------|--------|
| **Projet** | Korrigo - Système de Correction d'Examens |
| **Version** | 2.2 (Production - GPT-4o-mini Vision + Ollama) |
| **Date de dernière mise à jour** | 23 Mars 2026 |
| **Auteur** | **Alaeddine BEN RHOUMA** |
| **Statut** | Production |
| **Commit actuel** | HEAD |

---

## 🎯 Objectif de cette Documentation

Cette documentation est **complète, détaillée et autosuffisante**. Elle permet à tout auditeur, développeur ou administrateur de comprendre **l'intégralité du système Korrigo** sans avoir besoin de consulter d'autres sources.

**Tous les aspects sont couverts** :
- Architecture technique complète
- Logique métier détaillée
- Workflows de bout en bout
- APIs et synchronisations
- Base de données et modèles
- Frontend et interfaces
- Profils et permissions
- Environnements et déploiement
- OCR et traitement des copies
- Sécurité et audit

---

## 📚 Structure de la Documentation

Cette documentation est organisée en **7 sections principales** :

### [01 - Architecture](./01-architecture/)
Documentation de l'architecture technique complète du système.

- **[01.1-Vue-Ensemble.md](./01-architecture/01.1-Vue-Ensemble.md)**
  - Architecture globale (Backend Django + Frontend Vue.js + Base PostgreSQL)
  - Stack technologique détaillée
  - Diagrammes d'architecture
  - Flux de données entre composants

- **[01.2-Backend-Django.md](./01-architecture/01.2-Backend-Django.md)**
  - Structure du backend Django
  - Applications Django (core, exams, grading, students, identification, processing)
  - Middleware et sécurité
  - Celery et traitement asynchrone

- **[01.3-Frontend-Vue.md](./01-architecture/01.3-Frontend-Vue.md)**
  - Architecture Vue.js 3 avec Composition API
  - Structure des composants
  - State management et routing
  - Communication avec le backend

- **[01.4-Base-Donnees.md](./01-architecture/01.4-Base-Donnees.md)**
  - Schéma complet de la base PostgreSQL
  - Relations entre tables
  - Indexes et performances
  - Stratégie de backup

- **[01.5-Infrastructure.md](./01-architecture/01.5-Infrastructure.md)**
  - Architecture Docker/Docker Compose
  - Nginx reverse proxy
  - Redis cache et Celery broker
  - Environnements (dev, test, staging, production)

---

### [02 - Workflows](./02-workflows/)
Documentation détaillée de tous les workflows métier.

- **[02.1-Workflow-Admin-Creation-Examen.md](./02-workflows/02.1-Workflow-Admin-Creation-Examen.md)**
  - Création d'un examen par l'administrateur
  - Définition de la structure de notation
  - Configuration des correcteurs
  - Validation et activation

- **[02.2-Workflow-Upload-Scans.md](./02-workflows/02.2-Workflow-Upload-Scans.md)**
  - Import des fichiers CSV (liste élèves)
  - Upload des scans PDF (A4 ou A3)
  - Validation des formats
  - Traitement batch vs individuel

- **[02.3-Workflow-Traitement-PDF.md](./02-workflows/02.3-Workflow-Traitement-PDF.md)**
  - Détection format (A3 vs A4)
  - Split et rotation des pages
  - Segmentation par étudiant
  - Extraction des pages par copie

- **[02.4-Workflow-OCR-Identification.md](./02-workflows/02.4-Workflow-OCR-Identification.md)**
  - OCR avec GPT-4o-mini Vision (Principal) + Tesseract (Fallback)
  - Matching étudiant avec CSV
  - Modes : AUTO / SEMI-AUTO / MANUAL
  - Desk d'identification

- **[02.5-Workflow-Anonymisation.md](./02-workflows/02.5-Workflow-Anonymisation.md)**
  - Génération des identifiants anonymes
  - Occultation des informations personnelles
  - Distribution aux correcteurs
  - Traçabilité

- **[02.6-Workflow-Correction.md](./02-workflows/02.6-Workflow-Correction.md)**
  - Interface de correction enseignant
  - Annotation des copies
  - Attribution des points
  - Commentaires et remarques
  - Sauvegarde automatique (draft)

- **[02.7-Workflow-Finalisation.md](./02-workflows/02.7-Workflow-Finalisation.md)**
  - Verrouillage des corrections
  - Désanonymisation
  - Calcul des notes finales
  - Publication des résultats

- **[02.8-Workflow-Consultation-Eleve.md](./02-workflows/02.8-Workflow-Consultation-Eleve.md)**
  - Authentification élève (email + date naissance)
  - Consultation de la copie corrigée
  - Visualisation des annotations
  - Téléchargement PDF

---

### [03 - API](./03-api/)
Documentation complète de toutes les APIs REST.

- **[03.1-Authentification.md](./03-api/03.1-Authentification.md)**
  - POST /api/login/
  - POST /api/logout/
  - GET /api/me/
  - Gestion des sessions et CSRF

- **[03.2-API-Examens.md](./03-api/03.2-API-Examens.md)**
  - GET /api/exams/
  - POST /api/exams/
  - GET /api/exams/{id}/
  - PUT /api/exams/{id}/
  - POST /api/exams/upload/

- **[03.3-API-Copies.md](./03-api/03.3-API-Copies.md)**
  - GET /api/grading/copies/
  - GET /api/grading/copies/{id}/
  - PATCH /api/grading/copies/{id}/
  - POST /api/grading/copies/{id}/lock/
  - POST /api/grading/copies/{id}/unlock/
  - POST /api/grading/copies/{id}/force-unlock/ (v2.2)
  - POST /api/grading/copies/{id}/reopen/ (v2.2)

- **[03.4-API-Identification.md](./03-api/03.4-API-Identification.md)**
  - GET /api/identification/copies/{id}/ocr-candidates/
  - POST /api/identification/copies/{id}/select-candidate/
  - POST /api/identification/copies/{id}/manual-assign/

- **[03.5-API-Etudiants.md](./03-api/03.5-API-Etudiants.md)**
  - POST /api/students/login/
  - GET /api/students/me/
  - GET /api/students/copies/
  - GET /api/students/results/

- **[03.6-Codes-Erreur.md](./03-api/03.6-Codes-Erreur.md)**
  - Table complète des codes HTTP
  - Messages d'erreur standardisés
  - Gestion des erreurs frontend

---

### [04 - Base de Données](./04-database/)
Schéma complet et documentation de la base PostgreSQL.

- **[04.1-Schema-Complet.md](./04-database/04.1-Schema-Complet.md)**
  - Diagramme ER complet
  - Liste exhaustive des tables
  - Relations et contraintes

- **[04.2-Modeles-Core.md](./04-database/04.2-Modeles-Core.md)**
  - User (authentification)
  - Group (permissions)
  - Session

- **[04.3-Modeles-Exams.md](./04-database/04.3-Modeles-Exams.md)**
  - Exam (examen)
  - GradingStructure (barème)
  - Copy (copie étudiant)
  - Booklet (cahier)
  - Page (page scannée)

- **[04.4-Modeles-Grading.md](./04-database/04.4-Modeles-Grading.md)**
  - Grade (note attribuée)
  - Annotation (annotations PDF)
  - Comment (commentaires)
  - DraftState (sauvegarde auto)

- **[04.5-Modeles-Students.md](./04-database/04.5-Modeles-Students.md)**
  - Student (élève)
  - StudentResult (résultat)

- **[04.6-Modeles-Processing.md](./04-database/04.6-Modeles-Processing.md)**
  - OCRResult (résultat OCR)
  - BatchProcessingJob (traitement batch)
  - ProcessingLog (logs)

- **[04.7-Migrations.md](./04-database/04.7-Migrations.md)**
  - Historique des migrations
  - Stratégie de migration
  - Rollback

---

### [05 - Frontend](./05-frontend/)
Documentation de l'interface utilisateur Vue.js.

- **[05.1-Architecture-Vue.md](./05-frontend/05.1-Architecture-Vue.md)**
  - Structure des dossiers
  - Composants principaux
  - Services et utils

- **[05.2-Routes.md](./05-frontend/05.2-Routes.md)**
  - Table complète des routes
  - Guards d'authentification
  - Navigation

- **[05.3-Composants-Admin.md](./05-frontend/05.3-Composants-Admin.md)**
  - Dashboard admin
  - Création d'examen
  - Gestion utilisateurs

- **[05.4-Composants-Teacher.md](./05-frontend/05.4-Composants-Teacher.md)**
  - Interface de correction
  - Desk d'identification
  - Gestion des copies

- **[05.5-Composants-Student.md](./05-frontend/05.5-Composants-Student.md)**
  - Portail élève
  - Consultation copie
  - Visualisation annotations

- **[05.6-State-Management.md](./05-frontend/05.6-State-Management.md)**
  - Stores Pinia
  - Gestion de l'état global
  - Synchronisation avec backend

---

### [06 - Déploiement](./06-deployment/)
Guide complet de déploiement et configuration.

- **[06.1-Environnements.md](./06-deployment/06.1-Environnements.md)**
  - Development
  - Testing
  - Staging
  - Production

- **[06.2-Installation-Locale.md](./06-deployment/06.2-Installation-Locale.md)**
  - Prérequis
  - Installation Docker
  - Configuration .env
  - Lancement des services

- **[06.3-Deploiement-Production.md](./06-deployment/06.3-Deploiement-Production.md)**
  - Serveur dédié (korrigo.labomths.tn)
  - Configuration DNS
  - SSL/TLS avec Certbot
  - Docker Compose production
  - Migrations
  - Backup et restauration

- **[06.4-Configuration-Nginx.md](./06-deployment/06.4-Configuration-Nginx.md)**
  - Reverse proxy
  - SSL/TLS
  - Security headers
  - Gzip compression
  - Rate limiting

- **[06.5-Monitoring.md](./06-deployment/06.5-Monitoring.md)**
  - Prometheus metrics
  - Logs structurés
  - Health checks
  - Alerting

---

### [07 - Annexes](./07-annexes/)
Informations complémentaires et références.

- **[07.1-Profils-Permissions.md](./07-annexes/07.1-Profils-Permissions.md)**
  - Table complète des profils
  - Matrice des permissions
  - Groupes Django
  - Comptes de test

- **[07.2-Format-CSV.md](./07-annexes/07.2-Format-CSV.md)**
  - Format attendu pour l'import élèves
  - Exemples
  - Validation

- **[07.3-Format-PDF.md](./07-annexes/07.3-Format-PDF.md)**
  - Formats supportés (A4, A3)
  - Résolution minimale
  - Organisation des pages

- **[07.4-OCR-Details.md](./07-annexes/07.4-OCR-Details.md)**
  - Tesseract configuration
  - EasyOCR modèles
  - PaddleOCR paramètres
  - Preprocessing images
  - Consensus voting

- **[07.5-Securite.md](./07-annexes/07.5-Securite.md)**
  - CSRF protection
  - XSS prevention
  - SQL injection protection
  - Rate limiting
  - Audit trail

- **[07.6-Performance.md](./07-annexes/07.6-Performance.md)**
  - Optimisations database
  - Caching strategy
  - CDN
  - Lazy loading

- **[07.7-Tests.md](./07-annexes/07.7-Tests.md)**
  - Tests unitaires (pytest)
  - Tests d'intégration
  - Tests E2E (Playwright)
  - Coverage
  - CI/CD

- **[07.8-Glossaire.md](./07-annexes/07.8-Glossaire.md)**
  - Termes métier
  - Acronymes
  - Définitions

---

## 🚀 Comment Utiliser Cette Documentation

### Pour un Auditeur
1. Commencer par la **Vue d'Ensemble** (01.1)
2. Lire les **Workflows** complets (section 02)
3. Consulter l'**Architecture** détaillée (section 01)
4. Vérifier les **Permissions** et **Sécurité** (07.1, 07.5)

### Pour un Développeur
1. Comprendre l'**Architecture Backend** (01.2) et **Frontend** (01.3)
2. Étudier les **APIs** (section 03)
3. Comprendre le **Schéma DB** (section 04)
4. Suivre les **Workflows** pour comprendre la logique métier (section 02)

### Pour un DevOps
1. Lire **Infrastructure** (01.5)
2. Suivre le guide de **Déploiement** (section 06)
3. Configurer le **Monitoring** (06.5)
4. Mettre en place les **Backups** (06.3)

### Pour un Product Owner
1. Comprendre les **Workflows métier** (section 02)
2. Vérifier les **Profils** et **Permissions** (07.1)
3. Consulter les **Interfaces** utilisateur (section 05)

---

## ✅ Garanties de Cette Documentation

✓ **Complète** : Tous les aspects du système sont documentés
✓ **Détaillée** : Chaque fonctionnalité est expliquée en profondeur
✓ **Autosuffisante** : Aucune source externe n'est nécessaire
✓ **À jour** : Version actuelle v2.2 (23 mars 2026)
✓ **Structurée** : Organisation logique et navigation facile
✓ **Illustrée** : Diagrammes, tableaux et exemples concrets
✓ **Traçable** : Historique des modifications

---

## 📞 Contacts et Support

**Responsable Documentation** : **Alaeddine BEN RHOUMA**
**Projet** : Korrigo - Plateforme de Correction d'Examens
**Institution** : Laboratoire de Mathématiques, Tunisie
**URL Production** : https://korrigo.labomths.tn

---

## 📜 Licence et Propriété Intellectuelle

© 2026 Alaeddine BEN RHOUMA - Tous droits réservés

Cette documentation est propriété de l'auteur et ne peut être reproduite, distribuée ou modifiée sans autorisation écrite préalable.

---

**Document rédigé et validé par :**

**Alaeddine BEN RHOUMA**
*Lead Senior Documentation & Architecture*

Date de signature : 23 Mars 2026

---

## Historique des Versions

| Version | Date | Description |
|---------|------|-------------|
| 2.0 | 03 Février 2026 | Version initiale production |
| 2.1 | 20 Février 2026 | GPT-4o-mini Vision + Ollama, rate limiting, documentation |
| 2.2 | 23 Mars 2026 | Tampon V/X (VRAI/FAUX), split view correction, force-unlock et reopen copies (admin), TrueFalseTool.vue, CanvasLayer V/X rendering |
