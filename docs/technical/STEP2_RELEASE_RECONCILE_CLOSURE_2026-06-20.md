# Etape 2 - cloture technique avant build propre

Date UTC: 2026-06-20
Branche: `release/reconcile`

## Modele `Copy`

Le modele canonique est `exams.models.Copy`; sa table est `exams_copy`.

`grading.models` ne definit pas de classe `Copy` propre au module `grading`. Il importe `Copy` depuis `exams.models` pour declarer ses ForeignKey (`Annotation.copy`, `GradingEvent.copy`, `CopyLock.copy`, etc.). En Python, `grading.models.Copy` est donc un alias de module vers la meme classe que `exams.models.Copy`, pas un second modele ni une seconde table.

Les corrections d'import appliquees dans `bilan.permissions`, `core.views`, `exams.views`, `seed_e2e.py` et les tests sont semantiquement neutres: elles remplacent un chemin indirect par le chemin canonique, sans changer la classe cible. Si `grading.models.Copy` avait ete une classe distincte, l'impact aurait ete majeur: les permissions/dashboard auraient interroge une autre table ou un autre modele. Ce n'est pas le cas ici.

## Orchestrateurs bilan EAM

Deux fichiers coexistent:

- `backend/bilan/services/eam_orchestrator.py`, classe `EamBilanOrchestrator`, environ 94 Ko. C'est le flux réellement cable: `backend/bilan/views.py` importe `EamBilanOrchestrator` depuis `.services.eam_orchestrator` et l'utilise dans `generate_bilan()` quand `exam_slug` contient `EAM BLANCHE`.
- `backend/bilan/services/orchestrator_eam.py`, classe `BilanOrchestratorEAM`, fichier `MISSING_IN_IMAGE` integre depuis l'overlay. Aucun import runtime direct n'a ete trouve dans `backend/bilan`, `backend/grading` ou `backend/exams`.

Conclusion Etape 2: `eam_orchestrator.py` est le flux actif; `orchestrator_eam.py` est conserve car il etait classe `MISSING_IN_IMAGE`, mais il semble redondant/dormant. Ne pas supprimer maintenant. A traiter en Etape 7 avec analyse fonctionnelle et tests de non-regression.

## Historique migrations et divergence `exams.0038`

Etat observe:

- `exams.0038_copy_check_copy_status_valid.py` en Git ajoute une contrainte a 5 statuts: `READY`, `LOCKED`, `IN_PROGRESS`, `GRADED`, `FINALIZED`.
- La DB restauree depuis StorageBox marque `exams.0038`, `0039`, `0040`, `0041` comme appliquees.
- Le schema live restaure expose une contrainte physique a 3 statuts: `READY`, `IN_PROGRESS`, `FINALIZED`.

Le controle complet d'historique doit comparer `django_migrations` restaure avec les fichiers presents dans l'image propre sur toutes les apps. La decision attendue est:

- aucune migration appliquee en DB sans fichier dans l'image;
- aucune migration fichier inattendue en attente, sauf `exams.0042`, `exams.0043`, `grading.0028`;
- aucune migration fantome expliquant le passage de 5 a 3 statuts.

Si ce controle confirme l'absence de migration fantome, la cause formelle est un drift physique non trace par `django_migrations` (probablement SQL manuel ou artefact de deploiement historique non versionne). `exams.0043_reconcile_copy_status_constraint.py` est alors la reconciliation volontaire de l'etat final live dans le graphe Django.

## Contrainte `grading.0028`

`grading.0027_peerreviewcorrection_peerreviewevent_and_more.py` et le schema live autorisent les memes valeurs: `NOT_STARTED`, `IN_PROGRESS`, `FINALIZED`.

Le diff initial clone vs base vide ne portait pas sur les valeurs mais sur la serialisation PostgreSQL de `pg_get_constraintdef()`:

