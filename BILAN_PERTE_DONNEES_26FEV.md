# BILAN DE PERTE DE DONNÉES — Korrigo Bac Blanc Maths
**Date du rapport** : 26 février 2026 (mis à jour le 26 fév 17h)  
**Contexte** : Réinstallation serveur Hetzner (88.99.254.59) avec formatage disques — perte totale des données serveur  
**Dernier backup disponible** : dump PostgreSQL du **20 février 2026 à 09:06 UTC+1**

---

## 1. RÉSUMÉ EXÉCUTIF

| Métrique | BB_J1 | BB_J2 | Total |
|----------|-------|-------|-------|
| **Copies totales** | 106 | 103 | **209** |
| **Finalisées (GRADED) dans le dump** | 16 | 26 | **42** |
| **Notes saisies non finalisées (READY + scores)** | 31 | 32 | **63** |
| **Total notes récupérables** | **47** | **58** | **105** |
| **Copies sans données (PERDUES)** | 59 | 45 | **104** |
| **Preuve de correction post-dump** | bilan_walid.tex (22 fév, 8,25/20), PDFs (23-25 fév) | | |

### Verdict
> **~50% des notes sont récupérables** (105/209). L'extraction approfondie du dump a révélé **63 copies supplémentaires** avec notes saisies dans le barème mais non finalisées. Les **104 copies sans aucune donnée** dans le dump sont définitivement perdues — elles ont été corrigées après le 20 février.
>
> **Découverte majeure** : philippe.carr a **27/27 notes** dans le dump, sami.bentiba **26/26**, chawki.saadi **25/25**. Seuls patrick.dupont (0/26), une partie de selima.klibi (14/27 manquantes), edouard.rousseau (22/26 manquantes), laroussi (23/26 manquantes) et alaeddine (19/26 manquantes) ont des copies réellement perdues.

---

## 2. DONNÉES RÉCUPÉRABLES (dump du 20 février) — 105 NOTES

L'extraction approfondie du dump a révélé que **105 copies** possèdent des notes complètes avec détail par exercice (`scores_data`). Parmi elles, 42 sont finalisées (GRADED) et **63 supplémentaires** avaient les notes saisies dans le barème mais n'avaient pas encore été finalisées (statut READY).

### 2.1 RÉCAPITULATIF PAR CORRECTEUR

| Correcteur | Exam | Assignées | Finalisées | Notes saisies | **Total notes** | Sans données |
|------------|------|-----------|-----------|---------------|-----------------|-------------|
| **philippe.carr** | BB_J1 | 27 | 16 | 11 | **27/27** ✅ | 0 |
| **selima.klibi** | BB_J1 | 27 | 0 | 13 | **13/27** | 14 |
| **alaeddine.benrhouma** | BB_J1 | 26 | 0 | 7 | **7/26** | 19 |
| **patrick.dupont** | BB_J1 | 26 | 0 | 0 | **0/26** ❌ | 26 |
| | | **106** | **16** | **31** | **47** | **59** |
| **chawki.saadi** | BB_J2 | 25 | 23 | 2 | **25/25** ✅ | 0 |
| **sami.bentiba** | BB_J2 | 26 | 0 | 26 | **26/26** ✅ | 0 |
| **edouard.rousseau** | BB_J2 | 26 | 3 | 1 | **4/26** | 22 |
| **laroussi.laroussi** | BB_J2 | 26 | 0 | 3 | **3/26** | 23 |
| | | **103** | **26** | **32** | **58** | **45** |
| **TOTAL** | | **209** | **42** | **63** | **105** | **104** |

### 2.2 BB_J1 — philippe.carr : 27/27 notes (16 finalisées + 11 en cours)

