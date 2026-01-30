# E2E Testing Contract

## Environnement de Référence

**Les tests E2E (Playwright) sont conçus pour et doivent être exécutés dans un environnement Docker Compose.**

Cette décision est:
- ✅ **Factuelle:** Tests conçus pour architecture Docker
- ✅ **Défendable:** Aligne avec environnement CI/CD
- ✅ **Assumée:** C'est un choix d'architecture produit

## Architecture Requise

### Environment Docker

```yaml
# infra/docker/docker-compose.local-prod.yml
services:
  backend:   # Django
  frontend:  # Reverse proxy vers Vite
  db:        # PostgreSQL
  redis:     # Celery broker
```

**Caractéristiques:**
- Frontend + Backend servis via reverse proxy sur même host/port
- Réseau Docker interne pour services (DB, Redis)
- Gestion CSRF automatique via configuration Docker
- Variables d'environnement injectées automatiquement

### Topologie

| Service | URL Interne | URL Externe |
|---------|-------------|-------------|
| Frontend + Backend | http://backend:8000 | http://localhost:8088 |
| PostgreSQL | postgres://db:5432 | localhost:55432 |
| Redis | redis://redis:6379 | N/A (Docker network) |

## Seed Data

### Script de Référence

**Utiliser:** `backend/scripts/seed_e2e.py`

**NE PAS utiliser:** `backend/seed_e2e.py` (racine, obsolète pour E2E)

### Données Créées

**Users (Django auth):**
- `admin` / password (superuser)
- `prof1` / password (staff, teacher)

**Students (modèle Student):**
- INE: `123456789`, Nom: `E2E_STUDENT` (Gate 4)
- INE: `987654321`, Nom: `OTHER` (tests sécurité)

**Exams & Copies:**
- 1 Exam principal avec Copy READY
- 3 Copies Gate 4 (GRADED, LOCKED, OTHER)

### Exécution Seed

```bash
# Dans conteneur backend Docker
docker-compose -f infra/docker/docker-compose.local-prod.yml exec backend \
  sh -c "export PYTHONPATH=/app && python scripts/seed_e2e.py"
```

## Authentification

### Teacher/Admin

**Endpoint:** `/api/login/`
**Méthode:** POST
**Body:**
```json
{
  "username": "admin",
  "password": "password"
}
```

**Session:** Cookie-based + CSRF token

### Student

**Endpoint:** `/api/students/login/`
**Méthode:** POST
**Body:**
```json
{
  "ine": "123456789",
  "last_name": "E2E_STUDENT"
}
```

**Session:** Cookie-based (pas de CSRF pour student public endpoint)

**⚠️ Important:** Student login n'utilise PAS username/password, mais INE + nom de famille.

## Exécution E2E

### Commande Standard

```bash
# 1. Démarrer environnement Docker
cd infra/docker
docker-compose -f docker-compose.local-prod.yml up -d

# 2. Seed data (si pas déjà fait)
docker-compose exec backend sh -c "export PYTHONPATH=/app && python scripts/seed_e2e.py"

# 3. Lancer tests E2E
cd ../../frontend
npx playwright test
```

### Configuration Playwright

**Fichier:** `frontend/playwright.config.ts`

```typescript
export default defineConfig({
    testDir: './tests/e2e',
    globalSetup: './tests/e2e/global-setup.ts',  // Seed via Docker
    use: {
        baseURL: 'http://localhost:8088',  // Backend reverse proxy
    },
});
```

## Environnement Local (Hors Docker)

### État Actuel

**L'exécution E2E en mode "local" (Vite 5173 + Django 8088 séparés) n'est PAS supportée.**

**Raisons techniques:**

1. **CSRF Protection (6 tests):**
   - `DEBUG=false` active CSRF strict Django
   - Tests ne gèrent pas extraction/injection token CSRF
   - Architecture séparée (5173 vs 8088) complique gestion cookies

2. **URL Mismatch:**
   - Tests attendent: `http://localhost:8088/admin-dashboard`
   - Navigateur reçoit: `http://localhost:5173/teacher/login`
   - Cause: Pas de reverse proxy unifié

3. **Redis/Celery:**
   - `CELERY_BROKER_URL=redis://redis:6379/0` (hostname Docker)
   - Pas accessible depuis processus locaux hors réseau Docker

### Support Futur (Optionnel)

Si support local requis, actions nécessaires:

1. **CSRF Handling:**
```typescript
// frontend/tests/e2e/helpers/csrf.ts
async function getCsrfToken(page) {
  const response = await page.request.get('/api/csrf/');
  const cookies = await page.context().cookies();
  return cookies.find(c => c.name === 'csrftoken')?.value;
}
```

2. **Configuration Conditionnelle:**
```typescript
// playwright.config.ts
use: {
  baseURL: process.env.E2E_BASE_URL || 'http://localhost:8088',
}
```