- clone restaure: `ARRAY[('NOT_STARTED'::character varying)::text, ...]`;
- base vide: `(ARRAY['NOT_STARTED'::character varying, ...])::text[]`.

`grading.0028_reconcile_peer_review_status_constraint.py` stabilise la definition physique PostgreSQL sans changement metier. La migration est conditionnee a PostgreSQL; elle est no-op sous SQLite pour conserver les tests unitaires.

## Deltas comportementaux vs prod actuelle

### Gunicorn

La release source conserve le passage au worker `gthread`:

- ancien comportement image/prod: commande `gunicorn ... --workers 3` et logique historique `cpu*2+1`/sync selon configuration;
- release: `backend/gunicorn_config.py` configure `worker_class='gthread'`, `workers=int(GUNICORN_WORKERS, default 4)`, `threads=4`, `max_requests=1000`, `max_requests_jitter=100`, `timeout=120`.

Decision prod attendue: definir explicitement `GUNICORN_WORKERS=4` dans l'environnement de deploiement initial, puis ajuster apres observation CPU/RAM. Retester en recette: uploads PDF, finalisation PDF, consultation eleve en parallele.

### Nginx

Deltas integres dans `infra/nginx/nginx.conf`:

- `resolver 127.0.0.11` pour upstream Docker dynamique;
- rate limits eleves: `student_login` a `30r/s` avec `burst=60`, `student_api` a `100r/s` avec `burst=200`;
- `/api/media/` et `/api/grading/copies/<id>/final-pdf/` masquent les headers upstream et reappliquent `X-Frame-Options SAMEORIGIN` + CSP adaptee pour iframe PDF;
- headers de securite reappliques sur les locations qui utilisent `add_header`.

Decision prod attendue: garder ces deltas en recette, verifier que le proxy amont transmet bien `X-Forwarded-Proto` et `X-Real-IP`; tester login eleve depuis IP partagee, rendu PDF eleve, media proteges et admin Django.

### Entrypoint et migrations

`backend/entrypoint.sh` lance `python manage.py migrate` si `DJANGO_AUTO_MIGRATE` n'est pas `false`, puis continue les initialisations; certaines erreurs non critiques sont avalees plus loin (`create_user_roles || true`). Pour l'Etape 3, ne pas compter sur l'entrypoint pour appliquer les migrations de release.

Plan Etape 3 attendu:

1. backup complet juste avant bascule;
2. deployment par digest GHCR, sans tag flottant;
3. `DJANGO_AUTO_MIGRATE=false` pendant le demarrage applicatif;
4. application explicite et observee de `exams.0042`, `exams.0043`, `grading.0028` via `python manage.py migrate --noinput` dans un conteneur one-shot;
5. surveiller les locks: `0043` et `0028` font un `DROP/ADD CONSTRAINT` impliquant un verrou `ACCESS EXCLUSIVE` bref sur des tables de petite taille (`exams_copy` environ 733 lignes dans le backup de reference);
6. health backend/celery/nginx, parcours roles et logs avant retrait des overlays prod.

## Image prod et image test

L'image prod doit etre construite depuis `backend/Dockerfile` avec `INSTALL_DEV_REQUIREMENTS=false` (valeur par defaut ou arg explicite). Elle ne doit pas contenir `pytest`.

Les tests backend doivent utiliser une image separee du meme commit avec `INSTALL_DEV_REQUIREMENTS=true`, non publiee, ou un montage source jetable. L'absence de `backend/seed_e2e.py` du contexte Docker prod est volontaire: `backend/.dockerignore` exclut `seed_*.py`; c'est un script de dev/e2e, pas un fichier runtime.

## Recette UI

Les tests unitaires frontend (`vitest`, incluant `AdminPasswordReset.test.ts`) sont requis en Etape 2. Les parcours UI complets Playwright admin/correcteur/eleve/direction sont reportes a la recette Etape 6; ne pas cocher une validation de parcours UI complet avant execution explicite.