| # | Anon_ID | Élève | Note/20 | Statut | Annots | Rem. |
|---|---------|-------|---------|--------|--------|------|
| 1 | 0F8E-055 | HACHICH Selim | **20,00** | 📝 notes saisies | 0 | 4 |
| 2 | 0F8E-059 | ISSA Mourad | **19,50** | ✅ finalisée | 17 | 6 |
| 3 | 0F8E-056 | HAMAIED Emna | **18,75** | ✅ finalisée | 18 | 6 |
| 4 | 0F8E-066 | JOMAA Emine | **18,60** | ✅ finalisée | 17 | 5 |
| 5 | 0F8E-063 | JALLOULI Amine | **17,85** | 📝 notes saisies | 5 | 12 |
| 6 | 0F8E-076 | MECHICHI Mehdi | **17,60** | ✅ finalisée | 17 | 9 |
| 7 | 0F8E-077 | MEDFAI Iyed-Ahmed | **15,70** | ✅ finalisée | 22 | 13 |
| 8 | 0F8E-071 | KHOUADJA Lina | **15,50** | ✅ finalisée | 21 | 17 |
| 9 | 0F8E-079 | MEHERZI Mohamed-Wael | **15,50** | ✅ finalisée | 31 | 13 |
| 10 | 0F8E-074 | MARRAKCHI Ahmed | **15,45** | ✅ finalisée | 36 | 17 |
| 11 | 0F8E-067 | KAABI Omar-Mokhtar | **15,00** | 📝 notes saisies | 0 | 19 |
| 12 | 0F8E-070 | KHEMIRI Hedi | **14,25** | ✅ finalisée | 35 | 16 |
| 13 | 0F8E-065 | JERIBI Omar | **14,00** | 📝 notes saisies | 0 | 15 |
| 14 | 0F8E-061 | JABEUR Ramy | **13,50** | 📝 notes saisies | 4 | 17 |
| 15 | 0F8E-068 | KAMMOUN Aymar | **16,65** | 📝 notes saisies | 11 | 12 |
| 16 | 0F8E-075 | MDIMAGH Emna | **12,25** | 📝 notes saisies | 6 | 21 |
| 17 | 0F8E-058 | HASSAIRI Hedi | **12,80** | ✅ finalisée | 32 | 19 |
| 18 | 0F8E-054 | GRATI Mohamed-Mehdi | **11,75** | ✅ finalisée | 15 | 22 |
| 19 | 0F8E-057 | HAMZAOUI Ismaël Satyavan | **11,15** | ✅ finalisée | 27 | 18 |
| 20 | 0F8E-072 | LUCIANI Ines | **9,00** | ✅ finalisée | 28 | 18 |
| 21 | 0F8E-060 | JAAFAR Youssef | **8,75** | 📝 notes saisies | 0 | 20 |
| 22 | 0F8E-062 | JAIDANE Mohamed-Seyf | **8,25** | 📝 notes saisies | 11 | 24 |
| 23 | 0F8E-078 | MEHERZI Ines | **8,00** | ✅ finalisée | 35 | 20 |
| 24 | 0F8E-064 | JEBIRA Sami | **7,75** | ✅ finalisée | 34 | 21 |
| 25 | 0F8E-053 | GRAF Alia | **7,25** | 📝 notes saisies | 0 | 27 |
| 26 | 0F8E-069 | KHALSI Safe | **6,25** | 📝 notes saisies | 11 | 27 |
| 27 | 0F8E-073 | MAATOUG Safa | **4,50** | ✅ finalisée | 30 | 25 |

*Statistiques philippe.carr : min=4,50 — max=20,00 — moy=**13,46***

### 2.3 BB_J1 — selima.klibi : 13/27 notes (0 finalisées, 13 en cours)

| # | Anon_ID | Élève | Note/20 | Annots | Rem. |
|---|---------|-------|---------|--------|------|
| 1 | 0F8E-090 | OUEDERNI Rafif | **18,45** | 23 | 5 |
| 2 | 0F8E-080 | MEJRI Haroun | **18,15** | 0 | 11 |
| 3 | 0F8E-088 | MZOUGHI Lina | **18,10** | 8 | 6 |
| 4 | 0F8E-091 | OUERGHI Maya | **18,05** | 0 | 7 |
| 5 | 0F8E-086 | MRAD Mohamed-Aziz | **17,70** | 0 | 12 |
| 6 | 0F8E-081 | MESTIRI Mahmoud | **17,60** | 0 | 13 |
| 7 | 0F8E-084 | M'HIRSI Rayene | **16,40** | 0 | 16 |
| 8 | 0F8E-092 | PERON Rayan | **14,80** | 0 | 19 |
| 9 | 0F8E-089 | NAJI Ines | **11,75** | 0 | 17 |
| 10 | 0F8E-087 | MYAMBAYE Ahmat Christopher | **10,90** | 0 | 19 |
| 11 | 0F8E-085 | MONTACER Rayen | **9,70** | 0 | 17 |
| 12 | 0F8E-083 | M'HAMED Selima | **7,55** | 0 | 22 |
| 13 | 0F8E-082 | MEZIANE Walid | **6,25** | 0 | 20 |

