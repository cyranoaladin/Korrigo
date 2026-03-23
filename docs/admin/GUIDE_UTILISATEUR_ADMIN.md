# Guide Utilisateur Administrateur - Korrigo PMF

> **Version**: 2.0.0
> **Date**: 23 Mars 2026
> **Public**: Administrateurs techniques (Admin NSI, IT staff, Proviseur Adjoint)  
> **Langue**: Français (technique)

Ce document constitue le manuel technique complet pour les administrateurs de la plateforme Korrigo PMF.

---

## 📋 Table des Matières

1. [Prise en Main](#1-prise-en-main)
2. [Gestion des Utilisateurs](#2-gestion-des-utilisateurs)
3. [Gestion des Examens](#3-gestion-des-examens)
4. [Configuration Système](#4-configuration-système)
5. [Monitoring et Logs](#5-monitoring-et-logs)
6. [Export de Données](#6-export-de-données)
7. [Opérations Avancées](#7-opérations-avancées)
8. [Maintenance](#8-maintenance)
9. [Résolution de Problèmes](#9-résolution-de-problèmes)

---

## 1. Prise en Main

### 1.1 Première Connexion

#### Accès à la Plateforme

**URL** : `https://korrigo.votre-lycee.fr` (ou `http://localhost:8088` en développement)

**Identifiants par Défaut** (à changer immédiatement):
- **Username**: `admin`
- **Password**: `admin` (défini lors de l'installation)

#### Tableau de Bord Administrateur

Après connexion, vous accédez au **Dashboard Administrateur** avec les modules suivants:

```
┌────────────────────────────────────────────────────────────┐
│ Korrigo PMF - Dashboard Administrateur                     │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  📊 Statistiques                                           │
│  ├─ Examens: 12 (actifs: 3, terminés: 9)                   │
│  ├─ Copies: 450 (corrigées: 380, en cours: 70)             │
│  ├─ Utilisateurs: 45 enseignants, 650 élèves              │
│  └─ Stockage: 45 Go / 200 Go                              │
│                                                            │
│  🎓 Examens                                                │
│  ├─ [Créer un Examen]                                      │
│  ├─ [Liste des Examens]                                    │
│  └─ [Exports Pronote]                                      │
│                                                            │
│  👥 Utilisateurs                                           │
│  ├─ [Gérer les Utilisateurs]                               │
│  ├─ [Importer Élèves (CSV)]                                │
│  └─ [Groupes et Permissions]                               │
│                                                            │
│  ⚙️ Configuration                                          │
│  ├─ [Paramètres Système]                                   │
│  ├─ [Sauvegardes]                                          │
│  └─ [Logs d'Audit]                                         │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 1.2 Navigation Principale

#### Menu Principal

| Section | Description | Rôle Requis |
|---------|-------------|-------------|
| **Accueil** | Dashboard avec statistiques | Admin |
| **Examens** | Gestion complète des examens | Admin / Teacher |
| **Correction** | Interface de correction (si utilisée par admin) | Admin / Teacher |
| **Utilisateurs** | Gestion des comptes | Admin uniquement |
| **Étudiants** | Base de données élèves | Admin / Teacher |
| **Paramètres** | Configuration système | Admin uniquement |
| **Logs** | Journal d'audit | Admin uniquement |
| **Profil** | Mon compte, changer mot de passe | Tous |

#### Raccourcis Clavier (Desktop)

| Raccourci | Action |
|-----------|--------|
| `Ctrl + H` | Retour au dashboard |
| `Ctrl + E` | Accéder aux examens |
| `Ctrl + U` | Gérer les utilisateurs |
| `Ctrl + L` | Ouvrir les logs |
| `Ctrl + S` | Sauvegarder (contexte formulaire) |
| `Esc` | Fermer modal |

---

## 2. Gestion des Utilisateurs

### 2.1 Créer un Utilisateur

#### Enseignants et Administrateurs

**Chemin** : Dashboard → Utilisateurs → [+ Nouvel Utilisateur]

**Formulaire** :

| Champ | Type | Obligatoire | Validation | Exemple |
|-------|------|-------------|------------|---------|
| **Username** | Texte | ✅ | Unique, 3-150 caractères | `jdupont` |
| **Email** | Email | ✅ | Format valide | `j.dupont@lycee.fr` |
| **Prénom** | Texte | ✅ | 1-100 caractères | `Jean` |
| **Nom** | Texte | ✅ | 1-100 caractères | `Dupont` |
| **Rôle** | Select | ✅ | Admin / Teacher | `Teacher` |
| **Mot de Passe** | Password | ✅ | Min. 8 caractères | `********` |
| **Actif** | Checkbox | ✅ | Par défaut: ✅ | ✅ |

**Procédure** :
1. Cliquer sur **[+ Nouvel Utilisateur]**
2. Remplir le formulaire
3. Sélectionner le **rôle** :
   - `Admin` : Accès complet (gestion utilisateurs, config, exports)
   - `Teacher` : Correction et gestion d'examens uniquement
4. Définir un mot de passe temporaire (recommandation : `Lycee2026!`)
5. Cocher **"Forcer changement de mot de passe"** (recommandé)
6. Cliquer **[Créer]**
7. **Communication** : Envoyer les identifiants à l'utilisateur (email sécurisé)

#### Étudiants

**Méthode Recommandée** : Import CSV depuis Pronote (voir [Section 2.3](#23-import-en-masse-csv))

**Création Manuelle** (cas exceptionnel):
- Chemin : Dashboard → Étudiants → [+ Nouvel Étudiant]
- Champs : INE, Nom, Prénom, Classe, Email (optionnel)

### 2.2 Modifier un Utilisateur

**Chemin** : Dashboard → Utilisateurs → [Cliquer sur l'utilisateur] → [Modifier]

**Actions Possibles** :
- Changer le rôle (Admin ↔ Teacher)
- Réinitialiser le mot de passe
- Désactiver le compte (sans suppression)
- Mettre à jour l'email ou le nom

**Réinitialisation de Mot de Passe** :
1. Cliquer sur [Réinitialiser Mot de Passe]
2. Choisir :
   - **Générer Automatiquement** : Korrigo génère un mot de passe aléatoire
   - **Définir Manuellement** : Saisir un mot de passe temporaire
3. Copier le nouveau mot de passe
4. Envoyer à l'utilisateur (email sécurisé)

### 2.3 Import en Masse (CSV)

#### Export depuis Pronote

**Pronote** → **Ressources** → **Élèves** → **Exporter** → **Format CSV**

**Colonnes Requises** :
- `INE` : Identifiant National Élève (11 caractères)
- `Nom` : Nom de famille
- `Prénom` : Prénom
- `Classe` : Code classe (ex: `TG2`, `1ES3`)
- `Email` : Email (optionnel)

**Exemple CSV** :
```csv
INE,Nom,Prénom,Classe,Email
12345678901,DUPONT,Jean,TG2,jean.dupont@exemple.fr
12345678902,MARTIN,Sophie,TG2,sophie.martin@exemple.fr
12345678903,DURAND,Pierre,TG4,pierre.durand@exemple.fr
```

#### Procédure d'Import

**Chemin** : Dashboard → Étudiants → [Importer CSV]

1. **Préparer le Fichier** :
   - Format : CSV (encodage UTF-8 recommandé)
   - Taille max : 10 Mo
   - Lignes max : 5000 élèves

2. **Upload** :
   - Cliquer sur [Parcourir] ou glisser-déposer le fichier
   - Sélectionner le fichier CSV

3. **Mapping des Colonnes** :
   - Korrigo détecte automatiquement les colonnes
   - Vérifier la correspondance :
     ```
     Colonne CSV → Champ Korrigo
     INE         → INE
     Nom         → Nom
     Prénom      → Prénom
     Classe      → Classe
     Email       → Email (optionnel)
     ```

4. **Validation** :
   - Korrigo affiche un aperçu (10 premières lignes)
   - **Vérifier** : Pas de doublons INE, format correct

5. **Import** :
   - Cliquer sur [Importer]
   - Barre de progression s'affiche
   - **Résultat** :
     ```
     ✅ 650 élèves importés
     ⚠️ 3 doublons ignorés (INE déjà existant)
     ❌ 2 erreurs (INE invalide)
     ```

6. **Rapport** :
   - Télécharger le rapport d'import (CSV) pour les erreurs
   - Corriger les erreurs dans Pronote
   - Réimporter uniquement les lignes en erreur

### 2.4 Désactiver / Supprimer un Utilisateur

#### Désactiver (Recommandé)

**Avantages** : Conservation de l'historique, pas de suppression de données

**Procédure** :
1. Dashboard → Utilisateurs → [Utilisateur] → [Modifier]
2. Décocher **"Compte actif"**
3. Sauvegarder
4. **Effet** : L'utilisateur ne peut plus se connecter, mais ses corrections restent visibles

#### Supprimer (Prudence)

⚠️ **Avertissement** : La suppression d'un utilisateur peut casser la traçabilité des corrections.

**Procédure Recommandée** :
1. **Désactiver** le compte (voir ci-dessus)
2. **Attendre** 1 an (délai légal de conservation)
3. **Supprimer** : Dashboard → Utilisateurs → [Utilisateur] → [Supprimer] → Confirmer

**Effet** :
- Compte supprimé de la base de données
- Corrections conservées (avec mention "Utilisateur supprimé")
- Logs d'audit conservés (compliance RGPD)

### 2.5 Gestion des Permissions

#### Rôles et Matrice de Permissions

| Action | Admin | Teacher | Student |
|--------|-------|---------|---------|
| **Voir Dashboard Admin** | ✅ | ❌ | ❌ |
| **Créer Examen** | ✅ | ✅ | ❌ |
| **Voir Tous les Examens** | ✅ | ✅ | ❌ |
| **Modifier Examen** | ✅ | ✅ (si créateur) | ❌ |
| **Supprimer Examen** | ✅ | ❌ | ❌ |
| **Corriger Copie** | ✅ | ✅ | ❌ |
| **Voir Toutes les Copies** | ✅ | ✅ (de son examen) | ❌ |
| **Voir Ma Copie** | ❌ | ❌ | ✅ |
| **Gérer Utilisateurs** | ✅ | ❌ | ❌ |
| **Importer Élèves** | ✅ | ❌ | ❌ |
| **Exporter CSV Pronote** | ✅ | ❌ | ❌ |
| **Configuration Système** | ✅ | ❌ | ❌ |
| **Voir Logs d'Audit** | ✅ | ❌ | ❌ |
| **Sauvegardes** | ✅ | ❌ | ❌ |

**Document de Référence** : [SECURITY_PERMISSIONS_INVENTORY.md](../../SECURITY_PERMISSIONS_INVENTORY.md)

---

## 3. Gestion des Examens

### 3.1 Créer un Examen

#### Informations Générales

**Chemin** : Dashboard → Examens → [+ Nouvel Examen]

**Formulaire - Étape 1 : Informations** :

| Champ | Type | Obligatoire | Exemple |
|-------|------|-------------|---------|
| **Nom** | Texte | ✅ | `Bac Blanc Mathématiques TG` |
| **Date** | Date | ✅ | `15/03/2026` |
| **Matière** | Select | ✅ | `Mathématiques` |
| **Classe** | Select (multiple) | ✅ | `TG2`, `TG4` |
| **Description** | Textarea | ❌ | `Examen blanc sur les suites et probabilités` |

**Cliquer sur [Suivant] pour passer à l'étape 2**

#### Définition du Barème

**Étape 2 : Barème**

Le barème définit la structure de notation hiérarchique : **Exercices → Questions → Points**

**Exemple de Structure** :
```
Exercice 1 (10 points)
  ├─ Question 1.a (3 points)
  ├─ Question 1.b (4 points)
  └─ Question 1.c (3 points)

Exercice 2 (8 points)
  ├─ Question 2.a (4 points)
  └─ Question 2.b (4 points)

Exercice 3 (2 points)
  └─ Question unique (2 points)

TOTAL : 20 points
```

**Interface de Construction** :

1. **Ajouter un Exercice** :
   - Cliquer sur [+ Exercice]
   - Label : `Exercice 1`
   - Points : `10`

2. **Ajouter des Questions** :
   - Cliquer sur l'exercice (déplier)
   - [+ Question]
   - Label : `Question 1.a`
   - Points : `3`

3. **Validation Automatique** :
   - Korrigo vérifie que la somme des questions = points de l'exercice
   - Alerte si incohérence

4. **Sauvegarder** :
   - Cliquer sur [Créer Examen]
   - L'examen est créé avec le statut `CREATED`

### 3.2 Uploader un PDF d'Examen

#### Prérequis

**Format Requis** :
- **Extension** : `.pdf` uniquement
- **Taille Max** : 50 Mo (par défaut, configurable)
- **Pages** : Multiple de 4 (si A3 recto-verso = 4 pages A4 par copie)
- **Résolution** : 150-300 DPI (recommandé)
- **Couleur** : Niveaux de gris ou couleur (OCR fonctionne mieux en niveaux de gris)

**Scan Recommandé** :
- Scanner **A3 recto-verso** (ex: Canon DR-C230, Fujitsu fi-7160)
- Mode : **Recto-Verso automatique**
- Format : **A3** (sera découpé automatiquement en A4)
- Ordre : **Pages dans l'ordre** (P1, P2, P3, P4, P1, P2, P3, P4, ...)

#### Procédure d'Upload

**Chemin** : Dashboard → Examens → [Examen] → [Upload PDF]

1. **Sélectionner le Fichier** :
   - Cliquer sur [Parcourir] ou glisser-déposer
   - Choisir le fichier PDF

2. **Validation** :
   - Korrigo vérifie :
     - ✅ Format PDF
     - ✅ Taille < 50 Mo
     - ✅ PDF non corrompu
     - ✅ Nombre de pages (warning si pas multiple de 4)

3. **Upload** :
   - Barre de progression s'affiche
   - **Temps estimé** : ~30 secondes pour 100 pages

4. **Traitement Automatique** (Asynchrone via Celery) :
   - ✅ **Rasterisation** : Conversion PDF → Images (1 image/page)
   - ✅ **Détection A3** : Détection automatique des pages A3
   - ✅ **Découpage** : Split A3 → A4 (gauche/droite)
   - ✅ **Détection En-têtes** : Reconnaissance zones de nom
   - ✅ **OCR** : Lecture optique des noms (via Tesseract)
   - ✅ **Création Booklets** : Groupement par fascicules de 4 pages

5. **Résultat** :
   ```
   ✅ PDF traité avec succès
   📄 100 pages scannées
   📋 25 fascicules (booklets) créés
   🔍 OCR effectué sur 25 en-têtes
   ⏱️ Temps de traitement : 2 min 15 s
   ```

6. **Statut** :
   - L'examen passe au statut `PROCESSED`
   - Les booklets sont prêts pour identification

### 3.3 Identification des Copies

**Voir Guide Détaillé** : [GESTION_UTILISATEURS.md - Section Import](./GESTION_UTILISATEURS.md)

**Workflow Simplifié** :

1. **Accéder au Bureau d'Identification** :
   - Dashboard → Examens → [Examen] → [Identifier les Copies]

2. **Interface "Video-Coding"** :
   ```
   ┌─────────────────────────────────────────────────┐
   │ Copie 1/25 - Anonymat Temporaire: BK-001       │
   ├─────────────────────────────────────────────────┤
   │                                                 │
   │  [Image en-tête avec nom manuscrit]            │
   │                                                 │
   │  🔍 OCR détecté: "DUPONT" (confiance: 85%)     │
   │                                                 │
   │  Suggestions élèves:                           │
   │  ○ Jean DUPONT - TG2 (INE: 12345678901)        │
   │  ○ Marie DUPONT - TG4 (INE: 12345678902)       │
   │  ○ Pierre DUPOND - TG2 (INE: 12345678903)      │
   │                                                 │
   │  ou Saisie manuelle:                           │
   │  [Recherche par nom: _______________]          │
   │                                                 │
   │  [Valider]  [Passer]  [Agrafage Manuel]       │
   └─────────────────────────────────────────────────┘
   ```

3. **Valider l'Identification** :
   - Sélectionner l'élève correct
   - Cliquer sur [Valider]
   - La copie passe au statut `READY` (prête à corriger)

4. **Cas Spéciaux** :
   - **Nom Illisible** : Saisie manuelle (recherche par classe)
   - **Fascicule Incomplet** : [Agrafage Manuel] pour fusionner plusieurs booklets
   - **Copie de Remplacement** : Marquer comme doublon

### 3.4 Suivi de la Correction

**Chemin** : Dashboard → Examens → [Examen] → [Suivi]

**Tableau de Bord Examen** :

```
┌──────────────────────────────────────────────────────────────┐
│ Bac Blanc Mathématiques TG - 15/03/2026                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 Statistiques                                             │
│  ├─ Total Copies: 50                                         │
│  ├─ ✅ Corrigées (GRADED): 35 (70%)                          │
│  ├─ 🔒 En Cours (LOCKED): 10 (20%)                           │
│  ├─ 📝 À Corriger (READY): 5 (10%)                           │
│  └─ ⏱️ Temps Moyen: 18 min/copie                             │
│                                                              │
│  👥 Correcteurs                                              │
│  ├─ Jean Dupont: 15/20 corrigées (75%)                       │
│  ├─ Sophie Martin: 20/20 corrigées (100%) ✅                 │
│  └─ Pierre Durand: 0/10 corrigées (0%) ⚠️                    │
│                                                              │
│  📈 Progression                                              │
│  [████████████████████░░░░░░░░] 70%                         │
│                                                              │
│  [Exporter CSV] [Générer PDF Finaux] [Voir Logs]           │
└──────────────────────────────────────────────────────────────┘
```

**Indicateurs** :
- **Taux de Correction** : % de copies finalisées
- **Copies Bloquées** : Copies verrouillées depuis > 30 min (risque d'oubli)
- **Moyenne Classe** : Note moyenne calculée en temps réel
- **Temps Moyen** : Temps moyen de correction par copie

---

## 4. Configuration Système

### 4.1 Paramètres Généraux

**Chemin** : Dashboard → Paramètres → [Général]

| Paramètre | Description | Valeur Par Défaut | Recommandé |
|-----------|-------------|-------------------|------------|
| **Nom du Lycée** | Affiché sur le portail élève | `Lycée Exemple` | Nom complet |
| **Email Contact** | Email de support affiché aux utilisateurs | `contact@lycee.fr` | Email secrétariat |
| **Langue** | Langue de l'interface | `Français` | `Français` |
| **Fuseau Horaire** | Timezone pour les logs | `Europe/Paris` | Ajuster selon localisation |
| **Taille Max Upload** | Taille maximale fichier PDF | `50 Mo` | `100 Mo` (si scanner haute résolution) |

### 4.2 Sécurité

**Chemin** : Dashboard → Paramètres → [Sécurité]

| Paramètre | Description | Valeur Par Défaut | Recommandé |
|-----------|-------------|-------------------|------------|
| **Expiration Session** | Durée de validité d'une session | `2 heures` | `2 heures` |
| **Longueur Min. Mot de Passe** | Caractères minimum | `8` | `10` (haute sécurité) |
| **Complexité Mot de Passe** | Lettres + chiffres + symboles | `Recommandé` | `Obligatoire` (production) |
| **Tentatives de Connexion** | Max avant blocage temporaire | `5` | `5` |
| **Durée Blocage** | Durée du blocage après échecs | `15 min` | `15 min` |
| **Verrou Copie Expiration** | Durée max d'un verrou de copie | `30 min` | `60 min` (corrections longues) |
| **HTTPS Obligatoire** | Forcer connexions HTTPS | `Non` (dev) | `Oui` (production) |

⚠️ **Note Production** : `HTTPS Obligatoire` doit être activé en production (certificat SSL requis).

### 4.3 Email (Notifications)

**Chemin** : Dashboard → Paramètres → [Email]

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| **Serveur SMTP** | Serveur d'envoi email | `smtp.gmail.com` |
| **Port SMTP** | Port (25, 587, 465) | `587` (TLS) |
| **Utilisateur SMTP** | Compte email émetteur | `noreply@lycee.fr` |
| **Mot de Passe SMTP** | Mot de passe email | `********` |
| **TLS/SSL** | Chiffrement | `TLS` (recommandé) |
| **Email Expéditeur** | Nom affiché | `Korrigo PMF - Lycée Exemple` |

**Notifications Activables** :
- ✅ Nouvel utilisateur créé (envoi identifiants)
- ✅ Réinitialisation mot de passe
- ✅ Copie finalisée (notification à l'élève) - optionnel
- ✅ Examen publié (notification enseignants)

**Test Email** :
- Cliquer sur [Envoyer Email de Test]
- Vérifier réception sur votre boîte email

### 4.4 Stockage et Sauvegardes

**Chemin** : Dashboard → Paramètres → [Stockage]

| Paramètre | Description | Valeur |
|-----------|-------------|--------|
| **Chemin Média** | Dossier de stockage des PDF/images | `/app/media` (Docker) |
| **Espace Total** | Capacité totale du volume | `200 Go` (configurable) |
| **Espace Utilisé** | Espace actuellement occupé | `45 Go` |
| **Sauvegarde Auto** | Activation sauvegarde quotidienne | ✅ Activée |
| **Heure Sauvegarde** | Heure de déclenchement | `01:00` (1h du matin) |
| **Conservation** | Nombre de sauvegardes à conserver | `7 jours` |
| **Destination** | Emplacement sauvegarde | `/backups` (ou NAS) |

**Procédure de Sauvegarde Manuelle** :
1. Dashboard → Paramètres → [Stockage] → [Sauvegarder Maintenant]
2. Confirmation de la sauvegarde
3. **Temps Estimé** : 5-15 minutes (selon taille base de données)
4. **Télécharger** : Lien de téléchargement disponible après génération

**Restauration** :
- Voir [Section 7.5 - Restauration depuis Sauvegarde](#75-restauration-depuis-sauvegarde)

---

## 5. Monitoring et Logs

### 5.1 Tableau de Bord de Monitoring

**Chemin** : Dashboard → Monitoring

**Indicateurs en Temps Réel** :

```
┌────────────────────────────────────────────────────┐
│ Monitoring Système - Korrigo PMF                   │
├────────────────────────────────────────────────────┤
│                                                    │
│  🖥️ Serveur                                        │
│  ├─ CPU: 25% (4 cœurs)                             │
│  ├─ RAM: 4.2 Go / 8 Go (52%)                       │
│  ├─ Disque: 45 Go / 200 Go (22%)                   │
│  └─ Uptime: 15 jours 3h 42m                        │
│                                                    │
│  📊 Base de Données                                │
│  ├─ PostgreSQL: ✅ En ligne                        │
│  ├─ Connexions: 12 / 100                           │
│  ├─ Taille DB: 2.5 Go                              │
│  └─ Dernier Backup: Aujourd'hui 01:00             │
│                                                    │
│  🔄 Celery (Tâches Asynchrones)                    │
│  ├─ Workers: 2 actifs                              │
│  ├─ Tâches en file: 3                              │
│  ├─ Tâches réussies (24h): 145                     │
│  └─ Tâches échouées (24h): 2 ⚠️                    │
│                                                    │
│  📡 Redis (Cache)                                  │
│  ├─ Statut: ✅ En ligne                            │
│  ├─ Mémoire: 125 Mo / 512 Mo                       │
│  └─ Clés: 1,234                                    │
│                                                    │
│  [Rafraîchir] [Logs Détaillés] [Alertes]         │
└────────────────────────────────────────────────────┘
```

**Alertes Automatiques** :
- 🔴 **Critique** : Service hors ligne, disque > 90%, RAM > 95%
- 🟠 **Avertissement** : Disque > 80%, tâches échouées > 10%
- 🟢 **Info** : Sauvegarde réussie, mise à jour disponible

### 5.2 Logs d'Audit

**Chemin** : Dashboard → Logs → [Audit]

**Types d'Événements Enregistrés** :

| Action | Données Enregistrées | Exemple |
|--------|----------------------|---------|
| **LOGIN** | Utilisateur, IP, horodatage | `jdupont` connecté depuis `192.168.1.42` le 30/01/2026 14:32 |
| **LOGOUT** | Utilisateur, horodatage | `jdupont` déconnecté le 30/01/2026 15:12 |
| **CREATE_EXAM** | Auteur, nom examen, date | Admin `admin` a créé "Bac Blanc Maths TG" |
| **UPLOAD_PDF** | Auteur, examen, taille fichier | `admin` a uploadé 45 Mo pour "Bac Blanc Maths" |
| **IDENTIFY_COPY** | Opérateur, copie, élève | Secrétariat `secr01` a lié copie `A3F7` à Jean DUPONT |
| **LOCK_COPY** | Enseignant, copie, horodatage | `jdupont` a verrouillé copie `A3F7B2E1` |
| **UNLOCK_COPY** | Enseignant, copie, raison | `jdupont` a déverrouillé copie `A3F7B2E1` |
| **CREATE_ANN** | Enseignant, copie, type, page | `jdupont` a créé annotation COMMENT page 2 |
| **UPDATE_ANN** | Enseignant, annotation, modifications | `jdupont` a modifié annotation `ann-123` |
| **DELETE_ANN** | Enseignant, annotation | `jdupont` a supprimé annotation `ann-456` |
| **FINALIZE_COPY** | Enseignant, copie, note | `jdupont` a finalisé copie `A3F7` (note: 15/20) |
| **EXPORT_CSV** | Admin, examen, horodatage | `admin` a exporté CSV pour "Bac Blanc Maths" |
| **DOWNLOAD_PDF** | Utilisateur, copie | Élève `Jean DUPONT` a téléchargé sa copie |
| **CREATE_USER** | Admin, utilisateur créé | `admin` a créé utilisateur `sophie.martin` |
| **DELETE_USER** | Admin, utilisateur supprimé | `admin` a supprimé utilisateur `ancien.prof` |

**Interface de Consultation** :

```
┌────────────────────────────────────────────────────────────────┐
│ Logs d'Audit                                                   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ Filtres:                                                       │
│ [Date: 01/01/2026 - 31/01/2026] [Action: Tous] [User: Tous]   │
│ [Recherche: _______________] [Filtrer]                         │
│                                                                │
│ Date/Heure         | Action        | Utilisateur | Détails    │
│ ------------------|---------------|-------------|------------ │
│ 30/01 14:32:15    | LOGIN         | jdupont     | IP: 192... │
│ 30/01 14:35:42    | LOCK_COPY     | jdupont     | Copie A3F7 │
│ 30/01 14:48:21    | CREATE_ANN    | jdupont     | Comment P2 │
│ 30/01 15:05:33    | FINALIZE_COPY | jdupont     | Note: 15/20│
│ 30/01 15:12:01    | LOGOUT        | jdupont     | -          │
│                                                                │
│ [Précédent] Page 1/25 [Suivant]                               │
│ [Exporter CSV] [Télécharger Logs Bruts]                       │
└────────────────────────────────────────────────────────────────┘
```

**Export des Logs** :
- **Format** : CSV, JSON
- **Période** : Personnalisable (7 jours, 30 jours, année complète)
- **Usage** : Compliance RGPD, audit de sécurité

### 5.3 Logs Techniques (Erreurs)

**Chemin** : Dashboard → Logs → [Erreurs]

**Types de Logs** :
- **DEBUG** : Informations de débogage (désactivé en production)
- **INFO** : Événements normaux (ex: tâche Celery terminée)
- **WARNING** : Avertissements non critiques (ex: OCR échoué, retry)
- **ERROR** : Erreurs (ex: échec upload, corruption fichier)
- **CRITICAL** : Erreurs critiques (ex: base de données indisponible)

**Exemple de Log d'Erreur** :
```
[2026-01-30 14:35:42] ERROR [backend.processing.tasks]
Message: Échec de rasterisation du PDF
Exception: pdf2image.exceptions.PDFPageCountError: Unable to get page count.
File: /app/media/exams/exam_uuid.pdf
User: admin
Traceback: ...
```

**Actions de Résolution** :
- Vérifier l'intégrité du fichier PDF
- Consulter la section [Résolution de Problèmes](#9-résolution-de-problèmes)

---

## 6. Export de Données

### 6.1 Export CSV pour Pronote

**Objectif** : Exporter les notes finales pour import dans Pronote

**Chemin** : Dashboard → Examens → [Examen] → [Exporter CSV]

**Format de Sortie** :

```csv
INE,MATIERE,NOTE,COEFFICIENT
12345678901,MATHS,15.5,1.0
12345678902,MATHS,12.0,1.0
12345678903,MATHS,18.5,1.0
```

**Colonnes** :
- `INE` : Identifiant National Élève
- `MATIERE` : Code matière Pronote (ex: `MATHS`, `PHYS`, `HIST`)
- `NOTE` : Note sur 20 (format: `15.5`)
- `COEFFICIENT` : Coefficient (défini lors de la création de l'examen)

**Procédure** :
1. Vérifier que **toutes les copies sont finalisées** (statut `GRADED`)
2. Cliquer sur [Exporter CSV]
3. **Télécharger** le fichier `export_pronote_EXAMEN_DATE.csv`
4. **Importer dans Pronote** :
   - Pronote → Notes → Importer → CSV
   - Sélectionner le fichier
   - Valider la correspondance des colonnes
   - Importer

### 6.2 Export PDF en Masse

**Objectif** : Télécharger toutes les copies finalisées (PDF avec annotations)

**Chemin** : Dashboard → Examens → [Examen] → [Exporter PDF]

**Procédure** :
1. Cliquer sur [Exporter PDF]
2. **Génération** : Korrigo génère un ZIP contenant tous les PDF finaux
3. **Temps Estimé** : ~30 secondes pour 50 copies
4. **Télécharger** : `copies_finales_EXAMEN_DATE.zip`

**Structure du ZIP** :
```
copies_finales_BAC_BLANC_MATHS_20260315.zip
├─ DUPONT_Jean_TG2.pdf
├─ MARTIN_Sophie_TG2.pdf
├─ DURAND_Pierre_TG4.pdf
└─ ...
```

**Usage** :
- Archivage physique (gravure DVD, stockage NAS)
- Remise copies papier (impression si demandé)

### 6.3 Sauvegarde Complète de la Base de Données

**Chemin** : Dashboard → Paramètres → [Sauvegarde] → [Sauvegarder Maintenant]

**Contenu** :
- Base de données PostgreSQL complète (dump SQL)
- Fichiers média (PDF, images) - optionnel

**Format** : `.sql.gz` (compressé gzip)

**Procédure** :
1. Cliquer sur [Sauvegarder Maintenant]
2. Confirmation
3. **Génération** : ~5-15 minutes
4. **Télécharger** : `korrigo_backup_20260130_143542.sql.gz`

**Stockage Recommandé** :
- Serveur NAS dédié
- Cloud sécurisé (AWS S3, Google Cloud Storage)
- Disque dur externe (rotation hebdomadaire)

---

## 7. Opérations Avancées

### 7.1 Identification Manuelle de Copie

**Cas d'Usage** : Nom illisible, OCR échoué

**Chemin** : Dashboard → Identification → [Copie] → [Identification Manuelle]

**Procédure** :
1. Afficher l'image de l'en-tête
2. Déchiffrer le nom manuscrit
3. Rechercher l'élève :
   - Par nom : `DUPONT`
   - Par classe : `TG2`
   - Par INE : `12345678901`
4. Sélectionner l'élève correct
5. Valider

### 7.2 Fusion de Booklets (Agrafage Manuel)

**Cas d'Usage** : Copie incomplète (élève a rendu 2 fascicules séparés)

**Chemin** : Dashboard → Identification → [Agrafeuse Numérique]

**Interface** :
```
┌─────────────────────────────────────────────────┐
│ Agrafeuse Numérique                             │
├─────────────────────────────────────────────────┤
│                                                 │
│ Fascicules Disponibles (non identifiés):       │
│ ☐ Booklet 1 (P1-4) - OCR: "DUPONT"             │
│ ☐ Booklet 2 (P5-8) - OCR: Échec                │
│ ☐ Booklet 3 (P9-12) - OCR: "MARTIN"            │
│                                                 │
│ Sélectionner les fascicules à fusionner:       │
│ ☑ Booklet 1                                    │
│ ☑ Booklet 2                                    │
│                                                 │
│ Ordre: [↑ Booklet 1] [↓ Booklet 2]             │
│                                                 │
│ [Fusionner et Identifier]                      │
└─────────────────────────────────────────────────┘
```

**Procédure** :
1. Cocher les booklets à fusionner
2. Vérifier l'ordre (glisser-déposer pour réorganiser)
3. Cliquer sur [Fusionner et Identifier]
4. Identifier l'élève (voir section 7.1)

### 7.3 Déverrouiller une Copie (Force Unlock)

**Cas d'Usage** : Enseignant a fermé son navigateur sans finaliser, copie reste verrouillée

**V2 - Méthode recommandée (CorrectorDesk)** :
1. Ouvrir la copie bloquée dans le CorrectorDesk
2. Dans la **toolbar**, cliquer sur le bouton **"Déverrouiller"**
3. Confirmer l'action dans la modale de confirmation
4. La copie repasse au statut `READY`

**Méthode alternative (Dashboard)** :
**Chemin** : Dashboard → Examens → [Examen] → [Copies] → [Copie] → [Forcer Déverrouillage]

⚠️ **Avertissement** : Déverrouiller de force peut causer la perte de travail en cours.

**Procédure** :
1. Vérifier que l'enseignant n'est **plus en train de corriger**
2. Dashboard → Copies → [Copie Verrouillée]
3. Afficher les détails du verrou :
   ```
   Verrouillée par: Jean Dupont
   Depuis: 30/01/2026 14:35
   Expiration: 30/01/2026 15:05 (dans 12 minutes)
   ```
4. Cliquer sur [Forcer Déverrouillage]
5. Confirmation :
   ```
   Êtes-vous sûr de vouloir forcer le déverrouillage ?
   Cela peut entraîner la perte de travail en cours.
   [Annuler] [Confirmer]
   ```
6. La copie repasse au statut `READY`

**Événement d'Audit** : `FORCE_UNLOCK` enregistré via GradingEvent avec metadata completes (acteur, timestamp, copie, raison)

### 7.3b Réouverture d'une Copie Finalisée (Reopen)

**Cas d'Usage** : Une copie finalisée (statut `GRADED`) doit etre corrigee a nouveau (erreur de saisie, oubli d'annotation, etc.)

**Restriction d'Acces** : **Superuser uniquement** (ni admin standard, ni enseignant)

**V2 - Methode (CorrectorDesk)** :
1. Ouvrir la copie finalisee dans le CorrectorDesk
2. Dans la **toolbar**, cliquer sur le bouton **"Rouvrir"**
3. Confirmer l'action dans la modale de confirmation
4. La copie passe du statut `GRADED` au statut `READY`
5. Un enseignant peut alors la re-verrouiller et modifier les annotations/notes

**Transition de statut** : `GRADED` → `READY`

**Evenement d'Audit** : `REOPEN` enregistre via GradingEvent avec metadata completes :
- Acteur (superuser)
- Timestamp
- Copie concernee
- Statut precedent (`GRADED`)
- Statut cible (`READY`)

⚠️ **Attention** :
- Cette action est irreversible (la copie devra etre re-finalisee apres modification)
- Toutes les reouvertures sont tracees dans le journal d'audit
- Seuls les superusers ont acces a cette fonctionnalite

### 7.4 Nettoyer les Fichiers Orphelins

**Cas d'Usage** : Fichiers PDF/images non liés à une copie (uploads échoués, suppressions)

**Chemin** : Dashboard → Maintenance → [Nettoyer Orphelins]

**Procédure** :
1. Cliquer sur [Analyser]
2. Korrigo scanne le dossier `media/` et compare avec la base de données
3. **Résultat** :
   ```
   📁 Fichiers analysés: 1,234
   ✅ Fichiers liés: 1,180
   ⚠️ Fichiers orphelins: 54 (2.1 Go)
   ```
4. **Liste des Orphelins** :
   ```
   /media/exams/old_exam_uuid.pdf (45 Mo)
   /media/copies/deleted_copy_uuid.pdf (12 Mo)
   ...
   ```
5. **Options** :
   - [Télécharger Liste CSV] : Sauvegarder la liste avant suppression
   - [Supprimer Tous] : Suppression définitive
   - [Supprimer Sélection] : Cocher manuellement les fichiers à supprimer

⚠️ **Avertissement** : Suppression définitive, pas de corbeille.

### 7.5 Restauration depuis Sauvegarde

**Cas d'Usage** : Corruption base de données, panne serveur

⚠️ **ATTENTION** : Opération sensible, à effectuer uniquement en cas de nécessité.

**Prérequis** :
- Fichier de sauvegarde `.sql.gz` disponible
- Accès SSH au serveur (ou Docker exec)

**Procédure (via Docker)** :

1. **Arrêter les Services** :
   ```bash
   cd /chemin/vers/korrigo
   docker-compose stop backend celery
   ```

2. **Sauvegarder la Base Actuelle** (précaution) :
   ```bash
   docker-compose exec db pg_dump -U postgres korrigo > backup_avant_restauration.sql
   ```

3. **Restaurer la Sauvegarde** :
   ```bash
   gunzip < korrigo_backup_20260130.sql.gz | docker-compose exec -T db psql -U postgres -d korrigo
   ```

4. **Redémarrer les Services** :
   ```bash
   docker-compose start backend celery
   ```

5. **Vérification** :
   - Se connecter à Korrigo
   - Vérifier que les données sont présentes
   - Tester une action (ex: créer un examen de test)

6. **Restaurer les Fichiers Média** (si nécessaire) :
   ```bash
   # Copier depuis la sauvegarde NAS/cloud
   cp -r /backup/media/* /var/lib/docker/volumes/korrigo_media_volume/_data/
   ```

**Temps Estimé** : 15-30 minutes (selon taille base de données)

---

## 8. Maintenance

### 8.1 Tâches Quotidiennes (Automatisées)

| Tâche | Heure | Durée | Description |
|-------|-------|-------|-------------|
| **Sauvegarde Incrémentale** | 01:00 | 5 min | Sauvegarde des modifications depuis dernière sauvegarde complète |
| **Purge Logs > 1 An** | 02:00 | 2 min | Suppression des logs d'audit obsolètes (conformité RGPD) |
| **Nettoyage Sessions Expirées** | 03:00 | 1 min | Suppression des sessions Django expirées |
| **Nettoyage Verrous Expirés** | Toutes les 30 min | < 1 min | Suppression des verrous de copies expirés |

**Configuration** : Ces tâches sont exécutées automatiquement par Celery Beat.

### 8.2 Tâches Hebdomadaires

| Tâche | Jour | Durée | Responsable |
|-------|------|-------|-------------|
| **Sauvegarde Complète** | Dimanche 02:00 | 15 min | Automatique |
| **Vérification Sauvegardes** | Lundi matin | 10 min | Admin NSI |
| **Revue Logs d'Erreur** | Vendredi après-midi | 15 min | Admin NSI |
| **Surveillance Espace Disque** | Lundi matin | 5 min | Admin NSI |

**Checklist Hebdomadaire** (Admin NSI) :
- [ ] Vérifier que la sauvegarde de dimanche a réussi
- [ ] Tester la restauration d'une sauvegarde (mensuel)
- [ ] Consulter les logs d'erreur (si WARNING/ERROR)
- [ ] Vérifier l'espace disque (alerte si > 80%)
- [ ] Vérifier les tâches Celery échouées (si > 5)

### 8.3 Tâches Mensuelles

| Tâche | Période | Durée | Responsable |
|-------|---------|-------|-------------|
| **Mises à Jour de Sécurité** | 1er du mois | 1h | Admin NSI |
| **Test de Restauration** | 15 du mois | 30 min | Admin NSI |
| **Revue Comptes Inactifs** | Fin du mois | 20 min | Admin |
| **Analyse des KPI** | Fin du mois | 30 min | Comité Pilotage |

**Procédure de Mise à Jour** :
1. **Vérifier les Mises à Jour Disponibles** :
   - Consulter le [CHANGELOG.md](../../CHANGELOG.md)
   - Vérifier les correctifs de sécurité

2. **Sauvegarde Complète** :
   - Dashboard → Sauvegarde → [Sauvegarder Maintenant]

3. **Appliquer la Mise à Jour** (via Docker) :
   ```bash
   cd /chemin/vers/korrigo
   git pull origin main  # Si déploiement depuis Git
   docker-compose pull   # Télécharger nouvelles images
   docker-compose down
   docker-compose up -d
   ```

4. **Vérification** :
   - Tester la connexion
   - Vérifier une fonctionnalité clé (ex: créer examen)
   - Consulter les logs (erreurs ?)

5. **Rollback** (si problème) :
   - Restaurer la sauvegarde (voir section 7.5)

### 8.4 Tâches Trimestrielles

| Tâche | Période | Durée | Responsable |
|-------|---------|-------|-------------|
| **Audit de Sécurité** | Chaque trimestre | 2h | Admin NSI + Prestataire |
| **Revue RGPD** | Chaque trimestre | 1h | Admin + DPO |
| **Test PRA** (Simulation Panne) | Chaque trimestre | 2h | Équipe IT |
| **Formation de Rappel** | Avant chaque période d'examen | 1h | Référent Pédagogique |

**Test PRA** (Plan de Reprise d'Activité) :
1. **Simulation** : Arrêt brutal du serveur
2. **Objectif** : Restaurer le service sous 24h
3. **Mesure** : Temps réel de restauration
4. **Documentation** : Noter les points d'amélioration

### 8.5 Tâches Annuelles

| Tâche | Période | Durée | Responsable |
|-------|---------|-------|-------------|
| **Audit Complet** | Juin (fin d'année) | 1 jour | Externe (recommandé) |
| **Revue Documentation** | Juin | 2h | Admin NSI |
| **Mise à Jour Majeure** | Juillet (vacances) | 4h | Admin NSI |
| **Purge Données Obsolètes** | Juillet | 2h | Admin |

**Purge Annuelle** (Conformité RGPD) :
- Suppression des copies d'examens > 1 an
- Suppression des comptes élèves sortants (après fin de scolarité + 1 an)
- Archivage des notes (conservation 50 ans selon Code de l'Éducation)

---

## 9. Résolution de Problèmes

### 9.1 Service Indisponible

**Symptôme** : `Erreur 502 Bad Gateway` ou `Connexion refusée`

**Causes Possibles** :
1. Backend Django arrêté
2. Base de données hors ligne
3. Nginx mal configuré

**Diagnostic** :
```bash
# Vérifier statut des conteneurs
docker-compose ps

# Résultat attendu:
# backend    running
# db         running
# redis      running
# celery     running
```

**Résolution** :
```bash
# Si conteneur arrêté:
docker-compose start backend db redis celery

# Si erreur persistante, consulter les logs:
docker-compose logs backend --tail=50
```

### 9.2 Upload PDF Échoue

**Symptôme** : `Erreur lors de l'upload` ou `Fichier trop volumineux`

**Causes Possibles** :
1. Taille fichier > 50 Mo (limite par défaut)
2. PDF corrompu
3. Espace disque insuffisant

**Résolution** :

**1. Augmenter la Limite d'Upload** :
- Dashboard → Paramètres → [Général] → Taille Max Upload → `100 Mo`
- Sauvegarder

**2. Vérifier l'Intégrité du PDF** :
```bash
# Sur votre machine locale
pdfinfo fichier.pdf
# Si erreur → PDF corrompu, rescanner
```

**3. Vérifier l'Espace Disque** :
```bash
docker-compose exec backend df -h /app/media
# Si > 90% → nettoyer fichiers orphelins (section 7.4)
```

### 9.3 OCR Ne Reconnaît Pas les Noms

**Symptôme** : Tous les résultats OCR sont vides ou incohérents

**Causes Possibles** :
1. Scan de mauvaise qualité (résolution < 150 DPI)
2. En-tête mal positionné
3. Écriture trop illisible

**Résolution** :

**1. Améliorer la Qualité du Scan** :
- Augmenter la résolution : 200-300 DPI
- Utiliser le mode **Niveaux de Gris** (meilleur contraste)
- Nettoyer la vitre du scanner

**2. Vérifier la Zone de Détection** :
- L'en-tête doit être dans la **zone haute de la page** (premiers 15%)
- Format attendu : `Nom: DUPONT` ou `Élève: Jean DUPONT`

**3. Identifier Manuellement** :
- Si OCR échoue systématiquement, utiliser l'identification manuelle (section 7.1)

### 9.4 Copie Reste Verrouillée

**Symptôme** : `Cette copie est verrouillée par un autre utilisateur`

**Causes Possibles** :
1. Enseignant a fermé son navigateur sans finaliser
2. Crash du navigateur
3. Verrou non expiré (< 30 min)

**Résolution** :

**1. Attendre l'Expiration Automatique** :
- Les verrous expirent automatiquement après **30 minutes** d'inactivité
- Vérifier l'heure d'expiration dans les logs

**2. Forcer le Déverrouillage** (Admin uniquement) :
- Dashboard → Copies → [Copie] → [Forcer Déverrouillage]
- ⚠️ Risque de perte de travail en cours

**3. Contacter l'Enseignant** :
- Demander à l'enseignant de finaliser ou libérer la copie

### 9.5 Annotations Non Sauvegardées

**Symptôme** : Les annotations disparaissent après rechargement

**Causes Possibles** :
1. Perte de connexion réseau
2. Verrou de copie expiré
3. Problème de synchronisation

**Résolution** :

**1. Vérifier le Verrou** :
- L'enseignant doit avoir un verrou valide pour sauvegarder
- Si expiré : Reverrouiller la copie

**2. Récupération depuis localStorage** :
- Korrigo sauvegarde automatiquement dans le navigateur
- Actualiser la page → Modal de récupération apparaît
- Cliquer sur [Récupérer le Brouillon]

**3. Prévention** :
- Activer l'autosave (activé par défaut toutes les 30s)
- Vérifier la connexion réseau avant de commencer
- Sauvegarder manuellement régulièrement (Ctrl+S)

### 9.6 Export CSV Pronote Vide

**Symptôme** : Le CSV exporté est vide ou incomplet

**Causes Possibles** :
1. Aucune copie finalisée (statut `GRADED`)
2. Filtre de classe incorrect
3. Problème de mapping INE

**Résolution** :

**1. Vérifier l'État des Copies** :
- Dashboard → Examens → [Examen] → [Suivi]
- **Vérifier** : Toutes les copies doivent être `GRADED` (✅)

**2. Vérifier les INE** :
- Dashboard → Étudiants → [Liste]
- **Vérifier** : Tous les élèves ont un INE valide (11 caractères)
- Si manquant : Mettre à jour manuellement ou réimporter CSV Pronote

**3. Tester avec un Élève** :
- Finaliser une copie de test
- Exporter CSV
- Vérifier la présence de la ligne

### 9.7 Tâches Celery Bloquées

**Symptôme** : Les PDF ne sont pas traités (rasterisation bloquée)

**Diagnostic** :
```bash
# Vérifier les workers Celery
docker-compose exec celery celery -A core inspect active

# Résultat: liste des tâches en cours
```

**Résolution** :

**1. Redémarrer Celery** :
```bash
docker-compose restart celery
```

**2. Purger la File de Tâches** (si bloquage persistant) :
```bash
docker-compose exec celery celery -A core purge
# Attention: cela supprime toutes les tâches en attente
```

**3. Vérifier Redis** :
```bash
docker-compose exec redis redis-cli ping
# Résultat attendu: PONG
```

---

## Conclusion

Ce guide couvre l'ensemble des opérations d'administration de Korrigo PMF. Pour toute question non traitée ici, consultez :

### Documents Complémentaires

- [Guide Administrateur Lycée (Non-Technique)](./GUIDE_ADMINISTRATEUR_LYCEE.md)
- [Gestion des Utilisateurs (Détaillé)](./GESTION_UTILISATEURS.md)
- [Procédures Opérationnelles](./PROCEDURES_OPERATIONNELLES.md)
- [Manuel Sécurité](../security/MANUEL_SECURITE.md)
- [FAQ](../support/FAQ.md)
- [Guide de Dépannage](../support/DEPANNAGE.md)

### Support Technique

- **Documentation Technique** : [docs/TECHNICAL_MANUAL.md](../TECHNICAL_MANUAL.md)
- **API Reference** : [docs/API_REFERENCE.md](../API_REFERENCE.md)
- **GitHub Issues** : https://github.com/korrigo/korrigo-pmf/issues (si open-source)

---

**Dernière Mise à Jour** : 30 janvier 2026  
**Version du Document** : 1.0.0
