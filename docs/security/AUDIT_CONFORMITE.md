# Procédures d'Audit et Conformité
# Plateforme Korrigo PMF

> **Version**: 1.0.0  
> **Date**: 30 Janvier 2026  
> **Public**: DPO, RSSI, Auditeurs, Direction  
> **Fréquence révision**: Annuelle

---

## 📋 Table des Matières

1. [Introduction](#introduction)
2. [Programme d'Audit](#programme-daudit)
3. [Audit RGPD](#audit-rgpd)
4. [Audit Sécurité Technique](#audit-sécurité-technique)
5. [Audit Accès et Permissions](#audit-accès-et-permissions)
6. [Audit Intégrité Données](#audit-intégrité-données)
7. [Audit Conformité Opérationnelle](#audit-conformité-opérationnelle)
8. [Rapports et Suivi](#rapports-et-suivi)
9. [Actions Correctives](#actions-correctives)
10. [Annexes](#annexes)

---

## 1. Introduction

### 1.1 Objet

Ce document définit les procédures d'audit et de contrôle de conformité pour la plateforme Korrigo PMF, couvrant :
- **Conformité RGPD** : Respect protection données personnelles
- **Sécurité technique** : Contrôles systèmes et applicatifs
- **Intégrité données** : Fiabilité notes et annotations
- **Conformité opérationnelle** : Respect procédures établissement

### 1.2 Objectifs

- ✅ **Prévention** : Détecter vulnérabilités avant exploitation
- ✅ **Conformité** : Vérifier respect réglementations (RGPD, CNIL)
- ✅ **Amélioration continue** : Identifier axes optimisation
- ✅ **Responsabilité** : Démontrer accountability RGPD

### 1.3 Périmètre

**Systèmes audités** :
- Application Korrigo PMF (backend + frontend)
- Base de données PostgreSQL
- Infrastructure serveur (Nginx, Docker, OS)
- Procédures organisationnelles (chartes, formations)
- Documentation (registres, politiques)

**Hors périmètre** :
- Sécurité physique locaux (audit établissement)
- Sécurité postes utilisateurs (responsabilité DSI)

---

## 2. Programme d'Audit

### 2.1 Calendrier Annuel

| Audit | Fréquence | Période | Responsable | Durée |
|-------|-----------|---------|-------------|-------|
| **Audit RGPD complet** | Annuel | Septembre | DPO + Auditeur externe | 5 jours |
| **Audit sécurité technique** | Trimestriel | Janv, Avril, Juil, Oct | RSSI/Admin NSI | 2 jours |
| **Audit permissions** | Trimestriel | Mars, Juin, Sept, Déc | Admin NSI | 1 jour |
| **Revue logs sécurité** | Mensuel | 1er de chaque mois | Admin NSI | 2h |
| **Test restauration sauvegarde** | Trimestriel | Fév, Mai, Août, Nov | Admin NSI | 4h |
| **Scan vulnérabilités** | Trimestriel | Janv, Avril, Juil, Oct | RSSI | 1 jour |
| **Audit intégrité données** | Semestriel | Janvier, Juillet | DPO + Admin NSI | 1 jour |

---

### 2.2 Ressources Requises

**Équipe audit interne** :
- **DPO** : Conformité RGPD, droits personnes concernées
- **RSSI/Admin NSI** : Sécurité technique, logs, permissions
- **Proviseur** : Validation résultats, approbation actions correctives

**Outils** :
- Scripts audit automatisés (`audit_permissions.py`, `check_data_retention.py`)
- OWASP ZAP (scan vulnérabilités web)
- PostgreSQL audit queries
- Checklist papier (conformité organisationnelle)

**Audit externe** (optionnel, annuel) :
- Prestataire PASSI (Prestataire d'Audit de la Sécurité des SI)
- Pentest (test intrusion)
- Revue code sécurité

---

## 3. Audit RGPD

### 3.1 Objectifs

- Vérifier conformité aux 6 principes RGPD (Art. 5)
- Valider exercice droits personnes concernées
- Contrôler durées de conservation
- Vérifier registre des traitements à jour

### 3.2 Checklist Audit RGPD

**A. Registre des Traitements (Art. 30 RGPD)**

| Critère | Conforme | Non-Conforme | Observations |
|---------|----------|--------------|--------------|
| Registre existe et accessible | ☐ | ☐ | |
| Tous traitements documentés | ☐ | ☐ | |
| Finalités clairement définies | ☐ | ☐ | |
| Base légale identifiée | ☐ | ☐ | |
| Destinataires listés | ☐ | ☐ | |
| Durées conservation spécifiées | ☐ | ☐ | |
| Mesures sécurité décrites | ☐ | ☐ | |
| Mise à jour < 12 mois | ☐ | ☐ | Date dernière MAJ : ______ |

**Emplacement registre** : `docs/security/REGISTRE_TRAITEMENTS_RGPD.xlsx`

---

**B. Droits des Personnes Concernées (Art. 15-22 RGPD)**

| Droit | Procédure Existe | Délai Respecté | Testée |
|-------|-----------------|----------------|--------|
| Droit d'accès (Art. 15) | ☐ | ☐ | ☐ |
| Droit de rectification (Art. 16) | ☐ | ☐ | ☐ |
| Droit à l'effacement (Art. 17) | ☐ | ☐ | ☐ |
| Droit à la portabilité (Art. 20) | ☐ | ☐ | ☐ |
| Droit d'opposition (Art. 21) | ☐ | ☐ | ☐ |

**Test** :
```bash
# Simuler demande d'accès
python manage.py export_student_data --ine TEST_INE --format json

# Vérifier délai < 1 mois
# Vérifier exhaustivité données fournies
```

---

**C. Durées de Conservation (Art. 5.1.e RGPD)**

| Type de données | Durée légale | Durée appliquée | Conforme |
|----------------|--------------|-----------------|----------|
| Données élèves | 1 an après fin scolarité | ______ | ☐ |
| Copies PDF | 1 an après examen | ______ | ☐ |
| Notes/annotations | 1 an après examen | ______ | ☐ |
| Logs audit | 6 mois | ______ | ☐ |
| Sauvegardes | 30j quotidiennes + 6m hebdo | ______ | ☐ |

**Vérification automatisée** :
```python
# Script audit rétention
from datetime import datetime, timedelta

# Vérifier copies > 1 an non supprimées
threshold = datetime.now() - timedelta(days=365)
old_exams = Exam.objects.filter(date__lt=threshold)
old_copies = Copy.objects.filter(exam__in=old_exams)

if old_copies.exists():
    print(f"⚠️ ALERTE: {old_copies.count()} copies dépassent durée conservation")
    for copy in old_copies[:10]:
        print(f"  - Copie {copy.anonymous_id}, examen {copy.exam.date}")
else:
    print("✅ Conformité conservation : Aucune copie expirée")
```

---

**D. Mesures Sécurité (Art. 32 RGPD)**

| Mesure | Implémentée | Testée | Notes |
|--------|-------------|--------|-------|
| Chiffrement en transit (HTTPS) | ☐ | ☐ | Vérifier certificat SSL valide |
| Chiffrement au repos (DB) | ☐ | ☐ | PostgreSQL SSL mode |
| Authentification forte | ☐ | ☐ | Rate limiting actif |
| Contrôle d'accès RBAC | ☐ | ☐ | Permissions testées |
| Audit trail complet | ☐ | ☐ | Logs GradingEvent |
| Sauvegardes chiffrées | ☐ | ☐ | GPG encryption |
| Anonymisation copies | ☐ | ☐ | Numéro anonymat unique |

**Test SSL** :
```bash
# Vérifier HTTPS et HSTS
curl -I https://korrigo.lycee-exemple.fr | grep -i "strict-transport-security"
# Attendu: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

---

**E. Violations de Données (Art. 33-34 RGPD)**

| Critère | Conforme | Notes |
|---------|----------|-------|
| Procédure notification CNIL existe | ☐ | Délai 72h |
| Registre violations tenu à jour | ☐ | Emplacement : ______ |
| Contact CNIL/DPO accessible 24/7 | ☐ | |
| Procédure testée (exercice) | ☐ | Date dernier test : ______ |

---

### 3.3 Analyse d'Impact (AIPD)

**Vérifications** :

| Critère | Statut | Date Réalisation |
|---------|--------|------------------|
| AIPD réalisée | ☐ Oui / ☐ Non | ____________ |
| Risques identifiés documentés | ☐ | |
| Mesures atténuation implémentées | ☐ | |
| Niveau risque résiduel acceptable | ☐ | |
| Consultation DPO effectuée | ☐ | |
| Révision annuelle planifiée | ☐ | Prochaine : ______ |

**Référence** : `docs/security/POLITIQUE_RGPD.md § 11`

---

### 3.4 Score Conformité RGPD

**Calcul** :
```
Score = (Critères conformes / Total critères) × 100

Niveaux :
- 90-100% : Excellent (conformité complète)
- 75-89%  : Satisfaisant (améliorations mineures)
- 50-74%  : Insuffisant (actions correctives requises)
- < 50%   : Critique (mise en conformité urgente)
```

**Résultat audit** : _______ % (Date : __________)

---

## 4. Audit Sécurité Technique

### 4.1 Checklist Infrastructure

**A. Serveur et OS**

| Critère | Conforme | Observations |
|---------|----------|--------------|
| OS à jour (patches sécurité) | ☐ | Version : ______ |
| Firewall actif et configuré | ☐ | Règles iptables vérifiées |
| SSH désactivé ou sécurisé (clé, pas mdp) | ☐ | |
| Services inutiles désactivés | ☐ | Liste services actifs : ______ |
| Logs système activés | ☐ | rsyslog/journald |
| Antivirus/EDR installé | ☐ | Nom produit : ______ |

**Commandes vérification** :
```bash
# Version OS et patches
cat /etc/os-release
apt list --upgradable

# Firewall
iptables -L -n

# Services actifs
systemctl list-units --type=service --state=running

# Logs système
journalctl -xe --since "1 hour ago"
```

---

**B. Application Django**

| Critère | Conforme | Observations |
|---------|----------|--------------|
| Django version stable et supportée | ☐ | Version : ______ |
| `DEBUG=False` en production | ☐ | Vérifier .env |
| `SECRET_KEY` unique et sécurisée | ☐ | Pas de valeur par défaut |
| `ALLOWED_HOSTS` configuré (pas *) | ☐ | Valeur : ______ |
| HTTPS obligatoire (`SSL_ENABLED=True`) | ☐ | |
| HSTS activé | ☐ | max-age=31536000 |
| CSRF protection activée | ☐ | |
| CSP configuré | ☐ | Vérifier unsafe-inline |
| Rate limiting activé | ☐ | RATELIMIT_ENABLE=true |

**Commande vérification** :
```bash
# Check déploiement Django
python manage.py check --deploy

# Attendu: System check identified no issues (0 silenced).
```

---

**C. Base de Données PostgreSQL**

| Critère | Conforme | Observations |
|---------|----------|--------------|
| PostgreSQL version supportée | ☐ | Version : ______ |
| Connexions SSL obligatoires | ☐ | sslmode=require |
| Mot de passe fort | ☐ | Rotation 6 mois |
| Accès réseau restreint | ☐ | Firewall + pg_hba.conf |
| Logs activés | ☐ | log_connections, log_statement |
| Sauvegardes quotidiennes | ☐ | Dernière sauvegarde : ______ |

**Vérification SSL** :
```bash
psql "host=localhost dbname=korrigo_db user=korrigo sslmode=require"
# Doit réussir uniquement si SSL configuré
```

---

**D. Nginx (Reverse Proxy)**

| Critère | Conforme | Observations |
|---------|----------|--------------|
| Nginx version stable | ☐ | Version : ______ |
| Certificat SSL valide | ☐ | Expiration : ______ |
| TLS 1.2+ uniquement | ☐ | Pas SSLv3, TLS 1.0/1.1 |
| Ciphers sécurisés | ☐ | ECDHE prioritaire |
| Headers sécurité configurés | ☐ | HSTS, X-Frame-Options, CSP |
| Logs accès/erreur actifs | ☐ | Rotation configurée |

**Test SSL Labs** :
```
URL : https://www.ssllabs.com/ssltest/analyze.html?d=korrigo.lycee-exemple.fr
Objectif : Grade A ou A+
```

---

### 4.2 Scan Vulnérabilités

**A. OWASP ZAP (Web Application Scan)**

**Procédure** :
```bash
# Scan baseline (rapide, 10 min)
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://korrigo.lycee-exemple.fr \
  -r zap_baseline_report.html

# Analyser rapport
# Critères : 0 vulnérabilités High/Critical
```

**Vulnérabilités OWASP Top 10 à vérifier** :
- [ ] A01 - Broken Access Control
- [ ] A02 - Cryptographic Failures
- [ ] A03 - Injection (SQL, XSS, CSRF)
- [ ] A04 - Insecure Design
- [ ] A05 - Security Misconfiguration
- [ ] A06 - Vulnerable Components
- [ ] A07 - Authentication Failures
- [ ] A08 - Software/Data Integrity
- [ ] A09 - Logging Failures
- [ ] A10 - Server-Side Request Forgery

---

**B. Scan Dépendances (Python)**

```bash
# Safety (CVE Python packages)
pip install safety
safety check --json > safety_report.json

# Vérifier 0 vulnérabilités critiques/élevées
cat safety_report.json | jq '.vulnerabilities[] | select(.severity == "high" or .severity == "critical")'
```

**Résultat attendu** : `[]` (aucune vulnérabilité)

---

**C. Scan Dépendances (JavaScript/npm)**

```bash
cd frontend
npm audit --json > npm_audit.json

# Vérifier résumé
npm audit
# Attendu: found 0 vulnerabilities
```

---

### 4.3 Test Intrusion (Pentest)

**Fréquence** : Annuel (ou avant mise en production majeure)

**Prestataire** : Certification PASSI (liste ANSSI)

**Scope** :
- [ ] Authentification (brute force, session hijacking)
- [ ] Autorisation (escalade privilèges, IDOR)
- [ ] Injection (SQL, XSS, CSRF)
- [ ] Configuration (headers, SSL, cookies)
- [ ] Logique métier (bypass verrou copies, modification notes)

**Livrables** :
- Rapport exécutif (synthèse direction)
- Rapport technique (détail vulnérabilités)
- Plan actions correctives

**Suivi** :
- Correction vulnérabilités P0/P1 sous 30 jours
- Retest après corrections

---

## 5. Audit Accès et Permissions

### 5.1 Revue Comptes Utilisateurs

**Procédure trimestrielle** :

```bash
# Exécuter script audit
python manage.py audit_permissions > audit_Q1_2026.txt
```

**Critères vérifiés** :

| Critère | Conforme | Actions |
|---------|----------|---------|
| Aucun compte inactif > 90 jours | ☐ | Désactiver : ______ |
| Nombre superusers ≤ 3 | ☐ | Justifier excédents : ______ |
| Tous comptes ont email valide | ☐ | Mettre à jour : ______ |
| Pas de comptes test/demo actifs | ☐ | Supprimer : ______ |
| Groupes Django cohérents | ☐ | Corriger : ______ |

---

### 5.2 Test Permissions

**Scénarios de test** :

**Test 1 : Enseignant ne peut pas accéder admin**
```bash
# Se connecter comme teacher1
curl -X POST https://korrigo.lycee-exemple.fr/api/login/ \
  -d '{"username": "teacher1", "password": "..."}' \
  -c cookies.txt

# Tenter accès admin
curl -b cookies.txt https://korrigo.lycee-exemple.fr/api/users/
# Attendu: 403 Forbidden
```

**Test 2 : Élève ne peut voir que ses copies**
```python
# Se connecter comme student
response = client.post('/api/students/login/', {
    'ine': '1234567890A',
    'last_name': 'DUPONT'
})

# Lister copies
response = client.get('/api/students/copies/')
copies = response.json()

# Vérifier : toutes copies ont student_id = élève connecté
for copy in copies:
    assert copy['student']['ine'] == '1234567890A'
```

**Test 3 : Annotations modifiables uniquement par créateur**
```python
# Teacher1 crée annotation
teacher1_client.post('/api/grading/annotations/', {...})

# Teacher2 tente modifier
response = teacher2_client.patch('/api/grading/annotations/{id}/', {...})
# Attendu: 403 Forbidden
```

---

### 5.3 Revue Logs d'Accès

**Procédure mensuelle** :

```bash
# Analyser logs Nginx (accès suspects)
cat /var/log/nginx/korrigo_access.log | awk '{print $1}' | sort | uniq -c | sort -nr | head -20
# Vérifier IPs anormalement actives

# Analyser logs Django (erreurs 403/401)
grep "403\|401" /var/log/korrigo/django.log | tail -100

# GradingEvent : Téléchargements PDF
psql -U korrigo -d korrigo_db -c "
  SELECT action, COUNT(*) 
  FROM grading_gradingevent 
  WHERE action = 'EXPORT' AND timestamp > NOW() - INTERVAL '30 days'
  GROUP BY action;
"
```

**Critères alerte** :
- ⚠️ Même IP > 100 requêtes/min (potentiel DoS)
- ⚠️ Nombreux 403 d'un utilisateur (tentative accès non autorisé)
- ⚠️ Téléchargements PDF anormaux (exfiltration ?)

---

## 6. Audit Intégrité Données

### 6.1 Cohérence Base de Données

**Vérifications** :

```sql
-- 1. Copies sans examen (orphelins)
SELECT COUNT(*) FROM exams_copy WHERE exam_id NOT IN (SELECT id FROM exams_exam);
-- Attendu: 0

-- 2. Annotations sans copie (cascade non respecté)
SELECT COUNT(*) FROM grading_annotation WHERE copy_id NOT IN (SELECT id FROM exams_copy);
-- Attendu: 0

-- 3. Élèves sans INE (contrainte unique)
SELECT COUNT(*) FROM students_student WHERE ine IS NULL OR ine = '';
-- Attendu: 0

-- 4. Copies identifiées sans élève (incohérence)
SELECT COUNT(*) FROM exams_copy WHERE is_identified = TRUE AND student_id IS NULL;
-- Attendu: 0

-- 5. Verrous expirés non supprimés
SELECT COUNT(*) FROM grading_copylock WHERE expires_at < NOW();
-- Attendu: 0 (nettoyage automatique)
```

---

### 6.2 Intégrité Fichiers

**Vérification fichiers référencés existent** :

```python
# Script vérification
missing_files = []

for copy in Copy.objects.all():
    if copy.pdf_source and not os.path.exists(copy.pdf_source.path):
        missing_files.append(f"Copy {copy.id}: pdf_source manquant")
    
    if copy.final_pdf and not os.path.exists(copy.final_pdf.path):
        missing_files.append(f"Copy {copy.id}: final_pdf manquant")

if missing_files:
    print(f"⚠️ ALERTE: {len(missing_files)} fichiers manquants")
    for msg in missing_files[:10]:
        print(f"  - {msg}")
else:
    print("✅ Intégrité fichiers : Tous fichiers présents")
```

---

### 6.3 Calcul Scores (Validation)

**Test échantillon** :

```python
# Vérifier cohérence annotations ↔ score final
import random

copies_sample = random.sample(list(Copy.objects.filter(status='GRADED')), 10)

for copy in copies_sample:
    # Recalculer score depuis annotations
    annotations = Annotation.objects.filter(copy=copy)
    calculated_score = sum(a.score_delta for a in annotations if a.score_delta)
    
    # Comparer avec score enregistré
    if abs(calculated_score - copy.score) > 0.01:
        print(f"⚠️ Incohérence copie {copy.anonymous_id}: "
              f"Score DB={copy.score}, Calculé={calculated_score}")
```

---

## 7. Audit Conformité Opérationnelle

### 7.1 Procédures Documentées

| Procédure | Document Existe | À Jour (<12 mois) | Testée |
|-----------|----------------|-------------------|--------|
| Import élèves Pronote | ☐ | ☐ | ☐ |
| Upload et traitement copies | ☐ | ☐ | ☐ |
| Identification copies (Video-Coding) | ☐ | ☐ | ☐ |
| Correction numérique | ☐ | ☐ | ☐ |
| Export notes Pronote | ☐ | ☐ | ☐ |
| Gestion utilisateurs | ☐ | ☐ | ☐ |
| Sauvegardes et restauration | ☐ | ☐ | ☐ |
| Réponse incident sécurité | ☐ | ☐ | ☐ |

**Référence** : `docs/admin/PROCEDURES_OPERATIONNELLES.md`

---

### 7.2 Formations Utilisateurs

| Formation | Public | Fréquence | Dernière Session | Taux Participation |
|-----------|--------|-----------|-----------------|-------------------|
| RGPD et confidentialité | Tous | Annuelle | __________ | ______% |
| Utilisation Korrigo (enseignants) | Teachers | Rentrée | __________ | ______% |
| Administration technique | Admin NSI | Annuelle | __________ | ______% |
| Sécurité et bonnes pratiques | Tous | Annuelle | __________ | ______% |

**Objectif** : Taux participation > 90%

---

### 7.3 Chartes et Consentements

| Document | Signataires | Taux Signature |
|----------|------------|----------------|
| Charte utilisation enseignants | ______ / ______ | ______% |
| Charte utilisation admin | ______ / ______ | ______% |
| Consentement portail élève (parents) | ______ / ______ | ______% |

**Stockage** : Armoire sécurisée secrétariat (version papier) + scan chiffré

---

## 8. Rapports et Suivi

### 8.1 Rapport d'Audit Type

**Structure** :

```
1. RÉSUMÉ EXÉCUTIF
   - Périmètre audit
   - Date et auditeurs
   - Synthèse résultats (score global)
   - Recommandations principales

2. MÉTHODOLOGIE
   - Référentiels utilisés (RGPD, OWASP, ANSSI)
   - Outils (scripts, scans, tests manuels)
   - Échantillons testés

3. RÉSULTATS DÉTAILLÉS
   - Conformité RGPD : ____%
   - Sécurité technique : ____%
   - Permissions : ____%
   - Intégrité données : ____%
   - Conformité opérationnelle : ____%

4. CONSTATS ET ÉCARTS
   - Liste non-conformités (criticité P0-P3)
   - Preuves (captures écran, logs)

5. RECOMMANDATIONS
   - Actions correctives prioritaires
   - Délais proposés
   - Responsables désignés

6. ANNEXES
   - Checklist complète
   - Résultats scans (ZAP, safety)
   - Logs pertinents
```

---

### 8.2 Score Global de Conformité

**Calcul** :

```
Score Global = Moyenne pondérée :
- Conformité RGPD : 40%
- Sécurité technique : 30%
- Permissions : 15%
- Intégrité données : 10%
- Conformité opérationnelle : 5%

Exemple :
RGPD = 95% → 95 × 0.40 = 38
Sécurité = 85% → 85 × 0.30 = 25.5
Permissions = 90% → 90 × 0.15 = 13.5
Intégrité = 100% → 100 × 0.10 = 10
Opérationnel = 80% → 80 × 0.05 = 4
------------------------------------------
Score Global = 91%
```

**Interprétation** :
- **90-100%** : ✅ Excellent (conformité complète)
- **75-89%** : ⚠️ Satisfaisant (améliorations mineures)
- **50-74%** : ⚠️ Insuffisant (actions correctives)
- **< 50%** : ❌ Critique (mise en conformité urgente)

---

### 8.3 Tableau de Bord

**Indicateurs clés (KPI)** :

| Indicateur | Cible | Actuel | Tendance |
|------------|-------|--------|----------|
| Score conformité RGPD | > 90% | ______% | ↗ / → / ↘ |
| Vulnérabilités critiques | 0 | ______ | ↗ / → / ↘ |
| Comptes inactifs > 90j | 0 | ______ | ↗ / → / ↘ |
| Temps restauration sauvegarde | < 4h | ______ | ↗ / → / ↘ |
| Formations utilisateurs (taux) | > 90% | ______% | ↗ / → / ↘ |
| Incidents sécurité (nb/an) | 0 | ______ | ↗ / → / ↘ |

**Mise à jour** : Trimestrielle

---

## 9. Actions Correctives

### 9.1 Classification Priorités

| Niveau | Criticité | Délai Correction | Validation |
|--------|-----------|------------------|------------|
| **P0** | Critique (violation RGPD, faille sécurité majeure) | 7 jours | DPO + RSSI |
| **P1** | Élevée (non-conformité RGPD, vulnérabilité haute) | 30 jours | DPO |
| **P2** | Moyenne (amélioration sécurité, procédure manquante) | 90 jours | Admin NSI |
| **P3** | Faible (optimisation, documentation) | 180 jours | Admin NSI |

---

### 9.2 Plan d'Action Type

**Exemple : Non-conformité détectée**

```
NON-CONFORMITÉ N°2026-001
--------------------------
Catégorie : RGPD - Durée conservation
Criticité : P1 (Élevée)
Description : 245 copies d'examens datant de > 1 an non supprimées

ANALYSE CAUSE RACINE :
- Tâche Celery purge_old_copies désactivée depuis 3 mois
- Absence de monitoring purge automatique

ACTIONS CORRECTIVES :
1. Réactiver tâche Celery immédiatement
   Responsable : Admin NSI
   Délai : J+1

2. Exécuter purge manuelle des 245 copies
   Responsable : Admin NSI
   Délai : J+7

3. Mettre en place alerte si tâche échoue
   Responsable : Admin NSI
   Délai : J+15

4. Documenter procédure surveillance purge
   Responsable : DPO
   Délai : J+30

SUIVI :
- 10/02/2026 : Tâche réactivée ✅
- 17/02/2026 : Purge manuelle effectuée ✅
- 25/02/2026 : Alerte configurée ✅
- 12/03/2026 : Documentation mise à jour ✅

CLÔTURE : 12/03/2026
Validé par : DPO
```

---

### 9.3 Registre Actions Correctives

**Format** (feuille de calcul) :

| ID | Date Détection | Catégorie | Criticité | Description | Responsable | Délai | Statut | Date Clôture |
|----|---------------|-----------|-----------|-------------|-------------|-------|--------|--------------|
| 2026-001 | 10/02/2026 | RGPD | P1 | Copies > 1 an | Admin NSI | 12/03/2026 | Fermé | 12/03/2026 |
| 2026-002 | 15/03/2026 | Sécurité | P2 | Mot de passe faible | RSSI | 14/06/2026 | En cours | - |

---

## 10. Annexes

### Annexe A : Outils Audit

**Scripts Django** :
```bash
# Audit permissions
python manage.py audit_permissions

# Vérification conservation
python manage.py check_data_retention

# Export données RGPD
python manage.py export_student_data --ine <INE>

# Vérification déploiement
python manage.py check --deploy
```

**Outils externes** :
- **OWASP ZAP** : https://www.zaproxy.org/
- **Safety** : https://pyup.io/safety/
- **SSL Labs** : https://www.ssllabs.com/ssltest/
- **Mozilla Observatory** : https://observatory.mozilla.org/

---

### Annexe B : Checklist Audit Rapide (Mensuel)

**15 minutes, 1er de chaque mois** :

```
☐ Vérifier logs sécurité (403, 401, erreurs)
☐ Scanner vulnérabilités (safety check)
☐ Vérifier espace disque (> 20% libre)
☐ Vérifier dernière sauvegarde (< 24h)
☐ Tester restauration (échantillon)
☐ Comptes inactifs > 90j (désactiver)
☐ Certificat SSL (expiration > 30j)
☐ Mise à jour OS/Django disponibles ?
☐ Logs purge automatique (vérifier exécution)
☐ Incidents mois précédent (suivi actions)
```

---

### Annexe C : Modèle Rapport Audit

**Télécharger** : `docs/security/templates/RAPPORT_AUDIT_TEMPLATE.docx`

**Sections** :
1. Page de garde (date, auditeur, périmètre)
2. Résumé exécutif (1 page)
3. Méthodologie (1 page)
4. Résultats (5-10 pages)
5. Recommandations (2-5 pages)
6. Annexes (preuves, logs)

---

### Annexe D : Contacts

| Rôle | Contact | Email |
|------|---------|-------|
| **DPO** | M./Mme DPO | dpo@lycee-exemple.fr |
| **RSSI Académie** | M./Mme RSSI | rssi@ac-exemple.fr |
| **Admin NSI** | M./Mme Admin | admin.nsi@lycee-exemple.fr |
| **CNIL** | Commission | https://www.cnil.fr/plainte |
| **CERT-FR** | ANSSI | cert-fr.cossi@ssi.gouv.fr |

---

### Annexe E : Calendrier Audits 2026

| Mois | Audit | Responsable | Statut |
|------|-------|-------------|--------|
| Janvier | Scan vulnérabilités | RSSI | ☐ |
| Février | Test restauration | Admin NSI | ☐ |
| Mars | Audit permissions | Admin NSI | ☐ |
| Avril | Scan vulnérabilités | RSSI | ☐ |
| Mai | Test restauration | Admin NSI | ☐ |
| Juin | Audit permissions | Admin NSI | ☐ |
| Juillet | Scan vulnérabilités + Intégrité données | RSSI + DPO | ☐ |
| Août | Test restauration | Admin NSI | ☐ |
| Septembre | **AUDIT RGPD COMPLET** | DPO + Externe | ☐ |
| Octobre | Scan vulnérabilités | RSSI | ☐ |
| Novembre | Test restauration | Admin NSI | ☐ |
| Décembre | Audit permissions + Bilan annuel | Admin NSI + DPO | ☐ |

---

**Document approuvé par** :
- DPO : _______________
- RSSI : _______________
- Proviseur : _______________
- Date : 30 Janvier 2026

**Prochaine révision** : Janvier 2027
