# Documentation Korrigo — Index Principal

> **Version** : 3.1
> **Date** : 2026-04-03
> **Statut** : Documentation de référence alignée sur la production actuelle
> **Production** : https://korrigo.labomaths.tn

> **Périmètre documentaire**
> - `docs/` : documentation normative maintenue.
> - `docs/archive/` : documents historiques, rapports et audits figés.
> - `documentation/` : ancienne documentation exhaustive conservée comme archive de contexte, pas comme source de vérité opérationnelle.

---

## Navigation rapide par profil

| Vous êtes... | Commencez par... |
|-------------|-----------------|
| 🏫 **Direction du lycée** | [GUIDE_ADMINISTRATEUR_LYCEE](admin/GUIDE_ADMINISTRATEUR_LYCEE.md) |
| 👨‍💼 **Administrateur technique** | [QUICKSTART](QUICKSTART.md) → [ARCHITECTURE](technical/ARCHITECTURE.md) |
| 👨‍🏫 **Enseignant / Correcteur** | [GUIDE_ENSEIGNANT](users/GUIDE_ENSEIGNANT.md) |
| 👔 **Secrétariat** | [GUIDE_SECRETARIAT](users/GUIDE_SECRETARIAT.md) |
| 🎓 **Élève** | [GUIDE_ETUDIANT](users/GUIDE_ETUDIANT.md) |
| 🔧 **Développeur** | [QUICKSTART](QUICKSTART.md) → [ARCHITECTURE](technical/ARCHITECTURE.md) → [API_REFERENCE](technical/API_REFERENCE.md) |
| 🚀 **DevOps** | [DEPLOYMENT_GUIDE](deployment/DEPLOYMENT_GUIDE.md) → [RUNBOOK_PRODUCTION](deployment/RUNBOOK_PRODUCTION.md) |

---

## Documentation Technique

| Document | Description | Date màj |
|----------|-------------|----------|
| [**ARCHITECTURE.md**](technical/ARCHITECTURE.md) | Architecture complète : stack, apps Django, patterns, infrastructure | 2026-04-03 |
| [**DATABASE_SCHEMA.md**](technical/DATABASE_SCHEMA.md) | Tous les modèles, champs, relations, migrations | 2026-03-28 |
| [**API_REFERENCE.md**](technical/API_REFERENCE.md) | Référence complète de tous les endpoints REST | 2026-04-03 |
| [**BUSINESS_WORKFLOWS.md**](technical/BUSINESS_WORKFLOWS.md) | Workflows métier : ingestion, correction, publication | 2026-03-28 |
| [**FRONTEND_ARCHITECTURE.md**](technical/FRONTEND_ARCHITECTURE.md) | Vue 3 SPA : stores, router, composants clés | 2026-03-28 |
| [**PDF_PROCESSING.md**](technical/PDF_PROCESSING.md) | Pipeline PDF : split, rasterisation, aplatissement | 2026-03-23 |
| [**TECHNICAL_MANUAL.md**](technical/TECHNICAL_MANUAL.md) | Vue d'ensemble technique et pointeurs vers les références normatives | 2026-04-03 |
| [**CURRENT_STATE_MARCH_2026.md**](technical/CURRENT_STATE_MARCH_2026.md) | État réel du projet et de la production au 2026-04-03 | 2026-04-03 |

---

## Décisions d'Architecture (ADR)

| ADR | Décision | Statut |
|-----|---------|--------|
| [**ADR-001**](decisions/ADR-001-student-authentication-model.md) | Authentification élèves : email + date de naissance | ✅ Accepté |
| [**ADR-002**](decisions/ADR-002-pdf-coordinate-normalization.md) | Coordonnées annotations normalisées [0,1] | ✅ Accepté |
| [**ADR-003**](decisions/ADR-003-copy-status-state-machine.md) | Machine à états copies : READY/IN_PROGRESS/FINALIZED | ✅ V4 (Avril 2026) |

---

## Développement

