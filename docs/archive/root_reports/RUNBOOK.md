# RUNBOOK - Korrigo Production Deployment

## Pre-requisites

- Docker + Docker Compose v2
- Data files in place (CSVs + PDFs)
- `.env.prod` configured

## 1. Build

```bash
cd /home/alaeddine/viatique__PMF

# Build all services
docker compose -f infra/docker/docker-compose.prod.yml build
```

## 2. First Deploy (Zero Config)

```bash
# Set environment variables
export SEED_ON_START=true
export DEFAULT_PASSWORD=passe123

# Copy data files into the container volume
# Option A: Mount data directory in docker-compose
# Option B: Copy after container start

# Start all services
docker compose -f infra/docker/docker-compose.prod.yml up -d

# Verify seed ran successfully
docker compose -f infra/docker/docker-compose.prod.yml logs backend | grep "SEED COMPLETE"
```

## 3. Manual Seed (Alternative)

```bash
# If SEED_ON_START is not set, run manually:
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
    python manage.py seed_initial_exams --data-dir /app/seed_data

# With custom password:
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
    python manage.py seed_initial_exams --password MySecretPass123
```

## 4. Migrate

```bash
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
    python manage.py migrate
```

## 5. Run Backend Tests

```bash
# In development environment with venv:
cd backend
../.venv/bin/python -m pytest exams/tests/test_seed_initial_exams.py -v

# Or in Docker:
docker compose -f infra/docker/docker-compose.yml exec backend \
    python -m pytest exams/tests/test_seed_initial_exams.py -v
```

## 6. Run E2E Tests

```bash
cd frontend/e2e
npx playwright test tests/seed_zero_config.spec.ts --headed
```

## 7. Manual Verification

### 7.1 Admin Login
```bash
# Login
curl -c cookies.txt -X POST http://localhost:8088/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"passe123"}'

# List exams
curl -b cookies.txt http://localhost:8088/api/exams/ | python3 -m json.tool

# Expected: 2 exams (BB Jour 1, BB Jour 2)
```

### 7.2 Verify Correctors
```bash
curl -b cookies.txt http://localhost:8088/api/users/ | python3 -m json.tool
# Expected: admin + 8 correctors + student accounts
```

### 7.3 Corrector Login
```bash
curl -c corr_cookies.txt -X POST http://localhost:8088/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"alaeddine.benrhouma@ert.tn","password":"passe123"}'

# List assigned copies
curl -b corr_cookies.txt http://localhost:8088/api/copies/ | python3 -m json.tool
# Expected: ~26-27 copies for this corrector
```

### 7.4 Verify Copies Count
```bash
# As admin, check J1 copies
EXAM_ID=$(curl -s -b cookies.txt http://localhost:8088/api/exams/ | python3 -c "import sys,json; [print(e['id']) for e in json.load(sys.stdin) if 'Jour 1' in e.get('name','')]")
curl -b cookies.txt "http://localhost:8088/api/exams/$EXAM_ID/copies/" | python3 -c "import sys,json; print(f'J1 copies: {len(json.load(sys.stdin))}')"
```

### 7.5 Verify Bareme
```bash
curl -s -b cookies.txt "http://localhost:8088/api/exams/$EXAM_ID/" | python3 -c "
import sys,json
exam = json.load(sys.stdin)
structure = exam.get('grading_structure', [])
print(f'Exercices: {len(structure)}')
for ex in structure:
    count = len([c for c in ex.get('children', []) if c.get('type') == 'question'])
    print(f'  {ex[\"title\"]}: {count} questions directes')
"
```

### 7.6 Score Save + Finalize Test
```bash
# Get a copy ID (as corrector)
COPY_ID=$(curl -s -b corr_cookies.txt http://localhost:8088/api/copies/ | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

# Save scores
curl -b corr_cookies.txt -X PUT "http://localhost:8088/api/grading/copies/$COPY_ID/scores/" \
  -H "Content-Type: application/json" \
  -d '{"scores_data": {"1.1": 3, "1.2": 4}, "final_comment": ""}'

# Save appreciation
curl -b corr_cookies.txt -X PATCH "http://localhost:8088/api/grading/copies/$COPY_ID/global-appreciation/" \
  -H "Content-Type: application/json" \
  -d '{"global_appreciation": "Bon travail dans l ensemble."}'
```

## 8. Troubleshooting

### Seed fails with "relation does not exist"
```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_initial_exams
```

### Copies not visible to corrector
```bash
# Check dispatch status
docker compose exec backend python manage.py shell -c "
from exams.models import Copy, Exam
for e in Exam.objects.all():
    total = Copy.objects.filter(exam=e).count()
    assigned = Copy.objects.filter(exam=e, assigned_corrector__isnull=False).count()
    print(f'{e.name}: {assigned}/{total} assigned')
"
```

### Re-run seed after fixing data
```bash
docker compose exec backend python manage.py seed_initial_exams --force
```

## 9. Data Backup

```bash
docker compose exec backend python manage.py backup --include-media --output-dir /app/backups/
```

## 10. Acceptance Checklist

- [ ] Fresh install: `docker compose up` creates everything
- [ ] Reboot: seed idempotent, no duplication
- [ ] All accounts exist with `passe123`
- [ ] PDFs imported and dispatched (balanced)
- [ ] Corrector grading works (scores + appreciation persist)
- [ ] Copy not finalizable without all scores + appreciation
- [ ] Student sees copy only when finalized + released
- [ ] Dashboard stats visible after grading
- [ ] All backend tests pass
- [ ] E2E tests pass
