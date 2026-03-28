# AUDIT KORRIGO — RAPPORT EXHAUSTIF ET CAHIER DES CHARGES
## Date : 28/03/2026 | Auditeur : Claude (Anthropic) | Commanditaire : Shark

---

# TABLE DES MATIÈRES

1. État des lieux de l'architecture
2. Anomalies critiques détectées (P0)
3. Anomalies majeures (P1)
4. Anomalies mineures (P2)
5. Audit multi-examen (BAC BLANC vs DNB BLANC)
6. Audit des statuts de copies
7. Audit des affectations correcteurs
8. Audit de la persistance des données de correction
9. Audit de la sauvegarde et recovery
10. Audit du serveur de production
11. Plan de tests en production
12. Cahier des charges — Actions correctives

---

# 1. ÉTAT DES LIEUX DE L'ARCHITECTURE

## Stack technique

| Composant | Technologie | Localisation |
|-----------|------------|--------------|
| Backend | Django 4.x + DRF | `backend/` |
| Frontend | Vue 3 + Vite + Tailwind | `frontend/` |
| Base de données | PostgreSQL (Docker) | `docker-db-1` |
| Serveur web | Nginx reverse proxy | `infra/nginx/` |
| Conteneurisation | Docker Compose | `infra/docker/` |
| Production | Hetzner VPS 88.99.254.59 | `korrigo.labomaths.tn` |

## Apps Django

| App | Rôle | Modèles |
|-----|------|---------|
| `core` | Auth, settings, audit, health | GlobalSettings, AuditLog, UserProfile |
| `exams` | Examens, copies, booklets, documents | ExamType, Exam, Copy, Booklet, ExamPDF, ExamDocumentSet, ExamDocument, DocumentTextExtraction, DocumentPage, DocumentChunk, JuryReport |
| `grading` | Correction, annotations, scores | Annotation, GradingEvent, CopyLock, DraftState, QuestionRemark, Score, AnnotationTemplate, UserAnnotation, QuestionnaireResponse |
| `students` | Élèves | Student |
| `identification` | Identification copies-élèves | (views) |
| `processing` | OCR, découpage PDF | HeaderDetector |

## Modèle de données — Relations clés

```
ExamType (1) ──→ (N) Exam
Exam (1) ──→ (N) Copy
Exam (1) ──→ (N) Booklet
Exam (M) ←──→ (N) User (correctors ManyToMany)
Copy (N) ──→ (1) Student
Copy (N) ──→ (1) User (assigned_corrector)
Copy (1) ──→ (N) Annotation
Copy (1) ──→ (N) GradingEvent
Copy (1) ──→ (1) Score (UniqueConstraint)
Copy (1) ──→ (N) QuestionRemark
Copy (1) ──→ (1) CopyLock
Copy (1) ──→ (N) DraftState
```

---

# 2. ANOMALIES CRITIQUES (P0) — BLOQUANTES

## P0-001 : DONNÉES MOCK DANS LE DASHBOARD CORRECTEUR (Dashboard.vue)

**Fichier** : `frontend/src/views/Dashboard.vue`, lignes 43-49

**Constat** : Le Dashboard correcteur utilise des **données en dur** au lieu d'appeler l'API :
```javascript
copies.value = [
    { id: '1', anonymous_id: 'A7F93', status: 'GRADED', total_score: 14.5 },
    { id: '2', anonymous_id: 'B2X41', status: 'READY', total_score: 0 },
    // ...
]
```

**Impact** : Le correcteur ne voit **jamais ses vraies copies**. C'est le bug le plus grave de la plateforme.

**Fix** : Remplacer par un appel `api.get(`/exams/${examId}/copies/`)` qui filtre par `assigned_corrector=request.user`.

---

## P0-002 : 6 STATUTS DE COPIES AU LIEU DE 3

**Fichier** : `backend/exams/models.py`, classe `Copy.Status`

