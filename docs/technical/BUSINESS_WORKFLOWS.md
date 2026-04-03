# Workflows Métier — Korrigo v2

> **Version** : 3.1
> **Date** : 2026-04-03
> **Public** : Développeurs, Product Owners, Administrateurs

---

## Vue d'ensemble

Korrigo est une plateforme de correction numérique d'examens scannés. Le cycle complet va de l'ingestion des PDFs scannés jusqu'à la publication des résultats annotés aux élèves, en passant par l'identification, le dispatch et la correction annotée.

```
Scans PDF
   │
   ▼
Ingestion (BATCH_A3 ou INDIVIDUAL_A4)
   │
   ▼
Copies en statut READY
   │
   ▼
Identification élèves (OCR ou import CSV + matching)
   │
   ▼
Dispatch aux correcteurs
   │
   ▼
Correction annotée (IN_PROGRESS)
   │
   ▼
Finalisation PDF (FINALIZED)
   │
   ▼
Publication résultats → Élèves
```

---

## Workflow 1 : Ingestion en mode BATCH_A3

**Acteur** : Admin ou Enseignant avec permissions upload
**Cas d'usage** : Copies scannées en lot sur scanner A3 (feuilles A4 recto-verso = A3)

### Préconditions
- Examen créé avec `upload_mode=BATCH_A3`
- PDF valide (extension `.pdf`, max 50 MB, max 500 pages, vrai PDF)

### Étapes
1. Admin sélectionne l'examen dans le dashboard
2. Clique "Uploader copies" → `ExamUploadModal`
3. Sélectionne le PDF batch → `POST /api/exams/upload/`
4. Backend : `PDFSplitter` découpe le PDF en fascicules (`Booklet`)
   - Chaque fascicule = N pages consécutives (logique de découpage configurable)
   - PyMuPDF rastérise chaque page en PNG 144 DPI (`copies/pages/{uuid}/p000.png`, …)
5. Chaque `Booklet` génère une `Copy` (statut=READY, anonymous_id=`IMPORT-XXXXXXXX`)
6. `GradingEvent.IMPORT` enregistré pour traçabilité

### Postconditions
- N copies en statut READY
- Pages PNG disponibles dans `/media/copies/pages/`
- Dashboard affiche les nouvelles copies

### Cas d'erreur
- PDF corrompu → `400` avec message explicite
- Copies IN_PROGRESS ou FINALIZED déjà présentes → `409` (re-upload bloqué, intégrité protégée)
- Espace disque insuffisant → `500`

---

## Workflow 2 : Ingestion en mode INDIVIDUAL_A4 (workflow DNB)

**Acteur** : Admin
**Cas d'usage** : Un PDF A4 par élève, pré-découpé avant upload (ex : DNB 2026)

### Préconditions
- Examen créé avec `upload_mode=INDIVIDUAL_A4`
- PDFs nommés selon le format `NOM_PRENOM_DDMMYYYY.pdf`
  - Exemple : `ABBES_MYRIAM_03122010.pdf`
- Élèves importés dans la table `students_student`

### Étapes
1. Upload en masse via `POST /api/exams/{id}/upload-individual-pdfs/`
   - Chaque PDF → 1 `Copy` (READY) + 1 `ExamPDF` (`student_identifier=NOM_PRENOM_DDMMYYYY`)
2. **Identification automatique** via `python manage.py identify_dnb_copies`
   - Pour chaque copie non-identifiée, parse `student_identifier` → `(name_part, date_naissance)`
   - Lookup dans `students_student` par DDN exacte
   - Si 1 candidat : match direct
   - Si plusieurs : score fuzzy `SequenceMatcher` ≥ 0.65 sur nom+prénom
   - Si 0 : copie reste non-identifiée (avertissement)
   - Met à jour : `copy.student`, `copy.is_identified=True`

### Résultats DNB 2026
- 289 copies importées, 294 élèves importés
- 289/289 copies identifiées (100%) en un seul passage

### Postconditions
- Toutes les copies READY avec `is_identified=True`
- `copy.student` lié à l'élève correspondant

---

## Workflow 3 : Import d'élèves depuis CSV

**Acteur** : Admin (ligne de commande)
**Commande** : `python manage.py import_dnb_students [--file troisieme.csv] [--dry-run]`

### Format CSV attendu
```csv
Nom;Prenom;Date_Naissance;Mail;Classe
AKROUT;RAHMA;22/07/2011;rahma.akrout-e@ert.tn;3.1
BEN RHOUMA;KAMEL;26/06/2011;kamel.benrhouma-e@ert.tn;3.5
```

Séparateur auto-détecté (`;` ou `,`). En-têtes insensibles à la casse.

### Traitement par ligne
1. `_normalize_name()` : mise en MAJUSCULES, strip
2. `_parse_date()` : formats DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY
3. Email sanitisation : split sur `" et "` → prend le premier (cas "addr1 et addr2")
4. `Student.objects.get_or_create(last_name, first_name, date_naissance)`
5. Si créé : `User.objects.get_or_create(username=email)` puis association au `Student`
6. Ajout au groupe Django `STUDENT`
7. `student.user = user` si non lié

