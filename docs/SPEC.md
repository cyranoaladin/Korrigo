**Cahier des Charges (SPEC.md)**.

Elle intègre les spécificités "Bac Blanc" (absence de QR Code, pédagogie, Pronote) et la séparation stricte des interfaces de connexion demandée.

---

# Projet Korrigo PMF — Cahier des Charges (Révisé v2.0)

**Version :** 2.0 (Adaptation "Bac Blanc")
**Date :** 17 Janvier 2026
**Responsable :** Équipe NSI / Mathématiques (Lycée Pierre Mendès France)
**Contexte :** Plateforme locale de correction dématérialisée pour examens internes, sans infrastructure industrielle (pas de code-barres).

---

## 1. Périmètre et Objectifs

### 1.1. Résumé du besoin

L'application doit permettre la correction numérique de copies d'examens scannées en masse. Elle vise à fluidifier la logistique du "Bac Blanc" au sein du lycée, depuis la numérisation sur les copieurs de l'établissement jusqu'au retour pédagogique vers l'élève.

### 1.2. Contraintes Critiques & Spécificités PMF

1. **Logistique "Sans QR Code" :** Les copies sont des feuilles standard. L'identification ne peut pas être entièrement automatisée. Elle repose sur un processus semi-automatique (OCR + Validation humaine).
2. **Entrée unique "Vrac" :** Le système ingère des PDF massifs (ex: "Scan_Salle_B202.pdf") contenant des centaines de pages mélangées.
3. **Architecture Locale :** Déploiement sur serveur interne ou cloud privé léger (Docker), stockage des fichiers en local (NAS/Volume) ou MinIO.
4. **Double Finalité :**
* **Administrative :** Export des notes vers Pronote.
* **Pédagogique :** L'élève doit pouvoir consulter sa copie corrigée et annotée.



---

## 2. Architecture Technique (La Stack)

### 2.1. Backend (API & Logique)

* **Langage :** Python 3.9
* **Framework :** Django 4.2 LTS (API REST).
* **Traitement d'image & OCR :**
* `opencv-python-headless` : Découpage et détection de structure.
* `pytesseract` ou `EasyOCR` : **[Ajout]** Pour la reconnaissance du Nom/Prénom dans l'en-tête.
* `PyMuPDF` (fitz) : Manipulation PDF.


* **File d'attente :** Celery + Redis.

### 2.2. Base de Données & Stockage

* **SGBD :** PostgreSQL 15+.
* **Stockage Fichiers :** Volume Docker local (monté sur le NAS du lycée) ou MinIO.

### 2.3. Frontend (Interface Utilisateur)

* **Framework :** Vue.js 3 + Pinia.
* **Architecture UI :** Séparation stricte des portails (Admin vs Correcteur vs Élève).

---

## 3. Workflow Fonctionnel Détaillé

### Phase 1 : Ingestion et Identification (Le "Video-Coding") - *Rôle Admin / Secrétariat*

Cette phase remplace l'automatisation par QR Code.

1. **Ingestion :** Upload du PDF de masse.
2. **Découpage (Splitter) :** Analyse visuelle pour séparer les copies (détection de la page de garde "En-tête PMF").
3. **L'Atelier d'Identification (Nouveau Module) :**
* L'interface présente à l'opérateur le zoom sur l'en-tête de la copie.
* **OCR Assisté :** Le système lit "DUPONT" et propose les élèves correspondants depuis la base Pronote (ex: "Jean Dupont - TG2").
* **Validation :** L'opérateur clique pour lier la copie physique à l'identité numérique de l'élève.
* *Cas d'erreur :* Possibilité d'agrafage manuel si une page a été détachée.



### Phase 2 : Anonymisation et Distribution - *Rôle Admin*

1. **Anonymisation :** Une fois identifiée, la copie reçoit un `anonymous_id`. L'en-tête (Nom) est masqué numériquement par un bandeau blanc pour les correcteurs.
2. **Brassage :** Les copies sont mélangées (sauf si le prof demande à corriger sa propre classe).
3. **Attribution :** Assignation aux correcteurs.

### Phase 3 : Correction - *Rôle Enseignant*

