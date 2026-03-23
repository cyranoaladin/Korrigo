# Guide de l'Administrateur du Lycée - Korrigo PMF

> **Version**: 1.0.0  
> **Date**: 23 Mars 2026
> **Public**: Direction du lycée (Proviseur, Proviseur Adjoint, CPE)  
> **Langue**: Français (non-technique)

Ce document constitue un guide complet pour les responsables d'établissement souhaitant déployer et administrer la plateforme Korrigo PMF de correction numérique d'examens.

---

## 📋 Table des Matières

1. [Introduction](#introduction)
2. [Vue d'Ensemble du Système](#vue-densemble-du-système)
3. [Déploiement et Infrastructure](#déploiement-et-infrastructure)
4. [Conformité Légale et RGPD](#conformité-légale-et-rgpd)
5. [Gouvernance et Organisation](#gouvernance-et-organisation)
6. [Sécurité et Protection des Données](#sécurité-et-protection-des-données)
7. [Modèle Opérationnel](#modèle-opérationnel)
8. [Risques et Mitigation](#risques-et-mitigation)
9. [Support et Maintenance](#support-et-maintenance)
10. [Glossaire](#glossaire)

---

## 1. Introduction

### 1.1 Qu'est-ce que Korrigo PMF ?

**Korrigo PMF** est une plateforme numérique de correction d'examens conçue spécifiquement pour les lycées. Elle permet de transformer le processus traditionnel de correction papier en un workflow numérique moderne, efficace et sécurisé.

#### Fonctionnalités Principales

- **Numérisation Intelligente** : Import de copies scannées en masse avec découpage automatique
- **Identification Semi-Automatique** : Reconnaissance optique (OCR) des noms d'élèves assistée par validation humaine
- **Correction Numerique** : Interface de correction avec annotations vectorielles, commentaires et bareme
- **Tampon Vrai/Faux (V2)** : Boutons V/X dans la barre d'outils pour marquer rapidement les reponses vrai/faux
- **Vue Scindee (V2)** : Affichage simultane de la copie et du bareme (Split View) pour une correction plus efficace
- **Anonymisation** : Protection de l'impartialite de la correction
- **Force Unlock (V2)** : Deverrouillage force d'une copie bloquee par un administrateur via le CorrectorDesk
- **Export Pronote** : Integration directe avec votre systeme de gestion scolaire
- **Portail Eleve** : Consultation securisee des copies corrigees par les eleves

### 1.2 Bénéfices pour l'Établissement

#### Pédagogiques

- **Retour Détaillé** : Les élèves consultent leurs copies annotées à tout moment
- **Traçabilité** : Historique complet de toutes les actions de correction
- **Qualité** : Annotations claires, lisibles et pérennes (vs. encre sur papier)
- **Accessibilité** : Les élèves absents le jour de remise peuvent consulter leurs copies en ligne

#### Organisationnels

- **Gain de Temps** : Réduction du temps de distribution, collecte et archivage
- **Flexibilité** : Les enseignants corrigent de n'importe où (domicile, salle des profs, etc.)
- **Archivage Numérique** : Fin des armoires pleines de copies papier
- **Écologie** : Réduction de l'impression papier pour les retours élèves

#### Sécuritaires

- **Conformité RGPD** : Protection des données personnelles des élèves
- **Audit Complet** : Journal d'événements pour toute action sensible
- **Sauvegardes Automatiques** : Protection contre la perte de données
- **Contrôle d'Accès** : Gestion fine des permissions par rôle

### 1.3 Vision et Objectifs Stratégiques

**Vision** : Moderniser l'évaluation scolaire en préservant la rigueur pédagogique et en renforçant la protection des données.

**Objectifs** :
- Déployer la solution pour les examens blancs (Bac Blanc, brevets blancs)
- Former 100% des enseignants à la correction numérique d'ici juin 2026
- Réduire le volume de copies papier archivées de 80%
- Garantir un accès élève 24/7 à leurs copies corrigées
- Assurer une conformité RGPD à 100%

---

## 2. Vue d'Ensemble du Système

### 2.1 Architecture Simplifiée

Korrigo PMF fonctionne selon le modèle suivant :

```
┌──────────────────────────────────────────────────────┐
│                    NAVIGATEUR WEB                    │
│  (Enseignants, Administration, Élèves)               │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│               SERVEUR KORRIGO PMF                    │
│  - Application Web (Django + Vue.js)                 │
│  - Base de Données (PostgreSQL)                      │
│  - Stockage Fichiers (PDF, images)                   │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│                 INTÉGRATIONS                         │
│  - Export CSV vers Pronote                           │
│  - Import Élèves depuis Pronote                      │
└──────────────────────────────────────────────────────┘
```

**Mode de Déploiement** : Local (serveur interne du lycée) ou cloud privé (hébergement dédié)

### 2.2 Rôles et Responsabilités

La plateforme définit **trois rôles principaux** :

| Rôle | Utilisateurs | Responsabilités |
|------|--------------|-----------------|
| **Administrateur** | Proviseur Adjoint, Secrétariat, Admin NSI | Gestion globale : création d'examens, gestion des utilisateurs, exports |
| **Enseignant** | Professeurs de toutes disciplines | Correction des copies, annotations, finalisation |
| **Élève** | Tous les élèves de l'établissement | Consultation de leurs copies corrigées uniquement |

### 2.3 Flux de Données - Workflow Global

#### Phase 1 : Préparation (Administration)
1. **Création de l'examen** dans Korrigo (nom, date, matière, barème)
2. **Scan des copies** après l'examen (scanner A3 recto-verso recommandé)
3. **Upload du PDF** contenant toutes les copies scannées

#### Phase 2 : Traitement Automatique (Système)
4. **Découpage automatique** : Le PDF massif est découpé en fascicules individuels (4 pages A4 par copie)
5. **OCR des en-têtes** : Reconnaissance optique des noms manuscrits des élèves

#### Phase 3 : Identification (Secrétariat)
6. **Validation de l'identification** : Un opérateur confirme ou corrige les noms détectés par OCR
7. **Création des copies** : Chaque fascicule validé devient une copie liée à un élève

#### Phase 4 : Anonymisation (Automatique)
8. **Génération d'un numéro d'anonymat** pour chaque copie
9. **Masquage de l'identité** de l'élève pour la correction

#### Phase 5 : Correction (Enseignants)
10. **Verrouillage** : Un enseignant « prend » une copie pour la corriger
11. **Annotation** : Ajout de commentaires, surligné, corrections, notes par question
12. **Finalisation** : L'enseignant valide la copie (calcul automatique de la note totale)

#### Phase 6 : Export et Publication (Administration)
13. **Génération des PDF finaux** : Copies avec annotations visibles et nom de l'élève réaffiché
14. **Export CSV vers Pronote** : Notes et coefficients pour import dans le système de gestion
15. **Activation du portail élève** : Les élèves peuvent consulter leurs copies

---

## 3. Déploiement et Infrastructure

### 3.1 Exigences Serveur

#### Configuration Minimale (< 500 élèves)

- **Processeur** : 4 cœurs (Intel Xeon / AMD EPYC)
- **RAM** : 8 Go
- **Stockage** : 200 Go SSD (système + application + base de données)
- **Stockage Données** : 500 Go SSD/HDD (copies PDF, images)
- **Réseau** : 100 Mbps (connexion interne)
- **OS** : Ubuntu 22.04 LTS ou Debian 11 (serveur Linux recommandé)

#### Configuration Recommandée (> 500 élèves ou usage intensif)

- **Processeur** : 8 cœurs
- **RAM** : 16 Go
- **Stockage** : 500 Go SSD NVMe
- **Stockage Données** : 1 To (avec sauvegardes automatiques sur NAS)
- **Réseau** : 1 Gbps
- **Redondance** : RAID 1 pour le stockage des données

#### Options de Déploiement

| Option | Avantages | Inconvénients | Coût Estimé |
|--------|-----------|---------------|-------------|
| **Serveur Interne** | Contrôle total, données sur site, pas de coût récurrent | Maintenance interne requise, expertise technique nécessaire | 2000-4000 € (matériel initial) |
| **Cloud Privé** | Maintenance externalisée, sauvegardes automatiques, haute disponibilité | Coût récurrent, dépendance au fournisseur | 50-150 €/mois |
| **Machine Virtuelle Interne** | Mutualisation du matériel existant, flexibilité | Performance partagée avec autres services | 0 € (si infrastructure existante) |

### 3.2 Besoins Humains et Compétences

#### Équipe de Déploiement

| Rôle | Profil | Temps Estimé | Mission |
|------|--------|--------------|---------|
| **Responsable Projet** | Proviseur Adjoint / CPE | 10h | Pilotage, validation, communication |
| **Administrateur Technique** | Professeur NSI / Prestataire IT | 20h | Installation, configuration, formation |
| **Référent Pédagogique** | Enseignant pilote | 5h | Tests, feedback, formation pairs |
| **Secrétariat** | Agent administratif | Formation 2h | Identification des copies |

#### Compétences Techniques Requises

**Pour l'installation initiale** :
- Administration système Linux (niveau intermédiaire)
- Docker et Docker Compose (connaissances de base)
- Réseau (IP, ports, pare-feu)
- Gestion PostgreSQL (optionnel mais recommandé)

**Pour l'administration quotidienne** :
- Utilisation d'une interface web (aucune compétence technique)
- Export CSV (niveau bureautique)
- Gestion de sauvegardes (procédures documentées)

### 3.3 Calendrier de Déploiement

#### Déploiement Type (8 semaines)

**Semaine 1-2 : Préparation**
- Réunion de lancement avec l'équipe
- Commande/préparation du serveur
- Import de la base élèves (export Pronote)

**Semaine 3-4 : Installation Technique**
- Installation du serveur et de Korrigo PMF
- Configuration réseau (accès intranet)
- Tests de charge initiaux

**Semaine 5-6 : Phase Pilote**
- Formation des enseignants pilotes (2h par groupe)
- Test sur un petit examen (1 classe)
- Ajustements suite aux retours

**Semaine 7 : Formation Généralisée**
- Formation de tous les enseignants (sessions de 1h30)
- Formation du secrétariat (2h)
- Documentation remise aux utilisateurs

**Semaine 8 : Déploiement Officiel**
- Premier examen blanc en grandeur nature
- Support renforcé (hotline interne)
- Bilan et ajustements

### 3.4 Budget Prévisionnel

#### Coûts Initiaux (One-Time)

| Poste | Détail | Montant |
|-------|--------|---------|
| **Matériel Serveur** | Serveur Dell PowerEdge T340 ou équivalent | 2 500 € |
| **Licence Logicielle** | Korrigo PMF (open-source, gratuit) | 0 € |
| **Installation** | Prestation externe (si nécessaire) | 1 500 € |
| **Formation** | 15h de formation (enseignants + admin) | 500 € |
| **Scanner A3** | Si non disponible (Canon DR-C230) | 1 200 € |
| **Total Initial** | | **5 700 €** |

#### Coûts Récurrents (Annuels)

| Poste | Détail | Montant/an |
|-------|--------|------------|
| **Maintenance Technique** | Support technique (si externe) | 800 € |
| **Sauvegardes Externes** | Stockage cloud (Backup) | 200 € |
| **Électricité Serveur** | 24/7, ~150W | 150 € |
| **Total Annuel** | | **1 150 €** |

**ROI Estimé** : Économies sur l'impression, l'archivage papier et le temps administratif : ~3 000 €/an  
**Retour sur Investissement** : 2 ans

---

## 4. Conformité Légale et RGPD

### 4.1 Cadre Légal Applicable

Korrigo PMF traite des **données personnelles d'élèves mineurs**, ce qui implique une conformité stricte au **Règlement Général sur la Protection des Données (RGPD)** et à la loi « Informatique et Libertés ».

#### Textes de Référence

- **RGPD** (Règlement UE 2016/679)
- **Loi Informatique et Libertés** (modifiée 2018)
- **Code de l'Éducation** (articles L. 111-5, L. 131-1)
- **Référentiel CNIL** pour l'Éducation Nationale

### 4.2 Responsabilités RGPD

#### Responsable de Traitement

**Le Lycée** (représenté par le Proviseur) est le **responsable de traitement** au sens du RGPD.

**Obligations** :
- Définir les finalités et moyens du traitement
- Garantir la conformité RGPD
- Désigner un Délégué à la Protection des Données (DPO) si nécessaire
- Tenir un registre des traitements
- Informer les personnes concernées (élèves, parents)

#### Sous-Traitant (si applicable)

Si Korrigo PMF est hébergé par un prestataire externe, ce dernier est **sous-traitant** au sens RGPD.

**Obligations** :
- Contrat de sous-traitance conforme (Article 28 RGPD)
- Garanties de sécurité
- Assistance au responsable de traitement

**Document requis** : [Accord de Traitement de Données](../legal/ACCORD_TRAITEMENT_DONNEES.md)

### 4.3 Données Personnelles Collectées

#### Élèves

| Donnée | Finalité | Base Légale |
|--------|----------|-------------|
| **Date de Naissance** | Identification unique (avec Nom/Prénom) | Mission d'intérêt public |
| **Nom, Prénom** | Identification, affichage | Mission d'intérêt public |
| **Classe** | Organisation pédagogique | Mission d'intérêt public |
| **Email** (optionnel) | Communication, notifications | Consentement (si utilisé) |
| **Copies d'Examen** | Évaluation pédagogique | Mission d'intérêt public |
| **Notes et Annotations** | Évaluation pédagogique | Mission d'intérêt public |

#### Enseignants et Personnel

| Donnée | Finalité | Base Légale |
|--------|----------|-------------|
| **Nom, Prénom** | Identification utilisateur | Contrat de travail |
| **Login (username)** | Authentification | Contrat de travail |
| **Email Professionnel** | Communication | Contrat de travail |
| **Actions de Correction** | Traçabilité, audit | Obligation légale |

### 4.4 Droits des Personnes Concernées

Les élèves (et leurs représentants légaux si mineurs) disposent des droits suivants :

| Droit | Description | Procédure |
|-------|-------------|-----------|
| **Accès** | Consulter toutes leurs données | Demande écrite au Proviseur |
| **Rectification** | Corriger une donnée inexacte | Demande écrite au Proviseur |
| **Suppression** | Effacement après la période légale de conservation | Demande écrite (après délai légal) |
| **Portabilité** | Recevoir une copie numérique de leurs données | Export PDF fourni par l'admin |
| **Opposition** | S'opposer au traitement (limité dans le contexte scolaire) | Demande écrite au Proviseur |

**Délai de Réponse** : 1 mois maximum (Article 12 RGPD)

**Procédure** : Voir [Politique RGPD - Exercice des Droits](../security/POLITIQUE_RGPD.md#6-droits-des-personnes)

### 4.5 Durées de Conservation

Les données sont conservées selon les durées légales applicables :

| Type de Donnée | Durée de Conservation | Justification |
|----------------|----------------------|---------------|
| **Copies d'Examens** | 1 an après la session | Code de l'Éducation (durée de conservation des épreuves) |
| **Notes et Résultats** | 50 ans (archivage intermédiaire) | Code de l'Éducation (registres de notes) |
| **Données Élèves** | Jusqu'à fin de scolarité + 1 an | Gestion administrative |
| **Logs d'Audit** | 1 an | Sécurité et traçabilité |
| **Comptes Utilisateurs Enseignants** | Durée du contrat + 1 an | Gestion RH |

**Suppression Automatique** : Korrigo PMF propose des scripts de purge automatique conformes à ces durées.

### 4.6 Obligations d'Information

#### Information des Élèves et Parents

**Document requis** : [Politique de Confidentialité](../legal/POLITIQUE_CONFIDENTIALITE.md) (version simplifiée pour élèves)

**Contenu** :
- Quelles données sont collectées
- Pourquoi (finalités)
- Combien de temps elles sont conservées
- Qui y a accès
- Quels sont leurs droits

**Diffusion** :
- Affichage sur le portail élève (avant première connexion)
- Remise lors de l'inscription (avec le règlement intérieur)
- Disponible en permanence sur le site du lycée

#### Consentement (si applicable)

Le consentement **n'est pas requis** pour le traitement principal (évaluation pédagogique = mission d'intérêt public).

**Exceptions nécessitant un consentement** :
- Utilisation de l'email pour des communications non obligatoires
- Partage de données avec des tiers (hors Pronote)

**Formulaires** : [Formulaires de Consentement](../legal/FORMULAIRES_CONSENTEMENT.md)

### 4.7 Déclarations et Formalités

#### Registre des Activités de Traitement

**Obligation** : Tenir un registre des traitements (Article 30 RGPD)

**Contenu** :
- Nom et coordonnées du responsable de traitement
- Finalités du traitement
- Catégories de données
- Catégories de personnes concernées
- Destinataires des données
- Durées de conservation
- Mesures de sécurité

**Modèle** : Fourni par la CNIL (registre simplifié pour les établissements publics)

#### Analyse d'Impact (DPIA)

**Obligation** : Si le traitement présente un risque élevé pour les droits et libertés

**Korrigo PMF** : Risque **modéré** (données d'élèves mineurs, mais pas de catégories sensibles)

**Recommandation** : Réaliser une DPIA par précaution (voir [Politique RGPD - Section 9](../security/POLITIQUE_RGPD.md#9-analyse-dimpact))

#### Notification CNIL

**Pas de notification préalable requise** depuis le RGPD (sauf violation de données)

---

## 5. Gouvernance et Organisation

### 5.1 Comité de Pilotage

**Composition Recommandée** :
- **Proviseur** (sponsor, décisions stratégiques)
- **Proviseur Adjoint** (pilotage opérationnel)
- **CPE** (lien avec vie scolaire)
- **Professeur Référent** (remontées terrain)
- **Admin NSI / IT** (support technique)
- **DPO** (conformité RGPD) - si désigné

**Fréquence** : Réunion mensuelle (30 min)

**Ordre du Jour Type** :
1. Statistiques d'usage (nombre d'examens, de corrections)
2. Incidents et problèmes rencontrés
3. Demandes d'évolutions
4. Points de conformité RGPD
5. Budget et investissements

### 5.2 Matrice de Décision et d'Autorité

| Décision | Autorité | Consultation |
|----------|----------|--------------|
| **Déploiement Initial** | Proviseur | Conseil d'Administration |
| **Création d'Examens** | Admin / Enseignant Chef de Département | - |
| **Gestion des Utilisateurs** | Admin (Proviseur Adjoint) | Enseignants |
| **Configuration Système** | Admin NSI | Proviseur Adjoint |
| **Mise à Jour Majeure** | Proviseur Adjoint | Comité de Pilotage |
| **Export de Données** | Admin (avec traçabilité) | Proviseur |
| **Suppression de Données** | Admin (après délai légal) | DPO (si applicable) |

### 5.3 Procédures de Gestion des Changements

#### Changements Mineurs (correctifs, petites améliorations)

- **Décision** : Admin NSI
- **Communication** : Email aux utilisateurs concernés
- **Test** : Environnement de pré-production (recommandé)
- **Déploiement** : Hors heures de cours (mercredi après-midi, week-end)

#### Changements Majeurs (nouvelles fonctionnalités, migration)

- **Décision** : Comité de Pilotage
- **Planning** : 4 semaines de préavis
- **Test** : Phase pilote avec enseignants volontaires
- **Formation** : Sessions de formation (1h)
- **Déploiement** : Période de vacances scolaires (privilégier)
- **Rollback** : Plan de retour arrière documenté

#### Procédure d'Escalade en Cas d'Incident

```
Incident Mineur (ex: utilisateur bloqué)
    → Admin NSI (résolution sous 24h)

Incident Moyen (ex: service dégradé)
    → Admin NSI + Proviseur Adjoint
    → Résolution sous 4h

Incident Majeur (ex: perte de données, faille de sécurité)
    → Proviseur + Admin NSI + DPO
    → Cellule de crise (résolution immédiate)
    → Notification CNIL si violation de données (72h)
```

### 5.4 Rôles et Responsabilités Détaillés

#### Proviseur / Direction

- Valide le déploiement et le budget
- Représente le responsable de traitement (RGPD)
- Décide des orientations stratégiques
- Valide les communications aux familles
- Gère les réclamations formelles

#### Proviseur Adjoint / CPE

- Pilote le projet au quotidien
- Gère les comptes administrateurs
- Supervise les exports Pronote
- Coordonne les formations
- Suit les indicateurs d'usage

#### Professeur Référent

- Teste les nouvelles fonctionnalités
- Remonte les besoins des enseignants
- Anime les formations internes
- Contribue à la documentation
- Assure le support de premier niveau

#### Admin NSI / IT

- Installe et maintient le serveur
- Gère les sauvegardes
- Applique les mises à jour de sécurité
- Surveille les performances
- Résout les incidents techniques

#### Secrétariat

- Importe la base élèves (depuis Pronote)
- Identifie les copies scannées
- Valide les fascicules
- Gère les cas spéciaux (absents, rattrapages)

#### Enseignants

- Créent leurs examens
- Corrigent les copies numériquement
- Finalisent les notes
- Remontent les problèmes au référent

#### Élèves

- Consultent leurs copies corrigées
- Téléchargent leurs PDF
- Respectent les conditions d'utilisation

---

## 6. Sécurité et Protection des Données

### 6.1 Posture de Sécurité (Vue Non-Technique)

Korrigo PMF applique une **approche défensive multicouche** pour protéger les données sensibles des élèves.

#### Principes de Sécurité

1. **Moindre Privilège** : Chaque utilisateur ne peut accéder qu'aux données nécessaires à son rôle
2. **Défense en Profondeur** : Plusieurs couches de protection (authentification, chiffrement, audit)
3. **Traçabilité Totale** : Toute action sensible est enregistrée dans un journal d'audit
4. **Séparation des Devoirs** : Les élèves ne voient que leurs copies, les enseignants ne gèrent pas les utilisateurs

### 6.2 Contrôle d'Accès

#### Authentification

| Rôle | Méthode d'Authentification | Sécurité |
|------|----------------------------|----------|
| **Admin** | Identifiant + Mot de passe | Session sécurisée (cookie HttpOnly) |
| **Enseignant** | Identifiant + Mot de passe | Session sécurisée (cookie HttpOnly) |
| **Élève** | Email + Mot de passe | Session élève (isolation des données) |

**Politique de Mot de Passe** :
- Longueur minimale : 8 caractères
- Complexité : Lettres + chiffres + caractères spéciaux (recommandé)
- Renouvellement : Tous les 6 mois (recommandé pour les admins)

**Protection contre les Attaques** :
- Limitation de tentatives (5 essais maximum par 15 minutes)
- Verrouillage temporaire en cas d'abus
- Journalisation des échecs de connexion

#### Matrice de Permissions (Résumé)

| Action | Admin | Enseignant | Élève |
|--------|-------|------------|-------|
| Voir toutes les copies | ✅ | ✅ (de son examen) | ❌ |
| Voir sa copie | ❌ | ❌ | ✅ |
| Corriger une copie | ✅ | ✅ | ❌ |
| Créer un examen | ✅ | ✅ | ❌ |
| Gérer les utilisateurs | ✅ | ❌ | ❌ |
| Exporter les notes | ✅ | ❌ | ❌ |
| Consulter les logs d'audit | ✅ | ❌ | ❌ |

### 6.3 Protection des Données

#### Chiffrement

- **En Transit** : Connexions HTTPS (SSL/TLS 1.2 minimum) pour toutes les communications
- **Au Repos** : Chiffrement du disque serveur recommandé (LUKS, BitLocker)
- **Mots de Passe** : Hachage sécurisé (bcrypt avec salt) - jamais stockés en clair

#### Anonymisation

- Lors de la correction, l'identité de l'élève est masquée (numéro d'anonymat)
- L'enseignant ne voit **jamais** le nom de l'élève pendant la correction
- Le nom réapparaît uniquement sur le PDF final (après finalisation)

#### Isolation des Données

- **Base de Données** : Accès restreint (uniquement depuis le serveur applicatif)
- **Fichiers** : Stockage dans un volume dédié non accessible depuis Internet
- **Sessions** : Isolation stricte (un élève ne peut jamais accéder aux données d'un autre)

### 6.4 Audit et Traçabilité

Korrigo PMF enregistre **toutes les actions sensibles** dans un journal d'audit inviolable.

#### Événements Audités

| Événement | Données Enregistrées | Conservation |
|-----------|----------------------|--------------|
| **Connexion** | Utilisateur, IP, horodatage | 1 an |
| **Création d'Examen** | Auteur, nom examen, date | 1 an |
| **Identification Copie** | Opérateur, élève lié, horodatage | 1 an |
| **Verrouillage Copie** | Enseignant, copie, horodatage | 1 an |
| **Création Annotation** | Enseignant, copie, type, horodatage | 1 an |
| **Finalisation Copie** | Enseignant, copie, note, horodatage | 1 an |
| **Export CSV** | Admin, examen, horodatage | 1 an |
| **Téléchargement PDF** | Utilisateur, copie, horodatage | 1 an |

**Consultation des Logs** : Réservée aux administrateurs (interface dédiée)

**Intégrité** : Les logs ne peuvent pas être modifiés (écriture seule)

### 6.5 Sauvegardes et Continuité d'Activité

#### Stratégie de Sauvegarde

| Type | Fréquence | Conservation | Emplacement |
|------|-----------|--------------|-------------|
| **Sauvegarde Complète** | Hebdomadaire (dimanche 2h) | 4 semaines | Serveur NAS dédié |
| **Sauvegarde Incrémentale** | Quotidienne (1h du matin) | 7 jours | Serveur NAS dédié |
| **Sauvegarde Hors Site** | Mensuelle | 12 mois | Cloud sécurisé (optionnel) |
| **Snapshots Base de Données** | Avant chaque mise à jour | 3 dernières versions | Serveur local |

#### Plan de Reprise d'Activité (PRA)

**Objectifs** :
- **RTO** (Recovery Time Objective) : 24h maximum
- **RPO** (Recovery Point Objective) : 24h maximum (perte de données maximale acceptable)

**Scénarios de Sinistre** :
1. **Panne Serveur** : Restauration sur nouveau serveur (délai : 8h)
2. **Corruption Base de Données** : Restauration depuis sauvegarde (délai : 4h)
3. **Perte de Fichiers** : Restauration depuis NAS (délai : 2h)
4. **Incendie / Catastrophe** : Restauration depuis sauvegarde hors site (délai : 48h)

**Procédures Documentées** : Voir [Guide Opérationnel - Section Backup](./PROCEDURES_OPERATIONNELLES.md#5-sauvegardes)

### 6.6 Gestion des Incidents de Sécurité

#### Détection

- Surveillance des logs (tentatives de connexion suspectes)
- Alertes automatiques (accès non autorisés)
- Remontées utilisateurs (comportements anormaux)

#### Réponse

**Incident Mineur** (ex: tentative de connexion avec mauvais mot de passe) :
- Log automatique
- Pas d'action immédiate
- Revue mensuelle

**Incident Modéré** (ex: accès non autorisé à une copie) :
- Notification immédiate à l'admin
- Investigation (logs, utilisateur concerné)
- Mesures correctives (changement mot de passe, révocation session)

**Incident Grave** (ex: violation de données, fuite) :
- **Cellule de Crise** : Proviseur + Admin + DPO
- **Notification CNIL** : Dans les 72h si risque pour les personnes
- **Notification Personnes Concernées** : Si risque élevé
- **Mesures Immédiates** : Isolation du système, investigation forensique
- **Post-Mortem** : Analyse des causes, plan d'action préventif

**Document de Référence** : [Manuel Sécurité - Incident Response](../security/MANUEL_SECURITE.md#8-réponse-aux-incidents)

---

## 7. Modèle Opérationnel

### 7.1 Cycle de Vie d'un Examen (Vue d'Ensemble)

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1 : PLANIFICATION (J-7)                               │
│ - Admin crée l'examen dans Korrigo                          │
│ - Définition du barème (exercices, questions, points)       │
│ - Configuration des paramètres (anonymat, etc.)             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2 : EXAMEN (J)                                         │
│ - Distribution des copies papier aux élèves                 │
│ - Composition de l'examen (3h)                              │
│ - Collecte et scan des copies (scanner A3 recto-verso)      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3 : INGESTION (J+1, 30 min)                           │
│ - Upload du PDF scanné dans Korrigo                         │
│   * Option A : Batch A3 (toutes les copies dans 1 PDF)      │
│   * Option B : Individuel A4 (1 PDF par élève/copie)        │
│ - Découpage automatique (si Batch A3)                       │
│ - OCR des en-têtes (reconnaissance des noms)               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4 : IDENTIFICATION (J+1 à J+2, 2h pour 100 copies)   │
│ - Secrétariat valide les noms détectés par OCR             │
│ - Fusion de booklets si nécessaire (copie incomplète)      │
│ - Création des copies (lien élève ↔ fascicule)             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 5 : ANONYMISATION (Automatique)                       │
│ - Génération numéro d'anonymat (ex: A3F7B2E1)              │
│ - Masquage du nom sur la copie numérique                   │
│ - Copies disponibles pour correction                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 6 : CORRECTION (J+3 à J+7, 15 min/copie)             │
│ - Enseignants corrigent numériquement (annotations)        │
│ - Calcul automatique des notes par question                │
│ - Finalisation copie par copie                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 7 : FINALISATION (J+8, 30 min)                        │
│ - Admin vérifie que toutes les copies sont corrigées       │
│ - Génération des PDF finaux (nom élève réaffiché)          │
│ - Export CSV vers Pronote (notes + coefficients)           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 8 : PUBLICATION (J+9)                                 │
│ - Activation du portail élève                              │
│ - Élèves consultent leurs copies corrigées                 │
│ - Import CSV dans Pronote (notes officielles)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 9 : ARCHIVAGE (1 an après)                            │
│ - Suppression automatique des copies PDF (après 1 an)      │
│ - Conservation des notes (50 ans, conformité légale)       │
│ - Purge des comptes élèves sortants                        │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Planification des Ressources

#### Ressources Humaines par Examen (100 copies)

| Phase | Ressource | Temps Total | Observations |
|-------|-----------|-------------|--------------|
| **Planification** | Admin | 30 min | Création examen + barème |
| **Scan** | Agent | 1h | 100 copies A3 (recto-verso) |
| **Ingestion** | Admin | 10 min | Upload PDF |
| **Identification** | Secrétariat | 2h | ~1 min/copie |
| **Correction** | Enseignants (5) | 25h total | 15 min/copie × 100 / 5 profs |
| **Finalisation** | Admin | 30 min | Export + vérification |
| **Total** | | **29h** | Répartis sur 7-10 jours |

**Comparaison avec Correction Papier** :
- Distribution papier : 1h (vs. 0h numérique)
- Remise copies : 1h (vs. 0h numérique)
- Archivage : 2h (vs. 0h numérique)
- **Gain estimé : 4h** par examen de 100 copies

### 7.3 Qualité et Assurance

#### Indicateurs de Performance (KPI)

| Indicateur | Objectif | Mesure |
|------------|----------|--------|
| **Taux d'Identification OCR Correcte** | > 80% | % de copies identifiées sans correction manuelle |
| **Temps Moyen de Correction** | < 20 min/copie | Temps total / nombre de copies |
| **Taux de Finalisation sous 7 Jours** | > 90% | % d'examens finalisés en moins de 7 jours |
| **Satisfaction Enseignants** | > 4/5 | Enquête semestrielle |
| **Disponibilité Système** | > 99% | Uptime mensuel |
| **Incidents de Sécurité** | 0 | Nombre d'incidents graves/an |

#### Processus d'Amélioration Continue

1. **Collecte de Feedback** : Enquête post-examen (enseignants) + retours élèves
2. **Analyse Trimestrielle** : Comité de pilotage examine les KPI
3. **Plan d'Action** : Identification des irritants + priorisation
4. **Déploiement** : Mise en œuvre des améliorations
5. **Suivi** : Vérification d'efficacité au trimestre suivant

---

## 8. Risques et Mitigation

### 8.1 Analyse des Risques

#### Risques Techniques

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| **Panne Serveur** | Faible | Élevé | Serveur redondant + sauvegarde quotidienne + PRA documenté |
| **Perte de Données** | Très Faible | Critique | Sauvegardes multiples (locale + NAS + cloud) + tests de restauration trimestriels |
| **Corruption Base de Données** | Faible | Élevé | Snapshots avant mise à jour + sauvegarde quotidienne |
| **Faille de Sécurité** | Faible | Élevé | Mises à jour de sécurité mensuelles + audit annuel + limitation accès réseau |
| **Surcharge Serveur** | Moyenne | Moyen | Dimensionnement adapté + monitoring CPU/RAM + migration vers serveur plus puissant si nécessaire |

#### Risques Opérationnels

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| **Manque de Formation Enseignants** | Moyenne | Moyen | Formation initiale (1h30) + documentation + support référent |
| **Résistance au Changement** | Moyenne | Moyen | Phase pilote + communication bénéfices + accompagnement personnalisé |
| **Erreur d'Identification Copie** | Faible | Moyen | Double validation secrétariat + possibilité correction a posteriori |
| **Absence Référent Technique** | Faible | Élevé | Documentation complète + formation admin backup |
| **Scan de Mauvaise Qualité** | Moyenne | Moyen | Procédure de scan documentée + vérification qualité avant upload |

#### Risques Juridiques et Conformité

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| **Non-Conformité RGPD** | Faible | Critique | Audit annuel + DPO (si applicable) + formation RGPD admin |
| **Violation de Données** | Très Faible | Critique | Chiffrement + accès restreint + audit logs + plan de réponse incident |
| **Réclamation Élève/Parent** | Faible | Moyen | Politique de confidentialité claire + procédure exercice droits RGPD |
| **Fuite de Copie Avant Correction** | Très Faible | Élevé | Anonymisation + contrôle d'accès strict + logs d'audit |
| **Litige Note Contestée** | Moyenne | Faible | Traçabilité totale (annotations + historique) + PDF final inviolable |

### 8.2 Plan de Continuité d'Activité (PCA)

#### Scénario 1 : Panne Serveur en Période de Correction

**Durée d'Indisponibilité Acceptable** : 24h

**Plan d'Action** :
1. **Immédiat** : Notification aux enseignants (report correction)
2. **4h** : Diagnostic panne (Admin NSI + prestataire si nécessaire)
3. **8h** : Restauration sur serveur de secours (si disponible) OU réparation serveur principal
4. **24h** : Service rétabli + vérification intégrité données
5. **Post-Incident** : Report deadline correction de 2 jours

**Prérequis** :
- Sauvegarde à jour (< 24h)
- Serveur de secours configuré (optionnel mais recommandé)
- Procédure de restauration testée trimestriellement

#### Scénario 2 : Corruption de la Base de Données

**Durée d'Indisponibilité Acceptable** : 4h

**Plan d'Action** :
1. **Immédiat** : Isolation du serveur (arrêt service)
2. **1h** : Évaluation étendue de la corruption (Admin NSI)
3. **2h** : Restauration depuis dernière sauvegarde saine
4. **4h** : Tests de vérification + remise en service
5. **Post-Incident** : Récupération manuelle des corrections effectuées depuis la sauvegarde (si possible via localStorage navigateur)

#### Scénario 3 : Violation de Données (Fuite)

**Délai de Notification CNIL** : 72h

**Plan d'Action** :
1. **Immédiat** : Isolation du système + préservation des preuves
2. **2h** : Évaluation de la portée (données concernées, nombre de personnes)
3. **6h** : Notification Proviseur + DPO + cellule de crise
4. **24h** : Mesures de confinement + correction de la faille
5. **72h** : Notification CNIL (si risque pour les personnes)
6. **7j** : Notification personnes concernées (si risque élevé) + communication interne
7. **1 mois** : Post-mortem + plan d'action préventif

**Document de Référence** : [Manuel Sécurité - Incident Response](../security/MANUEL_SECURITE.md#8-incident-response)

### 8.3 Gestion de Crise - Procédure d'Escalade

#### Niveaux de Criticité

| Niveau | Exemple | Délai de Résolution | Autorité |
|--------|---------|---------------------|----------|
| **P4 - Info** | Utilisateur a oublié son mot de passe | 48h | Admin / Support |
| **P3 - Mineur** | Service lent, annotation non sauvegardée | 24h | Admin NSI |
| **P2 - Moyen** | Service indisponible (hors période critique) | 8h | Admin NSI + Proviseur Adjoint |
| **P1 - Grave** | Service indisponible (période d'examen) | 4h | Cellule de Crise |
| **P0 - Critique** | Violation de données, faille de sécurité | Immédiat | Cellule de Crise + CNIL |

#### Cellule de Crise (P0/P1)

**Composition** :
- Proviseur (décisions stratégiques)
- Admin NSI (résolution technique)
- DPO (conformité RGPD)
- Référent Communication (communication externe si nécessaire)

**Contact** : Numéros de téléphone + email (liste à jour et testée semestriellement)

**Salle de Crise** : Salle de réunion dédiée (ou visioconférence)

---

## 9. Support et Maintenance

### 9.1 Modèle de Support

#### Support de Niveau 1 (Utilisateurs)

**Ressources** :
- [FAQ](../support/FAQ.md) : Questions fréquentes par rôle
- [Guide de Dépannage](../support/DEPANNAGE.md) : Problèmes courants et solutions
- Professeur Référent : Support téléphonique/email (heures de bureau)

**SLA** : Réponse sous 48h (hors vacances scolaires)

#### Support de Niveau 2 (Technique)

**Ressources** :
- Admin NSI : Support technique (incidents, configuration)
- Prestataire Externe (si applicable) : Support expert

**SLA** :
- Incident P3 : Résolution sous 24h
- Incident P2 : Résolution sous 8h
- Incident P1/P0 : Résolution immédiate

#### Support de Niveau 3 (Éditeur/Développeur)

**Ressources** :
- Communauté Open-Source (GitHub Issues)
- Documentation Technique ([docs/TECHNICAL_MANUAL.md](../TECHNICAL_MANUAL.md))

**SLA** : Pas de SLA garanti (dépend de la communauté)

### 9.2 Maintenance Préventive

#### Quotidienne (Automatisée)

- Sauvegarde incrémentale (1h du matin)
- Purge des logs > 1 an
- Nettoyage des sessions expirées
- Monitoring CPU/RAM/Disque

#### Hebdomadaire (Admin NSI - 30 min)

- Sauvegarde complète (dimanche 2h)
- Vérification de l'intégrité des sauvegardes
- Revue des logs d'erreur
- Surveillance de l'espace disque

#### Mensuelle (Admin NSI - 1h)

- Mise à jour de sécurité (OS + dépendances)
- Test de restauration (sauvegarde aléatoire)
- Revue des comptes utilisateurs inactifs
- Analyse des KPI (performance, usage)

#### Trimestrielle (Comité de Pilotage - 2h)

- Revue des incidents
- Analyse des retours utilisateurs
- Planification des évolutions
- Test du PRA (simulation panne)

#### Annuelle (Audit Complet - 1 jour)

- Audit de sécurité (vulnérabilités)
- Audit de conformité RGPD
- Revue de la documentation
- Formation de rappel (enseignants)
- Mise à jour majeure (si disponible)

### 9.3 Mises à Jour et Évolutions

#### Politique de Mise à Jour

| Type | Fréquence | Déploiement | Communication |
|------|-----------|-------------|---------------|
| **Correctifs de Sécurité** | Immédiat (si critique) | Hors heures de cours | Email urgent |
| **Correctifs Bugs** | Mensuel | Week-end | Note de version |
| **Améliorations Mineures** | Trimestriel | Vacances scolaires | Email + formation courte |
| **Nouvelles Fonctionnalités** | Annuel | Vacances d'été | Formation complète |

#### Procédure de Mise à Jour

1. **Notification** : Email 2 semaines avant (sauf sécurité critique)
2. **Sauvegarde** : Snapshot complet avant mise à jour
3. **Test** : Environnement de pré-production (si disponible)
4. **Déploiement** : Hors heures de cours (samedi matin recommandé)
5. **Vérification** : Tests post-déploiement (connexion, correction, export)
6. **Rollback** : Si problème majeur détecté, retour à la version précédente (sous 1h)
7. **Communication** : Confirmation mise à jour réussie

### 9.4 Formation et Accompagnement

#### Formation Initiale

**Enseignants** (1h30 par groupe de 10) :
- Introduction à Korrigo (10 min)
- Démonstration correction numérique (20 min)
- Pratique guidée (40 min)
- Q&A (20 min)

**Administrateurs** (3h) :
- Gestion des utilisateurs (30 min)
- Création d'examens (30 min)
- Identification de copies (30 min)
- Export Pronote (30 min)
- Sauvegardes et maintenance (30 min)
- Sécurité et RGPD (30 min)

**Secrétariat** (2h) :
- Import élèves (30 min)
- Identification des copies (1h)
- Cas spéciaux (30 min)

#### Formation Continue

- **Webinaire Trimestriel** : Nouvelles fonctionnalités (30 min)
- **Documentation en Ligne** : Mise à jour continue
- **Vidéos Tutorielles** : Tâches courantes (3-5 min chacune)

#### Ressources de Formation

- [Guide Enseignant](../users/GUIDE_ENSEIGNANT.md)
- [Guide Utilisateur Admin](./GUIDE_UTILISATEUR_ADMIN.md)
- [Guide Secrétariat](../users/GUIDE_SECRETARIAT.md)
- [FAQ](../support/FAQ.md)
- [Vidéos (playlist YouTube)](https://example.com/korrigo-tutorials) - À créer

---

## 10. Glossaire

| Terme | Définition |
|-------|------------|
| **Anonymisation** | Masquage de l'identité de l'élève lors de la correction (numéro d'anonymat) |
| **Annotation** | Commentaire, note, surlignage ou correction ajouté par l'enseignant sur la copie numérique |
| **API** | Application Programming Interface - Interface permettant l'échange de données entre Korrigo et d'autres systèmes (ex: Pronote) |
| **Barème** | Structure hiérarchique définissant les exercices, questions et points d'un examen |
| **Booklet** | Fascicule détecté automatiquement lors du découpage (4 pages A4) |
| **Celery** | Système de traitement asynchrone pour les tâches longues (découpage PDF, OCR) |
| **CNIL** | Commission Nationale de l'Informatique et des Libertés (autorité de contrôle RGPD en France) |
| **Copy** | Copie d'élève validée et prête à être corrigée |
| **CSRF** | Cross-Site Request Forgery - Protection contre les attaques par falsification de requête |
| **Docker** | Technologie de conteneurisation utilisée pour le déploiement de Korrigo |
| **DPO** | Data Protection Officer - Délégué à la Protection des Données |
| **Finalisation** | Action de valider définitivement une copie corrigée (calcul note, génération PDF) |
| **GradingEvent** | Événement d'audit (log) enregistrant une action de correction |
| **INE** | Identifiant National Élève (numéro unique de 11 caractères) |
| **Korrigo PMF** | Plateforme de correction numérique (PMF = "Plus de Mystère avec les Fascicules") |
| **Lock** | Verrou empêchant qu'une copie soit corrigée par deux enseignants simultanément |
| **OCR** | Optical Character Recognition - Reconnaissance optique de caractères (lecture automatique du nom manuscrit) |
| **PDF** | Portable Document Format - Format de fichier utilisé pour les copies scannées |
| **PostgreSQL** | Système de gestion de base de données utilisé par Korrigo |
| **Pronote** | Logiciel de gestion de vie scolaire utilisé dans les lycées français |
| **RBAC** | Role-Based Access Control - Contrôle d'accès basé sur les rôles (Admin, Enseignant, Élève) |
| **Redis** | Système de cache et de gestion de files de tâches |
| **RGPD** | Règlement Général sur la Protection des Données (GDPR en anglais) |
| **Rasterisation** | Conversion d'un PDF en images (une image par page) |
| **Snapshot** | Capture instantanée de l'état de la base de données à un moment donné |
| **SSL/TLS** | Protocoles de chiffrement pour sécuriser les connexions HTTPS |
| **Staging** | État intermédiaire d'une copie (créée mais non validée) |
| **Vue.js** | Framework JavaScript utilisé pour l'interface utilisateur de Korrigo |

---

## Conclusion

Korrigo PMF représente une opportunité de moderniser la correction d'examens tout en renforçant la protection des données des élèves. Ce guide a présenté tous les aspects nécessaires à une prise de décision éclairée et à un déploiement réussi.

### Points Clés à Retenir

- **Conformité RGPD** : Korrigo est conçu pour respecter les exigences légales françaises
- **Sécurité** : Architecture défensive multicouche avec audit complet
- **ROI** : Retour sur investissement en 2 ans (économies temps + archivage)
- **Support** : Documentation exhaustive et support par niveaux
- **Gouvernance** : Rôles et responsabilités clairs

### Prochaines Étapes

1. **Présentation au Conseil d'Administration** (délibération)
2. **Validation du budget** (5 700 € initial + 1 150 €/an)
3. **Désignation de l'équipe de pilotage**
4. **Commande du matériel** (serveur + scanner si nécessaire)
5. **Planification du déploiement** (8 semaines)

### Documents Complémentaires

- [Guide Utilisateur Admin (Technique)](./GUIDE_UTILISATEUR_ADMIN.md)
- [Procédures Opérationnelles](./PROCEDURES_OPERATIONNELLES.md)
- [Politique RGPD](../security/POLITIQUE_RGPD.md)
- [Manuel Sécurité](../security/MANUEL_SECURITE.md)
- [FAQ](../support/FAQ.md)

---

**Contact** :  
**Proviseur** : proviseur@lycee-exemple.fr  
**Admin NSI** : admin.nsi@lycee-exemple.fr  
**Support Korrigo** : support@korrigo-pmf.fr (si applicable)

**Dernière Mise à Jour** : 30 janvier 2026  
**Version du Document** : 1.0.0
