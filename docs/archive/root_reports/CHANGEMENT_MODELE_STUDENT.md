# Changement du Modèle Student - Migration INE vers Date de Naissance

**Date**: 2026-02-10  
**Version**: 1.0

---

## 🎯 Objectif

Remplacer l'utilisation de l'INE (Identifiant National Élève) par un système d'identification basé sur:
- **Nom** (last_name)
- **Prénom** (first_name)
- **Date de naissance** (date_naissance)

Cette combinaison constitue désormais la **clé primaire unique** pour identifier un élève.

---

## 📋 Modifications Effectuées

### 1. Modèle Student (`students/models.py`)

#### Avant
```python
class Student(models.Model):
    ine = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    class_name = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)
```

#### Après
```python
class Student(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    date_naissance = models.DateField(verbose_name="Date de naissance")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    class_name = models.CharField(max_length=50, verbose_name="Classe")
    groupe = models.CharField(max_length=20, blank=True, null=True, verbose_name="Groupe")
    
    class Meta:
        unique_together = [['last_name', 'first_name', 'date_naissance']]
        indexes = [
            models.Index(fields=['last_name', 'first_name', 'date_naissance']),
        ]
```

**Nouveaux champs**:
- ✅ `date_naissance` (DateField, obligatoire)
- ✅ `groupe` (CharField, optionnel) - Ex: "G1", "G2", "G3"

**Champs supprimés**:
- ❌ `ine` (remplacé par la combinaison nom+prénom+date)

---

### 2. Authentification Student (`students/views.py`)

#### StudentLoginView - Avant
```python
POST /api/students/login/
{
    "ine": "1234567890A",
    "last_name": "DUPONT"
}
```

#### StudentLoginView - Après
```python
POST /api/students/login/
{
    "last_name": "DUPONT",
    "first_name": "Jean",
    "date_naissance": "2005-03-15"  # Format: YYYY-MM-DD ou DD/MM/YYYY
}
```

**Formats de date acceptés**:
- `YYYY-MM-DD` (ISO standard, recommandé)
- `DD/MM/YYYY` (format français)

---

### 3. Import CSV (`students/views.py - StudentImportView`)

#### Format CSV - Avant
```csv
INE,Nom,Prenom,Classe
1234567890A,DUPONT,Jean,TS1
9876543210B,MARTIN,Sophie,TS2
```

#### Format CSV - Après
```csv
Élèves,Né(e) le,Adresse E-mail,Classe,Groupe
ABID YOUCEF,01/02/2008,youcef.abid-e@ert.tn,T.01,G3
ABOUDA AMINE,10/07/2008,amine.abouda-e@ert.tn,T.02,G2
```

**Structure des colonnes**:
1. **Élèves** - Format: "NOM PRENOM" (le nom en majuscules, prénom capitalisé)
2. **Né(e) le** - Format: DD/MM/YYYY
3. **Adresse E-mail** - Email de l'élève
4. **Classe** - Ex: T.01, T.02, T.10
5. **Groupe** - Ex: G1, G2, G3, T.06

**Parsing automatique**:
- Le premier mot est considéré comme le **nom** (converti en majuscules)
- Le reste est le **prénom** (première lettre en majuscule)
- Exemple: "ABID YOUCEF" → last_name="ABID", first_name="Youcef"

**Validation**:
- ✅ Format de date vérifié (DD/MM/YYYY)
- ✅ Nom et prénom obligatoires
- ✅ Détection automatique de l'en-tête
- ✅ Rapports d'erreurs détaillés par ligne

---

### 4. Migration Base de Données

**Fichier**: `students/migrations/0003_remove_ine_add_date_naissance.py`

**Étapes de migration**:
1. Ajout de `date_naissance` (temporairement nullable)
2. Ajout de `groupe`
3. Suppression du champ `ine`
4. `date_naissance` devient obligatoire (NOT NULL)
5. Ajout de la contrainte `unique_together` sur (last_name, first_name, date_naissance)
6. Ajout d'index pour performance

**⚠️ ATTENTION**: Si vous avez des données existantes:
```bash
# Option 1: Supprimer les anciennes données (développement uniquement)
python manage.py migrate students zero
python manage.py migrate students

# Option 2: Peupler manuellement date_naissance avant migration
# (voir scripts/seed_*.py pour exemples)
```

