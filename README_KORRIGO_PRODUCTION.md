# Korrigo — Documentation production

La documentation complète est dans :

`docs/technical/KORRIGO_FULL_STACK_PRODUCTION_README_AND_AUDIT_2026-06-25.md`

Ce document couvre l'architecture, le backend, le frontend, Docker, Nginx, PostgreSQL, Redis, Celery, RGPD, déploiement, backups, tests et exploitation.

## Accès rapide

| Section | Description |
|---------|-------------|
| [Architecture](#3-architecture-générale) | Diagrammes Mermaid, flux HTTP, couches |
| [Services Docker](#6-docker-et-services-production) | 6 services, volumes, réseaux |
| [API](#13-api-et-routage-frontendbackend) | Cartographie complète des endpoints |
| [Sécurité et RGPD](#15-sécurité-et-rgpd) | Mesures, dettes, exposition |
| [Backups et PRA](#16-backups-storagebox-et-pra) | Scripts, fréquence, restauration |
| [Déploiement](#19-déploiement-serveur) | Procédure pas-à-pas |
| [Runbook exploitation](#20-runbook-dexploitation-production) | Incidents, diagnostics, résolutions |

## Autres documents

- [README principal](README.md) — Présentation générale du projet
- [Index documentation](docs/INDEX.md) — Index complet de la documentation
- [Architecture technique](docs/technical/ARCHITECTURE.md) — Architecture détaillée
- [Runbook production](docs/deployment/RUNBOOK_PRODUCTION.md) — Runbook opérationnel
- [RGPD](docs/security/POLITIQUE_RGPD.md) — Politique de protection des données