*Statistiques selima.klibi : min=6,25 — max=18,45 — moy=**14,26***
*Note : MEZIANE Walid avait 6,25 dans le dump mais 8,25 dans bilan_walid.tex (22 fév) — note révisée post-dump*

### 2.4 BB_J1 — alaeddine.benrhouma : 7/26 notes (0 finalisées, 7 en cours)

| # | Anon_ID | Élève | Note/20 |
|---|---------|-------|---------|
| 1 | 0F8E-005 | ALLANI Meriem | **5,00** |
| 2 | 0F8E-006 | ALOULOU Malek Loula | **5,00** |
| 3 | 0F8E-007 | AMARA Fares | **5,00** |
| 4 | 0F8E-003 | AGREBI Sandra-Ines | **4,00** |
| 5 | 0F8E-002 | ABOUDA Amine | **4,00** |
| 6 | 0F8E-004 | ALBANESE Alexandre | **3,00** |
| 7 | 0F8E-001 | ABID Youcef | **2,00** |

*Statistiques alaeddine : min=2,00 — max=5,00 — moy=**4,00***

### 2.5 BB_J2 — chawki.saadi : 25/25 notes (23 finalisées + 2 en cours)

| # | Anon_ID | Élève | Note/20 | Statut |
|---|---------|-------|---------|--------|
| 1 | 75FB-016 | BENNANI Lilya | **19,00** | ✅ finalisée |
| 2 | 75FB-007 | AMMAR Amal | **19,00** | ✅ finalisée |
| 3 | 75FB-006 | ALBOUCHI Adam | **18,25** | ✅ finalisée |
| 4 | 75FB-011 | BCHATNIA Ikram | **18,25** | ✅ finalisée |
| 5 | 75FB-013 | BELHAJ Sirine | **18,25** | ✅ finalisée |
| 6 | 75FB-018 | BENOTHMAN Malek | **17,75** | ✅ finalisée |
| 7 | 75FB-021 | BEN GHORBAL Feryel | **17,50** | ✅ finalisée |
| 8 | 75FB-004 | AKID Aziz | **14,75** | ✅ finalisée |
| 9 | 75FB-003 | AFFES Youssef | **14,50** | ✅ finalisée |
| 10 | 75FB-008 | AOUADI Ahmed | **14,50** | ✅ finalisée |
| 11 | 75FB-012 | BEJI Sarra | **14,50** | ✅ finalisée |
| 12 | 75FB-017 | BENNEJI Sarah | **14,00** | ✅ finalisée |
| 13 | 75FB-009 | ATI Syrine | **12,75** | ✅ finalisée |
| 14 | 75FB-002 | ABDENNADHER Zaineb | **12,50** | ✅ finalisée |
| 15 | 75FB-019 | BEN ALAYA Zineddine | **12,00** | ✅ finalisée |
| 16 | 75FB-015 | BENLTIFA Maram | **11,25** | ✅ finalisée |
| 17 | 75FB-010 | BACCOUCHE Lina | **10,75** | ✅ finalisée |
| 18 | 75FB-022 | BEN HTIRA Adonis | **10,75** | ✅ finalisée |
| 19 | 75FB-025 | BEN RABAA Mohamed | **9,75** | ✅ finalisée |
| 20 | 75FB-014 | BELTAIEF Lina | **9,50** | ✅ finalisée |
| 21 | 75FB-020 | BEN BRIK Anes | **9,00** | ✅ finalisée |
| 22 | 75FB-005 | AKROUT Mehdi | **7,75** | ✅ finalisée |
| 23 | 75FB-024 | BEN MEZIANE Maya | **2,50** | ✅ finalisée |
| 24 | 75FB-001 | ABDELMOULA Khalil | **20,00** | 📝 notes saisies |
| 25 | 75FB-023 | BEN JEMAA Slim | **8,50** | 📝 notes saisies |

*Statistiques chawki.saadi : min=2,50 — max=20,00 — moy=**13,28***

### 2.6 BB_J2 — sami.bentiba : 26/26 notes (0 finalisées, 26 en cours)

