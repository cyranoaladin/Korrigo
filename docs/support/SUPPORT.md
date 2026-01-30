# Procédures de Support - Korrigo PMF

> **Version**: 1.0.0  
> **Date**: 30 Janvier 2026  
> **Public**: Administrateurs, Support technique, Direction  
> **Langue**: Français

Documentation des procédures de support, escalade, et maintenance de la plateforme Korrigo PMF.

---

## 📋 Table des Matières

1. [Vue d'Ensemble du Support](#vue-densemble-du-support)
2. [Niveaux de Support](#niveaux-de-support)
3. [Matrice d'Escalade](#matrice-descalade)
4. [Procédures de Support par Rôle](#procédures-de-support-par-rôle)
5. [Classification des Incidents](#classification-des-incidents)
6. [SLA et Temps de Réponse](#sla-et-temps-de-réponse)
7. [Outils de Support](#outils-de-support)
8. [Maintenance de la Documentation](#maintenance-de-la-documentation)
9. [Formation et Accompagnement](#formation-et-accompagnement)
10. [Gestion des Demandes](#gestion-des-demandes)

---

## Vue d'Ensemble du Support

### Objectifs du Support

Le support Korrigo PMF a pour missions :
- **Assistance utilisateurs** : Répondre aux questions et résoudre les problèmes d'utilisation
- **Maintenance technique** : Assurer le bon fonctionnement de la plateforme
- **Formation** : Accompagner les utilisateurs dans la prise en main
- **Amélioration continue** : Identifier les problèmes récurrents et proposer des améliorations
- **Documentation** : Maintenir la documentation à jour

### Modèle de Support

**Support à 3 niveaux** :
- **Niveau 1 (L1)** : Support utilisateur de premier niveau (administrateur lycée)
- **Niveau 2 (L2)** : Support technique avancé (équipe IT du lycée ou prestataire)
- **Niveau 3 (L3)** : Support éditeur Korrigo (développement, bugs système)

### Canaux de Support

| Canal | Usage | Public | Disponibilité |
|-------|-------|--------|---------------|
| **FAQ en ligne** | Consultation autonome | Tous | 24/7 |
| **Email** | Demandes non urgentes | Tous | Réponse sous 48h |
| **Téléphone** | Support urgent | Admin, Enseignants | Heures ouvrables |
| **Ticket system** | Suivi des incidents | Admin, Support IT | 24/7 (soumission) |
| **Documentation** | Auto-formation | Tous | 24/7 |
| **Formation en présentiel** | Prise en main initiale | Tous | Sur planification |

---

## Niveaux de Support

### Niveau 1 (L1) - Support Utilisateur

**Responsable** : Administrateur du lycée (Admin NSI ou référent numérique)

**Périmètre** :
- ✅ Questions d'utilisation courante
- ✅ Création/modification de comptes utilisateurs
- ✅ Réinitialisation de mots de passe
- ✅ Aide à la navigation (interface)
- ✅ Problèmes d'identification de copies
- ✅ Attribution de copies aux enseignants
- ✅ Export vers Pronote
- ✅ Consultation de la documentation

**Résolution attendue** : 80% des demandes

**Outils** :
- Accès administrateur à la plateforme
- Documentation utilisateur complète
- FAQ
- Checklist de diagnostic de base

**Formation requise** :
- Formation initiale Korrigo (2 jours)
- Connaissance des workflows métier
- Bases d'administration système (optionnel)

**Escalade vers L2** :
- Problèmes techniques serveur (services down, erreurs 500)
- Problèmes de performance persistants
- Bugs système
- Problèmes de base de données
- Incidents de sécurité

### Niveau 2 (L2) - Support Technique Avancé

**Responsable** : Équipe IT du lycée ou prestataire technique

**Périmètre** :
- ✅ Diagnostic et résolution des problèmes serveur
- ✅ Gestion de l'infrastructure (Docker, PostgreSQL, Redis)
- ✅ Optimisation des performances
- ✅ Sauvegardes et restaurations
- ✅ Migrations et mises à jour
- ✅ Configuration réseau et sécurité
- ✅ Analyse des logs et monitoring
- ✅ Incidents de sécurité (niveau 1)

**Résolution attendue** : 90% des incidents techniques

**Outils** :
- Accès SSH au serveur
- Docker et docker-compose
- Outils de monitoring (Grafana, Prometheus si configurés)
- Guide de dépannage technique
- Logs système et applicatifs

**Formation requise** :
- Administration système Linux
- Docker et conteneurisation
- PostgreSQL et Redis
- Bases de Django (optionnel)
- Sécurité informatique

**Escalade vers L3** :
- Bugs applicatifs (code Django/Vue.js)
- Problèmes de conception (architecture)
- Demandes d'évolution fonctionnelle
- Incidents de sécurité majeurs (faille applicative)
- Problèmes non résolus après 48h

### Niveau 3 (L3) - Support Éditeur

**Responsable** : Équipe de développement Korrigo (si applicable)

**Périmètre** :
- ✅ Correction de bugs applicatifs
- ✅ Évolutions fonctionnelles
- ✅ Problèmes d'architecture
- ✅ Patches de sécurité
- ✅ Mise à jour majeure
- ✅ Audit de code
- ✅ Optimisations critiques

**Résolution attendue** : 100% (avec délai variable)

**Outils** :
- Accès au code source
- Environnement de développement
- CI/CD
- Issue tracker (GitLab, GitHub, Jira)

**Contact** :
- Email : support.korrigo@example.com (à adapter)
- Téléphone d'urgence : +33 X XX XX XX XX (à adapter)
- Portail de tickets : https://support.korrigo.example.com (à adapter)

---

## Matrice d'Escalade

### Flux d'Escalade

```
┌─────────────────┐
│   Utilisateur   │
│ (Enseignant,    │
│  Étudiant, etc.)│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         NIVEAU 1 (L1)                   │
│   Administrateur Lycée                  │
│   - Questions utilisation               │
│   - Gestion comptes                     │
│   - FAQ & Documentation                 │
│                                         │
│   Résolution : 80% sous 24-48h          │
└────────┬────────────────────────────────┘
         │ Si non résolu ou technique
         ▼
┌─────────────────────────────────────────┐
│         NIVEAU 2 (L2)                   │
│   Support Technique IT                  │
│   - Problèmes serveur                   │
│   - Performance                         │
│   - Sauvegardes                         │
│                                         │
│   Résolution : 90% sous 48-72h          │
└────────┬────────────────────────────────┘
         │ Si bug applicatif ou non résolu
         ▼
┌─────────────────────────────────────────┐
│         NIVEAU 3 (L3)                   │
│   Éditeur Korrigo                       │
│   - Bugs code                           │
│   - Évolutions                          │
│   - Sécurité critique                   │
│                                         │
│   Résolution : Variable (2j-2 semaines) │
└─────────────────────────────────────────┘
```

### Critères d'Escalade

**L1 → L2** :
- ✅ Problème non résolu après consultation de la documentation
- ✅ Erreur technique serveur (500, services down)
- ✅ Problème de performance persistant
- ✅ Perte de données
- ✅ Problème de sécurité suspecté

**L2 → L3** :
- ✅ Bug applicatif confirmé (erreur dans le code)
- ✅ Problème non documenté
- ✅ Demande d'évolution fonctionnelle
- ✅ Faille de sécurité confirmée
- ✅ Problème non résolu après 48h (L2)

### Informations à Fournir lors de l'Escalade

**Template de ticket d'escalade** :

```markdown
## Contexte
- **Niveau actuel** : L1 / L2
- **Date de première détection** : JJ/MM/AAAA HH:MM
- **Rapporté par** : [Nom, rôle]
- **Criticité** : P1 / P2 / P3 / P4 (voir classification)

## Description du Problème
[Description claire et concise]

## Comportement Attendu vs Observé
- **Attendu** : ...
- **Observé** : ...

## Étapes de Reproduction
1. ...
2. ...
3. ...

## Impact
- **Utilisateurs affectés** : [nombre] enseignants / étudiants
- **Fonctionnalités bloquées** : ...
- **Contournement possible** : Oui / Non (si oui, décrire)

## Actions Déjà Effectuées (L1/L2)
- [ ] Consultation FAQ
- [ ] Consultation Guide de Dépannage
- [ ] Redémarrage des services
- [ ] Analyse des logs
- [ ] Restauration depuis backup
- [ ] Autres : ...

## Informations Techniques
- **Environnement** : Production / Staging
- **Version Korrigo** : X.Y.Z
- **Navigateur** (si applicable) : Chrome/Firefox/etc. version X
- **Logs** : [Joindre extraits pertinents]
- **Captures d'écran** : [Joindre si applicable]

## Contact
- **Nom** : ...
- **Email** : ...
- **Téléphone** : ...
- **Disponibilité** : ...
```

---

## Procédures de Support par Rôle

### Support pour les Étudiants

**Problèmes courants** :
1. Impossible de se connecter
2. Copie non visible
3. Téléchargement PDF
4. Compréhension des annotations

**Procédure L1** :
1. **Vérifier l'identité** : INE, nom, classe
2. **Vérifier le compte** : Existe ? Actif ?
3. **Vérifier les copies** :
   ```bash
   docker-compose exec backend python manage.py shell
   >>> from backend.copies.models import Copy
   >>> from backend.students.models import Student
   >>> student = Student.objects.get(ine='XXXXXXXXXX')
   >>> student.copies.all()
   ```
4. **Actions possibles** :
   - Réinitialiser mot de passe
   - Vérifier statut des copies (GRADED + published)
   - Envoyer par email si problème technique

**Documentation** : [Guide Étudiant](../users/GUIDE_ETUDIANT.md)

### Support pour les Enseignants

**Problèmes courants** :
1. Impossible de verrouiller une copie
2. Annotations disparues
3. Copie mal identifiée
4. Performance lente

**Procédure L1** :
1. **Diagnostic rapide** :
   - Vérifier le statut de la copie (READY/LOCKED/GRADED)
   - Vérifier les verrous (`locked_by`, `locked_at`)
   - Consulter les logs d'audit
2. **Actions courantes** :
   - Déverrouiller une copie expirée
   - Réassigner une copie
   - Signaler un problème d'identification
3. **Escalade L2** si :
   - Perte réelle de données (annotations)
   - Bug de l'interface
   - Performance inacceptable

**Documentation** : [Guide Enseignant](../users/GUIDE_ENSEIGNANT.md), [FAQ Enseignant](FAQ.md#faq-enseignant)

### Support pour le Secrétariat

**Problèmes courants** :
1. OCR ne fonctionne pas
2. Fusion de carnets
3. Élève non trouvé dans la base
4. Qualité du scan

**Procédure L1** :
1. **Identification** :
   - Essayer identification manuelle
   - Vérifier l'orthographe du nom
   - Vérifier la classe/INE
2. **Import d'élèves** :
   - Valider le format CSV
   - Vérifier l'encodage UTF-8
   - Refaire l'import si nécessaire
3. **Carnets** :
   - Vérifier les booklets créés
   - Fusionner manuellement si nécessaire

**Documentation** : [Guide Secrétariat](../users/GUIDE_SECRETARIAT.md)

### Support pour les Administrateurs

**Problèmes courants** :
1. Migration échouée
2. Export Pronote
3. Backup/restauration
4. Mises à jour

**Procédure L1** :
1. **Consulter la documentation technique** :
   - [Guide Administrateur](../admin/GUIDE_UTILISATEUR_ADMIN.md)
   - [Guide de Dépannage](DEPANNAGE.md)
   - [Deployment Guide](../DEPLOYMENT_GUIDE.md)
2. **Diagnostics** :
   - Logs serveur
   - État des services
   - Ressources système
3. **Actions** :
   - Redémarrage services
   - Rollback si nécessaire
   - Restauration backup

**Escalade L2** : Systématique pour problèmes techniques serveur

---

## Classification des Incidents

### Niveaux de Priorité

| Priorité | Nom | Impact | Exemple | SLA Réponse | SLA Résolution |
|----------|-----|--------|---------|-------------|----------------|
| **P1** | Critique | Système inutilisable | Tous les services down, perte de données, faille sécurité active | 1 heure | 4 heures |
| **P2** | Majeur | Fonctionnalité bloquée | Impossible de corriger, upload bloqué, export ne fonctionne pas | 4 heures | 24 heures |
| **P3** | Mineur | Gêne utilisateur | Performance lente, bug UI mineur, confusion dans l'interface | 24 heures | 72 heures |
| **P4** | Trivial | Cosmétique | Faute d'orthographe, amélioration esthétique, suggestion | 72 heures | Best effort |

### Exemples de Classification

**P1 - Critique** :
- Serveur inaccessible pendant période d'examens
- Perte de données de correction (sans backup)
- Faille de sécurité exploitée activement
- Impossible de finaliser les copies (deadline Pronote)

**Actions P1** :
- Notification immédiate de tous les niveaux (L1, L2, L3)
- Mobilisation d'urgence
- Communication aux utilisateurs
- Point de situation toutes les heures

**P2 - Majeur** :
- Une fonctionnalité clé ne fonctionne pas (ex: verrouillage de copies)
- Export Pronote échoue systématiquement
- OCR complètement HS
- Performance inacceptable (> 30s chargement)

**Actions P2** :
- Escalade rapide si non résolu en L1 sous 2h
- Communication aux utilisateurs affectés
- Recherche de contournement temporaire

**P3 - Mineur** :
- Interface lente mais utilisable
- Bug cosmétique (mauvais affichage)
- Message d'erreur peu clair
- Fonctionnalité secondaire défaillante

**Actions P3** :
- Traitement normal via ticket
- Pas d'escalade immédiate
- Documentation du contournement si possible

**P4 - Trivial** :
- Faute de frappe dans l'interface
- Suggestion d'amélioration UX
- Demande de fonctionnalité "nice to have"
- Question de formation

**Actions P4** :
- Backlog
- Traitement par lot lors de mises à jour mineures

---

## SLA et Temps de Réponse

### Définitions

**SLA** : Service Level Agreement (Accord de Niveau de Service)
- **Temps de réponse** : Délai entre la soumission du ticket et la première réponse
- **Temps de résolution** : Délai entre la soumission et la résolution complète

### SLA par Niveau de Support

**Niveau 1 (L1)** :

| Priorité | Temps de Réponse | Temps de Résolution | Disponibilité |
|----------|------------------|---------------------|---------------|
| P1 | 1h | 4h | 24/7 (téléphone) |
| P2 | 4h | 24h | Heures ouvrables |
| P3 | 24h | 72h | Heures ouvrables |
| P4 | 72h | Best effort | Email uniquement |

**Heures ouvrables** : Lundi-Vendredi 8h-18h (hors vacances scolaires)

**Niveau 2 (L2)** :

| Priorité | Temps de Réponse | Temps de Résolution |
|----------|------------------|---------------------|
| P1 | 30 min | 4h |
| P2 | 2h | 24h |
| P3 | 12h | 72h |
| P4 | 48h | Best effort |

**Niveau 3 (L3)** :

| Priorité | Temps de Réponse | Temps de Résolution |
|----------|------------------|---------------------|
| P1 | 2h | 48h (patch emergency) |
| P2 | 8h | 1 semaine |
| P3 | 48h | 2 semaines |
| P4 | 1 semaine | Prochaine release |

### Suivi des SLA

**Indicateurs** :
- **Taux de respect des SLA** : % de tickets résolus dans les délais
- **Temps moyen de réponse** : Moyenne par priorité
- **Temps moyen de résolution** : Moyenne par priorité
- **Taux de réouverture** : % de tickets rouverts après résolution

**Reporting** :
- Rapport hebdomadaire (L1) : Tickets traités, SLA respectés
- Rapport mensuel (L2/L3) : Tendances, problèmes récurrents, améliorations
- Rapport trimestriel (Direction) : Satisfaction, évolutions, budget

---

## Outils de Support

### Système de Ticketing

**Options** :
1. **Email simple** : Pour petits établissements (< 500 élèves)
   - Adresse dédiée : support.korrigo@lycee.fr
   - Tags dans les sujets : [P1], [P2], etc.
   - Limite : Pas de suivi structuré

2. **OsTicket** (open source) : Recommandé
   - Gestion de tickets
   - SLA tracking
   - Escalade automatique
   - Base de connaissance intégrée

3. **GLPI** (open source) : Pour lycées avec IT structure
   - ITSM complet
   - Gestion d'actifs
   - Inventaire
   - Intégration LDAP

4. **Freshdesk / Zendesk** (commercial) : Si budget disponible
   - Interface moderne
   - Automatisation avancée
   - Reporting puissant

**Configuration minimale** :
- Catégories : Authentification, Correction, Identification, Technique, RGPD
- Priorités : P1, P2, P3, P4
- Assignation automatique par catégorie
- Templates de réponses courantes
- Escalade automatique si SLA dépassé

### Base de Connaissance

**Structure recommandée** :
```
Base de Connaissance Korrigo
├── Prise en main
│   ├── Premiers pas - Enseignant
│   ├── Premiers pas - Secrétariat
│   └── Premiers pas - Étudiant
├── Problèmes courants
│   ├── Authentification
│   ├── Correction
│   ├── Identification
│   └── Export Pronote
├── Procédures
│   ├── Création d'utilisateurs
│   ├── Import CSV
│   ├── Sauvegarde/Restauration
│   └── Mise à jour
└── Vidéos tutorielles
    ├── Correction d'une copie (5 min)
    ├── Identification des copies (10 min)
    └── Administration (15 min)
```

**Outils** :
- Wiki interne (MediaWiki, DokuWiki)
- Documentation Markdown + GitBook
- Vidéos : OBS Studio + YouTube privé ou serveur interne

### Monitoring et Alertes

**Outils recommandés** :

**1. Uptime monitoring** :
```bash
# UptimeRobot (SaaS) ou self-hosted
# Ping HTTP toutes les 5 minutes
# Alertes email/SMS si down
```

**2. Logs centralisés** :
```bash
# Stack ELK (Elasticsearch, Logstash, Kibana)
# Ou Loki + Grafana (plus léger)
docker-compose exec backend python manage.py configure_logging --output=elasticsearch
```

**3. Métriques système** :
```bash
# Prometheus + Grafana
# Dashboards : CPU, RAM, Disk, Requests/s, Latency
```

**4. Alertes applicatives** :
```python
# Django : Envoyer email si exception
ADMINS = [('Admin', 'admin@lycee.fr')]
SERVER_EMAIL = 'korrigo@lycee.fr'
EMAIL_SUBJECT_PREFIX = '[Korrigo Error] '
```

**Alertes critiques** :
- Services down > 2 minutes
- Espace disque < 10%
- Mémoire > 90% pendant 5 minutes
- Erreurs 500 > 10 par minute
- Backup échoué

---

## Maintenance de la Documentation

### Responsabilités

**Qui maintient quoi** :

| Document | Responsable | Fréquence de Révision |
|----------|-------------|----------------------|
| FAQ | Admin L1 | Mensuelle |
| Guide de Dépannage | Support L2 | Trimestrielle |
| Guide Utilisateur | Admin L1 + Utilisateurs pilotes | Semestrielle |
| Documentation Technique | Support L2/L3 | Après chaque mise à jour |
| Procédures Opérationnelles | Admin L1 | Annuelle |
| Politique RGPD | DPO | Annuelle ou si changement légal |

### Processus de Mise à Jour

**Déclencheurs de mise à jour** :
1. **Nouvelle version Korrigo** : Mise à jour obligatoire de la doc technique
2. **Problème récurrent** : Ajout à la FAQ
3. **Feedback utilisateurs** : Clarification des guides
4. **Évolution légale** : Mise à jour RGPD, sécurité
5. **Changement organisationnel** : Mise à jour des contacts, procédures

**Workflow** :
```
1. Identification du besoin
   ↓
2. Rédaction/modification (brouillon)
   ↓
3. Revue par pair (L1/L2/utilisateur pilote)
   ↓
4. Validation (Responsable doc)
   ↓
5. Publication (Git commit + notification)
   ↓
6. Archivage ancienne version (Git tag)
```

**Versioning** :
```markdown
## Historique des Versions

| Version | Date | Modifications | Auteur |
|---------|------|---------------|--------|
| 1.1.0 | 15/02/2026 | Ajout section export Pronote v2 | Admin NSI |
| 1.0.1 | 05/02/2026 | Corrections typos, clarifications FAQ | Support L1 |
| 1.0.0 | 30/01/2026 | Création initiale | Équipe projet |
```

**Outils** :
- **Git** : Versioning et collaboration
- **Markdown** : Format simple et lisible
- **MkDocs** ou **Docusaurus** : Générateur de site de documentation
- **Review** : Pull requests pour changements importants

### Métriques de Qualité

**Indicateurs** :
- **Complétude** : % de fonctionnalités documentées
- **Fraîcheur** : Délai depuis dernière mise à jour
- **Utilité** : % de tickets résolus via documentation seule (sans escalade)
- **Feedback** : Score de satisfaction sur la doc (sondage utilisateurs)

**Objectifs** :
- ✅ 100% des fonctionnalités documentées
- ✅ Mise à jour < 1 mois après release
- ✅ 60% de résolution autonome (via FAQ/guides)
- ✅ Satisfaction > 4/5

### Audit Annuel de la Documentation

**Checklist** :
- [ ] Toutes les captures d'écran sont à jour (version UI actuelle)
- [ ] Tous les liens internes fonctionnent
- [ ] Toutes les procédures ont été testées
- [ ] Tous les contacts sont à jour
- [ ] La terminologie est cohérente
- [ ] Les guides reflètent les workflows réels
- [ ] Les FAQ couvrent 80% des questions récurrentes
- [ ] La documentation RGPD est conforme aux lois en vigueur

---

## Formation et Accompagnement

### Programme de Formation Initiale

**Formation Administrateurs (2 jours)** :

**Jour 1 - Fondamentaux** :
- 9h-10h : Présentation de Korrigo PMF, architecture, workflows
- 10h-12h : Prise en main interface admin, création utilisateurs
- 14h-16h : Gestion des examens, upload PDF, identification
- 16h-17h : Export Pronote, reporting

**Jour 2 - Technique et Support** :
- 9h-10h30 : Administration système, Docker, backups
- 10h30-12h : Dépannage courant, analyse de logs
- 14h-16h : RGPD et sécurité, procédures conformité
- 16h-17h : Q&A, cas pratiques

**Formation Enseignants (1/2 journée)** :
- 14h-15h : Présentation, bénéfices de la correction numérique
- 15h-16h : Démonstration : verrouillage, annotation, finalisation
- 16h-17h : TP : Correction d'une copie de démonstration
- 17h-17h30 : Q&A

**Formation Secrétariat (1/2 journée)** :
- 14h-14h30 : Workflow global, rôle du secrétariat
- 14h30-15h30 : Identification des copies, OCR, fusion carnets
- 15h30-16h30 : TP : Identifier un lot de 20 copies
- 16h30-17h : Q&A, bonnes pratiques

**Formation Étudiants (15 minutes)** :
- Email avec vidéo tutorielle (3 min)
- Guide PDF "Comment accéder à mes copies"
- Session Q&A en classe (optionnel)

### Matériel de Formation

**Documents** :
- Slides PowerPoint / LibreOffice Impress
- Guides PDF imprimables
- Cheatsheet (fiche mémo) format A4 recto-verso
- Vidéos tutorielles (< 10 min chacune)

**Environnement de démonstration** :
```bash
# Serveur de démo avec données fictives
docker-compose -f docker-compose.demo.yml up -d

# Données de démo :
# - 3 examens
# - 50 copies (déjà identifiées)
# - 5 utilisateurs enseignants
# - 100 étudiants
```

**Ressources** :
- Copies d'examen anonymisées (pour TP)
- Comptes de démo (enseignant_demo, admin_demo, etc.)
- Scripts de réinitialisation (entre sessions de formation)

### Accompagnement Post-Formation

**Semaine 1-2** (Support renforcé) :
- Disponibilité L1 étendue (8h-19h)
- Visite sur site (si possible)
- Hotline dédiée

**Mois 1-3** (Consolidation) :
- Point hebdomadaire avec admin principal
- Suivi des KPIs d'utilisation
- Identification des difficultés récurrentes
- Mise à jour de la documentation si besoin

**Mois 3-6** (Autonomie) :
- Support normal (SLA standards)
- Formation des nouveaux utilisateurs par les utilisateurs formés
- Retour d'expérience, amélioration continue

### Sessions de Rappel

**Fréquence** : Annuelle ou avant chaque période d'examens

**Format** : 1 heure, rappel des fonctionnalités, nouveautés

**Public** :
- Nouveaux enseignants
- Enseignants n'ayant pas utilisé depuis > 1 an
- Rappel pour tous (optionnel)

---

## Gestion des Demandes

### Types de Demandes

**1. Incident** : Quelque chose ne fonctionne pas comme attendu
- Exemple : "Impossible de verrouiller une copie"
- Action : Diagnostic, résolution, clôture

**2. Demande de service** : Demande d'action administrative
- Exemple : "Créer 5 comptes enseignants"
- Action : Exécution, confirmation, clôture

**3. Question** : Demande d'information
- Exemple : "Comment exporter vers Pronote ?"
- Action : Réponse (souvent via doc existante), clôture

**4. Évolution** : Demande de nouvelle fonctionnalité
- Exemple : "Ajouter un champ 'Appréciation' dans les copies"
- Action : Qualification, priorisation, backlog, développement (L3)

### Cycle de Vie d'un Ticket

```
┌──────────┐
│  NOUVEAU │  ← Ticket créé
└─────┬────┘
      │
      ▼
┌──────────┐
│  OUVERT  │  ← En cours d'analyse (L1)
└─────┬────┘
      │
      ├──────────────────┐
      │                  │
      ▼                  ▼
┌──────────┐      ┌────────────┐
│  RÉSOLU  │      │  ESCALADÉ  │  ← Vers L2 ou L3
└─────┬────┘      └─────┬──────┘
      │                  │
      │                  ├─→ (Résolution L2/L3)
      │                  │
      ▼                  ▼
┌──────────┐      ┌──────────┐
│  FERMÉ   │←─────┤  RÉSOLU  │
└──────────┘      └──────────┘
      │
      ├─→ (Réouverture si problème persiste)
      │
┌──────────┐
│ RÉOUVERT │
└─────┬────┘
      │
      └─→ Retour à OUVERT
```

**Statuts** :
- **NOUVEAU** : Ticket vient d'être créé, pas encore pris en charge
- **OUVERT** : Assigné à un agent, en cours de traitement
- **EN ATTENTE** : En attente d'information de l'utilisateur
- **ESCALADÉ** : Transféré à un niveau supérieur (L2/L3)
- **RÉSOLU** : Solution trouvée, en attente de confirmation utilisateur
- **FERMÉ** : Clôturé définitivement (résolu et confirmé)
- **RÉOUVERT** : Problème non résolu ou récurrent

### Bonnes Pratiques

**Pour les utilisateurs** :
- ✅ Vérifier la FAQ avant de soumettre un ticket
- ✅ Fournir un maximum d'informations (captures d'écran, logs)
- ✅ Un ticket = un problème (ne pas mélanger plusieurs demandes)
- ✅ Indiquer l'urgence de manière réaliste

**Pour le support L1** :
- ✅ Accuser réception sous 1h (heures ouvrables)
- ✅ Qualifier la priorité correctement
- ✅ Documenter toutes les actions entreprises
- ✅ Escalader rapidement si hors périmètre L1
- ✅ Tenir l'utilisateur informé régulièrement
- ✅ Demander confirmation avant de fermer

**Pour le support L2/L3** :
- ✅ Fournir une estimation de résolution
- ✅ Communiquer sur les workarounds possibles
- ✅ Documenter la cause racine et la résolution
- ✅ Alimenter la base de connaissance

---

## Indicateurs de Performance (KPI)

### KPI de Support

**Volume** :
- Nombre de tickets par semaine/mois
- Répartition par catégorie (Authentification, Correction, etc.)
- Répartition par priorité (P1, P2, P3, P4)

**Qualité** :
- % de respect des SLA (par priorité)
- Temps moyen de première réponse
- Temps moyen de résolution
- Taux de réouverture (< 5% souhaité)

**Efficacité** :
- % de résolution L1 (objectif : 80%)
- % de résolution via documentation seule (objectif : 60%)
- Taux d'escalade (< 20% souhaité)

**Satisfaction** :
- Note moyenne utilisateurs (sur 5)
- % de tickets avec feedback positif
- NPS (Net Promoter Score) - optionnel

### Reporting

**Rapport hebdomadaire (L1)** :
```markdown
# Rapport de Support - Semaine 5 (30/01 - 05/02/2026)

## Résumé
- **Total tickets** : 15
- **Résolus** : 12 (80%)
- **En cours** : 2
- **Escaladés** : 1 (L2)

## Répartition par Priorité
- P1 : 0
- P2 : 2
- P3 : 10
- P4 : 3

## Répartition par Catégorie
- Authentification : 5 (33%)
- Correction : 6 (40%)
- Identification : 2 (13%)
- Technique : 1 (7%)
- Autre : 1 (7%)

## SLA
- Temps moyen de réponse : 3h (objectif : 4h pour P3) ✅
- Temps moyen de résolution : 18h (objectif : 72h pour P3) ✅

## Problèmes Récurrents
- Enseignants oubliant de déverrouiller les copies → Rappel par email

## Actions
- Mise à jour FAQ avec nouvelle section "Déverrouillage"
```

**Tableau de bord (mensuel)** :
- Graphiques d'évolution du volume de tickets
- Respect des SLA
- Top 5 des problèmes
- Satisfaction utilisateurs

---

## Contacts

### Contacts Internes (Lycée)

| Rôle | Nom | Email | Téléphone | Disponibilité |
|------|-----|-------|-----------|---------------|
| **Admin L1 Principal** | [À compléter] | admin.korrigo@lycee.fr | XXX | Lun-Ven 8h-18h |
| **Admin L1 Secondaire** | [À compléter] | admin2.korrigo@lycee.fr | XXX | Lun-Ven 8h-18h |
| **Support IT (L2)** | [À compléter] | it@lycee.fr | XXX | Lun-Ven 9h-17h |
| **DPO (RGPD)** | [À compléter] | dpo@lycee.fr | XXX | Sur RDV |
| **Direction** | [À compléter] | direction@lycee.fr | XXX | Sur RDV |

### Contacts Externes (si applicable)

| Service | Contact | Usage |
|---------|---------|-------|
| **Support Korrigo L3** | support@korrigo.example.com | Bugs applicatifs, évolutions |
| **Support Infrastructure** | [Prestataire] | Problèmes serveur, réseau |
| **DPO externe** | [Si externalisé] | Conformité RGPD |

### Urgences

**Numéro d'urgence** (P1 uniquement) : [À compléter]
- Disponibilité : 24/7 pendant périodes d'examens
- Hors période : Lun-Ven 8h-20h

**Escalade d'urgence** :
1. Admin L1 principal
2. Support IT (L2)
3. Direction du lycée
4. Support Korrigo (L3) si bug critique

---

## Ressources Complémentaires

**Documentation** :
- [FAQ](FAQ.md) - Questions fréquentes
- [Guide de Dépannage](DEPANNAGE.md) - Résolution de problèmes techniques
- [Guide Administrateur](../admin/GUIDE_UTILISATEUR_ADMIN.md) - Administration complète
- [Procédures Opérationnelles](../admin/PROCEDURES_OPERATIONNELLES.md) - Workflows quotidiens

**Formation** :
- Vidéos tutorielles : [Lien serveur interne ou YouTube privé]
- Base de connaissance : [Lien wiki interne]
- Webinars : [Planning formations à distance]

**Communauté** :
- Forum utilisateurs Korrigo : [Si existe]
- Liste de diffusion : [Email de discussion entre établissements]

---

## Historique des Versions

| Version | Date | Modifications |
|---------|------|---------------|
| 1.0.0 | 30/01/2026 | Création initiale des procédures de support |

---

**Pour toute question sur ces procédures, contactez l'administrateur principal.**
