# Documentation Korrigo - Index Principal

> **Version**: 1.3  
> **Date**: 14 février 2026  
> **Statut**: Documentation mise à jour — fidèle à l'état actuel du projet

---

## 📚 Guide de Navigation Rapide

**Vous êtes...**

- 🏫 **Direction du Lycée** → Consultez [GUIDE_ADMINISTRATEUR_LYCEE](admin/GUIDE_ADMINISTRATEUR_LYCEE.md) pour une vue d'ensemble non-technique
- 👨‍💼 **Administrateur Technique** → Commencez par [GUIDE_UTILISATEUR_ADMIN](admin/GUIDE_UTILISATEUR_ADMIN.md) et [MANUEL_SECURITE](security/MANUEL_SECURITE.md)
- 👨‍🏫 **Enseignant** → Lisez le [GUIDE_ENSEIGNANT](users/GUIDE_ENSEIGNANT.md) pour corriger des copies
- 👔 **Personnel de Secrétariat** → Consultez [GUIDE_SECRETARIAT](users/GUIDE_SECRETARIAT.md) pour gérer l'identification
- 🎓 **Élève** → Lisez le [GUIDE_ETUDIANT](users/GUIDE_ETUDIANT.md) pour consulter vos copies
- 🔧 **Développeur** → Accédez à [TECHNICAL_MANUAL](technical/TECHNICAL_MANUAL.md), [API_REFERENCE](technical/API_REFERENCE.md), [ARCHITECTURE](technical/ARCHITECTURE.md)

---

## 🏛️ Documentation Administrative

### Guides pour la Direction et Administration

| Document | Description | Taille | Public |
|----------|-------------|--------|--------|
| [**GUIDE_ADMINISTRATEUR_LYCEE**](admin/GUIDE_ADMINISTRATEUR_LYCEE.md) | Guide exécutif pour la direction du lycée (non-technique) | ~28 KB | Direction |
| [**GUIDE_UTILISATEUR_ADMIN**](admin/GUIDE_UTILISATEUR_ADMIN.md) | Manuel technique de l'administrateur système | ~32 KB | Administrateurs |
| [**GESTION_UTILISATEURS**](admin/GESTION_UTILISATEURS.md) | Procédures de gestion des utilisateurs | ~17 KB | Administrateurs |
| [**PROCEDURES_OPERATIONNELLES**](admin/PROCEDURES_OPERATIONNELLES.md) | Opérations quotidiennes et gestion d'examens | ~28 KB | Administrateurs |

**📂 Accès rapide**: [Index Administration](admin/README.md)

---

## 👥 Guides Utilisateurs par Rôle

### Documentation pour Chaque Profil Utilisateur

| Document | Description | Taille | Public |
|----------|-------------|--------|--------|
| [**GUIDE_ENSEIGNANT**](users/GUIDE_ENSEIGNANT.md) | Guide complet pour les enseignants correcteurs | ~22 KB | Enseignants |
| [**GUIDE_SECRETARIAT**](users/GUIDE_SECRETARIAT.md) | Guide pour le personnel d'identification | ~18 KB | Secrétariat |
| [**GUIDE_ETUDIANT**](users/GUIDE_ETUDIANT.md) | Guide simple pour les élèves | ~11 KB | Élèves |
| [**NAVIGATION_UI**](users/NAVIGATION_UI.md) | Référence complète de navigation par rôle | ~27 KB | Tous utilisateurs |

**📂 Accès rapide**: [Index Utilisateurs](users/README.md)

---

## 🔒 Sécurité et Conformité

### RGPD, Sécurité, Protection des Données

| Document | Description | Taille | Public |
|----------|-------------|--------|--------|
| [**POLITIQUE_RGPD**](security/POLITIQUE_RGPD.md) | Politique complète de conformité RGPD/CNIL | ~33 KB | Direction, DPO |
| [**MANUEL_SECURITE**](security/MANUEL_SECURITE.md) | Manuel technique de sécurité | ~27 KB | Administrateurs |
| [**GESTION_DONNEES**](security/GESTION_DONNEES.md) | Guide de gestion du cycle de vie des données | ~22 KB | Administrateurs |
| [**AUDIT_CONFORMITE**](security/AUDIT_CONFORMITE.md) | Procédures d'audit de conformité | ~14 KB | DPO, Auditeurs |
| [**SECURITY_PERMISSIONS_INVENTORY**](security/SECURITY_PERMISSIONS_INVENTORY.md) | Inventaire technique des permissions | ~29 KB | Développeurs |

