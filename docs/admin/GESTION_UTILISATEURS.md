# Gestion des Utilisateurs - Korrigo PMF

> **Version**: 1.0.0  
> **Date**: 30 janvier 2026  
> **Public**: Administrateurs, Secrétariat  
> **Langue**: Français

Ce document détaille toutes les procédures de gestion des utilisateurs dans Korrigo PMF : création, modification, désactivation, import en masse et gestion des permissions.

---

## 📋 Table des Matières

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Création de Comptes](#2-création-de-comptes)
3. [Import en Masse](#3-import-en-masse)
4. [Modification et Gestion](#4-modification-et-gestion)
5. [Gestion des Permissions](#5-gestion-des-permissions)
6. [Désactivation et Suppression](#6-désactivation-et-suppression)
7. [Bonnes Pratiques](#7-bonnes-pratiques)
8. [Dépannage](#8-dépannage)

---

## 1. Vue d'Ensemble

### 1.1 Types d'Utilisateurs

Korrigo PMF distingue **trois types d'utilisateurs** principaux :

| Type | Modèle de Données | Authentification | Cas d'Usage |
|------|-------------------|------------------|-------------|
| **Administrateur** | Django User (is_superuser=True) | Username + Password | Proviseur Adjoint, Admin NSI, Secrétariat |
| **Enseignant** | Django User + Group("teacher") | Username + Password | Tous les professeurs correcteurs |
| **Élève** | Student (table dédiée) | INE + Nom de Famille | Tous les élèves de l'établissement |

### 1.2 Cycle de Vie d'un Compte

```
┌──────────────────────────────────────────────────────────┐
│ CRÉATION                                                 │
│ - Manuel (admin) OU Import CSV (élèves)                 │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ ACTIVATION                                               │
│ - Définition mot de passe (enseignants/admins)          │
│ - Compte actif automatiquement (élèves via import)      │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ UTILISATION                                              │
│ - Connexion, actions selon rôle                         │
│ - Modifications (mot de passe, email)                   │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ DÉSACTIVATION (recommandé) OU SUPPRESSION               │
│ - Fin de contrat (enseignant) OU Fin scolarité (élève)  │
│ - Conservation traçabilité (désactivation)              │
│ - Suppression définitive (après délai légal)            │
└──────────────────────────────────────────────────────────┘
```

### 1.3 Permissions et Rôles

#### Matrice de Permissions (Résumé)

| Action | Administrateur | Enseignant | Élève |
|--------|----------------|------------|-------|
| Créer/Modifier Utilisateurs | ✅ | ❌ | ❌ |
| Importer Élèves (CSV) | ✅ | ❌ | ❌ |
| Créer Examens | ✅ | ✅ | ❌ |
| Corriger Copies | ✅ | ✅ | ❌ |
| Voir Toutes les Copies | ✅ | ✅ (de son examen) | ❌ |
| Voir Sa Copie | ❌ | ❌ | ✅ |
| Exporter CSV Pronote | ✅ | ❌ | ❌ |
| Configuration Système | ✅ | ❌ | ❌ |

**Document de Référence Complet** : [SECURITY_PERMISSIONS_INVENTORY.md](../../SECURITY_PERMISSIONS_INVENTORY.md)

---

## 2. Création de Comptes

### 2.1 Créer un Administrateur

**Quand** : Nouvel admin NSI, nouveau proviseur adjoint, nouveau compte secrétariat

**Chemin** : Dashboard → Utilisateurs → [+ Nouvel Utilisateur]

#### Formulaire de Création

| Champ | Description | Exemple | Validation |
|-------|-------------|---------|------------|
| **Username** | Identifiant de connexion unique | `jdupont` | 3-150 caractères, lettres/chiffres/underscore |
| **Email** | Email professionnel | `j.dupont@lycee.fr` | Format email valide |
| **Prénom** | Prénom | `Jean` | 1-100 caractères |
| **Nom** | Nom de famille | `Dupont` | 1-100 caractères |
| **Rôle** | Admin (accès complet) | `Administrateur` | Obligatoire |
| **Mot de Passe** | Mot de passe initial | `LyceeSecure2026!` | Min. 8 caractères |
| **Confirmer MdP** | Confirmation | `LyceeSecure2026!` | Doit correspondre |
| **Compte Actif** | Activer immédiatement | ✅ Coché | Par défaut oui |
| **Forcer Changement MdP** | Forcer changement à la 1ère connexion | ✅ Recommandé | Sécurité |

#### Procédure Complète

1. **Remplir le Formulaire** :
   - Username : Préférer format `prenom.nom` (ex: `jean.dupont`)
   - Email : Utiliser l'email professionnel du lycée
   - Mot de passe : Générer un mot de passe fort (12+ caractères, lettres + chiffres + symboles)

2. **Définir le Rôle** :
   - Sélectionner **"Administrateur"** dans le menu déroulant
   - Cocher **"Staff Status"** (accès à l'interface admin Django)
   - Cocher **"Superuser Status"** (permissions complètes)

3. **Options de Sécurité** :
   - ✅ Cocher **"Forcer changement de mot de passe"**
   - ✅ Cocher **"Compte actif"**

4. **Validation** :
   - Cliquer sur [Créer]
   - **Résultat** : `✅ Utilisateur jean.dupont créé avec succès`

5. **Communication des Identifiants** :
   - **Email Automatique** (si SMTP configuré) : Envoi automatique des identifiants
   - **Email Manuel** : Copier-coller le modèle ci-dessous et envoyer de façon sécurisée

**Modèle d'Email** :
```
Objet: Création de votre compte Korrigo PMF

Bonjour Jean Dupont,

Votre compte administrateur Korrigo PMF a été créé.

Identifiant : jean.dupont
Mot de passe temporaire : LyceeSecure2026!

Accès : https://korrigo.lycee-exemple.fr

À votre première connexion, vous devrez changer ce mot de passe.

Cordialement,
L'équipe administrative
```

#### Recommandations de Sécurité

- **Mot de Passe Initial** : Minimum 12 caractères avec lettres majuscules, minuscules, chiffres et symboles
- **Transmission** : Envoyer par email sécurisé (ou remettre en main propre)
- **Changement Obligatoire** : Toujours forcer le changement à la première connexion
- **Principe du Moindre Privilège** : Ne créer un admin que si nécessaire (privilégier le rôle enseignant sinon)

### 2.2 Créer un Enseignant

**Quand** : Nouveau professeur, enseignant contractuel

**Procédure** : Identique à [2.1 Créer un Administrateur](#21-créer-un-administrateur), avec les différences suivantes :

| Champ | Valeur Enseignant | Différence vs Admin |
|-------|-------------------|---------------------|
| **Rôle** | `Enseignant` | Sélectionner "Enseignant" |
| **Staff Status** | ❌ Décoché | Pas d'accès admin Django |
| **Superuser Status** | ❌ Décoché | Permissions limitées |
| **Groupe** | `teacher` | Auto-assigné par Korrigo |

#### Permissions Enseignant

Un enseignant peut :
- ✅ Se connecter à Korrigo
- ✅ Créer des examens
- ✅ Voir tous les examens
- ✅ Corriger les copies
- ✅ Finaliser les copies
- ❌ Gérer les utilisateurs
- ❌ Modifier la configuration système
- ❌ Exporter CSV Pronote
- ❌ Accéder aux logs d'audit

### 2.3 Créer un Élève (Méthode Manuelle)

⚠️ **Note** : La création manuelle d'élèves est **déconseillée**. Privilégier l'import CSV depuis Pronote (voir [Section 3](#3-import-en-masse)).

**Quand** : Élève arrivé en cours d'année, cas exceptionnel

**Chemin** : Dashboard → Étudiants → [+ Nouvel Étudiant]

#### Formulaire de Création

| Champ | Description | Exemple | Validation |
|-------|-------------|---------|------------|
| **INE** | Identifiant National Élève | `12345678901` | 11 caractères, alphanumérique |
| **Nom** | Nom de famille | `DUPONT` | 1-100 caractères |
| **Prénom** | Prénom | `Jean` | 1-100 caractères |
| **Classe** | Code classe | `TG2` | Format libre (ex: TG2, 1ES3) |
| **Email** | Email élève (optionnel) | `jean.dupont@exemple.fr` | Format email valide |

#### Procédure

1. Remplir le formulaire
2. **Vérifier l'INE** : 11 caractères exacts (disponible dans Pronote ou dossier élève)
3. Cliquer sur [Créer]
4. **Résultat** : `✅ Élève Jean DUPONT (TG2) créé`

#### Authentification Élève

Les élèves se connectent avec :
- **Identifiant** : INE (11 caractères)
- **Mot de Passe** : Nom de famille (sensible à la casse)

**Exemple** :
- INE : `12345678901`
- Mot de Passe : `DUPONT`

⚠️ **Sécurité** : Ce mode d'authentification est simple mais peu sécurisé. Pour une sécurité renforcée, envisager l'ajout d'un mot de passe personnalisé (fonctionnalité future).

---

## 3. Import en Masse

### 3.1 Prérequis

#### Export depuis Pronote

**Pronote** → **Ressources** → **Élèves** → **Exporter** → **Format CSV**

**Colonnes à Inclure** :
- ✅ INE (obligatoire)
- ✅ Nom (obligatoire)
- ✅ Prénom (obligatoire)
- ✅ Classe (obligatoire)
- ✅ Email (optionnel mais recommandé)

**Paramètres d'Export Pronote** :
- Séparateur : `,` (virgule) ou `;` (point-virgule)
- Encodage : **UTF-8** (recommandé) ou **ISO-8859-1**
- Guillemets : Oui (si noms contiennent des virgules)

#### Exemple de Fichier CSV

**Fichier `eleves_TG_2026.csv`** :
```csv
INE,Nom,Prénom,Classe,Email
12345678901,DUPONT,Jean,TG2,jean.dupont@exemple.fr
12345678902,MARTIN,Sophie,TG2,sophie.martin@exemple.fr
12345678903,DURAND,Pierre,TG4,pierre.durand@exemple.fr
12345678904,BERNARD,Marie,TG4,marie.bernard@exemple.fr
```

**Vérifications Avant Import** :
- ✅ Première ligne contient les **noms de colonnes** (headers)
- ✅ Chaque ligne correspond à **un élève**
- ✅ INE : **Exactement 11 caractères** (ajouter des zéros si nécessaire)
- ✅ Pas de lignes vides
- ✅ Encodage UTF-8 (évite les problèmes d'accents)

### 3.2 Procédure d'Import

**Chemin** : Dashboard → Étudiants → [Importer CSV]

#### Étape 1 : Upload du Fichier

1. Cliquer sur [Parcourir] ou **glisser-déposer** le fichier CSV
2. **Contraintes** :
   - Format : `.csv` uniquement
   - Taille max : 10 Mo
   - Lignes max : 5 000 élèves

3. Sélectionner le fichier `eleves_TG_2026.csv`
4. Cliquer sur [Suivant]

#### Étape 2 : Mapping des Colonnes

Korrigo détecte automatiquement les colonnes, mais vous pouvez vérifier/ajuster :

```
┌─────────────────────────────────────────────────────┐
│ Mapping des Colonnes                                │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Colonne CSV         →    Champ Korrigo             │
│ ─────────────────        ──────────────             │
│ INE                 →    [INE ▼]                    │
│ Nom                 →    [Nom ▼]                    │
│ Prénom              →    [Prénom ▼]                 │
│ Classe              →    [Classe ▼]                 │
│ Email               →    [Email ▼]                  │
│                                                     │
│ [Précédent]  [Aperçu]  [Importer]                  │
└─────────────────────────────────────────────────────┘
```

**Actions** :
- Si mapping incorrect : Ajuster via le menu déroulant
- Cliquer sur [Aperçu] pour voir les 10 premières lignes

#### Étape 3 : Aperçu et Validation

```
┌──────────────────────────────────────────────────────────┐
│ Aperçu (10 premières lignes)                             │
├──────────────────────────────────────────────────────────┤
│ INE         │ Nom     │ Prénom  │ Classe │ Email          │
│─────────────┼─────────┼─────────┼────────┼────────────────│
│ 12345678901 │ DUPONT  │ Jean    │ TG2    │ jean.dupont... │
│ 12345678902 │ MARTIN  │ Sophie  │ TG2    │ sophie.mar...  │
│ 12345678903 │ DURAND  │ Pierre  │ TG4    │ pierre.dur...  │
│ ...         │ ...     │ ...     │ ...    │ ...            │
│                                                          │
│ Validation:                                              │
│ ✅ 650 lignes détectées                                  │
│ ✅ Format INE correct (650/650)                          │
│ ⚠️ 3 doublons INE détectés                               │
│ ⚠️ 5 emails invalides (seront ignorés)                   │
│                                                          │
│ [Précédent]  [Importer]                                  │
└──────────────────────────────────────────────────────────┘
```

**Validations Automatiques** :
- ✅ INE unique (pas de doublon dans le fichier)
- ✅ INE = 11 caractères
- ✅ Nom et Prénom non vides
- ✅ Format email valide (si fourni)

**Warnings (non bloquants)** :
- ⚠️ Doublons INE (ligne ignorée, l'élève existant sera conservé)
- ⚠️ Emails invalides (importation quand même, email vide)

#### Étape 4 : Import

1. Vérifier l'aperçu
2. Cliquer sur [Importer]
3. **Barre de Progression** :
   ```
   Import en cours...
   [████████████████████░░░░░░░░] 75% (487/650)
   ```

4. **Résultat** :
   ```
   ✅ Import Terminé

   Statistiques:
   - 647 élèves importés avec succès
   - 3 doublons ignorés (INE déjà existant)
   - 5 emails invalides (champ email laissé vide)

   [Télécharger Rapport Détaillé (CSV)]
   [Retour à la Liste des Élèves]
   ```

#### Étape 5 : Vérification Post-Import

1. Dashboard → Étudiants → [Liste]
2. **Filtrer par Classe** : Sélectionner `TG2`
3. **Vérifier** :
   - Nombre d'élèves correct
   - INE corrects
   - Pas de noms tronqués

### 3.3 Gestion des Erreurs d'Import

#### Doublons INE

**Symptôme** : `⚠️ 3 doublons ignorés`

**Cause** : L'INE existe déjà en base de données

**Résolution** :
1. Télécharger le **Rapport Détaillé**
2. Identifier les INE en doublon :
   ```csv
   Ligne,INE,Nom,Prénom,Statut,Erreur
   45,12345678901,DUPONT,Jean,IGNORÉ,Doublon INE
   ```
3. **Options** :
   - **Mise à Jour Manuelle** : Dashboard → Étudiants → [Rechercher INE] → [Modifier]
   - **Réimport** : Supprimer l'ancien élève (si erreur de saisie) puis réimporter

#### INE Invalide

**Symptôme** : `❌ 2 erreurs (INE invalide)`

**Cause** : INE ≠ 11 caractères (ex: `123456789` ou `123456789012`)

**Résolution** :
1. Télécharger le **Rapport Détaillé**
2. Corriger les INE dans le fichier CSV source (Pronote)
3. **Vérifier** : L'INE doit faire **exactement 11 caractères**
   - Si INE court : Ajouter des zéros devant (ex: `00123456789`)
4. Réimporter uniquement les lignes en erreur

#### Emails Invalides

**Symptôme** : `⚠️ 5 emails invalides`

**Cause** : Format email incorrect (ex: `jean.dupont@`, `jean.dupont`, `@exemple.fr`)

**Résolution** :
- **Impact Faible** : L'élève est importé, seul l'email est vide
- **Correction Post-Import** : Dashboard → Étudiants → [Élève] → [Modifier] → Ajouter email

### 3.4 Mise à Jour des Élèves (Import Incrémental)

**Quand** : Nouvel élève en cours d'année, changement de classe

**Procédure** :
1. Exporter **uniquement les nouveaux élèves** depuis Pronote
2. Créer un fichier CSV avec les nouveaux élèves :
   ```csv
   INE,Nom,Prénom,Classe,Email
   99988877766,NOUVEAU,Élève,TG2,eleve.nouveau@exemple.fr
   ```
3. Importer via la même procédure (section 3.2)
4. **Comportement** :
   - Si INE existe : Ligne ignorée (aucune modification)
   - Si INE nouveau : Élève créé

**Mise à Jour d'Élèves Existants** :
- L'import CSV **ne met PAS à jour** les élèves existants
- Pour modifier : Utiliser l'interface manuelle (Dashboard → Étudiants → [Modifier])

---

## 4. Modification et Gestion

### 4.1 Modifier un Utilisateur (Admin/Enseignant)

**Chemin** : Dashboard → Utilisateurs → [Cliquer sur l'utilisateur] → [Modifier]

#### Champs Modifiables

| Champ | Modifiable | Restrictions |
|-------|------------|--------------|
| **Username** | ✅ | Doit rester unique |
| **Email** | ✅ | Format valide |
| **Prénom / Nom** | ✅ | - |
| **Rôle** | ✅ | Admin ↔ Enseignant |
| **Compte Actif** | ✅ | Désactiver sans supprimer |
| **Mot de Passe** | ✅ | Via bouton dédié |

#### Procédure de Modification

1. Rechercher l'utilisateur (barre de recherche ou liste)
2. Cliquer sur l'utilisateur
3. Modifier les champs souhaités
4. Cliquer sur [Sauvegarder]
5. **Résultat** : `✅ Utilisateur mis à jour`

### 4.2 Réinitialiser un Mot de Passe

**Quand** : Utilisateur a oublié son mot de passe, compte compromis

**Chemin** : Dashboard → Utilisateurs → [Utilisateur] → [Réinitialiser Mot de Passe]

#### Méthodes

**Méthode 1 : Génération Automatique** (Recommandée)
1. Cliquer sur [Générer Automatiquement]
2. Korrigo génère un mot de passe sécurisé (ex: `Kx9@pL2#qR5$`)
3. **Copier** le mot de passe affiché
4. Envoyer à l'utilisateur (email sécurisé ou en main propre)
5. Cocher **"Forcer changement de mot de passe"** (recommandé)

**Méthode 2 : Définir Manuellement**
1. Cliquer sur [Définir Manuellement]
2. Saisir un mot de passe temporaire (ex: `LyceeTemp2026!`)
3. Confirmer
4. **Copier** le mot de passe
5. Envoyer à l'utilisateur
6. Cocher **"Forcer changement de mot de passe"**

**Modèle d'Email** :
```
Objet: Réinitialisation de votre mot de passe Korrigo PMF

Bonjour Jean Dupont,

Votre mot de passe Korrigo PMF a été réinitialisé.

Identifiant : jean.dupont
Nouveau mot de passe temporaire : Kx9@pL2#qR5$

Accès : https://korrigo.lycee-exemple.fr

Vous devrez changer ce mot de passe à votre prochaine connexion.

Cordialement,
Support Korrigo PMF
```

### 4.3 Modifier un Élève

**Chemin** : Dashboard → Étudiants → [Rechercher élève] → [Modifier]

#### Champs Modifiables

| Champ | Modifiable | Cas d'Usage |
|-------|------------|-------------|
| **INE** | ⚠️ Déconseillé | Uniquement si erreur de saisie |
| **Nom** | ✅ | Changement de nom (mariage, adoption) |
| **Prénom** | ✅ | Correction orthographe |
| **Classe** | ✅ | Changement de classe en cours d'année |
| **Email** | ✅ | Mise à jour email |

**Procédure** :
1. Rechercher l'élève (par nom, INE ou classe)
2. Cliquer sur [Modifier]
3. Modifier les champs
4. [Sauvegarder]

⚠️ **Attention INE** : Modifier l'INE peut casser le lien avec les copies déjà corrigées. À éviter sauf erreur grave.

### 4.4 Changer le Rôle d'un Utilisateur

**Cas d'Usage** : Enseignant devient admin NSI, admin devient simple enseignant

**Procédure** :
1. Dashboard → Utilisateurs → [Utilisateur] → [Modifier]
2. **Changer le Rôle** :
   - Sélectionner nouveau rôle dans menu déroulant
   - **Admin → Enseignant** : Décocher "Staff Status" et "Superuser Status"
   - **Enseignant → Admin** : Cocher "Staff Status" et "Superuser Status"
3. Sauvegarder
4. **Effet immédiat** : L'utilisateur obtient/perd les permissions à sa prochaine connexion

**Vérification** :
- Demander à l'utilisateur de se déconnecter/reconnecter
- Vérifier qu'il a bien accès aux fonctionnalités de son nouveau rôle

---

## 5. Gestion des Permissions

### 5.1 Groupes Django

Korrigo utilise les **Groupes Django** pour gérer les permissions :

| Groupe | Utilisateurs | Permissions |
|--------|--------------|-------------|
| **admin** | Administrateurs | Toutes permissions |
| **teacher** | Enseignants | Permissions limitées (correction, examen) |
| *(Aucun)* | Élèves | Accès portail élève uniquement |

**Association Automatique** :
- Lors de la création d'un utilisateur, Korrigo assigne automatiquement le groupe selon le rôle
- **Admin** → Pas de groupe spécifique (is_superuser=True suffit)
- **Enseignant** → Groupe `teacher`

### 5.2 Permissions Détaillées

**Document Complet** : [SECURITY_PERMISSIONS_INVENTORY.md](../../SECURITY_PERMISSIONS_INVENTORY.md)

#### Permissions par Module

**Module Examens** :
| Action | Permission Django | Admin | Enseignant |
|--------|-------------------|-------|------------|
| Créer Examen | `exams.add_exam` | ✅ | ✅ |
| Voir Examen | `exams.view_exam` | ✅ | ✅ |
| Modifier Examen | `exams.change_exam` | ✅ | ✅ (si créateur) |
| Supprimer Examen | `exams.delete_exam` | ✅ | ❌ |
| Uploader PDF | `exams.upload_pdf` | ✅ | ✅ |

**Module Correction** :
| Action | Permission Django | Admin | Enseignant |
|--------|-------------------|-------|------------|
| Verrouiller Copie | `grading.lock_copy` | ✅ | ✅ |
| Créer Annotation | `grading.add_annotation` | ✅ | ✅ |
| Modifier Annotation | `grading.change_annotation` | ✅ | ✅ (si créateur) |
| Supprimer Annotation | `grading.delete_annotation` | ✅ | ✅ (si créateur) |
| Finaliser Copie | `grading.finalize_copy` | ✅ | ✅ |

**Module Utilisateurs** :
| Action | Permission Django | Admin | Enseignant |
|--------|-------------------|-------|------------|
| Créer Utilisateur | `auth.add_user` | ✅ | ❌ |
| Modifier Utilisateur | `auth.change_user` | ✅ | ❌ |
| Supprimer Utilisateur | `auth.delete_user` | ✅ | ❌ |
| Voir Utilisateurs | `auth.view_user` | ✅ | ❌ |

### 5.3 Permissions Personnalisées (Avancé)

Pour des besoins spécifiques (ex: créer un rôle "Correcteur Senior"), il est possible de créer des permissions personnalisées via l'interface Django Admin.

**Prérequis** : Accès admin Django (`is_staff=True`)

**Procédure** :
1. Accéder à l'Admin Django : `https://korrigo.lycee.fr/admin/`
2. **Groupes** → [Ajouter un Groupe]
3. Nom : `correcteur_senior`
4. **Permissions** : Cocher les permissions souhaitées
   - `exams | exam | Can view exam`
   - `grading | annotation | Can add annotation`
   - `grading | annotation | Can change annotation`
   - etc.
5. Sauvegarder
6. **Assigner le Groupe** :
   - Utilisateurs → [Utilisateur] → Groupes → Cocher `correcteur_senior`

⚠️ **Note** : Cette fonctionnalité est avancée et réservée aux administrateurs expérimentés.

---

## 6. Désactivation et Suppression

### 6.1 Désactiver un Compte (Recommandé)

**Avantages** :
- ✅ Conservation de l'historique (traçabilité RGPD)
- ✅ Réactivation possible
- ✅ Pas de rupture de références en base de données

**Quand** :
- Enseignant en congé longue durée
- Fin de contrat temporaire
- Élève déménagement (avant fin d'année scolaire)

**Procédure** :
1. Dashboard → Utilisateurs (ou Étudiants) → [Utilisateur] → [Modifier]
2. **Décocher "Compte actif"**
3. Sauvegarder
4. **Effet** :
   - L'utilisateur ne peut plus se connecter
   - Ses actions passées restent visibles (corrections, annotations)
   - Réactivation possible en recochant "Compte actif"

### 6.2 Supprimer un Compte

⚠️ **Avertissements** :
- **Risque de perte de traçabilité** : Les corrections/annotations restent mais avec mention "Utilisateur supprimé"
- **Irréversible** : Aucune récupération possible
- **Impact RGPD** : Respecter les durées légales de conservation

**Délais de Conservation Recommandés** :
| Type d'Utilisateur | Délai Avant Suppression | Justification |
|--------------------|-------------------------|---------------|
| **Enseignant** | Fin de contrat + 1 an | Conservation traçabilité pédagogique |
| **Élève** | Fin de scolarité + 1 an | Art. L. 131-1 Code de l'Éducation |
| **Administrateur** | Fin de fonction + 1 an | Traçabilité administrative |

#### Procédure de Suppression

**Étape 1 : Vérification**
1. Dashboard → Utilisateurs → [Utilisateur]
2. Vérifier la date de dernière connexion
3. Vérifier qu'aucune copie n'est verrouillée par cet utilisateur

**Étape 2 : Sauvegarde**
1. Exporter les logs d'audit de cet utilisateur :
   - Dashboard → Logs → [Filtrer par utilisateur] → [Exporter CSV]
2. Sauvegarder le CSV (archivage légal)

**Étape 3 : Suppression**
1. Dashboard → Utilisateurs → [Utilisateur] → [Supprimer]
2. **Confirmation** :
   ```
   ⚠️ Supprimer l'utilisateur jean.dupont ?

   Cette action est irréversible.
   Ses corrections resteront visibles avec la mention "Utilisateur supprimé".

   [Annuler] [Confirmer la Suppression]
   ```
3. Cliquer sur [Confirmer la Suppression]
4. **Résultat** : `✅ Utilisateur jean.dupont supprimé`

**Étape 4 : Vérification**
- Les corrections de cet utilisateur affichent `Corrigé par: Utilisateur supprimé`
- Les logs d'audit conservent l'ID utilisateur (traçabilité)

### 6.3 Suppression en Masse (Élèves Sortants)

**Quand** : Fin d'année scolaire, suppression des élèves diplômés/partis

**Procédure Recommandée** :
1. **Exporter Liste** :
   - Dashboard → Étudiants → [Filtrer par classe: "TERMINALE"] → [Exporter CSV]
2. **Attendre Délai Légal** : 1 an après fin de scolarité
3. **Suppression en Masse** :
   - Dashboard → Étudiants → [Sélection Multiple]
   - Cocher les élèves à supprimer
   - [Actions] → [Supprimer les élèves sélectionnés]
   - Confirmer
4. **Archivage** :
   - Sauvegarder le CSV exporté sur NAS (conservation notes 50 ans selon Code de l'Éducation)

**Automatisation** (via Script Django) :
```bash
# Exemple de commande Django management pour purge automatique
docker-compose exec backend python manage.py purge_students --older-than=1year --dry-run
# Vérifier le dry-run, puis exécuter réellement:
docker-compose exec backend python manage.py purge_students --older-than=1year
```

⚠️ **Note** : Cette fonctionnalité nécessite un script personnalisé (non fourni par défaut).

---

## 7. Bonnes Pratiques

### 7.1 Sécurité des Mots de Passe

**Politique de Mot de Passe Recommandée** :
- **Longueur Minimale** : 10 caractères (admin), 8 caractères (enseignants)
- **Complexité** : Majuscules + minuscules + chiffres + symboles
- **Renouvellement** : Tous les 6 mois (admins), annuel (enseignants)
- **Historique** : Ne pas réutiliser les 3 derniers mots de passe

**Outils de Génération** :
- Générateur intégré Korrigo (lors de réinitialisation)
- `openssl rand -base64 12` (ligne de commande)
- Gestionnaires de mots de passe (KeePass, Bitwarden)

### 7.2 Gestion des Départs

**Enseignant qui Part** :
1. **J-30** : Planifier la transition (transfert des examens en cours)
2. **J-7** : Désactiver le compte (après fin des corrections)
3. **J+365** : Supprimer le compte (après délai légal)

**Élève qui Part** :
1. **Fin d'Année** : Désactiver automatiquement tous les élèves de Terminale
2. **Année N+1** : Supprimer les comptes après vérification qu'aucune copie n'est consultée

### 7.3 Audit des Comptes

**Fréquence** : Trimestrielle

**Checklist** :
- [ ] Identifier les comptes inactifs (aucune connexion depuis 6 mois)
- [ ] Vérifier les comptes avec permissions admin (liste minimale)
- [ ] Supprimer les comptes obsolètes (après délai légal)
- [ ] Mettre à jour les emails (départs, changements)
- [ ] Vérifier les groupes d'utilisateurs (cohérence)

**Rapport d'Audit** :
- Dashboard → Utilisateurs → [Exporter CSV] → Analyser avec Excel/LibreOffice
- Colonnes : Username, Email, Rôle, Dernière Connexion, Actif

### 7.4 Communication avec les Utilisateurs

**Email de Bienvenue** :
- Envoyer systématiquement lors de création de compte
- Inclure : Identifiants, URL, instructions première connexion

**Email de Désactivation** :
- Notifier l'utilisateur avant désactivation (courtoisie)
- Expliquer la raison (fin de contrat, inactivité)

**Email de Suppression** :
- Informer de la suppression (RGPD - droit à l'information)
- Fournir coordonnées pour réclamation si besoin

### 7.5 RGPD et Conformité

**Registre des Traitements** :
- Documenter tous les comptes utilisateurs créés
- Finalité : Gestion pédagogique, correction d'examens
- Base légale : Mission d'intérêt public (Code de l'Éducation)

**Exercice des Droits** :
- **Droit d'Accès** : Un utilisateur peut demander toutes ses données (Dashboard → Profil → [Exporter Mes Données])
- **Droit de Rectification** : Modifier via Dashboard → Profil ou demander à l'admin
- **Droit à l'Effacement** : Supprimer le compte après délai légal (voir section 6.2)

**Documentation de Référence** : [Politique RGPD](../security/POLITIQUE_RGPD.md)

---

## 8. Dépannage

### 8.1 Impossible de Créer un Utilisateur

**Symptôme** : `Erreur: Ce nom d'utilisateur existe déjà`

**Cause** : Username déjà utilisé (même pour un compte désactivé)

**Résolution** :
1. Rechercher l'utilisateur existant : Dashboard → Utilisateurs → [Recherche]
2. **Options** :
   - **Réactiver** le compte existant (si même personne)
   - **Renommer** l'ancien compte (ex: `jean.dupont` → `jean.dupont.old`)
   - **Choisir un nouveau username** (ex: `jean.dupont2`)

### 8.2 Import CSV Échoue Complètement

**Symptôme** : `Erreur: Impossible de lire le fichier CSV`

**Causes Possibles** :
1. **Encodage incorrect** (ISO-8859-1 vs UTF-8)
2. **Séparateur incorrect** (`,` vs `;`)
3. **Fichier Excel au lieu de CSV** (`.xlsx` vs `.csv`)

**Résolution** :

**Vérifier l'Encodage** :
```bash
# Sur Linux/Mac
file -I eleves.csv
# Résultat attendu: text/plain; charset=utf-8

# Si charset=iso-8859-1 → Convertir
iconv -f ISO-8859-1 -t UTF-8 eleves.csv > eleves_utf8.csv
```

**Vérifier le Séparateur** :
- Ouvrir le CSV avec un éditeur de texte (Notepad++, Sublime)
- Vérifier : `,` ou `;` ?
- Korrigo détecte automatiquement, mais peut échouer

**Convertir Excel → CSV** :
- Excel → Fichier → Enregistrer Sous → Format: `CSV UTF-8 (délimité par des virgules)`

### 8.3 Élève Ne Peut Pas Se Connecter

**Symptôme** : `Identifiants incorrects` lors de la connexion élève

**Causes Possibles** :
1. INE mal saisi
2. Nom de famille incorrect (sensible à la casse)
3. Compte désactivé

**Résolution** :

**Vérifier l'INE** :
1. Dashboard → Étudiants → [Rechercher par nom]
2. Vérifier l'INE affiché : `12345678901`
3. Demander à l'élève de ressaisir **exactement cet INE**

**Vérifier le Nom** :
- Le nom doit être saisi **en majuscules** : `DUPONT` (et non `Dupont` ou `dupont`)
- Accents : Vérifier la cohérence (`DUPRÉ` vs `DUPRE`)

**Vérifier le Statut** :
- Dashboard → Étudiants → [Élève] → Vérifier **"Compte actif"** ✅

**Réinitialiser** :
- Modifier manuellement le nom si erreur de saisie
- Sauvegarder
- Demander à l'élève de réessayer

### 8.4 Permissions Incohérentes

**Symptôme** : Un enseignant ne peut pas créer d'examen

**Cause** : Groupe `teacher` non assigné

**Résolution** :
1. Dashboard → Utilisateurs → [Enseignant] → [Modifier]
2. **Vérifier le Rôle** : Doit être `Enseignant`
3. **Vérifier le Groupe** (Admin Django) :
   - Admin Django (`/admin/`) → Utilisateurs → [Utilisateur]
   - Groupes : Doit contenir `teacher`
4. Si absent : Cocher `teacher` et sauvegarder
5. Demander à l'utilisateur de se déconnecter/reconnecter

---

## Conclusion

La gestion des utilisateurs dans Korrigo PMF est un processus structuré qui garantit :
- ✅ Sécurité (mots de passe, permissions)
- ✅ Traçabilité (audit, logs)
- ✅ Conformité RGPD (durées de conservation, droits des personnes)

### Documents Complémentaires

- [Guide Utilisateur Admin](./GUIDE_UTILISATEUR_ADMIN.md)
- [Procédures Opérationnelles](./PROCEDURES_OPERATIONNELLES.md)
- [Politique RGPD](../security/POLITIQUE_RGPD.md)
- [Manuel Sécurité](../security/MANUEL_SECURITE.md)
- [FAQ](../support/FAQ.md)

---

**Dernière Mise à Jour** : 30 janvier 2026  
**Version du Document** : 1.0.0
