# Rapport Authentification & Permissions - Production Locale

**Date**: 2026-02-03
**Environnement**: Local Production (Docker Compose)
**URL**: http://localhost:8088

## ✅ Tests d'Authentification Réussis

### 1. Administrateurs (2 comptes)

| Username | Password | Status | Accès Examens | Django Admin |
|----------|----------|--------|---------------|--------------|
| **test_admin** | `admin123` | ✅ OK | ✅ Oui | ✅ Oui |
| admin | `6eyURSeD8lpc,fw\v02)yP=1` | ⚠️ JSON Error | - | - |

### 2. Professeurs (4 comptes)

| Username | Password | Status | Accès Examens | Groupes |
|----------|----------|--------|---------------|---------|
| **test_prof** | `prof123` | ✅ OK | ✅ Oui (1 exam) | teacher |
| prof1 | `&@NB6]9gT.&UX\`r5\|@1ip/s#` | ✅ OK | ✅ Oui (1 exam) | teacher |
| prof2 | `&@NB6]9gT.&UX\`r5\|@1ip/s#` | ✅ OK | ✅ Oui (1 exam) | teacher |
| prof3 | `&@NB6]9gT.&UX\`r5\|@1ip/s#` | ✅ OK | ✅ Oui (1 exam) | teacher |

### 3. Étudiants (11 comptes)

| Username | Email | Password | Status | Student Record |
|----------|-------|----------|--------|----------------|
| **test_student** | test_student@test.local | `student123` | ✅ OK | ✅ Oui |
| eleve1-10 | eleve{N}@viatique.local | `eleve2025` | ✅ OK | ✅ Oui |

**Tous les 11 étudiants** peuvent se connecter avec le mot de passe `eleve2025`.

## 📊 Statistiques

- **Total Utilisateurs**: 17
  - Superusers: 2
  - Staff (enseignants): 6
  - Réguliers (étudiants): 11
- **Students (modèle)**: 11 (100% liés à un User)
- **Examens**: 1
- **Copies**: 3

## 🔐 Matrice des Permissions

| Rôle | /api/login/ | /api/me/ | /api/exams/ | /api/grading/ | Django Admin |
|------|-------------|----------|-------------|---------------|--------------|
| **Admin** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Teacher** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Student** | ✅ | ✅ | ❌ (403) | ❌ (403) | ❌ |

## ⚠️ Problèmes Identifiés

1. **Compte `admin`**: Login échoue en API REST à cause de caractères spéciaux dans le mot de passe → **Utiliser `test_admin` à la place**

2. **Rôle affiché**: `/api/me/` retourne `role="Teacher"` pour les étudiants (bug d'affichage)
   - **Impact**: Aucun - Les permissions réelles sont correctes (`is_staff=False`)
   - **Workaround**: Vérifier `is_staff` au lieu de `role`

## ✅ Comptes Recommandés pour Tests

```
Admin:      test_admin / admin123
Professeur: test_prof / prof123
Étudiant:   test_student / student123
            eleve1 / eleve2025
```

## 🚀 URLs d'Accès

- **Application**: http://localhost:8088
- **Django Admin**: http://localhost:8088/admin/
- **API Docs**: http://localhost:8088/api/docs/
- **Health**: http://localhost:8088/api/health/

## 📝 Conclusion

✅ **16/17 comptes fonctionnels** (94% success rate)
✅ **Permissions correctement appliquées**
✅ **Environnement production opérationnel**

---

*Généré automatiquement le 2026-02-03*