**📂 Accès rapide**: [Index Sécurité](security/README.md)

---

## ⚖️ Documentation Légale

### Politiques, Accords, Consentements

| Document | Description | Taille | Public |
|----------|-------------|--------|--------|
| [**POLITIQUE_CONFIDENTIALITE**](legal/POLITIQUE_CONFIDENTIALITE.md) | Politique de confidentialité pour utilisateurs | ~11 KB | Tous utilisateurs |
| [**CONDITIONS_UTILISATION**](legal/CONDITIONS_UTILISATION.md) | Conditions générales d'utilisation | ~9 KB | Tous utilisateurs |
| [**ACCORD_TRAITEMENT_DONNEES**](legal/ACCORD_TRAITEMENT_DONNEES.md) | Accord de traitement des données (DPA) | ~13 KB | Direction |
| [**FORMULAIRES_CONSENTEMENT**](legal/FORMULAIRES_CONSENTEMENT.md) | Modèles de formulaires de consentement | ~7 KB | Administration |

**📂 Accès rapide**: [Index Légal](legal/README.md)

---

## 🆘 Support et Dépannage

### FAQ, Résolution de Problèmes, Assistance

| Document | Description | Taille | Public |
|----------|-------------|--------|--------|
| [**FAQ**](support/FAQ.md) | Foire aux questions par rôle | ~23 KB | Tous utilisateurs |
| [**DEPANNAGE**](support/DEPANNAGE.md) | Guide de dépannage et diagnostic | ~17 KB | Administrateurs |
| [**SUPPORT**](support/SUPPORT.md) | Procédures de support et contact | ~9 KB | Tous utilisateurs |

**📂 Accès rapide**: [Index Support](support/README.md)

---

## 🔧 Documentation Technique

### Architecture, API, Base de Données, Développement

> **Stack** : Django 4.2 + DRF (Python 3.11) · Vue.js 3 + Vite · PostgreSQL 15 · Redis · Celery · PyMuPDF · OpenCV · GPT-4o-mini Vision + Tesseract OCR  
> **Production** : Docker Compose · Nginx reverse proxy · korrigo.labomaths.tn (TLS)

| Document | Description | Public |
|----------|-------------|--------|
| [**ARCHITECTURE**](technical/ARCHITECTURE.md) | Architecture technique du système (services, flux, diagrammes) | Développeurs |
| [**API_REFERENCE**](technical/API_REFERENCE.md) | Référence complète de l'API REST (~60 endpoints) | Développeurs |
| [**DATABASE_SCHEMA**](technical/DATABASE_SCHEMA.md) | Schéma PostgreSQL (5 apps, ~20 modèles) | Développeurs |
| [**BUSINESS_WORKFLOWS**](technical/BUSINESS_WORKFLOWS.md) | Workflows métier détaillés (import, correction, export) | Développeurs |
| [**TECHNICAL_MANUAL**](technical/TECHNICAL_MANUAL.md) | Manuel technique général | Développeurs |
| [**DEVELOPMENT_GUIDE**](development/DEVELOPMENT_GUIDE.md) | Guide de développement local | Développeurs |
| [**DEPLOYMENT_GUIDE**](deployment/DEPLOYMENT_GUIDE.md) | Guide de déploiement (Docker Compose, env vars) | DevOps |
| [**DEPLOY_PRODUCTION**](deployment/DEPLOY_PRODUCTION.md) | Déploiement en production (korrigo.labomaths.tn) | DevOps |

---

## 🚀 Démarrage Rapide

### Premiers Pas selon Votre Rôle