**Constat** : Le modèle définit 6 statuts :
```python
STAGING = 'STAGING'           # En attente
READY = 'READY'               # Prêt à corriger
LOCKED = 'LOCKED'             # Verrouillé
GRADING_IN_PROGRESS = 'GRADING_IN_PROGRESS'  # Correction en cours
GRADING_FAILED = 'GRADING_FAILED'            # Échec
GRADED = 'GRADED'             # Corrigé
```

**Exigence** : Shark demande exactement **3 statuts** : `READY` (prêt), `IN_PROGRESS` (en cours), `FINALIZED` (finalisée).

**Impact** : Les statuts `STAGING`, `LOCKED`, `GRADING_FAILED` créent de la confusion et des états zombies.

**Fix** :
1. Migrer vers 3 statuts : `READY`, `IN_PROGRESS`, `FINALIZED`
2. Mapping de transition :
   - `STAGING` → `READY` (les copies uploadées sont immédiatement prêtes dans le mode INDIVIDUAL_A4)
   - `LOCKED` + `GRADING_IN_PROGRESS` → `IN_PROGRESS`
   - `GRADING_FAILED` → `READY` (la copie redevient disponible)
   - `GRADED` → `FINALIZED`
3. Mettre à jour le frontend partout (Dashboard.vue, ProgressDashboard.vue, MyStudents.vue, CorrectorDesk.vue, StudentBilan.vue, CopyLifecycleDiagram.vue)

---

## P0-003 : AUCUN SCRIPT DE BACKUP VERS HETZNER STORAGEBOX

**Constat** : Le script `scripts/korrigo_backup.sh` sauvegarde en local dans `/var/www/labomaths/korrigo/backups/automated/` mais **n'envoie rien vers le StorageBox Hetzner**.

**Impact** : En cas de crash du VPS, **toutes les données sont perdues** (DB + media + corrections).

**Fix** : Ajouter un envoi vers le StorageBox après chaque backup local :

```bash
# À ajouter en fin de korrigo_backup.sh
STORAGEBOX_USER="u402541"  # À vérifier
STORAGEBOX_HOST="u402541.your-storagebox.de"
STORAGEBOX_DIR="/backups/korrigo"

log "Step 3: Syncing to Hetzner StorageBox..."
rsync -avz --progress \
    "${BACKUP_DIR}/" \
    "${STORAGEBOX_USER}@${STORAGEBOX_HOST}:${STORAGEBOX_DIR}/${TIMESTAMP}/" \
    2>>"${LOG_FILE}"

# Ou via SFTP si rsync non disponible
```

**Cron** : Vérifier que le crontab contient :
```
*/30 * * * * /var/www/labomaths/korrigo/scripts/korrigo_backup.sh >> /var/log/korrigo_backup.log 2>&1
```

---

## P0-004 : AFFECTATION CORRECTEUR NON PROPAGÉE AU BACKEND

**Constat** : Le modèle `Exam.correctors` (ManyToMany) permet d'assigner des correcteurs à un examen, mais la vue d'upload `ExamUploadView` ne les propage pas aux copies individuelles (`Copy.assigned_corrector`). Le script `dispatch_dnb_copies.py` existe mais doit être lancé manuellement.

**Impact** : Quand l'admin affecte des correcteurs dans l'interface, les copies ne sont pas automatiquement réparties.

**Fix** :
1. Ajouter un signal `post_save` ou un endpoint dédié qui, quand `Exam.correctors` change, déclenche automatiquement le dispatch des copies
2. Ou : lors de l'upload des copies individuelles (mode INDIVIDUAL_A4), assigner automatiquement les correcteurs via round-robin

---

# 3. ANOMALIES MAJEURES (P1)

## P1-001 : CSV DES ÉLÈVES — SÉPARATEUR INCOHÉRENT

**Constat** :
- `scan_DNB_maths/troisieme.csv` utilise `;` comme séparateur (295 lignes)
- `liste_troisieme.csv` (uploadé par Shark) utilise `,` comme séparateur (294 lignes)
- Le script `setup_dnb_exam.py` doit gérer les deux

