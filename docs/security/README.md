# Documentation Sécurité et Conformité - Korrigo

> **Public cible** : Direction, DPO, Administrateurs, Responsables sécurité, Auditeurs  
> **Version** : 1.0  
> **Date** : 30 janvier 2026

---

## 📋 Vue d'Ensemble

Cette section contient toute la documentation relative à la sécurité, la protection des données personnelles, la conformité RGPD/CNIL, et les procédures d'audit. Elle est essentielle pour assurer la conformité légale et la sécurité du système Korrigo dans un établissement scolaire.

---

## 📚 Documents Disponibles

### 🛡️ [POLITIQUE_RGPD.md](POLITIQUE_RGPD.md)
**Politique Complète de Conformité RGPD/CNIL**  
**Taille** : ~33 KB | **Niveau** : Légal/Technique | **Public** : Direction, DPO, Responsables conformité

**Contenu principal** :
- Cadre légal et réglementaire (RGPD, Loi Informatique et Libertés, CNIL)
- Rôles et responsabilités (responsable de traitement, sous-traitant, DPO)
- Inventaire des traitements de données personnelles
- Finalités et bases légales
- Droits des personnes concernées (accès, rectification, effacement, opposition, portabilité)
- Mesures de sécurité techniques et organisationnelles
- Durées de conservation des données
- Transferts de données (si applicable)
- Procédures de gestion des demandes RGPD
- Gestion des violations de données (data breach)
- Formation et sensibilisation
- Documentation et registre des activités de traitement

**👉 Document fondamental** pour la conformité RGPD. À valider par le DPO et la direction.

**Obligatoire pour** :
- ✅ Mise en production du système
- ✅ Audits CNIL
- ✅ Signature du DPA (Accord de Traitement des Données)

---

### 🔐 [MANUEL_SECURITE.md](MANUEL_SECURITE.md)
**Manuel Technique de Sécurité**  
**Taille** : ~27 KB | **Niveau** : Technique | **Public** : Administrateurs systèmes, RSSI

**Contenu principal** :
- Architecture de sécurité
- Authentification et gestion des sessions
- Contrôle d'accès et permissions (RBAC)
- Sécurité des données (chiffrement, hachage, pseudonymisation)
- Sécurité réseau et infrastructure
- Journalisation et audit (audit logs)
- Gestion des vulnérabilités
- Procédures de réponse aux incidents de sécurité
- Tests de sécurité et pentests
- Sécurité du développement (SSDLC)
- Sauvegarde et récupération
- Gestion des correctifs (patch management)
- Configuration sécurisée
- Hardening des systèmes

**👉 Guide technique** pour sécuriser et maintenir le système.

**Référence technique** :
- Complète [SECURITY_PERMISSIONS_INVENTORY.md](../../SECURITY_PERMISSIONS_INVENTORY.md) (28.8 KB)

---

### 💾 [GESTION_DONNEES.md](GESTION_DONNEES.md)
**Guide de Gestion du Cycle de Vie des Données**  
**Taille** : ~22 KB | **Niveau** : Technique | **Public** : Administrateurs, DPO

**Contenu principal** :
- Cycle de vie des données (collecte → archivage → suppression)
- Catégories de données personnelles traitées
- Stockage et organisation des données
- Sauvegarde et restauration
- Politiques de rétention (combien de temps conserver quoi)
- Archivage des données
- Suppression et anonymisation sécurisées
- Export des données personnelles (droit à la portabilité)
- Procédures de purge automatique
- Gestion des données sensibles
- Minimisation des données (privacy by design)
- Procédures de migration de données

**👉 Guide opérationnel** pour la gestion quotidienne des données.

**Cas d'usage** :
- ✅ Répondre à une demande d'accès RGPD (export données élève)
- ✅ Supprimer les données d'un élève ayant quitté l'établissement
- ✅ Archiver les examens de fin d'année
- ✅ Planifier les purges de données expirées

---