#### 🏫 Direction du Lycée
1. **Lisez** [GUIDE_ADMINISTRATEUR_LYCEE](admin/GUIDE_ADMINISTRATEUR_LYCEE.md) - Vue d'ensemble du système
2. **Consultez** [POLITIQUE_RGPD](security/POLITIQUE_RGPD.md) - Comprendre les obligations légales
3. **Examinez** [ACCORD_TRAITEMENT_DONNEES](legal/ACCORD_TRAITEMENT_DONNEES.md) - Accord DPA à signer

#### 👨‍💼 Administrateur Technique
1. **Lisez** [GUIDE_UTILISATEUR_ADMIN](admin/GUIDE_UTILISATEUR_ADMIN.md) - Prise en main administrative
2. **Suivez** [GESTION_UTILISATEURS](admin/GESTION_UTILISATEURS.md) - Créer les premiers comptes
3. **Configurez** selon [PROCEDURES_OPERATIONNELLES](admin/PROCEDURES_OPERATIONNELLES.md)
4. **Sécurisez** avec [MANUEL_SECURITE](security/MANUEL_SECURITE.md)

#### 👨‍🏫 Enseignant
1. **Lisez** [GUIDE_ENSEIGNANT](users/GUIDE_ENSEIGNANT.md) - Workflow de correction complet
2. **Consultez** [NAVIGATION_UI](users/NAVIGATION_UI.md) - Interface utilisateur détaillée
3. **En cas de problème** → [FAQ](support/FAQ.md) section Enseignants

#### 👔 Personnel de Secrétariat
1. **Lisez** [GUIDE_SECRETARIAT](users/GUIDE_SECRETARIAT.md) - Procédures d'identification
2. **Consultez** [NAVIGATION_UI](users/NAVIGATION_UI.md) pour l'interface
3. **En cas de problème** → [FAQ](support/FAQ.md) section Secrétariat

#### 🎓 Élève
1. **Lisez** [GUIDE_ETUDIANT](users/GUIDE_ETUDIANT.md) - Consulter vos copies
2. **Vos droits** → [POLITIQUE_CONFIDENTIALITE](legal/POLITIQUE_CONFIDENTIALITE.md)
3. **Questions** → [FAQ](support/FAQ.md) section Élèves

#### 🔧 Développeur/DevOps
1. **Architecture** → [ARCHITECTURE](technical/ARCHITECTURE.md)
2. **API** → [API_REFERENCE](technical/API_REFERENCE.md)
3. **Base de données** → [DATABASE_SCHEMA](technical/DATABASE_SCHEMA.md)
4. **Développement local** → [DEVELOPMENT_GUIDE](development/DEVELOPMENT_GUIDE.md)
5. **Déploiement** → [DEPLOYMENT_GUIDE](deployment/DEPLOYMENT_GUIDE.md)

---

## 📊 Workflows Critiques

### Guides Pas-à-Pas pour les Opérations Courantes

#### 📝 Créer un Nouvel Examen
1. Admin: [GUIDE_UTILISATEUR_ADMIN](admin/GUIDE_UTILISATEUR_ADMIN.md) § "Création d'Examen"
2. Technique: [BUSINESS_WORKFLOWS](technical/BUSINESS_WORKFLOWS.md) § "Exam Creation Workflow"

#### 🔍 Identifier des Copies Scannées
1. Secrétariat: [GUIDE_SECRETARIAT](users/GUIDE_SECRETARIAT.md) § "Workflow d'Identification"
2. Détails UI: [NAVIGATION_UI](users/NAVIGATION_UI.md) § "Interface Secrétariat"

#### ✍️ Corriger des Copies
1. Enseignant: [GUIDE_ENSEIGNANT](users/GUIDE_ENSEIGNANT.md) § "Workflow de Correction"
2. Annotations: [GUIDE_ENSEIGNANT](users/GUIDE_ENSEIGNANT.md) § "Outil d'Annotation"
3. Barème: [GUIDE_ENSEIGNANT](users/GUIDE_ENSEIGNANT.md) § "Gestion du Barème"

#### 📤 Exporter les Notes vers Pronote
1. Admin: [GUIDE_UTILISATEUR_ADMIN](admin/GUIDE_UTILISATEUR_ADMIN.md) § "Export Pronote"
2. Format CSV: [BUSINESS_WORKFLOWS](technical/BUSINESS_WORKFLOWS.md) § "Pronote Export"