**Fix** : Normaliser sur `;` (standard français) ET ajouter une détection automatique du séparateur dans tous les parseurs CSV :
```python
import csv
dialect = csv.Sniffer().sniff(f.read(1024))
f.seek(0)
reader = csv.DictReader(f, delimiter=dialect.delimiter)
```

## P1-002 : MODÈLE STUDENT SANS LIEN EXAM_TYPE

**Constat** : Le modèle `Student` n'a pas de champ `exam_type` ni de lien direct vers `Exam`. Les élèves sont globaux. Un élève de 3ème inscrit au DNB apparaîtra aussi dans le contexte du BAC BLANC si les filtres ne sont pas stricts.

**Fix** : Filtrer via `Copy.student → Copy.exam → Exam.exam_type`. Vérifier que TOUS les endpoints et vues qui listent des élèves passent par ce chemin.

## P1-003 : SCORE MODEL — SCORES_DATA NON VALIDÉ

**Constat** : `Score.scores_data` est un `JSONField` sans validation de structure. Aucune garantie que les données correspondent au `grading_structure` de l'examen.

**Fix** : Ajouter un validateur qui vérifie la cohérence `scores_data` vs `exam.grading_structure` lors du save.

## P1-004 : ABSENCE DE TESTS POUR L'ISOLATION MULTI-EXAMEN

**Constat** : Aucun test unitaire ne vérifie qu'un correcteur assigné au BAC BLANC ne voit pas les copies du DNB BLANC.

**Fix** : Écrire des tests :
- Test : correcteur BAC voit uniquement copies BAC
- Test : correcteur DNB voit uniquement copies DNB
- Test : admin voit tout
- Test : dispatch d'un examen ne touche pas les copies de l'autre
- Test : statistiques par exam_type ne mélangent pas les données

## P1-005 : ANNOTATIONS — VERSION OPTIMISTIC LOCKING NON UTILISÉ CÔTÉ FRONTEND

**Constat** : Le champ `Annotation.version` existe pour le verrouillage optimiste (P0-DI-008) mais aucune trace de son utilisation dans `gradingApi.js`.

**Fix** : Le frontend doit envoyer `version` à chaque PUT et le backend doit rejeter si `version` ne correspond pas (code 409 Conflict).

## P1-006 : EXTRACT_CORRECTION_DATA.PY — COMPLÉTUDE

**Fichier** : `scripts/extract_correction_data.py`

**Vérifier** qu'il exporte bien TOUTES les données de correction :
- Scores (scores_data JSON)
- Annotations (position, contenu, type, score_delta, page)
- QuestionRemarks (question_id, remark)
- DraftStates (payload complet)
- GradingEvents (audit trail)
- Copy.global_appreciation
- Copy.llm_summary
- Copy.subject_variant
- Copy.assigned_corrector
- Copy.student (lien élève)

---

# 4. ANOMALIES MINEURES (P2)

## P2-001 : Frontend — Label `LOCKED` absent du Dashboard

Le Dashboard (`statusLabels`) ne contient pas `LOCKED`. Si une copie est dans cet état, le label brut s'affiche.

## P2-002 : enseignants.csv contenu minimal

`enseignants.csv` ne fait que 512 octets. Vérifier qu'il contient tous les correcteurs (BAC BLANC + DNB BLANC) et leurs rôles.

## P2-003 : Fichier `docker-compose.prod.yml.obsolete`

Fichier obsolète à supprimer du repo pour éviter toute confusion.

## P2-004 : `eval_loi_binom_log.pdf` — 9.5 Mo dans le repo

Fichier PDF qui n'a rien à faire dans le repo Git. Le supprimer ou le déplacer.

## P2-005 : `proofs/` — 33 Mo de captures d'écran

Dossier de preuve de 33 Mo qui alourdit le repo. Envisager `.gitignore` ou LFS.

