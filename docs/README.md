# Korrigo PMF — Documentation

**Dernière mise à jour** : 10 mars 2026  
**Version** : 1.5  
**Production** : [https://korrigo.labomaths.tn](https://korrigo.labomaths.tn)

---

## 📚 Index de la Documentation

> **Point d'entrée complet** : Voir [INDEX.md](INDEX.md) pour l'index exhaustif avec tables, checklists et guide de navigation par rôle.

### Guides Utilisateurs

| Public | Document | Description |
|--------|----------|-------------|
| Direction | [GUIDE_ADMINISTRATEUR_LYCEE](admin/GUIDE_ADMINISTRATEUR_LYCEE.md) | Vue d'ensemble exécutive (non-technique) |
| Admin | [GUIDE_UTILISATEUR_ADMIN](admin/GUIDE_UTILISATEUR_ADMIN.md) | Manuel technique administrateur |
| Admin | [GESTION_UTILISATEURS](admin/GESTION_UTILISATEURS.md) | Procédures gestion des comptes |
| Admin | [PROCEDURES_OPERATIONNELLES](admin/PROCEDURES_OPERATIONNELLES.md) | Opérations quotidiennes |
| Enseignant | [GUIDE_ENSEIGNANT](users/GUIDE_ENSEIGNANT.md) | Workflow de correction complet |
| Secrétariat | [GUIDE_SECRETARIAT](users/GUIDE_SECRETARIAT.md) | Identification et gestion copies |
| Élève | [GUIDE_ETUDIANT](users/GUIDE_ETUDIANT.md) | Consultation copies corrigées |
| Tous | [NAVIGATION_UI](users/NAVIGATION_UI.md) | Référence complète de l'interface |

### Support et Dépannage

- **[FAQ](support/FAQ.md)** — Questions fréquentes par rôle
- **[Dépannage](support/DEPANNAGE.md)** — Diagnostic et résolution de problèmes
- **[Support](support/SUPPORT.md)** — Niveaux de support, SLA, escalade

### Documentation Technique

| Document | Description |
|----------|-------------|
| [ARCHITECTURE](technical/ARCHITECTURE.md) | Architecture système (Django + Vue + Docker) |
| [API_REFERENCE](technical/API_REFERENCE.md) | Référence API REST (~60 endpoints) |
| [DATABASE_SCHEMA](technical/DATABASE_SCHEMA.md) | Schéma PostgreSQL (5 apps, ~20 modèles) |
| [BUSINESS_WORKFLOWS](technical/BUSINESS_WORKFLOWS.md) | Workflows métier (import, correction, export) |
| [DEVELOPMENT_GUIDE](development/DEVELOPMENT_GUIDE.md) | Guide de développement local |
| [DEPLOYMENT_GUIDE](deployment/DEPLOYMENT_GUIDE.md) | Guide de déploiement Docker |
| [DEPLOY_PRODUCTION](deployment/DEPLOY_PRODUCTION.md) | Déploiement korrigo.labomaths.tn |

### Sécurité et Conformité

- **[POLITIQUE_RGPD](security/POLITIQUE_RGPD.md)** — Conformité RGPD/CNIL
- **[MANUEL_SECURITE](security/MANUEL_SECURITE.md)** — Sécurité technique
- **[GESTION_DONNEES](security/GESTION_DONNEES.md)** — Cycle de vie des données
- **[AUDIT_CONFORMITE](security/AUDIT_CONFORMITE.md)** — Procédures d'audit

### Documentation Légale

- **[POLITIQUE_CONFIDENTIALITE](legal/POLITIQUE_CONFIDENTIALITE.md)** — Politique de confidentialité
- **[CONDITIONS_UTILISATION](legal/CONDITIONS_UTILISATION.md)** — CGU
- **[ACCORD_TRAITEMENT_DONNEES](legal/ACCORD_TRAITEMENT_DONNEES.md)** — DPA contractuel
- **[FORMULAIRES_CONSENTEMENT](legal/FORMULAIRES_CONSENTEMENT.md)** — Modèles de consentement

### Architecture Decision Records (ADRs)

- [ADR-001: Student Authentication Model](decisions/ADR-001-student-authentication-model.md)
- [ADR-002: PDF Coordinate Normalization](decisions/ADR-002-pdf-coordinate-normalization.md)
- [ADR-003: Copy Status State Machine](decisions/ADR-003-copy-status-state-machine.md)

---

## 📂 Structure des Répertoires

```
docs/
├── INDEX.md                     # Index principal exhaustif
├── README.md                    # Ce fichier — index rapide
├── ARCHITECTURE.md              # Architecture technique
├── API_REFERENCE.md             # Référence API REST
├── DATABASE_SCHEMA.md           # Schéma base de données
├── BUSINESS_WORKFLOWS.md        # Workflows métier
├── DEVELOPMENT_GUIDE.md         # Guide développement local
├── DEPLOYMENT_GUIDE.md          # Guide déploiement
├── admin/                       # Guides administration
├── users/                       # Guides par rôle utilisateur
├── security/                    # RGPD, sécurité, données
├── legal/                       # Documents légaux
├── support/                     # FAQ, dépannage, support
├── decisions/                   # ADRs
└── archive/                     # Documents historiques
```

---

## 🚀 Démarrage Rapide

| Besoin | Documents |
|--------|-----------|
| **Nouveau sur Korrigo** | [FAQ](support/FAQ.md) puis guide de votre rôle |
| **Développement local** | [DEVELOPMENT_GUIDE](development/DEVELOPMENT_GUIDE.md) → [ARCHITECTURE](technical/ARCHITECTURE.md) → [API_REFERENCE](technical/API_REFERENCE.md) |
| **Déploiement production** | [DEPLOYMENT_GUIDE](deployment/DEPLOYMENT_GUIDE.md) → [DEPLOY_PRODUCTION](deployment/DEPLOY_PRODUCTION.md) |
| **Problème technique** | [FAQ](support/FAQ.md) → [Dépannage](support/DEPANNAGE.md) → [Support](support/SUPPORT.md) |
| **Conformité RGPD** | [POLITIQUE_RGPD](security/POLITIQUE_RGPD.md) → [GESTION_DONNEES](security/GESTION_DONNEES.md) |

---

## 📜 Historique

- [Changelog](../CHANGELOG.md)

---

**Maintenu par** : Alaeddine BEN RHOUMA — Labo Maths ERT  
**Dernière revue** : 10 mars 2026