### 📋 [AUDIT_CONFORMITE.md](AUDIT_CONFORMITE.md)
**Procédures d'Audit de Conformité**  
**Taille** : ~14 KB | **Niveau** : Procédural | **Public** : DPO, Auditeurs, Direction

**Contenu principal** :
- Méthodologie d'audit de conformité RGPD
- Calendrier d'audits (annuel, trimestriel)
- Checklist d'audit RGPD
- Checklist d'audit sécurité
- Procédure d'auto-évaluation
- Audits techniques (logs, permissions, vulnérabilités)
- Audits organisationnels (procédures, formation, documentation)
- Reporting et documentation des audits
- Gestion des non-conformités
- Plan d'actions correctives
- Préparation aux audits CNIL
- Suivi des recommandations

**👉 Guide procédural** pour les audits internes et externes.

**Fréquence recommandée** :
- 🔄 Auto-évaluation : Trimestrielle
- 🔍 Audit complet : Annuel
- 📊 Revue des logs : Mensuelle

---

## 🚀 Démarrage Rapide

### Pour la Direction et le DPO

```
1. Comprendre les obligations RGPD
   → POLITIQUE_RGPD.md § "Cadre Légal et Réglementaire"

2. Identifier les responsabilités
   → POLITIQUE_RGPD.md § "Rôles et Responsabilités"

3. Valider l'inventaire des traitements
   → POLITIQUE_RGPD.md § "Inventaire des Traitements"

4. Signer le DPA avec Korrigo
   → ACCORD_TRAITEMENT_DONNEES (../legal/ACCORD_TRAITEMENT_DONNEES.md)

5. Planifier les audits
   → AUDIT_CONFORMITE.md § "Calendrier d'Audits"

6. Former les équipes
   → POLITIQUE_RGPD.md § "Formation et Sensibilisation"
```

### Pour les Administrateurs Techniques

```
1. Comprendre l'architecture de sécurité
   → MANUEL_SECURITE.md § "Architecture de Sécurité"

2. Configurer l'authentification
   → MANUEL_SECURITE.md § "Authentification et Sessions"

3. Paramétrer les permissions
   → MANUEL_SECURITE.md § "Contrôle d'Accès RBAC"
   → SECURITY_PERMISSIONS_INVENTORY.md

4. Activer la journalisation
   → MANUEL_SECURITE.md § "Journalisation et Audit"

5. Configurer les sauvegardes
   → GESTION_DONNEES.md § "Sauvegarde et Restauration"

6. Planifier les rétentions
   → GESTION_DONNEES.md § "Politiques de Rétention"

7. Tester la récupération
   → MANUEL_SECURITE.md § "Tests de Récupération"
```

### Pour Gérer une Demande RGPD

```
1. Réception de la demande
   → POLITIQUE_RGPD.md § "Procédures de Gestion des Demandes"

2. Vérifier l'identité du demandeur
   → POLITIQUE_RGPD.md § "Vérification d'Identité"

3. Identifier le type de demande
   - Droit d'accès → POLITIQUE_RGPD.md § "Droit d'Accès"
   - Droit de rectification → § "Droit de Rectification"
   - Droit à l'effacement → § "Droit à l'Effacement"
   - Droit à la portabilité → § "Droit à la Portabilité"
   - Droit d'opposition → § "Droit d'Opposition"

4. Exécuter la demande
   - Export données → GESTION_DONNEES.md § "Export des Données"
   - Suppression → GESTION_DONNEES.md § "Suppression Sécurisée"

5. Répondre dans les délais
   → POLITIQUE_RGPD.md § "Délais de Réponse" (1 mois max)

6. Documenter la demande
   → POLITIQUE_RGPD.md § "Documentation des Demandes"
```

---

## 📊 Workflows de Sécurité Critiques

### Workflow 1 : Gestion d'un Incident de Sécurité

