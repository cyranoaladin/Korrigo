# Documentation Administration - Korrigo

> **Public cible** : Direction du lycée, administrateurs techniques, responsables informatiques  
> **Version** : 1.0  
> **Date** : 30 janvier 2026

---

## 📋 Vue d'Ensemble

Cette section contient toute la documentation nécessaire pour administrer la plateforme Korrigo, de la vision stratégique pour la direction aux procédures opérationnelles quotidiennes pour les administrateurs techniques.

---

## 📚 Documents Disponibles

### 🏛️ [GUIDE_ADMINISTRATEUR_LYCEE.md](GUIDE_ADMINISTRATEUR_LYCEE.md)
**Guide Exécutif pour la Direction du Lycée**  
**Taille** : ~28 KB | **Niveau** : Non-technique | **Public** : Direction, Conseil d'Administration

**Contenu principal** :
- Vue d'ensemble stratégique du système Korrigo
- Bénéfices pédagogiques et organisationnels
- Aspects légaux et conformité RGPD/CNIL
- Budget, ressources et planification
- Gouvernance et responsabilités
- Risques et mesures de sécurité
- Indicateurs de performance (KPI)

**👉 À lire en priorité** si vous êtes membre de la direction ou si vous évaluez Korrigo pour votre établissement.

---

### 👨‍💼 [GUIDE_UTILISATEUR_ADMIN.md](GUIDE_UTILISATEUR_ADMIN.md)
**Manuel Technique de l'Administrateur**  
**Taille** : ~32 KB | **Niveau** : Technique | **Public** : Administrateurs systèmes, Responsables IT

**Contenu principal** :
- Prise en main de l'interface d'administration
- Gestion des utilisateurs (création, modification, suppression)
- Gestion des examens (création, configuration, archivage)
- Configuration système (paramètres, sécurité, intégrations)
- Monitoring et tableaux de bord
- Surveillance des performances
- Gestion des logs et audits
- Procédures de sauvegarde et restauration
- Dépannage technique

**👉 Manuel de référence quotidien** pour les administrateurs techniques.

---

### 👥 [GESTION_UTILISATEURS.md](GESTION_UTILISATEURS.md)
**Procédures de Gestion des Utilisateurs**  
**Taille** : ~17 KB | **Niveau** : Technique | **Public** : Administrateurs

**Contenu principal** :
- Création manuelle d'utilisateurs (enseignants, élèves, secrétariat)
- Import en masse via fichier CSV
- Attribution et modification des rôles
- Gestion des permissions par profil
- Réinitialisation de mots de passe
- Désactivation et suppression de comptes
- Gestion des classes et groupes
- Bonnes pratiques de gestion des accès

**👉 Guide procédural** pour toutes les opérations de gestion des comptes utilisateurs.

---

### ⚙️ [PROCEDURES_OPERATIONNELLES.md](PROCEDURES_OPERATIONNELLES.md)
**Procédures Opérationnelles Quotidiennes**  
**Taille** : ~28 KB | **Niveau** : Technique | **Public** : Administrateurs, Équipe opérationnelle

**Contenu principal** :
- Cycle de vie complet d'un examen (de la création à l'archivage)
- Opérations de début d'année scolaire
- Opérations de fin d'année scolaire
- Opérations quotidiennes et hebdomadaires
- Gestion des périodes d'examen
- Maintenance préventive
- Gestion des changements (change management)
- Procédures d'urgence
- Checklist opérationnelles

**👉 Référence opérationnelle** pour les tâches récurrentes et les procédures standards.

---

## 🚀 Démarrage Rapide

### Pour la Direction du Lycée

1. **Découverte** : Lisez [GUIDE_ADMINISTRATEUR_LYCEE.md](GUIDE_ADMINISTRATEUR_LYCEE.md) sections 1-3
2. **Conformité** : Consultez [GUIDE_ADMINISTRATEUR_LYCEE.md](GUIDE_ADMINISTRATEUR_LYCEE.md) § "Conformité RGPD"
3. **Décision** : Examinez [GUIDE_ADMINISTRATEUR_LYCEE.md](GUIDE_ADMINISTRATEUR_LYCEE.md) § "Budget et Ressources"
4. **Validation** : Consultez la [Politique RGPD](../security/POLITIQUE_RGPD.md) et l'[Accord de Traitement des Données](../legal/ACCORD_TRAITEMENT_DONNEES.md)

### Pour les Administrateurs Techniques

1. **Installation** : Suivez le [Deployment Guide](../DEPLOYMENT_GUIDE.md)
2. **Configuration initiale** : [GUIDE_UTILISATEUR_ADMIN.md](GUIDE_UTILISATEUR_ADMIN.md) § "Première Configuration"
3. **Création des utilisateurs** : [GESTION_UTILISATEURS.md](GESTION_UTILISATEURS.md) § "Import en Masse"
4. **Premier examen** : [PROCEDURES_OPERATIONNELLES.md](PROCEDURES_OPERATIONNELLES.md) § "Cycle de Vie d'un Examen"
5. **Sécurisation** : [Manuel de Sécurité](../security/MANUEL_SECURITE.md)

---

## 📊 Workflows Critiques

### Workflow 1 : Démarrage d'Année Scolaire

```
1. Import des utilisateurs (élèves + enseignants)
   → GESTION_UTILISATEURS.md § "Import CSV"

2. Création des classes et groupes
   → GUIDE_UTILISATEUR_ADMIN.md § "Gestion des Classes"

3. Configuration des paramètres d'année
   → PROCEDURES_OPERATIONNELLES.md § "Début d'Année Scolaire"

4. Formation des utilisateurs
   → Guides Utilisateurs (../users/)

5. Tests de validation
   → PROCEDURES_OPERATIONNELLES.md § "Validation Pré-Production"
```