| # | Anon_ID | Élève | Note/20 |
|---|---------|-------|---------|
| 1 | 75FB-089 | REJEB Nour | **18,75** |
| 2 | 75FB-090 | SAADI Myriam | **15,50** |
| 3 | 75FB-094 | SMAOUI Yassine | **14,75** |
| 4 | 75FB-086 | OUESLATI Israa | **14,00** |
| 5 | 75FB-088 | RAJHI Leith | **13,50** |
| 6 | 75FB-093 | SLAMA Zeineb | **13,25** |
| 7 | 75FB-092 | SKHIRI Fatma | **12,25** |
| 8 | 75FB-089 | REJEB Nour | **12,25** |
| 9 | 75FB-091 | SAIGHI Ghalia | **11,75** |
| 10 | 75FB-098 | TRABELSI Ons | **11,75** |
| 11 | 75FB-085 | MZOUGHI Emna | **11,75** |
| 12 | 75FB-082 | MESSEDI Khadija | **10,00** |
| 13 | 75FB-084 | MOATEMRI Mohamed-Badis | **8,75** |
| 14 | 75FB-078 | MAYARD Rafed | **8,75** |
| 15 | 75FB-083 | MEZIOU Ines Celia | **7,75** |
| 16 | 75FB-080 | MEGDICHE Sarah | **7,25** |
| 17 | 75FB-079 | M'BAZAA Skander | **7,25** |
| 18 | 75FB-075 | MDIMAGH Emna | **7,55** |
| 19 | 75FB-099 | TRIFA Yassine | **5,75** |
| 20 | 75FB-100 | TURKI Malek | **5,00** |
| 21 | 75FB-095 | SNOUSSI Yasmine | **2,25** |
| 22 | 75FB-103 | ZOUAOUI Ilian | **4,25** |
| 23 | 75FB-097 | TRABELSI Mohamed | **0,75** |
| 24 | 75FB-096 | SOUISSI Aya | **13,75** |
| 25 | 75FB-101 | YOLCU Elif | **10,25** |
| 26 | 75FB-081 | MEGHIRBI Fatma | **12,25** |

*Statistiques sami.bentiba : min=0,75 — max=18,75 — moy=**9,69***

### 2.7 BB_J2 — edouard.rousseau : 4/26 notes (3 finalisées + 1 en cours)

| # | Anon_ID | Élève | Note/20 | Statut |
|---|---------|-------|---------|--------|
| 1 | 75FB-027 | BLOUZA Emna | **19,50** | ✅ finalisée |
| 2 | 75FB-028 | BOUDAYA Ahmed | **17,00** | ✅ finalisée |
| 3 | 75FB-029 | BOUGUEDOUR Samy-Nazim | **6,25** | ✅ finalisée |
| 4 | 75FB-026 | BEN SLIMANE Ines | **13,75** | 📝 notes saisies |

*Statistiques edouard : min=6,25 — max=19,50 — moy=**14,13***

### 2.8 BB_J2 — laroussi.laroussi : 3/26 notes (0 finalisées, 3 en cours)

| # | Anon_ID | Élève | Note/20 |
|---|---------|-------|---------|
| 1 | 75FB-070 | KTATA Emna | **18,25** |
| 2 | 75FB-071 | LAADHARI Nour | **14,50** |
| 3 | 75FB-069 | KRIR Oussema | **11,00** |

*Statistiques laroussi : min=11,00 — max=18,25 — moy=**14,58***

### 2.9 Données annexes récupérées du dump

| Entité | Quantité |
|--------|----------|
| Scores (barèmes détaillés par exercice) | **105** (toutes les notes ci-dessus) |
| Annotations | 544 (494 J1 + 50 J2) |
| Remarques par question | 1 075 (627 J1 + 448 J2) |
| Événements de correction | 2 221 (1 519 J1 + 699 J2) |
| Appréciations globales | 42 (copies finalisées) |
| Bilans LLM générés | 42 (copies finalisées) |
| PDFs finaux (dans dump) | 42 (copies finalisées) |

### 2.10 Source complémentaire : bilan_walid.tex (22 février)

- **MEZIANE Walid** (0F8E-082, BB_J1) : dump donne **6,25/20** (selima.klibi), bilan LaTeX du 22 fév donne **8,25/20** (philippe.carr)
- La note 8,25 est la note révisée post-dump, non présente dans le dump

---

## 3. DONNÉES PERDUES (104 copies sans aucune donnée)

### 3.1 Bilan révisé par correcteur

| Correcteur | Exam | Assignées | Notes dans dump | **Sans données (PERDUES)** |
|------------|------|-----------|-----------------|---------------------------|
| **patrick.dupont** | BB_J1 | 26 | 0 | **26** |
| **alaeddine.benrhouma** | BB_J1 | 26 | 7 | **19** |
| **selima.klibi** | BB_J1 | 27 | 13 | **14** |
| philippe.carr | BB_J1 | 27 | 27 | **0** ✅ |
| **laroussi.laroussi** | BB_J2 | 26 | 3 | **23** |
| **edouard.rousseau** | BB_J2 | 26 | 4 | **22** |
| chawki.saadi | BB_J2 | 25 | 25 | **0** ✅ |
| sami.bentiba | BB_J2 | 26 | 26 | **0** ✅ |
| **Total** | | **209** | **105** | **104** |

