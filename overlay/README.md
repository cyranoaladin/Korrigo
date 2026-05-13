# Overlay — Hotfixes de production

Ce répertoire contient les fichiers de surcharge (overlays) montés dans les containers Docker de production via `docker-compose.prod.yml`. Ces fichiers permettent d'appliquer des correctifs urgents sans reconstruire l'image Docker.

## Fichiers actifs (montés en production)

| Fichier overlay | Destination dans le container |
|---|---|
| `core/views.py` | `/app/core/views.py` |
| `core/views_platform.py` | `/app/core/views_platform.py` |
| `gunicorn_config.py` | `/app/gunicorn_config.py` |
| `grading/views.py` | `/app/grading/views.py` |
| `students/views.py` | `/app/students/views.py` |
| `students/urls.py` | `/app/students/urls.py` |
| `exams/views.py` | `/app/exams/views.py` |
| `exams/permissions.py` | `/app/exams/permissions.py` |
| `exams/urls.py` | `/app/exams/urls.py` |
| `exams/views_direction.py` | `/app/exams/views_direction.py` |
| `backend/bilan/models.py` | `/app/bilan/models.py` |
| `backend/bilan/views.py` | `/app/bilan/views.py` |
| `backend/bilan/urls.py` | `/app/bilan/urls.py` |
| `backend/bilan/permissions.py` | `/app/bilan/permissions.py` |
| `backend/bilan/services/rag_retriever.py` | `/app/bilan/services/rag_retriever.py` |
| `backend/bilan/services/orchestrator.py` | `/app/bilan/services/orchestrator.py` |
| `backend/bilan/services/eam_orchestrator.py` | `/app/bilan/services/eam_orchestrator.py` |
| `backend/bilan/services/llm_writer.py` | `/app/bilan/services/llm_writer.py` |
| `backend/bilan/0002_alter_bilanreport_exam_type.py` | `/app/bilan/migrations/0002_alter_bilanreport_exam_type.py` |

## Fichiers de référence / archives

| Fichier | Statut |
|---|---|
| `backend/core/views.py` | Copie de référence (non monté — `core/views.py` est utilisé) |
| `backend/exams/*.py` | Copies de référence (non montées) |
| `bilan/` | Copies legacy (non montées) |
| `core/settings_prod.py` | Référence settings (non monté) |
| `exams/views_jury_report.py` | Non monté (désactivé) |
| `frontend/src/views/corrector/StudentBilan.vue` | Non monté |
| `students/serializers.py` | Non monté |
| `stat_BB_MATHS_2026.md` | Stats jury BB MATHS 2026 |

## Correctifs inclus dans `core/views.py`

- **Direction role detection** : Les groupes `direction_all`, `direction_lycee`, `direction_college` sont reconnus → redirection vers `/direction/dashboard` à la connexion
- **P0.2 security** : Le mot de passe temporaire n'est pas renvoyé dans la réponse API de réinitialisation

## Principe

L'overlay est un mécanisme de hotfix temporaire. Chaque fichier overlay devrait être réintégré dans l'image Docker lors du prochain cycle de refactoring. La gouvernance à long terme est d'éliminer ces overrides en les fusionnant dans le code source principal.