3. **Adapter Seed:**
Exécuter `scripts/seed_e2e.py` localement avec PYTHONPATH correct.

**Effort estimé:** 2-4 heures d'adaptation.

## CI/CD

### GitHub Actions / GitLab CI

```yaml
jobs:
  e2e-tests:
    steps:
      - name: Start Docker Compose
        run: |
          cd infra/docker
          docker-compose -f docker-compose.local-prod.yml up -d

      - name: Wait for services
        run: |
          docker-compose exec -T backend python manage.py wait_for_db

      - name: Seed E2E data
        run: |
          docker-compose exec -T backend sh -c \
            "export PYTHONPATH=/app && python scripts/seed_e2e.py"

      - name: Run E2E tests
        run: |
          cd frontend
          npx playwright test --reporter=html
```

## Résolution Problèmes

### Erreur: "Identifiants invalides" (Student Login)

**Cause:** Student n'existe pas en DB ou seed pas exécuté.

**Solution:**
```bash
# Vérifier Students en DB
docker-compose exec backend python manage.py shell -c \
  "from students.models import Student; \
   print(list(Student.objects.values('ine', 'last_name')))"

# Si vide, réexécuter seed
docker-compose exec backend sh -c \
  "export PYTHONPATH=/app && python scripts/seed_e2e.py"
```

**Attendu:**
```python
[{'ine': '123456789', 'last_name': 'E2E_STUDENT'}, ...]
```

### Erreur: CSRF 403 Forbidden

**Cause:** Tests exécutés hors Docker.

**Solution:** Exécuter dans Docker Compose (voir section "Exécution E2E").

### Erreur: URL mismatch (expected /admin-dashboard)

**Cause:** Tests exécutés contre Vite dev server (5173) au lieu de backend (8088).

**Solution:** Vérifier `playwright.config.ts` → `baseURL: 'http://localhost:8088'`

## Comportements Produit Documentés

### Flux Correcteur : Restauration de Brouillon Local

**Scénario:** Correcteur annote une copie, sauvegarde, puis recharge la page.

**Comportement attendu:**

1. **Sauvegarde initiale** : Annotation sauvegardée sur serveur + brouillon local (localStorage)
2. **Rechargement page** : Modal apparaît : *"Restaurer le brouillon non sauvegardé (LOCAL) ?"*
3. **Clic "Oui, restaurer"** : L'éditeur d'annotation s'ouvre avec le contenu restauré
4. **Action requise** : L'utilisateur doit **re-sauvegarder** pour que l'annotation apparaisse dans la liste

**Raison technique:**

Le brouillon local permet de récupérer le travail en cas de crash/fermeture accidentelle. La restauration rouvre l'éditeur (pas d'auto-sauvegarde) pour que l'utilisateur puisse :
- Continuer à éditer
- Sauvegarder à nouveau
- Annuler (supprimer le brouillon)

**Tests E2E concernés:**

- `corrector_flow.spec.ts` : "Full Corrector Cycle: Login -> Lock -> Annotate -> Autosave -> Refresh -> Restore"

**Implémentation E2E:**

```typescript
// Après page.reload()
const restoreModal = page.getByText(/Restaurer le brouillon/i);
if (await restoreModal.isVisible({ timeout: 4000 })) {
    await page.getByRole('button', { name: /Oui, restaurer/i }).click();

    // Vérifier que l'éditeur contient le contenu restauré
    await expect(page.locator('textarea')).toHaveValue('Test E2E Annotation');

    // Re-sauvegarder pour ajouter à la liste
    await page.click('.editor-actions .btn-primary');
    await expect(page.getByTestId('save-indicator')).toContainText('Sauvegardé');
}
```

**Note:** Ce comportement est intentionnel et aligné avec les meilleures pratiques UX (confirmation avant action automatique).

## Responsabilités

### Développeurs

- **Exécuter E2E en Docker** avant merge
- Ne pas adapter tests pour environnement non-Docker sans validation Lead
- Maintenir seed `scripts/seed_e2e.py` synchronisé avec tests

### CI/CD

- **Environnement de référence:** Docker Compose
- Seed obligatoire avant tests E2E
- Rapport HTML uploadé en artifact

### Lead/Architecture

- Décider si support local E2E nécessaire (coût: 2-4h)
- Maintenir ce contrat à jour
- Valider changements seed data

## Conclusion

**Les tests E2E sont un contrat d'infrastructure, pas uniquement de code.**

L'environnement Docker Compose est la **référence unique** pour:
- Validation pre-merge
- CI/CD
- Reproduction bugs

Le mode local (Vite + Django séparés) est pour **développement rapide**, pas pour E2E.

---

**Version:** 1.0
**Date:** 2026-01-30
**Auteur:** Architecture Team
**Statut:** ✅ Décision Produit Validée