#### 👥 Gérer les Utilisateurs
1. Création manuelle: [GESTION_UTILISATEURS](admin/GESTION_UTILISATEURS.md) § "Création Utilisateur"
2. Import en masse: [GESTION_UTILISATEURS](admin/GESTION_UTILISATEURS.md) § "Import CSV"
3. Désactivation: [GESTION_UTILISATEURS](admin/GESTION_UTILISATEURS.md) § "Désactivation Compte"

#### 🔒 Gérer les Droits RGPD
1. Droits des personnes: [POLITIQUE_RGPD](security/POLITIQUE_RGPD.md) § "Droits des Personnes Concernées"
2. Suppression données: [GESTION_DONNEES](security/GESTION_DONNEES.md) § "Suppression et Anonymisation"
3. Export données: [GESTION_DONNEES](security/GESTION_DONNEES.md) § "Export des Données Personnelles"

---

## 🔍 Index Thématique

### Par Sujet

#### Sécurité
- [Politique RGPD](security/POLITIQUE_RGPD.md)
- [Manuel de Sécurité](security/MANUEL_SECURITE.md)
- [Gestion des Données](security/GESTION_DONNEES.md)
- [Inventaire Permissions](security/SECURITY_PERMISSIONS_INVENTORY.md)
- [Audit de Conformité](security/AUDIT_CONFORMITE.md)

#### Gestion Utilisateurs
- [Guide Admin - Gestion Utilisateurs](admin/GESTION_UTILISATEURS.md)
- [Politique de Confidentialité](legal/POLITIQUE_CONFIDENTIALITE.md)
- [Formulaires de Consentement](legal/FORMULAIRES_CONSENTEMENT.md)

#### Examens et Corrections
- [Business Workflows](technical/BUSINESS_WORKFLOWS.md)
- [Guide Enseignant](users/GUIDE_ENSEIGNANT.md)
- [Guide Secrétariat](users/GUIDE_SECRETARIAT.md)
- [Procédures Opérationnelles](admin/PROCEDURES_OPERATIONNELLES.md)

#### Déploiement et Infrastructure
- [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)
- [Deploy Production](deployment/DEPLOY_PRODUCTION.md)
- [Development Guide](development/DEVELOPMENT_GUIDE.md)
- [Architecture](technical/ARCHITECTURE.md)

#### Support
- [FAQ](support/FAQ.md)
- [Dépannage](support/DEPANNAGE.md)
- [Support](support/SUPPORT.md)

---

## 📝 Documents Requis pour Mise en Production

### Checklist de Conformité