---

# 5. AUDIT MULTI-EXAMEN : BAC BLANC vs DNB BLANC

## Architecture actuelle

```
ExamType: BAC_BLANC_2026 (code: BB2026)
    └── Exam: "Bac Blanc Maths 2026 J1"
        ├── Copies (mode BATCH_A3, 4 pages/booklet)
        └── Correctors: [liste BAC]

ExamType: DNB_BLANC_MATHS_2026 (code: DNBM2026)
    └── Exam: "DNB_2026"
        ├── Copies (mode INDIVIDUAL_A4, fichiers déjà découpés)
        └── Correctors: [liste DNB]
```

## Points de vérification obligatoires

| Critère | Endpoint/Vue | Vérifié ? |
|---------|-------------|----------|
| Liste copies filtrée par exam | GET /exams/{id}/copies/ | ❓ À vérifier |
| Dashboard correcteur filtré par exam | Dashboard.vue | ❌ Utilise mock data |
| Admin : exams listés avec exam_type | AdminDashboard.vue | ❓ À vérifier |
| Dispatch copies ne mélange pas les examens | dispatch_dnb_copies.py | ❓ |
| Statistiques par examen isolées | StatsReport.vue, views_stats.py | ❓ |
| Barème (grading_structure) différent par examen | Exam.grading_structure | ✅ Par examen |
| Upload CSV par examen | Exam.students_csv | ✅ Par examen |
| Documents (sujet/corrigé/barème) par examen | ExamDocumentSet → Exam | ✅ Par examen |
| Score constraints par examen | Q_MAX_BY_EXAM | ❓ Vérifier le contenu |

## Actions requises

1. **Vérifier `score_constraints.py`** : Le fichier `backend/exams/score_constraints.py` doit contenir les barèmes max pour CHAQUE examen (BAC et DNB)
2. **Filtrage strict dans TOUS les serializers** : `CopySerializer`, `AnnotationSerializer`, `ScoreSerializer` — toujours filtrer par exam_id
3. **Test E2E** : Créer 2 copies (une BAC, une DNB), 2 correcteurs (un pour chaque), vérifier l'isolation totale

---

# 6. AUDIT DES STATUTS DE COPIES

## Exigence : 3 statuts uniquement

| Statut | Signification | Transition |
|--------|--------------|------------|
| `READY` | Copie prête à corriger | État initial après upload |
| `IN_PROGRESS` | Correction en cours | Quand le correcteur commence |
| `FINALIZED` | Correction terminée | Quand le correcteur finalise |

## Transitions autorisées

```
READY ──→ IN_PROGRESS  (correcteur ouvre la copie)
IN_PROGRESS ──→ FINALIZED  (correcteur finalise)
IN_PROGRESS ──→ READY  (correcteur annule / admin réouvre)
FINALIZED ──→ IN_PROGRESS  (admin réouvre pour correction)
```

## Transitions interdites

```
READY ──→ FINALIZED  (impossible de finaliser sans corriger)
FINALIZED ──→ READY  (doit passer par IN_PROGRESS)
```

## Implémentation

### Backend (`exams/models.py`)
```python
class Copy(models.Model):
    class Status(models.TextChoices):
        READY = 'READY', _("Prêt")
        IN_PROGRESS = 'IN_PROGRESS', _("En cours")
        FINALIZED = 'FINALIZED', _("Finalisée")
```

### Migration de données
```python
# Migration : convertir les anciens statuts
def migrate_statuses(apps, schema_editor):
    Copy = apps.get_model('exams', 'Copy')
    Copy.objects.filter(status='STAGING').update(status='READY')
    Copy.objects.filter(status='LOCKED').update(status='IN_PROGRESS')
    Copy.objects.filter(status='GRADING_IN_PROGRESS').update(status='IN_PROGRESS')
    Copy.objects.filter(status='GRADING_FAILED').update(status='READY')
    Copy.objects.filter(status='GRADED').update(status='FINALIZED')
```

