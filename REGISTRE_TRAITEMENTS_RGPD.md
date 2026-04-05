# REGISTRE DES TRAITEMENTS — KORRIGO
## Article 30 du RGPD — Lycée Pierre Mendès France, Tunis

### Responsable du traitement
- **Organisme** : Lycée Pierre Mendès France, Tunis (réseau AEFE/ERT)
- **Responsable** : Le Proviseur du Lycée PMF
- **Contact DPD** : À désigner par l'établissement

---

### Traitement 1 : Correction dématérialisée des examens

| Champ | Détail |
|-------|--------|
| **Finalité** | Correction dématérialisée des copies (BAC Blanc, DNB Blanc, EAM) |
| **Base légale** | Mission de service public (Art. 6.1.e RGPD) |
| **Catégories de personnes** | Élèves (mineurs), enseignants correcteurs |
| **Données élèves** | Nom, prénom, date de naissance, email, classe, groupe |
| **Données correcteurs** | Nom, prénom, email professionnel |
| **Données de correction** | Notes par question, annotations, remarques, appréciations |
| **Mesures d'anonymisation** | Copies présentées aux correcteurs sans identité (anonymous_id UUID). Serializer dédié supprimant student, student_name, header_image. |
| **Durée de conservation** | Année scolaire en cours + 1 an. Purge manuelle via commande `purge_old_exam_data`. |
| **Destinataires** | Correcteurs (copies anonymisées), administration (résultats nominatifs), élèves (leurs propres résultats uniquement) |
| **Transferts hors UE** | Aucun |
| **Sous-traitant hébergement** | Hetzner Online GmbH, Falkenstein, Allemagne |
| **Mesures de sécurité** | HTTPS TLS 1.2+, authentification mot de passe 12 car. min, isolation des rôles, rate limiting, media protégé par authentification |

### Traitement 2 : Sauvegarde automatisée

| Champ | Détail |
|-------|--------|
| **Finalité** | Continuité de service et restauration en cas d'incident |
| **Base légale** | Obligation de sécurité (Art. 32 RGPD) |
| **Données** | Dump DB (données complètes), export JSON (pseudonymisé), fichiers media |
| **Durée** | 24 heures glissantes sur StorageBox |
| **Chiffrement** | SSH en transit. Fichiers en clair au repos (risque accepté, accès par clé SSH uniquement) |
| **Localisation** | Hetzner StorageBox, Falkenstein, Allemagne |

### Traitement 3 : Journalisation des accès

| Champ | Détail |
|-------|--------|
| **Finalité** | Traçabilité (Art. 5.2 RGPD) |
| **Données** | ID utilisateur, action, horodatage, adresse IP |
| **Durée** | 365 jours (purge automatique quotidienne à 3h) |

---
*Créé le 2026-04-03. À réviser annuellement.*
