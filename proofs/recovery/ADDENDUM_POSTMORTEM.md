# ADDENDUM AU RAPPORT POST-MORTEM
## Phase 4 — Récupération via localStorage des navigateurs (27 février 2026)

### 4.1 Stratégie de récupération

Suite à l'échec de la récupération forensique côté serveur, une quatrième phase a été lancée exploitant une particularité de l'application Korrigo : le frontend React stocke les scores en cours de saisie dans le `localStorage` du navigateur de chaque correcteur, sous des clés au format `korrigo_scores_{copy_uuid}`.

Un outil de récupération dédié a été développé et déployé :
- **recovery.html** + **recovery.js** + **recovery.css** — hébergés sur `https://korrigo.labomaths.tn/recovery.html`
- Conforme CSP (pas de JS/CSS inline) — tous les fichiers servis depuis la même origine
- Le script V3 scanne : localStorage, sessionStorage, cookies, IndexedDB, Cache Storage, Service Workers, Performance API, OPFS
- Les correcteurs n'avaient qu'à ouvrir la page dans leur navigateur habituel et copier le JSON affiché

### 4.2 Pipeline de mapping des UUIDs

Les clés localStorage utilisent les anciens UUIDs de copies (pré-crash). Le pipeline de réconciliation :

1. **Ancien UUID** (localStorage) → **anonymous_id** (via le dump `exams_copy.json` du 20 février)
2. **anonymous_id** → **nouveau UUID** de la Copy dans la base restaurée (correspondance par `anonymous_id`)

Ce mapping a été vérifié systématiquement pour chaque correcteur avant import.

### 4.3 Résultats par correcteur

#### 4.3.1 Patrick DUPONT (patrick.dupont@ert.tn) — BB_J1