---

### 5. Serializer (`students/serializers.py`)

#### Avant
```python
fields = ['id', 'ine', 'first_name', 'last_name', 'class_name', 'email']
```

#### Après
```python
fields = ['id', 'first_name', 'last_name', 'date_naissance', 'email', 'class_name', 'groupe']
```

---

### 6. Interface Admin Django (`students/admin.py`)

#### Avant
```python
list_display = ('ine', 'last_name', 'first_name', 'class_name', 'email')
search_fields = ('ine', 'last_name', 'first_name', 'email')
```

#### Après
```python
list_display = ('last_name', 'first_name', 'date_naissance', 'class_name', 'groupe', 'email')
search_fields = ('last_name', 'first_name', 'email')
list_filter = ('class_name', 'groupe')
date_hierarchy = 'date_naissance'
```

---

## 🔄 Migration des Scripts de Seed

### Exemple de mise à jour

#### Avant
```python
student = Student.objects.create(
    ine="1234567890A",
    last_name="DUPONT",
    first_name="Jean",
    class_name="TS1"
)
```

#### Après
```python
from datetime import date

student = Student.objects.create(
    last_name="DUPONT",
    first_name="Jean",
    date_naissance=date(2005, 3, 15),
    class_name="TS1",
    groupe="G2",
    email="jean.dupont@example.com"
)
```

### Scripts à mettre à jour

Les scripts suivants contiennent des références à `ine` et doivent être mis à jour:

| Fichier | Priorité | Occurrences |
|---------|----------|-------------|
| `scripts/seed_gate4.py` | 🔴 HAUTE | 7 |
| `scripts/seed_e2e.py` | 🔴 HAUTE | 5 |
| `seed_prod.py` | 🟡 MOYENNE | 3 |
| `students/services/csv_import.py` | 🟡 MOYENNE | 3 |
| `identification/test_*.py` | 🟢 BASSE | 3 chacun |
| `scripts/creation_profils_test.py` | 🟢 BASSE | 3 |

**Note**: Les fichiers de test et seed nécessitent une mise à jour manuelle ou peuvent être laissés en l'état s'ils ne sont plus utilisés.

---

## 🧪 Tests

### Test mis à jour

**Fichier**: `students/tests/test_gate4_flow.py`

#### Avant
```python
self.student = Student.objects.create(
    ine="123456789",
    last_name="E2E_STUDENT",
    first_name="Jean"
)

# Login
self.client.post("/api/students/login/", {
    "ine": "123456789",
    "last_name": "E2E_STUDENT"
})
```

#### Après
```python
self.student = Student.objects.create(
    last_name="E2E_STUDENT",
    first_name="Jean",
    date_naissance=date(2005, 3, 15),
    class_name="TS1"
)

# Login
self.client.post("/api/students/login/", {
    "last_name": "E2E_STUDENT",
    "first_name": "Jean",
    "date_naissance": "2005-03-15"
})
```

---

## 📊 Exemple de Fichier CSV Réel

Basé sur l'image fournie, voici le format exact:

```csv
Élèves,Né(e) le,Adresse E-mail,Classe,Groupe
ABID YOUCEF,01/02/2008,youcef.abid-e@ert.tn,T.01,G3
ABOUDA AMINE,10/07/2008,amine.abouda-e@ert.tn,T.02,G2
KERBEJ SANDRA-INES,21/10/2008,sandraines.kerbej-e@ert.tn,T.01,G3
ALBANESE ALEXANDRE,21/10/2008,alexandre.albanese-e@ert.tn,T.06,T.06
ALLANI MERIEM,20/02/2008,meriem.allani-e@ert.tn,T.06,G3
```

**Cas particuliers gérés**:
- ✅ Noms composés avec tiret (SANDRA-INES)
- ✅ Plusieurs prénoms (SANDRA INES traité comme un seul prénom)
- ✅ Groupes spéciaux (T.06 au lieu de G1/G2/G3)
- ✅ Dates diverses années (2007-2009)

---

## ✅ Checklist de Migration

### Pour les Développeurs

