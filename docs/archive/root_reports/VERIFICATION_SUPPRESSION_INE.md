# Vérification: Suppression Complète de l'INE

**Date**: 2026-02-10  
**Statut**: ⚠️ MIGRATION EN COURS

---

## ✅ Modifications Complétées

### Backend - App Students

| Fichier | Statut | Action |
|---------|--------|--------|
| `students/models.py` | ✅ OK | INE supprimé, date_naissance ajouté |
| `students/serializers.py` | ✅ OK | Champs mis à jour |
| `students/views.py` (StudentImportView) | ✅ OK | Parser CSV nouveau format |
| `students/views.py` (StudentLoginView) | ✅ OK | Auth nom+prénom+date |
| `students/views.py` (StudentListView) | ✅ OK | search_fields mis à jour (ligne 110) |
| `students/admin.py` | ✅ OK | list_display mis à jour |
| `students/tests/test_gate4_flow.py` | ✅ OK | Tests mis à jour |
| `students/migrations/0003_*.py` | ✅ OK | Migration créée |
| `students/services/csv_import.py` | ✅ ARCHIVÉ | → `.obsolete` |
| `students/management/commands/import_students.py` | ✅ ARCHIVÉ | → `.obsolete` |
| `students/tests/test_import_students_csv.py` | ✅ ARCHIVÉ | → `.obsolete` |

---

## ⚠️ Fichiers Backend à Mettre à Jour

### Scripts de Seed (PRIORITÉ HAUTE)

Ces scripts sont utilisés pour créer des données de test/dev et **NE FONCTIONNERONT PLUS** tant qu'ils ne seront pas mis à jour.

| Fichier | Lignes | Statut | Impact |
|---------|--------|--------|--------|
| `backend/seed_prod.py` | 151, 160, 162 | ❌ À CORRIGER | Seed production |
| `backend/scripts/seed_gate4.py` | 27, 35, 88 | ❌ À CORRIGER | Tests Gate 4 |
| `backend/scripts/seed_e2e.py` | 271, 280 | ❌ À CORRIGER | Tests E2E |
| `backend/scripts/creation_profils_test.py` | 43, 52, 54 | ❌ À CORRIGER | Création profils test |

**Exemple de correction** (`seed_prod.py`):

```python
# AVANT
student, _ = Student.objects.get_or_create(
    ine=f"INE{i:03d}PROD",
    defaults={
        "last_name": f"STUDENT{i}",
        "first_name": f"Test",
        "class_name": class_name
    }
)

# APRÈS
from datetime import date
student, _ = Student.objects.get_or_create(
    last_name=f"STUDENT{i}",
    first_name=f"Test",
    date_naissance=date(2005 + (i % 3), 1 + (i % 12), 1 + (i % 28)),
    defaults={
        "class_name": class_name,
        "email": f"test{i}@example.com"
    }
)
```

---

### Tests Backend (PRIORITÉ MOYENNE)

Tests qui échoueront tant que non mis à jour:

| Fichier | Lignes | Statut |
|---------|--------|--------|
| `core/test_auth_rbac.py` | 55 | ❌ À CORRIGER |
| `core/tests/test_full_audit.py` | 22, 58, 68, 94, 103 | ❌ À CORRIGER |
| `core/tests/test_rate_limiting.py` | 39 | ❌ À CORRIGER |
| `tests/test_api_bac_blanc.py` | 53 | ❌ À CORRIGER |
| `tests/test_backup_restore.py` | 32 | ❌ À CORRIGER |
| `identification/test_e2e_bac_blanc.py` | 50, 312, 320 | ❌ À CORRIGER |
| `identification/test_workflow.py` | 28, 120, 155 | ❌ À CORRIGER |
| `identification/test_backup_restore_full.py` | 35, 89 | ❌ À CORRIGER |
| `identification/test_ocr_assisted.py` | 31, 153 | ❌ À CORRIGER |
| `identification/tests.py` | 24, 92, 153 | ❌ À CORRIGER |

