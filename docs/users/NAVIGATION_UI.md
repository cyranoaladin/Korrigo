# Guide de Navigation UI - Korrigo PMF

> **Version** : 1.0.0  
> **Date** : 30 Janvier 2026  
> **Public** : Tous les utilisateurs (Administrateurs, Enseignants, Élèves)  
> **Type** : Référence Complète de l'Interface Utilisateur

---

## 📋 Table des Matières

1. [Introduction](#introduction)
2. [Architecture de l'Interface](#architecture-de-linterface)
3. [Pages d'Authentification](#pages-dauthentification)
4. [Interface Administrateur](#interface-administrateur)
5. [Interface Enseignant](#interface-enseignant)
6. [Interface Élève](#interface-élève)
7. [Composants Communs](#composants-communs)
8. [Workflows de Navigation](#workflows-de-navigation)
9. [Responsive Design](#responsive-design)
10. [Accessibilité](#accessibilité)

---

## Introduction

### Objectif de ce Document

Ce guide fournit une **référence complète** de toutes les interfaces utilisateur de la plateforme Korrigo PMF. Il décrit :
- Toutes les pages et vues
- Les éléments d'interface
- Les workflows de navigation
- Les composants réutilisables

### Public Cible

| Utilisateur | Usage de ce Guide |
|-------------|-------------------|
| **Administrateurs** | Comprendre toutes les interfaces pour assister les utilisateurs |
| **Enseignants** | Naviguer efficacement dans l'interface de correction |
| **Élèves** | Comprendre le portail de consultation |
| **Support Technique** | Référence pour résoudre les problèmes |
| **Développeurs** | Documentation de l'interface existante |

### Conventions

| Symbole | Signification |
|---------|---------------|
| `[Bouton]` | Bouton cliquable |
| `[Champ___]` | Champ de saisie |
| `📱 Mobile` | Fonctionnalité mobile |
| `🖥️ Desktop` | Fonctionnalité desktop uniquement |
| `⚠️` | Attention / Point important |
| `✅` | Action réussie |
| `❌` | Erreur / Action échouée |

---

## Architecture de l'Interface

### Vue d'Ensemble

Korrigo PMF est une **application web monopage (SPA)** construite avec Vue.js 3. L'interface est divisée en **trois portails distincts** selon le rôle utilisateur :

```
Korrigo PMF
├── Portail Administrateur (Admin + Enseignants)
│   ├── Tableau de bord
│   ├── Gestion des examens
│   ├── Gestion des utilisateurs (Admin uniquement)
│   └── Interface de correction
│
├── Portail Élève
│   ├── Connexion élève
│   ├── Tableau de bord élève
│   └── Visualiseur de copies
│
└── Composants Partagés
    ├── Visualiseur PDF
    ├── Système de notifications
    └── Gestion d'état (Pinia stores)
```

### Stack Technique UI

| Technologie | Version | Usage |
|-------------|---------|-------|
| **Vue.js** | 3.4+ | Framework UI (Composition API) |
| **Vue Router** | 4.2+ | Routing SPA |
| **Pinia** | 2.1+ | State management |
| **TypeScript** | 5.9+ | Typage statique |
| **PDF.js** | 4.0+ | Visualisation PDF |
| **Axios** | 1.13+ | Appels API |

### Routes Principales

| Route | Rôle | Composant | Description |
|-------|------|-----------|-------------|
| `/login` | Public | `LoginView` | Connexion Admin/Teacher |
| `/student/login` | Public | `StudentLoginView` | Connexion Élève |
| `/dashboard` | Admin/Teacher | `DashboardView` | Tableau de bord |
| `/exams` | Admin/Teacher | `ExamsListView` | Liste des examens |
| `/exam/:id` | Admin/Teacher | `ExamDetailView` | Détails d'un examen |
| `/grading/:copyId` | Admin/Teacher | `GradingDeskView` | Interface de correction |
| `/student/dashboard` | Student | `StudentDashboardView` | Tableau de bord élève |
| `/student/copy/:id` | Student | `StudentCopyView` | Consultation copie |

---

## Pages d'Authentification

### Page de Connexion Admin/Teacher

#### URL
```
/login
```

#### Wireframe

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│                    🎓 Korrigo PMF                            │
│                 Plateforme de Correction                     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │                                                    │     │
│  │  Connexion Enseignant / Administrateur            │     │
│  │                                                    │     │
│  │  Nom d'utilisateur :                              │     │
│  │  [___________________________________]            │     │
│  │                                                    │     │
│  │  Mot de passe :                                   │     │
│  │  [___________________________________]  [👁️]      │     │
│  │                                                    │     │
│  │  ☐ Se souvenir de moi                             │     │
│  │                                                    │     │
│  │  [Se connecter]                                   │     │
│  │                                                    │     │
│  │  Mot de passe oublié ? → Contactez l'admin       │     │
│  │                                                    │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  → Vous êtes élève ? [Accéder au portail élève]             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Éléments de l'Interface

| Élément | Type | Validation | Comportement |
|---------|------|------------|--------------|
| **Nom d'utilisateur** | `input[text]` | Obligatoire, max 150 chars | Trim automatique |
| **Mot de passe** | `input[password]` | Obligatoire, min 6 chars | Afficher/masquer avec 👁️ |
| **Se souvenir de moi** | `checkbox` | Optionnel | Cookie de session étendu |
| **Se connecter** | `button[submit]` | - | POST `/api/login/` |

#### États de l'Interface

##### État Initial
- Tous les champs vides
- Bouton « Se connecter » actif

##### État de Chargement
```
[🔄 Connexion en cours...]
```

##### État d'Erreur
```
❌ Nom d'utilisateur ou mot de passe incorrect
```

##### État de Succès
- Redirection automatique vers `/dashboard`
- Message flash : « ✅ Bienvenue, [Nom] ! »

#### Gestion des Erreurs

| Code Erreur | Message Affiché | Action |
|-------------|----------------|--------|
| **400** | « Veuillez remplir tous les champs » | Highlight champs manquants |
| **401** | « Nom d'utilisateur ou mot de passe incorrect » | Effacer le mot de passe |
| **429** | « Trop de tentatives. Réessayez dans 15 minutes » | Désactiver formulaire |
| **500** | « Erreur serveur. Contactez l'administrateur » | - |

---

### Page de Connexion Élève

#### URL
```
/student/login
```

#### Wireframe

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│                    🎓 Korrigo PMF                            │
│                   Portail Élève                              │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │                                                    │     │
│  │  Connexion Élève                                  │     │
│  │                                                    │     │
│  │  INE (Identifiant National Élève) :              │     │
│  │  [___________________________________]            │     │
│  │  Ex: 1234567890AB                                 │     │
│  │                                                    │     │
│  │  Nom de famille :                                 │     │
│  │  [___________________________________]            │     │
│  │  Ex: DUPONT                                       │     │
│  │                                                    │     │
│  │  [Se connecter]                                   │     │
│  │                                                    │     │
│  │  ❓ Identifiants oubliés ?                         │     │
│  │  → Contactez le secrétariat                       │     │
│  │                                                    │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ← [Retour à l'accueil]                                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Éléments de l'Interface

| Élément | Type | Validation | Comportement |
|---------|------|------------|--------------|
| **INE** | `input[text]` | Obligatoire, 11 chars alphanumériques | Uppercase automatique |
| **Nom de famille** | `input[text]` | Obligatoire, max 100 chars | Uppercase automatique |
| **Se connecter** | `button[submit]` | - | POST `/api/students/login/` |

#### Différences avec Login Admin/Teacher

- ❌ Pas de champ « mot de passe »
- ✅ Authentification par **INE + Nom** uniquement
- ✅ Messages d'aide plus explicites (public élève)
- ✅ Lien vers secrétariat au lieu de « Mot de passe oublié »

---

## Interface Administrateur

### Tableau de Bord Administrateur

#### URL
```
/dashboard
```

#### Wireframe

```
┌──────────────────────────────────────────────────────────────┐
│ 🏠 Accueil  📝 Examens  👥 Utilisateurs  ⚙️ Paramètres  🚪     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Tableau de Bord - Admin M. MARTIN                          │
│  Rôle: Administrateur                                       │
│                                                              │
│  ┌─────────────────────┬─────────────────────┬──────────┐   │
│  │ 📊 Statistiques     │                     │          │   │
│  ├─────────────────────┼─────────────────────┼──────────┤   │
│  │ Examens actifs      │ Copies en correction│ Utilisateurs│ │
│  │ 5                   │ 127/250             │ 42       │   │
│  └─────────────────────┴─────────────────────┴──────────┘   │
│                                                              │
│  📝 Examens Récents                                         │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Bac Blanc Mathématiques TG - Janvier 2026          │     │
│  │ Copies: 25   Identifiées: 25   Corrigées: 13       │     │
│  │ [Gérer] [Exporter]                                 │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  👥 Actions Rapides                                         │
│  [➕ Nouvel examen] [👤 Ajouter utilisateur] [📥 Importer]  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Navigation Principale (Admin)

| Menu | URL | Description | Permissions |
|------|-----|-------------|-------------|
| **🏠 Accueil** | `/dashboard` | Tableau de bord | Admin + Teacher |
| **📝 Examens** | `/exams` | Liste des examens | Admin + Teacher |
| **👥 Utilisateurs** | `/users` | Gestion utilisateurs | **Admin uniquement** |
| **⚙️ Paramètres** | `/settings` | Paramètres système | **Admin uniquement** |
| **👤 Mon Profil** | `/profile` | Profil personnel | Admin + Teacher |
| **🚪 Déconnexion** | - | Logout | Tous |

#### Widgets du Dashboard

##### Widget 1 : Statistiques Globales

Affiche 3 cartes :
- **Examens actifs** : Nombre d'examens non archivés
- **Copies en correction** : Ratio copies finalisées / total
- **Utilisateurs** : Nombre total d'utilisateurs

##### Widget 2 : Examens Récents

Liste des 5 derniers examens créés avec :
- Nom de l'examen
- Progression : Copies identifiées / Copies corrigées
- Boutons d'action : `[Gérer]`, `[Exporter]`

##### Widget 3 : Actions Rapides

Boutons d'action rapide :
- `[➕ Nouvel examen]` → Redirection `/exams/create`
- `[👤 Ajouter utilisateur]` → Modal de création utilisateur
- `[📥 Importer élèves]` → Modal d'import CSV

---

### Page Gestion des Examens

#### URL
```
/exams
```

#### Wireframe

```
┌──────────────────────────────────────────────────────────────┐
│ 🏠 Accueil  📝 Examens  👥 Utilisateurs  ⚙️ Paramètres  🚪     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📝 Gestion des Examens                                     │
│                                                              │
│  [➕ Créer un examen]       Recherche: [______] [🔍]         │
│                                                              │
│  Filtres: [Tous ▼] [Actifs] [Archivés]                      │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 📄 Bac Blanc Mathématiques TG - Janvier 2026       │     │
│  │ Date: 15/01/2026                                   │     │
│  │ Copies: 25 | Identifiées: 25 | Corrigées: 13      │     │
│  │ Statut: 🟡 En cours                                │     │
│  │                                                    │     │
│  │ [📋 Détails] [🔗 Identifier] [📊 Correction]      │     │
│  │ [📥 Exporter CSV] [📦 Archiver]                   │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 📄 Contrôle Continu Physique 1ère - Janvier 2026   │     │
│  │ Date: 12/01/2026                                   │     │
│  │ Copies: 30 | Identifiées: 30 | Corrigées: 30      │     │
│  │ Statut: ✅ Terminé                                  │     │
│  │                                                    │     │
│  │ [📋 Détails] [📥 Exporter CSV] [📦 Archiver]      │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  [Page 1/3]  [◀️ Précédent] [Suivant ▶️]                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Fonctionnalités

| Action | Bouton | Résultat |
|--------|--------|----------|
| **Créer examen** | `[➕ Créer un examen]` | Redirection `/exams/create` |
| **Rechercher** | `[🔍]` | Filtrage en temps réel |
| **Filtrer** | `[Tous ▼]` | Affichage selon statut |
| **Détails** | `[📋 Détails]` | Redirection `/exam/:id` |
| **Identifier** | `[🔗 Identifier]` | Redirection `/exam/:id/identify` |
| **Correction** | `[📊 Correction]` | Redirection `/exam/:id/copies` |
| **Exporter CSV** | `[📥 Exporter CSV]` | Téléchargement CSV |
| **Archiver** | `[📦 Archiver]` | Confirmation + archivage |

#### Statuts d'Examen

| Statut | Badge | Signification |
|--------|-------|---------------|
| **En cours** | 🟡 | Corrections en cours |
| **Terminé** | ✅ | Toutes les copies corrigées |
| **Archivé** | 📦 | Examen archivé |
| **En attente** | ⏳ | Aucune copie identifiée |

---

### Page Détails d'un Examen

#### URL
```
/exam/:id
```

#### Wireframe

```
┌──────────────────────────────────────────────────────────────┐
│ 🏠 Accueil  📝 Examens  ← Retour à la liste                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Bac Blanc Mathématiques TG - Janvier 2026                  │
│  Date: 15/01/2026  |  Créé par: M. MARTIN                   │
│                                                              │
│  ┌─────────────────────┬─────────────────────┬──────────┐   │
│  │ Copies totales      │ Identifiées         │ Corrigées│   │
│  │ 25                  │ 25 (100%)           │ 13 (52%) │   │
│  └─────────────────────┴─────────────────────┴──────────┘   │
│                                                              │
│  📊 Barème de Notation                         [✏️ Modifier] │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Exercice 1 (10 points)                             │     │
│  │   ├─ Question 1.a (3 points)                       │     │
│  │   └─ Question 1.b (7 points)                       │     │
│  │ Exercice 2 (8 points)                              │     │
│  │   ├─ Question 2.a (4 points)                       │     │
│  │   └─ Question 2.b (4 points)                       │     │
│  │ Exercice 3 (2 points)                              │     │
│  │                                                    │     │
│  │ Total: 20 points                                   │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  📋 Actions                                                 │
│  [🔗 Identifier les copies] [📊 Accéder aux corrections]    │
│  [📥 Exporter CSV] [📥 Exporter tous les PDF]              │
│  [🗑️ Supprimer l'examen]                                   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Onglets de Navigation

| Onglet | Contenu |
|--------|---------|
| **📋 Détails** | Informations générales et barème |
| **📦 Fascicules** | Liste des fascicules (booklets) générés |
| **📄 Copies** | Liste des copies identifiées |
| **📊 Statistiques** | Graphiques et statistiques de correction |

---

### Page Identification des Copies (Video-Coding)

#### URL
```
/exam/:id/identify
```

#### Wireframe

```
┌──────────────────────────────────────────────────────────────┐
│ Identification - Bac Blanc Mathématiques TG                  │
│ Copie 1/25                                      [Quitter X]  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────┐               │
│  │                                         │               │
│  │   [Image de l'en-tête de la copie]     │               │
│  │   Nom manuscrit: DUPONT Jean            │               │
│  │                                         │               │
│  └─────────────────────────────────────────┘               │
│                                                              │
│  🤖 OCR détecté : "DUPONT"            Confiance: 85%        │
│                                                              │
│  📚 Suggestions d'élèves :                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │ ● Jean DUPONT - Classe TG2 - INE: 1234567890AB    │    │
│  │ ○ Marie DUPONT - Classe TG4 - INE: 0987654321CD   │    │
│  │ ○ Pierre DUPOND - Classe TG2 - INE: 1122334455EF  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  🔍 Recherche manuelle :                                    │
│  [Nom, INE ou classe...____________]      [Rechercher]     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Résultats de recherche : (vide)                    │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  [← Retour]  [⏩ Passer]  [✅ Valider l'identification]     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Interactions

| Action | Déclencheur | Résultat |
|--------|-------------|----------|
| **Sélectionner élève** | Clic sur radio button | Élève sélectionné (●) |
| **Rechercher** | Saisie + `[Rechercher]` | Mise à jour liste résultats |
| **Valider** | `[✅ Valider]` | POST `/api/copies/:id/identify/` → Copie suivante |
| **Passer** | `[⏩ Passer]` | Copie marquée « À traiter » → Copie suivante |
| **Retour** | `[← Retour]` | Retour à la copie précédente |

#### Indicateur de Progression

```
Progression: ████████████░░░░░░░░ 12/25 (48%)
```

---

### Page Gestion des Utilisateurs

#### URL
```
/users
```

#### Wireframe

```
┌──────────────────────────────────────────────────────────────┐
│ 🏠 Accueil  📝 Examens  👥 Utilisateurs  ⚙️ Paramètres  🚪     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  👥 Gestion des Utilisateurs                                │
│                                                              │
│  [➕ Ajouter un utilisateur]  Recherche: [______] [🔍]       │
│                                                              │
│  Filtres: [Tous ▼] [Admin] [Enseignants] [Élèves]           │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 👤 Jean MARTIN                                     │     │
│  │ Email: jean.martin@lycee.fr                        │     │
│  │ Rôle: 🔐 Administrateur                            │     │
│  │ Statut: ✅ Actif                                    │     │
│  │                                                    │     │
│  │ [✏️ Modifier] [🔒 Réinitialiser MDP] [❌ Désactiver]│     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 👤 Marie DUPONT                                    │     │
│  │ Email: marie.dupont@lycee.fr                       │     │
│  │ Rôle: 📝 Enseignant (Mathématiques)                │     │
│  │ Statut: ✅ Actif                                    │     │
│  │                                                    │     │
│  │ [✏️ Modifier] [🔒 Réinitialiser MDP] [❌ Désactiver]│     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  [Page 1/5]  [◀️ Précédent] [Suivant ▶️]                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Modal Ajout d'Utilisateur

```
┌────────────────────────────────────────────────┐
│ ➕ Ajouter un Utilisateur           [Fermer X] │
├────────────────────────────────────────────────┤
│                                                │
│  Nom d'utilisateur * :                        │
│  [_________________________________]           │
│                                                │
│  Email * :                                    │
│  [_________________________________]           │
│                                                │
│  Mot de passe * :                             │
│  [_________________________________]  [👁️]    │
│                                                │
│  Confirmer mot de passe * :                   │
│  [_________________________________]  [👁️]    │
│                                                │
│  Rôle * :                                     │
│  [Enseignant ▼]  Options: Admin, Enseignant  │
│                                                │
│  Prénom :                                     │
│  [_________________________________]           │
│                                                │
│  Nom :                                        │
│  [_________________________________]           │
│                                                │
│  [Annuler]  [Créer l'utilisateur]             │
│                                                │
└────────────────────────────────────────────────┘
```

---

## Interface Enseignant

### Tableau de Bord Enseignant

#### URL
```
/dashboard
```

#### Wireframe

```
┌──────────────────────────────────────────────────────────────┐
│ 🏠 Accueil  📝 Mes Examens  👤 Mon Profil  🚪 Déconnexion      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Tableau de Bord - Professeur M. DUPONT                     │
│  Matière: Mathématiques                                     │
│                                                              │
│  📊 Mes Statistiques                                        │
│  ┌───────────────────┬───────────────────┬──────────────┐   │
│  │ Copies en attente │ Copies corrigées  │ Taux complet.│   │
│  │ 12                │ 38                │ 76%          │   │
│  └───────────────────┴───────────────────┴──────────────┘   │
│                                                              │
│  📝 Mes Examens                                             │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Bac Blanc Mathématiques TG - Janvier 2026          │     │
│  │ Copies à corriger : 12/25                          │     │
│  │ Progression: ████████████░░░░░░░░ 52%              │     │
│  │                                                    │     │
│  │ [Accéder aux copies]                               │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Contrôle Continu Physique 1ère - Janvier 2026      │     │
│  │ Copies corrigées : 30/30                           │     │
│  │ Progression: ████████████████████ 100%             │     │
│  │                                                    │     │
│  │ [Consulter] [Exporter]                             │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Différences avec Dashboard Admin

| Fonctionnalité | Admin | Teacher |
|----------------|-------|---------|
| **Gestion utilisateurs** | ✅ Oui | ❌ Non |
| **Paramètres système** | ✅ Oui | ❌ Non |
| **Statistiques globales** | ✅ Oui | ⚠️ Partielles (ses copies uniquement) |
| **Upload examens** | ✅ Oui | ✅ Oui |
| **Correction copies** | ✅ Oui | ✅ Oui |

---

### Page Liste des Copies (Enseignant)

#### URL
```
/exam/:id/copies
```

#### Wireframe

```
┌──────────────────────────────────────────────────────────────┐
│ 🏠 Accueil  📝 Mes Examens  ← Retour                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Copies - Bac Blanc Mathématiques TG                        │
│                                                              │
│  Filtre: [Toutes ▼] [PRÊT] [VERROUILLÉE] [CORRIGÉE]         │
│  Tri: [Par date ▼]                                          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 📄 Copie A3F7B2E1                                   │     │
│  │ Statut : 🟢 PRÊT                                   │     │
│  │ Pages : 4                                          │     │
│  │ Dernière modif: -                                  │     │
│  │                                                    │     │
│  │ [🔒 Verrouiller et corriger]                       │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 📄 Copie B4C8D3F2                                   │     │
│  │ Statut : 🔒 VERROUILLÉE par vous                   │     │
│  │ Pages : 4                                          │     │
│  │ Annotations : 12  |  Score: 12.5/20               │     │
│  │ Dernière modif: il y a 5 min                      │     │
│  │                                                    │     │
│  │ [Continuer la correction]                          │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 📄 Copie C5D9E4F3                                   │     │
│  │ Statut : 🔴 VERROUILLÉE par M. MARTIN             │     │
│  │ Pages : 4                                          │     │
│  │ Dernière modif: il y a 15 min                     │     │
│  │                                                    │     │
│  │ [En attente...]                                    │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 📄 Copie D6E0F5G4                                   │     │
│  │ Statut : ✅ CORRIGÉE                                │     │
│  │ Pages : 4  |  Score final: 16/20                  │     │
│  │ Corrigé par: Vous  |  Le: 28/01/2026             │     │
│  │                                                    │     │
│  │ [Consulter] [📥 Télécharger PDF]                  │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### États des Copies

| Statut | Badge | Actions Disponibles |
|--------|-------|---------------------|
| **PRÊT** | 🟢 | `[🔒 Verrouiller et corriger]` |
| **VERROUILLÉE (par vous)** | 🔒 | `[Continuer la correction]` |
| **VERROUILLÉE (autre)** | 🔴 | `[En attente...]` (désactivé) |
| **CORRIGÉE** | ✅ | `[Consulter]`, `[📥 Télécharger]` |

---

### Interface de Correction (Grading Desk)

#### URL
```
/grading/:copyId
```

#### Wireframe Complet

```
┌──────────────────────────────────────────────────────────────┐
│ Copie A3F7B2E1 - Bac Blanc Maths TG         [Quitter X]     │
│ ☁️ Sauvegardé il y a 12 sec                                  │
├────────────────────────────┬─────────────────────────────────┤
│                            │                                 │
│                            │  📊 Barème et Notation          │
│                            │                                 │
│   📄 Visualiseur PDF       │  ┌────────────────────────┐    │
│                            │  │ ☑ Ex1 (10 pts) [10/10] │    │
│   [PDF de la copie]        │  │   ☑ Q1.a (3) [3/3]     │    │
│   Page 1/4                 │  │   ☑ Q1.b (7) [7/7]     │    │
│                            │  │                        │    │
│   🔍 Zoom: 100%            │  │ ☐ Ex2 (8 pts) [0/8]    │    │
│   [➖] [100%] [➕]          │  │   ☐ Q2.a (4) [__/4]    │    │
│                            │  │   ☐ Q2.b (4) [__/4]    │    │
│   🛠️ Outils d'Annotation    │  │                        │    │
│   ┌──────────────────┐     │  │ ☐ Ex3 (2 pts) [__/2]   │    │
│   │ ✏️ Commentaire    │     │  │                        │    │
│   │ 🟨 Surligner     │     │  │ Total: 10/20           │    │
│   │ ❌ Erreur        │     │  │                        │    │
│   │ ⭐ Bonus         │     │  └────────────────────────┘    │
│   └──────────────────┘     │                                 │
│                            │  📝 Annotations (3)             │
│   ◀️ Page préc. | Page suiv.▶️│  ┌────────────────────────┐  │
│                            │  │ 💬 "Erreur ligne 3"     │    │
│                            │  │    Page 1 (-0.5 pts)   │    │
│                            │  │    [Modifier] [Suppr]  │    │
│                            │  └────────────────────────┘    │
│                            │                                 │
│                            │  [💾 Sauvegarder]               │
│                            │  [✅ Finaliser la copie]        │
│                            │                                 │
└────────────────────────────┴─────────────────────────────────┘
```

#### Zones de l'Interface

##### Zone 1 : Visualiseur PDF (Gauche - 60%)

| Élément | Fonction |
|---------|----------|
| **PDF Canvas** | Affiche le PDF avec annotations superposées |
| **Zoom** | Contrôle zoom: 50%, 75%, 100%, 125%, 150%, 200% |
| **Navigation pages** | Boutons « ◀️ Précédent » et « Suivant ▶️ » |
| **Outils annotation** | Sélection outil actif (surbrillance) |

##### Zone 2 : Barre de Notation (Droite - 40%)

| Section | Contenu |
|---------|---------|
| **Barème** | Arbre hiérarchique des exercices/questions |
| **Champs de score** | Input numériques pour saisir les points |
| **Total** | Calcul automatique de la note finale |
| **Liste annotations** | Liste des annotations créées (cliquables pour modifier) |
| **Boutons action** | Sauvegarder, Finaliser |

#### Workflow de Création d'Annotation

##### 1. Annotation « Commentaire » 💬

```
┌──────────────────────────────────────┐
│ 💬 Ajouter un Commentaire             │
├──────────────────────────────────────┤
│                                      │
│ Position: Page 1, (x: 120, y: 350)  │
│                                      │
│ Commentaire * :                      │
│ ┌──────────────────────────────────┐ │
│ │ Erreur de signe à la ligne 3     │ │
│ │                                  │ │
│ └──────────────────────────────────┘ │
│                                      │
│ Points ajoutés/retirés :             │
│ [-0.5_]  (négatif pour retirer)     │
│                                      │
│ [Annuler]  [Valider]                 │
│                                      │
└──────────────────────────────────────┘
```

**Actions** :
1. Clic sur outil `✏️ Commentaire`
2. Clic sur PDF à l'emplacement souhaité
3. Modal s'ouvre
4. Saisie commentaire + points
5. Clic `[Valider]`
6. Annotation créée sur PDF + ajoutée à la liste

##### 2. Annotation « Surligner » 🟨

**Actions** :
1. Clic sur outil `🟨 Surligner`
2. Clic + glissement sur PDF (drag)
3. Rectangle jaune transparent créé
4. Annotation enregistrée automatiquement

##### 3. Annotation « Erreur » ❌

```
┌──────────────────────────────────────┐
│ ❌ Signaler une Erreur                │
├──────────────────────────────────────┤
│                                      │
│ Position: Page 2, (x: 200, y: 180)  │
│                                      │
│ Commentaire (optionnel) :            │
│ ┌──────────────────────────────────┐ │
│ │ Erreur de méthode                │ │
│ └──────────────────────────────────┘ │
│                                      │
│ Points retirés * :                   │
│ [-1.0_]  (doit être négatif)        │
│                                      │
│ [Annuler]  [Valider]                 │
│                                      │
└──────────────────────────────────────┘
```

##### 4. Annotation « Bonus » ⭐

```
┌──────────────────────────────────────┐
│ ⭐ Ajouter un Bonus                   │
├──────────────────────────────────────┤
│                                      │
│ Position: Page 3, (x: 150, y: 420)  │
│                                      │
│ Commentaire (optionnel) :            │
│ ┌──────────────────────────────────┐ │
│ │ Excellente initiative !          │ │
│ └──────────────────────────────────┘ │
│                                      │
│ Points bonus * :                     │
│ [+0.5_]  (doit être positif)        │
│                                      │
│ [Annuler]  [Valider]                 │
│                                      │
└──────────────────────────────────────┘
```

#### Finalisation de la Copie

```
┌────────────────────────────────────────────────┐
│ ⚠️ Confirmation de Finalisation                 │
├────────────────────────────────────────────────┤
│                                                │
│ Êtes-vous sûr de vouloir finaliser cette      │
│ copie ?                                       │
│                                                │
│ Résumé :                                      │
│ • Score total : 14.5/20                        │
│ • Annotations : 8                              │
│ • Questions notées : 7/7                       │
│                                                │
│ ⚠️ Cette action ne peut pas être annulée       │
│ facilement. La copie sera verrouillée et      │
│ le PDF final sera généré.                     │
│                                                │
│ [Annuler]  [Confirmer la finalisation]         │
│                                                │
└────────────────────────────────────────────────┘
```

**Après confirmation** :
1. Loading spinner : « 🔄 Génération du PDF final... »
2. Redirect vers `/exam/:id/copies`
3. Message de succès : « ✅ Copie finalisée avec succès ! »

---

## Interface Élève

### Tableau de Bord Élève

#### URL
```
/student/dashboard
```

#### Wireframe

```
┌──────────────────────────────────────────────────────────────┐
│ 🏠 Mes Copies  👤 Mon Profil  🚪 Déconnexion                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Mes Copies - Jean DUPONT (TG2)                             │
│  INE: 1234567890AB                                          │
│                                                              │
│  📚 Mes Examens Corrigés                                    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 📝 Bac Blanc Mathématiques TG - Janvier 2026       │     │
│  │ Note : 14.5/20                                     │     │
│  │ Corrigé le : 28/01/2026                            │     │
│  │ Professeur: M. DUPONT                              │     │
│  │                                                    │     │
│  │ [👁️ Voir la copie] [📥 Télécharger PDF]           │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 📝 Contrôle Continu Physique - Janvier 2026        │     │
│  │ Note : 16/20                                       │     │
│  │ Corrigé le : 25/01/2026                            │     │
│  │ Professeur: Mme MARTIN                             │     │
│  │                                                    │     │
│  │ [👁️ Voir la copie] [📥 Télécharger PDF]           │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ℹ️ Vous ne voyez que vos copies finalisées par les         │
│  professeurs.                                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Informations Affichées

Pour chaque copie :
- **Nom de l'examen**
- **Note finale** (en gras)
- **Date de correction**
- **Nom du professeur** (si disponible)
- **Boutons d'action** : Voir, Télécharger

---

### Visualiseur de Copie Élève

#### URL
```
/student/copy/:id
```

#### Wireframe

```
┌──────────────────────────────────────────────────────────────┐
│ Bac Blanc Mathématiques TG - Janvier 2026      [Fermer X]   │
│ Note : 14.5/20                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                                                              │
│                                                              │
│                  [PDF avec annotations]                      │
│                  Affichage de votre copie                    │
│                  avec les commentaires du professeur         │
│                                                              │
│                                                              │
│                                                              │
│  Page 1/4                                                   │
│                                                              │
│  🔍 Zoom:  [➖] [100%] [➕]                                   │
│                                                              │
│  [◀️ Page précédente]  [Page suivante ▶️]                    │
│                                                              │
│  [📥 Télécharger cette copie]                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Fonctionnalités

| Fonction | Action |
|----------|--------|
| **Zoom** | Boutons `-` et `+`, ou `Ctrl + Molette` |
| **Navigation** | Flèches ou boutons « ◀️ » « ▶️ » |
| **Téléchargement** | Bouton `[📥 Télécharger]` |
| **Fermeture** | Bouton `[X]` ou touche `Échap` |

> ⚠️ **Limitations** : Les élèves ne peuvent **PAS** :
> - Modifier les annotations
> - Voir les copies des autres élèves
> - Voir leurs copies avant finalisation

---

## Composants Communs

### Visualiseur PDF (PDF.js)

#### Technologie
- **Librairie** : PDF.js 4.0+
- **Rendu** : Canvas HTML5

#### Fonctionnalités

| Fonctionnalité | Implémentation |
|----------------|----------------|
| **Zoom** | Niveaux: 50%, 75%, 100%, 125%, 150%, 200% |
| **Navigation** | Pagination avec boutons ou flèches clavier |
| **Rendu** | Canvas 2D avec antialiasing |
| **Performance** | Lazy loading des pages (uniquement page visible) |
| **Annotations** | SVG overlay sur canvas |

#### Gestion des Annotations (Enseignant uniquement)

**Stockage** :
- Annotations stockées en **coordonnées relatives** (0-1)
- Format : `{ x: 0.25, y: 0.40, width: 0.1, height: 0.05, ... }`

**Affichage** :
- Conversion coordonnées relatives → pixels selon zoom actuel
- SVG `<svg>` overlay sur canvas
- Éléments : `<rect>`, `<text>`, `<line>`, etc.

**Interaction** :
- Clic sur annotation → Modal d'édition
- Hover → Tooltip avec commentaire

---

### Système de Notifications

#### Types de Notifications

| Type | Couleur | Icône | Durée Affichage |
|------|---------|-------|-----------------|
| **Succès** | Vert | ✅ | 3 secondes |
| **Erreur** | Rouge | ❌ | 5 secondes (manuelle) |
| **Avertissement** | Orange | ⚠️ | 4 secondes |
| **Information** | Bleu | ℹ️ | 3 secondes |

#### Position

- **Desktop** : Coin supérieur droit
- **Mobile** : Haut de l'écran (full width)

#### Exemples

```
┌────────────────────────────────────┐
│ ✅ Copie finalisée avec succès !    │
└────────────────────────────────────┘
```

```
┌────────────────────────────────────┐
│ ❌ Erreur: Copie déjà verrouillée   │
│ [X Fermer]                         │
└────────────────────────────────────┘
```

---

### Indicateurs de Chargement

#### Spinner Global

Pour les chargements de page :

```
┌──────────────────────────────────────┐
│                                      │
│            🔄                         │
│      Chargement...                   │
│                                      │
└──────────────────────────────────────┘
```

#### Skeleton Loaders

Pour le chargement de listes (meilleure UX) :

```
┌────────────────────────────────────┐
│ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄               │
│ ▄▄▄▄▄▄▄▄▄▄▄▄▄                      │
│ ▄▄▄▄▄▄▄▄                           │
└────────────────────────────────────┘
```

---

### Modals et Dialogues

#### Structure Standard

```
┌────────────────────────────────────────────────┐
│ Titre du Modal                      [Fermer X] │
├────────────────────────────────────────────────┤
│                                                │
│ Contenu du modal                               │
│                                                │
│ [Bouton Secondaire]  [Bouton Principal]        │
│                                                │
└────────────────────────────────────────────────┘
```

#### Fermeture

- Clic sur `[X]`
- Clic en dehors du modal (overlay)
- Touche `Échap`

---

## Workflows de Navigation

### Workflow Correction Complète (Enseignant)

```
1. Connexion
   ↓
2. Dashboard Enseignant (/dashboard)
   ↓
3. Clic "Accéder aux copies" sur un examen
   ↓
4. Liste des copies (/exam/:id/copies)
   ↓
5. Clic "Verrouiller et corriger" sur une copie PRÊT
   ↓
6. Interface de correction (/grading/:copyId)
   ↓ (Ajout annotations, notation)
   ↓
7. Clic "Finaliser la copie"
   ↓ (Confirmation)
   ↓
8. Retour à Liste des copies (4)
   ↓ (Répéter 5-8 pour autres copies)
   ↓
9. Toutes les copies corrigées
   ↓
10. Export CSV / PDF (depuis Liste examens)
```

### Workflow Identification (Secrétariat)

```
1. Connexion Admin
   ↓
2. Dashboard (/dashboard)
   ↓
3. Clic "Gérer" sur un examen
   ↓
4. Détails examen (/exam/:id)
   ↓
5. Clic "Identifier les copies"
   ↓
6. Interface Video-Coding (/exam/:id/identify)
   ↓ (Pour chaque copie)
   ├─ Lecture en-tête
   ├─ Sélection élève
   └─ Validation
   ↓
7. Toutes copies identifiées
   ↓
8. Retour Dashboard
```

### Workflow Consultation (Élève)

```
1. Connexion Élève (/student/login)
   ↓
2. Dashboard Élève (/student/dashboard)
   ↓ (Liste des copies corrigées)
   ↓
3. Clic "Voir la copie" sur un examen
   ↓
4. Visualiseur copie (/student/copy/:id)
   ↓ (Consultation)
   ├─ Navigation pages
   ├─ Zoom
   └─ Lecture annotations
   ↓
5. (Optionnel) Téléchargement PDF
   ↓
6. Fermeture visualiseur → Retour Dashboard (2)
```

---

## Responsive Design

### Breakpoints

| Breakpoint | Largeur | Nom | Usage |
|------------|---------|-----|-------|
| **xs** | < 640px | Mobile portrait | 1 colonne |
| **sm** | 640-768px | Mobile landscape | 1-2 colonnes |
| **md** | 768-1024px | Tablette | 2 colonnes |
| **lg** | 1024-1280px | Desktop | 2-3 colonnes |
| **xl** | > 1280px | Large desktop | Full layout |

### Adaptations Mobile

#### Interface de Correction (Mobile)

> 🖥️ **Recommandation** : L'interface de correction est **optimisée pour desktop**. Utilisation sur tablette possible, déconseillée sur mobile.

**Adaptation Tablette (768px+)** :
- Barème en **onglet** au lieu de sidebar
- Bouton `[📊]` pour afficher/masquer barème
- Outils annotation en **barre flottante**

**Mobile (< 768px)** :
```
⚠️ Message affiché :
"Pour une meilleure expérience, utilisez un ordinateur
ou une tablette pour corriger les copies."

[Continuer quand même] [Retour]
```

#### Dashboard (Mobile)

- Navigation en **menu hamburger** 🍔
- Cartes statistiques en **pile verticale**
- Liste examens en **liste compacte**

---

## Accessibilité

### Standards

- **WCAG 2.1** Niveau AA visé
- **Aria labels** sur tous les boutons icônes
- **Keyboard navigation** supportée

### Navigation Clavier

| Touche | Action |
|--------|--------|
| `Tab` | Navigation entre éléments |
| `Shift + Tab` | Navigation inverse |
| `Entrée` | Activer bouton/lien |
| `Espace` | Cocher checkbox, activer bouton |
| `Échap` | Fermer modal |
| `←` `→` | Navigation pages PDF |

### Contraste

| Élément | Ratio | Conformité |
|---------|-------|------------|
| Texte normal | 4.5:1 | ✅ AA |
| Texte large | 3:1 | ✅ AA |
| Boutons principaux | 4.5:1 | ✅ AA |
| Icônes | 3:1 | ✅ AA |

### Screen Readers

- Tous les boutons icônes ont un `aria-label`
- Les images ont un `alt` descriptif
- Les formulaires ont des `<label>` associés

---

## Annexes

### Palette de Couleurs

| Usage | Couleur | Hex |
|-------|---------|-----|
| **Primary** | Bleu | `#3B82F6` |
| **Success** | Vert | `#10B981` |
| **Error** | Rouge | `#EF4444` |
| **Warning** | Orange | `#F59E0B` |
| **Info** | Bleu clair | `#06B6D4` |
| **Gray** | Gris | `#6B7280` |

### Icônes

**Librairie** : Font Awesome 6+ ou Heroicons

| Concept | Icône |
|---------|-------|
| Examen | 📝 |
| Copie | 📄 |
| Utilisateur | 👤 |
| Admin | 🔐 |
| Statistiques | 📊 |
| Téléchargement | 📥 |
| Upload | 📤 |
| Fermer | ✖️ |
| Valider | ✅ |
| Erreur | ❌ |

---

## Changelog

| Version | Date | Changements |
|---------|------|-------------|
| **1.0.0** | 30/01/2026 | Version initiale du guide de navigation UI |

---

**© 2026 Korrigo PMF - Plateforme de Correction Numérique pour Lycées**

> 📧 **Contact** : Pour toute question, consultez les autres guides utilisateur ou contactez le support.