- [x] Modifier `students/models.py`
- [x] Créer migration `0003_remove_ine_add_date_naissance.py`
- [x] Modifier `students/serializers.py`
- [x] Modifier `students/views.py` (StudentImportView)
- [x] Modifier `students/views.py` (StudentLoginView)
- [x] Modifier `students/admin.py`
- [x] Mettre à jour tests `students/tests/test_gate4_flow.py`
- [ ] Mettre à jour scripts de seed (si nécessaire)
- [ ] Tester l'import CSV avec données réelles
- [ ] Tester l'authentification élève
- [ ] Vérifier la performance des requêtes (index créé)

### Pour les Administrateurs

- [ ] Backup de la base de données **AVANT** migration
- [ ] Exécuter la migration: `python manage.py migrate students`
- [ ] Tester l'import CSV avec le nouveau format
- [ ] Vérifier que les élèves existants sont accessibles (si données migrées)
- [ ] Mettre à jour la documentation utilisateur

---

## 🚨 Points d'Attention

### 1. Homonymes

Avec la nouvelle clé unique (nom + prénom + date_naissance), deux élèves peuvent avoir le même nom et prénom s'ils sont nés à des dates différentes.

**Exemple valide**:
- Jean DUPONT, né le 15/03/2005
- Jean DUPONT, né le 20/07/2005 ← ✅ Accepté (dates différentes)

### 2. Import CSV - Parsing du Nom

Le parsing "NOM PRENOM" dans la colonne "Élèves" suppose:
- Le **premier mot** est le nom de famille (majuscules)
- Tout le **reste** est le prénom

**Cas particuliers**:
```csv
ALBANESE ALEXANDRE           → last_name="ALBANESE", first_name="Alexandre"
KERBEJ SANDRA-INES          → last_name="KERBEJ", first_name="Sandra-ines"
BEN AHMED MOHAMED ALI       → last_name="BEN", first_name="Ahmed mohamed ali"
```

⚠️ **Problème potentiel**: Si le nom de famille est composé (ex: "BEN AHMED"), seul "BEN" sera considéré comme nom.

**Solution recommandée**: Format CSV avec colonnes séparées:
```csv
Nom,Prénom,Date de naissance,Email,Classe,Groupe
BEN AHMED,Mohamed Ali,15/03/2005,mohamed.benahmed@example.com,TS1,G2
```

### 3. Performance

L'index créé sur `(last_name, first_name, date_naissance)` garantit:
- ✅ Recherches rapides lors du login
- ✅ Validation unique rapide lors de l'import CSV
- ✅ Pas de régression de performance vs INE

**Requête optimisée**:
```python
# Cette requête utilise l'index
Student.objects.filter(
    last_name__iexact="DUPONT",
    first_name__iexact="Jean",
    date_naissance=date(2005, 3, 15)
)
```

---

## 🔗 Endpoints API Mis à Jour

### Login Élève
```http
POST /api/students/login/
Content-Type: application/json

{
    "last_name": "DUPONT",
    "first_name": "Jean",
    "date_naissance": "2005-03-15"
}
```

**Réponse** (200 OK):
```json
{
    "message": "Login successful",
    "role": "Student",
    "student": {
        "id": 123,
        "first_name": "Jean",
        "last_name": "DUPONT",
        "class_name": "TS1"
    }
}
```

### Import CSV
```http
POST /api/students/import/
Content-Type: multipart/form-data

file: <students.csv>
```

**Réponse** (200 OK ou 207 Multi-Status):
```json
{
    "created": 45,
    "updated": 3,
    "errors": [
        {
            "line": 12,
            "error": "Invalid date format: '32/13/2008' (expected DD/MM/YYYY)"
        }
    ]
}
```

---

## 📚 Références

- **Modèle**: `backend/students/models.py`
- **Views**: `backend/students/views.py`
- **Migration**: `backend/students/migrations/0003_remove_ine_add_date_naissance.py`
- **Tests**: `backend/students/tests/test_gate4_flow.py`
- **Format CSV**: Voir image d'exemple fournie

---

## 🤝 Support

Pour toute question ou problème:
1. Vérifier que la migration a été exécutée: `python manage.py showmigrations students`
2. Vérifier les logs lors de l'import CSV
3. Tester avec un fichier CSV minimal (2-3 lignes)

---

**Version**: 1.0  
**Date**: 2026-02-10  
**Auteur**: Équipe Développement
