# Plan de Test - Korrigo PMF

**Date**: 25 janvier 2026  
**Version**: 1.0  
**Auditeur**: Codex

## 1. Objectif

Valider la conformité du projet Korrigo PMF aux spécifications fonctionnelles et techniques, avec une attention particulière aux aspects critiques pour la production.

## 2. Périmètre de Test

### 2.1 Fonctionnalités à Tester

| Module | Fonctionnalité | Priorité | Statut Actuel | Type Test |
|--------|----------------|----------|---------------|-----------|
| **Identification** | OCR assisté + validation humaine | CRITIQUE | ❌ Non implémenté | **GATE** |
| **Authentification** | Triple portail (Admin/Prof/Élève) | CRITIQUE | ⚠️ Partiel | **GATE** |
| **PDF Processing** | Ingestion, découpage A3→A4 | HAUTE | ✅ OK | Unitaires |
| **État Copy** | Machine d'états (STAGING→READY→LOCKED→GRADED) | CRITIQUE | ✅ OK | Intégration |
| **Concurrence** | Verrouillage copies (CopyLock) | HAUTE | ✅ OK | Concurrence |
| **Annotations** | Coordonnées normalisées | HAUTE | ✅ OK | Unitaires |
| **Sécurité** | Validation PDF avancée | CRITIQUE | ✅ OK | Sécurité |
| **Export** | CSV Pronote | MOYENNE | ⚠️ Partiel | Intégration |
| **Consultation** | Portail élève | MOYENNE | ⚠️ Partiel | Intégration |

### 2.2 Types de Tests

- **Unitaires**: Tests unitaires backend (pytest)
- **Intégration**: Tests API endpoints (DRF)
- **Concurrence**: Tests de charge et verrouillage
- **Sécurité**: Tests de validation et injection
- **E2E**: Tests bout-en-bout Playwright
- **GATE**: Tests critiques bloquants pour production

## 3. Stratégie de Test

### 3.1 Tests Unitaires Backend

**Objectif**: Valider la logique métier isolée

**Commande**:
```bash
cd backend
source .venv/bin/activate  # Si disponible
python -m pytest grading/tests/test_services_strict_unit.py -v
```

**Fichiers concernés**:
- `backend/grading/tests/test_services_strict_unit.py`
- `backend/exams/tests/test_pdf_validators.py`
- `backend/grading/tests/test_workflow.py`

### 3.2 Tests d'Intégration API

**Objectif**: Valider les endpoints REST

**Commande**:
```bash
python -m pytest grading/tests/test_integration_real.py -v
```

**Fichiers concernés**:
- `backend/grading/tests/test_integration_real.py`
- `backend/grading/tests/test_fixtures_advanced.py`

### 3.3 Tests de Concurrence

**Objectif**: Valider le verrouillage et la gestion de la concurrence

**Commande**:
```bash
python -m pytest grading/tests/test_concurrency.py -v
```

**Fichiers concernés**:
- `backend/grading/tests/test_concurrency.py`
- `backend/grading/tests/test_anti_loss.py`

### 3.4 Tests de Sécurité

**Objectif**: Valider les validations et protections

**Commande**:
```bash
python -m pytest exams/tests/test_pdf_validators.py -v
python -m pytest grading/tests/test_error_handling.py -v
```

**Fichiers concernés**:
- `backend/exams/tests/test_pdf_validators.py`
- `backend/grading/tests/test_error_handling.py`

### 3.5 Tests E2E

**Objectif**: Valider le workflow complet "Bac Blanc"

**Commande**:
```bash
# Backend seed
python backend/seed_e2e.py

# Frontend E2E
cd frontend
npm run test:e2e
```

**Fichiers concernés**:
- `frontend/tests/e2e/`
- `backend/seed_e2e.py`

## 4. Tests Critiques (GATES)

### 4.1 Gate 1: Identification OCR

**Objectif**: Valider le workflow d'identification sans QR Code

**Critère de succès**:
- [ ] OCR capable de lire les noms/prénoms sur en-têtes
- [ ] Interface "Video-Coding" fonctionnelle
- [ ] Liaison Copie↔Élève réussie

**Statut**: ❌ **ÉCHEC PRÉVU** - Fonctionnalité non implémentée

### 4.2 Gate 2: Authentification Triple Portail

**Objectif**: Valider la séparation des rôles

**Critère de succès**:
- [ ] Portail Admin fonctionnel
- [ ] Portail Prof fonctionnel
- [ ] Portail Élève fonctionnel
- [ ] RBAC correctement appliqué

**Statut**: ⚠️ **RISQUE ÉLEVÉ** - Partiellement implémenté

### 4.3 Gate 3: Workflow Complet "Bac Blanc"

**Objectif**: Valider le workflow de bout en bout

**Scénario**:
1. Upload PDF examen
2. Découpage A3→A4
3. Identification des copies
4. Anonymisation
5. Correction par prof
6. Finalisation
7. Export CSV Pronote
8. Consultation par élève

**Critère de succès**:
- [ ] Workflow complet sans erreur
- [ ] Données cohérentes à chaque étape
- [ ] Audit trail complet

**Statut**: ❌ **ÉCHEC PRÉVU** - Étapes critiques manquantes

## 5. Commandes d'Exécution

### 5.1 Environnement de Test

```bash
# Setup Docker
docker-compose -f infra/docker/docker-compose.yml up -d --build

# Migrations
docker-compose exec backend python manage.py migrate

# Tests backend
docker-compose exec -T backend python -m pytest grading/tests/ -v --tb=short

# Tests frontend E2E
cd frontend && npm run test:e2e
```

### 5.2 Tests de Production

```bash
# Environnement prodlike
docker-compose -f infra/docker/docker-compose.prodlike.yml up -d --build
docker-compose -f infra/docker/docker-compose.prodlike.yml exec backend python manage.py migrate

# Tests complets
docker-compose -f infra/docker/docker-compose.prodlike.yml exec -T backend python -m pytest --cov=. --cov-report=html
```

## 6. Indicateurs de Qualité

| Métrique | Cible | Actuel | Statut |
|----------|-------|--------|--------|
| Couverture de code | >80% | ? | ❓ |
| Tests unitaires | 100% passants | ? | ❓ |
| Tests E2E | 100% passants | ❌ | ❌ |
| Temps réponse API | <500ms | ? | ❓ |
| Sécurité PDF | Validations complètes | ✅ | ✅ |

## 7. Risques de Test

### 7.1 Risques Techniques

1. **Environnement instable**: Docker compose peut ne pas fonctionner correctement
2. **Dépendances manquantes**: OCR libraries non installées
3. **Tests flaky**: Tests de concurrence instables

### 7.2 Risques Fonctionnels

1. **Fonctionnalités manquantes**: Tests impossibles à exécuter
2. **Données insuffisantes**: Tests E2E sans données réalistes
3. **Authentification incomplète**: Tests bloqués par accès refusé

## 8. Conclusion

Le plan de test révèle plusieurs **GATES critiques** qui seront **ÉCHOUÉES** en l'état actuel du projet. La mise en production est **IMPOSSIBLE** tant que les fonctionnalités suivantes ne sont pas implémentées:

1. **Module d'identification OCR**
2. **Interface "Video-Coding"**
3. **Authentification triple portail complète**
4. **Tests E2E complets du workflow**

**Recommandation**: Ne pas procéder à la mise en production tant que les gates critiques ne sont pas passées avec succès.