# Audit et Conformité RGPD/Sécurité
# Plateforme Korrigo PMF

> **Version**: 1.0.0  
> **Date**: 30 Janvier 2026  
> **Public**: DPO, Auditeurs internes, Direction, RSSI  
> **Classification**: Usage interne - Sensible  
> **Conformité**: RGPD (UE) 2016/679, CNIL

---

## 📋 Table des Matières

1. [Introduction](#introduction)
2. [Méthodologie d'Audit](#méthodologie-daudit)
3. [Calendrier et Fréquence](#calendrier-et-fréquence)
4. [Checklist d'Audit RGPD](#checklist-daudit-rgpd)
5. [Checklist d'Audit Sécurité](#checklist-daudit-sécurité)
6. [Procédure d'Auto-Évaluation](#procédure-dauto-évaluation)
7. [Audits Techniques](#audits-techniques)
8. [Audits Organisationnels](#audits-organisationnels)
9. [Reporting et Documentation](#reporting-et-documentation)
10. [Gestion des Non-Conformités](#gestion-des-non-conformités)
11. [Préparation aux Audits CNIL](#préparation-aux-audits-cnil)
12. [Suivi des Recommandations](#suivi-des-recommandations)

---

## 1. Introduction

### 1.1 Objet

Ce document définit les procédures d'audit de conformité RGPD et de sécurité pour la plateforme Korrigo PMF, permettant de vérifier le respect des obligations légales et des mesures de protection des données personnelles des élèves.

### 1.2 Objectifs des Audits

- **Conformité RGPD** : Vérifier le respect du Règlement européen 2016/679
- **Conformité CNIL** : Respecter les recommandations de la CNIL pour le secteur éducatif
- **Sécurité** : Valider l'efficacité des mesures techniques et organisationnelles
- **Amélioration continue** : Identifier les risques et opportunités d'amélioration
- **Accountability** : Démontrer la conformité en cas de contrôle

### 1.3 Périmètre d'Audit

**Aspects couverts** :
- ✅ Conformité RGPD (finalités, bases légales, droits des personnes)
- ✅ Sécurité technique (accès, chiffrement, journalisation)
- ✅ Gestion des données (conservation, archivage, suppression)
- ✅ Documentation (registre, DPA, politiques)
- ✅ Formation et sensibilisation des utilisateurs
- ✅ Gestion des incidents et violations de données

**Références documentaires** :
- [POLITIQUE_RGPD.md](POLITIQUE_RGPD.md) : Politique de protection des données
- [MANUEL_SECURITE.md](MANUEL_SECURITE.md) : Mesures de sécurité techniques
- [GESTION_DONNEES.md](GESTION_DONNEES.md) : Cycle de vie des données
- [ACCORD_TRAITEMENT_DONNEES.md](../legal/ACCORD_TRAITEMENT_DONNEES.md) : DPA

---

## 2. Méthodologie d'Audit

### 2.1 Types d'Audits

| Type | Fréquence | Responsable | Durée | Objectif |
|------|-----------|-------------|-------|----------|
| **Auto-évaluation rapide** | Trimestrielle | Administrateur NSI | 2h | Contrôle de routine |
| **Audit interne complet** | Annuel | DPO + RSSI | 2 jours | Conformité globale |
| **Audit technique** | Semestriel | Admin système | 4h | Sécurité infrastructure |
| **Revue des logs** | Mensuelle | Admin NSI | 1h | Détection incidents |
| **Audit externe** | Si requis | Auditeur CNIL | Variable | Validation officielle |

### 2.2 Phases d'un Audit Complet

```
┌─────────────┐
│ PRÉPARATION │  - Collecte documentation
│  (J-15)     │  - Définition périmètre
└──────┬──────┘  - Planification interviews
       │
       v
┌─────────────┐
│  EXÉCUTION  │  - Vérification checklists
│  (J0 → J+2) │  - Tests techniques
└──────┬──────┘  - Interviews utilisateurs
       │
       v
┌─────────────┐
│  ANALYSE    │  - Synthèse des écarts
│  (J+3 → J+5)│  - Évaluation risques
└──────┬──────┘  - Recommandations
       │
       v
┌─────────────┐
│  REPORTING  │  - Rapport d'audit
│  (J+7)      │  - Plan d'actions
└──────┬──────┘  - Présentation direction
       │
       v
┌─────────────┐
│    SUIVI    │  - Mise en œuvre actions
│ (J+30/60)   │  - Contrôle effectivité
└─────────────┘
```

### 2.3 Outils d'Audit

**Documentation** :
- Registre des activités de traitement (Excel/Google Sheets)
- Cartographie des flux de données
- Inventaire des permissions ([SECURITY_PERMISSIONS_INVENTORY.md](../../SECURITY_PERMISSIONS_INVENTORY.md))

**Outils techniques** :
```bash
# Audit des accès utilisateurs
python manage.py audit_permissions

# Vérification des logs de sécurité (6 derniers mois)
python manage.py check_audit_logs --days=180

# Export registre RGPD
python manage.py export_rgpd_register
```

---

## 3. Calendrier et Fréquence

### 3.1 Planning Annuel Type

| Mois | Action | Responsable | Livrables |
|------|--------|-------------|-----------|
| **Janvier** | Audit interne complet | DPO + RSSI | Rapport annuel N-1 |
| **Février** | Plan d'actions correctives | Direction | Roadmap sécurité |
| **Avril** | Auto-évaluation T1 | Admin NSI | Checklist Q1 |
| **Juin** | Audit technique infrastructure | Admin système | Rapport pentest |
| **Juillet** | Auto-évaluation T2 | Admin NSI | Checklist Q2 |
| **Septembre** | Revue registre traitements | DPO | Registre mis à jour |
| **Octobre** | Auto-évaluation T3 | Admin NSI | Checklist Q3 |
| **Novembre** | Audit organisationnel | DPO | Rapport formation |
| **Décembre** | Auto-évaluation T4 | Admin NSI | Checklist Q4 |
| **Mensuel** | Revue logs sécurité | Admin NSI | Rapport incidents |

### 3.2 Déclencheurs d'Audit Exceptionnel

**Audits hors calendrier déclenchés si** :
- ❗ Violation de données personnelles (data breach)
- ❗ Mise à jour majeure de la plateforme (nouvelle version)
- ❗ Changement de sous-traitant (hébergement, maintenance)
- ❗ Demande CNIL (contrôle sur pièces ou sur place)
- ❗ Incident de sécurité majeur
- ❗ Modification législative (nouveau décret CNIL)

---

## 4. Checklist d'Audit RGPD

### 4.1 Conformité Générale

**A - Base Légale et Finalités**

| Critère | Conforme | Observations | Preuve |
|---------|----------|--------------|--------|
| Les finalités du traitement sont clairement définies | ☐ Oui ☐ Non | | POLITIQUE_RGPD.md § 4.2 |
| Base légale identifiée (Art. 6.1.e - mission publique) | ☐ Oui ☐ Non | | Code de l'éducation |
| Absence de détournement de finalité | ☐ Oui ☐ Non | | Audit logs |
| Information des personnes concernées (élèves/parents) | ☐ Oui ☐ Non | | POLITIQUE_CONFIDENTIALITE.md |

**B - Droits des Personnes**

| Critère | Conforme | Délai Réponse | Procédure |
|---------|----------|---------------|-----------|
| Droit d'accès (Art. 15) : procédure opérationnelle | ☐ Oui ☐ Non | < 1 mois | `export_student_data.sh` |
| Droit de rectification (Art. 16) : formulaire disponible | ☐ Oui ☐ Non | < 1 mois | Interface admin |
| Droit à l'effacement (Art. 17) : script anonymisation | ☐ Oui ☐ Non | < 1 mois | `anonymize_student.py` |
| Droit d'opposition (Art. 21) : possibilité de refus portail | ☐ Oui ☐ Non | Immédiat | Formulaire consentement |
| Droit à la portabilité (Art. 20) : export JSON | ☐ Oui ☐ Non | < 1 mois | `manage.py export_data` |

**C - Conservation et Suppression**

| Critère | Conforme | Durée | Automatisation |
|---------|----------|-------|----------------|
| Durée de conservation définie (examen) | ☐ Oui ☐ Non | 1 an | GESTION_DONNEES.md § 6 |
| Durée de conservation logs d'audit | ☐ Oui ☐ Non | 6 mois | Celery purge task |
| Archivage fin d'année académique | ☐ Oui ☐ Non | Juillet | Script manuel |
| Suppression automatique données expirées | ☐ Oui ☐ Non | Daily | `purge_expired_data` |

### 4.2 Sécurité Technique (Art. 32 RGPD)

| Mesure | Implémentée | Niveau | Validation |
|--------|-------------|--------|------------|
| Chiffrement des données en transit (HTTPS) | ☐ Oui ☐ Non | TLS 1.3 | `openssl s_client` |
| Chiffrement au repos (PostgreSQL) | ☐ Oui ☐ Non | AES-256 | Config DB |
| Hachage des mots de passe | ☐ Oui ☐ Non | Argon2 | `PASSWORD_HASHERS` |
| Pseudonymisation des logs | ☐ Oui ☐ Non | IP masquées | Audit GradingEvent |
| Contrôle d'accès RBAC | ☐ Oui ☐ Non | 6 rôles | SECURITY_PERMISSIONS |
| Journalisation des accès | ☐ Oui ☐ Non | 100% actions | `GradingEvent` |
| Sauvegarde chiffrée | ☐ Oui ☐ Non | GPG | `/backups/*.gpg` |
| Politique de mots de passe | ☐ Oui ☐ Non | 12 car. min | Django validators |

### 4.3 Documentation et Traçabilité

| Document | Existant | Mis à jour | Responsable |
|----------|----------|------------|-------------|
| Registre des activités de traitement | ☐ Oui ☐ Non | Date: ______ | DPO |
| Analyse d'impact (AIPD) | ☐ Oui ☐ Non | Date: ______ | DPO |
| Politique de protection des données | ☐ Oui ☐ Non | Date: ______ | DPO |
| DPA avec sous-traitants | ☐ Oui ☐ Non | Date: ______ | Direction |
| Procédure violation de données | ☐ Oui ☐ Non | Date: ______ | DPO |
| Formulaires de consentement | ☐ Oui ☐ Non | Date: ______ | Secrétariat |

---

## 5. Checklist d'Audit Sécurité

### 5.1 Authentification et Accès

**Vérifications à effectuer** :

```bash
# 1. Liste des comptes actifs
python manage.py list_users --active

# 2. Comptes administrateurs (doit être minimal)
python manage.py list_users --role=admin

# 3. Comptes inactifs depuis 6 mois (à désactiver)
python manage.py list_inactive_users --days=180

# 4. Vérification force mots de passe
python manage.py check_password_strength

# 5. Sessions actives (détecter anomalies)
python manage.py list_sessions
```

**Checklist** :

| Critère | Conforme | Action |
|---------|----------|--------|
| Aucun compte avec mot de passe par défaut | ☐ Oui ☐ Non | Forcer changement |
| Comptes admin limités (≤ 2) | ☐ Oui ☐ Non | Révoquer excès |
| Comptes inactifs désactivés | ☐ Oui ☐ Non | `user.is_active = False` |
| Sessions expirées après 24h inactivité | ☐ Oui ☐ Non | Vérifier `SESSION_COOKIE_AGE` |
| 2FA activé pour admin (si disponible) | ☐ Oui ☐ Non | Activer django-otp |

### 5.2 Permissions et Autorisations

**Test de matrice de permissions** :

| Rôle | Créer examen | Voir copie | Annoter | Valider note | Admin |
|------|--------------|------------|---------|--------------|-------|
| Élève | ❌ | ✅ (sienne) | ❌ | ❌ | ❌ |
| Enseignant | ❌ | ✅ (sa matière) | ✅ | ❌ | ❌ |
| Secrétariat | ✅ | ✅ (toutes) | ❌ | ❌ | ❌ |
| Admin Matière | ❌ | ✅ (sa matière) | ✅ | ✅ | ❌ |
| Admin NSI | ✅ | ✅ | ✅ | ✅ | ✅ |
| Proviseur | ❌ | ✅ (vue seule) | ❌ | ❌ | ❌ |

**Tests à exécuter** :

```python
# Script de test automatique (tests/test_permissions.py)
from django.test import TestCase
from korrigo.models import User, Exam, ExamCopy

class PermissionsAuditTestCase(TestCase):
    def test_student_cannot_view_other_copies(self):
        # Test isolation des copies élèves
        pass
    
    def test_teacher_cannot_access_other_subject(self):
        # Test cloisonnement par matière
        pass
    
    def test_secretary_cannot_annotate(self):
        # Test lecture seule secrétariat
        pass
```

### 5.3 Audit des Logs de Sécurité

**Événements critiques à vérifier** :

```sql
-- Connexions échouées (attaques brute-force?)
SELECT username, COUNT(*), MAX(timestamp)
FROM auth_failed_login
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY username
HAVING COUNT(*) > 10;

-- Accès admin en dehors heures bureau (8h-18h)
SELECT user, action, timestamp
FROM grading_event
WHERE user_role = 'admin'
  AND (EXTRACT(HOUR FROM timestamp) < 8 OR EXTRACT(HOUR FROM timestamp) > 18)
  AND timestamp > NOW() - INTERVAL '7 days';

-- Téléchargements massifs de copies (exfiltration?)
SELECT user_id, COUNT(*) as download_count, DATE(timestamp)
FROM grading_event
WHERE action_type = 'copy_download'
  AND timestamp > NOW() - INTERVAL '1 day'
GROUP BY user_id, DATE(timestamp)
HAVING COUNT(*) > 50;

-- Modifications de permissions
SELECT actor, target_user, old_permissions, new_permissions, timestamp
FROM permission_change_log
WHERE timestamp > NOW() - INTERVAL '30 days'
ORDER BY timestamp DESC;
```

### 5.4 Vulnérabilités et Correctifs

**Commandes de vérification** :

```bash
# Scan dépendances Python (CVE)
pip install safety
safety check --json > security_report.json

# Vérification Django (XSS, CSRF, SQL injection)
python manage.py check --deploy

# Scan fichiers sensibles exposés
curl -I https://korrigo.lycee.fr/settings.py  # Doit retourner 404
curl -I https://korrigo.lycee.fr/.env         # Doit retourner 404

# Headers de sécurité HTTP
curl -I https://korrigo.lycee.fr/ | grep -E "Strict-Transport-Security|X-Frame-Options|Content-Security-Policy"
```

**Checklist** :

| Critère | Conforme | Action |
|---------|----------|--------|
| Aucune CVE critique non patchée | ☐ Oui ☐ Non | `pip install -U` |
| Django settings en mode production | ☐ Oui ☐ Non | `DEBUG=False` |
| Fichiers sensibles non exposés | ☐ Oui ☐ Non | Vérifier `.gitignore` |
| Headers sécurité présents (HSTS, CSP) | ☐ Oui ☐ Non | Config Nginx |
| Certificat SSL valide (> 30j restants) | ☐ Oui ☐ Non | `certbot renew` |

---

## 6. Procédure d'Auto-Évaluation

### 6.1 Auto-Évaluation Trimestrielle (2h)

**Responsable** : Administrateur NSI  
**Fréquence** : Tous les 3 mois (avril, juillet, octobre, décembre)

**Étapes** :

1. **Préparation (15 min)**
   ```bash
   cd /srv/korrigo
   python manage.py audit_prepare --quarter=Q1
   ```

2. **Vérification conformité RGPD (30 min)**
   - ✅ Consulter [Checklist RGPD](#41-conformité-générale) (sections A, B, C)
   - ✅ Vérifier délais de réponse demandes RGPD (< 1 mois)
   - ✅ Contrôler registre mis à jour

3. **Vérification sécurité (45 min)**
   - ✅ Exécuter [tests permissions](#52-permissions-et-autorisations)
   - ✅ Analyser [logs sécurité](#53-audit-des-logs-de-sécurité) (30 derniers jours)
   - ✅ Vérifier mises à jour système (`apt update`, `pip list --outdated`)

4. **Documentation (20 min)**
   - ✅ Remplir grille d'auto-évaluation (`audit_QX_YYYY.xlsx`)
   - ✅ Capturer les écarts identifiés
   - ✅ Proposer actions correctives

5. **Reporting (10 min)**
   - ✅ Envoyer rapport au DPO et direction
   - ✅ Planifier actions urgentes (si criticité haute)

**Modèle de rapport** :

```markdown
# Auto-Évaluation Q[X] [ANNÉE]

**Date** : __________
**Auditeur** : Administrateur NSI
**Durée** : 2h

## Résumé
- Conformité RGPD : ☐ Conforme ☐ Écarts mineurs ☐ Écarts majeurs
- Sécurité technique : ☐ Conforme ☐ Écarts mineurs ☐ Écarts majeurs

## Écarts identifiés
1. [Description écart] - Criticité: ☐ Faible ☐ Moyenne ☐ Haute
   - Action corrective : __________
   - Échéance : __________

## Statistiques
- Utilisateurs actifs : ___
- Examens en cours : ___
- Copies traitées (trimestre) : ___
- Incidents sécurité : ___

## Prochaines actions
- [ ] Action 1
- [ ] Action 2
```

---

## 7. Audits Techniques

### 7.1 Audit Infrastructure (Semestriel)

**Périmètre** :
- Configuration serveur (Nginx, PostgreSQL, Redis)
- Permissions système (`/srv/korrigo/media/`, `/var/log/`)
- Sauvegardes (test de restauration)
- Monitoring et alertes

**Commandes de vérification** :

```bash
# 1. Permissions fichiers
find /srv/korrigo/media -type f ! -perm 0640 -ls
find /srv/korrigo/media -type d ! -perm 0750 -ls

# 2. Propriétaires corrects
ls -la /srv/korrigo/ | grep -v "korrigo:korrigo"

# 3. Test restauration backup
cd /backups
tar -tzf backup_latest.tar.gz  # Lister contenu
# Restauration test en environnement isolé

# 4. Vérification espace disque (alerte si > 80%)
df -h | grep -E "/srv|/var"

# 5. Vérification certificat SSL
echo | openssl s_client -connect korrigo.lycee.fr:443 2>/dev/null | openssl x509 -noout -dates

# 6. Test connectivité base de données
psql -U korrigo -d korrigo_db -c "SELECT version();"
```

### 7.2 Audit Base de Données (Semestriel)

**Objectifs** :
- Vérifier l'intégrité des données
- Détecter anomalies (doublons, orphelins)
- Optimiser performances

**Requêtes SQL d'audit** :

```sql
-- 1. Doublons INE (ne doit rien retourner)
SELECT ine, COUNT(*)
FROM students_student
GROUP BY ine
HAVING COUNT(*) > 1;

-- 2. Copies sans examen (données orphelines)
SELECT COUNT(*)
FROM exams_examcopy
WHERE exam_id NOT IN (SELECT id FROM exams_exam);

-- 3. Notes hors plage valide (0-20)
SELECT id, score, exam_id
FROM exams_examcopy
WHERE score < 0 OR score > 20;

-- 4. Élèves sans classe (données incomplètes)
SELECT id, first_name, last_name
FROM students_student
WHERE class_name IS NULL OR class_name = '';

-- 5. Taille base de données
SELECT 
    pg_size_pretty(pg_database_size('korrigo_db')) as db_size,
    pg_size_pretty(pg_total_relation_size('exams_examcopy')) as copies_size;
```

---

## 8. Audits Organisationnels

### 8.1 Formation et Sensibilisation

**Vérifications annuelles** :

| Critère | Preuve | Conforme |
|---------|--------|----------|
| Formation RGPD dispensée aux enseignants | Attestations de formation | ☐ Oui ☐ Non |
| Sensibilisation sécurité (phishing, mots de passe) | Support de présentation | ☐ Oui ☐ Non |
| Charte d'utilisation signée par utilisateurs | Formulaires signés | ☐ Oui ☐ Non |
| Procédures de sécurité accessibles | Intranet/wiki | ☐ Oui ☐ Non |

**Thèmes de formation obligatoires** :
- ✅ Droits des élèves (RGPD)
- ✅ Gestion des mots de passe
- ✅ Détection tentatives de phishing
- ✅ Signalement incidents sécurité
- ✅ Procédure de sauvegarde manuelle

### 8.2 Procédures et Gouvernance

**Audit des procédures** :

| Procédure | Existante | Testée | Dernière MAJ |
|-----------|-----------|--------|--------------|
| Violation de données (data breach) | ☐ Oui ☐ Non | ☐ Oui ☐ Non | __________ |
| Demande d'accès RGPD | ☐ Oui ☐ Non | ☐ Oui ☐ Non | __________ |
| Gestion incident sécurité | ☐ Oui ☐ Non | ☐ Oui ☐ Non | __________ |
| Onboarding nouvel enseignant | ☐ Oui ☐ Non | ☐ Oui ☐ Non | __________ |
| Offboarding utilisateur | ☐ Oui ☐ Non | ☐ Oui ☐ Non | __________ |
| Sauvegarde et restauration | ☐ Oui ☐ Non | ☐ Oui ☐ Non | __________ |

**Test annuel de procédures** :
- 🧪 Simuler data breach (exercice tabletop)
- 🧪 Tester restauration backup (en environnement de test)
- 🧪 Chronométrer réponse à demande RGPD

---

## 9. Reporting et Documentation

### 9.1 Structure du Rapport d'Audit

**Rapport standard** (modèle : `audit_report_template.md`) :

```markdown
# Rapport d'Audit RGPD/Sécurité - Korrigo PMF

**Établissement** : Lycée [NOM]
**Date d'audit** : [DATE]
**Auditeur(s)** : [NOM(S)]
**Type d'audit** : ☐ Interne ☐ Externe ☐ Auto-évaluation
**Périmètre** : ☐ RGPD ☐ Sécurité ☐ Complet

---

## 1. Synthèse Exécutive

**Statut global** : ☐ Conforme ☐ Partiellement conforme ☐ Non conforme

**Résumé en 3 points** :
- [Point clé 1]
- [Point clé 2]
- [Point clé 3]

**Score de conformité** : [X]% (calculé sur checklists)

---

## 2. Résultats Détaillés

### 2.1 Conformité RGPD

| Critère | Résultat | Observations |
|---------|----------|--------------|
| Bases légales | ☐ ✅ ☐ ⚠️ ☐ ❌ | |
| Droits des personnes | ☐ ✅ ☐ ⚠️ ☐ ❌ | |
| Conservation données | ☐ ✅ ☐ ⚠️ ☐ ❌ | |
| Sécurité (Art. 32) | ☐ ✅ ☐ ⚠️ ☐ ❌ | |

### 2.2 Sécurité Technique

| Critère | Résultat | Observations |
|---------|----------|--------------|
| Authentification | ☐ ✅ ☐ ⚠️ ☐ ❌ | |
| Permissions | ☐ ✅ ☐ ⚠️ ☐ ❌ | |
| Journalisation | ☐ ✅ ☐ ⚠️ ☐ ❌ | |
| Vulnérabilités | ☐ ✅ ☐ ⚠️ ☐ ❌ | |

---

## 3. Écarts et Non-Conformités

| ID | Description | Criticité | Risque | Recommandation |
|----|-------------|-----------|--------|----------------|
| NC-01 | [Description] | ☐ Faible ☐ Moyenne ☐ Haute | [Impact] | [Action] |

---

## 4. Plan d'Actions Correctives

| Action | Responsable | Échéance | Statut |
|--------|-------------|----------|--------|
| [Action 1] | [Nom] | [Date] | ☐ À faire ☐ En cours ☐ Fait |

---

## 5. Recommandations

### Court terme (< 1 mois)
- [Recommandation 1]

### Moyen terme (1-6 mois)
- [Recommandation 2]

### Long terme (> 6 mois)
- [Recommandation 3]

---

## 6. Annexes

- [ ] Checklist RGPD complétée
- [ ] Checklist sécurité complétée
- [ ] Logs d'audit analysés
- [ ] Captures d'écran tests
```

### 9.2 Archivage des Rapports

**Organisation des fichiers** :

```
/srv/korrigo/audits/
├── 2026/
│   ├── Q1_auto-evaluation_2026-04-15.pdf
│   ├── Q2_auto-evaluation_2026-07-10.pdf
│   ├── audit_interne_2026-01-20.pdf
│   └── annexes/
│       ├── checklist_rgpd_2026-01-20.xlsx
│       └── logs_export_2026-01-20.csv
├── 2025/
│   └── [archives année précédente]
└── templates/
    ├── audit_report_template.md
    └── checklist_rgpd.xlsx
```

**Durée de conservation** : 5 ans (conformité CNIL)

---

## 10. Gestion des Non-Conformités

### 10.1 Classification des Écarts

| Criticité | Définition | Délai Correction | Escalade |
|-----------|------------|------------------|----------|
| **🔴 Haute** | Violation RGPD, faille sécurité critique | < 7 jours | Direction + DPO |
| **🟠 Moyenne** | Non-conformité partielle, risque modéré | < 30 jours | DPO |
| **🟡 Faible** | Amélioration souhaitable, risque faible | < 90 jours | Admin NSI |

### 10.2 Processus de Traitement

```
┌──────────────────┐
│ Détection écart  │
│  (lors audit)    │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│ Évaluation       │  - Criticité
│  risque          │  - Impact potentiel
└────────┬─────────┘  - Urgence
         │
         v
    ┌────┴────┐
    │ Haute ? │
    └─┬────┬──┘
      │OUI │NON
      v    v
 ┌─────┐ ┌────────────┐
 │Alert│ │Plan action │
 │Dir. │ │ standard   │
 └──┬──┘ └─────┬──────┘
    │          │
    └────┬─────┘
         v
┌──────────────────┐
│ Mise en œuvre    │  - Assignation responsable
│  action          │  - Échéance définie
└────────┬─────────┘  - Suivi régulier
         │
         v
┌──────────────────┐
│ Vérification     │  - Test effectivité
│  effectivité     │  - Contrôle résultat
└────────┬─────────┘
         │
         v
┌──────────────────┐
│ Clôture écart    │  - Documentation
│                  │  - Archivage
└──────────────────┘
```

### 10.3 Registre des Non-Conformités

**Modèle de suivi** (`non_conformites.xlsx`) :

| ID | Date Détection | Description | Criticité | Responsable | Action | Échéance | Statut | Date Clôture |
|----|---------------|-------------|-----------|-------------|--------|----------|--------|--------------|
| NC-2026-01 | 2026-01-15 | Comptes inactifs non désactivés | Moyenne | Admin NSI | Script désactivation | 2026-02-15 | En cours | - |
| NC-2026-02 | 2026-01-18 | Certificat SSL expire dans 20j | Haute | Admin NSI | Renouvellement Certbot | 2026-01-25 | À faire | - |

---

## 11. Préparation aux Audits CNIL

### 11.1 Types de Contrôles CNIL

| Type | Déclencheur | Format | Délai Notification |
|------|-------------|--------|-------------------|
| **Contrôle sur pièces** | Plainte, signalement, programme annuel | Demande documentaire | 15 jours |
| **Contrôle sur place** | Suspicion violation grave | Visite physique (inopinée ou annoncée) | 0-15 jours |
| **Contrôle en ligne** | Site web public | Inspection à distance | Non applicable |

### 11.2 Documents à Préparer

**Checklist pré-audit CNIL** :

✅ **Documentation RGPD obligatoire** :
- [ ] Registre des activités de traitement (à jour)
- [ ] Analyse d'Impact (AIPD) si traitement à risque élevé
- [ ] Politique de protection des données ([POLITIQUE_RGPD.md](POLITIQUE_RGPD.md))
- [ ] DPA avec sous-traitants ([ACCORD_TRAITEMENT_DONNEES.md](../legal/ACCORD_TRAITEMENT_DONNEES.md))
- [ ] Procédures droits des personnes (accès, rectification, effacement)
- [ ] Procédure violation de données

✅ **Preuves techniques** :
- [ ] Inventaire des permissions ([SECURITY_PERMISSIONS_INVENTORY.md](../../SECURITY_PERMISSIONS_INVENTORY.md))
- [ ] Configuration chiffrement (TLS, base de données)
- [ ] Logs d'audit des 6 derniers mois (anonymisés si nécessaire)
- [ ] Attestations de formation utilisateurs
- [ ] Résultats tests de sécurité (pentest, scan vulnérabilités)

✅ **Procédures opérationnelles** :
- [ ] Gestion du cycle de vie des données ([GESTION_DONNEES.md](GESTION_DONNEES.md))
- [ ] Procédure de sauvegarde/restauration
- [ ] Politique de gestion des incidents
- [ ] Charte d'utilisation signée par utilisateurs

### 11.3 Scénarios de Questions CNIL

**Questions fréquentes et réponses préparées** :

| Question CNIL | Document de référence | Réponse type |
|---------------|----------------------|--------------|
| **Quelle est la base légale du traitement ?** | POLITIQUE_RGPD.md § 2.2 | Mission d'intérêt public (Art. 6.1.e) : évaluation pédagogique |
| **Combien de temps conservez-vous les copies ?** | GESTION_DONNEES.md § 6 | 1 an après examen, puis archivage anonymisé |
| **Comment gérez-vous les demandes d'accès ?** | GESTION_DONNEES.md § 9 | Script `export_student_data.py` - délai < 1 mois |
| **Quelles mesures de sécurité pour les mineurs ?** | MANUEL_SECURITE.md § 5 | RBAC strict, logs audit, chiffrement AES-256 |
| **Avez-vous désigné un DPO ?** | POLITIQUE_RGPD.md § 3.1 | Oui (si applicable) - Contact: [email] |
| **Y a-t-il eu des violations de données ?** | Registre incidents | Non / Oui [détails incident + mesures prises] |

### 11.4 Simulation d'Audit Blanc

**Exercice annuel recommandé (décembre)** :

1. **Préparation** : Désigner un auditeur externe (autre lycée, DSI académique)
2. **Exécution** : Audit complet sur 1 journée (checklists RGPD + sécurité)
3. **Débriefing** : Identifier écarts avant audit réel
4. **Actions** : Corriger faiblesses avant fin d'année

**Bénéfices** :
- ✅ Réduire stress équipe
- ✅ Identifier angles morts
- ✅ Tester procédures de réponse
- ✅ Améliorer documentation

---

## 12. Suivi des Recommandations

### 12.1 Tableau de Bord Conformité

**Indicateurs clés (KPI)** :

| Indicateur | Cible | Actuel | Tendance |
|------------|-------|--------|----------|
| **Score conformité RGPD** | ≥ 95% | __% | ☐ ↗️ ☐ → ☐ ↘️ |
| **Délai réponse demande RGPD** | < 1 mois | __ jours | ☐ ↗️ ☐ → ☐ ↘️ |
| **Taux de formation utilisateurs** | 100% | __% | ☐ ↗️ ☐ → ☐ ↘️ |
| **Vulnérabilités critiques non patchées** | 0 | __ | ☐ ↗️ ☐ → ☐ ↘️ |
| **Incidents sécurité (trimestre)** | 0 | __ | ☐ ↗️ ☐ → ☐ ↘️ |
| **Taux de complétion plan d'actions** | 100% | __% | ☐ ↗️ ☐ → ☐ ↘️ |

### 12.2 Revue Trimestrielle Direction

**Ordre du jour type** (1h) :

1. **Résultats audit trimestre écoulé** (15 min)
   - Score conformité
   - Écarts identifiés
   - Incidents sécurité

2. **Avancement plan d'actions** (20 min)
   - Actions clôturées
   - Actions en retard (justification)
   - Nouvelles actions

3. **Indicateurs de risque** (15 min)
   - Évolution menaces (phishing, ransomware)
   - Changements réglementaires (CNIL, RGPD)
   - Ressources nécessaires

4. **Décisions et budget** (10 min)
   - Validation actions correctives
   - Allocation budget sécurité
   - Planification audits

**Participants** : Proviseur, DPO, RSSI, Admin NSI

### 12.3 Amélioration Continue

**Cycle PDCA appliqué aux audits** :

```
┌──────────────────────────────────────────────────────────┐
│                    PLAN (Planifier)                      │
│  - Définir périmètre audit                               │
│  - Préparer checklists                                   │
│  - Planifier calendrier                                  │
└───────────────────────┬──────────────────────────────────┘
                        │
                        v
┌──────────────────────────────────────────────────────────┐
│                     DO (Faire)                           │
│  - Exécuter audits                                       │
│  - Collecter preuves                                     │
│  - Documenter écarts                                     │
└───────────────────────┬──────────────────────────────────┘
                        │
                        v
┌──────────────────────────────────────────────────────────┐
│                   CHECK (Vérifier)                       │
│  - Analyser résultats                                    │
│  - Mesurer KPI conformité                                │
│  - Comparer avec audits précédents                       │
└───────────────────────┬──────────────────────────────────┘
                        │
                        v
┌──────────────────────────────────────────────────────────┐
│                    ACT (Agir)                            │
│  - Implémenter actions correctives                       │
│  - Améliorer procédures d'audit                          │
│  - Former équipe sur lacunes identifiées                 │
└───────────────────────┬──────────────────────────────────┘
                        │
                        └──────────> PLAN (cycle suivant)
```

---

## 📌 Annexes

### Annexe A : Modèle de Rapport d'Auto-Évaluation

Voir section [6.1](#61-auto-évaluation-trimestrielle-2h)

### Annexe B : Scripts d'Audit Automatisés

```bash
# Script complet d'audit trimestriel
# Fichier: /srv/korrigo/scripts/audit_quarterly.sh

#!/bin/bash
REPORT_DIR="/srv/korrigo/audits/$(date +%Y)"
REPORT_FILE="$REPORT_DIR/Q${1}_auto-evaluation_$(date +%Y-%m-%d).txt"

mkdir -p "$REPORT_DIR"

echo "=== Audit Trimestriel Korrigo PMF ===" > "$REPORT_FILE"
echo "Date: $(date)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 1. Utilisateurs actifs
echo "### UTILISATEURS ACTIFS ###" >> "$REPORT_FILE"
python manage.py list_users --active >> "$REPORT_FILE"

# 2. Vérification permissions
echo "### COMPTES ADMIN ###" >> "$REPORT_FILE"
python manage.py list_users --role=admin >> "$REPORT_FILE"

# 3. Logs incidents
echo "### INCIDENTS SÉCURITÉ (30j) ###" >> "$REPORT_FILE"
python manage.py list_security_incidents --days=30 >> "$REPORT_FILE"

# 4. Espace disque
echo "### ESPACE DISQUE ###" >> "$REPORT_FILE"
df -h | grep -E "/srv|/var" >> "$REPORT_FILE"

# 5. Certificat SSL
echo "### CERTIFICAT SSL ###" >> "$REPORT_FILE"
echo | openssl s_client -connect korrigo.lycee.fr:443 2>/dev/null | openssl x509 -noout -dates >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "Rapport sauvegardé: $REPORT_FILE"
```

### Annexe C : Contacts Utiles

| Organisme | Contact | Usage |
|-----------|---------|-------|
| **CNIL** | servicedelaprotectiondesdonnees@cnil.fr<br>01 53 73 22 22 | Conseil RGPD, signalement violation |
| **ANSSI** | https://www.ssi.gouv.fr/signalement | Incident sécurité majeur |
| **DPO Académie** | [email académique] | Support conformité |
| **Éditeur Korrigo** | support@korrigo.fr | Incident technique |

---

## 🔄 Historique des Révisions

| Version | Date | Auteur | Modifications |
|---------|------|--------|---------------|
| 1.0.0 | 30/01/2026 | DPO Établissement | Création initiale |

---

**Document validé par** :  
☐ DPO Établissement  
☐ Proviseur  
☐ RSSI (si applicable)

**Prochaine révision** : Janvier 2027