### Frontend — Labels et couleurs uniformes

```javascript
const STATUS_CONFIG = {
  READY: { label: 'Prêt', color: '#3B82F6', bg: '#DBEAFE' },
  IN_PROGRESS: { label: 'En cours', color: '#F59E0B', bg: '#FEF3C7' },
  FINALIZED: { label: 'Finalisée', color: '#10B981', bg: '#D1FAE5' },
}
```

Fichiers à mettre à jour :
- `frontend/src/views/Dashboard.vue`
- `frontend/src/views/AdminDashboard.vue`
- `frontend/src/views/admin/CorrectorDesk.vue`
- `frontend/src/views/corrector/MyStudents.vue`
- `frontend/src/views/corrector/StudentBilan.vue`
- `frontend/src/components/ProgressDashboard.vue`
- `frontend/src/components/CopyLifecycleDiagram.vue`

---

# 7. AUDIT DES AFFECTATIONS CORRECTEURS

## Flux attendu

1. Admin crée l'examen et uploade les copies (mode INDIVIDUAL_A4 pour DNB)
2. Admin assigne les correcteurs à l'examen (`Exam.correctors`)
3. **Automatiquement** : les copies sont réparties équitablement entre les correcteurs (`Copy.assigned_corrector`)
4. Chaque correcteur ne voit que SES copies assignées
5. L'admin voit toutes les copies avec le correcteur assigné

## Points à vérifier/implémenter

### Auto-dispatch à l'affectation
```python
# Signal ou endpoint : quand Exam.correctors change → dispatch automatique
@receiver(m2m_changed, sender=Exam.correctors.through)
def auto_dispatch_copies(sender, instance, action, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        dispatch_copies_to_correctors(instance)

def dispatch_copies_to_correctors(exam):
    copies = exam.copies.filter(status='READY', assigned_corrector__isnull=True)
    correctors = list(exam.correctors.all())
    if not correctors:
        return
    for i, copy in enumerate(copies):
        copy.assigned_corrector = correctors[i % len(correctors)]
        copy.assigned_at = timezone.now()
        copy.save(update_fields=['assigned_corrector', 'assigned_at'])
```

### Filtrage côté API
```python
# views.py — endpoint correcteur
def get_queryset(self):
    user = self.request.user
    if user.is_superuser:
        return Copy.objects.all()
    return Copy.objects.filter(assigned_corrector=user)
```

---

# 8. AUDIT DE LA PERSISTANCE DES DONNÉES

## Données de correction à sauvegarder

| Donnée | Modèle | Champs critiques |
|--------|--------|-----------------|
| Notes par question | `Score` | `scores_data` (JSON), `final_comment` |
| Annotations visuelles | `Annotation` | position (x,y,w,h), contenu, type, score_delta, page_index |
| Remarques par question | `QuestionRemark` | question_id, remark |
| Appréciation globale | `Copy` | `global_appreciation` |
| Bilan LLM | `Copy` | `llm_summary` |
| Variante sujet | `Copy` | `subject_variant` |
| Brouillons | `DraftState` | `payload` (JSON complet) |
| Audit trail | `GradingEvent` | action, actor, timestamp, metadata |
| Lien élève | `Copy` | `student`, `is_identified` |

## Vérifications

1. **Score.scores_data** : Vérifier que la structure JSON est identique entre ce que le frontend envoie et ce qui est stocké
2. **DraftState** : Vérifier que l'autosave fonctionne (POST toutes les 30 secondes depuis le frontend)
3. **GradingEvent** : Vérifier qu'un événement est créé pour CHAQUE action (CREATE_ANN, UPDATE_ANN, DELETE_ANN, FINALIZE, REOPEN, etc.)
4. **Annotations** : Vérifier que `on_delete=CASCADE` sur `Copy` → les annotations suivent la copie si elle est supprimée

## Script de récupération d'urgence