### Options
- `--dry-run` : simule sans écriture
- `--file` : nom du fichier (défaut : `troisieme.csv`)
- `--dir` : répertoire contenant le CSV (défaut : `scan_DNB_maths/`)
- `--password` : paramètre historique d'anciens imports ; ne fait pas partie du flux élève canonique actuel

### Idempotence
La clé unique `(last_name, first_name, date_naissance)` garantit qu'un import multiple ne crée pas de doublons. Seuls email et classe sont mis à jour si changés.

---

## Workflow 4 : Dispatch des copies vers les correcteurs

**Acteur** : Admin
**Méthode standard** : `POST /api/exams/{id}/dispatch-copies/`

### Règles de dispatch (DNB 2026 — exemple)
1. **Pas d'auto-correction** : un enseignant ne corrige pas ses propres élèves (lookup dans `classes_troisieme.csv`)
2. **Contraintes individuelles** : KAMEL BEN RHOUMA (3.5) → exclure NASRI, SAADI, BEN TIBA
3. **Distribution équitable** : tri des enseignants par nombre de copies croissant → round-robin équitable

### Algorithme de dispatch équitable
```python
def pick_teacher(forbidden_emails):
    available = [(count, email) for email, count in counts.items()
                 if email not in forbidden_emails]
    available.sort()  # Enseignant avec le moins de copies en premier
    return available[0][1]
```

### Résultat DNB 2026
| Enseignant | Email | Copies | Classes gérées |
|-----------|-------|--------|---------------|
| Fatma ABID | fatma.abid@ert.tn | 49 | 3.1, 3.7 |
| Maroua FRAIJI | maroua.fraiji@ert.tn | 48 | 3.2, 3.4 |
| Chawki SAADI | chawki.saadi@ert.tn | 48 | 3.3 |
| Soumaya NASRI | soumaya.nasri@ert.tn | 48 | 3.5, 3.6 |
| Sami BEN TIBA | sami.bentiba@ert.tn | 48 | 3.8, 3.9 |
| Gilles COLLY | gilles.colly@ert.tn | 48 | 3.10 |

---

## Workflow 5 : Correction annotée (workflow principal enseignant)

**Acteur** : Enseignant (Correcteur)
**Interface** : `CorrectorDesk.vue`

### Préconditions
- `copy.assigned_corrector = user` courant
- `copy.status ∈ {READY, IN_PROGRESS}`

### Étapes détaillées

#### 1. Accès à la copie
- Dashboard → liste copies READY/IN_PROGRESS
- Clic → `GET /api/grading/copies/{id}/` → chargement complet

#### 2. Accès à la copie
- la copie doit être assignée au correcteur courant
- la machine à états active est `READY → IN_PROGRESS → FINALIZED`
- les anciens endpoints explicites de lock ne font plus partie du workflow métier de référence

#### 3. Visualisation PDF
- PDF.js charge `booklets[0].pages_images` (PNGs rastérisés)
- Canvas overlay pour le dessin des annotations

#### 4. Création d'annotations (transition READY → IN_PROGRESS)
- Clic-glisser sur la page PDF → rectangle sélectionné
- Coordonnées en pixels → normalisées [0,1] via `canvas.getBoundingClientRect()`
- `POST /api/grading/copies/{id}/annotations/`
- **Première annotation : copie passe automatiquement à IN_PROGRESS**
- Annotation affichée immédiatement en overlay coloré

#### 5. Types d'annotations disponibles
| Type | Couleur | Raccourci | Usage |
|------|---------|-----------|-------|
| COMMENT | Bleu | C | Commentaire libre |
| ERROR | Rouge | E | Erreur pénalisante |
| BONUS | Vert | B | Point bonus |
| VRAI | Vert ✓ | V | Réponse correcte |
| FAUX | Rouge ✗ | F | Réponse incorrecte |
| HIGHLIGHT | Jaune | H | Mise en évidence |

#### 6. Saisie des notes
- Panel latéral : structure de l'examen (`grading_structure`)
- Note par question → `POST /api/grading/copies/{id}/score/`
- Score total calculé automatiquement (somme des notes)

#### 7. Appréciation globale
- Textarea → `POST /api/grading/copies/{id}/appreciation/`
- Auto-save toutes les 30 secondes

#### 8. Sauvegarde automatique (anti-perte de données)
- `DraftState` : snapshot de l'état toutes les 30s
- `POST /api/grading/copies/{id}/draft/`
- Récupéré automatiquement si reconnexion

#### 9. Finalisation
- Bouton "Finaliser" → modal de confirmation
- `POST /api/grading/copies/{id}/finalize/`
- Backend :
  1. verrou transactionnel `select_for_update(nowait=True)`
  2. transition atomique du statut vers `FINALIZED`
  3. `PDFFlattener.flatten_copy()` : imprime les annotations sur le PDF source → bytes
  4. sauvegarde `copy.final_pdf` dans `copies/final/`
  5. `GradingEvent.FINALIZE` enregistré
