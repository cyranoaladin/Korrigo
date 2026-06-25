# Reconciliation overlays Etape 2

Date UTC: 2026-06-20T14:20Z
Branche: `release/reconcile`
Source overlay lue en lecture seule: `/tmp/korrigo_prod_overlay_20260620T1358Z/overlay`, copie SSH de `/var/www/labomaths/korrigo/overlay`.

## Regle canonique

Le chemin canonique Git est le fichier qui produit la cible `/app/...` dans l'image backend. Les doublons `overlay/backend/...` et `overlay/...` ne sont pas dedupliques automatiquement: le compose prod actif determine le fichier monte, et les fichiers non montes sont documentes.

## Decisions fichiers

| Cible canonique | Source decision | Decision | SHA-256 final |
|---|---|---|---|
| `backend/exams/views.py` | `overlay/exams/views.py` actif | Overlay actif integre; ajout local `grading_structure` conserve car strictement additionnel pour le portail eleve; import runtime `Copy` corrige vers `exams.models` pour eviter l'ancien chemin overlay invalide. | `94eaaafe8c3d35a11c9f887d8ff84cd31d80ddf338dc087648b865b113b09a6d` |
| `backend/exams/urls.py` | `overlay/exams/urls.py` actif | Parite exacte avec overlay actif, rien a copier. | `0d368f40f775af63e54dec6f1057ec74bae07bbe908d2e886687e138bf94a140` |
| `backend/exams/permissions.py` | `overlay/exams/permissions.py` actif | Parite exacte avec overlay actif, rien a copier. | `6128754459a5469f896757aa6d2a9458f23e596cb8691c08df1499465cb7e02b` |
| `backend/exams/views_direction.py` | `overlay/exams/views_direction.py` actif | Parite exacte avec overlay actif, rien a copier. | `c442c3aec0dd968ce67d4a7741e88102b3617d2cd72e579dae2b7a2bcd92cc41` |
| `backend/exams/views_jury_report.py` | `overlay/exams/views_jury_report.py` non monte | Fichier `MISSING_IN_IMAGE` integre tel quel. | `74f47ab2557ba7b2a43a76428e00689cd0030f01e585fee1c05f2bd02562c535` |
| `backend/core/views.py` | `overlay/core/views.py` actif | Overlay actif integre; import runtime `Copy` corrige vers `exams.models` pour les flags dashboard/jury report. | `12ce63ca109b53bde8624f0f5e0209063aa7104636bf2e986da5684169c7f48b` |
| `backend/core/settings_prod.py` | `overlay/core/settings_prod.py` actif | Parite exacte avec overlay actif, rien a copier. | `40745b1d267db82c2836722fe233e65b594f3f6350d7a03c42d94afb58a3a9c1` |
| `backend/core/views_platform.py` | `overlay/core/views_platform.py` non monte dans compose prod actif | Source locale/image plus complete que l'overlay dormant; conservee. | `e4a251cd3ea490961fa8ef50c3682c47b163457a5c9c5dfc41cde142603e6fcb` |
| `backend/bilan/permissions.py` | `overlay/backend/bilan/permissions.py` actif | Overlay actif integre avec fallback local `DIRECTION_GROUPS`; import runtime `Copy` corrige vers `exams.models`. | `cc5e995cc2bb562fcf27b78a015c465fa00cceb8fbcb1693c79241b8ee649bbc` |
| `backend/bilan/services/orchestrator_eam.py` | `overlay/backend/bilan/services/orchestrator_eam.py` | Fichier `MISSING_IN_IMAGE` integre tel quel. | `c8a3fe8af7440f748100d21adbccb8eee175fadfc01065b7c90a281ce7658dfb` |
| `backend/bilan/services/rag_retriever_premiere.py` | `overlay/backend/bilan/services/rag_retriever_premiere.py` | Fichier `MISSING_IN_IMAGE` integre tel quel. | `c3c8df5c9f1f672e7f9067053cadb75ecf2d26ff01f773b4caa755e6a43c0a03` |
| `backend/bilan/migrations/0002_alter_bilanreport_exam_type.py` | `overlay/backend/bilan/0002_alter_bilanreport_exam_type.py` | Parite exacte; migration deja presente au chemin Django correct. | `bb145f57c4133fb984a4216832a07ad5a447850880333509d763dd0a78ddcd7c` |
| `backend/exams/migrations/0021_merge_20260513_0001.py` | `overlay/backend/exams/migrations/0021_merge_20260513_0001.py` | Parite exacte; migration deja presente. | `fc0ef04cbeb3156a7ff47d507c7ff0d53b50ed6642ffde97724add41802319f9` |
| `backend/gunicorn_config.py` | `overlay/gunicorn_config.py` non monte dans compose prod actif | Reconciliation manuelle: `gthread`, `GUNICORN_WORKERS`, `max_requests`, `max_requests_jitter`; `GUNICORN_BIND` conserve. | `6d6d06b724d1615983b98bf6821ab3d4aa5ba192470ee6c00994b5c23b1a46ff` |
| `backend/students/serializers.py` | `overlay/students/serializers.py` non monte dans compose prod actif | Parite exacte, rien a copier. | `04306452e40c1d085792d7347ce320da59c965200d421ca2509ca6968495c169` |

## Doublons arbitres

- `overlay/backend/exams/views.py` n'est pas monte par le compose prod actif; `overlay/exams/views.py` est canonique pour `/app/exams/views.py`.
- `overlay/backend/core/views.py` n'est pas monte par le compose prod actif; `overlay/core/views.py` est canonique pour `/app/core/views.py`.
- `overlay/bilan/services/eam_orchestrator.py` fait `29 798` octets et diverge fortement de `overlay/backend/bilan/services/eam_orchestrator.py` / source canonique `94 597` octets. Le fichier canonique reste `backend/bilan/services/eam_orchestrator.py` (`94 597` octets), identique a l'image et a l'overlay actif du compose infra; aucune deduplication automatique n'est faite.
- `overlay/bilan/models.py` est dormant et diverge de `backend/bilan/models.py`; le fichier canonique reste `backend/bilan/models.py`.

## Constat reporte Etape 8/11

L'entrypoint de l'image lance des initialisations Django avant la commande, ce qui casse une restauration sur base vide. L'Etape 2 ne corrige pas ce comportement; il est a rendre idempotent plus tard sans regression.

## Corrections de reconciliation appliquees

- Tous les imports runtime `Copy` pointent vers le modele canonique `exams.models.Copy`; l'ancien chemin `grading.models.Copy` venait de l'overlay/source historique et n'existe pas.
- `backend/grading/migrations/0028_reconcile_peer_review_status_constraint.py` normalise la contrainte `check_peer_review_status_valid` sans changer les valeurs autorisees, afin que le schema migre depuis clone et le schema from-scratch soient identiques.