### Workflow 2 : Création d'un Nouvel Examen

```
1. Créer l'examen dans l'interface admin
   → GUIDE_UTILISATEUR_ADMIN.md § "Création d'Examen"

2. Configurer le barème
   → GUIDE_UTILISATEUR_ADMIN.md § "Configuration Barème"

3. Assigner les correcteurs
   → GUIDE_UTILISATEUR_ADMIN.md § "Attribution Correcteurs"

4. Scanner les copies
   → GUIDE_SECRETARIAT (../users/GUIDE_SECRETARIAT.md)

5. Suivi de correction
   → GUIDE_UTILISATEUR_ADMIN.md § "Tableaux de Bord"

6. Export des notes
   → GUIDE_UTILISATEUR_ADMIN.md § "Export Pronote"
```

### Workflow 3 : Gestion d'une Demande RGPD

```
1. Réception de la demande
   → POLITIQUE_RGPD (../security/POLITIQUE_RGPD.md) § "Droits des Personnes"

2. Vérification identité demandeur
   → POLITIQUE_RGPD § "Procédure de Vérification"

3. Extraction des données (si demande d'accès)
   → GESTION_DONNEES (../security/GESTION_DONNEES.md) § "Export Données"

4. Suppression des données (si demande d'effacement)
   → GESTION_DONNEES § "Suppression et Anonymisation"

5. Confirmation au demandeur
   → POLITIQUE_RGPD § "Délais de Réponse"
```

---

## 🔗 Liens Connexes

### Documentation de Sécurité
- [Politique RGPD](../security/POLITIQUE_RGPD.md) - Conformité RGPD complète
- [Manuel de Sécurité](../security/MANUEL_SECURITE.md) - Sécurité technique
- [Gestion des Données](../security/GESTION_DONNEES.md) - Cycle de vie des données
- [Audit de Conformité](../security/AUDIT_CONFORMITE.md) - Procédures d'audit

### Documentation Légale
- [Politique de Confidentialité](../legal/POLITIQUE_CONFIDENTIALITE.md)
- [Conditions d'Utilisation](../legal/CONDITIONS_UTILISATION.md)
- [Accord de Traitement des Données](../legal/ACCORD_TRAITEMENT_DONNEES.md)

### Guides Utilisateurs
- [Guide Enseignant](../users/GUIDE_ENSEIGNANT.md)
- [Guide Secrétariat](../users/GUIDE_SECRETARIAT.md)
- [Guide Étudiant](../users/GUIDE_ETUDIANT.md)

### Documentation Technique
- [Architecture](../ARCHITECTURE.md)
- [API Reference](../API_REFERENCE.md)
- [Database Schema](../DATABASE_SCHEMA.md)
- [Deployment Guide](../DEPLOYMENT_GUIDE.md)

### Support
- [FAQ](../support/FAQ.md) - Section Administration
- [Dépannage](../support/DEPANNAGE.md)
- [Support](../support/SUPPORT.md)

---

## ❓ Questions Fréquentes (Administration)

### Gestion des Utilisateurs

**Q : Comment importer 500 élèves en une seule fois ?**  
R : Voir [GESTION_UTILISATEURS.md](GESTION_UTILISATEURS.md) § "Import en Masse via CSV"

**Q : Comment réinitialiser le mot de passe d'un élève ?**  
R : Voir [GESTION_UTILISATEURS.md](GESTION_UTILISATEURS.md) § "Réinitialisation Mots de Passe"

**Q : Peut-on désactiver un compte temporairement sans le supprimer ?**  
R : Oui, voir [GESTION_UTILISATEURS.md](GESTION_UTILISATEURS.md) § "Désactivation de Compte"

### Gestion des Examens

**Q : Combien d'examens peut-on créer simultanément ?**  
R : Voir [GUIDE_UTILISATEUR_ADMIN.md](GUIDE_UTILISATEUR_ADMIN.md) § "Limites Système"

**Q : Comment archiver un examen terminé ?**  
R : Voir [PROCEDURES_OPERATIONNELLES.md](PROCEDURES_OPERATIONNELLES.md) § "Archivage Examens"

**Q : Peut-on exporter les notes vers Pronote ?**  
R : Oui, voir [GUIDE_UTILISATEUR_ADMIN.md](GUIDE_UTILISATEUR_ADMIN.md) § "Export Pronote CSV"

### RGPD et Conformité

**Q : Combien de temps conserver les copies numérisées ?**  
R : Voir [POLITIQUE_RGPD](../security/POLITIQUE_RGPD.md) § "Durées de Conservation"

**Q : Comment supprimer toutes les données d'un élève qui change d'établissement ?**  
R : Voir [GESTION_DONNEES](../security/GESTION_DONNEES.md) § "Suppression Complète"

**Q : Qui est le DPO pour Korrigo ?**  
R : Voir [POLITIQUE_RGPD](../security/POLITIQUE_RGPD.md) § "Contacts et Responsabilités"

---

## 📞 Contact et Support

Pour toute question administrative ou technique :

1. **Consultez** : [FAQ](../support/FAQ.md) section Administration
2. **Dépannage** : [Guide de Dépannage](../support/DEPANNAGE.md)
3. **Support technique** : Voir [Procédures de Support](../support/SUPPORT.md)

---

## 📌 Informations

- **Dernière mise à jour** : 30 janvier 2026
- **Version** : 1.0
- **Maintenance** : Voir [SUPPORT](../support/SUPPORT.md) § "Maintenance Documentation"

---

**🏠 Retour** : [Index Principal](../INDEX.md) | [README Projet](../../README.md)