- Frontend : notification "Copie finalisée", retour au dashboard

### Postconditions
- `copy.status == FINALIZED`
- `copy.final_pdf` : PDF annoté disponible
- `copy.graded_at` : timestamp de finalisation
- la copie n’est plus modifiable par un correcteur standard

---

## Workflow 6 : Publication des résultats aux élèves

**Acteur** : Admin
**Précondition** : toutes les copies souhaitées en FINALIZED

### Étapes
1. Admin vérifie les statistiques de l'examen (`GET /api/exams/{id}/stats/`)
2. `POST /api/exams/{id}/release-results/` → `exam.results_released_at = now()`
3. Les élèves peuvent se connecter avec email + date de naissance
4. `GET /api/students/my-copies/` retourne les copies dont `exam.results_released_at` est défini

### Vue élève
- Liste des copies finalisées
- Visualisation du PDF annoté (`final_pdf`)
- Score obtenu
- Appréciation globale du correcteur
- Bilan IA (si généré)

---

## Workflow 7 : Bilan IA (LLM)

**Acteur** : Système (Celery) déclenché par Admin
**Service** : Ollama (qwen2.5:32b ou llama3.2)

### Étapes
1. Admin déclenche la génération après finalisation
2. Celery task `generate_questionnaire_bilan_task` envoyée au broker Redis
3. Pour chaque copie FINALIZED sans `llm_summary` :
   - Collecte annotations, score, appréciation
   - Prompt LLM : génère un bilan personnalisé en français
4. Résultat sauvegardé dans `copy.llm_summary`
5. Visible dans l'espace élève après publication

### Format du bilan
Texte structuré : points forts, axes d'amélioration, conseils méthodologiques, encouragements.

---

## Workflow 8 : Identification manuelle par secrétariat

**Acteur** : Secrétaire / Admin
**Interface** : `IdentificationDesk.vue`

### Préconditions
- Copies avec `is_identified=False`

### Étapes
1. Liste des copies non-identifiées
2. Clic sur une copie → vue de l'en-tête
3. `POST /api/identification/perform-ocr/{copy_id}/`
   - GPT-4o-mini Vision extrait le texte de l'en-tête
   - Fallback Tesseract si GPT-4o indisponible
   - Matching fuzzy avec la liste des élèves
4. Liste de suggestions avec scores de confiance affichée
5. Secrétaire valide ou sélectionne manuellement
6. `POST /api/identification/identify/{copy_id}/` → `{student_id}`
7. Copie marquée `is_identified=True`

---

## Workflow 9 : Réouverture admin (cas exceptionnel)

**Acteur** : Admin (superuser uniquement)
**Précondition** : Copie en statut FINALIZED avec erreur détectée après finalisation

### Procédure
1. Admin identifie la copie concernée
2. `POST /api/grading/copies/{id}/reopen/` — **superuser requis**
3. Effets :
   - `status → READY`
   - `final_pdf` effacé (fichier supprimé)
   - `graded_at → null`
   - `grading_retries → 0`
   - `GradingEvent.REOPEN` enregistré avec `{old_status, old_pdf}`
4. **Conservé** : annotations, notes (Score), appréciation, bilan LLM
5. L'enseignant assigné peut re-corriger normalement

### Traçabilité
Chaque réouverture est tracée dans `GradingEvent` avec l'acteur admin et les métadonnées de l'état précédent.

---

## Workflow 10 : Gestion des erreurs de finalisation

### Finalisation concurrente
- une seule requête peut entrer dans la section critique
- les doublons sont rejetés avec `LockConflictError`
- le frontend doit traiter ce cas comme un `409` logique et proposer un rechargement

### Panne pendant la finalisation
- si la génération du PDF échoue, la transaction n’aboutit pas à un état `FINALIZED` valide
- `grading_error_message` peut être renseigné
- un retry est possible après diagnostic

### Copie abandonnée `IN_PROGRESS`
En cas d’abandon prolongé :
```bash
docker exec docker-backend-1 python manage.py recover_stuck_copies
```

---

## Workflow 11 : Export vers Pronote

**Acteur** : Admin
**Commande** : `python manage.py export_pronote --exam DNB_2026`

### Préconditions
- Copies FINALIZED avec scores
- Élèves identifiés

### Sortie
Fichier CSV compatible Pronote :
```csv
Nom;Prénom;Classe;Note;Appréciation
AKROUT;RAHMA;3.1;14.5;"Bon travail..."
BEN RHOUMA;KAMEL;3.5;12.0;"..."
```

---

## Résumé des acteurs et permissions

| Acteur | Permissions clés |
|--------|-----------------|
| **Admin** (superuser + ADMIN) | Tout : créer examens, uploader, dispatcher, release results, réouvrir, export |
| **Enseignant** (TEACHER) | Voir ses copies assignées, corriger, annoter, finaliser |
| **Secrétaire** | Identifier copies (OCR + validation manuelle) |
| **Élève** (STUDENT) | Voir ses propres copies finalisées (si résultats publiés) |