```
┌─────────────────────────────────────────┐
│ 1. Détection de l'incident              │
│    → Alerte automatique ou signalement  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 2. Qualification de l'incident          │
│    → Gravité, type, impact              │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 3. Confinement immédiat                 │
│    → Isolation, blocage accès           │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 4. Investigation                        │
│    → Analyse logs, forensics            │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 5. Éradication de la menace             │
│    → Correction vulnérabilité           │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 6. Récupération                         │
│    → Restauration service               │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 7. Notification (si violation données)  │
│    → CNIL (72h) + Personnes concernées  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 8. Post-mortem et amélioration          │
│    → Rapport, leçons apprises           │
└─────────────────────────────────────────┘
```

**Référence** : [MANUEL_SECURITE.md](MANUEL_SECURITE.md) § "Réponse aux Incidents de Sécurité"  
**Référence** : [POLITIQUE_RGPD.md](POLITIQUE_RGPD.md) § "Gestion des Violations de Données"

---

### Workflow 2 : Audit Trimestriel de Conformité

```
┌─────────────────────────────────────────┐
│ 1. Planification de l'audit             │
│    → Calendrier, scope, équipe          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 2. Audit technique                      │
│    → Logs, permissions, sauvegardes     │
│    → Checklist AUDIT_CONFORMITE.md      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 3. Audit organisationnel                │
│    → Procédures, documentation, formation│
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 4. Vérification registre traitements    │
│    → Mise à jour si nécessaire          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 5. Tests de sécurité                    │
│    → Scan vulnérabilités, tests accès   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 6. Rapport d'audit                      │
│    → Findings, non-conformités, risques │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 7. Plan d'actions correctives           │
│    → Priorisation, assignation, délais  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ 8. Suivi et validation                  │
│    → Vérification corrections           │
└─────────────────────────────────────────┘
```

**Référence** : [AUDIT_CONFORMITE.md](AUDIT_CONFORMITE.md) § "Méthodologie d'Audit"

---

## 🔗 Liens Connexes

### Documentation Administrative
- [Guide Administrateur Lycée](../admin/GUIDE_ADMINISTRATEUR_LYCEE.md) - Vision direction sur sécurité
- [Guide Utilisateur Admin](../admin/GUIDE_UTILISATEUR_ADMIN.md) - Opérations sécurité quotidiennes
- [Procédures Opérationnelles](../admin/PROCEDURES_OPERATIONNELLES.md) - Maintenance sécurisée