Le script `extract_correction_data.py` doit produire un JSON exhaustif par examen :

```json
{
  "exam_id": "...",
  "exam_name": "DNB_2026",
  "export_date": "2026-03-28T01:00:00Z",
  "copies": [
    {
      "anonymous_id": "A7F9-001",
      "student": {"last_name": "SFAR", "first_name": "FATMA", "ddn": "18/09/2011"},
      "status": "FINALIZED",
      "assigned_corrector": "a.benrhouma",
      "global_appreciation": "...",
      "subject_variant": "A",
      "scores": {"ex1_q1": 2, "ex1_q2": 1.5, ...},
      "final_score": 14.5,
      "annotations": [
        {"page": 0, "x": 0.3, "y": 0.5, "type": "COMMENT", "content": "..."}
      ],
      "question_remarks": [
        {"question_id": "ex3_q5", "remark": "..."}
      ],
      "grading_events": [
        {"action": "LOCK", "actor": "a.benrhouma", "timestamp": "..."}
      ]
    }
  ]
}
```

---

# 9. AUDIT DE LA SAUVEGARDE ET RECOVERY

## État actuel

| Composant | Sauvegardé ? | Fréquence | Destination |
|-----------|-------------|-----------|-------------|
| PostgreSQL (dump) | ✅ | 30 min | `/var/www/labomaths/korrigo/backups/automated/` |
| JSON corrections | ✅ | 30 min | `/var/www/labomaths/korrigo/backups/automated/` |
| Media files (PDFs) | ❌ | — | — |
| Hetzner StorageBox | ❌ | — | — |
| Rétention | ✅ | 48 derniers (24h) | Local uniquement |

## Actions requises

### 9.1 Backup media files
```bash
# Ajouter dans korrigo_backup.sh :
log "Step 3: Media files backup..."
tar czf "${BACKUP_DIR}/media_${TIMESTAMP}.tar.gz" \
    -C /var/www/labomaths/korrigo media/ 2>>"${LOG_FILE}"
```

### 9.2 Envoi vers StorageBox
```bash
# Step 4: Sync to Hetzner StorageBox
STORAGEBOX="u402541@u402541.your-storagebox.de"
log "Step 4: Syncing to StorageBox..."
rsync -az --timeout=60 \
    "${BACKUP_DIR}/" \
    "${STORAGEBOX}:/korrigo_backups/${TIMESTAMP}/" 2>>"${LOG_FILE}"
```

### 9.3 Vérification de la crontab
```bash
ssh root@88.99.254.59 "crontab -l | grep korrigo"
# Attendu : */30 * * * * /path/to/korrigo_backup.sh
```

### 9.4 Test de restauration
Exécuter un test de restore sur un environnement staging :
```bash
# 1. Créer une DB temporaire
# 2. Restaurer le dump
# 3. Vérifier les comptages (copies, scores, annotations)
# 4. Comparer avec la prod
```

---

# 10. AUDIT DU SERVEUR DE PRODUCTION

## Vérifications à effectuer via SSH

```bash
ssh root@88.99.254.59
```