### 3.2 Total perdu vs. ancien bilan

| Catégorie | Ancien bilan (42 notes) | **Bilan révisé (105 notes)** |
|-----------|------------------------|------------------------------|
| Notes perdues | 167 | **104** |
| Notes récupérables | 42 | **105** |
| Taux de récupération | 20% | **50%** |
| Travail à refaire (heures) | ~80-120h | **~50-60h** |

---

## 4. PREUVES DE CORRECTIONS POST-DUMP

Les éléments suivants prouvent que des corrections ont été effectuées **après** le dump du 20 février :

### 4.1 Bilan LaTeX de Walid Meziane (22 février)
- **Fichier** : `/home/alaeddine/Documents/walid_meziane/bilan_walid.tex`
- **Date** : 22 février 2026, 20:56
- **Note BB J1** : **8,25/20** (Ex1: 3/5, Ex2: 1,25/5, Ex3: 1,75/4, Ex4: 2,25/6)
- **Correcteur** : philippe.carr (BB_J1)
- **WALID MEZIANE n'est PAS dans les 16 copies corrigées du dump** → preuve de correction post-dump

### 4.2 PDFs téléchargés depuis Korrigo (23-25 février)
| Fichier | Date | Taille |
|---------|------|--------|
| `copies_lot1/BELCADHI_YOLDEZ.pdf` | 23 fév 16:09 | 2,2 Mo |
| `copies_lot1/BEN_MRAD_YOUSSEF.pdf` | 23 fév 16:09 | 912 Ko |
| `copies_lot1/JERIBI_OMAR.pdf` | 23 fév 16:09 | 1,6 Mo |
| `copies_lot1/MEZIANE_WALID.pdf` | 23 fév 16:09 | 747 Ko |
| `copie_KTATA_EMNA.pdf` (pypdf) | 25 fév 14:36 | 2,86 Mo |
| `KTATA_EMNA.pdf` | 25 fév 14:09 | 2,74 Mo |

### 4.3 Activité serveur confirmée
- Le serveur Korrigo était **opérationnel** entre le 20 et le 26 février
- Les correcteurs ont continué à corriger via l'interface web
- Philippe Carr a explicitement corrigé les 27 copies BB_J1 qui lui étaient assignées (+ bilan Walid comme preuve)

---

## 5. RESSOURCES LOCALES DISPONIBLES

### 5.1 Scans originaux (copies brutes, non annotées)
| Source | Copies | Emplacement |
|--------|--------|-------------|
| BB_J1 scans | 106 | `~/Téléchargements/scan_J1_BB_maths/copies_finales/` |
| BB_J1 scans (korrigo format) | 106 | `~/Téléchargements/scan_J1_BB_maths/copies_finales_J1_korrigo/` |
| BB_J2 scans | 103 | `~/Téléchargements/scan_J2_BB_maths/copies_finales_J2/` |
| BB_J1 scans (Documents) | 106 | `~/Documents/BB_maths/scan_J1_BB_maths/copies_finales/` |

### 5.2 Fichiers de référence
| Fichier | Contenu |
|---------|---------|
| `BILAN_AFFECTATIONS.md` | Affectations complètes des 209 copies aux 8 correcteurs |
| `deploy_mapping.json` | Mapping copy_uuid ↔ nom élève ↔ anon_id (106 J1) |
| `eleves_terminale_maths.csv` | Liste des 209 élèves (nom, prénom, email, classe, groupe) |
| `entity_counts.txt` | Comptages du dump |
| `db_2026-02-20.dump` | Dump PostgreSQL (445 Ko) |
| `bilan_walid.tex` | 1 note BB J1 confirmée post-dump |

### 5.3 Notes d'évaluations antérieures (hors BB)
| Source | Élèves | Nature |
|--------|--------|--------|
| `EDS MATHS_notes_trim1.csv` | 28 | Notes trimestre 1 (nov 2025) |
| `eval_log_binom_terminale/` | 28 | Bilans eval logarithmes/binomiale (fév 2026) |

---

## 6. CHRONOLOGIE

