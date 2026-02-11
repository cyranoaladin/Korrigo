# SEED_EXAMS - Zero Config Production Setup

## Overview

The `seed_initial_exams` management command creates a complete production environment with:
- 1 admin account
- 8 corrector accounts (4 per exam)
- All student accounts from CSV files
- 2 exams with full baremes
- Imported PDF copies
- Anonymous copy codes
- Copy dispatch to correctors

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SEED_ON_START` | `false` | Set to `true` to auto-run seed on container start |
| `DEFAULT_PASSWORD` | `passe123` | Initial password for all accounts |
| `SEED_DATA_DIR` | `/app/seed_data` | Directory containing CSV and PDF files |

## Data Directory Structure

```
seed_data/
  eleves_maths_J1.csv
  eleves_maths_J2.csv
  copies_finales_J1/
    copie_DUPONT_JEAN.pdf
    copie_MARTIN_PAUL.pdf
    ...
  copies_finales_J2/
    copie_GARCIA_MARIE.pdf
    ...
```

## Usage

### Manual Run
```bash
python manage.py seed_initial_exams
python manage.py seed_initial_exams --force          # Reset passwords
python manage.py seed_initial_exams --password xyz   # Custom password
python manage.py seed_initial_exams --data-dir /path # Custom data dir
python manage.py seed_initial_exams --dry-run        # Preview only
```

### Docker Auto-Run
Set in docker-compose or .env:
```yaml
environment:
  SEED_ON_START: "true"
  DEFAULT_PASSWORD: "passe123"
```

## Idempotence Rules

| Entity | Create | Re-run behavior |
|--------|--------|-----------------|
| Groups | `get_or_create` | No change |
| Admin | `get_or_create` | No password change (unless --force) |
| Correctors | `get_or_create` | No password change (unless --force) |
| Students | `get_or_create` by email | No duplicate; updates name/class |
| Exams | `get_or_create` by name | Updates barème if empty |
| Copies | Check by anonymous_id | Skip if exists |
| Dispatch | Only unassigned copies | No reshuffle if grading started |

## Anonymization

Each copy receives a stable 7-character code:
- Format: `AA9999C` (2 letters + 4 digits + 1 checksum)
- Generated from: `SHA256(exam_id:filename)`
- Deterministic: same inputs always produce same code
- Checksum: `sum(ascii) % 10`

## Accounts Created

### Admin
- Username: `admin`
- Email: `labo.maths@ert.tn`
- Password: `passe123` (or DEFAULT_PASSWORD)

### Correctors J1 (BB Jour 1)
| Name | Email |
|------|-------|
| Alaeddine BEN RHOUMA | alaeddine.benrhouma@ert.tn |
| Patrick DUPONT | patrick.dupont@ert.tn |
| Philippe CARR | philippe.carr@ert.tn |
| Selima KLIBI | selima.klibi@ert.tn |

### Correctors J2 (BB Jour 2)
| Name | Email |
|------|-------|
| Chawki SAADI | chawki.saadi@ert.tn |
| Edouard ROUSSEAU | edouard.rousseau@ert.tn |
| Sami BEN TIBA | sami.bentiba@ert.tn |
| Laroussi LAROUSSI | laroussi.laroussi@ert.tn |

### Students
- Created from CSV files (79 J1 + 103 J2)
- Login: email as username
- Password: `passe123`

## Bareme Structure

### BB Jour 1
- Exercice 1: 5 questions
- Exercice 2: 14 questions (with sub-questions)
- Exercice 3: 8 questions (with sub-questions)
- Exercice 4: 11 questions (4 parties: A, B, C, D)

### BB Jour 2
- Exercice 1: 6 questions
- Exercice 2: 10 questions (parts A, B)
- Exercice 3: 7 questions
- Exercice 4: 9 questions (parts A, B)

## Safety

- Never logs passwords
- Emails are safe to log
- Atomic transaction: all-or-nothing
- No data loss on re-run
- Grading work preserved across re-seeds