#### ✅ Documents Légaux à Fournir aux Utilisateurs
- [ ] [Politique de Confidentialité](legal/POLITIQUE_CONFIDENTIALITE.md) - Publier sur le site
- [ ] [Conditions d'Utilisation](legal/CONDITIONS_UTILISATION.md) - Acceptation à la première connexion
- [ ] [Formulaires de Consentement](legal/FORMULAIRES_CONSENTEMENT.md) - Distribuer aux parents/élèves

#### ✅ Documents Légaux à Signer avec l'Établissement
- [ ] [Accord de Traitement des Données (DPA)](legal/ACCORD_TRAITEMENT_DONNEES.md) - Signature direction

#### ✅ Documents de Gouvernance Interne
- [ ] [Politique RGPD](security/POLITIQUE_RGPD.md) - Validation DPO/Direction
- [ ] [Manuel de Sécurité](security/MANUEL_SECURITE.md) - Formation administrateurs
- [ ] [Procédures Opérationnelles](admin/PROCEDURES_OPERATIONNELLES.md) - Formation équipe

#### ✅ Formation Utilisateurs
- [ ] Session formation enseignants → [GUIDE_ENSEIGNANT](users/GUIDE_ENSEIGNANT.md)
- [ ] Session formation secrétariat → [GUIDE_SECRETARIAT](users/GUIDE_SECRETARIAT.md)
- [ ] Session formation administration → [GUIDE_UTILISATEUR_ADMIN](admin/GUIDE_UTILISATEUR_ADMIN.md)
- [ ] Communication élèves → [GUIDE_ETUDIANT](users/GUIDE_ETUDIANT.md)

---

## 📞 Contacts et Support

### En Cas de Besoin

| Situation | Document | Contact |
|-----------|----------|---------|
| Question technique | [FAQ](support/FAQ.md) | Voir [SUPPORT](support/SUPPORT.md) |
| Problème système | [DEPANNAGE](support/DEPANNAGE.md) | Administrateur technique |
| Question RGPD | [POLITIQUE_RGPD](security/POLITIQUE_RGPD.md) | DPO de l'établissement |
| Incident sécurité | [MANUEL_SECURITE](security/MANUEL_SECURITE.md) § "Réponse aux Incidents" | Administrateur + Direction |
| Demande de support | [SUPPORT](support/SUPPORT.md) | Voir procédure d'escalade |

---

## 📌 Informations sur cette Documentation

### Métadonnées

- **Projet**: Korrigo - Plateforme de Correction Numérique
- **Production**: [https://korrigo.labomaths.tn](https://korrigo.labomaths.tn)
- **Version Documentation**: 1.3
- **Date de Mise à Jour**: 14 février 2026
- **Stack**: Django 4.2 (Python 3.11) + Vue.js 3 + PostgreSQL 15 + Redis + Celery
- **OCR**: GPT-4o-mini Vision + Tesseract (fallback)
- **Langues**: Français (documentation utilisateur), Anglais (documentation technique)
- **Maintenance**: Voir [SUPPORT](support/SUPPORT.md) § "Maintenance Documentation"

### Structure des Répertoires

```
docs/
├── INDEX.md                    # Ce fichier - Index principal
├── admin/                      # Documentation administrative
│   ├── README.md
│   ├── GUIDE_ADMINISTRATEUR_LYCEE.md
│   ├── GUIDE_UTILISATEUR_ADMIN.md
│   ├── GESTION_UTILISATEURS.md
│   └── PROCEDURES_OPERATIONNELLES.md
├── users/                      # Guides utilisateurs par rôle
│   ├── README.md
│   ├── GUIDE_ENSEIGNANT.md
│   ├── GUIDE_SECRETARIAT.md
│   ├── GUIDE_ETUDIANT.md
│   └── NAVIGATION_UI.md
├── security/                   # Sécurité et conformité
│   ├── README.md
│   ├── POLITIQUE_RGPD.md
│   ├── MANUEL_SECURITE.md
│   ├── GESTION_DONNEES.md
│   └── AUDIT_CONFORMITE.md
├── legal/                      # Documents légaux
│   ├── README.md
│   ├── POLITIQUE_CONFIDENTIALITE.md
│   ├── CONDITIONS_UTILISATION.md
│   ├── ACCORD_TRAITEMENT_DONNEES.md
│   └── FORMULAIRES_CONSENTEMENT.md
├── support/                    # Support et dépannage
│   ├── README.md
│   ├── FAQ.md
│   ├── DEPANNAGE.md
│   └── SUPPORT.md
└── [docs techniques]          # Architecture, API, etc.
```

### Conventions de Documentation

- **Titres de Documents**: MAJUSCULES_AVEC_UNDERSCORES.md
- **Langue**: Français pour docs utilisateurs, Anglais pour docs techniques
- **Format**: Markdown avec front matter (version, date, audience)
- **Liens**: Relatifs au sein de docs/, absolus pour racine projet
- **Sections**: Numérotation décimale (1., 1.1, 1.1.1)

---

## 🔄 Historique des Versions

| Version | Date | Changements |
|---------|------|-------------|
| 1.3 | 2026-02-14 | Mise à jour complète : README réécrit, stack technique actualisée (Python 3.11, GPT-4o-mini, mode INDIVIDUAL_A4), API exhaustive, modèle de données complet |
| 1.2 | 2026-01-24 | CORS production, DRF Spectacular, infrastructure tests |
| 1.1 | 2026-01-24 | Audit trail RGPD, rate limiting, documentation sécurité |
| 1.0 | 2026-01-30 | Publication initiale de la documentation complète |

---

**🏠 Retour**: [README Principal du Projet](../README.md)
