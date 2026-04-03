# Procédures Opérationnelles - Korrigo PMF

> **Version**: 2.0.0
> **Date**: 23 Mars 2026
> **Public**: Administrateurs, Personnel administratif, Équipe pédagogique  
> **Langue**: Français (non-technique)

> **Note de cohérence**
> Ce document contient encore des formulations héritées d’anciens workflows.
> La machine d’états active est `READY → IN_PROGRESS → FINALIZED`.
> Pour les sauvegardes et le diagnostic de prod, utiliser d’abord [RUNBOOK_PRODUCTION](../deployment/RUNBOOK_PRODUCTION.md).

Ce document décrit toutes les procédures opérationnelles quotidiennes, hebdomadaires et exceptionnelles pour l'utilisation de Korrigo PMF dans un établissement scolaire.

---

## 📋 Table des Matières

1. [Opérations Quotidiennes](#1-opérations-quotidiennes)
2. [Cycle de Vie Complet d'un Examen](#2-cycle-de-vie-complet-dun-examen)
3. [Onboarding Utilisateurs](#3-onboarding-utilisateurs)
4. [Offboarding Utilisateurs](#4-offboarding-utilisateurs)
5. [Maintenance Régulière](#5-maintenance-régulière)
6. [Gestion du Changement](#6-gestion-du-changement)
7. [Assurance Qualité](#7-assurance-qualité)
8. [Reporting et Suivi](#8-reporting-et-suivi)
9. [Procédures d'Urgence](#9-procédures-durgence)

---

## 1. Opérations Quotidiennes

### 1.1 Vérification Santé du Système

**Responsable** : Admin NSI / Proviseur Adjoint  
**Fréquence** : Chaque matin (9h)  
**Durée** : 5 minutes

#### Checklist Quotidienne

| Vérification | Critère de Succès | Action si Échec |
|--------------|-------------------|-----------------|
| **Service En Ligne** | Accès à `https://korrigo.lycee.fr` → Page d'accueil affichée | Redémarrer services (voir [9.1](#91-service-indisponible)) |
| **Connexion** | Login avec compte admin → Dashboard affiché | Vérifier logs d'erreur |
| **Espace Disque** | < 80% utilisé | Nettoyer fichiers orphelins (voir [Maintenance](#5-maintenance-régulière)) |
| **RAM** | < 90% utilisée | Redémarrer conteneur backend |
| **Sauvegarde** | Sauvegarde nocturne OK (01:00) | Vérifier logs Celery, relancer sauvegarde manuelle |
| **Tâches Celery** | Aucune tâche bloquée > 1h | Redémarrer Celery |

**Procédure** :
1. Accéder au Dashboard Korrigo
2. Vérifier le **Widget Monitoring** :
   ```
   ┌────────────────────────────────┐
   │ Statut Système                 │
   ├────────────────────────────────┤
   │ ✅ Serveur: En ligne           │
   │ ✅ Base de données: Opérationnelle │
   │ ✅ Espace disque: 45% utilisé  │
   │ ✅ Sauvegarde: Aujourd'hui 01:03 │
   │ ⚠️ Celery: 2 tâches en attente │
   └────────────────────────────────┘
   ```
3. Si ⚠️ ou ❌ : Consulter les logs (Dashboard → Logs → [Erreurs])
4. **Documenter** tout incident dans un journal de bord (Excel ou cahier)

### 1.2 Support Utilisateurs

**Responsable** : Professeur Référent / Admin  
**Fréquence** : En continu (heures de bureau)  
**Canaux** : Email, téléphone, bureau physique

#### Temps de Réponse (SLA Interne)

| Type de Demande | Délai de Réponse | Délai de Résolution |
|-----------------|------------------|---------------------|
| **P1 - Bloquant** (impossible de corriger) | 2h | 4h |
| **P2 - Gênant** (ralentissement, bug mineur) | 8h | 24h |
| **P3 - Question** | 24h | 48h |

#### Procédure de Support

1. **Réception Demande** :
   - Email : `support.korrigo@lycee.fr`
   - Téléphone : 01 23 45 67 89
   - En personne : Bureau administration

2. **Triage** :
   - **P1** : Traitement immédiat
   - **P2/P3** : Ajout à la file de support (outil de ticketing ou Excel)

3. **Diagnostic** :
   - Reproduire le problème
   - Consulter la [FAQ](../support/FAQ.md)
   - Consulter le [Guide de Dépannage](../support/DEPANNAGE.md)

4. **Résolution** :
   - Appliquer la solution
   - Vérifier avec l'utilisateur
   - Documenter dans la base de connaissances

5. **Clôture** :
   - Email de confirmation à l'utilisateur
   - Mise à jour du ticket (statut : résolu)

### 1.3 Surveillance Examens en Cours

**Responsable** : Admin / Proviseur Adjoint  
**Fréquence** : Quotidienne (en période d'examen)  
**Durée** : 10 minutes

#### Indicateurs à Surveiller

**Dashboard → Examens → [Examen en cours] → [Suivi]**

```
┌──────────────────────────────────────────────────┐
│ Bac Blanc Mathématiques TG - 15/03/2026          │
├──────────────────────────────────────────────────┤
│ Progression: [████████████░░░░░░] 60% (30/50)   │
│                                                  │
│ Copies Corrigées: 30                             │
│ Copies En Cours: 15                              │
│ Copies À Corriger: 5                             │
│ Copies Bloquées (> 30 min): 2 ⚠️                │
│                                                  │
│ Temps Moyen: 18 min/copie                        │
│ Deadline: J-3 (avant export Pronote)             │
└──────────────────────────────────────────────────┘
```

**Actions** :
- **Copies Bloquées** : Contacter l'enseignant (a-t-il oublié de finaliser ?)
- **Deadline Proche** : Relancer les enseignants en retard
- **Progression < 50% à J-3** : Alerte Proviseur Adjoint

---

## 2. Cycle de Vie Complet d'un Examen

### 2.1 Phase 1 : Planification (J-7)

**Responsable** : Admin / Enseignant Chef de Département  
**Durée** : 30 minutes

#### Checklist de Planification

- [ ] **Créer l'examen dans Korrigo** :
  - Nom : `Bac Blanc Mathématiques TG`
  - Date : `15/03/2026`
  - Matière : `Mathématiques`
  - Classes : `TG2`, `TG4`

- [ ] **Définir le Barème** :
  - Créer la structure (exercices → questions → points)
  - Vérifier que le total = note finale (ex: 20 points)

- [ ] **Assigner les Correcteurs** :
  - Vérifier que les enseignants ont des comptes actifs
  - Communiquer la deadline de correction (ex: J+7)

- [ ] **Préparer le Scan** :
  - Réserver le scanner A3 (si partagé)
  - Vérifier stock de toner/encre
  - Préparer une clé USB (si scan sur machine dédiée)

#### Exemple de Communication (Email aux Enseignants)

```
Objet: Bac Blanc Mathématiques TG - 15/03/2026 - Correction Numérique

Bonjour à tous,

Le Bac Blanc de Mathématiques TG aura lieu le 15 mars 2026.

Les copies seront scannées et disponibles pour correction numérique sur Korrigo à partir du 16 mars (après-midi).

Deadline de correction: 22 mars 2026
Barème: Voir Korrigo (Exercice 1: 10 pts, Exercice 2: 8 pts, Exercice 3: 2 pts)

Équipe de correction:
- Jean Dupont: TG2 (25 copies)
- Sophie Martin: TG4 (25 copies)

Cordialement,
Administration Korrigo PMF
```

### 2.2 Phase 2 : Jour de l'Examen (J)

**Responsable** : Secrétariat / Surveillants  
**Durée** : 3h + 1h (scan)

#### Déroulement

**Avant l'Examen** :
- [ ] Distribution des copies papier aux élèves
- [ ] Vérification que les élèves notent **leur nom lisiblement** en haut de la copie
- [ ] Rappel : Écriture **en majuscules** pour le nom (facilite l'OCR)

**Pendant l'Examen** :
- [ ] Surveillance normale
- [ ] Collecte des copies en fin d'examen

**Après l'Examen (Scan)** :
- [ ] Tri des copies (ordre alphabétique recommandé, mais pas obligatoire)
- [ ] Scan en **mode A3 recto-verso** :
  - Scanner : Canon DR-C230 (ou équivalent)
  - Résolution : 200-300 DPI
  - Format : PDF
  - Nom fichier : `Scan_BacBlanc_Maths_TG_20260315.pdf`
- [ ] Vérification rapide : Ouvrir le PDF, vérifier que toutes les pages sont lisibles
- [ ] Sauvegarde temporaire : Copier le PDF sur clé USB + serveur réseau

### 2.3 Phase 3 : Ingestion et Traitement (J+1, matin)

**Responsable** : Admin  
**Durée** : 15 minutes (+ 10 minutes traitement automatique)

#### Procédure d'Upload

1. **Accéder à Korrigo** :
   - Dashboard → Examens → [Bac Blanc Mathématiques TG] → [Upload PDF]

2. **Sélectionner le PDF** :
   - Glisser-déposer `Scan_BacBlanc_Maths_TG_20260315.pdf`
   - Taille : 45 Mo (100 pages)

3. **Validation** :
   - Korrigo vérifie le fichier
   - ✅ Format PDF
   - ✅ Taille < 50 Mo
   - ✅ Lisible

4. **Upload** :
   - Cliquer sur [Uploader]
   - Barre de progression : ~30 secondes

5. **Traitement Automatique** (Celery) :
   ```
   ┌───────────────────────────────────────────┐
   │ Traitement en cours...                    │
   ├───────────────────────────────────────────┤
   │ ✅ Rasterisation: 100/100 pages           │
   │ ✅ Découpage A3 → A4: 50 fascicules       │
   │ ✅ Détection en-têtes: 50/50              │
   │ ✅ OCR noms: 42/50 (84% confiance)        │
   │                                           │
   │ Temps: 8 min 32 s                         │
   └───────────────────────────────────────────┘
   ```

6. **Vérification** :
   - Dashboard → Examens → [Examen] → [Booklets]
   - Vérifier : 50 fascicules créés (1 par copie)

### 2.4 Phase 4 : Identification des Copies (J+1, après-midi)

**Responsable** : Secrétariat  
**Durée** : 2h pour 50 copies (~2 min/copie)

#### Procédure "Video-Coding"

**Chemin** : Dashboard → Examens → [Examen] → [Identifier les Copies]

**Interface** :
```
┌─────────────────────────────────────────────┐
│ Copie 1/50 - Booklet BK-001                 │
├─────────────────────────────────────────────┤
│ [Image en-tête avec nom manuscrit]          │
│                                             │
│ 🔍 OCR: "DUPONT" (confiance: 87%)          │
│                                             │
│ Suggestions:                                │
│ ○ Jean DUPONT - TG2 (INE: 12345678901)      │
│ ○ Marie DUPONT - TG4 (INE: 12345678902)     │
│                                             │
│ [Valider] [Saisie Manuelle] [Passer]       │
└─────────────────────────────────────────────┘
```

**Workflow** :
1. **Copie Lisible + OCR Correct** :
   - Vérifier visuellement que le nom OCR correspond à l'image
   - Sélectionner l'élève correct (vérifier la classe)
   - Cliquer sur [Valider]

2. **OCR Incorrect ou Nom Illisible** :
   - Cliquer sur [Saisie Manuelle]
   - Déchiffrer le nom manuscrit
   - Rechercher l'élève :
     - Par nom : `DURAND`
     - Par classe : `TG2`
   - Sélectionner et valider

3. **Fascicule Incomplet** (pages manquantes) :
   - Cliquer sur [Passer] temporairement
   - En fin d'identification : Utiliser l'**Agrafeuse Numérique**
   - Dashboard → Identification → [Agrafeuse] → Fusionner les booklets

**Cas Spéciaux** :

| Cas | Action |
|-----|--------|
| **Copie Anonyme** (pas de nom) | Contacter le surveillant, vérifier place de l'élève |
| **Doublon** (même nom, 2 copies) | Identifier les 2, marquer "Copie de remplacement" |
| **Élève Absent de la Base** | Ajouter manuellement (Dashboard → Étudiants → [+ Nouvel Étudiant]) |

### 2.5 Phase 5 : Distribution aux Correcteurs (Automatique)

**Responsable** : Système (automatique)  
**Durée** : Instantané

Une fois toutes les copies identifiées :
- ✅ Korrigo génère automatiquement un **numéro d'anonymat** (ex: `A3F7B2E1`)
- ✅ Le nom de l'élève est **masqué** sur la copie numérique
- ✅ Les copies passent au statut **READY** (prêtes à corriger)
- ✅ Les enseignants voient les copies dans leur interface

**Notification** (optionnel, si SMTP configuré) :
- Email automatique aux enseignants : `Les copies du Bac Blanc Maths TG sont disponibles pour correction`

### 2.6 Phase 6 : Correction Numérique (J+2 à J+7)

**Responsable** : Enseignants  
**Durée** : 15-20 min/copie × 50 copies = 12-16h réparties sur 5 jours

#### Workflow Enseignant (Résumé)

1. **Connexion** : `https://korrigo.lycee.fr` → Login enseignant
2. **Sélectionner Examen** : Dashboard → [Bac Blanc Maths TG]
3. **Lister Copies** : [Voir les Copies] → Liste des copies READY
4. **Verrouiller Copie** : Cliquer sur une copie → [Commencer la Correction]
5. **Corriger** :
   - Lire la copie (PDF viewer)
   - Ajouter annotations (commentaires, surlignage, erreurs, bonus)
   - Attribuer les points par question (sidebar)
6. **Finaliser** : [Finaliser la Copie] → Note calculée automatiquement → PDF final généré
7. **Copie Suivante** : Retour à la liste → Prendre une autre copie

**Support Enseignant** :
- [Guide Enseignant](../users/GUIDE_ENSEIGNANT.md)
- Support : Professeur Référent (téléphone, email)

### 2.7 Phase 7 : Finalisation et Contrôle (J+8)

**Responsable** : Admin  
**Durée** : 30 minutes

#### Vérifications Avant Export

**Dashboard → Examens → [Examen] → [Suivi]**

**Checklist** :
- [ ] **Toutes les copies corrigées** : Progression = 100%
- [ ] **Aucun verrou résiduel** : pas de `CopyLock` actif inattendu et pas de copies `IN_PROGRESS` abandonnées
- [ ] **Notes cohérentes** : Vérifier qu'aucune note aberrante (ex: 25/20)
- [ ] **Génération PDF Finaux** : Cliquer sur [Générer PDF Finaux]
  ```
  ┌─────────────────────────────────────────┐
  │ Génération PDF Finaux en cours...       │
  ├─────────────────────────────────────────┤
  │ [████████████████████] 100% (50/50)     │
  │                                         │
  │ ✅ 50 PDF générés                       │
  │ Temps: 2 min 15 s                       │
  └─────────────────────────────────────────┘
  ```

**Contrôle Qualité (Échantillon)** :
1. Télécharger 3-5 PDF finaux aléatoirement
2. Vérifier :
   - ✅ Nom de l'élève réaffiché (démasquage)
   - ✅ Annotations visibles et lisibles
   - ✅ Note affichée correctement

### 2.8 Phase 8 : Export et Publication (J+9)

**Responsable** : Admin  
**Durée** : 20 minutes

#### Export CSV vers Pronote

1. **Exporter** :
   - Dashboard → Examens → [Examen] → [Exporter CSV]
   - Télécharger `export_pronote_BacBlancMaths_20260323.csv`

2. **Vérifier le CSV** :
   ```csv
   INE,MATIERE,NOTE,COEFFICIENT
   12345678901,MATHS,15.5,1.0
   12345678902,MATHS,12.0,1.0
   12345678903,MATHS,18.5,1.0
   ```

3. **Importer dans Pronote** :
   - Pronote → Notes → [Importer] → Sélectionner le CSV
   - Vérifier la correspondance des colonnes
   - Cliquer sur [Importer]
   - **Résultat** : `✅ 50 notes importées`

#### Activation Portail Élève

1. **Activer la Consultation** :
   - Dashboard → Examens → [Examen] → [Paramètres]
   - Cocher **"Portail élève activé"**
   - Sauvegarder

2. **Notification Élèves** (optionnel) :
   - Email automatique (si SMTP configuré) : `Vos copies du Bac Blanc Maths sont disponibles`
   - Ou affichage Pronote : `Consultez vos copies sur Korrigo`

3. **Vérification** :
   - Se connecter avec un compte élève test
   - Vérifier que la copie est bien visible et téléchargeable

### 2.9 Phase 9 : Archivage (1 an après)

**Responsable** : Admin  
**Durée** : 1h (annuel)

#### Procédure de Purge (Conformité RGPD)

**Rappel Légal** :
- **Copies d'examens** : Conservation 1 an (Code de l'Éducation)
- **Notes** : Conservation 50 ans (registres scolaires)

**Procédure** :
1. **Identifier les Examens à Archiver** :
   - Dashboard → Examens → [Filtrer: Date < 365 jours]
   - Exemple : Tous les examens de l'année scolaire 2025-2026 (en juillet 2027)

2. **Export des Notes** (Archivage Long Terme) :
   - Pour chaque examen : [Exporter CSV]
   - Sauvegarder sur NAS ou archive physique (50 ans)

3. **Suppression des PDF** :
   - Dashboard → Examens → [Examen] → [Supprimer PDF]
   - Confirmation :
     ```
     ⚠️ Supprimer les PDF de cet examen ?
     - 50 copies élèves (PDF finaux)
     - 1 PDF source (scan original)

     Les notes seront conservées en base de données.
     [Annuler] [Confirmer]
     ```

4. **Vérification** :
   - Les notes restent visibles dans Korrigo (table `Exam`, `Copy`)
   - Les PDF sont supprimés (libère l'espace disque)

---

## 3. Onboarding Utilisateurs

### 3.1 Nouvel Enseignant

**Responsable** : Admin / Professeur Référent  
**Durée** : 1h30 (création compte + formation)

#### Checklist d'Accueil

**J-7 (avant arrivée)** :
- [ ] Créer le compte dans Korrigo
  - Username : `prenom.nom`
  - Rôle : Enseignant
  - Mot de passe temporaire : Généré automatiquement

- [ ] Envoyer email de bienvenue avec identifiants

**Jour J (premier jour)** :
- [ ] Accueil physique
- [ ] Remettre la documentation :
  - [Guide Enseignant](../users/GUIDE_ENSEIGNANT.md) (format PDF imprimé)
  - Fiche mémo (1 page A4) : Connexion, verrouillage, annotations, finalisation

**J+1 à J+7 (formation)** :
- [ ] Session de formation individuelle (1h) :
  - Démonstration sur copie de test
  - Pratique guidée (corriger 2-3 copies)
  - Q&A

- [ ] Assigner un "buddy" (enseignant expérimenté) pour support

**J+30 (suivi)** :
- [ ] Entretien de retour d'expérience
- [ ] Questionnaire de satisfaction (anonyme)

### 3.2 Nouveaux Élèves (Rentrée Scolaire)

**Responsable** : Secrétariat / Admin  
**Durée** : 2h (import 650 élèves)

#### Procédure de Rentrée

**Août (préparation)** :
- [ ] Exporter la base élèves depuis Pronote :
  - Pronote → Ressources → Élèves → [Exporter CSV]
  - Colonnes : INE, Nom, Prénom, Classe, Email

- [ ] Nettoyer le CSV :
  - Vérifier que tous les INE font 11 caractères
  - Compléter les INE courts avec des zéros : `123456789` → `00123456789`
  - Vérifier l'encodage UTF-8

**Septembre (import)** :
- [ ] Importer le CSV dans Korrigo :
  - Dashboard → Étudiants → [Importer CSV]
  - Suivre la procédure (voir [Gestion Utilisateurs](./GESTION_UTILISATEURS.md#3-import-en-masse))

- [ ] Vérifier l'import :
  - Nombre d'élèves = Effectif total
  - Pas d'erreur d'INE
  - Classes correctes

**Octobre (communication)** :
- [ ] Informer les élèves via Pronote :
  - Message : `Consultez vos copies corrigées sur Korrigo : https://korrigo.lycee.fr`
  - Identifiant : INE (11 chiffres)
  - Mot de passe : Nom de famille (majuscules)

- [ ] Affichage physique (panneau CDI, vie scolaire) :
  - QR Code vers Korrigo
  - Instructions de connexion

---

## 4. Offboarding Utilisateurs

### 4.1 Départ d'un Enseignant

**Responsable** : Admin  
**Durée** : 30 min

#### Procédure de Départ

**J-30 (préavis)** :
- [ ] Identifier les corrections en cours
- [ ] Transférer les examens non terminés à un autre enseignant (si possible)

**Dernier Jour** :
- [ ] Vérifier qu'aucune copie n'est verrouillée par cet enseignant
- [ ] Désactiver le compte :
  - Dashboard → Utilisateurs → [Enseignant] → [Modifier]
  - Décocher "Compte actif"
  - Sauvegarder

**J+365 (1 an après)** :
- [ ] Supprimer le compte (après délai légal de conservation) :
  - Dashboard → Utilisateurs → [Enseignant] → [Supprimer]
  - Confirmer

### 4.2 Élèves Sortants (Fin d'Année)

**Responsable** : Admin / Secrétariat  
**Durée** : 3h (purge annuelle)

#### Procédure de Fin d'Année

**Juillet N (après résultats du Bac)** :
- [ ] Exporter la liste des élèves de Terminale :
  - Dashboard → Étudiants → [Filtrer: Classe = "TERMINALE"] → [Exporter CSV]
  - Sauvegarder `eleves_terminale_2026.csv` (archivage NAS)

- [ ] Désactiver les comptes Terminale :
  - Dashboard → Étudiants → [Sélection Multiple]
  - Cocher tous les élèves de Terminale
  - [Actions] → [Désactiver les comptes]

**Juillet N+1 (1 an après)** :
- [ ] Supprimer les comptes Terminale N :
  - Dashboard → Étudiants → [Filtrer: Classe = "TERMINALE", Désactivé = Oui]
  - [Sélection Multiple] → [Supprimer Définitivement]
  - Confirmer

⚠️ **Important** : Les notes sont conservées en base de données (50 ans), seuls les comptes élèves sont supprimés.

---

## 5. Maintenance Régulière

### 5.1 Hebdomadaire

**Responsable** : Admin NSI  
**Jour** : Lundi matin (9h)  
**Durée** : 30 min

#### Checklist Hebdomadaire

- [ ] **Vérifier Sauvegarde Complète** (dimanche 02:00) :
  - Dashboard → Paramètres → [Sauvegardes]
  - Statut dernière sauvegarde : ✅ Succès
  - Si échec : Consulter logs, relancer manuellement

- [ ] **Revue Logs d'Erreur** :
  - Dashboard → Logs → [Erreurs] → [Filtrer: 7 derniers jours]
  - Si > 10 erreurs : Analyser les causes

- [ ] **Surveillance Espace Disque** :
  - Dashboard → Monitoring → Disque
  - Si > 80% : Nettoyer fichiers orphelins (Dashboard → Maintenance → [Nettoyer Orphelins])

- [ ] **Surveillance Tâches Celery** :
  - Dashboard → Monitoring → Celery
  - Si tâches échouées > 5 : Investiguer

### 5.2 Mensuelle

**Responsable** : Admin NSI  
**Jour** : 1er lundi du mois  
**Durée** : 2h

#### Checklist Mensuelle

- [ ] **Mises à Jour de Sécurité** :
  - Vérifier mises à jour disponibles (voir [CHANGELOG.md](../../CHANGELOG.md))
  - Appliquer les correctifs de sécurité
  - Procédure : [Guide Admin - Mise à Jour](./GUIDE_UTILISATEUR_ADMIN.md#83-mises-à-jour-et-évolutions)

- [ ] **Test de Restauration** :
  - Télécharger une sauvegarde aléatoire
  - Tester la restauration en environnement de test (si disponible)
  - Documenter le résultat

- [ ] **Revue Comptes Inactifs** :
  - Dashboard → Utilisateurs → [Filtrer: Dernière connexion > 6 mois]
  - Contacter les utilisateurs inactifs
  - Désactiver si confirmé (départ, congé longue durée)

- [ ] **Analyse KPI** :
  - Nombre d'examens créés ce mois
  - Nombre de copies corrigées
  - Temps moyen de correction
  - Incidents de sécurité
  - Générer rapport (Excel) pour comité de pilotage

### 5.3 Trimestrielle

**Responsable** : Comité de Pilotage  
**Durée** : 2h

#### Checklist Trimestrielle

- [ ] **Audit de Sécurité** :
  - Revue des accès (qui a des droits admin ?)
  - Vérification politique de mots de passe
  - Revue des logs d'audit (tentatives de connexion échouées)

- [ ] **Revue RGPD** :
  - Vérifier conformité durées de conservation
  - Traiter les demandes d'exercice de droits (accès, rectification)
  - Mettre à jour le registre des traitements

- [ ] **Test PRA** (Plan de Reprise d'Activité) :
  - Simuler une panne serveur
  - Mesurer le temps de restauration
  - Documenter les points d'amélioration

- [ ] **Formation de Rappel** :
  - Session de 1h pour les enseignants
  - Rappel bonnes pratiques, nouvelles fonctionnalités

### 5.4 Annuelle

**Responsable** : Direction + Admin + DPO  
**Durée** : 1 jour

#### Checklist Annuelle

- [ ] **Audit Complet** (externe recommandé) :
  - Audit de sécurité technique
  - Audit de conformité RGPD
  - Pentest (si budget disponible)

- [ ] **Revue Documentation** :
  - Mettre à jour tous les guides utilisateurs
  - Vérifier que les captures d'écran sont à jour
  - Traduire si multilinguisme (futur)

- [ ] **Mise à Jour Majeure** (période de vacances) :
  - Planifier 4h de maintenance
  - Appliquer la nouvelle version
  - Tester exhaustivement
  - Former les utilisateurs aux nouveautés

- [ ] **Purge Données Obsolètes** :
  - Supprimer copies > 1 an (voir [Phase 9](#29-phase-9--archivage-1-an-après))
  - Supprimer comptes élèves sortants (après délai légal)
  - Archiver notes (conservation 50 ans)

---

## 6. Gestion du Changement

### 6.1 Processus de Demande de Changement

#### Qui Peut Demander ?

- Enseignants (via Professeur Référent)
- Administrateurs
- Direction
- Élèves (via CPE)

#### Procédure

1. **Soumettre une Demande** :
   - Email à `korrigo.evolution@lycee.fr`
   - Décrire le besoin, le problème, la solution souhaitée

2. **Triage** (Comité de Pilotage) :
   - **Urgence** : Faible / Moyenne / Haute
   - **Impact** : Faible / Moyen / Élevé
   - **Complexité** : Simple / Moyen / Complexe

3. **Priorisation** :
   - Matrice Urgence × Impact
   - Backlog : Liste des changements planifiés

4. **Planification** :
   - Si changement mineur : Déploiement mensuel
   - Si changement majeur : Déploiement annuel (vacances d'été)

5. **Déploiement** :
   - Communication 2 semaines avant
   - Formation (si nécessaire)
   - Déploiement hors heures de cours
   - Suivi post-déploiement (2 semaines)

### 6.2 Types de Changements

#### Changement d'Urgence (Correctif de Sécurité)

**Délai** : Immédiat à 48h

**Procédure** :
1. **Notification** : Email urgent à tous les admins
2. **Sauvegarde** : Snapshot complet avant intervention
3. **Déploiement** : Hors heures de cours (ou nuit si critique)
4. **Communication** : Email post-déploiement + vérification

#### Changement Standard (Amélioration)

**Délai** : Planifié (mensuel/trimestriel)

**Procédure** :
1. **Notification** : 2 semaines avant
2. **Formation** : Session courte (30 min) si nécessaire
3. **Déploiement** : Week-end ou vacances
4. **Suivi** : Questionnaire de satisfaction après 1 mois

#### Changement Majeur (Nouvelle Fonctionnalité)

**Délai** : Planifié (annuel, vacances d'été)

**Procédure** :
1. **Analyse d'Impact** : Quelles équipes concernées ?
2. **Phase Pilote** : Test avec 5-10 enseignants volontaires
3. **Formation Complète** : 1h30 par groupe
4. **Déploiement Progressif** : Département par département
5. **Support Renforcé** : Hotline pendant 2 semaines

### 6.3 Rollback (Retour Arrière)

**Quand** : Problème majeur détecté après déploiement

**Procédure** :
1. **Décision** : Admin NSI + Proviseur Adjoint (dans les 2h)
2. **Communication** : Email urgent : `Retour à la version précédente en cours`
3. **Exécution** :
   ```bash
   # Restaurer snapshot
   docker-compose down
   docker-compose restore --snapshot=pre-update-20260315
   docker-compose up -d
   ```
4. **Vérification** : Tester connexion + fonctionnalités clés
5. **Post-Mortem** : Analyser les causes, documenter

---

## 7. Assurance Qualité

### 7.1 Contrôles Qualité Réguliers

**Fréquence** : Chaque examen

#### Checklist Qualité Examen

**Avant Correction** :
- [ ] PDF scanné lisible (pas de pages floues, noires)
- [ ] Tous les fascicules créés (nombre = copies attendues)
- [ ] OCR fonctionne (> 70% de confiance)

**Pendant Correction** :
- [ ] Aucune copie bloquée > 1h (sauf pause enseignant)
- [ ] Annotations sauvegardées (pas de perte de données)

**Après Correction** :
- [ ] Toutes les copies finalisées (0 copies `READY` ou `IN_PROGRESS`)
- [ ] Notes cohérentes (min/max dans la plage attendue)
- [ ] PDF finaux lisibles (échantillon de 5 copies)

### 7.2 Indicateurs de Performance (KPI)

#### KPI Techniques

| Indicateur | Objectif | Mesure | Fréquence |
|------------|----------|--------|-----------|
| **Uptime** | > 99% | Disponibilité mensuelle | Mensuel |
| **Temps Réponse Moyen** | < 2s | Temps de chargement page | Hebdomadaire |
| **Taux d'Erreur** | < 1% | % de requêtes en erreur | Hebdomadaire |
| **Espace Disque** | < 80% | % disque utilisé | Quotidien |

#### KPI Fonctionnels

| Indicateur | Objectif | Mesure | Fréquence |
|------------|----------|--------|-----------|
| **Taux OCR Réussi** | > 80% | % copies identifiées sans correction manuelle | Par examen |
| **Temps Moyen Correction** | < 20 min | Temps total / nombre copies | Par examen |
| **Taux Finalisation J+7** | > 90% | % examens finalisés sous 7 jours | Mensuel |
| **Satisfaction Enseignants** | > 4/5 | Enquête (note sur 5) | Semestriel |

#### KPI Sécurité

| Indicateur | Objectif | Mesure | Fréquence |
|------------|----------|--------|-----------|
| **Incidents de Sécurité** | 0 | Nombre d'incidents graves | Mensuel |
| **Tentatives Connexion Échouées** | < 5% | % échecs / total connexions | Hebdomadaire |
| **Comptes Admin** | < 5 | Nombre de comptes superuser | Mensuel |

### 7.3 Amélioration Continue

**Méthode** : Cycle PDCA (Plan-Do-Check-Act)

#### Trimestre N

1. **Plan** : Identifier 3 points d'amélioration (retours enseignants, KPI)
2. **Do** : Mettre en œuvre les améliorations
3. **Check** : Mesurer l'impact (KPI avant/après)
4. **Act** : Standardiser si succès, ajuster si échec

#### Exemple d'Amélioration Continue

**Problème Identifié** : Temps moyen de correction = 25 min (objectif : 20 min)

**Cause** : Enseignants perdent du temps à chercher les outils d'annotation

**Action** : Ajouter des raccourcis clavier (Ctrl+C = Commentaire, Ctrl+E = Erreur)

**Résultat** : Temps moyen de correction = 18 min ✅

**Standardisation** : Mettre à jour le guide enseignant avec les raccourcis

---

## 8. Reporting et Suivi

### 8.1 Rapports Mensuels

**Destinataire** : Comité de Pilotage  
**Format** : PDF (1 page A4)

#### Contenu

**Statistiques d'Usage** :
- Nombre d'examens créés : 12
- Nombre de copies corrigées : 450
- Nombre d'utilisateurs actifs : 45 enseignants, 650 élèves

**KPI** :
- Uptime : 99.8%
- Temps moyen correction : 18 min
- Satisfaction enseignants : 4.2/5

**Incidents** :
- Nombre d'incidents : 2 (P3 - mineurs)
- Résolution moyenne : 18h

**Actions du Mois** :
- Mise à jour sécurité appliquée (15/03)
- Formation 5 nouveaux enseignants (20/03)

### 8.2 Rapports Trimestriels

**Destinataire** : Direction + Conseil d'Administration  
**Format** : Présentation PowerPoint (10 slides)

#### Contenu

1. **Vue d'Ensemble** : Synthèse trimestre
2. **Usage** : Graphiques d'évolution (examens, corrections)
3. **KPI** : Tableau de bord complet
4. **Satisfaction** : Résultats enquête enseignants/élèves
5. **Incidents** : Analyse des problèmes rencontrés
6. **RGPD** : État de conformité
7. **Sécurité** : Audit, vulnérabilités
8. **Budget** : Coûts réels vs. budget prévisionnel
9. **Perspectives** : Améliorations prévues trimestre N+1
10. **Recommandations** : Décisions à prendre

### 8.3 Rapport Annuel

**Destinataire** : Conseil d'Administration, Rectorat  
**Format** : Document PDF (20-30 pages)

#### Contenu Complet

**Executive Summary** :
- Bilan année scolaire
- Chiffres clés
- ROI (Retour sur Investissement)

**Statistiques Annuelles** :
- 120 examens créés
- 5 400 copies corrigées
- 650 élèves, 45 enseignants

**Analyse KPI** :
- Évolution mois par mois
- Comparaison objectifs vs. réalisé

**Conformité** :
- Audit RGPD complet
- Audit de sécurité

**Satisfaction** :
- Enquête enseignants : 4.3/5
- Enquête élèves : 4.1/5
- Témoignages

**Perspectives** :
- Axes d'amélioration
- Roadmap année N+1
- Budget prévisionnel

---

## 9. Procédures d'Urgence

### 9.1 Service Indisponible

**Symptôme** : Impossible d'accéder à Korrigo

**Gravité** : P1 (Critique)  
**Délai de Résolution** : 4h

#### Procédure

1. **Diagnostic** (5 min) :
   ```bash
   # Vérifier statut des conteneurs
   docker-compose ps

   # Si conteneur arrêté :
   docker-compose logs backend --tail=50
   ```

2. **Action Immédiate** (10 min) :
   - Redémarrer les services :
   ```bash
   docker-compose restart backend db redis celery
   ```

3. **Vérification** (2 min) :
   - Accéder à `https://korrigo.lycee.fr`
   - Tester connexion admin
   - Vérifier dashboard

4. **Si Échec** (30 min) :
   - Restaurer snapshot de la veille :
   ```bash
   docker-compose down
   docker-compose restore --snapshot=daily-20260329
   docker-compose up -d
   ```

5. **Communication** :
   - Email à tous les utilisateurs : `Service temporairement indisponible, résolution en cours`
   - Mise à jour toutes les heures

6. **Post-Incident** :
   - Analyser les logs
   - Documenter la cause
   - Plan d'action préventif

### 9.2 Violation de Données Suspectée

**Symptôme** : Accès non autorisé détecté, fuite de données

**Gravité** : P0 (Critique)  
**Délai de Notification CNIL** : 72h

#### Procédure d'Urgence

1. **Immédiat (< 1h)** :
   - [ ] **Isolation** : Arrêter le serveur (empêcher aggravation)
   ```bash
   docker-compose down
   ```
   - [ ] **Notification Direction** : Appel téléphonique Proviseur + DPO
   - [ ] **Préservation Preuves** : Copier logs avant toute modification

2. **Investigation (< 4h)** :
   - [ ] Analyser les logs d'audit : Qui ? Quoi ? Quand ?
   - [ ] Identifier la portée : Combien de personnes concernées ?
   - [ ] Type de données : Copies ? Notes ? Données personnelles ?

3. **Confinement (< 8h)** :
   - [ ] Corriger la faille de sécurité
   - [ ] Changer tous les mots de passe admin
   - [ ] Révoquer toutes les sessions actives

4. **Notification (< 72h)** :
   - [ ] **Notification CNIL** :
     - En ligne : https://www.cnil.fr/notifier-une-violation
     - Formulaire : Décrire l'incident, les données, les mesures prises
   - [ ] **Notification Personnes Concernées** (si risque élevé) :
     - Email aux élèves/enseignants concernés
     - Expliquer la nature de la violation
     - Conseils de sécurité (changement mot de passe)

5. **Post-Mortem (< 1 mois)** :
   - [ ] Rapport d'incident complet
   - [ ] Plan d'action correctif
   - [ ] Formation équipe (sensibilisation)
   - [ ] Audit de sécurité externe

### 9.3 Perte de Données (Corruption Base)

**Symptôme** : Données incohérentes, base de données corrompue

**Gravité** : P1 (Critique)  
**Délai de Résolution** : 4h

#### Procédure

1. **Arrêt Immédiat** :
   ```bash
   docker-compose stop backend celery
   ```

2. **Évaluation** (30 min) :
   - Déterminer l'étendue de la corruption
   - Identifier la dernière sauvegarde saine

3. **Restauration** (2h) :
   ```bash
   # Restaurer sauvegarde
   gunzip < backup_20260328_0100.sql.gz | docker-compose exec -T db psql -U postgres -d korrigo
   ```

4. **Récupération Partielle** (si nécessaire) :
   - Récupérer les corrections récentes depuis localStorage navigateur
   - Demander aux enseignants de re-finaliser les copies en cours

5. **Communication** :
   - Informer les utilisateurs de la restauration
   - Expliquer la perte potentielle de données (depuis dernière sauvegarde)

6. **Prévention** :
   - Augmenter la fréquence de sauvegarde (toutes les 6h)
   - Tester les sauvegardes hebdomadairement

---

## 10. Procedures V2 : Deverrouillage Force et Reouverture

### 10.1 Procedure de Deverrouillage Force d'une Copie

**Responsable** : Administrateur
**Cas d'usage** : Une copie reste indisponible après interruption (verrou `CopyLock` résiduel ou statut `IN_PROGRESS`)

#### Etapes

1. **Verification prealable** :
   - Confirmer que l'enseignant n'est plus en train de corriger la copie
   - Contacter l'enseignant si possible pour eviter la perte de travail

2. **Deverrouillage via CorrectorDesk** :
   - Ouvrir la copie bloquee dans le CorrectorDesk
   - Cliquer sur le bouton **"Deverrouiller"** dans la toolbar
   - Confirmer dans la modale de confirmation

3. **Resultat** :
   - La copie repasse au statut `READY`
   - L'evenement `FORCE_UNLOCK` est enregistre dans `GradingEvent` avec les metadata completes

4. **Post-action** :
   - Informer l'enseignant que la copie est de nouveau disponible
   - Verifier dans les logs d'audit que l'evenement a ete correctement enregistre

### 10.2 Procedure de Reouverture d'une Copie Finalisee

**Responsable** : Superuser uniquement
**Cas d'usage** : Une copie finalisee (`FINALIZED`) doit etre modifiee (erreur de notation, oubli d'annotation, contestation justifiee)

#### Etapes

1. **Verification prealable** :
   - Confirmer la legitimite de la demande (erreur de saisie, oubli, etc.)
   - S'assurer que les notes n'ont pas encore ete exportees vers Pronote

2. **Reouverture via CorrectorDesk** :
   - Ouvrir la copie finalisee dans le CorrectorDesk
   - Cliquer sur le bouton **"Rouvrir"** dans la toolbar (visible uniquement pour les superusers)
   - Confirmer dans la modale de confirmation

3. **Resultat** :
   - La copie passe du statut `FINALIZED` au statut `READY`
   - L'evenement `REOPEN` est enregistre dans `GradingEvent` avec les metadata completes
   - L'enseignant peut alors re-verrouiller la copie et effectuer les modifications

4. **Post-action** :
   - Informer l'enseignant que la copie est de nouveau disponible pour correction
   - S'assurer que l'enseignant re-finalise la copie apres modification
   - Si les notes avaient ete exportees, prevoir un re-export apres la nouvelle finalisation

---

## Conclusion

Ces procédures opérationnelles garantissent une utilisation fluide, sécurisée et conforme de Korrigo PMF dans un établissement scolaire. La rigueur dans leur application assure :

- ✅ Continuité de service
- ✅ Qualité des données
- ✅ Conformité RGPD
- ✅ Satisfaction des utilisateurs

### Documents Complémentaires

- [Guide Administrateur Lycée](./GUIDE_ADMINISTRATEUR_LYCEE.md)
- [Guide Utilisateur Admin](./GUIDE_UTILISATEUR_ADMIN.md)
- [Gestion des Utilisateurs](./GESTION_UTILISATEURS.md)
- [Manuel Sécurité](../security/MANUEL_SECURITE.md)
- [FAQ](../support/FAQ.md)

---

**Derniere Mise a Jour** : 23 Mars 2026
**Version du Document** : 2.0.0