* **Accès :** Via page de connexion dédiée (voir section 5).
* **Interface :** (Identique à la v1.0) PDF à gauche, Barème interactif à droite.
* **Outils :** Stylo rouge vectoriel, Tampons, Texte LaTeX.

### Phase 4 : Restitution et Export

1. **Calculs :** Moyennes par question (pour analyse pédagogique).
2. **Aplatissement (Flattening) :** Génération des PDF finaux avec incrustation des notes et ré-affichage du nom de l'élève.
3. **Interopérabilité Pronote :** Export CSV au format `INE;MATIERE;NOTE;COEFF`.
4. **Accès Élève (Nouveau) :** Activation du portail élève pour consultation en lecture seule.

---

## 4. Modèle de Données (Mise à jour)

```python
class Student(models.Model):
    ine = CharField(unique=True) # Identifiant National ou Pronote
    first_name = CharField()
    last_name = CharField()
    class_name = CharField() # Ex: "Tle G4"
    email = EmailField()

class Copy(models.Model):
    exam = ForeignKey(Exam)
    student = ForeignKey(Student, null=True) # Lié lors de la phase "Identification"
    anonymous_id = CharField()
    
    # Workflow
    is_identified = BooleanField(default=False) # Validé par le secrétariat ?
    status = Enum('INGESTED', 'IDENTIFIED', 'READY', 'GRADED')
    
    # Fichiers
    raw_scan = FileField() # Scan original
    final_pdf = FileField() # Copie corrigée aplatie

```

---

## 5. Interface & UX (Ségrégation des Accès)

Pour des raisons de sécurité et d'ergonomie, les points d'entrée sont distincts.

### 5.1. Portail Administration (`/admin-login`)

* **Cible :** Proviseur adjoint, Secrétariat, Super-Admin NSI.
* **Design :** Sobre, dense, orienté gestion de listes.
* **Fonctions :**
* Import Base Élèves (CSV Pronote).
* Upload Scans.
* **Atelier d'Identification (Interface rapide clavier/souris).**
* Export Notes.



### 5.2. Portail Correcteurs (`/prof-login`)

