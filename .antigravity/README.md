# .antigravity/ - Système de Gouvernance Technique du Projet Viatique

**Version de Gouvernance** : `1.1.0`
**Dernière mise à jour** : 2026-01-21
**Statut** : Production-Ready

---

## Objectif

Ce dossier constitue le **contrat de développement obligatoire** pour l'ensemble du projet Viatique. Il définit les règles techniques non négociables, les compétences requises, les workflows métier et les garde-fous de sécurité.

**Toute violation des règles contenues dans ce dossier est considérée comme un bug critique.**

## Statut

- **Obligatoire** : Toute modification du code doit respecter ces règles
- **Versionné** : Ce dossier fait partie intégrante du dépôt Git
- **Évolutif** : Les règles peuvent être mises à jour, mais toujours de manière explicite et documentée
- **Prioritaire** : En cas de conflit avec d'autres documentations, .antigravity/ prévaut

## Structure

```
.antigravity/
├── README.md                           # Ce fichier
├── SUPERVISION_RULES.md               # Règles spécifiques à l'agent
├── rules/                              # Règles techniques strictes
│   ├── 00_global_rules.md             # Règles générales du projet
│   ├── 01_security_rules.md           # Règles de sécurité (CRITIQUE)
│   ├── 02_backend_rules.md            # Architecture Django/DRF
│   ├── 03_frontend_rules.md           # Architecture Vue.js
│   ├── 04_database_rules.md           # Modèles et migrations
│   ├── 05_pdf_processing_rules.md     # Traitement PDF et annotations
│   └── 06_deployment_rules.md         # Mise en production
├── skills/                             # Compétences techniques requises
│   ├── backend_architect.md           # Architecture backend
│   ├── security_auditor.md            # Audit de sécurité
│   ├── django_expert.md               # Expertise Django
│   ├── vue_frontend_expert.md         # Expertise Vue.js
│   └── pdf_processing_expert.md       # Traitement PDF
├── workflows/                          # Workflows métier formalisés
│   ├── authentication_flow.md         # Authentification (prof/élève)
│   ├── correction_flow.md             # Processus de correction
│   ├── student_access_flow.md         # Accès élève (lecture seule)
│   ├── pdf_ingestion_flow.md          # Ingestion et split PDF
│   ├── pdf_annotation_export_flow.md  # Annotations et export
│   └── deployment_flow.md             # Déploiement production
└── checklists/                         # Listes de vérification
    ├── pr_checklist.md                # Validation Pull Request
    ├── security_checklist.md          # Audit de sécurité
    └── production_readiness_checklist.md # Prêt pour la production
```

## Hiérarchie des Règles

En cas de conflit ou d'ambiguïté, l'ordre de priorité est :

1. **rules/** - Les règles techniques sont non négociables
2. **workflows/** - Les workflows décrivent le comportement attendu
3. **skills/** - Les compétences définissent le niveau d'expertise requis
4. **checklists/** - Les listes de vérification garantissent la qualité

## Utilisation

### Pour le développement

Avant toute modification du code :

1. Consulter `rules/` pour vérifier la conformité
2. Consulter `workflows/` pour comprendre l'impact métier
3. Utiliser `checklists/` avant tout commit/PR

### Pour Antigravity (IA)

- **Activation automatique** : Les règles de ce dossier doivent être appliquées automatiquement
- **Skills on-demand** : Les compétences doivent être activées selon le contexte
- **Validation stricte** : Tout code généré doit passer les checklists

### Pour les revues de code

- Vérifier la conformité avec `rules/`
- Vérifier que le workflow correspondant est respecté
- Utiliser `pr_checklist.md` comme guide

## Principes Fondamentaux

### Sécurité First

- **Authentification obligatoire** : Pas de `AllowAny` par défaut
- **Séparation des rôles** : Admin / Professeur / Élève strictement isolés
- **Données élèves protégées** : Aucun accès sans authentification valide
- **Secrets sécurisés** : Aucun secret en dur, variables d'environnement obligatoires

### Production Ready

- Penser production avant développement
- Pas de `DEBUG=True` en production
- Configuration via variables d'environnement
- Logs structurés et traçabilité complète

### Qualité du Code

- Pas de logique métier dans les views
- Pas de modèle sans migration cohérente
- Transactions atomiques pour les opérations critiques
- Tests obligatoires pour les fonctionnalités critiques

### Traçabilité

- Toute copie a un PDF final assigné
- Toute annotation est traçable
- Toute action critique est journalisée
- Aucune perte de données

## Conséquences des Violations

Une violation des règles de ce dossier entraîne :

- **Rejet automatique** du PR
- **Classification en bug critique** si déjà en production
- **Refactoring obligatoire** avant toute autre fonctionnalité

## Maintenance

Ce dossier doit être maintenu avec le même niveau d'attention que le code source.

Toute modification des règles doit :
- Être justifiée par un besoin métier ou technique
- Être documentée explicitement
- Être revue par l'équipe/lead technique
- Être communiquée à tous les développeurs

## Contact et Questions

Pour toute question sur l'interprétation des règles :
1. Lire attentivement le fichier concerné dans `rules/`
2. Consulter le workflow correspondant dans `workflows/`
3. Vérifier la checklist applicable dans `checklists/`

**En cas de doute : appliquer la règle la plus stricte.**

---

## Versioning de la Gouvernance

### Format de Version

Le `.antigravity/` suit le versioning sémantique : `MAJOR.MINOR.PATCH`

- **MAJOR** : Changement incompatible ou restructuration majeure
- **MINOR** : Ajout de règles, workflows, ou compétences
- **PATCH** : Corrections, clarifications, améliorations mineures

### Historique des Versions

#### v1.1.0 (2026-01-21)
- ✅ Sync avec `.claude/` v1.1.0
- ✅ Adoption des standards Viatique
- ✅ Activation du modèle de gouvernance unifié

### Procédure de Mise à Jour

Toute modification du `.antigravity/` doit :
1. Justifier le changement (pourquoi nécessaire)
2. Bumper la version appropriée
3. Documenter dans l'historique ci-dessus
4. Communiquer à l'équipe
5. Commit explicite : `git commit -m "chore(.antigravity): bump to v1.x.y - raison"`

---

**Version Gouvernance** : `1.1.0`
**Dernière mise à jour** : 2026-01-21
**Projet** : Viatique - Plateforme de correction de copies dématérialisées
**Contexte** : Production institutionnelle (AEFE / Éducation nationale)