**Exemple de correction** (`test_full_audit.py`):

```python
# AVANT
self.student = Student.objects.create(
    ine="123456789", 
    last_name="BEN ALI", 
    first_name="Amine"
)

response = self.client.post('/api/students/login/', {
    'ine': '123456789', 
    'last_name': 'BEN ALI'
})

# APRÈS
from datetime import date
self.student = Student.objects.create(
    last_name="BEN ALI",
    first_name="Amine",
    date_naissance=date(2005, 3, 15),
    class_name="TS1"
)

response = self.client.post('/api/students/login/', {
    'last_name': 'BEN ALI',
    'first_name': 'Amine',
    'date_naissance': '2005-03-15'
})
```

---

### Commande Management (PRIORITÉ BASSE)

| Fichier | Lignes | Statut | Impact |
|---------|--------|--------|--------|
| `exams/management/commands/export_pronote.py` | 27, 30, 55 | ⚠️ PROBLÉMATIQUE | Export Pronote |

**⚠️ ATTENTION**: Ce fichier exporte vers Pronote qui **REQUIERT l'INE**.

**Options**:
1. **Conserver INE dans Student** (ajout d'un champ optionnel)
2. **Mapping manuel** INE ↔ (nom+prénom+date) dans une table séparée
3. **Générer un pseudo-INE** à partir du hash de (nom+prénom+date)

**Recommandation**: Option 3 - Génération pseudo-INE

```python
import hashlib

def generate_pseudo_ine(last_name, first_name, date_naissance):
    """Generate a unique pseudo-INE from student identity."""
    data = f"{last_name.upper()}{first_name.upper()}{date_naissance.isoformat()}"
    hash_val = hashlib.sha256(data.encode()).hexdigest()[:10]
    # Format: 10 digits + 1 letter (like real INE)
    return hash_val.upper() + 'Z'
```

---

## ❌ Frontend à Mettre à Jour (PRIORITÉ HAUTE)

### Authentification Élève

| Fichier | Lignes | Statut | Impact |
|---------|--------|--------|--------|
| `frontend/src/stores/auth.js` | 26, 28 | ❌ CRITIQUE | Login élève cassé |
| `frontend/src/views/student/LoginStudent.vue` | 6, 17, 41, 43 | ❌ CRITIQUE | Formulaire login |

**Avant** (`LoginStudent.vue`):
```vue
<template>
  <div>
    <label>Identifiant National (INE)</label>
    <input v-model="ine" placeholder="ex: 123456789A" />
    
    <label>Nom</label>
    <input v-model="lastName" />
    
    <button @click="login">Connexion</button>
  </div>
</template>

<script setup>
const ine = ref('')
const lastName = ref('')

async function login() {
  await authStore.loginStudent(ine.value, lastName.value)
}
</script>
```

**Après** (`LoginStudent.vue`):
```vue
<template>
  <div>
    <label>Nom</label>
    <input v-model="lastName" placeholder="ex: DUPONT" />
    
    <label>Prénom</label>
    <input v-model="firstName" placeholder="ex: Jean" />
    
    <label>Date de naissance</label>
    <input type="date" v-model="dateNaissance" />
    
    <button @click="login">Connexion</button>
  </div>
</template>

<script setup>
const lastName = ref('')
const firstName = ref('')
const dateNaissance = ref('')

async function login() {
  await authStore.loginStudent(lastName.value, firstName.value, dateNaissance.value)
}
</script>
```

**Store** (`auth.js`):
```javascript
// AVANT
async function loginStudent(ine, lastName) {
    const res = await api.post('/students/login/', { ine, last_name: lastName })
    // ...
}

// APRÈS
async function loginStudent(lastName, firstName, dateNaissance) {
    const res = await api.post('/students/login/', {
        last_name: lastName,
        first_name: firstName,
        date_naissance: dateNaissance
    })
    // ...
}
```

---

### Gestion des Utilisateurs (Admin)

| Fichier | Lignes | Statut |
|---------|--------|--------|
| `frontend/src/views/admin/UserManagement.vue` | 45, 264, 285 | ❌ À CORRIGER |
| `frontend/src/views/admin/IdentificationDesk.vue` | 70, 98 | ❌ À CORRIGER |

**Corrections** (`UserManagement.vue`):

```vue
<!-- AVANT -->
<th>INE</th>
<!-- ... -->
<td>{{ item.ine }}</td>

<!-- APRÈS -->
<th>Date de naissance</th>
<!-- ... -->
<td>{{ formatDate(item.date_naissance) }}</td>

<!-- Recherche -->
<!-- AVANT -->
(item.ine?.toLowerCase() || '').includes(lower)

<!-- APRÈS -->
(item.email?.toLowerCase() || '').includes(lower)
```

---

### Tests E2E Frontend

| Fichier | Lignes | Statut |
|---------|--------|--------|
| `frontend/tests/e2e/helpers/auth.ts` | 17 | ❌ À CORRIGER |
| `frontend/tests/e2e/student_flow.spec.ts` | 50, 93, 98, 113, 142 | ❌ À CORRIGER |

**Avant** (`auth.ts`):
```typescript
export const CREDS = {
    student: {
        ine: process.env.E2E_STUDENT_INE || '123456789',
        lastname: 'E2E_STUDENT'
    }
}
```

**Après** (`auth.ts`):
```typescript
export const CREDS = {
    student: {
        lastname: 'E2E_STUDENT',
        firstname: 'Jean',
        dateNaissance: '2005-03-15'
    }
}
```

**Avant** (`student_flow.spec.ts`):
```typescript
await page.fill('input[placeholder="ex: 123456789A"]', CREDS.student.ine);
await page.fill('input[placeholder="Nom"]', CREDS.student.lastname);
```

**Après** (`student_flow.spec.ts`):
```typescript
await page.fill('input[placeholder="Nom"]', CREDS.student.lastname);
await page.fill('input[placeholder="Prénom"]', CREDS.student.firstname);
await page.fill('input[type="date"]', CREDS.student.dateNaissance);
```

---

## 📊 Résumé des Fichiers Affectés

### Backend

| Catégorie | Fichiers | Statut |
|-----------|----------|--------|
| **Modèles & Core** | 11 | ✅ OK |
| **Scripts Seed** | 4 | ❌ À CORRIGER |
| **Tests** | 10 | ❌ À CORRIGER |
| **Commands** | 1 | ⚠️ PROBLÉMATIQUE |
| **Migrations** | 2 | ✅ OK (historique) |
| **Total Backend** | **28** | **15 à corriger** |

### Frontend

| Catégorie | Fichiers | Statut |
|-----------|----------|--------|
| **Stores** | 1 | ❌ À CORRIGER |
| **Vues** | 3 | ❌ À CORRIGER |
| **Tests E2E** | 2 | ❌ À CORRIGER |
| **Total Frontend** | **6** | **6 à corriger** |

### TOTAL GLOBAL

- **34 fichiers** affectés
- **21 fichiers** à corriger
- **11 fichiers** déjà OK
- **2 fichiers** migrations (historique OK)

---

## 🚨 Risques & Blocages

### 1. Export Pronote ⚠️ CRITIQUE

Le système Pronote **REQUIERT l'INE** pour l'import des notes.

**Solutions possibles**:

1. **Ajouter un champ INE optionnel** dans Student
   ```python
   class Student(models.Model):
       # ... champs existants ...
       ine = models.CharField(max_length=11, blank=True, null=True, verbose_name="INE (optionnel)")
   ```

2. **Créer une table de mapping**
   ```python
   class StudentINEMapping(models.Model):
       student = models.OneToOneField(Student, on_delete=models.CASCADE)
       ine = models.CharField(max_length=11, unique=True)
       created_at = models.DateTimeField(auto_now_add=True)
   ```

3. **Générer un pseudo-INE déterministe**
   ```python
   @property
   def pseudo_ine(self):
       import hashlib
       data = f"{self.last_name}{self.first_name}{self.date_naissance}"
       return hashlib.sha256(data.encode()).hexdigest()[:11].upper()
   ```

**Recommandation**: Solution 3 (pseudo-INE) car:
- ✅ Pas de modification du modèle
- ✅ Déterministe (toujours le même pour un élève)
- ✅ Unique (collision quasi-impossible)
- ⚠️ Incompatible avec Pronote réel (uniquement pour tests)

Si Pronote est utilisé en production → **Solution 2 (table mapping)**

---

### 2. Tests Cassés

**Tous les tests backend/frontend échoueront** tant qu'ils ne seront pas mis à jour.

**Commande pour identifier les tests cassés**:
```bash
cd backend
python manage.py test students 2>&1 | grep -E "FAIL|ERROR"
```

---

### 3. Seed Scripts Cassés

Les scripts de seed ne fonctionneront plus:
```bash
# Ceci échouera
python backend/seed_prod.py

# Error: Student() missing 1 required positional argument: 'date_naissance'
```

---

## ✅ Actions Immédiates Requises

### Priorité 1 - CRITIQUE (Login Cassé)

- [ ] Mettre à jour `frontend/src/stores/auth.js`
- [ ] Mettre à jour `frontend/src/views/student/LoginStudent.vue`
- [ ] Tester le login élève manuellement

### Priorité 2 - HAUTE (Seed & Tests)

- [ ] Corriger `backend/seed_prod.py`
- [ ] Corriger `backend/scripts/seed_gate4.py`
- [ ] Corriger `backend/scripts/seed_e2e.py`
- [ ] Corriger `backend/scripts/creation_profils_test.py`

### Priorité 3 - MOYENNE (Frontend Admin)

- [ ] Mettre à jour `frontend/src/views/admin/UserManagement.vue`
- [ ] Mettre à jour `frontend/src/views/admin/IdentificationDesk.vue`
- [ ] Mettre à jour tests E2E frontend

### Priorité 4 - BASSE (Tests Backend)

- [ ] Corriger tous les fichiers de tests backend (10 fichiers)
- [ ] Lancer la suite de tests complète: `python manage.py test`

### Priorité 5 - SPÉCIAL (Export Pronote)

- [ ] Décider de la solution pour l'export Pronote (INE requis)
- [ ] Implémenter la solution choisie

---

## 🔍 Commandes de Vérification

### Vérifier toutes les références INE restantes

```bash
# Backend
cd backend
grep -r "\bine\b" --include="*.py" . | grep -v "migrations" | grep -v ".obsolete" | wc -l

# Frontend
cd frontend
grep -r "\bine\b" --include="*.{vue,js,ts}" src/ tests/ | wc -l
```

### Tester la migration

```bash
cd backend
source ../venv/bin/activate

# Vérifier les migrations
python manage.py showmigrations students

# Appliquer si pas encore fait
python manage.py migrate students

# Vérifier l'intégrité
python manage.py check
```

### Tester l'import CSV

```bash
# Créer un fichier test
cat > /tmp/test_students.csv << 'EOF'
Élèves,Né(e) le,Adresse E-mail,Classe,Groupe
DUPONT JEAN,15/03/2005,jean.dupont@test.tn,TS1,G2
MARTIN SOPHIE,20/07/2005,sophie.martin@test.tn,TS2,G1
EOF

# Tester via API (nécessite serveur lancé + auth)
curl -X POST http://localhost:8000/api/students/import/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "file=@/tmp/test_students.csv"
```

---

## 📚 Documentation

- **Guide de migration**: `CHANGEMENT_MODELE_STUDENT.md`
- **Workflow audit**: `WORKFLOW_AUDIT.md`
- **Ce rapport**: `VERIFICATION_SUPPRESSION_INE.md`

---

**Dernière mise à jour**: 2026-02-10  
**Auteur**: Équipe Développement