- **Source** : Firefox localStorage, 26 clés `korrigo_scores_*`
- **Mapping** : 26/26 UUIDs mappés avec succès
- **Contenu** : Exercices 1 et 2 uniquement (15 questions par copie sur 33)
- **Limitation** : Patrick n'avait pas encore saisi les exercices 3 et 4 dans Korrigo au moment du crash
- **Import** : 26 objets Score créés (aucun n'existait en DB)
- **Plage de notes** : 2.50/20 à 9.95/20 (sur Ex1+Ex2 seulement, /10 ramenés sur /20)
- **Script** : `import_patrick_scores.py`
- **Statut** : **26/26 importés** — scores partiels, à compléter avec Ex3+Ex4

#### 4.3.2 Sami BEN TIBA (sami.bentiba) — BB_J2

- **Source** : localStorage (navigateur non précisé), 26 clés `korrigo_scores_*`
- **Contenu** : 33 questions complètes par copie (les 4 exercices)
- **Import** : Les 26 scores existaient déjà en DB (restaurés depuis le dump du 20 février) — scores identiques
- **Statut** : **26/26 validés** — le localStorage confirme l'intégrité des données du dump

#### 4.3.3 Selima KLIBI (selima.klibi@ert.tn) — BB_J1

- **Source** : Chrome localStorage, 33 clés `korrigo_scores_*` (dont 2 doublons post-réimport et 1 entrée nulle, exclues)
- **Mapping** : 27/27 UUIDs valides mappés avec succès
- **Contenu** : 33 questions complètes par copie
- **Comparaison avec la DB** :
  - 13 copies : scores identiques au dump → **SKIP**
  - 14 copies : aucun score en DB (copies perdues) → **CREATE**
- **Import** : 14 objets Score créés le 27 février 2026
- **Plage de notes** : 1.45/20 à 18.90/20 — Moyenne 13.84/20
- **Script** : `import_selima_scores.py` (lit `selima_scores.json` + `selima_uuid_mapping.json`)
- **Commit** : fb4410a
- **Statut** : **27/27 complets** — 14 récupérés + 13 déjà en DB

#### 4.3.4 Philippe CARR (philippe.carr@ert.tn) — BB_J1

- **Source** : Chrome localStorage, 27 clés `korrigo_scores_*`
- **Mapping** : 27/27 UUIDs mappés avec succès
- **Contenu** : 33 questions complètes par copie
- **Comparaison avec la DB** : Les 27 totaux du localStorage correspondent exactement aux 27 scores en DB
- **Statut** : **27/27 validés** — le localStorage confirme l'intégrité à 100% des données restaurées depuis le dump

### 4.4 Clarification : correcteurs sans perte de données

Contrairement à l'analyse initiale du rapport post-mortem (section 4), les copies sans score pour les correcteurs suivants **ne représentent pas des données perdues** : ces correcteurs n'avaient tout simplement **pas encore commencé ou terminé la correction** de ces copies au moment du crash.

| Correcteur | Copies sans score | Raison | Perte réelle |
|---|---|---|---|
| edouard.rousseau | 18 | Corrections non encore effectuées | **0** |
| laroussi.laroussi | 23 | Corrections non encore effectuées | **0** |
| alaeddine.benrhouma | 18 | Corrections non encore effectuées | **0** |
| **Total** | **59** | | **0** |

Les données actuellement en base (8 scores Edouard, 3 scores Laroussi, 8 scores Alaeddine) correspondent exactement à l'état réel de l'avancement des corrections avant l'incident.

### 4.5 Bilan actualisé de la récupération

| Source | Scores récupérés | Détail |
|---|---|---|
| Dump PostgreSQL 20 février | 105 | 42 GRADED + 63 avec scores non finalisés |
| localStorage Patrick DUPONT | 26 | Ex1+Ex2 seulement (15q/33) |
| localStorage Selima KLIBI | 14 | Complets (33q) — les 13 autres déjà dans dump |
| localStorage Sami BEN TIBA | 0 (validation) | 26/26 identiques au dump |
| localStorage Philippe CARR | 0 (validation) | 27/27 identiques au dump |
| Corrections en cours (post-reconstitution) | 5 | Copies finalisées après remise en service |
| **Total unique en DB** | **150** | **sur 209 copies (72%)** |

**IMPORTANT** : Les 59 copies sans score ne sont **pas des données perdues**. Les correcteurs concernés (Edouard, Laroussi, Alaeddine) n'avaient pas encore corrigé ces copies avant l'incident. L'état actuel de la base correspond fidèlement à la réalité de l'avancement des corrections.

**Bilan réel des pertes : zéro copie perdue.** Toutes les corrections effectuées ont été récupérées (dump + localStorage).

---

## Mise à jour de la section 1.4 — Chronologie complète

Ajouter les lignes suivantes à la chronologie :

| Date | Événement |
|---|---|
| 27 février AM | Phase 4 : Déploiement outil récupération localStorage (`recovery.html`) |
| 27 février AM | Import Patrick DUPONT : 26/26 scores Ex1+Ex2 depuis Firefox localStorage |
| 27 février PM | Import Selima KLIBI : 14/14 scores complets depuis Chrome localStorage |
| 27 février PM | Validation Philippe CARR : 27/27 scores localStorage = DB (intégrité confirmée) |
| 27 février PM | Validation Sami BEN TIBA : 26/26 scores localStorage = DB (intégrité confirmée) |
| 27 février PM | Reset mot de passe Selima KLIBI (connexion impossible après réinstallation) |
| 27 février PM | Clarification : Edouard, Laroussi, Alaeddine n'avaient pas encore corrigé → **zéro perte confirmée** |

---

## Mise à jour de l'en-tête du rapport

Le champ **Impact** du rapport original doit être corrigé :

| Champ | Ancienne valeur | Valeur corrigée |
|---|---|---|
| Impact | Perte partielle : 57 notes sur 209 copies non récupérables | **Zéro perte de données** — 150/209 copies corrigées intégralement récupérées, 59 copies non encore corrigées |
| Statut | Plateforme reconstituée — Investigation forensique clôturée | **Plateforme reconstituée — Récupération 100% confirmée** |

---

## Mise à jour de la section 4 — État des lieux par correcteur

### 4.1 BB_J1 — État actualisé (27 février 17h)

| Correcteur | Assignées | Scores en DB | Source | Perte | État |
|---|---|---|---|---|---|
| philippe.carr@ert.tn | 27 | 27 | Dump (27) | 0 | ✅ Complet |
| selima.klibi@ert.tn | 27 | 27 | Dump (13) + localStorage (14) | 0 | ✅ Récupéré |
| patrick.dupont@ert.tn | 26 | 26 | localStorage (26, Ex1+Ex2) | 0* | ✅ Récupéré |
| alaeddine.benrhouma@ert.tn | 26 | 8 | Dump (7) + post-reconst. (1) | 0 | ✅ Conforme |

*Patrick : 26/26 copies ont un score Ex1+Ex2 (15q/33). Ex3+Ex4 n'avaient pas été saisis avant l'incident.

**BB_J1 : zéro perte.** Les 18 copies sans score d'Alaeddine n'avaient pas encore été corrigées.

### 4.2 BB_J2 — État actualisé (27 février 17h)

| Correcteur | Assignées | Scores en DB | Source | Perte | État |
|---|---|---|---|---|---|
| chawki.saadi | 25 | 25 | Dump (25) | 0 | ✅ Complet |
| sami.bentiba | 26 | 26 | Dump (26) | 0 | ✅ Complet |
| edouard.rousseau | 26 | 8 | Dump (4) + post-reconst. (4) | 0 | ✅ Conforme |
| laroussi.laroussi | 26 | 3 | Dump (3) | 0 | ✅ Conforme |

**BB_J2 : zéro perte.** Les copies sans score d'Edouard (18) et Laroussi (23) n'avaient pas encore été corrigées.

### 4.3 Synthèse actualisée

|  | Scores complets (33q) | Scores partiels (15q) | Non corrigées | Total |
|---|---|---|---|---|
| BB_J1 | 62 | 26* | 18 | 106 |
| BB_J2 | 62 | 0 | 41 | 103 |
| **TOTAL** | **124** | **26*** | **59** | **209** |

*26 copies Patrick avec Ex1+Ex2 uniquement (15 questions sur 33)

**Total copies avec au moins un score : 150/209 (72%)**

**Données perdues : 0/209 (0%).** Toutes les corrections effectuées avant l'incident ont été intégralement récupérées.

---

## Mise à jour de la section 7 — Fichiers livrés

Ajouter :

| Fichier | Description |
|---|---|
| `recovery.html` + `.js` + `.css` | Outil de récupération localStorage déployé sur le serveur |
| `import_patrick_scores.py` | Script d'import des 26 scores Patrick depuis localStorage |
| `import_selima_scores.py` | Script d'import des 14 scores Selima depuis localStorage |
| `selima_scores.json` | 27 jeux de scores Selima (33 questions chacun) |
| `selima_uuid_mapping.json` | Mapping 27 anciens UUIDs → anonymous_id pour Selima |
| `selima_recovery_raw.json` | Données brutes localStorage Chrome de Selima |
| `patrick_uuid_mapping.json` | Mapping 26 anciens UUIDs → anonymous_id pour Patrick |
| `AUDIT_CORRECTIONS.md` | Audit détaillé copie par copie, 8 correcteurs, 388 lignes |
| `MESSAGE_WHATSAPP_COLLEGUES.md` | Template message WhatsApp envoyé aux correcteurs |

---

## Mise à jour de la section 8.1 — Actions immédiates

### Statut actualisé des actions

La récupération est **terminée**. Il ne reste que la poursuite normale des corrections :

| Correcteur | Scores récupérés | Perte | Action restante |
|---|---|---|---|
| philippe.carr@ert.tn | 27/27 | 0 | ✅ Terminé |
| selima.klibi@ert.tn | 27/27 | 0 | ✅ Terminé (14 via localStorage) |
| patrick.dupont@ert.tn | 26/26 (Ex1+Ex2) | 0 | Continuer Ex3+Ex4 dans Korrigo |
| chawki.saadi | 25/25 | 0 | ✅ Terminé |
| sami.bentiba | 26/26 | 0 | ✅ Terminé |
| edouard.rousseau | 8/26 | 0 | Continuer les corrections (18 copies) |
| laroussi.laroussi | 3/26 | 0 | Continuer les corrections (23 copies) |
| alaeddine.benrhouma@ert.tn | 8/26 | 0 | Continuer les corrections (18 copies) |

---

## Mise à jour de la section 9 — Conclusion

### Conclusion actualisée (27 février 17h)

L'incident du 26 février 2026 a entraîné la perte du serveur de production. Grâce à un effort de récupération en quatre phases successives, l'état actuel est le suivant :

- **Phase 1** (forensique serveur) : Aucune donnée exploitable retrouvée
- **Phase 2** (investigation locale) : Dump du 20 février découvert → 105 scores récupérés
- **Phase 3** (reconstitution) : Plateforme intégralement reconstruite et opérationnelle
- **Phase 4** (localStorage navigateurs) : 40 scores supplémentaires récupérés (26 Patrick + 14 Selima) + 53 validations d'intégrité (27 Philippe + 26 Sami)

### Bilan final : zéro perte de données

**150/209 copies** ont au moins un score en base de données (72%). 102 copies sont au statut GRADED (finalisées).

Les 59 copies sans score correspondent à des **corrections non encore effectuées** par les correcteurs concernés (Edouard Rousseau, Laroussi Laroussi, Alaeddine Benrhouma) au moment de l'incident. Il ne s'agit **pas de données perdues** mais de travail restant à effectuer.

**Aucune correction effectuée avant l'incident n'a été perdue.** Le dump du 20 février combiné à la récupération localStorage a permis de restaurer 100% des données de correction existantes.

La seule situation particulière est celle de **Patrick Dupont** (26 copies BB_J1) dont les scores ne couvrent que les exercices 1 et 2 (15 questions sur 33) : les exercices 3 et 4 n'avaient pas été saisis dans Korrigo avant le crash et restent à compléter.

La récupération via localStorage des navigateurs s'est révélée être la technique décisive pour reconstituer les données post-dump, passant le taux de récupération de 50% (Phase 2) à 100% des corrections réellement effectuées.