### 10.1 État des containers Docker
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
# Vérifier : backend, frontend (nginx), db, tous UP
```

### 10.2 Espace disque
```bash
df -h /var/www/labomaths/korrigo
du -sh /var/www/labomaths/korrigo/media/*
du -sh /var/www/labomaths/korrigo/backups/*
# Alerter si > 80% utilisé
```

### 10.3 Fichiers zombies/orphelins
```bash
# Fichiers media non référencés en DB
docker exec docker-backend-1 python manage.py shell -c "
from exams.models import Copy
import os
media_dir = '/app/media/copies/'
db_files = set(str(c.final_pdf).split('/')[-1] for c in Copy.objects.all() if c.final_pdf)
disk_files = set(os.listdir(media_dir)) if os.path.exists(media_dir) else set()
orphans = disk_files - db_files
print(f'Orphelins: {len(orphans)}')
for f in sorted(orphans)[:20]:
    print(f'  {f}')
"
```

### 10.4 Doublons en DB
```bash
docker exec docker-backend-1 python manage.py shell -c "
from exams.models import Copy, Exam
from django.db.models import Count

# Copies avec même anonymous_id
dupes = Copy.objects.values('anonymous_id').annotate(cnt=Count('id')).filter(cnt__gt=1)
print(f'Doublons anonymous_id: {dupes.count()}')

# Copies sans exam
orphan_copies = Copy.objects.filter(exam__isnull=True).count()
print(f'Copies sans examen: {orphan_copies}')

# Scores sans copie valide
from grading.models import Score
orphan_scores = Score.objects.filter(copy__isnull=True).count()
print(f'Scores orphelins: {orphan_scores}')
"
```

### 10.5 Certificat SSL
```bash
echo | openssl s_client -connect korrigo.labomaths.tn:443 2>/dev/null | openssl x509 -noout -dates
```

### 10.6 Logs d'erreur récents
```bash
docker logs docker-backend-1 --since 24h 2>&1 | grep -E "ERROR|CRITICAL|Exception" | tail -20
```

### 10.7 Migrations en attente
```bash
docker exec docker-backend-1 python manage.py showmigrations | grep "\[ \]"
# Toutes les migrations doivent être appliquées [X]
```

---

# 11. PLAN DE TESTS EN PRODUCTION

## Tests smoke (à exécuter après chaque déploiement)

| # | Test | Commande/Action | Résultat attendu |
|---|------|----------------|-----------------|
| 1 | Page d'accueil accessible | `curl -sI https://korrigo.labomaths.tn` | HTTP 200 |
| 2 | API santé | `curl https://korrigo.labomaths.tn/api/health/` | `{"status":"ok"}` |
| 3 | Login admin | POST `/api/auth/login/` avec credentials admin | Token JWT |
| 4 | Liste examens | GET `/api/exams/` avec token | Liste avec BAC + DNB |
| 5 | Liste copies BAC | GET `/api/exams/{bac_id}/copies/` | Copies BAC uniquement |
| 6 | Liste copies DNB | GET `/api/exams/{dnb_id}/copies/` | Copies DNB uniquement |
| 7 | Login correcteur | POST `/api/auth/login/` correcteur | Token + exams assignés |
| 8 | Copies du correcteur | GET `/api/grading/my-copies/` | Uniquement ses copies |
| 9 | Sauvegarder annotation | POST `/api/grading/annotations/` | 201 Created |
| 10 | Sauvegarder score | POST `/api/grading/scores/` | 201 Created |
| 11 | Finaliser copie | PATCH `/api/copies/{id}/finalize/` | Status → FINALIZED |
| 12 | Export corrections JSON | Script extract_correction_data.py | JSON complet |
| 13 | Backup DB | Script korrigo_backup.sh | Dump créé |
| 14 | Backup StorageBox | rsync vers StorageBox | Fichier présent |

## Tests d'isolation multi-examen

| # | Test | Résultat attendu |
|---|------|-----------------|
| 1 | Correcteur BAC appelle GET copies DNB | 403 Forbidden ou liste vide |
| 2 | Correcteur DNB annote copie BAC | 403 Forbidden |
| 3 | Admin liste copies filtrées par exam_type | Filtrage correct |
| 4 | Stats BAC ne contiennent pas de notes DNB | Vérification des moyennes |
| 5 | Dispatch DNB ne touche pas copies BAC | Comptage avant/après |

## Tests de robustesse

| # | Test | Résultat attendu |
|---|------|-----------------|
| 1 | 2 correcteurs ouvrent la même copie simultanément | Seul le 1er verrouille |
| 2 | Correcteur perd sa connexion pendant correction | DraftState sauvé, reprise OK |
| 3 | Upload d'un PDF corrompu | Rejet avec message d'erreur clair |
| 4 | Suppression accidentelle d'un examen par admin | `on_delete=PROTECT` → refus |
| 5 | Restauration backup → vérification intégrité | Toutes les corrections présentes |

---

# 12. CAHIER DES CHARGES — ACTIONS CORRECTIVES

## Priorité P0 (Bloquant — à faire IMMÉDIATEMENT)

| # | Action | Fichiers | Effort |
|---|--------|---------|--------|
| P0-001 | Remplacer mock data Dashboard.vue par appel API réel | `frontend/src/views/Dashboard.vue` | 2h |
| P0-002 | Migration 3 statuts (READY, IN_PROGRESS, FINALIZED) + migration données | `backend/exams/models.py`, migration, 7 fichiers frontend | 4h |
| P0-003 | Script backup → StorageBox + vérifier crontab 30min | `scripts/korrigo_backup.sh` | 1h |
| P0-004 | Auto-dispatch copies quand Exam.correctors change | `backend/exams/signals.py` ou `views.py` | 2h |

## Priorité P1 (Majeur — cette semaine)

| # | Action | Fichiers | Effort |
|---|--------|---------|--------|
| P1-001 | Détection auto séparateur CSV (`;` ou `,`) | Tous les parseurs CSV | 1h |
| P1-002 | Filtrage Student par exam via Copy→Exam→ExamType | Endpoints students | 1h |
| P1-003 | Validation Score.scores_data vs grading_structure | `backend/grading/models.py` | 2h |
| P1-004 | Tests isolation multi-examen (6 tests) | `backend/tests/` | 3h |
| P1-005 | Optimistic locking annotations côté frontend | `frontend/src/services/gradingApi.js` | 1h |
| P1-006 | Audit complétude extract_correction_data.py | `scripts/extract_correction_data.py` | 2h |

## Priorité P2 (Mineur — cette quinzaine)

| # | Action | Effort |
|---|--------|--------|
| P2-001 | Ajouter label LOCKED au Dashboard (ou supprimer si migration P0-002) | 15min |
| P2-002 | Vérifier et compléter enseignants.csv | 15min |
| P2-003 | Supprimer docker-compose.prod.yml.obsolete | 1min |
| P2-004 | Supprimer eval_loi_binom_log.pdf du repo | 1min |
| P2-005 | Déplacer proofs/ vers Git LFS ou .gitignore | 15min |

## Audit serveur (à faire en SSH avant mise en production DNB)

| # | Action | Commande |
|---|--------|---------|
| 1 | Vérifier containers Docker UP | `docker ps` |
| 2 | Vérifier espace disque | `df -h` |
| 3 | Nettoyer fichiers orphelins media | Script fourni §10.3 |
| 4 | Vérifier doublons en DB | Script fourni §10.4 |
| 5 | Vérifier certificat SSL | `openssl s_client` |
| 6 | Vérifier migrations appliquées | `manage.py showmigrations` |
| 7 | Vérifier crontab backup | `crontab -l` |
| 8 | Vérifier logs erreur | `docker logs` |
| 9 | Test smoke complet (14 tests) | Script §11 |

---

# RÉSUMÉ EXÉCUTIF

| Catégorie | Nombre | Impact |
|-----------|--------|--------|
| P0 — Critiques | 4 | Plateforme inutilisable pour DNB sans fix |
| P1 — Majeures | 6 | Risques de perte/mélange de données |
| P2 — Mineures | 5 | Qualité et propreté du repo |
| Tests requis | 14 smoke + 5 isolation + 5 robustesse | Validation production |

**Estimation effort total** : ~20h de développement pour les P0+P1, ~1h pour les P2, ~4h pour l'audit serveur et les tests.

**⚠️ NE PAS METTRE EN PRODUCTION LE DNB BLANC sans avoir corrigé au minimum les 4 P0.**

---

*Fin du rapport d'audit — Document à transmettre au développeur Claude/Windsurf pour exécution.*