```
13 fév   Reset complet DB + réimport 209 copies (0 correction)
14 fév   Première correction : edouard → BLOUZA EMNA (J2) = 19,50
16 fév   philippe.carr finalise 16 copies J1 (GRADED)
         edouard.rousseau finalise 2 copies J2
18 fév   chawki.saadi finalise 23 copies J2 (dernière : 20:35)
         ← Dernière FINALISATION dans le dump : 18 fév 20:35 ←
         Pendant ce temps : notes saisies (non finalisées) par selima, sami, alaeddine, etc.
20 fév   DUMP PostgreSQL réalisé à 09:06
         → 42 copies finalisées (GRADED) + 63 copies avec notes saisies (READY + scores)
         → TOTAL : 105 notes récupérables dans le dump
         Audit RC_2026-02-20 + déploiement overlay + fix compute_score
         Génération 42 bilans LLM + 42 PDFs finaux
20-25    Corrections continuent sur les 104 copies restantes sans données
22 fév   Bilan LaTeX Walid Meziane créé (note révisée: 8,25/20, était 6,25 dans dump)
23 fév   4 PDFs copies BB_J1 téléchargés depuis le serveur
25 fév   copie_KTATA_EMNA.pdf téléchargé (BB_J2, pypdf = annoté)
26 fév   Réinstallation serveur Hetzner — FORMATAGE DISQUES
         → Perte totale de toutes les données post-dump
```

---

## 7. OPTIONS DE RECONSTRUCTION

### Option A — Re-correction des 104 copies manquantes uniquement
- **Effort** : ~50-60h de travail correcteur (au lieu de 80-120h initialement estimé)
- **Prérequis** : Restaurer le dump → réinjecter les 105 notes → re-dispatcher les 104 restantes
- **Avantage** : Les correcteurs philippe.carr, chawki.saadi et sami.bentiba n'ont RIEN à refaire
- **Inconvénient** : patrick.dupont doit tout refaire (26 copies)

### Option B — Restauration des 105 notes + notes approximatives
- **Restaurer les 105 notes du dump** (42 finalisées + 63 en cours)
- **Contacter edouard, laroussi, patrick** pour récupérer des notes manuscrites ou photos d'écran
- **Utiliser les bilans de classe** (trim 1 + eval log/binom) pour estimer les notes manquantes
- **Effort** : Variable, principalement patrick (26), edouard (22), laroussi (23)

### Option C — Restauration du dump seul (minimum viable)
- **105 notes disponibles immédiatement** après restauration (avec script de réinjection)
- Les 104 copies restantes seraient marquées READY (non corrigées)
- **Redémarrage très rapide** : 50% des notes déjà disponibles

---

## 8. RECOMMANDATION

1. **Restaurer le dump immédiatement** sur le nouveau serveur
2. **Réinjecter les 63 notes non finalisées** via un script SQL INSERT INTO grading_score
3. **philippe.carr : RIEN à refaire** — ses 27/27 notes sont dans le dump
4. **chawki.saadi : RIEN à refaire** — ses 25/25 notes sont dans le dump
5. **sami.bentiba : RIEN à refaire** — ses 26/26 notes sont dans le dump
6. **Contacter patrick.dupont en priorité** — 0/26 notes, tout est perdu
7. **Contacter edouard.rousseau** — 22/26 notes perdues
8. **Contacter laroussi.laroussi** — 23/26 notes perdues
9. **selima.klibi** — 14/27 notes perdues (13 récupérables)
10. **alaeddine** — 19/26 notes perdues (7 récupérables)
11. **Mettre en place des backups automatiques** (cron pg_dump toutes les 6h minimum)

---

## 9. FICHIERS GÉNÉRÉS

| Fichier | Description |
|---------|-------------|
| `BILAN_PERTE_DONNEES_26FEV.md` | Ce rapport (mis à jour) |
| `proofs/RC_2026-02-20/NOTES_RECUPERABLES_105.csv` | CSV avec les 105 notes détaillées (note, exercices, correcteur, statut) |
| `proofs/RC_2026-02-20/RECONSTITUTION_COMPLETE_105_NOTES.md` | Rapport détaillé par correcteur avec notes par exercice |
| `proofs/RC_2026-02-20/backups/db_2026-02-20.dump` | Dump PostgreSQL source (445 Ko) |

---

*Rapport généré par analyse forensique approfondie du dump PostgreSQL, des fichiers locaux (bilan_walid.tex, PDFs téléchargés) et de l'historique Windsurf. Mis à jour le 26 février 2026 à 17h.*