| Document | Description |
|----------|-------------|
| [**QUICKSTART.md**](QUICKSTART.md) | Lancer l'environnement local en < 15 min |
| [**DEVELOPMENT_GUIDE.md**](development/DEVELOPMENT_GUIDE.md) | Conventions, tests, commandes de gestion, debugging |
| [**SPECIFICATION.md**](development/SPECIFICATION.md) | Spécification fonctionnelle complète |
| [**TESTING_GUIDE.md**](TESTING_GUIDE.md) | Guide des tests : pytest, Playwright, markers |

---

## Déploiement & Opérations

| Document | Description |
|----------|-------------|
| [**DEPLOYMENT_GUIDE.md**](deployment/DEPLOYMENT_GUIDE.md) | Guide de déploiement production |
| [**RUNBOOK_PRODUCTION.md**](deployment/RUNBOOK_PRODUCTION.md) | Runbook opérationnel production |
| [**RUNBOOK_STAGING.md**](deployment/RUNBOOK_STAGING.md) | Runbook staging |

---

## Guides Utilisateurs

| Document | Public | Description |
|----------|--------|-------------|
| [**GUIDE_ENSEIGNANT.md**](users/GUIDE_ENSEIGNANT.md) | Enseignants | Corriger des copies annotées |
| [**GUIDE_SECRETARIAT.md**](users/GUIDE_SECRETARIAT.md) | Secrétariat | Identifier les copies (OCR) |
| [**GUIDE_ETUDIANT.md**](users/GUIDE_ETUDIANT.md) | Élèves | Consulter ses copies corrigées |

---

## Documentation Administrative

| Document | Public | Description |
|----------|--------|-------------|
| [**GUIDE_ADMINISTRATEUR_LYCEE.md**](admin/GUIDE_ADMINISTRATEUR_LYCEE.md) | Direction | Vue d'ensemble non-technique |
| [**GUIDE_UTILISATEUR_ADMIN.md**](admin/GUIDE_UTILISATEUR_ADMIN.md) | Admin technique | Manuel complet admin |
| [**GESTION_UTILISATEURS.md**](admin/GESTION_UTILISATEURS.md) | Admin | Gestion des comptes utilisateurs |
| [**PROCEDURES_OPERATIONNELLES.md**](admin/PROCEDURES_OPERATIONNELLES.md) | Admin | Procédures quotidiennes |

---

## Sécurité & Conformité RGPD

| Document | Description |
|----------|-------------|
| [**MANUEL_SECURITE.md**](security/MANUEL_SECURITE.md) | Procédures et politiques de sécurité |
| [**POLITIQUE_RGPD.md**](security/POLITIQUE_RGPD.md) | Conformité RGPD |
| [**GESTION_DONNEES.md**](security/GESTION_DONNEES.md) | Cycle de vie des données |
| [**AUDIT_CONFORMITE.md**](security/AUDIT_CONFORMITE.md) | Procédures d'audit |

---

## Support

| Document | Description |
|----------|-------------|
| [**FAQ.md**](support/FAQ.md) | Questions fréquentes par rôle |
| [**DEPANNAGE.md**](support/DEPANNAGE.md) | Guide de dépannage |

---

## Points clés à connaître

### Machine à états des copies (actuelle)
```
READY → IN_PROGRESS → FINALIZED
  ↑                       │
  └──── reopen (admin) ───┘
```
**Ancienne machine (obsolète)** : STAGING/READY/LOCKED/GRADING_IN_PROGRESS/GRADED — supprimée en migration 0026.

### Production au 2026-04-03
- 4 examens en base
- 504 copies
- 3414 annotations
- 396 scores
- backup automatisé vers Hetzner StorageBox toutes les 30 minutes avec rétention distante de 24h

### Santé applicative
- point de santé de référence en production : `https://korrigo.labomaths.tn/api/health/`
- les probes internes `/api/health/live/` et `/api/health/ready/` existent, mais la vérification opérationnelle de référence passe par Nginx

### Authentification
- Admin/Teacher : session Django (username + password)
- Élève : email + date de naissance (POST `/api/students/login/`)

### Production
- Serveur : 88.99.254.59
- 6 conteneurs Docker opérationnels
- `docker-celery-beat-1` corrigé et opérationnel