* **Cible :** Professeurs correcteurs.
* **Design :** Épuré, focus sur la tâche de lecture, "Mode Zen".
* **Dashboard :**
* "Mes copies à corriger" (Jauge d'avancement).
* "Mes statistiques" (Moyenne de mon lot vs Moyenne nationale).


* **Authentification :** Peut utiliser le LDAP du lycée ou comptes locaux simplifiés.

### 5.3. Portail Élèves (`/student-access`)

* **Cible :** Élèves (Post-correction).
* **Fonctions :**
* Connexion via INE + Date de naissance (ou lien email).
* Visualisation de la copie.
* Téléchargement PDF.



---

## 6. Structure du Projet (Mise à jour Arborescence)

```text
korrigo-pmf/
├── backend/
│   ├── exams/              # Gestion administrative
│   ├── identification/     # [NOUVEAU] Module OCR & Liaison Élèves
│   ├── grading/            # Correction
│   └── students/           # [NOUVEAU] Gestion base élèves & Portail
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── admin/      # Vues Admin
│   │   │   │   ├── LoginAdmin.vue
│   │   │   │   ├── IdentificationDesk.vue  # Video-coding
│   │   │   ├── teacher/    # Vues Prof
│   │   │   │   ├── LoginTeacher.vue
│   │   │   │   ├── CorrectorDesk.vue
│   │   │   └── student/    # Vues Élève
│   │   │       ├── LoginStudent.vue
│   │   │       ├── ResultView.vue

```

---

## 7. Roadmap Révisée

1. **Semaine 1 : Socle & Données**
* Modèles Django (dont `Student`).
* Script d'import CSV Pronote.
* Mise en place des 3 pages de login distinctes.


2. **Semaine 2 : Ingestion & Identification (Cœur du "Sans QR")**
* Splitter PDF.
* Intégration Tesseract/EasyOCR.
* Interface "Identification Desk" (Autocomplete nom élève).


3. **Semaine 3 : Correction & Barème**
* Canvas vectoriel.
* Calcul des notes.


4. **Semaine 4 : Restitution**
* Génération PDF final.
* Export Pronote.
* Ouverture accès élèves.Voici la version révisée et enrichie du **Cahier des Charges (SPEC.md)**.

Elle intègre les spécificités "Bac Blanc" (absence de QR Code, pédagogie, Pronote) et la séparation stricte des interfaces de connexion demandée.

---

# Projet Korrigo PMF — Cahier des Charges (Révisé v2.0)

**Version :** 2.0 (Adaptation "Bac Blanc")
**Date :** 17 Janvier 2026
**Responsable :** Équipe NSI / Mathématiques (Lycée Pierre Mendès France)
**Contexte :** Plateforme locale de correction dématérialisée pour examens internes, sans infrastructure industrielle (pas de code-barres).

---

## 1. Périmètre et Objectifs

### 1.1. Résumé du besoin

L'application doit permettre la correction numérique de copies d'examens scannées en masse. Elle vise à fluidifier la logistique du "Bac Blanc" au sein du lycée, depuis la numérisation sur les copieurs de l'établissement jusqu'au retour pédagogique vers l'élève.

### 1.2. Contraintes Critiques & Spécificités PMF

1. **Logistique "Sans QR Code" :** Les copies sont des feuilles standard. L'identification ne peut pas être entièrement automatisée. Elle repose sur un processus semi-automatique (OCR + Validation humaine).
2. **Entrée unique "Vrac" :** Le système ingère des PDF massifs (ex: "Scan_Salle_B202.pdf") contenant des centaines de pages mélangées.
3. **Architecture Locale :** Déploiement sur serveur interne ou cloud privé léger (Docker), stockage des fichiers en local (NAS/Volume) ou MinIO.
4. **Double Finalité :**
* **Administrative :** Export des notes vers Pronote.
* **Pédagogique :** L'élève doit pouvoir consulter sa copie corrigée et annotée.



---

## 2. Architecture Technique (La Stack)

### 2.1. Backend (API & Logique)

* **Langage :** Python 3.9
* **Framework :** Django 4.2 LTS (API REST).
* **Traitement d'image & OCR :**
* `opencv-python-headless` : Découpage et détection de structure.
* `pytesseract` ou `EasyOCR` : **[Ajout]** Pour la reconnaissance du Nom/Prénom dans l'en-tête.
* `PyMuPDF` (fitz) : Manipulation PDF.


* **File d'attente :** Celery + Redis.

### 2.2. Base de Données & Stockage

* **SGBD :** PostgreSQL 15+.
* **Stockage Fichiers :** Volume Docker local (monté sur le NAS du lycée) ou MinIO.

### 2.3. Frontend (Interface Utilisateur)

* **Framework :** Vue.js 3 + Pinia.
* **Architecture UI :** Séparation stricte des portails (Admin vs Correcteur vs Élève).

---

## 3. Workflow Fonctionnel Détaillé

### Phase 1 : Ingestion et Identification (Le "Video-Coding") - *Rôle Admin / Secrétariat*

Cette phase remplace l'automatisation par QR Code.

1. **Ingestion :** Upload du PDF de masse.
2. **Découpage (Splitter) :** Analyse visuelle pour séparer les copies (détection de la page de garde "En-tête PMF").
3. **L'Atelier d'Identification (Nouveau Module) :**
* L'interface présente à l'opérateur le zoom sur l'en-tête de la copie.
* **OCR Assisté :** Le système lit "DUPONT" et propose les élèves correspondants depuis la base Pronote (ex: "Jean Dupont - TG2").
* **Validation :** L'opérateur clique pour lier la copie physique à l'identité numérique de l'élève.
* *Cas d'erreur :* Possibilité d'agrafage manuel si une page a été détachée.



### Phase 2 : Anonymisation et Distribution - *Rôle Admin*

1. **Anonymisation :** Une fois identifiée, la copie reçoit un `anonymous_id`. L'en-tête (Nom) est masqué numériquement par un bandeau blanc pour les correcteurs.
2. **Brassage :** Les copies sont mélangées (sauf si le prof demande à corriger sa propre classe).
3. **Attribution :** Assignation aux correcteurs.

### Phase 3 : Correction - *Rôle Enseignant*

* **Accès :** Via page de connexion dédiée (voir section 5).
* **Interface :** (Identique à la v1.0) PDF à gauche, Barème interactif à droite.
* **Outils :** Stylo rouge vectoriel, Tampons, Texte LaTeX.

### Phase 4 : Restitution et Export

1. **Calculs :** Moyennes par question (pour analyse pédagogique).
2. **Aplatissement (Flattening) :** Génération des PDF finaux avec incrustation des notes et ré-affichage du nom de l'élève.
3. **Interopérabilité Pronote :** Export CSV au format `INE;MATIERE;NOTE;COEFF`.
4. **Accès Élève (Nouveau) :** Activation du portail élève pour consultation en lecture seule.

---

## 4. Modèle de Données (Mise à jour)

```python
class Student(models.Model):
    ine = CharField(unique=True) # Identifiant National ou Pronote
    first_name = CharField()
    last_name = CharField()
    class_name = CharField() # Ex: "Tle G4"
    email = EmailField()

class Copy(models.Model):
    exam = ForeignKey(Exam)
    student = ForeignKey(Student, null=True) # Lié lors de la phase "Identification"
    anonymous_id = CharField()
    
    # Workflow
    is_identified = BooleanField(default=False) # Validé par le secrétariat ?
    status = Enum('INGESTED', 'IDENTIFIED', 'READY', 'GRADED')
    
    # Fichiers
    raw_scan = FileField() # Scan original
    final_pdf = FileField() # Copie corrigée aplatie

```

---

## 5. Interface & UX (Ségrégation des Accès)

Pour des raisons de sécurité et d'ergonomie, les points d'entrée sont distincts.

### 5.1. Portail Administration (`/admin-login`)

* **Cible :** Proviseur adjoint, Secrétariat, Super-Admin NSI.
* **Design :** Sobre, dense, orienté gestion de listes.
* **Fonctions :**
* Import Base Élèves (CSV Pronote).
* Upload Scans.
* **Atelier d'Identification (Interface rapide clavier/souris).**
* Export Notes.



### 5.2. Portail Correcteurs (`/prof-login`)

* **Cible :** Professeurs correcteurs.
* **Design :** Épuré, focus sur la tâche de lecture, "Mode Zen".
* **Dashboard :**
* "Mes copies à corriger" (Jauge d'avancement).
* "Mes statistiques" (Moyenne de mon lot vs Moyenne nationale).


* **Authentification :** Peut utiliser le LDAP du lycée ou comptes locaux simplifiés.

### 5.3. Portail Élèves (`/student-access`)

* **Cible :** Élèves (Post-correction).
* **Fonctions :**
* Connexion via INE + Date de naissance (ou lien email).
* Visualisation de la copie.
* Téléchargement PDF.



---

## 6. Structure du Projet (Mise à jour Arborescence)

```text
korrigo-pmf/
├── backend/
│   ├── exams/              # Gestion administrative
│   ├── identification/     # [NOUVEAU] Module OCR & Liaison Élèves
│   ├── grading/            # Correction
│   └── students/           # [NOUVEAU] Gestion base élèves & Portail
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── admin/      # Vues Admin
│   │   │   │   ├── LoginAdmin.vue
│   │   │   │   ├── IdentificationDesk.vue  # Video-coding
│   │   │   ├── teacher/    # Vues Prof
│   │   │   │   ├── LoginTeacher.vue
│   │   │   │   ├── CorrectorDesk.vue
│   │   │   └── student/    # Vues Élève
│   │   │       ├── LoginStudent.vue
│   │   │       ├── ResultView.vue

```

---

## 7. Roadmap Révisée

1. **Semaine 1 : Socle & Données**
* Modèles Django (dont `Student`).
* Script d'import CSV Pronote.
* Mise en place des 3 pages de login distinctes.


2. **Semaine 2 : Ingestion & Identification (Cœur du "Sans QR")**
* Splitter PDF.
* Intégration Tesseract/EasyOCR.
* Interface "Identification Desk" (Autocomplete nom élève).


3. **Semaine 3 : Correction & Barème**
* Canvas vectoriel.
* Calcul des notes.


4. **Semaine 4 : Restitution**
* Génération PDF final.
* Export Pronote.
* Ouverture accès élèves.
