# Foire Aux Questions (FAQ) - Korrigo PMF

> **Version**: 2.0.0
> **Date**: 23 Mars 2026
> **Public**: Tous les utilisateurs  
> **Langue**: Français

> **Note de cohérence**
> Certains exemples anciens de ce guide peuvent encore employer la terminologie historique `GRADED` ou `LOCKED`.
> La terminologie canonique actuelle est `READY`, `IN_PROGRESS`, `FINALIZED`.
> Pour les procédures de backup et de production, se référer à [RUNBOOK_PRODUCTION](../deployment/RUNBOOK_PRODUCTION.md).

Documentation des questions fréquemment posées et leurs réponses pour tous les utilisateurs de la plateforme Korrigo PMF.

---

## 📋 Table des Matières

1. [Questions Générales](#questions-générales)
2. [FAQ Administrateur](#faq-administrateur)
3. [FAQ Enseignant](#faq-enseignant)
4. [FAQ Secrétariat](#faq-secrétariat)
5. [FAQ Élève](#faq-élève)
6. [FAQ Technique](#faq-technique)
7. [Contact et Support](#contact-et-support)

---

## Questions Générales

### Qu'est-ce que Korrigo PMF ?

**Réponse**: Korrigo PMF est une plateforme de correction numérique d'examens conçue pour les lycées. Elle permet de :
- Numériser des copies d'examens papier
- Corriger les copies de manière numérique avec des annotations vectorielles
- Gérer l'identification et l'anonymisation des copies
- Exporter les notes vers Pronote
- Permettre aux élèves de consulter leurs copies corrigées en ligne

### Qui peut accéder à la plateforme ?

**Réponse**: La plateforme est accessible aux quatre profils utilisateurs suivants :
- **Administrateurs** : Gestion complète du système, utilisateurs, examens
- **Enseignants** : Correction des copies qui leur sont assignées
- **Secrétariat** : Identification des copies et gestion des carnets
- **Élèves** : Consultation de leurs copies corrigées uniquement

Chaque utilisateur reçoit des identifiants personnels lors de la création de son compte.

### Mes données sont-elles sécurisées ?

**Réponse**: Oui, absolument. Korrigo PMF respecte le RGPD et les recommandations de la CNIL :
- Toutes les données sont chiffrées en transit (HTTPS) et au repos
- L'accès est contrôlé par authentification et permissions strictes
- Les copies sont anonymisées pendant la correction
- Les logs d'audit tracent toutes les actions sensibles
- Les sauvegardes sont automatiques et sécurisées
- Les données sont hébergées localement dans le lycée

Pour plus de détails, consultez la [Politique de Confidentialité](../legal/POLITIQUE_CONFIDENTIALITE.md).

### Quels navigateurs sont compatibles ?

**Réponse**: Navigateurs recommandés (versions récentes) :
- ✅ **Google Chrome** (recommandé pour les performances)
- ✅ **Mozilla Firefox** (bonne alternative)
- ✅ **Microsoft Edge** (basé sur Chromium)
- ⚠️ **Safari** (fonctionne mais performances moindres pour les gros PDF)
- ❌ **Internet Explorer** (non supporté)

**Configuration minimale** :
- Connexion Internet stable
- Résolution d'écran : 1280×720 minimum (1920×1080 recommandé pour la correction)
- JavaScript activé
- Cookies activés

### Comment obtenir un compte ?

**Réponse**: 
- **Enseignants** : Contactez l'administrateur du lycée qui créera votre compte. Vous vous connecterez avec votre adresse email **@ert.tn**
- **Secrétariat** : L'administrateur créera votre compte avec un nom d'utilisateur (**secretariat**) et un mot de passe
- **Administrateurs** : Compte créé avec un nom d'utilisateur (**admin**) et un mot de passe
- **Élèves** : Vos comptes sont créés automatiquement lors de l'import depuis Pronote. Vous vous connecterez avec votre adresse email **@ert.tn**
- **Identifiants** : Vous recevrez vos identifiants par email ou en main propre

### J'ai oublié mon mot de passe

**Réponse**: 
1. Sur la page de connexion, cliquez sur "Mot de passe oublié ?"
2. Saisissez votre adresse email
3. Suivez les instructions reçues par email
4. Si vous ne recevez pas d'email sous 10 minutes, vérifiez vos spams
5. En cas de problème, contactez l'administrateur du lycée

**Note** :
- Les élèves et enseignants se connectent avec leur adresse email **@ert.tn**
- Les administrateurs et secrétariat utilisent leur nom d'utilisateur (admin ou secretariat)

### La plateforme est-elle accessible depuis mon domicile ?

**Réponse**: 
**Oui**, la plateforme Korrigo est accessible depuis n'importe où avec une connexion Internet :
- ✅ Depuis le lycée
- ✅ Depuis votre domicile
- ✅ Depuis tout lieu disposant d'une connexion Internet

**Tous les profils** (administrateurs, enseignants, secrétariat, élèves) peuvent accéder à la plateforme à distance.

**Sécurité** : L'accès est protégé par authentification (identifiants personnels) et HTTPS.

### Les données sont-elles conservées combien de temps ?

**Réponse**: Conformément au RGPD et aux recommandations de l'Éducation Nationale :
- **Copies d'examens** : 1 an après la fin de l'année scolaire
- **Notes et résultats** : 5 ans (obligation légale)
- **Logs d'audit** : 1 an
- **Comptes utilisateurs** : Tant que l'utilisateur est actif dans l'établissement

Les données sont supprimées automatiquement après expiration. Voir [Gestion des Données](../security/GESTION_DONNEES.md) pour les détails.

---

## FAQ Administrateur

### Comment créer un nouvel utilisateur ?

**Réponse**: 
1. Connectez-vous avec votre compte administrateur
2. Allez dans **Admin > Utilisateurs**
3. Cliquez sur **"Créer un utilisateur"**
4. Remplissez les champs requis :
   - Nom d'utilisateur (unique)
   - Email
   - Rôle (Admin, Teacher, Student)
   - Mot de passe initial (l'utilisateur devra le changer à la première connexion)
5. Cliquez sur **"Enregistrer"**

**Création en masse** : Utilisez l'import CSV pour créer plusieurs utilisateurs d'un coup. Voir [Gestion des Utilisateurs](../admin/GESTION_UTILISATEURS.md).

### Comment importer des élèves depuis Pronote ?

**Réponse**:
1. Dans Pronote, exportez la liste des élèves au format CSV :
   - Fichier > Exporter > Élèves
   - Colonnes requises : INE, Nom, Prénom, Classe, Email
2. Dans Korrigo, allez dans **Admin > Élèves > Importer CSV**
3. Sélectionnez le fichier CSV
4. Vérifiez le mapping des colonnes
5. Cliquez sur **"Importer"**
6. Vérifiez le rapport d'import (succès/erreurs)

**Format CSV attendu** :
```csv
INE,Nom,Prenom,Classe,Email
1234567890A,DUPONT,Jean,TG1,jean.dupont@ert.tn
```

### Comment sauvegarder la base de données ?

**Réponse**:
**Méthode automatique** (recommandée) :
- Les sauvegardes automatiques sont configurées quotidiennement à 2h00
- Emplacement : `/backups/` (dans le conteneur) ou NAS configuré
- Rétention : 30 jours

**Sauvegarde manuelle** :
```bash
# Se connecter au serveur
ssh admin@serveur-korrigo

# Lancer la sauvegarde
docker-compose exec backend python manage.py backup_database

# Vérifier
ls -lh /path/to/backups/
```

**Restauration** : Voir [Guide Administrateur](../admin/GUIDE_UTILISATEUR_ADMIN.md#sauvegarde-et-restauration).

### Que faire si une migration échoue ?

**Réponse**:
**Diagnostic** :
1. Consultez les logs : `docker-compose logs backend`
2. Identifiez l'erreur de migration
3. Vérifiez l'intégrité de la base de données

**Résolution** :
```bash
# 1. Restaurer une sauvegarde récente
docker-compose exec backend python manage.py restore_backup <date>

# 2. Annuler la dernière migration
docker-compose exec backend python manage.py migrate <app_name> <previous_migration>

# 3. Réessayer
docker-compose exec backend python manage.py migrate
```

**Prévention** : Toujours sauvegarder avant une migration. Voir [Dépannage](DEPANNAGE.md#migration-failures).

### Comment désactiver un utilisateur qui a quitté l'établissement ?

**Réponse**:
**Important** : Ne jamais supprimer un utilisateur qui a corrigé des copies (pour l'intégrité des logs d'audit).

**Procédure** :
1. **Admin > Utilisateurs**
2. Recherchez l'utilisateur
3. Cliquez sur **"Modifier"**
4. Décochez **"Compte actif"**
5. Ajoutez une note : "Départ - [date]"
6. **"Enregistrer"**

L'utilisateur ne pourra plus se connecter, mais ses actions passées restent tracées.

### Comment attribuer des copies à un enseignant ?

**Réponse**:
**Méthode automatique** (recommandée) :
- Lors de la création de l'examen, configurez la **"Matière"** et les **"Enseignants responsables"**
- Les copies seront automatiquement visibles par ces enseignants

**Attribution manuelle** :
1. **Admin > Examens > [Examen] > Copies**
2. Sélectionnez les copies
3. Actions > **"Attribuer à un enseignant"**
4. Choisissez l'enseignant
5. **"Valider"**

### Comment surveiller l'avancement des corrections ?

**Réponse**:
**Dashboard Administrateur** :
1. **Admin > Dashboard**
2. Consultez les indicateurs :
   - Total de copies à corriger
   - Copies corrigées (%)
   - Copies en cours (`IN_PROGRESS`)
   - Copies en attente (READY)
   - Moyenne de temps par copie

**Par examen** :
1. **Admin > Examens > [Examen]**
2. Onglet **"Statistiques"**
3. Vue détaillée par correcteur

**Rapports** : Exportez un rapport CSV pour analyse externe.

### Comment gérer les fichiers orphelins ?

**Réponse**:
**Détection** :
```bash
docker-compose exec backend python manage.py find_orphaned_files
```

**Nettoyage** :
```bash
# Dry-run (simulation)
docker-compose exec backend python manage.py cleanup_orphaned_files --dry-run

# Nettoyage réel (attention : irréversible)
docker-compose exec backend python manage.py cleanup_orphaned_files --confirm
```

**Automatisation** : Configurer un cron mensuel. Voir [Procédures Opérationnelles](../admin/PROCEDURES_OPERATIONNELLES.md#maintenance-régulière).

### Comment mettre à jour Korrigo vers une nouvelle version ?

**Réponse**:
**Avant de commencer** :
- ⚠️ Planifiez la mise à jour hors période de correction
- 📦 Sauvegardez la base de données
- 📖 Lisez les notes de version (CHANGELOG)

**Procédure** :
```bash
# 1. Sauvegarde
docker-compose exec backend python manage.py backup_database

# 2. Télécharger la nouvelle version
git pull origin main  # Ou télécharger le package

# 3. Arrêter les services
docker-compose down

# 4. Reconstruire les images
docker-compose build

# 5. Relancer
docker-compose up -d

# 6. Appliquer les migrations
docker-compose exec backend python manage.py migrate

# 7. Vérifier
docker-compose logs -f
```

**Rollback si problème** : Voir [Dépannage - Rollback](DEPANNAGE.md#rollback-migration).

### Comment configurer l'export vers Pronote ?

**Réponse**:
**Configuration** :
1. **Admin > Paramètres > Intégrations > Pronote**
2. Configurez :
   - Format CSV Pronote (colonnes : INE, Note, Coefficient, etc.)
   - Mapping des champs
   - Encodage (UTF-8 recommandé)
3. **"Tester la configuration"**
4. **"Enregistrer"**

**Export manuel** :
1. **Admin > Examens > [Examen]**
2. Onglet **"Export"**
3. **"Exporter vers Pronote (CSV)"**
4. Téléchargez le fichier
5. Importez-le dans Pronote

**Automatisation** : Configurez un export automatique après finalisation de toutes les copies.

### Comment debloquer une copie verrouillee ?

**Reponse**:
Une copie peut être temporairement indisponible soit parce qu’un `CopyLock` actif existe encore, soit parce qu’elle est restée en statut `IN_PROGRESS` après interruption d’une correction.

**Procedure (V2)** :
1. Ouvrir la copie dans le **CorrectorDesk**
2. Cliquer sur le bouton **"Deverrouiller"** dans la toolbar admin
3. Confirmer l'action dans la modale

Le verrou `CopyLock` est supprimé. Si la copie était restée bloquée en `IN_PROGRESS`, il faut ensuite la réouvrir vers `READY` avec la procédure de récupération prévue.

### Comment corriger une copie deja finalisee ?

**Reponse**:
Une copie finalisée (`FINALIZED`) n’est plus modifiable en usage normal. Seul un administrateur autorisé peut la rouvrir.

**Procedure (V2)** :
1. Ouvrir la copie dans le **CorrectorDesk**
2. Cliquer sur le bouton **"Rouvrir"** dans la toolbar (visible uniquement pour les superusers)
3. Confirmer l'action
4. La copie passe de `FINALIZED` à `READY`
5. L'enseignant peut alors reprendre la correction

Un evenement `REOPEN` est enregistre dans le journal d'audit avec toutes les metadata.

---

## FAQ Enseignant

### Je ne peux pas verrouiller une copie, pourquoi ?

**Réponse**:
**Causes possibles** :
1. **Copie déjà verrouillée** par un autre enseignant
   - Message : "Cette copie est actuellement verrouillée par [Nom]"
   - **Solution** : Attendez que le collègue termine ou contactez-le
   - L'administrateur peut forcer le déverrouillage si nécessaire

2. **Copie déjà finalisée** (status = `FINALIZED`)
   - Message : "Cette copie a déjà été corrigée"
   - **Solution** : Vous ne pouvez plus la modifier (sauf si l'admin réouvre la copie)

3. **Problème de connexion réseau**
   - Message : "Erreur réseau"
   - **Solution** : Vérifiez votre connexion Internet, rafraîchissez la page

4. **Session expirée**
   - Message : "Session expirée, veuillez vous reconnecter"
   - **Solution** : Reconnectez-vous

### Mes annotations ont disparu, que faire ?

**Réponse**:
**Diagnostic** :
1. **Rafraîchissez la page** (F5) : Les annotations sont peut-être juste masquées
2. **Vérifiez le statut de sauvegarde** : Icône en haut à droite
   - ✅ Vert : Sauvegardé
   - 🔄 Orange : En cours de sauvegarde
   - ❌ Rouge : Erreur de sauvegarde

**Si les annotations sont réellement perdues** :
1. **Vérifiez la console navigateur** (F12) : Y a-t-il des erreurs ?
2. **Contactez l'administrateur** avec :
   - Nom de l'examen
   - Numéro de la copie
   - Heure approximative de la perte
   - Capture d'écran de l'erreur

**Prévention** :
- ⏱️ L'enregistrement automatique se fait toutes les 30 secondes
- 💾 Sauvegardez manuellement régulièrement (Ctrl+S)
- 🔌 Évitez de fermer brutalement l'onglet
- 🌐 Vérifiez votre connexion réseau

### Comment déverrouiller une copie sans la finaliser ?

**Réponse**:
**Scénario 1 : Vous avez verrouillé mais voulez faire une pause**
- **Bouton "Libérer le verrou"** en haut à droite
- Vos annotations sont sauvegardées (status = DRAFT)
- Un autre enseignant peut prendre le relais

**Scénario 2 : Vous avez quitté sans déverrouiller (fermeture navigateur)**
- Le verrou expire automatiquement après **30 minutes d'inactivité**
- L'administrateur peut forcer le déverrouillage si urgent

**Note** : Ne fermez jamais brutalement le navigateur pendant une correction, utilisez toujours "Libérer le verrou".

### Puis-je modifier une copie après l'avoir finalisée ?

**Réponse**:
**Non, par défaut** : Une fois finalisée (status = `FINALIZED`), la copie n’est plus modifiable pour garantir l'intégrité.

**Exception - Réouverture par l'administrateur** :
1. Contactez l'administrateur
2. Expliquez la raison (erreur de saisie, oubli, etc.)
3. L'administrateur peut **réinitialiser le statut** (`FINALIZED` → `READY`)
4. Vous pourrez alors re-verrouiller et modifier
5. ⚠️ **Traçabilité** : Toutes les actions sont loggées (audit)

**Bonnes pratiques** :
- ✅ Relisez avant de finaliser
- ✅ Vérifiez le total des points
- ✅ Vérifiez que toutes les questions sont annotées

### Comment utiliser les raccourcis clavier ?

**Réponse**:
**Raccourcis disponibles** :

| Raccourci | Action |
|-----------|--------|
| **Ctrl+S** | Sauvegarder manuellement |
| **Ctrl+Z** | Annuler dernière annotation |
| **Ctrl+Y** | Refaire |
| **C** | Mode Commentaire |
| **H** | Mode Surlignage |
| **E** | Mode Erreur |
| **B** | Mode Bonus |
| **Suppr** | Supprimer annotation sélectionnée |
| **Échap** | Désélectionner |
| **+** / **-** | Zoom in/out |
| **Espace** | Main (déplacement) |

**Activer/désactiver** : Cliquez sur l'icône clavier (⌨️) en haut à droite.

### Le PDF met trop de temps à charger, que faire ?

**Réponse**:
**Optimisations** :
1. **Qualité d'affichage** : Réduisez la résolution (Paramètres > Qualité : "Standard" au lieu de "Haute")
2. **Navigateur** : Utilisez Chrome (meilleure performance que Firefox/Safari pour les PDF)
3. **Connexion** : Vérifiez votre débit Internet
4. **RAM** : Fermez les autres onglets et applications

**Si le problème persiste** :
- Contactez l'administrateur : Le PDF source peut être trop lourd (> 50 MB)
- Solution : L'admin peut re-compresser le PDF ou découper en plusieurs parties

### Comment signaler une copie illisible ou un problème d'identification ?

**Réponse**:
**Depuis l'interface de correction** :
1. Cliquez sur **"Signaler un problème"** (🚩)
2. Choisissez le type :
   - Copie illisible (scan de mauvaise qualité)
   - Mauvaise identification (nom incorrect)
   - Pages manquantes
   - Autre problème
3. Ajoutez un commentaire explicatif
4. **"Envoyer"**

L'administrateur sera notifié et pourra corriger le problème.

### Puis-je corriger depuis une tablette ?

**Réponse**:
**Oui, mais avec limitations** :
- ✅ Lecture des copies : OK
- ✅ Ajout de commentaires texte : OK
- ⚠️ Annotations dessinées : Difficile (stylet recommandé)
- ❌ Performance : Moins fluide que sur ordinateur

**Configuration recommandée** :
- Tablette 10 pouces minimum
- Stylet capacitif
- Navigateur Chrome ou Safari
- Connexion WiFi stable

**Alternative** : Utilisez l'ordinateur pour les annotations graphiques, la tablette pour les commentaires texte uniquement.

### Comment assurer la cohérence de mes notes ?

**Réponse**:
**Bonnes pratiques** :
1. **Barème** : Consultez régulièrement le barème affiché dans le panneau latéral
2. **Annotations standardisées** : Utilisez les mêmes symboles/couleurs pour les mêmes types d'erreurs
3. **Commentaires types** : Créez des commentaires pré-enregistrés pour les erreurs récurrentes
4. **Pauses** : Faites des pauses régulières pour éviter la fatigue
5. **Révision** : Relisez les premières copies corrigées après avoir terminé (pour ajuster si nécessaire)

**Statistiques** : Le systeme calcule votre moyenne, mediane, ecart-type pour detecter les incoherences.

### Comment marquer rapidement Vrai/Faux sur les copies ?

**Reponse**:
La V2 introduit les **boutons V/X** dans la barre d'outils du CorrectorDesk :
1. Selectionnez l'outil **V** (Vrai) ou **X** (Faux) dans la toolbar
2. Cliquez sur la zone de la copie a annoter
3. Un tampon vert (V) ou rouge (X) est appose directement sur la copie
4. Cela accelere considerablement la correction des QCM et exercices vrai/faux

### Comment voir le bareme en meme temps que la copie ?

**Reponse**:
La V2 propose la **Vue Scindee** (Split View) :
1. Cliquer sur le bouton **"Split"** dans la toolbar du CorrectorDesk
2. L'ecran se divise en deux panneaux : la copie a gauche, le bareme a droite
3. Les deux panneaux sont navigables independamment
4. Pour revenir a la vue normale, cliquer de nouveau sur le bouton **"Split"**

---

## FAQ Secretariat

### L'OCR ne reconnaît pas le nom de l'élève, que faire ?

**Réponse**:
**Identification manuelle** :
1. Dans l'interface d'identification, cliquez sur **"Identification manuelle"**
2. Saisissez le nom de l'élève dans la barre de recherche
3. Sélectionnez l'élève dans la liste
4. Validez

**Améliorer la reconnaissance OCR** :
- Demandez aux élèves d'écrire lisiblement en **MAJUSCULES**
- Utilisez un modèle d'en-tête standardisé
- Vérifiez la qualité du scan (300 DPI minimum)

**Si le nom est vraiment illisible** :
- Comparez avec d'autres indices (classe, numéro de place)
- Contactez l'enseignant responsable de la surveillance
- En dernier recours : Marquez la copie comme "Anonyme" et l'enseignant pourra identifier via l'écriture

### Comment fusionner des carnets (booklets) ?

**Réponse**:
**Scénario** : Un élève a rendu sa copie sur plusieurs carnets agrafés.

**Procédure** :
1. Allez dans **Identification > Carnets**
2. Sélectionnez les carnets à fusionner (ex : Carnet 5 et Carnet 12)
3. Cliquez sur **"Fusionner"** (🔗)
4. Vérifiez l'ordre des pages dans l'aperçu
5. Réorganisez si nécessaire (glisser-déposer)
6. Cliquez sur **"Confirmer la fusion"**

Le système crée une nouvelle copie unique avec toutes les pages.

### Un élève n'apparaît pas dans la base de données, pourquoi ?

**Réponse**:
**Causes possibles** :
1. **Élève nouvel arrivant** : Non présent dans l'export Pronote
   - **Solution** : Demandez à l'admin de l'ajouter manuellement ou refaites un import Pronote

2. **Erreur de saisie du nom** : Vous avez mal orthographié
   - **Solution** : Essayez des variantes (avec/sans accent, nom composé, etc.)

3. **Élève d'une autre classe** : Pas dans la liste filtrée
   - **Solution** : Désactivez le filtre "Classe" pour chercher dans toute la base

4. **Problème d'import** : L'élève était mal formaté dans le CSV
   - **Solution** : Vérifiez les logs d'import, contactez l'admin

### Comment gérer une copie avec des pages manquantes ?

**Réponse**:
**Procédure** :
1. **Identifiez la copie** normalement
2. Ajoutez une **note** : "Pages manquantes : [numéros]"
3. Cochez **"Copie incomplète"**
4. **Validez**

**Notification** :
- L'enseignant verra l'alerte "⚠️ Copie incomplète" lors de la correction
- L'administrateur est notifié pour investigation

**Résolution** :
- Si les pages sont retrouvées : L'admin peut les ajouter manuellement
- Si perdues : L'enseignant corrigera sur la base des pages présentes

### Comment annuler une identification erronée ?

**Réponse**:
**Avant validation** :
- Cliquez simplement sur **"Réinitialiser"** ou sélectionnez le bon élève

**Après validation** :
1. Recherchez la copie dans la liste
2. Cliquez sur **"Modifier"** (✏️)
3. Changez l'élève assigné
4. Ajoutez une note : "Correction identification - [raison]"
5. **"Enregistrer"**

⚠️ **Important** : Si la copie est déjà en cours de correction, contactez l'administrateur.

### Quelle est la différence entre "Booklet" et "Copy" ?

**Réponse**:
**Booklet (Carnet)** :
- Unité physique : Un carnet de copies
- Créé automatiquement lors du découpage du PDF source
- Peut contenir 4, 8, 12, 16 pages (selon format)
- Status : `PENDING_ID@ert.tnIFICATION`

**Copy (Copie)** :
- Unité logique : La copie d'un élève
- Créée après identification du booklet
- Peut être composée d'un ou plusieurs booklets fusionnés
- Status : `READY` → `IN_PROGRESS` → `FINALIZED`

**Exemple** :
```
Examen PDF (50 pages, 25 élèves)
  ↓ Découpage automatique
Booklet 1 (pages 1-2)  ──┐
Booklet 2 (pages 3-4)  ──┴─→ Copy de DUPONT Jean (READY)
Booklet 3 (pages 5-6)  ─────→ Copy de MARTIN Marie (READY)
```

### Comment vérifier la qualité d'identification avant envoi aux enseignants ?

**Réponse**:
**Procédure de vérification** :
1. **Identification > Rapport de qualité**
2. Consultez les indicateurs :
   - ✅ **Copies identifiées** : 100% souhaité
   - ⚠️ **Identifications manuelles** : Vérifiez les cas douteux
   - ❌ **Copies non identifiées** : À traiter en priorité
3. **Cliquez sur "Prévisualiser les copies"**
4. Vérifiez un échantillon aléatoire (10-20 copies)
5. Confirmez que les noms correspondent aux écritures

**Validation finale** :
- Cliquez sur **"Valider toutes les identifications"**
- Les copies passent en status `READY` et deviennent visibles des enseignants

---

## FAQ Élève

### Je ne peux pas me connecter, pourquoi ?

**Réponse**:
**Vérifications** :
1. **Identifiants corrects ?**
   - Adresse email : Votre adresse **@ert.tn** (ex: `prenom.nom-e@ert.tn`)
   - Mot de passe par défaut : Votre **date de naissance au format JJMMAAAA** (ex: 15 mars 2007 → `15032007`)
   - Si vous avez déjà changé votre mot de passe, utilisez le nouveau

2. **Compte activé ?**
   - Les comptes élèves sont activés après l'import depuis Pronote
   - Contactez le secrétariat si votre compte n'existe pas

3. **Message « Trop de tentatives de connexion » ?**
   - Ce message apparaît si trop de tentatives ont été effectuées depuis votre réseau (WiFi école, 4G)
   - **Attendez 15 minutes** puis réessayez
   - C'est normal : tous les élèves sur le même WiFi partagent la même adresse IP

4. **Connexion Internet ?**
   - Vérifiez que vous avez une connexion Internet fonctionnelle
   - La plateforme est accessible depuis n'importe où (lycée ou domicile)

**Toujours bloqué ?** Contactez le secrétariat avec votre nom, prénom et classe.


### Je ne vois pas ma copie corrigée, pourquoi ?

**Réponse**:
**Raisons possibles** :
1. **Correction en cours** : L'enseignant n'a pas encore finalisé votre copie
   - Status visible : "En cours de correction"
   - Patience : Les corrections prennent 3-5 jours en général

2. **Copie non attribuée** : Problème d'identification
   - Contactez le secrétariat pour vérification

3. **Publication non activée** : L'enseignant/admin doit activer la publication
   - Status : "Corrigée, non publiée"
   - Sera visible prochainement

4. **Connexion avec mauvais compte** : Vous êtes connecté avec un autre identifiant
   - Vérifiez votre nom affiché en haut à droite
   - Déconnectez-vous et reconnectez-vous avec le bon compte

### Comment télécharger ma copie en PDF ?

**Réponse**:
**Procédure** :
1. Connectez-vous au portail élève
2. Allez dans **"Mes copies"**
3. Cliquez sur la copie souhaitée
4. Bouton **"Télécharger PDF"** (📥) en haut à droite
5. Le PDF annoté par l'enseignant sera téléchargé

**Format** : PDF avec toutes les annotations vectorielles de l'enseignant.

**Conservation** : Sauvegardez le PDF, il sera supprimé du système après 1 an.

### Je ne comprends pas une annotation, que faire ?

**Réponse**:
**Démarche** :
1. **Demandez à vos camarades** : Peut-être ont-ils la même annotation
2. **Consultez l'enseignant** : Lors du cours suivant ou par email
3. **Forums/ressources** : Cherchez l'explication en ligne si c'est une notion de cours

**Note** : Le système ne permet pas de messagerie directe enseignant-élève pour des raisons RGPD. Utilisez les canaux officiels du lycée (email @ert.tn, Pronote).

### Puis-je contester une note ?

**Réponse**:
**Oui**, selon la procédure habituelle de votre lycée :
1. **Consultez votre copie** pour comprendre la notation
2. **Discutez avec l'enseignant** lors d'une séance de correction collective
3. **Réclamation formelle** : Si désaccord persistant, suivez la procédure du lycée (généralement via Pronote ou courrier)

**Important** : Korrigo est un outil de correction, les règles de contestation restent celles de votre établissement.

### Mes parents peuvent-ils accéder à mes copies ?

**Réponse**:
**Non, pas directement** : Les comptes sont individuels et personnels.

**Alternatives** :
1. **Téléchargez le PDF** et envoyez-le à vos parents
2. **Consultez ensemble** depuis votre session (ne partagez pas votre mot de passe)
3. **Pronote** : Les notes (sans les copies) sont synchronisées dans Pronote où les parents ont accès

**RGPD** : Conformément aux règles de protection des données, les copies numériques sont traitées comme les copies papier traditionnelles.

### Combien de temps mes copies sont-elles disponibles ?

**Réponse**:
**Durée de conservation** :
- **Copies consultables** : Jusqu'à la fin de l'année scolaire + 1 an
- **Archivage** : Les copies sont ensuite archivées (non consultables en ligne)
- **Suppression définitive** : Après 1 an d'archivage

**Recommandation** : Téléchargez vos copies importantes en PDF pour conservation personnelle.

### L'affichage de ma copie est flou, que faire ?

**Réponse**:
**Solutions** :
1. **Zoom** : Utilisez les boutons +/- ou Ctrl+molette pour ajuster
2. **Qualité d'affichage** : Paramètres > Qualité : "Haute" (si votre connexion le permet)
3. **Navigateur** : Chrome offre le meilleur rendu PDF
4. **Téléchargez le PDF** : Ouvrez-le avec un lecteur PDF natif (Adobe Reader, Foxit, etc.)

**Si c'est le scan original qui est flou** : Contactez le secrétariat pour signaler le problème de qualité.

---

## FAQ Technique

### Comment diagnostiquer un problème de performance ?

**Réponse**:
**Outils de diagnostic** :
1. **Console navigateur** (F12) : Vérifiez les erreurs JavaScript
2. **Onglet Network** : Identifiez les requêtes lentes
3. **Onglet Performance** : Enregistrez une session et analysez

**Vérifications serveur** (admin) :
```bash
# État des services
docker-compose ps

# Logs en temps réel
docker-compose logs -f backend frontend

# Utilisation ressources
docker stats

# Base de données
docker-compose exec db psql -U postgres -d korrigo -c "SELECT pg_size_pretty(pg_database_size('korrigo'));"
```

**Goulots d'étranglement courants** :
- 🐌 **PDF trop lourds** : Compressez les sources (< 20 MB par examen)
- 🐌 **Requêtes DB lentes** : Vérifiez les index (`EXPLAIN ANALYZE`)
- 🐌 **Redis plein** : Augmentez la mémoire ou configurez l'éviction
- 🐌 **Celery surchargé** : Augmentez le nombre de workers

### Quelle est la limite de taille pour l'upload de PDF ?

**Réponse**:
**Limites configurées** :
- **Backend Django** : 100 MB par défaut (configurable dans `settings.py` : `DATA_UPLOAD_MAX_MEMORY_SIZE`)
- **Nginx** : 100 MB par défaut (configurable dans `nginx.conf` : `client_max_body_size`)
- **Recommandé** : 20-50 MB par PDF d'examen (pour des performances optimales)

**Dépasser la limite** :
- Augmentez les deux paramètres (backend + nginx)
- Redémarrez les services
- Ou : Découpez le PDF source en plusieurs fichiers

**Compression** :
```bash
# Compresser un PDF volumineux
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH -sOutputFile=output.pdf input.pdf
```

### Comment résoudre une erreur CSRF token ?

**Réponse**:
**Causes** :
1. **Cookies désactivés** : Activez les cookies dans le navigateur
2. **Session expirée** : Reconnectez-vous
3. **Conflit CORS** : Vérifiez que le frontend et backend ont les bons headers
4. **Proxy/firewall** : Peut bloquer les headers

**Solutions** :
```javascript
// Frontend : Vérifiez que le CSRF token est envoyé
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';
```

```python
# Backend : Vérifiez les settings Django
CSRF_TRUSTED_ORIGINS = ['http://localhost:8088', 'https://korrigo.example.com']
CSRF_COOKIE_SAMESITE = 'Lax'
```

**Mode debug** :
```python
# Temporairement (DEV uniquement, JAMAIS en prod)
MIDDLEWARE = [
    # ...
    # 'django.middleware.csrf.CsrfViewMiddleware',  # Commentez pour tester
]
```

### Comment redémarrer un worker Celery bloqué ?

**Réponse**:
**Diagnostic** :
```bash
# Voir les tasks actives
docker-compose exec backend celery -A backend inspect active

# Voir les tasks en attente
docker-compose exec backend celery -A backend inspect reserved
```

**Redémarrage** :
```bash
# Méthode douce
docker-compose restart celery

# Si bloqué : Kill forcé
docker-compose kill celery
docker-compose up -d celery
```

**Vider la queue Redis** (si nécessaire) :
```bash
docker-compose exec redis redis-cli FLUSHALL
```

⚠️ **Attention** : Cela supprime toutes les tasks en attente. Utilisez uniquement si les tasks sont corrompues.

### Comment activer les logs de debug ?

**Réponse**:
**Backend Django** :
```python
# backend/settings.py
DEBUG = True  # Activer uniquement en DEV

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',  # INFO, WARNING, ERROR, CRITICAL
    },
}
```

**Frontend Vue.js** :
```javascript
// frontend/src/main.ts
import { createApp } from 'vue'

const app = createApp(App)
app.config.performance = true  // Performance tracking
app.config.devtools = true     // Vue devtools
```

**Docker logs** :
```bash
# Tous les services
docker-compose logs -f

# Service spécifique avec plus de détails
docker-compose logs -f --tail=100 backend
```

### Comment vérifier que Redis fonctionne correctement ?

**Réponse**:
**Test de connexion** :
```bash
# Connexion au CLI Redis
docker-compose exec redis redis-cli

# Ping
127.0.0.1:6379> PING
PONG

# Info
127.0.0.1:6379> INFO

# Voir les clés
127.0.0.1:6379> KEYS *

# Vérifier la mémoire utilisée
127.0.0.1:6379> INFO memory
```

**Tests depuis Django** :
```python
# Django shell
docker-compose exec backend python manage.py shell

>>> from django.core.cache import cache
>>> cache.set('test', 'hello', 60)
True
>>> cache.get('test')
'hello'
```

**Performance** :
```bash
# Benchmark
docker-compose exec redis redis-benchmark -q -n 10000
```

### Quelle est la configuration matérielle recommandée ?

**Réponse**:
**Minimum** (petit lycée, < 500 élèves) :
- CPU : 4 cores
- RAM : 8 GB
- Stockage : 100 GB SSD
- Réseau : 100 Mbps

**Recommandé** (lycée moyen, 500-1500 élèves) :
- CPU : 8 cores
- RAM : 16 GB
- Stockage : 250 GB SSD (ou NAS)
- Réseau : 1 Gbps

**Production** (grand lycée, > 1500 élèves) :
- CPU : 16 cores
- RAM : 32 GB
- Stockage : 500 GB SSD + NAS
- Réseau : 1 Gbps + redondance

**Considérations** :
- **Concurrence** : Pic de 20-30 enseignants corrigeant simultanément
- **Stockage** : ~50 MB par examen (PDF source + copies générées)
- **Backups** : Doublez l'espace de stockage pour les sauvegardes

### Comment migrer les données vers un nouveau serveur ?

**Réponse**:
**Procédure** :
1. **Sauvegarde complète** sur ancien serveur :
   ```bash
   # Backup DB
   docker-compose exec backend python manage.py backup_database
   
   # Backup fichiers media
   tar -czf media_backup.tar.gz /path/to/media/
   ```

2. **Installer Korrigo** sur nouveau serveur (voir [Deployment Guide](../DEPLOYMENT_GUIDE.md))

3. **Transférer les données** :
   ```bash
   # Copier vers nouveau serveur
   scp backup_*.sql.gz media_backup.tar.gz user@new-server:/tmp/
   ```

4. **Restaurer sur nouveau serveur** :
   ```bash
   # Restaurer DB
   docker-compose exec backend python manage.py restore_backup /tmp/backup_*.sql.gz
   
   # Restaurer media
   tar -xzf /tmp/media_backup.tar.gz -C /path/to/new/media/
   ```

5. **Vérification** :
   ```bash
   # Tester la connexion
   docker-compose exec backend python manage.py check
   
   # Migrer si nécessaire
   docker-compose exec backend python manage.py migrate
   ```

6. **Mise à jour DNS/URLs** : Pointez le domaine vers le nouveau serveur

**Temps d'arrêt** : Planifiez 2-4 heures hors période de correction.

---

## Contact et Support

### Qui contacter selon le problème ?

**Hiérarchie de support** :

| Problème | Contact | Délai de réponse |
|----------|---------|------------------|
| **Mot de passe oublié** | Administrateur lycée | < 1 jour |
| **Problème technique mineur** | Administrateur lycée | 1-2 jours |
| **Bug système** | Support technique Korrigo | 2-3 jours |
| **Question d'utilisation** | Consultez cette FAQ d'abord | Immédiat |
| **Problème RGPD/légal** | DPO du lycée | Variable |
| **Urgence (système down)** | Administrateur lycée + Support Korrigo | < 4 heures |

### Comment signaler un bug ?

**Informations à fournir** :
1. **Description** : Que s'est-il passé ? Comportement attendu vs observé
2. **Étapes de reproduction** : Comment reproduire le bug ?
3. **Environnement** :
   - Navigateur et version
   - Système d'exploitation
   - Rôle utilisateur
4. **Captures d'écran** : Si applicable
5. **Logs** : Console navigateur (F12) ou logs serveur
6. **Date/heure** : Quand le problème est survenu

**Canaux** :
- Email : support.korrigo@lycee.fr (remplacez par l'email réel)
- Issue tracker : Si déployé en interne avec un système de tickets

### Où trouver plus de documentation ?

**Documentation complète** :

**Pour les utilisateurs** :
- [Guide Enseignant](../users/GUIDE_ENSEIGNANT.md)
- [Guide Secrétariat](../users/GUIDE_SECRETARIAT.md)
- [Guide Élève](../users/GUIDE_ETUDIANT.md)
- [Navigation UI](../users/NAVIGATION_UI.md)

**Pour les administrateurs** :
- [Guide Administrateur Lycée](../admin/GUIDE_ADMINISTRATEUR_LYCEE.md)
- [Guide Utilisateur Admin](../admin/GUIDE_UTILISATEUR_ADMIN.md)
- [Gestion des Utilisateurs](../admin/GESTION_UTILISATEURS.md)
- [Procédures Opérationnelles](../admin/PROCEDURES_OPERATIONNELLES.md)

**Sécurité et conformité** :
- [Politique RGPD](../security/POLITIQUE_RGPD.md)
- [Manuel de Sécurité](../security/MANUEL_SECURITE.md)
- [Gestion des Données](../security/GESTION_DONNEES.md)
- [Audit de Conformité](../security/AUDIT_CONFORMITE.md)

**Légal** :
- [Politique de Confidentialité](../legal/POLITIQUE_CONFIDENTIALITE.md)
- [Conditions d'Utilisation](../legal/CONDITIONS_UTILISATION.md)

**Support** :
- [Dépannage](DEPANNAGE.md)
- [Support](SUPPORT.md)

**Technique** :
- [API Reference](../API_REFERENCE.md)
- [Business Workflows](../BUSINESS_WORKFLOWS.md)
- [Deployment Guide](../DEPLOYMENT_GUIDE.md)

---

## Glossaire

**Termes clés** :

- **Booklet** : Carnet de copies (unité physique issue du découpage du PDF)
- **Copy** : Copie d'un élève (unité logique après identification)
- **Grading** : Processus de correction
- **Annotation** : Élément vectoriel ajouté par l'enseignant (commentaire, surlignage, etc.)
- **Lock** : Verrou empêchant deux enseignants de corriger simultanément la même copie
- **Status** : État d'une copie (`READY`, `IN_PROGRESS`, `FINALIZED`)
- **OCR** : Reconnaissance optique de caractères (pour lire les noms sur les copies)
- **Pronote** : Logiciel de vie scolaire français (gestion notes, absences, etc.)
- **INE** : Identifiant National Élève (numéro unique de 11 caractères)
- **RGPD** : Règlement Général sur la Protection des Données
- **CNIL** : Commission Nationale de l'Informatique et des Libertés

---

## Historique des Versions

| Version | Date | Modifications |
|---------|------|---------------|
| 1.0.0 | 30/01/2026 | Création initiale de la FAQ |

---

**Besoin d'aide supplémentaire ?**  
Consultez le [Guide de Dépannage](DEPANNAGE.md) ou contactez votre administrateur.