### Documentation Légale (Connexe RGPD)
- [Politique de Confidentialité](../legal/POLITIQUE_CONFIDENTIALITE.md) - Politique utilisateur (simplifiée)
- [Accord de Traitement des Données (DPA)](../legal/ACCORD_TRAITEMENT_DONNEES.md) - Contrat RGPD Article 28
- [Conditions d'Utilisation](../legal/CONDITIONS_UTILISATION.md) - CGU incluant clauses sécurité
- [Formulaires de Consentement](../legal/FORMULAIRES_CONSENTEMENT.md) - Consentement RGPD

### Documentation Technique
- [**SECURITY_PERMISSIONS_INVENTORY.md**](../../SECURITY_PERMISSIONS_INVENTORY.md) - Inventaire technique complet des permissions (28.8 KB)
- [Architecture](../ARCHITECTURE.md) - Architecture technique et sécurité
- [Database Schema](../DATABASE_SCHEMA.md) - Schéma base de données
- [Deployment Guide](../DEPLOYMENT_GUIDE.md) - Déploiement sécurisé

### Guides Utilisateurs (Formation Sécurité)
- [Guide Enseignant](../users/GUIDE_ENSEIGNANT.md) - Bonnes pratiques sécurité enseignants
- [Guide Secrétariat](../users/GUIDE_SECRETARIAT.md) - Bonnes pratiques sécurité secrétariat
- [Guide Étudiant](../users/GUIDE_ETUDIANT.md) - Vie privée et sécurité élèves

### Support
- [FAQ](../support/FAQ.md) - Section Sécurité et RGPD
- [Dépannage](../support/DEPANNAGE.md) - Problèmes de sécurité
- [Support](../support/SUPPORT.md) - Escalade incidents sécurité

---

## 📋 Checklists de Conformité

### ✅ Checklist Mise en Production (Sécurité & RGPD)

#### Documents Légaux
- [ ] Politique RGPD validée par DPO
- [ ] DPA signé entre établissement et Korrigo
- [ ] Politique de confidentialité publiée
- [ ] Formulaires de consentement distribués (si requis)
- [ ] Registre des activités de traitement à jour

#### Mesures Techniques
- [ ] Chiffrement des données en transit (HTTPS/TLS)
- [ ] Chiffrement des données au repos (base de données)
- [ ] Authentification forte activée
- [ ] Contrôle d'accès RBAC configuré
- [ ] Journalisation (audit logs) activée
- [ ] Sauvegardes automatiques configurées
- [ ] Tests de restauration effectués
- [ ] Scan de vulnérabilités réalisé
- [ ] Certificats SSL valides

#### Mesures Organisationnelles
- [ ] DPO désigné et contactable
- [ ] Équipe formée à la sécurité et RGPD
- [ ] Procédures de réponse aux incidents documentées
- [ ] Procédures de gestion des demandes RGPD opérationnelles
- [ ] Plan de continuité d'activité (PCA) défini
- [ ] Plan de reprise d'activité (PRA) testé
- [ ] Calendrier d'audits planifié
- [ ] Politique de rétention des données définie

**Référence complète** : [POLITIQUE_RGPD.md](POLITIQUE_RGPD.md) § "Checklist de Conformité"

---

### ✅ Checklist Audit Trimestriel

#### Audit Technique
- [ ] Revue des logs d'authentification
- [ ] Revue des logs d'accès aux données sensibles
- [ ] Vérification des permissions utilisateurs
- [ ] Vérification des sauvegardes (complétude, fréquence)
- [ ] Test de restauration d'une sauvegarde
- [ ] Scan de vulnérabilités système
- [ ] Vérification des mises à jour de sécurité
- [ ] Revue des comptes inactifs
- [ ] Vérification des certificats SSL (expiration)

#### Audit Organisationnel
- [ ] Vérification registre des traitements à jour
- [ ] Vérification procédures RGPD suivies
- [ ] Revue des demandes RGPD (délais respectés ?)
- [ ] Vérification formation utilisateurs
- [ ] Revue des incidents de sécurité (s'il y en a eu)
- [ ] Vérification politiques de rétention appliquées
- [ ] Vérification documentation à jour

#### Audit des Données
- [ ] Vérification minimisation des données
- [ ] Vérification exactitude des données
- [ ] Vérification purge données expirées
- [ ] Vérification anonymisation copies archivées (si applicable)

**Référence complète** : [AUDIT_CONFORMITE.md](AUDIT_CONFORMITE.md) § "Checklist d'Audit"

---

## ❓ Questions Fréquentes (Sécurité & RGPD)

### RGPD et Conformité

**Q : Qui est le responsable de traitement pour Korrigo ?**  
R : L'établissement scolaire (le lycée). Voir [POLITIQUE_RGPD.md](POLITIQUE_RGPD.md) § "Rôles et Responsabilités"

**Q : Combien de temps peut-on conserver les copies numérisées ?**  
R : Voir [POLITIQUE_RGPD.md](POLITIQUE_RGPD.md) § "Durées de Conservation" et [GESTION_DONNEES.md](GESTION_DONNEES.md) § "Politiques de Rétention"

**Q : Que faire si un élève demande la suppression de ses données ?**  
R : Voir [POLITIQUE_RGPD.md](POLITIQUE_RGPD.md) § "Droit à l'Effacement" et [GESTION_DONNEES.md](GESTION_DONNEES.md) § "Suppression Sécurisée"

**Q : Doit-on notifier la CNIL en cas de piratage ?**  
R : Oui, si violation de données personnelles. Voir [POLITIQUE_RGPD.md](POLITIQUE_RGPD.md) § "Notification CNIL (72h)"

**Q : Les élèves doivent-ils consentir au traitement de leurs données ?**  
R : Voir [POLITIQUE_RGPD.md](POLITIQUE_RGPD.md) § "Base Légale" (généralement mission d'intérêt public, pas de consentement requis pour fonction pédagogique)

### Sécurité Technique

**Q : Les mots de passe sont-ils stockés en clair ?**  
R : Non, hachés avec Argon2. Voir [MANUEL_SECURITE.md](MANUEL_SECURITE.md) § "Hachage Mots de Passe"

**Q : Les communications sont-elles chiffrées ?**  
R : Oui, HTTPS/TLS. Voir [MANUEL_SECURITE.md](MANUEL_SECURITE.md) § "Chiffrement en Transit"

**Q : Quelle est la fréquence des sauvegardes ?**  
R : Voir [GESTION_DONNEES.md](GESTION_DONNEES.md) § "Sauvegarde et Restauration" et configuration système

**Q : Les logs sont-ils consultables ?**  
R : Oui, par les administrateurs. Voir [MANUEL_SECURITE.md](MANUEL_SECURITE.md) § "Journalisation et Audit"

**Q : Que faire en cas de violation de données (data breach) ?**  
R : Voir [MANUEL_SECURITE.md](MANUEL_SECURITE.md) § "Réponse aux Incidents" et [POLITIQUE_RGPD.md](POLITIQUE_RGPD.md) § "Gestion des Violations"

### Audits

**Q : Quelle est la fréquence d'audit recommandée ?**  
R : Trimestrielle (auto-évaluation) et annuelle (audit complet). Voir [AUDIT_CONFORMITE.md](AUDIT_CONFORMITE.md) § "Calendrier"

**Q : Qui peut réaliser les audits ?**  
R : DPO, administrateurs, ou auditeurs externes. Voir [AUDIT_CONFORMITE.md](AUDIT_CONFORMITE.md) § "Équipe d'Audit"

**Q : Comment se préparer à un audit CNIL ?**  
R : Voir [AUDIT_CONFORMITE.md](AUDIT_CONFORMITE.md) § "Préparation aux Audits CNIL"

---

## 📞 Contact et Support

### En Cas d'Incident de Sécurité

**🚨 URGENCE SÉCURITÉ** :
1. **Immédiatement** : Contacter l'administrateur système
2. **Suivre** : [MANUEL_SECURITE.md](MANUEL_SECURITE.md) § "Procédure d'Incident"
3. **Si violation données** : Notifier DPO immédiatement

### Pour Questions RGPD

- **DPO de l'établissement** : Voir [POLITIQUE_RGPD.md](POLITIQUE_RGPD.md) § "Contact DPO"
- **Demandes RGPD** : Voir [POLITIQUE_RGPD.md](POLITIQUE_RGPD.md) § "Formulaire de Demande"

### Pour Audits

- **Planification** : Voir [AUDIT_CONFORMITE.md](AUDIT_CONFORMITE.md) § "Contact Audit"
- **Support** : Voir [Support](../support/SUPPORT.md)

---

## 📌 Informations

- **Dernière mise à jour** : 30 janvier 2026
- **Version** : 1.0
- **Conformité** : RGPD, Loi Informatique et Libertés, Recommandations CNIL
- **Maintenance** : Voir [SUPPORT](../support/SUPPORT.md) § "Maintenance Documentation"

---

## 🔐 Avertissement Important

> **⚠️ CONFIDENTIALITÉ** : Les documents de cette section contiennent des informations sensibles sur la sécurité et la conformité de Korrigo. Leur diffusion doit être limitée au personnel autorisé (Direction, DPO, RSSI, Administrateurs).
>
> **⚠️ MISE À JOUR** : La conformité RGPD et les mesures de sécurité doivent être revues régulièrement. Les procédures et politiques doivent être maintenues à jour en fonction des évolutions réglementaires et techniques.

---

**🏠 Retour** : [Index Principal](../INDEX.md) | [README Projet](../../README.md)
