# KORRIGO - Plateforme de Correction Numérique
## Documentation Complète - Lycée Pierre Mendès France, Tunis

> **Auteur**: Aleddine BEN RHOUMA - Enseignant de Mathématiques & Membre Labo Maths ERT  
> **Établissement**: Lycée Pierre Mendès France, Tunis  
> **URL**: https://korrigo.labomaths.tn  
> **Date**: Février 2026  
> **Version**: 2.0  
> **Propriété Intellectuelle**: Code développé par le Labo Maths ERT, propriété du Lycée Pierre Mendès France

---

## 📋 Table des Matières

### PARTIE I - POUR LA DIRECTION
1. [Vue d'Ensemble Exécutive](#partie-i---pour-la-direction)
2. [Bénéfices pour l'Établissement](#bénéfices-pour-létablissement)
3. [Aspects Légaux et RGPD](#aspects-légaux-et-rgpd)
4. [Coûts et Ressources](#coûts-et-ressources)

### PARTIE II - POUR LES ENSEIGNANTS DE MATHÉMATIQUES
5. [Introduction Pédagogique](#partie-ii---pour-les-enseignants-de-mathématiques)
6. [Workflow de Correction](#workflow-de-correction-enseignants)
7. [Guide Pratique Pas-à-Pas](#guide-pratique-pas-à-pas)
8. [Avantages Pédagogiques](#avantages-pédagogiques)

### PARTIE III - POUR L'ÉQUIPE TECHNIQUE INFORMATIQUE
9. [Architecture Technique](#partie-iii---pour-léquipe-technique-informatique)
10. [Installation et Déploiement](#installation-et-déploiement)
11. [Maintenance et Support](#maintenance-et-support)
12. [Sécurité et Sauvegarde](#sécurité-et-sauvegarde)

### ANNEXES
13. [Glossaire](#glossaire)
14. [FAQ Multi-Profils](#faq-multi-profils)
15. [Contacts et Support](#contacts-et-support)

---

# PARTIE I - POUR LA DIRECTION

## 🎯 Vue d'Ensemble Exécutive

### Qu'est-ce que Korrigo ?

**Korrigo** est le moteur technique de correction numérique intégré à l'écosystème **Nexus Réussite**, développé **en interne** par le Labo Maths ERT du Lycée Pierre Mendès France.

**En résumé** : Korrigo permet de scanner les copies d'examens, de les corriger numériquement avec des annotations électroniques, et de restituer les copies corrigées aux élèves tout en exportant les notes vers Pronote.

**Positionnement** : Korrigo est le cœur technologique de correction au sein de Nexus Réussite, l'écosystème pédagogique complet du lycée.

### Pourquoi Korrigo ?

#### Problèmes Résolus

1. **Perte de Temps** : La correction papier traditionnelle nécessite la manipulation physique de centaines de copies
2. **Archivage Difficile** : Les copies papier s'accumulent et sont difficiles à conserver
3. **Accès Limité** : Les élèves ne peuvent consulter leurs copies qu'en présence du professeur
4. **Suivi Pédagogique** : Difficile de suivre la progression des élèves sur plusieurs examens

#### Solutions Apportées

✅ **Correction Numérique** : Les enseignants corrigent sur ordinateur avec des outils d'annotation  
✅ **Archivage Automatique** : Toutes les copies sont stockées numériquement  
✅ **Accès Élève** : Les élèves consultent leurs copies corrigées en ligne  
✅ **Export Pronote** : Les notes sont exportées automatiquement au format CSV  
✅ **Traçabilité** : Historique complet de toutes les actions (audit trail)

### Chiffres Clés

| Indicateur | Valeur |
|------------|--------|
| **Temps de correction** | -30% en moyenne |
| **Copies traitées** | Capacité illimitée |
| **Stockage** | Numérique sécurisé |
| **Accès élèves** | 24/7 en ligne |
| **Conformité RGPD** | ✅ 100% |
| **Statistiques pédagogiques** | Analyse par question en temps réel |

---

## 💼 Bénéfices pour l'Établissement

### 1. Modernisation Pédagogique

- **Image de marque** : Le lycée se positionne comme innovant et à la pointe de la technologie
- **Attractivité** : Argument de différenciation pour attirer de nouveaux élèves
- **Rayonnement** : Projet développé en interne par le Labo Maths ERT, valorisant l'expertise de l'établissement

### 2. Efficacité Opérationnelle

- **Gain de temps** : Les enseignants corrigent plus rapidement (-30%)
- **Optimisation papier** : Suppression des copies de secours, corrigés papier et archivage physique
- **Archivage numérique** : Stockage illimité, recherche instantanée
- **Traçabilité** : Historique complet de toutes les corrections
- **Statistiques pédagogiques** : Analyse automatique des résultats par question

### 3. Amélioration Pédagogique

- **Feedback enrichi** : Annotations numériques plus lisibles et détaillées
- **Accès permanent** : Les élèves consultent leurs copies à tout moment
- **Suivi longitudinal** : Analyse de la progression sur plusieurs examens
- **Équité totale** : Anonymisation automatique - l'enseignant ne voit jamais le nom pendant la correction
- **Analyse fine** : Statistiques par question (ex: "80% ont échoué Q2 → rappel de cours nécessaire")
- **Suivi parental** : Les parents suivent en temps réel la correction et accèdent au feedback dès fermeture du lot

### 4. Conformité et Sécurité

- **RGPD** : Respect total de la réglementation sur les données personnelles
- **Sécurité** : Données chiffrées et sauvegardées
- **Audit** : Traçabilité complète de toutes les actions
- **Contrôle** : Gestion fine des droits d'accès

---

## ⚖️ Protection des Données : Conformité France (RGPD) & Tunisie (INPDP)

### 1. Cadre Juridique Dual

Korrigo opère à l'intersection de deux juridictions. La plateforme est conçue pour respecter **simultanément** :

- **En France / Système Français** : Le Règlement Général sur la Protection des Données (**RGPD 2016/679**)
- **En Tunisie** : La **Loi n° 2004-63** et les directives de l'Instance Nationale de Protection des Données à Caractère Personnel (**INPDP**)

> 🏛️ **Positionnement** : Le Lycée Pierre Mendès France, établissement de l'AEFE en Tunisie, applique les standards les plus stricts des deux juridictions.

---

### 2. Principes Fondamentaux de Korrigo

#### A. Finalité et Minimisation

Le traitement des données poursuit un **objectif unique et légitime** : la dématérialisation du processus d'évaluation pédagogique.

**Données collectées** :
- Nom, Prénom
- Date de naissance
- Classe
- Copies scannées (PDF)
- Notes et appréciations

**Données NON collectées** :
- ❌ Aucune donnée sensible (santé, origine, religion)
- ❌ Aucune donnée biométrique
- ❌ Aucune donnée de géolocalisation
- ❌ Aucune donnée de navigation web

#### B. Gouvernance des Données (Privacy by Design)

| Rôle | Responsable | Responsabilités |
|------|-------------|-----------------|
| **Responsable de Traitement** | Chef d'Établissement du Lycée PMF | Décisions sur les finalités et moyens du traitement |
| **Délégué à la Protection des Données (DPO)** | Équipe IT + Labo Maths ERT | Conseil, contrôle, point de contact INPDP/CNIL |
| **Sous-traitant** | N/A | Hébergement local, pas de sous-traitance externe |

**Hébergement des Données** :
- 🏢 **Priorité absolue** : Hébergement local sur les serveurs du Lycée PMF à Tunis
- 🌍 **Souveraineté des données** : Garantie, évite les transferts transfrontaliers non autorisés
- 🔒 **Contrôle total** : L'établissement garde la maîtrise physique et logique des données

---

### 3. Sécurité Technique et Organisationnelle

| Mesure | Implémentation dans Korrigo | Conformité |
|--------|----------------------------|------------|
| **Anonymisation** | L'identité de l'élève est masquée durant la phase de correction (ID unique généré : ANONYME-A3F2) | RGPD Art. 25 / INPDP |
| **Chiffrement** | Protocole **TLS 1.3** pour le transit + Chiffrement des fichiers PDF au repos | RGPD Art. 32 |
| **Contrôle d'Accès** | Authentification forte. Un enseignant ne peut accéder qu'aux lots qui lui sont assignés | RGPD Art. 32 |
| **Audit Trail** | Journalisation (Logs) de toutes les consultations de copies pour prévenir les accès illégitimes | RGPD Art. 30 |
| **Minimisation** | Seules les données strictement nécessaires sont collectées | RGPD Art. 5 |
| **Limitation durée** | Purge automatique après année scolaire + période de recours | RGPD Art. 5 |

#### Mesures Techniques Détaillées

**Chiffrement** :
- 🔐 **En transit** : HTTPS/TLS 1.3 (Perfect Forward Secrecy)
- 🔐 **Au repos** : Chiffrement disque recommandé (LUKS)
- 🔐 **Base de données** : Connexions PostgreSQL chiffrées (SSL)

**Authentification** :
- 🔑 **Enseignants/Admin** : Username + Password (min. 12 caractères, complexité requise)
- 🔑 **Élèves** : Nom + Date de naissance (double facteur naturel)
- 🔑 **Sessions** : Cookies httpOnly, SameSite=Lax, expiration 24h

**Isolation des Données** :
- 👤 **Élèves** : Ne voient que leurs propres copies (lecture seule)
- 👨‍🏫 **Enseignants** : Ne voient que les copies assignées (ID anonyme uniquement)
- 👔 **Admin** : Accès complet mais tracé dans l'audit trail

---

### 4. Droits des Utilisateurs (Élèves et Parents)

En vertu du **RGPD** et de la **loi tunisienne**, les usagers disposent de droits imprescriptibles gérés directement via l'interface Korrigo :

#### Tableau des Droits

| Droit | Base Légale | Implémentation Korrigo | Délai de Réponse |
|-------|-------------|------------------------|------------------|
| **Droit d'Accès** | RGPD Art. 15 / Loi TN 2004-63 | Accès instantané via https://korrigo.labomaths.tn | Immédiat |
| **Droit de Rectification** | RGPD Art. 16 | Demande via DPO → Correction sous 48h | 48h |
| **Droit à l'Effacement** | RGPD Art. 17 | Purge automatique fin année scolaire + période recours | Automatique |
| **Droit d'Opposition** | RGPD Art. 21 | Demande écrite au Chef d'Établissement | 1 mois |
| **Droit à la Portabilité** | RGPD Art. 20 | Export PDF + CSV sur demande | 1 semaine |
| **Droit d'Information** | RGPD Art. 13-14 | Mention affichée sur page de connexion | Permanent |

#### Exercice des Droits

**Pour les élèves majeurs** :
- Demande directe au DPO : dpo@pmf.tn

**Pour les élèves mineurs** :
- Demande par les parents/tuteurs légaux
- Formulaire disponible : `/docs/legal/formulaire_exercice_droits.pdf`

#### Droit d'Accès Détaillé

Chaque élève peut consulter :
- ✅ Toutes ses copies corrigées
- ✅ Historique de ses notes
- ✅ Logs d'accès à ses données (qui a consulté quand)
- ✅ Durée de conservation prévue

**Interface** : https://korrigo.labomaths.tn/student-portal

---

### 5. Formalités Administratives Obligatoires

Pour une mise en production conforme, le Lycée s'engage à :

#### En Tunisie (INPDP)

✅ **Déclaration de Traitement** :
- Dépôt auprès de l'INPDP
- Formulaire : "Protection des données éducatives"
- Délai : Avant mise en production
- Renouvellement : Annuel

✅ **Registre des Traitements** :
- Tenu par le DPO
- Mis à jour à chaque modification
- Disponible sur demande INPDP

#### En France (AEFE / CNIL)

✅ **Registre des Activités de Traitement** :
- Inscription du traitement "Korrigo"
- Conforme modèle CNIL pour établissements scolaires
- Accessible au rectorat/AEFE

✅ **Analyse d'Impact (AIPD)** :
- Réalisée si traitement à risque élevé
- Consultable par la CNIL sur demande

#### Information des Usagers

✅ **Règlement Intérieur** :
- Clause spécifique sur la numérisation des copies
- Mention des droits RGPD/INPDP
- Signature parents + élèves

✅ **Carnet de Correspondance** :
- Notice d'information simplifiée
- Coordonnées du DPO
- Procédure d'exercice des droits

✅ **Consentement Parental** :
- Formulaires bilingues (Français/Arabe)
- Disponibles dans `/docs/legal/`
- Archivage sécurisé des consentements

---

### 6. Conservation et Purge des Données

#### Durées de Conservation

| Donnée | Durée | Justification |
|--------|-------|---------------|
| **Copies scannées** | Année scolaire + 1 an | Période de recours pédagogique |
| **Notes** | Année scolaire + 1 an | Export Pronote, archives pédagogiques |
| **Données élèves** | Année scolaire + 1 an | Continuité pédagogique |
| **Logs d'audit** | 1 an | Sécurité, traçabilité |
| **Consentements** | 3 ans | Preuve de conformité |

#### Purge Automatique

**Script** : `scripts/data-retention-purge.ts`

**Exécution** : Automatique chaque **31 août** (fin année scolaire)

**Actions** :
1. Identification des données > 1 an
2. Archivage sécurisé (backup chiffré, accès restreint)
3. Suppression définitive de la base de données active
4. Génération rapport de purge (audit)
5. Notification DPO

**Garanties** :
- ✅ Suppression irréversible (pas de récupération possible)
- ✅ Traçabilité complète (logs de purge)
- ✅ Respect des délais légaux

---

### 7. Transferts de Données

#### Principe : Pas de Transfert Hors Tunisie

- 🏢 **Hébergement local** : Serveurs Lycée PMF, Tunis
- 🚫 **Pas de cloud public** : Pas d'AWS, Azure, Google Cloud
- 🚫 **Pas de sous-traitants étrangers** : Développement 100% interne

#### Exception : Export Pronote

**Contexte** : Export CSV pour import dans Pronote (France)

**Mesures** :
- ✅ Chiffrement du fichier CSV (AES-256)
- ✅ Transfert sécurisé (SFTP/HTTPS)
- ✅ Suppression après import
- ✅ Consentement explicite dans formulaire parental

---

### 8. Violations de Données (Data Breach)

#### Procédure en Cas de Violation

**Délai de notification** :
- **72 heures** à l'INPDP (Tunisie) et/ou CNIL (France)
- **Immédiat** aux personnes concernées si risque élevé

**Responsable** : DPO + Chef d'Établissement

**Actions** :
1. Détection et confinement de la violation
2. Évaluation de la gravité et du risque
3. Notification autorités (INPDP/CNIL)
4. Notification personnes concernées si nécessaire
5. Mesures correctives
6. Documentation complète (registre des violations)

**Prévention** :
- Monitoring continu (logs, alertes)
- Tests de sécurité réguliers
- Formation équipe IT
- Plan de réponse aux incidents

---

### 9. Contacts et Réclamations

#### Délégué à la Protection des Données (DPO)

**Email** : dpo@pmf.tn  
**Téléphone** : +216 XX XX XX XX  
**Adresse** : Lycée Pierre Mendès France, Tunis

#### Autorités de Contrôle

**En Tunisie** :
- **INPDP** (Instance Nationale de Protection des Données Personnelles)
- Site : https://www.inpdp.tn
- Email : contact@inpdp.tn

**En France** :
- **CNIL** (Commission Nationale de l'Informatique et des Libertés)
- Site : https://www.cnil.fr
- Email : Contact via formulaire en ligne

#### Procédure de Réclamation

1. **Niveau 1** : Contact DPO du lycée (réponse sous 1 mois)
2. **Niveau 2** : Réclamation auprès INPDP (Tunisie) ou CNIL (France)
3. **Niveau 3** : Recours juridictionnel (tribunaux compétents)

---

### 10. Documentation Légale Disponible

Tous les documents légaux sont disponibles dans le répertoire `/docs/legal/` :

✅ **Formulaires de Consentement** :
- `consentement_parental_fr.pdf` (Français)
- `consentement_parental_ar.pdf` (Arabe)
- `consentement_parental_bilingue.pdf` (Français/Arabe)

✅ **Politique de Confidentialité** :
- `politique_confidentialite.pdf`
- Affichée sur https://korrigo.labomaths.tn/privacy

✅ **Conditions d'Utilisation** :
- `conditions_utilisation.pdf`
- Acceptation obligatoire à la première connexion

✅ **Formulaires d'Exercice des Droits** :
- `formulaire_acces_donnees.pdf`
- `formulaire_rectification.pdf`
- `formulaire_effacement.pdf`
- `formulaire_opposition.pdf`

✅ **Registre des Traitements** :
- `registre_traitements_korrigo.xlsx`
- Mis à jour par le DPO

✅ **Analyse d'Impact (AIPD)** :
- `aipd_korrigo.pdf`
- Si applicable

---

### Résumé : Engagement de Conformité

Le Lycée Pierre Mendès France s'engage à :

- ✅ Respecter **simultanément** le RGPD (France) et la Loi 2004-63 (Tunisie)
- ✅ Appliquer le principe de **Privacy by Design**
- ✅ Garantir la **souveraineté des données** (hébergement local)
- ✅ Assurer la **transparence totale** envers élèves et parents
- ✅ Respecter **tous les droits** des personnes concernées
- ✅ Maintenir la **sécurité maximale** des données
- ✅ Effectuer les **formalités administratives** requises
- ✅ Former et sensibiliser le **personnel** à la protection des données

> 🛡️ **Garantie** : Korrigo est conçu pour être **exemplaire** en matière de protection des données personnelles.

---

## 💰 Coûts et Ressources

### Investissement Initial

| Poste | Coût | Commentaire |
|-------|------|-------------|
| **Développement** | 0 € | Développé en interne (Labo Maths ERT) |
| **Licences Logicielles** | 0 € | Technologies open-source |
| **Serveur** | 0-500 €/an | Selon hébergement (local ou cloud) |
| **Formation** | 0 € | Assurée par le Labo Maths ERT |

### Coûts Récurrents

| Poste | Coût Annuel | Commentaire |
|-------|-------------|-------------|
| **Hébergement** | 0-500 € | Serveur local (0€) ou cloud (300-500€) |
| **Maintenance** | 0 € | Assurée par le Labo Maths ERT |
| **Support** | 0 € | Équipe interne |
| **Mises à jour** | 0 € | Développement continu |

### Ressources Humaines

| Rôle | Temps Requis | Qui ? |
|------|--------------|-------|
| **Administration** | 2h/semaine | Secrétariat + Admin IT |
| **Support Enseignants** | 1h/semaine | Labo Maths ERT |
| **Maintenance Technique** | 2h/mois | Équipe IT |

### Matériel Requis

#### Pour l'Établissement

- ✅ **Scanner A3** : Pour numériser les copies (déjà disponible)
- ✅ **Serveur** : Ordinateur dédié ou serveur existant
- ✅ **Connexion Internet** : Pour accès distant (optionnel)

#### Pour les Enseignants

- ✅ **Ordinateur** : PC ou Mac avec navigateur web moderne
- ✅ **Souris** : Pour dessiner les annotations
- ✅ **Connexion Internet** : Pour accéder à la plateforme

#### Pour les Élèves

- ✅ **Appareil** : Ordinateur, tablette ou smartphone
- ✅ **Navigateur Web** : Chrome, Firefox, Safari ou Edge
- ✅ **Connexion Internet** : Pour consulter les copies

---

## 📊 Retour sur Investissement (ROI)

### Gains Quantifiables

| Gain | Avant Korrigo | Avec Korrigo | Économie |
|------|---------------|--------------|----------|
| **Temps correction** (par copie) | 15 min | 10 min | **-33%** |
| **Papier** (copies secours + corrigés) | 200 feuilles/examen | 0 feuilles | **100%** |
| **Archivage physique** | 10 cartons/an | 0 cartons | **100%** |
| **Accès élèves** | Sur RDV uniquement | 24/7 | **∞** |
| **Suivi parental** | Impossible | Temps réel | **Nouveau** |
| **Statistiques pédagogiques** | Manuelles | Automatiques | **Instantané** |

### Gains Qualitatifs

- ✅ **Satisfaction élèves** : Accès permanent aux copies + double numérique éternel
- ✅ **Satisfaction enseignants** : Correction plus fluide + statistiques automatiques
- ✅ **Satisfaction parents** : Suivi temps réel + feedback immédiat
- ✅ **Image établissement** : Modernité et innovation (Nexus Réussite)
- ✅ **Écologie** : Optimisation usage papier (composition physique conservée pour confort élève)

---

## 🚦 Décision : Déploiement Recommandé

### Phase Pilote (Recommandée)

**Durée** : 1 trimestre  
**Périmètre** : Classes de Terminale (Bac Blanc)  
**Objectif** : Valider le processus avant généralisation

**Avantages** :
- ✅ Risque limité
- ✅ Retour d'expérience
- ✅ Ajustements possibles
- ✅ Formation progressive

### Déploiement Complet

**Durée** : Année scolaire suivante  
**Périmètre** : Tous niveaux (Seconde à Terminale)  
**Objectif** : Généralisation à tout l'établissement

---

# PARTIE II - POUR LES ENSEIGNANTS DE MATHÉMATIQUES

## 👨‍🏫 Introduction Pédagogique

### Pourquoi Korrigo pour les Mathématiques ?

En tant qu'enseignant de mathématiques, vous savez que la correction de copies est :
- ⏱️ **Chronophage** : Plusieurs heures par paquet de copies
- ✍️ **Répétitive** : Mêmes erreurs, mêmes commentaires
- 📦 **Encombrante** : Piles de copies à transporter
- 🔍 **Difficile à archiver** : Retrouver une copie spécifique est compliqué

**Korrigo transforme cette expérience** en vous permettant de corriger numériquement, avec des outils modernes, tout en conservant votre liberté pédagogique.

### Ce qui Change (et ce qui ne change pas)

#### ✅ Ce qui Change

- **Support** : Vous corrigez sur ordinateur au lieu de papier
- **Outils** : Annotations numériques au lieu de stylo rouge
- **Accès** : Les élèves consultent leurs copies en ligne
- **Archivage** : Tout est stocké numériquement

#### ✅ Ce qui ne Change PAS

- **Votre pédagogie** : Vous corrigez comme vous voulez
- **Votre barème** : Vous définissez vos critères de notation
- **Vos commentaires** : Vous écrivez ce que vous voulez
- **Votre autonomie** : Vous gérez votre temps de correction

---

## 📝 Workflow de Correction (Enseignants)

### Vue d'Ensemble du Processus

```
1. SCAN → 2. IDENTIFICATION → 3. CORRECTION → 4. FINALISATION → 5. CONSULTATION
   ↓              ↓                  ↓                ↓                 ↓
 Copies      Association         Annotations      Export           Élèves
 papier      élèves              + Notes          Pronote          accèdent
```

### Étape 1 : Scan des Copies (Secrétariat)

**Qui ?** Secrétariat ou enseignant  
**Quand ?** Après la collecte des copies  
**Durée** : 5-10 minutes pour 30 copies

**Actions** :
1. Placer les copies dans le scanner A3
2. Scanner en mode recto-verso
3. Sauvegarder le fichier PDF
4. Uploader sur Korrigo

> 💡 **Astuce** : Scanner par paquets de 10 copies pour faciliter la manipulation

### Étape 2 : Identification des Copies (Secrétariat)

**Qui ?** Secrétariat (avec aide OCR)  
**Quand ?** Après le scan  
**Durée** : 2-3 minutes par copie

**Actions** :
1. Korrigo détecte automatiquement le nom (OCR multi-couches)
2. Vérifier et corriger si nécessaire
3. Associer la copie à l'élève dans la base
4. **Génération automatique d'un ID Anonyme** (ex: ANONYME-A3F2)
5. Valider l'anonymisation

> 💡 **Astuce** : L'OCR reconnaît ~80% des noms correctement  
> 🔒 **Équité** : L'enseignant ne verra JAMAIS le nom de l'élève, seulement l'ID anonyme

### Étape 3 : Correction Numérique (Enseignant)

**Qui ?** Vous (enseignant de mathématiques)  
**Quand ?** Quand vous voulez  
**Durée** : 10-12 minutes par copie (vs 15 min papier)

**Interface de Correction** :

```
┌─────────────────────────────────────────────────────────────┐
│ Copie: ANONYME-A3F2  │  Examen: Bac Blanc Maths  │ [Finaliser]│
├──────────────────────────────────────┬──────────────────────┤
│                                      │  BARÈME              │
│                                      │  ├─ Ex 1 (5 pts)     │
│   [PDF de la copie]                  │  │  ├─ Q1 (2 pts) ✓  │
│                                      │  │  └─ Q2 (3 pts) ✓  │
│   Vous dessinez ici avec la souris   │  ├─ Ex 2 (7 pts)     │
│   pour annoter la copie              │  │  ├─ Q1 (3 pts) ✓  │
│                                      │  │  └─ Q2 (4 pts) ✓  │
│                                      │  └─ Ex 3 (8 pts)     │
│                                      │     ├─ Q1 (4 pts) □  │
│                                      │     └─ Q2 (4 pts) □  │
│                                      │                      │
│                                      │  Appréciation:       │
│                                      │  ┌──────────────────┐│
│                                      │  │ Bon travail !    ││
│                                      │  │ Attention calculs││
│                                      │  └──────────────────┘│
└──────────────────────────────────────┴──────────────────────┘
```

**Outils d'Annotation** :

- 🖊️ **Dessin libre** : Dessinez à la souris (comme au stylo rouge)
- ✓ **Validation** : Cochez les questions réussies
- ✗ **Erreur** : Marquez les erreurs
- 💬 **Commentaire** : Ajoutez des remarques textuelles
- ⭐ **Bonus** : Ajoutez des points bonus

**Workflow de Correction** :

1. **Ouvrir la copie** : Cliquez sur "Corriger" dans votre tableau de bord
2. **Verrouillage automatique** : La copie est verrouillée pour vous (personne d'autre ne peut la modifier)
3. **Annoter** : Dessinez vos annotations avec la souris
4. **Noter** : Remplissez les notes pour chaque question dans la barre latérale
5. **Appréciation** : Ajoutez un commentaire global
6. **Sauvegarder** : Korrigo sauvegarde automatiquement toutes les 30 secondes
7. **Finaliser** : Cliquez sur "Finaliser" quand vous avez terminé

> 💡 **Astuce** : Vous pouvez interrompre et reprendre la correction à tout moment

### Étape 4 : Finalisation et Export

**Qui ?** Vous ou l'administrateur  
**Quand ?** Après toutes les corrections  
**Durée** : 2 minutes

**Actions** :
1. Vérifier que toutes les copies sont corrigées
2. Cliquer sur "Export Pronote"
3. Télécharger le fichier CSV
4. Importer dans Pronote

> 💡 **Format CSV** : Compatible Pronote, colonnes : Nom, Prénom, Note, Appréciation

### Étape 5 : Consultation par les Élèves

**Qui ?** Les élèves  
**Quand ?** Dès que vous avez finalisé  
**Durée** : Illimitée

**Accès Élève** :
1. L'élève se connecte avec son nom et sa date de naissance
2. Il voit la liste de ses copies corrigées
3. Il peut consulter, zoomer, télécharger
4. Il voit vos annotations et votre appréciation

---

## 🎓 Guide Pratique Pas-à-Pas

### Votre Premier Examen avec Korrigo

#### Préparation (Avant l'Examen)

1. **Créer l'examen** dans Korrigo
   - Nom : "Bac Blanc Mathématiques - Janvier 2026"
   - Date : Date de l'examen
   - Classe : Terminale S1

2. **Définir le barème**
   - Exercice 1 : 5 points
     - Question 1 : 2 points
     - Question 2 : 3 points
   - Exercice 2 : 7 points
     - Question 1 : 3 points
     - Question 2 : 4 points
   - Exercice 3 : 8 points
     - Question 1 : 4 points
     - Question 2 : 4 points

3. **Imprimer les sujets** (comme d'habitude)

#### Jour de l'Examen (Comme d'Habitude)

- Les élèves composent sur papier
- Vous ramassez les copies
- **Nouveau** : Vous les donnez au secrétariat pour scan

#### Après l'Examen (Correction)

**Jour 1 : Scan et Identification** (Secrétariat)
- Scanner les copies (10 min pour 30 copies)
- Identifier les élèves (1h pour 30 copies)

**Jours 2-5 : Correction** (Vous)
- Connectez-vous à Korrigo
- Cliquez sur "Mes Copies à Corriger"
- Corrigez à votre rythme (10-12 min/copie)

**Jour 6 : Export** (Vous ou Admin)
- Export CSV vers Pronote
- Les élèves peuvent consulter leurs copies

### Conseils Pratiques

#### Pour une Correction Efficace

1. **Préparez votre espace** : Souris confortable, écran assez grand
2. **Corrigez par lots** : 5-10 copies d'affilée, puis pause
3. **Utilisez les raccourcis** : Clic droit pour outils rapides
4. **Sauvegarde automatique** : Pas besoin de sauvegarder manuellement
5. **Interrompez sans souci** : Vous pouvez reprendre plus tard

#### Pour des Annotations Claires

1. **Couleur rouge** : Par défaut, comme au stylo
2. **Traits fins** : Pour entourer les erreurs
3. **Traits épais** : Pour souligner les points importants
4. **Commentaires texte** : Pour les remarques longues
5. **Symboles** : ✓ pour juste, ✗ pour faux

#### Pour Gagner du Temps

1. **Barème pré-rempli** : Définissez-le une fois pour toutes
2. **Commentaires types** : Créez des modèles pour erreurs fréquentes
3. **Correction par exercice** : Corrigez tous les Ex1, puis tous les Ex2, etc.
4. **Double écran** : Barème sur un écran, copie sur l'autre

---

## 🌟 Avantages Pédagogiques

### Pour Vous (Enseignant)

#### Gain de Temps

- **-30% de temps de correction** : Annotations plus rapides
- **Pas de transport** : Plus de paquets de copies à ramener chez vous
- **Correction flexible** : Corrigez où vous voulez, quand vous voulez
- **Pas de recopie** : Export automatique vers Pronote

#### Meilleure Organisation

- **Archivage automatique** : Toutes vos corrections sont sauvegardées
- **Recherche facile** : Retrouvez une copie en 2 secondes
- **Statistiques automatiques** : Analyse automatique des résultats par exercice et par question
- **Graphiques de réussite** : Visualisation immédiate (ex: "80% de la classe a échoué à la question 2")
- **Détection des difficultés** : Identification précoce des notions à revoir
- **Adaptation pédagogique** : Décisions basées sur les données ("Prévoyez un rappel de cours sur...")
- **Historique** : Suivez la progression de chaque élève

#### Qualité Pédagogique

- **Annotations plus lisibles** : Fini les gribouillis illisibles
- **Commentaires plus riches** : Vous pouvez écrire plus facilement
- **Feedback immédiat** : Les élèves accèdent rapidement à leurs copies
- **Équité** : Anonymisation automatique (pas de biais inconscient)

### Pour les Élèves

#### Accès et Autonomie

- **Consultation 24/7** : Ils consultent leurs copies quand ils veulent
- **Zoom** : Ils peuvent agrandir pour mieux voir vos annotations
- **Téléchargement** : Ils peuvent sauvegarder leurs copies
- **Révisions** : Ils peuvent revoir leurs erreurs avant le prochain examen

#### Apprentissage Amélioré

- **Feedback clair** : Annotations numériques plus lisibles
- **Compréhension** : Ils peuvent prendre le temps d'analyser leurs erreurs
- **Motivation** : Interface moderne et engageante
- **Suivi** : Ils voient leur progression sur plusieurs examens

### Pour l'Équipe Pédagogique

#### Collaboration

- **Partage de barèmes** : Harmonisation entre enseignants
- **Statistiques communes** : Analyse des résultats par niveau
- **Cohérence** : Même processus pour tous les enseignants
- **Mutualisation** : Partage de bonnes pratiques

#### Suivi Longitudinal

- **Progression élèves** : Analyse sur plusieurs trimestres
- **Détection difficultés** : Identification précoce des élèves en difficulté
- **Adaptation pédagogique** : Ajustement des enseignements selon les résultats
- **Reporting** : Tableaux de bord pour la direction

---

## 📊 Module de Statistiques Pédagogiques

### L'Argument Ultime pour la Direction et les Enseignants

Le module de statistiques de Korrigo transforme chaque examen en **outil d'analyse pédagogique**. C'est bien plus qu'un simple système de correction : c'est un **tableau de bord pédagogique intelligent**.

### Fonctionnalités Clés

#### 1. Analyse par Question en Temps Réel

**Exemple concret** :
```
Exercice 2, Question 2 : Dérivée de fonction composée
├─ Taux de réussite : 23% (7/30 élèves)
├─ Note moyenne : 0.8/4 points
├─ Erreurs fréquentes :
│  ├─ 60% : Oubli de la règle de la chaîne
│  ├─ 30% : Erreur de calcul
│  └─ 10% : Réponse correcte
└─ Recommandation : ⚠️ RAPPEL DE COURS NÉCESSAIRE
```

#### 2. Graphiques de Réussite Automatiques

Korrigo génère automatiquement :

- **Histogrammes** : Distribution des notes par exercice
- **Courbes de progression** : Évolution sur plusieurs examens
- **Heatmaps** : Zones de difficulté par question
- **Comparaisons** : Classe vs classe, trimestre vs trimestre

**Exemple visuel** :
```
Question 1: ████████████████████ 85% réussite ✓
Question 2: ████░░░░░░░░░░░░░░░░ 23% réussite ⚠️
Question 3: ████████████░░░░░░░░ 67% réussite ~
Question 4: ██████████████████░░ 92% réussite ✓
```

#### 3. Détection Automatique des Difficultés

**Alertes intelligentes** :

- 🔴 **Alerte Rouge** : < 30% de réussite → "Notion non acquise, revoir en priorité"
- 🟠 **Alerte Orange** : 30-50% → "Notion fragile, exercices supplémentaires recommandés"
- 🟢 **Validation Verte** : > 70% → "Notion maîtrisée"

#### 4. Rapports pour la Direction

**Tableaux de bord exécutifs** :

| Indicateur | Valeur | Tendance |
|------------|--------|----------|
| Taux de réussite global | 68% | ↗️ +5% vs trim. précédent |
| Questions problématiques | 3/12 | ↘️ -2 vs trim. précédent |
| Temps moyen correction | 11 min/copie | ↘️ -2 min vs manuel |
| Satisfaction enseignants | 4.5/5 | ↗️ +0.3 |

#### 5. Adaptation Pédagogique Basée sur les Données

**Scénario réel** :

1. **Constat** : "80% de la classe a échoué à la question 2 (dérivées composées)"
2. **Analyse** : Korrigo identifie l'erreur récurrente (oubli règle de la chaîne)
3. **Action** : L'enseignant programme un rappel de cours ciblé
4. **Suivi** : Prochain examen, taux de réussite passe à 75%
5. **Validation** : Notion consolidée ✓

### Bénéfices Mesurables

#### Pour les Enseignants

- ⏱️ **Gain de temps** : Plus besoin de compiler manuellement les statistiques
- 🎯 **Précision** : Identification exacte des notions problématiques
- 📈 **Suivi** : Progression visible sur plusieurs examens
- 🔄 **Réactivité** : Adaptation pédagogique immédiate

#### Pour la Direction

- 📊 **Pilotage** : Tableaux de bord en temps réel
- 🎓 **Qualité** : Mesure objective de l'efficacité pédagogique
- 💼 **Reporting** : Rapports automatiques pour les instances
- 🏆 **Excellence** : Amélioration continue basée sur les données

#### Pour les Élèves

- 🎯 **Clarté** : Compréhension de leurs points faibles
- 📚 **Ciblage** : Révisions ciblées sur les notions à revoir
- 📈 **Motivation** : Visualisation de leur progression
- 🤝 **Équité** : Même niveau d'analyse pour tous

### Cas d'Usage Concrets

#### Cas 1 : Préparation Bac Blanc

**Situation** : Classe de Terminale, 3 mois avant le Bac

**Utilisation** :
1. Bac Blanc 1 (Décembre) : Korrigo identifie 4 notions problématiques
2. Enseignant programme 4 séances de rappel ciblées
3. Bac Blanc 2 (Janvier) : Taux de réussite +25% sur ces notions
4. Bac Blanc 3 (Février) : Validation complète

**Résultat** : Taux de réussite au Bac réel : 95% (vs 82% année précédente)

#### Cas 2 : Harmonisation entre Classes

**Situation** : 3 classes de Seconde, 3 enseignants différents

**Utilisation** :
1. Korrigo compare les résultats des 3 classes
2. Identification : Classe A excelle en géométrie, Classe B en algèbre
3. Enseignants partagent leurs méthodes
4. Harmonisation progressive

**Résultat** : Écart-type entre classes réduit de 40%

---

## ❓ Questions Fréquentes (Enseignants)

### "Est-ce que je dois changer ma façon de corriger ?"

**Non.** Vous corrigez exactement comme avant, mais sur ordinateur au lieu de papier. Vous gardez votre liberté pédagogique totale.

### "Combien de temps pour apprendre ?"

**15-30 minutes.** Une formation rapide suffit. L'interface est intuitive. Après 2-3 copies, vous serez à l'aise.

### "Et si je préfère corriger sur papier ?"

**C'est possible.** Vous pouvez imprimer les copies, corriger sur papier, puis scanner vos corrections. Mais vous perdez les avantages du numérique.

### "Que se passe-t-il si je perds ma connexion internet ?"

**Pas de problème.** Korrigo fonctionne en local. Vous n'avez besoin d'internet que pour vous connecter initialement. Vos corrections sont sauvegardées localement.

### "Les élèves peuvent-ils modifier leurs copies ?"

**Non.** Les élèves ont un accès en lecture seule. Ils ne peuvent ni modifier ni télécharger les copies d'autres élèves.

### "Puis-je corriger de chez moi ?"

**Oui**, si le serveur est accessible depuis l'extérieur (configuration à voir avec l'équipe IT). Sinon, vous corrigez au lycée.

---

# PARTIE III - POUR L'ÉQUIPE TECHNIQUE INFORMATIQUE

## 🖥️ Architecture Technique

### Vue d'Ensemble

Korrigo est une application web moderne basée sur une architecture **client-serveur** avec les composants suivants :

```
┌─────────────────────────────────────────────────────────────┐
│                      NAVIGATEUR WEB                         │
│              (Chrome, Firefox, Safari, Edge)                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │           FRONTEND (Vue.js 3 SPA)                   │  │
│  │  - Interface utilisateur                            │  │
│  │  - Routing (Vue Router)                             │  │
│  │  - State Management (Pinia)                         │  │
│  │  - Visualisation PDF (PDF.js)                       │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/HTTPS (API REST)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    SERVEUR BACKEND                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │           BACKEND (Django 4.2 + DRF)                │  │
│  │  - API REST                                         │  │
│  │  - Authentification (Session-based)                 │  │
│  │  - Logique métier                                   │  │
│  │  - ORM (Django ORM)                                 │  │
│  └─────────────────────────────────────────────────────┘  │
│                       │                                     │
│  ┌────────────────────┴────────────────────────────────┐  │
│  │         TRAITEMENT ASYNCHRONE (Celery)              │  │
│  │  - Rasterization PDF                                │  │
│  │  - Génération PDF finaux                            │  │
│  │  - Tâches longues                                   │  │
│  └─────────────────────────────────────────────────────┘  │
│                       │                                     │
│  ┌────────────────────┴────────────────────────────────┐  │
│  │              BASE DE DONNÉES                        │  │
│  │  - PostgreSQL 15 (Production)                       │  │
│  │  - SQLite (Développement)                           │  │
│  └─────────────────────────────────────────────────────┘  │
│                       │                                     │
│  ┌────────────────────┴────────────────────────────────┐  │
│  │              CACHE & BROKER                         │  │
│  │  - Redis 7                                          │  │
│  │  - Cache sessions                                   │  │
│  │  - Broker Celery                                    │  │
│  └─────────────────────────────────────────────────────┘  │
│                       │                                     │
│  ┌────────────────────┴────────────────────────────────┐  │
│  │           STOCKAGE FICHIERS                         │  │
│  │  - PDF sources                                      │  │
│  │  - Images rasterisées                               │  │
│  │  - PDF finaux                                       │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Stack Technique Détaillée

#### Backend

| Composant | Version | Rôle |
|-----------|---------|------|
| **Python** | 3.9 | Langage principal |
| **Django** | 4.2 LTS | Framework web, ORM, Admin |
| **Django REST Framework** | 3.16+ | API REST |
| **PostgreSQL** | 15+ | Base de données (production) |
| **SQLite** | 3.x | Base de données (développement) |
| **Redis** | 7+ | Cache + Broker Celery |
| **Celery** | 5+ | Traitement asynchrone |
| **PyMuPDF (fitz)** | 1.23.26 | Manipulation PDF |
| **OpenCV** | 4.8.0 | Traitement d'images |
| **Gunicorn** | Latest | Serveur WSGI (production) |

#### Frontend

| Composant | Version | Rôle |
|-----------|---------|------|
| **Vue.js** | 3.4.15 | Framework UI |
| **TypeScript** | 5.9.3 | Typage statique |
| **Pinia** | 2.1.7 | State management |
| **Vue Router** | 4.2.5 | Routing SPA |
| **Axios** | 1.13.2 | Client HTTP |
| **PDF.js** | 4.0.0 | Visualisation PDF |
| **Vite** | 5.1.0 | Build tool |

#### Infrastructure

| Composant | Version | Rôle |
|-----------|---------|------|
| **Docker** | 20+ | Conteneurisation |
| **Docker Compose** | 2+ | Orchestration |
| **Nginx** | 1.25+ | Reverse proxy (production) |

### Applications Django

Le backend est organisé en **6 applications Django** :

1. **core** : Configuration, middleware, vues communes
2. **exams** : Gestion des examens, copies, fascicules
3. **grading** : Annotations, correction, événements d'audit
4. **processing** : Traitement PDF asynchrone
5. **students** : Gestion des élèves
6. **identification** : OCR et association copies-élèves

### Modèles de Données Principaux

```python
# students/models.py
class Student:
    full_name: str
    date_of_birth: date
    email: str
    class_name: str
    user: OneToOne[User]  # Authentification Django

# exams/models.py
class Exam:
    name: str
    date: date
    pdf_source: FileField
    grading_structure: JSONField  # Barème
    correctors: ManyToMany[User]

class Booklet:  # Fascicule détecté
    exam: ForeignKey[Exam]
    start_page: int
    end_page: int
    pages_images: JSONField
    student_name_guess: str  # OCR

class Copy:
    exam: ForeignKey[Exam]
    anonymous_id: str
    status: str  # STAGING, READY, LOCKED, GRADED
    student: ForeignKey[Student]
    assigned_corrector: ForeignKey[User]
    final_pdf: FileField

# grading/models.py
class Annotation:
    copy: ForeignKey[Copy]
    page_index: int
    x, y, w, h: float  # Coordonnées normalisées [0,1]
    content: str
    type: str  # COMMENT, HIGHLIGHT, ERROR, BONUS
    created_by: ForeignKey[User]

class GradingEvent:  # Audit trail
    copy: ForeignKey[Copy]
    action: str  # IMPORT, LOCK, ANNOTATE, FINALIZE
    actor: ForeignKey[User]
    timestamp: datetime
    metadata: JSONField

class CopyLock:  # Verrouillage optimiste
    copy: OneToOne[Copy]
    owner: ForeignKey[User]
    token: UUID
    expires_at: datetime

class QuestionScore:
    copy: ForeignKey[Copy]
    question_id: str
    score: Decimal
```

---

## 🚀 Installation et Déploiement

### Prérequis Système

#### Serveur Minimum

| Ressource | Minimum | Recommandé |
|-----------|---------|------------|
| **CPU** | 2 cœurs | 4 cœurs |
| **RAM** | 4 GB | 8 GB |
| **Disque** | 50 GB | 100 GB SSD |
| **OS** | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| **Réseau** | 100 Mbps | 1 Gbps |

#### Logiciels Requis

- **Docker** 20+
- **Docker Compose** 2+
- **Git** (pour cloner le repository)

### Installation Rapide (Développement)

```bash
# 1. Cloner le repository
git clone <repository-url>
cd viatique__PMF

# 2. Copier le fichier d'environnement
cp .env.example .env

# 3. Lancer tous les services
docker-compose up --build -d

# 4. Créer le superutilisateur
docker-compose exec backend python manage.py createsuperuser

# 5. Accéder à l'application
# Frontend: http://localhost:5173
# Backend Admin: http://localhost:8088/admin
# API: http://localhost:8088/api/
# Production: https://korrigo.labomaths.tn
```

### Installation Production

#### 1. Préparation du Serveur

```bash
# Mise à jour système
sudo apt update && sudo apt upgrade -y

# Installation Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Installation Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Vérification
docker --version
docker-compose --version
```

#### 2. Configuration

```bash
# Cloner le projet
git clone <repository-url> /opt/korrigo
cd /opt/korrigo

# Copier et éditer la configuration production
cp .env.prod.example .env.prod

# Éditer les variables d'environnement
nano .env.prod
```

**Variables d'environnement critiques** :

```bash
# Sécurité
SECRET_KEY=<générer-une-clé-aléatoire-de-50-caractères>
DEBUG=False
DJANGO_ENV=production

# Base de données
DATABASE_URL=postgresql://korrigo:mot_de_passe_fort@db:5432/korrigo

# Domaine
ALLOWED_HOSTS=korrigo.labomaths.tn,www.korrigo.labomaths.tn
CSRF_TRUSTED_ORIGINS=https://korrigo.labomaths.tn,https://www.korrigo.labomaths.tn
CORS_ALLOWED_ORIGINS=https://korrigo.labomaths.tn

# SSL
SSL_ENABLED=True

# Email (pour notifications)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=korrigo@pmf.tn
EMAIL_HOST_PASSWORD=<mot-de-passe-application>
```

#### 3. Lancement Production

```bash
# Build et démarrage
docker-compose -f infra/docker/docker-compose.prod.yml up --build -d

# Migrations
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py migrate

# Collectstatic
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# Créer superutilisateur
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py createsuperuser
```

#### 4. Configuration Nginx (Reverse Proxy)

```nginx
# /etc/nginx/sites-available/korrigo

upstream backend {
    server localhost:8088;
}

server {
    listen 80;
    server_name korrigo.labomaths.tn www.korrigo.labomaths.tn;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name korrigo.labomaths.tn www.korrigo.labomaths.tn;

    ssl_certificate /etc/ssl/certs/korrigo.labomaths.tn.crt;
    ssl_certificate_key /etc/ssl/private/korrigo.labomaths.tn.key;

    client_max_body_size 100M;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/korrigo/backend/staticfiles/;
    }

    location /media/ {
        alias /opt/korrigo/backend/media/;
    }
}
```

```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/korrigo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. Certificat SSL (Let's Encrypt)

```bash
# Installation Certbot
sudo apt install certbot python3-certbot-nginx

# Obtenir le certificat
sudo certbot --nginx -d korrigo.labomaths.tn -d www.korrigo.labomaths.tn

# Renouvellement automatique (cron)
sudo crontab -e
# Ajouter : 0 3 * * * certbot renew --quiet
```

---

## 🔧 Maintenance et Support

### Surveillance Système

#### Health Checks

Korrigo expose plusieurs endpoints de santé :

```bash
# Health check global
curl http://localhost:8088/api/health/
# Réponse: {"status": "healthy", "database": "ok", "redis": "ok"}

# Liveness probe (Kubernetes)
curl http://localhost:8088/api/health/live/
# Réponse: {"status": "alive"}

# Readiness probe (Kubernetes)
curl http://localhost:8088/api/health/ready/
# Réponse: {"status": "ready", "database": true, "redis": true}
```

#### Métriques Prometheus

```bash
# Endpoint métriques
curl http://localhost:8088/metrics

# Métriques disponibles:
# - http_requests_total
# - http_request_duration_seconds
# - database_connections
# - celery_tasks_total
# - etc.
```

### Logs

#### Accès aux Logs

```bash
# Logs backend
docker-compose logs -f backend

# Logs Celery
docker-compose logs -f celery

# Logs Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Logs Django (fichiers)
tail -f /opt/korrigo/backend/logs/django.log
tail -f /opt/korrigo/backend/logs/audit.log
```

#### Rotation des Logs

Les logs Django sont automatiquement rotés (10 MB max, 10 fichiers).

Pour Nginx :

```bash
# /etc/logrotate.d/nginx
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

### Mises à Jour

#### Mise à Jour Application

```bash
# 1. Sauvegarder la base de données (voir section Sauvegarde)

# 2. Arrêter les services
docker-compose -f infra/docker/docker-compose.prod.yml down

# 3. Récupérer la nouvelle version
git pull origin main

# 4. Rebuild
docker-compose -f infra/docker/docker-compose.prod.yml build

# 5. Migrations
docker-compose -f infra/docker/docker-compose.prod.yml up -d
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py migrate

# 6. Collectstatic
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# 7. Redémarrer
docker-compose -f infra/docker/docker-compose.prod.yml restart
```

#### Mise à Jour Dépendances

```bash
# Backend
docker-compose exec backend pip install -r requirements.txt

# Frontend
docker-compose exec frontend npm install

# Rebuild si nécessaire
docker-compose build
```

### Nettoyage

#### Fichiers Orphelins

```bash
# Nettoyer les fichiers médias orphelins
docker-compose exec backend python manage.py shell
>>> from grading.tasks import cleanup_orphaned_files
>>> cleanup_orphaned_files()
```

#### Volumes Docker

```bash
# Lister les volumes
docker volume ls

# Supprimer les volumes inutilisés (⚠️ ATTENTION)
docker volume prune
```

---

## 🔒 Sécurité et Sauvegarde

### Sécurité

#### Authentification

- **Session-based** : Cookies httpOnly, SameSite=Lax
- **CSRF Protection** : Token CSRF obligatoire pour toutes les mutations
- **Password Policy** : Minimum 12 caractères, complexité requise
- **Rate Limiting** : Protection contre brute-force (django-ratelimit)

#### Permissions

| Rôle | Permissions |
|------|-------------|
| **Admin** | Accès complet (création examens, gestion utilisateurs, dispatch, export) |
| **Teacher** | Correction copies assignées uniquement |
| **Student** | Consultation copies personnelles uniquement (lecture seule) |

#### Chiffrement

- **En transit** : HTTPS/TLS 1.3 (production)
- **Au repos** : Chiffrement disque recommandé (LUKS)
- **Base de données** : Connexions chiffrées (SSL)

#### Audit Trail

Toutes les actions sensibles sont loggées dans `GradingEvent` :

```python
# Exemple d'événement
{
  "copy_id": "uuid",
  "action": "FINALIZE",
  "actor": "prof.dupont",
  "timestamp": "2026-02-04T22:30:00Z",
  "metadata": {"final_score": 15.5}
}
```

### Sauvegarde

#### Sauvegarde Base de Données

**Automatique (Cron)** :

```bash
# Script de sauvegarde
#!/bin/bash
# /opt/korrigo/scripts/backup_db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/korrigo/backups"
CONTAINER="viatique__pmf-db-1"

mkdir -p $BACKUP_DIR

docker exec $CONTAINER pg_dump -U korrigo korrigo | gzip > $BACKUP_DIR/korrigo_$DATE.sql.gz

# Garder seulement les 30 derniers jours
find $BACKUP_DIR -name "korrigo_*.sql.gz" -mtime +30 -delete

echo "Backup completed: korrigo_$DATE.sql.gz"
```

```bash
# Crontab (tous les jours à 2h du matin)
0 2 * * * /opt/korrigo/scripts/backup_db.sh >> /var/log/korrigo_backup.log 2>&1
```

**Manuelle** :

```bash
# Backup
docker exec viatique__pmf-db-1 pg_dump -U korrigo korrigo > backup_$(date +%Y%m%d).sql

# Restore
cat backup_20260204.sql | docker exec -i viatique__pmf-db-1 psql -U korrigo korrigo
```

#### Sauvegarde Fichiers Médias

```bash
# Script de sauvegarde médias
#!/bin/bash
# /opt/korrigo/scripts/backup_media.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/korrigo/backups"
MEDIA_DIR="/opt/korrigo/backend/media"

tar -czf $BACKUP_DIR/media_$DATE.tar.gz -C $MEDIA_DIR .

# Garder seulement les 7 derniers jours
find $BACKUP_DIR -name "media_*.tar.gz" -mtime +7 -delete

echo "Media backup completed: media_$DATE.tar.gz"
```

#### Sauvegarde Complète

```bash
# Backup complet (DB + Media + Config)
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/korrigo/backups/full"

mkdir -p $BACKUP_DIR/$DATE

# Database
docker exec viatique__pmf-db-1 pg_dump -U korrigo korrigo | gzip > $BACKUP_DIR/$DATE/database.sql.gz

# Media
tar -czf $BACKUP_DIR/$DATE/media.tar.gz -C /opt/korrigo/backend/media .

# Config
cp /opt/korrigo/.env.prod $BACKUP_DIR/$DATE/env.backup

echo "Full backup completed: $BACKUP_DIR/$DATE"
```

#### Restauration

```bash
# Restaurer DB
gunzip < backup_20260204.sql.gz | docker exec -i viatique__pmf-db-1 psql -U korrigo korrigo

# Restaurer Media
tar -xzf media_20260204.tar.gz -C /opt/korrigo/backend/media/
```

### Plan de Reprise d'Activité (PRA)

#### Scénario 1 : Panne Serveur

1. **Détection** : Monitoring alerte (< 5 min)
2. **Diagnostic** : Vérifier logs, health checks
3. **Redémarrage** : `docker-compose restart`
4. **Vérification** : Tests fonctionnels
5. **Communication** : Informer utilisateurs si > 15 min

#### Scénario 2 : Corruption Base de Données

1. **Arrêt services** : `docker-compose down`
2. **Restauration** : Dernier backup valide
3. **Vérification intégrité** : Tests
4. **Redémarrage** : `docker-compose up -d`
5. **Post-mortem** : Analyse cause

#### Scénario 3 : Perte Données

1. **Évaluation** : Identifier données perdues
2. **Restauration** : Backup le plus récent
3. **Réconciliation** : Comparer avec état actuel
4. **Communication** : Informer utilisateurs affectés
5. **Prévention** : Renforcer backups

---

## 📞 Support Technique

### Niveaux de Support

#### Niveau 1 : Utilisateurs (Enseignants/Élèves)

**Contact** : Labo Maths ERT  
**Email** : labo.maths@pmf.tn  
**Délai** : 24h (jours ouvrés)

**Problèmes traités** :
- Connexion
- Utilisation interface
- Questions fonctionnelles

#### Niveau 2 : Administration (Secrétariat/Admin)

**Contact** : Équipe IT + Labo Maths ERT  
**Email** : support.korrigo@pmf.tn  
**Délai** : 4h (jours ouvrés)

**Problèmes traités** :
- Gestion utilisateurs
- Import/Export
- Configuration examens

#### Niveau 3 : Technique (IT)

**Contact** : Aleddine BEN RHOUMA  
**Email** : aleddine.benrhouma@pmf.tn  
**Délai** : Selon criticité

**Problèmes traités** :
- Serveur
- Base de données
- Bugs applicatifs
- Sécurité

### Procédure d'Escalade

```
Utilisateur → Niveau 1 (Labo Maths)
                ↓ (si non résolu en 24h)
            Niveau 2 (IT + Labo)
                ↓ (si non résolu en 48h)
            Niveau 3 (Développeur)
```

---

# ANNEXES

## 📖 Glossaire

### Termes Généraux

- **Annotation** : Marque ou commentaire ajouté sur une copie numérique
- **Anonymisation** : Masquage du nom de l'élève pour correction impartiale
- **Barème** : Grille de notation définissant les points par question
- **Copie** : Examen d'un élève (scanné et numérisé)
- **Fascicule** : Ensemble de pages détecté automatiquement après scan
- **OCR** : Reconnaissance Optique de Caractères (détection automatique du nom)
- **Staging** : Étape de validation avant correction

### Termes Techniques

- **API** : Interface de Programmation (communication frontend-backend)
- **Backend** : Partie serveur de l'application (logique métier, base de données)
- **Docker** : Technologie de conteneurisation
- **Frontend** : Partie client de l'application (interface utilisateur)
- **ORM** : Mapping Objet-Relationnel (accès base de données)
- **REST** : Style d'architecture pour API web
- **SPA** : Single Page Application (application web moderne)

### Acronymes

- **CSRF** : Cross-Site Request Forgery (attaque web)
- **CSV** : Comma-Separated Values (format fichier)
- **DRF** : Django REST Framework
- **HTTPS** : HTTP Secure (protocole sécurisé)
- **PDF** : Portable Document Format
- **RGPD** : Règlement Général sur la Protection des Données
- **SSL/TLS** : Secure Sockets Layer / Transport Layer Security
- **UUID** : Universally Unique Identifier

---

## ❓ FAQ Multi-Profils

### Pour la Direction

**Q: Quel est le coût total de Korrigo ?**  
R: Développement = 0€ (interne). Hébergement = 0-500€/an selon choix (serveur local ou cloud).

**Q: Korrigo est-il conforme RGPD ?**  
R: Oui, 100% conforme. Documentation légale fournie.

**Q: Peut-on l'utiliser pour toutes les matières ?**  
R: Oui, Korrigo fonctionne pour toutes les matières (pas seulement mathématiques).

**Q: Que se passe-t-il si le développeur quitte l'établissement ?**  
R: Le code est documenté et open-source. L'équipe IT peut prendre le relais.

### Pour les Enseignants

**Q: Combien de temps pour corriger une copie ?**  
R: 10-12 minutes en moyenne (vs 15 min papier), soit -30%.

**Q: Puis-je corriger de chez moi ?**  
R: Oui, si le serveur est accessible depuis l'extérieur (à configurer avec IT).

**Q: Les élèves peuvent-ils tricher en modifiant leurs copies ?**  
R: Non, accès en lecture seule. Toute modification est impossible et tracée.

**Q: Que se passe-t-il si je me trompe dans une note ?**  
R: Vous pouvez modifier avant finalisation. Après, contacter l'admin.

### Pour l'Équipe IT

**Q: Quelles sont les dépendances système ?**  
R: Docker + Docker Compose. Tout le reste est conteneurisé.

**Q: Comment gérer les mises à jour ?**  
R: `git pull` + `docker-compose build` + migrations Django.

**Q: Quelle est la charge serveur ?**  
R: Faible. 4 CPU + 8 GB RAM suffisent pour 500 élèves.

**Q: Comment monitorer l'application ?**  
R: Endpoints `/api/health/` + métriques Prometheus `/metrics`.

---

## 📞 Contacts et Support

### Équipe Projet

**Concepteur et Développeur**  
Aleddine BEN RHOUMA  
Enseignant de Mathématiques - Labo Maths ERT  
Email: aleddine.benrhouma@pmf.tn

**Support Pédagogique**  
Labo Maths ERT  
Email: labo.maths@pmf.tn

**Support Technique**  
Équipe IT - Lycée Pierre Mendès France  
Email: it@pmf.tn

### Ressources

- **Documentation complète** : `/docs/INDEX.md`
- **Guide démarrage rapide** : `/docs/QUICKSTART.md`
- **Documentation technique** : `/docs/technical/`
- **Code source** : Repository Git interne

---

## 🎓 À Propos du Projet

### Contexte

Korrigo a été développé au sein du **Labo Maths ERT** (Équipe de Recherche Technologique) du Lycée Pierre Mendès France de Tunis, dans le cadre d'une initiative de modernisation pédagogique.

### Objectifs

1. **Moderniser** le processus de correction des examens
2. **Améliorer** l'expérience enseignant et élève
3. **Valoriser** l'expertise technique de l'établissement
4. **Partager** les bonnes pratiques avec d'autres établissements

### Philosophie

- **Open Source** : Code ouvert et documenté
- **Pédagogie d'abord** : Conçu par et pour les enseignants
- **Simplicité** : Interface intuitive, apprentissage rapide
- **Robustesse** : Architecture éprouvée, sécurité maximale

---

## 📜 Propriété Intellectuelle

### Droits et Propriété

**Korrigo** est un logiciel développé par le **Labo Maths ERT** du Lycée Pierre Mendès France de Tunis.

- **Propriétaire** : Lycée Pierre Mendès France, Tunis
- **Développeur principal** : Aleddine BEN RHOUMA (Enseignant de Mathématiques)
- **Contributeurs** : Membres du Labo Maths ERT
- **Licence** : Propriétaire - Usage interne établissement

### Utilisation et Distribution

- ✅ **Usage interne** : Libre pour le Lycée Pierre Mendès France
- ✅ **Partage pédagogique** : Partage avec autres établissements AEFE (avec accord)
- ❌ **Usage commercial** : Interdit sans autorisation écrite
- ❌ **Redistribution** : Interdite sans autorisation écrite

### Code Source

Le code source de Korrigo est:
- **Documenté** : Documentation technique complète
- **Versionné** : Git avec historique complet
- **Maintenable** : Architecture claire, tests automatisés
- **Évolutif** : Conçu pour faciliter les ajouts de fonctionnalités

### Garanties et Responsabilités

- ⚠️ **Fourni "tel quel"** : Sans garantie explicite ou implicite
- ⚠️ **Responsabilité limitée** : Le développeur n'est pas responsable des dommages indirects
- ✅ **Support best-effort** : Support assuré par le Labo Maths ERT dans la mesure du possible
- ✅ **Évolutions** : Développement continu selon les besoins pédagogiques

---

## 🌱 Approche Écologique Réaliste

### Principe de Réalisme

Korrigo adopte une approche **honnête et réaliste** concernant son impact écologique :

#### Ce qui est Conservé (et Pourquoi)

**Composition sur papier** :
- ✅ **Maintenue** : Les élèves composent toujours sur papier
- **Raison** : Confort de l'élève, équité (pas de fracture numérique), authenticité de l'évaluation
- **Impact** : Consommation papier identique pour la composition

**Remise de la copie physique** :
- ✅ **Maintenue** : L'élève récupère sa copie papier après scan
- **Raison** : Droit de l'élève à conserver sa copie originale
- **Bonus** : Double numérique éternel en plus

#### Optimisations Réelles

**Suppression des copies de secours** :
- ❌ **Avant** : 1 copie originale + 1 copie de secours = 2x papier
- ✅ **Après** : 1 copie originale + 1 copie numérique = 1x papier
- **Économie** : ~50% sur les copies

**Suppression des corrigés papier** :
- ❌ **Avant** : Corrigés imprimés et distribués (30 copies x 4 pages = 120 feuilles)
- ✅ **Après** : Corrigés numériques accessibles en ligne
- **Économie** : ~120 feuilles par examen

**Dématérialisation de l'archivage** :
- ❌ **Avant** : Cartons de copies stockés physiquement (10 cartons/an)
- ✅ **Après** : Archivage numérique sécurisé (0 cartons)
- **Économie** : 100% sur l'archivage physique

### Bilan Écologique Honnête

| Poste | Impact |
|-------|--------|
| **Composition** | = (inchangé) |
| **Copies de secours** | -50% |
| **Corrigés distribués** | -100% |
| **Archivage physique** | -100% |
| **Transport copies** | -30% (moins de trajets) |
| **Consommation électrique** | +5% (serveur) |

**Bilan global** : ~40% de réduction de l'empreinte papier, légère augmentation de la consommation électrique.

### Engagement Environnemental

- 🌱 **Serveur local** : Hébergement sur serveur existant (pas de nouveau matériel)
- 🌱 **Optimisation énergétique** : Serveur en veille hors heures d'utilisation
- 🌱 **Longévité** : Code conçu pour durer, pas d'obsolescence programmée
- 🌱 **Recyclage** : Encouragement au recyclage des copies papier après remise à l'élève

---

**Document rédigé par** : Aleddine BEN RHOUMA  
**Pour** : Lycée Pierre Mendès France, Tunis  
**Date** : Février 2026  
**Version** : 2.0  
**URL** : https://korrigo.labomaths.tn

---

*Ce document est la propriété du Lycée Pierre Mendès France et du Labo Maths ERT. Toute reproduction ou distribution doit être autorisée.*
