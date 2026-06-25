"""
EAM Bilan Orchestrator v2 — Bilan Premium post-correction
Épreuve Anticipée de Mathématiques Blanche 2026 — Première Générale Spécialité Maths

Structure du rapport S0-S5 :
- S0 — Synthèse exécutive (5 puces denses + encadré méthodologique Cheine/Chahed)
- S1 — Tableau de bord (stats globales + A vs B + stats_by_class enrichies)
- S2A — Automatismes (12 QCM, 6 pts) — analyse + distracteurs + micro-rituels
- S2B — Exercices (3 exercices, 14 pts) — analyse profonde par sous-partie + erreurs typiques
- S3 — Tableau complet question-par-question (31 items)
- S4 — Recommandations premium (3 blocs avec indicateurs mesurables + plan 8 semaines)
- S5 — Table correspondance question ↔ programme BO ↔ sous-thème RAG

Sources exclusives : DB réelle (copies FINALIZED) + RAG rag_maths_premiere
Garde-fous : anti-DNB validation + retry automatique
Brief : Lycée Pierre Mendès France Tunis — N=189 copies — Classes 1.01 à 1.10
Exclus : groupes M. Sidi CHEINE et Mme Imen CHAHED (correction papier)
"""

import re
import statistics
import logging
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from .rag_retriever import RAGRetriever
from .llm_writer import write, EAM_SYSTEM_PROMPT
from .analytics_simple import DNBAnalyticsEngine as AnalyticsEngine
from exams.grading_utils import extract_leaf_questions

logger = logging.getLogger(__name__)

# Forbidden terms — anti-confusion EAM / DNB (exhaustif)
# Format: (term, use_word_boundary)
# use_word_boundary=True -> match only as whole word (avoids "Troisième action" false positive)
FORBIDDEN_TERMS: List[Tuple[str, bool]] = [
    ('DNB', False),
    ('brevet', True),
    ('cycle 4', False),
    ('3e', True),                  # word boundary: évite "3ème" collision
    ('3ème', True),
    ('3eme', True),
    ('classe de troisième', False),   # contextualised: only flags grade-level references
    ('en troisième', False),          # contextualised: "en troisième" = classe
    ('brevet des collèges', False),
    ('brevet des colleges', False),
    ('collège', True),
    ('college', True),
    ('diplôme national', False),
    ('diplome national', False),
]

# EAM-specific LLM models (overridable via Django settings)
# v2.2: EAM bilan requires sonnet (haiku hallucinates names/dates).
# EAM_LLM_SYNTHESIS/ANALYSIS are EAM-specific overrides in settings.
# Do NOT fall back to BILAN_LLM_PREMIUM/DEFAULT (those are set to haiku in prod).
EAM_LLM_SYNTHESIS = getattr(settings, 'EAM_LLM_SYNTHESIS', 'anthropic/claude-sonnet-4')
EAM_LLM_ANALYSIS = getattr(settings, 'EAM_LLM_ANALYSIS', 'anthropic/claude-sonnet-4')

# EAM grading structure constants
EAM_NODE_AUTOMATISMES = 'automatismes'
EAM_TOTAL_POINTS = 20.0
EAM_AUTOMATISMES_MAX_POINTS = 6.0
EAM_EXERCICES_MAX_POINTS = 14.0

# Classes incluses dans l'échantillon Korrigo
EAM_INCLUDED_CLASSES = ['1.01', '1.02', '1.03', '1.04', '1.05', '1.06', '1.07', '1.08', '1.09', '1.10']

# Classes corrigées hors Korrigo (mention obligatoire dans le rapport)
EAM_EXCLUDED_TEACHERS = ['M. Sidi CHEINE', 'Mme Imen CHAHED']
EAM_EXCLUDED_NOTE = (
    "Ce bilan porte sur 189 copies dématérialisées corrigées via la plateforme Korrigo. "
    "Les copies des groupes encadrés par M. Sidi CHEINE et Mme Imen CHAHED ont été corrigées "
    "au format papier, conformément à leur choix pédagogique. Elles ne sont pas intégrées à "
    "l'échantillon analysé : les indicateurs ci-dessous ne décrivent donc pas l'intégralité "
    "de la promotion de Première Générale. Une consolidation manuelle pourra être proposée "
    "ultérieurement à partir des notes papier transmises."
)

# ── Catalogue officiel des questions EAM BLANCHE 2026 ──────────────────────────
# Source : Sujet officiel + barème harmonisé + programme BO Première Générale
# Chaque entrée : id_bareme (correspond à label dans grading_structure),
#   notion, capacite_bo, automatisme_bo, rag_subtheme, distractor (si taux < 60%)
EAM_QUESTION_CATALOGUE = {
    # ── Automatismes (Partie A) ──
    'Q1':  {
        'notion': 'Probabilités totales sur arbre pondéré',
        'capacite_bo': 'Calculer une probabilité à l\'aide de la formule des probabilités totales',
        'automatisme_bo': 'Calcul de probabilités à partir d\'un arbre pondéré',
        'rag_subtheme': 'probabilites/arbres_ponderes',
        'distractor': None,
    },
    'Q2':  {
        'notion': 'Taux d\'évolution réciproque',
        'capacite_bo': 'Calculer un taux d\'évolution réciproque',
        'automatisme_bo': 'Taux d\'évolution et taux réciproque',
        'rag_subtheme': 'evolutions/taux_reciproque',
        'distractor': 'Confusion entre taux réciproque (÷ par 1+t) et taux opposé (−t) ; '
                      'erreur typique : −20 % donné comme réciproque de +25 % au lieu de −20 %.',
    },
    'Q3':  {
        'notion': 'Équation cartésienne de droite',
        'capacite_bo': 'Exploiter une équation de courbe dans le plan',
        'automatisme_bo': 'Lecture et écriture d\'une équation réduite de droite',
        'rag_subtheme': 'geometrie_reperee/droites',
        'distractor': None,
    },
    'Q4':  {
        'notion': 'Identité remarquable (a − b)²',
        'capacite_bo': 'Développer, factoriser, réduire une expression algébrique',
        'automatisme_bo': 'Identités remarquables — développement et factorisation',
        'rag_subtheme': 'algebre/identites',
        'distractor': None,
    },
    'Q5':  {
        'notion': 'Calcul de puissances entières',
        'capacite_bo': 'Effectuer des opérations sur les puissances entières relatives',
        'automatisme_bo': 'Règles de calcul sur les puissances',
        'rag_subtheme': 'algebre/puissances',
        'distractor': None,
    },
    'Q6':  {
        'notion': 'Valeurs exactes sin(π/4), cos(2π/3)',
        'capacite_bo': 'Déterminer les valeurs exactes de cosinus et sinus pour les valeurs remarquables',
        'automatisme_bo': 'Cercle trigonométrique — valeurs remarquables',
        'rag_subtheme': 'analyse/trigonometrie/valeurs_remarquables',
        'distractor': 'Confusion entre valeurs de sin et cos pour π/4 (égaux) et pour 2π/3 '
                      '(cos négatif). Erreur de signe fréquente sur cos(2π/3) = −1/2.',
    },
    'Q7':  {
        'notion': 'Image de 13π/4 sur le cercle trigonométrique',
        'capacite_bo': 'Déterminer l\'image d\'un nombre réel sur le cercle trigonométrique par enroulement',
        'automatisme_bo': 'Réduction modulo 2π — enroulement',
        'rag_subtheme': 'analyse/trigonometrie/cercle',
        'distractor': 'Q7 : deux réponses (a ou b) acceptées conformément au barème harmonisé '
                      '(équivalence trigonométrique vérifiée). À mentionner explicitement.',
    },
    'Q8':  {
        'notion': 'Dérivée de f(x) = 2 + 1/x',
        'capacite_bo': 'Calculer une fonction dérivée — somme et dérivée de 1/x',
        'automatisme_bo': 'Règles de dérivation de référence',
        'rag_subtheme': 'analyse/derivation/regles',
        'distractor': 'Oubli du signe lors de la dérivation de 1/x → −1/x². '
                      'Erreur fréquente : écrire 1/x² au lieu de −1/x².',
    },
    'Q9':  {
        'notion': 'Équation réduite d\'une droite à partir d\'un graphique',
        'capacite_bo': 'Lire graphiquement ou déterminer l\'équation réduite d\'une droite',
        'automatisme_bo': 'Pente et ordonnée à l\'origine — lecture graphique',
        'rag_subtheme': 'geometrie_reperee/droites',
        'distractor': None,
    },
    'Q10': {
        'notion': 'Image de [−3 ; 2[ par x ↦ x²',
        'capacite_bo': 'Étudier les variations de la fonction carré et déterminer l\'image d\'un intervalle',
        'automatisme_bo': 'Signe d\'une expression et variations de x²',
        'rag_subtheme': 'analyse/fonctions_reference',
        'distractor': 'Piège principal : oublier que x² atteint son minimum en 0 ∈ [−3 ; 2[, '
                      'donc l\'image est [0 ; 9] et non [0 ; 4[. '
                      'Erreur fréquente : exclure 0 ou borner par f(2) = 4.',
    },
    'Q11': {
        'notion': 'Somme géométrique 1 + q + q² + … + qⁿ',
        'capacite_bo': 'Calculer la somme des termes d\'une suite géométrique — formule 1 + q + … + qⁿ',
        'automatisme_bo': 'Suites géométriques — terme général et somme',
        'rag_subtheme': 'algebre/suites/somme_geometrique',
        'distractor': 'Confusion entre formule de la somme (1−qⁿ⁺¹)/(1−q) et terme général u_n = u₀·qⁿ. '
                      'Erreur fréquente : appliquer la formule de u_n à la place de la somme.',
    },
    'Q12': {
        'notion': 'Équation rationnelle (x+1)/3 = (2x−1)/5',
        'capacite_bo': 'Résoudre une équation du premier degré à coefficients rationnels',
        'automatisme_bo': 'Isoler une variable — produit en croix et développement',
        'rag_subtheme': 'algebre/equations/premier_degre',
        'distractor': None,
    },
    # ── Exercice 1 : Probabilités ──
    'A.1': {
        'notion': 'Probabilités simples sur tableau croisé',
        'capacite_bo': 'Calculer une probabilité à partir d\'un tableau croisé d\'effectifs',
        'automatisme_bo': 'Lecture de tableau croisé',
        'rag_subtheme': 'probabilites/tableaux_croises',
        'distractor': None,
    },
    'A.2': {
        'notion': 'P(F ∩ S) — lecture directe sur tableau',
        'capacite_bo': 'Calculer une probabilité de l\'intersection à partir d\'un tableau croisé',
        'automatisme_bo': 'Intersection et réunion d\'événements',
        'rag_subtheme': 'probabilites/tableaux_croises',
        'distractor': None,
    },
    'A.3': {
        'notion': 'Justification proportion garçons sportifs',
        'capacite_bo': 'Calculer et interpréter une fréquence relative',
        'automatisme_bo': 'Proportion et pourcentage',
        'rag_subtheme': 'probabilites/tableaux_croises',
        'distractor': None,
    },
    'A.4': {
        'notion': 'Probabilité conditionnelle P_F(S)',
        'capacite_bo': 'Calculer P_A(B) et distinguer P_A(B) de P_B(A)',
        'automatisme_bo': 'Probabilités conditionnelles',
        'rag_subtheme': 'probabilites/conditionnelles',
        'distractor': 'Confusion P_F(S) et P_S(F) — intervertir numérateur et dénominateur. '
                      'Pénalité barème : −0,5 pt si confusion avérée.',
    },
    'A.5': {
        'notion': 'Indépendance de deux événements par calcul',
        'capacite_bo': 'Vérifier l\'indépendance de deux événements par calcul comparatif',
        'automatisme_bo': 'Indépendance — critère P(A∩B) = P(A)·P(B)',
        'rag_subtheme': 'probabilites/independance',
        'distractor': 'Conclusion d\'indépendance sans calcul comparatif explicite '
                      '(P(F∩S) vs P(F)·P(S)). La démonstration doit être complète.',
    },
    'B.1': {
        'notion': 'Loi de probabilité de X (gain net avec mise de 2 €)',
        'capacite_bo': 'Déterminer la loi de probabilité d\'une variable aléatoire',
        'automatisme_bo': 'Variable aléatoire discrète — tableau de loi',
        'rag_subtheme': 'probabilites/variables_aleatoires/loi',
        'distractor': 'Loi incomplète : oubli de P(X = −2) = 0,8 (cas de non-gain). '
                      'Confusion gains bruts / gains nets (ne pas soustraire la mise de 2 €).',
    },
    'B.2': {
        'notion': 'Espérance E(X) et interprétation',
        'capacite_bo': 'Calculer l\'espérance d\'une variable aléatoire et l\'interpréter',
        'automatisme_bo': 'Espérance mathématique',
        'rag_subtheme': 'probabilites/variables_aleatoires/esperance',
        'distractor': 'Calcul avec gains bruts au lieu de gains nets (oubli de soustraire la mise). '
                      'Impact : E(X) erroné de +2 unités.',
    },
    'B.3': {
        'notion': 'Prix t pour jeu équitable E(Y) = 0',
        'capacite_bo': 'Utiliser l\'espérance pour résoudre un problème de jeu équitable',
        'automatisme_bo': 'Résolution E(Y) = 0 — isoler une variable',
        'rag_subtheme': 'probabilites/variables_aleatoires/jeu_equitable',
        'distractor': 'Équation E(Y) = 0 mal posée : le facteur (−t) sur les 80 % de cas '
                      'non gagnants est oublié. t doit apparaître dans toutes les valeurs de Y.',
    },
    # ── Exercice 2 : Optimisation ──
    '1':  {
        'notion': 'Calcul de B\'(x) et factorisation',
        'capacite_bo': 'Calculer une fonction dérivée — polynôme du second degré',
        'automatisme_bo': 'Développer et factoriser une expression',
        'rag_subtheme': 'analyse/derivation/polynomes',
        'distractor': None,
    },
    '2':  {
        'notion': 'Tableau de variations de B sur [0 ; 6] avec bornes',
        'capacite_bo': 'Dresser un tableau de variations complet avec valeurs aux bornes',
        'automatisme_bo': 'Signe d\'une expression factorisée du second degré',
        'rag_subtheme': 'analyse/variations/tableaux',
        'distractor': 'Tableau de variations incomplet : oubli systématique des valeurs aux bornes '
                      'B(0) = −20, B(5) = 80, B(6) = 70. Pénalité barème : −0,5 pt.',
    },
    '3':  {
        'notion': 'Traduction concrète du maximum (500 articles, 80 000 €)',
        'capacite_bo': 'Résoudre un problème d\'optimisation et interpréter dans le contexte',
        'automatisme_bo': None,
        'rag_subtheme': 'analyse/optimisation/contextualisation',
        'distractor': 'Faiblesse de traduction concrète : l\'élève trouve x = 5 mais ne traduit pas '
                      'en 500 articles et 80 000 €. Symptôme d\'un déficit d\'interprétation contextuelle.',
    },
    '4.a': {
        'notion': 'Vérification factorisation B(x) = (x−1)(−x²+5x+20)',
        'capacite_bo': 'Vérifier une factorisation par développement',
        'automatisme_bo': 'Développer, factoriser un polynôme',
        'rag_subtheme': 'algebre/factorisation/polynomes',
        'distractor': None,
    },
    '4.b': {
        'notion': 'Plage de rentabilité B(x) ≥ 0 sur [0 ; 6]',
        'capacite_bo': 'Résoudre une inéquation produit de facteurs — signe d\'un produit',
        'automatisme_bo': 'Signe d\'une expression factorisée du second degré',
        'rag_subtheme': 'analyse/inequations/signe_produit',
        'distractor': 'Les élèves résolvent −x²+5x+20 ≥ 0 alors que l\'énoncé l\'admet. '
                      'Déficit de lecture des admis dans la consigne. '
                      'Plage attendue : [1 ; 6] (facteur (x−1) ≥ 0 sur [1 ; 6]).',
    },
    # ── Exercice 3 : Suites ──
    'Ex3_1': {
        'notion': 'u₁ = 2660 et interprétation 2025',
        'capacite_bo': 'Calculer les premiers termes d\'une suite définie par récurrence',
        'automatisme_bo': 'Suites définies par récurrence — calcul de termes',
        'rag_subtheme': 'algebre/suites/recurrence',
        'distractor': None,
    },
    'Ex3_2a': {
        'notion': '(vₙ) géométrique de raison 1,02 — démonstration',
        'capacite_bo': 'Démontrer qu\'une suite est géométrique — montrer vₙ₊₁/vₙ = constante',
        'automatisme_bo': 'Suites géométriques — terme général et raison',
        'rag_subtheme': 'algebre/suites/geometriques',
        'distractor': 'Se contenter de calculer v₁/v₀ au lieu d\'établir vₙ₊₁ = 1,02·vₙ pour tout n. '
                      'La démonstration générale est exigée par le barème.',
    },
    'Ex3_2b': {
        'notion': 'Forme explicite uₙ = 20 000 − 17 000 × 1,02ⁿ',
        'capacite_bo': 'Exprimer le terme général d\'une suite à partir de la suite auxiliaire',
        'automatisme_bo': 'Suites géométriques — forme explicite',
        'rag_subtheme': 'algebre/suites/geometriques',
        'distractor': None,
    },
    'Ex3_3a': {
        'notion': 'uₙ₊₁ − uₙ = −340 × 1,02ⁿ (sens de variation)',
        'capacite_bo': 'Étudier le sens de variation d\'une suite par calcul de uₙ₊₁ − uₙ',
        'automatisme_bo': 'Sens de variation d\'une suite — signe de la différence',
        'rag_subtheme': 'algebre/suites/sens_variation',
        'distractor': 'Deux voies acceptées (forme explicite ou substitution directe) — '
                      'le barème les valide indistinctement. À mentionner dans le bilan.',
    },
    'Ex3_3b': {
        'notion': 'Conclusion : (uₙ) strictement décroissante',
        'capacite_bo': 'Conclure sur le sens de variation à partir du signe de uₙ₊₁ − uₙ',
        'automatisme_bo': 'Sens de variation — conclusion formelle',
        'rag_subtheme': 'algebre/suites/sens_variation',
        'distractor': None,
    },
    'Ex3_4': {
        'notion': 'Algorithme Python — boucle while u >= 1000',
        'capacite_bo': 'Écrire et analyser un algorithme de calcul de termes d\'une suite par boucle while',
        'automatisme_bo': None,
        'rag_subtheme': 'algorithmique/boucles_seuil',
        'distractor': 'Erreur prioritaire : while u > 1000 (strict) au lieu de while u >= 1000 (large). '
                      'Pénalité −0,15/0,25. Point de vigilance algorithmique pour la session 2027.',
    },
}

# Mapping grading_structure label → catalogue key
# Les labels dans la grading_structure sont: Q1..Q12, A.1..A.5, B.1..B.3, 1..4.b, 1..4 (Exercice 3)
# Les IDs Exercice 3 sont ambigus avec Exercice 2 (même labels 1,2...) — on résout par position
EAM_EXERCISE_LABEL_MAP: Dict[str, Dict[str, str]] = {
    'Exercice 1': {'A.1': 'A.1', 'A.2': 'A.2', 'A.3': 'A.3', 'A.4': 'A.4', 'A.5': 'A.5',
                   'B.1': 'B.1', 'B.2': 'B.2', 'B.3': 'B.3'},
    'Exercice 2': {'1': '1', '2': '2', '3': '3', '4.a': '4.a', '4.b': '4.b'},
    'Exercice 3': {'1': 'Ex3_1', '2.a': 'Ex3_2a', '2.b': 'Ex3_2b',
                   '3.a': 'Ex3_3a', '3.b': 'Ex3_3b', '4': 'Ex3_4'},
}

# ── Calendrier réel EAM 2026 (immuable) ─────────────────────────────────────
# Source : calendrier scolaire AEFE Tunis 2025-2026
EAM_CALENDAR = {
    'bilan_restitution': '2026-05-04',          # lundi — rentrée vacances de printemps
    'remediation_start': '2026-05-04',          # 4 mai : premier jour remédiation encadrée
    'remediation_end': '2026-05-29',            # 29 mai : dernier jour séances encadrées
    'remediation_jours_ouvres': 15,             # ≈ 15 jours ouvrés
    'revision_autonome_start': '2026-05-30',    # 30 mai
    'revision_autonome_end': '2026-06-07',      # 7 juin
    'revision_autonome_jours': 10,              # 10 jours
    'epreuve_officielle': '2026-06-08',         # lundi 8 juin : EAM session 2026
    'qcm_blanc_cible': '2026-05-18',            # Semaine du 18 mai : QCM blanc 12 items
    'dst_eam': '2026-05-27',                    # Semaine du 25 mai : DST type EAM 1h
    'concertation_equipe': '2026-05-11',        # Semaine du 11 ou 18 mai (15 min)
}

# Encadré méthodologique v2.2 — texte verbatim §2 du brief (CHEINE/CHAHED autonomie)
EAM_METHODOLOGICAL_NOTE = (
    "Le présent bilan exploite exclusivement les 189 copies dématérialisées sur la plateforme Korrigo "
    "et corrigées de manière anonyme par les enseignants de mathématiques de Première Générale "
    "ayant adhéré au protocole numérique. "
    "M. Sidi CHEINE et Mme Imen CHAHED ont choisi de corriger les copies de leurs propres élèves "
    "au format papier, au stylo rouge, sans passer par la plateforme. "
    "Ce choix professionnel est respecté et relève de leur autonomie pédagogique. "
    "Les copies et les résultats issus de cette correction papier ne sont donc pas intégrés au présent bilan : "
    "les indicateurs, taux de réussite et analyses qui suivent décrivent uniquement le périmètre Korrigo "
    "et ne sauraient être interprétés comme une photographie complète de la promotion de Première Générale. "
    "Une consolidation manuelle pourrait être envisagée ultérieurement, sur la base des notes papier transmises, "
    "à l'initiative des collègues concernés."
)

# Mention classes hors périmètre pour S1/S7 — §7 du brief (sans noms propres dans tableau)
EAM_HORS_PERIMETRE_NOTE = (
    "Deux groupes de Première Générale ne figurent pas dans l'analyse comparative ci-dessous, "
    "leurs enseignants ayant opté pour une correction papier hors plateforme. "
    "Les classes prises en compte représentent 189 copies sur l'effectif total de Première Générale."
)

# Trois leviers prioritaires verbatim §6 du brief — v2.3 : 7 items corrects (Q11 exclu >35%, Ex3 Q3.a ajouté)
EAM_TROIS_LEVIERS = [
    (
        "Remédiation ciblée sur les sept items strictement inférieurs à 35 % de réussite "
        "(Ex2 Q4.b à 18,5 %, Ex3 Q4 à 21,7 %, QCM Q10 à 28,6 %, Ex2 Q3 à 29,1 %, "
        "Ex3 Q3.a à 30,2 %, Ex2 Q2 à 31,2 %, Ex1 B.3 à 32,8 %), "
        "encadrée sur la fenêtre 4 → 29 mai 2026, pilotée par l'équipe de Première "
        "lors de la concertation [C1]."
    ),
    (
        "Trois ateliers de raisonnement et rédaction sur les exercices "
        "Ex1 B.3, Ex2 Q2 / Q4.b, Ex3 Q3 / Q4, intégrés aux séances ordinaires."
    ),
    (
        "Pack de révision autonome distribué le 29 mai 2026 "
        "(corrigé commenté, fiches méthode, annales, QCM auto-corrigés), "
        "pour la fenêtre 30 mai → 7 juin."
    ),
]

# Bloc C statique verbatim brief v2.2 (zéro LLM — noms propres interdits dans les recommandations)
EAM_BLOC_C_STATIC = {
    'title': 'Pilotage Pédagogique',
    'fenetre': '4 → 29 mai 2026',
    'grille_formative': None,
    'recommandations': [
        {
            'id': 'C1',
            'titre': 'Concertation d\'équipe sur les items déficitaires',
            'action': (
                "Passer en revue collégialement les sept items dont le taux de réussite est strictement inférieur à 35 % "
                "(Ex2 Q4.b 18,5 %, Ex3 Q4 21,7 %, QCM Q10 28,6 %, Ex2 Q3 29,1 %, "
                "Ex3 Q3.a 30,2 %, Ex2 Q2 31,2 %, Ex1 B.3 32,8 %) "
                "et arbitrer la priorité d'action pour la fenêtre 4 → 29 mai."
            ),
            'modalite': (
                "Un seul créneau de 20 à 30 minutes en fin de réunion d'équipe de Première, "
                "semaine du 11 ou du 18 mai 2026. Support : tableau de bord Korrigo projeté."
            ),
            'observable': (
                "Compte rendu d'une page archivé dans le cahier de continuité du Labo Maths, "
                "listant la priorisation retenue et la répartition des actions de Phase 1."
            ),
        },
        {
            'id': 'C2',
            'titre': 'Suivi nominatif des élèves sous 8/20',
            'action': (
                "Produire la liste nominative des élèves obtenant un score strictement inférieur à 8/20 "
                "sur les copies Korrigo, et identifier ceux pour lesquels un suivi individualisé "
                "est pertinent d'ici l'épreuve officielle."
            ),
            'modalite': (
                "Extraction automatisée depuis Korrigo, validation par l'équipe de Première "
                "lors de la concertation [C1], transmission aux familles sous couvert du professeur principal "
                "de chaque groupe concerné, avant le 22 mai 2026."
            ),
            'observable': (
                "Nombre d'élèves identifiés, nombre de familles effectivement contactées, "
                "taux de retour, archivés dans le cahier de continuité."
            ),
        },
        {
            'id': 'C3',
            'titre': 'Mise à disposition des ressources Korrigo pour la promotion entière',
            'action': (
                "Rendre accessibles, sur simple demande, le barème harmonisé, les fiches d'erreurs typiques "
                "et les copies-types anonymisées à tous les enseignants de Première Générale, "
                "y compris ceux ayant opté pour une correction papier."
            ),
            'modalite': (
                "Dépôt dans le dossier partagé du Labo Maths la semaine du 11 mai 2026, "
                "communication par e-mail interne, sans sollicitation individuelle."
            ),
            'observable': (
                "Nombre de téléchargements ou de consultations sur la période 11 mai → 8 juin, "
                "sans nominatif."
            ),
        },
    ],
}

# Grille formative Bloc B — citée une seule fois, référencée ensuite
EAM_GRILLE_FORMATIVE_B = {
    'titre': 'Grille formative commune — Bloc B (3 ateliers)',
    'criteres': [
        'Identification de la propriété ou du théorème mobilisé',
        'Formulation explicite des hypothèses utilisées',
        'Enchaînement logique des étapes (pas de saut de raisonnement)',
        'Conclusion rédigée complète (valeur numérique + unité + interprétation si contextualisée)',
    ],
    'niveaux': ['Maîtrisé', 'Partiel', 'Non maîtrisé'],
    'usage': 'Grille commune aux ateliers B1, B2 et B3. Référence dans chaque recommandation : « cf. grille formative — tête de Bloc B ».',
}

# Encart calendrier synthétique (S1 — 3 lignes)
EAM_CALENDAR_NOTE = (
    "Bilan restitué le 4 mai 2026 à la rentrée des vacances de printemps. "
    "Période de remédiation encadrée : 4 → 29 mai (15 jours ouvrés). "
    "Révision autonome : 30 mai → 7 juin. Épreuve officielle : lundi 8 juin 2026."
)

# Table des matières v2.1
EAM_TABLE_OF_CONTENTS = [
    {'num': 1,  'title': 'Page de garde et méthodologie (avec encart calendrier)'},
    {'num': 2,  'title': 'Synthèse exécutive'},
    {'num': 3,  'title': 'Tableau de bord visuel'},
    {'num': 4,  'title': 'Analyse Partie A — Automatismes'},
    {'num': 5,  'title': 'Analyse Partie B — exercice par exercice'},
    {'num': 6,  'title': 'Cartographie des erreurs récurrentes'},
    {'num': 7,  'title': 'Analyse par classe'},
    {'num': 8,  'title': 'Recommandations différenciées (Blocs A, B, C — 4 → 29 mai)'},
    {'num': 9,  'title': 'Plan d\'action 4 mai → 8 juin 2026 (Phase 1, Phase 2, Phase 3)'},
    {'num': 10, 'title': 'Annexes (A1 à A6)'},
    {'num': 11, 'title': 'Anticipation Terminale Spécialité Mathématiques'},
    {'num': 12, 'title': 'Note de transmission'},
]

# Premium system prompt for EAM v2.2 — règles dures nominatives intégrées
EAM_PREMIUM_SYSTEM_PROMPT = """Tu es un inspecteur pédagogique de mathématiques en lycée français de l'AEFE. \
Tu rédiges un bilan post-épreuve à destination d'enseignants agrégés et certifiés expérimentés et de la direction d'un lycée. \
Style sobre, factuel, dense. Aucune envolée, aucun superlatif (pas de "remarquable", "solide", "encourageant", "satisfaisant"). \
Chaque affirmation s'appuie soit sur un chiffre fourni, soit sur une capacité du BO citée explicitement, \
soit sur une ressource pédagogique identifiée. \
Maximum 3 paragraphes par sous-section. \
Vocabulaire attendu : cohorte, item, capacité attendue, automatisme, remédiation différenciée, erreur typique, consolidation. \
Tu ne compares jamais avec d'autres établissements. \
Tu ne mentionnes jamais d'effectif que tu n'as pas reçu en entrée. \
INTERDIT ABSOLU — NOMS PROPRES : Aucun nom propre d'enseignant, de chef d'établissement ou d'inspecteur ne doit apparaître dans ta réponse. \
Tous les acteurs sont désignés génériquement : l'enseignant, l'équipe de Première, le professeur référent, le correcteur principal. \
N'invente aucun nom. Tout nom absent des données fournies est une hallucination — supprime-le. \
INTERDIT ABSOLU — RUBRIQUES : Aucune rubrique "Classes exclues", "Groupes hors périmètre", "Enseignants non participants" ou équivalente. \
INTERDIT ABSOLU — CALENDRIER : Toute date hors de la fenêtre 4 mai → 29 mai (Phase 1) ou 30 mai → 7 juin (Phase 2) est interdite. \
INTERDIT ABSOLU — TERMES DNB : DNB, brevet, cycle 4, 3e, troisième, collège, diplôme national du brevet. \
INTERDIT ABSOLU — RÉFÉRENCES RELATIVES : Toute référence temporelle doit être ancrée par une date absolue (jour ou semaine du JJ mois 2026). \
Les formulations "en semaine N", "dans X semaines", "les 8 prochaines semaines", "huit semaines", "à la rentrée prochaine" sont interdites. \
INTERDIT ABSOLU — CIBLES SANS DISPOSITIF : Toute cible chiffrée ("objectif 80%", "taux cible de 75%") doit être associée à un dispositif d'évaluation \
explicitement programmé dans la fenêtre 4 → 29 mai (date précise) ou à l'épreuve officielle du 8 juin. \
Toute cible sans dispositif identifié est interdite — la remplacer par un observable qualitatif daté."""


def validate_no_name_hallucinations(text: str) -> Tuple[bool, List[str]]:
    """
    v2.2 — Validate that LLM-generated text contains no unauthorized proper names.

    Authorized appearances (in static fields, not in LLM content):
    - 'CHEINE' and 'CHAHED': only allowed in EAM_METHODOLOGICAL_NOTE and EAM_HORS_PERIMETRE_NOTE
    - 'BEN RHOUMA': only in S12 (static, not LLM-generated)

    For LLM-generated text, ALL occurrences of these names are forbidden.
    Additionally, 'BEN TIBA' is a known hallucination — always forbidden.

    Returns:
        (is_valid, forbidden_names_found)
    """
    forbidden_names = [
        r'\bCHEINE\b',
        r'\bCHAHED\b',
        r'\bBEN TIBA\b',
        r'\bM\.\s+BEN\b',
        r'\bMme\s+BEN\b',
    ]
    found = []
    for pattern in forbidden_names:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(re.sub(r'\\b', '', pattern).strip())
    return (len(found) == 0, found)


def validate_no_dnb_references(text: str) -> Tuple[bool, List[str]]:
    """
    Validate that text contains no DNB/cycle 4 references.

    Uses word-boundary matching for context-sensitive terms to avoid false positives
    (e.g. "Troisième action" should NOT be flagged, but "3e" as class level should).

    Returns:
        (is_valid, forbidden_terms_found)
    """
    text_lower = text.lower()
    found = []
    for term, word_boundary in FORBIDDEN_TERMS:
        term_lower = term.lower()
        if word_boundary:
            # Unicode-aware word boundary: preceded/followed by non-letter/non-digit
            # re.UNICODE ensures accented chars (é, è, ...) are treated as word chars
            pattern = r'(?<![^\W])' + re.escape(term_lower) + r'(?![^\W])'
            if re.search(pattern, text_lower, re.UNICODE):
                found.append(term)
        else:
            if term_lower in text_lower:
                found.append(term)
    return len(found) == 0, found


class EamBilanOrchestrator:
    """
    Orchestrator dédié pour le bilan EAM BLANCHE (Première Spé Maths).
    Pipeline 100% isolé — aucune dépendance au pipeline DNB.
    """

    def __init__(self, exam_slug: str = 'EAM BLANCHE 2026'):
        self.exam_slug = exam_slug
        self.engine = AnalyticsEngine(exam_slug)
        self.rag_retriever = RAGRetriever(collection='rag_maths_premiere')
        # Parse EAM grading structure once
        self._automatismes_leaves, self._exercices_leaves = self._parse_eam_structure()

    # ─────────────────────────────────────────── structure EAM ─────────────────

    def _parse_eam_structure(self) -> Tuple[List[dict], List[dict]]:
        """
        Parse la structure barème EAM pour séparer :
        - Automatismes (nœud dont le label contient 'automatisme')
        - Exercices (tous les autres nœuds top-level)

        Returns:
            (automatismes_leaves, exercices_leaves)
        """
        gs = self.engine.grading_structure
        if not gs:
            return [], []

        auto_leaves: List[dict] = []
        exo_leaves: List[dict] = []

        for node in gs:
            label = str(
                node.get('label') or node.get('title') or node.get('name') or ''
            ).lower()
            leaves = extract_leaf_questions([node])
            if EAM_NODE_AUTOMATISMES in label:
                auto_leaves.extend(leaves)
            else:
                exo_leaves.extend(leaves)

        return auto_leaves, exo_leaves

    def _sum_for_leaves(self, scores_data: Dict, leaves: List[dict]) -> float:
        """Somme les points pour un ensemble de feuilles depuis scores_data."""
        return self.engine._sum_for_leaves(scores_data, leaves)

    def _max_for_leaves(self, leaves: List[dict]) -> float:
        """Calcule le barème max pour un ensemble de feuilles."""
        return self.engine._max_for_leaves(leaves)

    # ─────────────────────────────────────────── analytique EAM ────────────────

    def _compute_part_stats(
        self, leaves: List[dict], label: str
    ) -> Dict[str, Any]:
        """
        Calcule les stats (moyenne/médiane/std/taux) pour un sous-ensemble de feuilles.
        Utilisé pour les Automatismes et les Exercices.
        """
        pairs, _ = self.engine._scored_pairs()
        if not pairs or not leaves:
            return {}

        max_pts = self._max_for_leaves(leaves)
        scores = [self._sum_for_leaves(sd, leaves) for _, _, sd in pairs]

        if not scores:
            return {}

        n = len(scores)
        mean_v = statistics.mean(scores)
        median_v = statistics.median(scores)
        std_v = statistics.stdev(scores) if n > 1 else 0.0
        pct_above_half = (
            round(sum(1 for s in scores if s >= max_pts * 0.5) / n * 100, 1)
            if max_pts > 0 else 0.0
        )

        return {
            'label': label,
            'n_copies': n,
            'max_points': round(max_pts, 2),
            'mean': round(mean_v, 2),
            'mean_pct': round(mean_v / max_pts * 100, 1) if max_pts > 0 else 0.0,
            'median': round(median_v, 2),
            'std': round(std_v, 2),
            'min': round(min(scores), 2),
            'max': round(max(scores), 2),
            'pct_above_half': pct_above_half,
        }

    def _compute_question_stats_for_leaves(
        self, leaves: List[dict]
    ) -> List[Dict[str, Any]]:
        """Retourne les stats question-par-question pour un sous-ensemble de feuilles."""
        all_q = self.engine.stats_by_question()
        leaf_ids = {str(l.get('id') or '') for l in leaves}
        return [q for q in all_q if q.get('question', {}).get('id') in leaf_ids]

    def _build_exercise_details(self) -> List[Dict[str, Any]]:
        """
        Construit les détails par exercice (Exercice 1, 2, 3) avec stats
        par sous-partie basées sur la structure du barème EAM.
        """
        gs = self.engine.grading_structure or []
        pairs, _ = self.engine._scored_pairs()
        exercises = []

        for node in gs:
            label = str(
                node.get('label') or node.get('title') or node.get('name') or ''
            )
            label_lower = label.lower()
            if EAM_NODE_AUTOMATISMES in label_lower:
                continue  # skip Automatismes node

            node_leaves = extract_leaf_questions([node])
            if not node_leaves:
                continue

            max_pts = self._max_for_leaves(node_leaves)
            scores = [self._sum_for_leaves(sd, node_leaves) for _, _, sd in pairs]
            n = len(scores)
            mean_v = statistics.mean(scores) if scores else 0.0
            mean_pct = round(mean_v / max_pts * 100, 1) if max_pts > 0 else 0.0

            # Sub-parts = children of the node
            subparts = []
            for child in node.get('children') or []:
                child_label = str(
                    child.get('label') or child.get('title') or child.get('name') or child.get('id') or ''
                )
                child_leaves = extract_leaf_questions([child])
                child_max = self._max_for_leaves(child_leaves)
                child_scores = [
                    self._sum_for_leaves(sd, child_leaves) for _, _, sd in pairs
                ]
                child_mean = statistics.mean(child_scores) if child_scores else 0.0
                child_success = (
                    round(
                        sum(1 for s in child_scores if child_max > 0 and s >= 0.8 * child_max)
                        / len(child_scores) * 100,
                        1,
                    )
                    if child_scores and child_max > 0
                    else 0.0
                )
                subparts.append({
                    'id': child.get('id') or child_label,
                    'label': child_label,
                    'max_points': round(child_max, 2),
                    'mean_score': round(child_mean, 2),
                    'success_rate': child_success,
                    'n_attempts': len(child_scores),
                })

            exercises.append({
                'id': node.get('id') or label,
                'name': label,
                'max_points': round(max_pts, 2),
                'mean_score': round(mean_v, 2),
                'mean_pct': mean_pct,
                'n_copies': n,
                'subparts': subparts,
            })

        return exercises

    # ─────────────────────────────────────────── generate ──────────────────────

    def generate(self, scope: str = 'ETABLISSEMENT', class_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Génère le bilan EAM complet avec la structure S0-S4.
        Toutes les données sont issues de la DB réelle (copies FINALIZED).
        """
        logger.info(f"EamBilanOrchestrator: Generating bilan for {self.exam_slug}, scope={scope}")

        # Fetch analytics data
        global_stats = self.engine.global_stats()
        stats_by_question = self.engine.stats_by_question()
        stats_by_domain = self.engine.stats_by_domain()
        inter_corrector = self.engine.inter_corrector_analysis()
        stats_by_class = self.engine.stats_by_class()
        at_risk = self.engine.at_risk_students()

        # EAM-specific analytics
        auto_stats = self._compute_part_stats(self._automatismes_leaves, 'Automatismes')
        exo_stats = self._compute_part_stats(self._exercices_leaves, 'Exercices')
        auto_questions = self._compute_question_stats_for_leaves(self._automatismes_leaves)
        exo_questions = self._compute_question_stats_for_leaves(self._exercices_leaves)
        exercise_details = self._build_exercise_details()

        analytics = {
            'global_stats': global_stats,
            'stats_by_question': stats_by_question,
            'stats_by_domain': stats_by_domain,
            'inter_corrector': inter_corrector,
            'stats_by_class': stats_by_class,
            'at_risk': at_risk,
            'auto_stats': auto_stats,
            'exo_stats': exo_stats,
            'auto_questions': auto_questions,
            'exo_questions': exo_questions,
            'exercise_details': exercise_details,
        }

        report = {
            'exam_slug': self.exam_slug,
            'scope': scope,
            'class_id': class_id,
            'metadata': self._build_metadata(global_stats),
            'sections': {
                'S0': self._generate_s0_synthesis(analytics),
                'S1': self._generate_s1_dashboard(analytics),
                'S2A': self._generate_s2a_automatismes(analytics),
                'S2B': self._generate_s2b_exercices(analytics),
                'S3': self._generate_s3_questions(analytics),
                'S4': self._generate_s4_recommendations(analytics),
                'S5': self._generate_s5_mapping(analytics),
                'S11': self._generate_s11_terminale(analytics),
                'S12': self._generate_s12_note_transmission(),
            },
            'llm_model': f"{EAM_LLM_SYNTHESIS} / {EAM_LLM_ANALYSIS}",
            'rag_collection': self.rag_retriever.collection,
        }

        logger.info("EamBilanOrchestrator: Bilan generated successfully")
        return report

    # ─────────────────────────────────────────── metadata ──────────────────────

    def _build_metadata(self, global_stats: Dict) -> Dict[str, Any]:
        """Build enriched metadata — v2: adds classes list and excluded_classes note."""
        return {
            'n_copies': global_stats.get('n_copies', 0),
            'mean': global_stats.get('mean'),
            'median': global_stats.get('median'),
            'std': global_stats.get('std'),
            'min': global_stats.get('min'),
            'max': global_stats.get('max'),
            'pct_above_10': global_stats.get('pct_above_10', 0),
            'distribution': global_stats.get('distribution', {}),
            'data_quality': global_stats.get('data_quality', {}),
            'included_classes': EAM_INCLUDED_CLASSES,
            'excluded_teachers': EAM_EXCLUDED_TEACHERS,
            'excluded_note': EAM_EXCLUDED_NOTE,
            'calendar': EAM_CALENDAR,
            'calendar_note': EAM_CALENDAR_NOTE,
            'table_of_contents': EAM_TABLE_OF_CONTENTS,
            'bilan_version': 'v2.1',
        }

    # ─────────────────────────────────────────── sections ──────────────────────

    def _enrich_question_with_catalogue(self, q: Dict, exercise_name: Optional[str] = None) -> Dict:
        """
        Enrichit une question avec les données du catalogue officiel :
        libellé réel, capacité BO, automatisme, sous-thème RAG, distracteur.
        exercise_name permet de résoudre les ambiguïtés Exercice 2 vs Exercice 3.
        """
        info = q.get('question', {})
        raw_label = str(info.get('label') or info.get('number') or info.get('id') or '')

        # Determine catalogue key
        cat_key = None
        if exercise_name and exercise_name in EAM_EXERCISE_LABEL_MAP:
            cat_key = EAM_EXERCISE_LABEL_MAP[exercise_name].get(raw_label)
        else:
            # Automatismes: strip prefix 'Automatismes — Q1' -> 'Q1'
            stripped = raw_label.replace('Automatismes — ', '').strip()
            if stripped in EAM_QUESTION_CATALOGUE:
                cat_key = stripped

        cat = EAM_QUESTION_CATALOGUE.get(cat_key, {}) if cat_key else {}
        q_copy = dict(q)
        q_copy['question'] = dict(info)
        q_copy['question']['notion'] = cat.get('notion', '')
        q_copy['question']['capacite_bo'] = cat.get('capacite_bo', '')
        q_copy['question']['automatisme_bo'] = cat.get('automatisme_bo', '')
        q_copy['question']['rag_subtheme'] = cat.get('rag_subtheme', '')
        q_copy['distractor'] = cat.get('distractor')
        q_copy['catalogue_key'] = cat_key
        return q_copy

    def _enrich_stats_by_class(self, stats_by_class: List[Dict]) -> List[Dict]:
        """
        Enrichit stats_by_class avec partA_mean, partB_mean, pct_above_10 par classe.
        """
        pairs, _ = self.engine._scored_pairs()
        if not pairs:
            return stats_by_class

        # Build per-class index — class_name is on copy.student.class_name
        from collections import defaultdict
        class_buckets: Dict[str, List] = defaultdict(list)
        for copy, total, sd in pairs:
            try:
                cls = copy.student.class_name or ''
            except Exception:
                cls = ''
            if cls:
                auto_score = self._sum_for_leaves(sd, self._automatismes_leaves)
                exo_score = self._sum_for_leaves(sd, self._exercices_leaves)
                class_buckets[cls].append((total, auto_score, exo_score))

        enriched = []
        for cls_stat in stats_by_class:
            cls_name = cls_stat.get('class_name', '')
            bucket = class_buckets.get(cls_name, [])
            enriched_stat = dict(cls_stat)
            if bucket:
                totals, autos, exos = zip(*bucket)
                n = len(totals)
                auto_max = self._max_for_leaves(self._automatismes_leaves)
                exo_max = self._max_for_leaves(self._exercices_leaves)
                enriched_stat['partA_mean'] = round(statistics.mean(autos), 2)
                enriched_stat['partA_mean_pct'] = round(statistics.mean(autos) / auto_max * 100, 1) if auto_max else 0.0
                enriched_stat['partB_mean'] = round(statistics.mean(exos), 2)
                enriched_stat['partB_mean_pct'] = round(statistics.mean(exos) / exo_max * 100, 1) if exo_max else 0.0
                enriched_stat['pct_above_10'] = round(sum(1 for t in totals if t >= 10) / n * 100, 1)
            enriched.append(enriched_stat)

        return sorted(enriched, key=lambda c: c.get('mean', 0))

    def _generate_s0_synthesis(self, analytics: Dict) -> Dict[str, Any]:
        """S0 — Synthèse exécutive premium : 5 puces denses + encadré Cheine/Chahed."""
        logger.info("EamBilanOrchestrator: Generating S0 synthesis v2")

        gs = analytics['global_stats']
        auto = analytics.get('auto_stats', {})
        exo = analytics.get('exo_stats', {})
        n = gs.get('n_copies', 189)
        mean = gs.get('mean', 'N/A')
        median = gs.get('median', 'N/A')
        std = gs.get('std', 'N/A')
        pct10 = gs.get('pct_above_10', 'N/A')
        auto_pct = auto.get('mean_pct', 67.5)
        exo_pct = exo.get('mean_pct', 58.2)
        diff = round(auto_pct - exo_pct, 1)

        rag_ctx = self.rag_retriever.search(
            query="épreuve anticipée mathématiques première bilan pédagogique résultats cohorte",
            top_k=3,
        )

        prompt = f"""Contexte : bilan post-correction de l'épreuve anticipée de mathématiques (EAM), Première Générale Spécialité Maths, lycée Pierre Mendès France Tunis.
Échantillon : {n} copies dématérialisées (classes 1.01 à 1.10). Deux groupes hors périmètre (correction papier hors plateforme).

DONNÉES STATISTIQUES (source : export Korrigo, traçables) :
- Moyenne : {mean}/20 | Médiane : {median}/20 | Écart-type : {std}
- Taux ≥ 10/20 : {pct10}%
- Partie A (Automatismes, 6 pts) : {auto.get('mean','N/A')}/6 = {auto_pct}% du barème
- Partie B (Exercices, 14 pts) : {exo.get('mean','N/A')}/14 = {exo_pct}% du barème
- Écart A−B : {diff} points de pourcentage
- Items ≥ 90% réussite (Partie A) : Q1 (92,1%), Q4 (90,5%), Q5 (96,8%)
- Items ≤ 30% réussite : Q10 (28,6%), Ex2 Q4.b (18,5%), Ex3 Q4 (21,7%)

RESSOURCES PÉDAGOGIQUES (RAG) :
{rag_ctx}

CALENDRIER RÉEL (non modifiable) :
- Remédiation encadrée : 4 → 29 mai 2026 (15 jours ouvrés, 3,5 semaines)
- Révision autonome : 30 mai → 7 juin 2026 (10 jours, sans séances)
- Épreuve officielle : lundi 8 juin 2026

MISSION :
Rédige une synthèse exécutive factuelle en 5 à 6 phrases courtes (pas de superlatifs, pas de métaphores).
N'emploie aucun nom propre d'enseignant. Désigne les acteurs génériquement : l'enseignant, l'équipe de Première.
Enchaine avec exactement 3 leviers prioritaires numérotés 1, 2, 3, reproduits mot pour mot :
1. Remédiation ciblée sur les six items < 35 % de réussite (Q10, Q11, Ex1 B.3, Ex2 Q2, Ex2 Q3, Ex2 Q4.b, Ex3 Q4), encadrée sur la fenêtre 4 → 29 mai, pilotée par l'équipe de Première lors de la concertation [C1].
2. Trois ateliers de raisonnement et rédaction sur les exercices Ex1 B.3, Ex2 Q2 / Q4.b, Ex3 Q3 / Q4, intégrés aux séances ordinaires.
3. Pack de révision autonome distribué le 29 mai 2026 (corrigé commenté, fiches méthode, annales, QCM auto-corrigés), pour la fenêtre 30 mai → 7 juin.
LIGNES INTERDITES : 'EAM blanche n°2', tout nom propre d'enseignant, 'M. BEN TIBA', 'Classes exclues', 'Groupes hors périmètre', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'globalement satisfaisant', 'solide', 'bonne dynamique', 'remarquable', 'encourageant'.
Toute date citée doit être réelle et appartenir à l'intervalle 4 mai → 8 juin 2026."""

        text = self._generate_with_validation(prompt, EAM_LLM_SYNTHESIS, max_tokens=800,
                                               system_prompt_override=EAM_PREMIUM_SYSTEM_PROMPT)

        return {
            'type': 'synthesis',
            'title': 'Synthèse Exécutive',
            'content': text,
            'methodological_note': EAM_METHODOLOGICAL_NOTE,
            'trois_leviers': EAM_TROIS_LEVIERS,
            'excluded_note': EAM_EXCLUDED_NOTE,
            'stats_snapshot': {
                'n_copies': n,
                'mean': mean,
                'median': median,
                'std': std,
                'pct_above_10': pct10,
                'auto_mean_pct': auto_pct,
                'exo_mean_pct': exo_pct,
                'diff_pct': diff,
            },
        }

    def _generate_s1_dashboard(self, analytics: Dict) -> Dict[str, Any]:
        """S1 — Tableau de bord v2 : stats globales enrichies + stats_by_class avec partA/partB."""
        logger.info("EamBilanOrchestrator: Generating S1 dashboard v2")

        auto = analytics.get('auto_stats', {})
        exo = analytics.get('exo_stats', {})

        comparison: Dict[str, Any] = {}
        if auto and exo:
            auto_pct = auto.get('mean_pct', 0)
            exo_pct = exo.get('mean_pct', 0)
            diff = round(auto_pct - exo_pct, 1)
            comparison = {
                'auto_mean_pct': auto_pct,
                'exo_mean_pct': exo_pct,
                'diff_pct': diff,
                'stronger_part': 'Automatismes' if auto_pct >= exo_pct else 'Exercices',
                'weaker_part': 'Exercices' if auto_pct >= exo_pct else 'Automatismes',
                'interpretation': (
                    f"L'écart de {diff} points de pourcentage entre Partie A ({auto_pct}%) "
                    f"et Partie B ({exo_pct}%) s'explique mécaniquement : les items "
                    "d'automatismes (QCM 0,5 pt chacun) pénalisent moins la note globale "
                    "qu'une sous-partie d'exercice manquée (1 à 1,5 pt). "
                    "Un élève ayant raté B.3 (1 pt) perd autant que sur 2 QCM entiers."
                ),
            }

        # Enrich stats_by_class with partA/partB
        enriched_classes = self._enrich_stats_by_class(analytics.get('stats_by_class', []))

        return {
            'type': 'dashboard',
            'title': 'Tableau de Bord',
            'global_stats': analytics['global_stats'],
            'automatismes_stats': auto,
            'exercices_stats': exo,
            'comparison': comparison,
            'stats_by_class': enriched_classes,
            'inter_corrector': analytics.get('inter_corrector', []),
            'at_risk_count': len(analytics.get('at_risk', [])),
            'excluded_note': EAM_EXCLUDED_NOTE,
            'hors_perimetre_note': EAM_HORS_PERIMETRE_NOTE,
        }

    def _generate_s2a_automatismes(self, analytics: Dict) -> Dict[str, Any]:
        """S2A v2 — Automatismes : libellés réels + distracteurs + micro-rituels."""
        logger.info("EamBilanOrchestrator: Generating S2A Automatismes v2")

        raw_qs = analytics.get('auto_questions', [])
        auto_stats = analytics.get('auto_stats', {})

        # Enrich with catalogue data
        auto_qs = [self._enrich_question_with_catalogue(q) for q in raw_qs]

        sorted_qs = sorted(auto_qs, key=lambda q: q.get('success_rate', 0), reverse=True)
        top_success = sorted_qs[:3]
        top_failures = sorted_qs[-3:][::-1]

        # Questions sous 60% avec distracteurs
        weak_qs = [q for q in auto_qs if (q.get('success_rate') or 100) < 60]

        rag_ctx = self.rag_retriever.search(
            query="automatismes QCM mathématiques Première calcul algébrique taux évolution trigonométrie suites",
            top_k=4,
        )

        def fmt_q_premium(q: Dict) -> str:
            info = q.get('question', {})
            lbl = info.get('label', '?')
            notion = info.get('notion', '')
            cap = info.get('capacite_bo', '')
            rate = q.get('success_rate', 0)
            dist = q.get('distractor', '')
            line = f"- {lbl} ({notion}) : taux {rate}% | Capacité BO : {cap}"
            if dist:
                line += f"\n  Erreur typique : {dist}"
            return line

        top_s_text = "\n".join(fmt_q_premium(q) for q in top_success)
        top_f_text = "\n".join(fmt_q_premium(q) for q in top_failures)
        weak_text = "\n".join(fmt_q_premium(q) for q in weak_qs)

        prompt = f"""Bilan EAM — Partie A : Automatismes (12 QCM, 6 points — barème 12 × 0,5 pt).
Échantillon : 189 copies, Première Générale Spécialité Mathématiques.

STATISTIQUES PARTIE A :
- Moyenne : {auto_stats.get('mean','N/A')}/6 ({auto_stats.get('mean_pct','N/A')}% du barème)
- Médiane : {auto_stats.get('median','N/A')}/6 | Écart-type : {auto_stats.get('std','N/A')}
- % ≥ 3/6 : {auto_stats.get('pct_above_half','N/A')}%

TOP 3 RÉUSSITES :
{top_s_text}

TOP 3 DIFFICULTÉS :
{top_f_text}

ITEMS SOUS 60% AVEC DISTRACTEURS IDENTIFIÉS :
{weak_text}

RESSOURCES PÉDAGOGIQUES (RAG) :
{rag_ctx}

MISSION :
Paragraphe 1 (3 lignes max) : analyse factuelle des réussites — citer les capacités BO maîtrisées.
Paragraphe 2 (4 lignes max) : analyse des difficultés item par item — nommer chaque distracteur identifié.
Paragraphe 3 : proposer 3 micro-rituels d'automatismes (5 min en début de séance, format QCM concret) 
ciblés sur Q2 (taux réciproque), Q10 (image d'intervalle par x²), Q11 (somme géométrique).
Chaque rituel = 1 phrase : fréquence, durée, format, objectif chiffré."""

        text = self._generate_with_validation(prompt, EAM_LLM_ANALYSIS, max_tokens=1100,
                                               system_prompt_override=EAM_PREMIUM_SYSTEM_PROMPT)

        return {
            'type': 'automatismes',
            'title': 'Automatismes (Partie A — 12 QCM, 6 pts)',
            'content': text,
            'stats': auto_stats,
            'questions': auto_qs,
            'top_success': top_success,
            'top_failures': top_failures,
        }

    def _generate_s2b_exercices(self, analytics: Dict) -> Dict[str, Any]:
        """S2B v2 — Exercices : max_points/mean_score corrigés + erreurs typiques par exercice."""
        logger.info("EamBilanOrchestrator: Generating S2B Exercices v2")

        exercise_details = analytics.get('exercise_details', [])
        exo_stats = analytics.get('exo_stats', {})

        # Exercise-specific RAG queries
        rag_probas = self.rag_retriever.search(
            query="probabilités conditionnelles variable aléatoire espérance jeu équitable Première", top_k=3)
        rag_optim = self.rag_retriever.search(
            query="optimisation dérivée tableau variations second degré contexte Première", top_k=3)
        rag_suites = self.rag_retriever.search(
            query="suites géométriques algorithme Python boucle while sens de variation Première", top_k=3)

        rag_by_ex = {
            'Exercice 1': rag_probas,
            'Exercice 2': rag_optim,
            'Exercice 3': rag_suites,
        }

        # Exercise-specific error analysis from catalogue
        ex_context = {
            'Exercice 1': (
                "Erreurs typiques identifiées dans la cohorte :\n"
                "1. Confusion P_F(S) / P_S(F) en A.4 (taux 55%) — interversion numérateur/dénominateur.\n"
                "2. Indépendance conclue sans calcul comparatif explicite en A.5 (taux 58,7%).\n"
                "3. Loi de X incomplète en B.1 (taux 65,1%) — oubli de P(X=−2)=0,8 et confusion gains bruts/nets.\n"
                "4. Espérance avec gains bruts en B.2 (taux 60,8%) — E(X) erroné de +2 unités.\n"
                "5. Équation E(Y)=0 mal posée en B.3 (taux 32,8%) — facteur (−t) omis sur les 80% de cas non gagnants."
            ),
            'Exercice 2': (
                "Erreurs typiques identifiées dans la cohorte :\n"
                "1. Tableau de variations incomplet en Q2 (taux 31,2%) — valeurs aux bornes B(0)=−20, B(5)=80, B(6)=70 omises.\n"
                "2. Traduction concrète absente en Q3 (taux 29,1%) — x=5 trouvé mais non traduit en 500 articles et 80 000 €.\n"
                "3. Q4.b (taux 18,5%) — résolution de −x²+5x+20≥0 alors que l'énoncé l'admet ; déficit de lecture des admis."
            ),
            'Exercice 3': (
                "Erreurs typiques identifiées dans la cohorte :\n"
                "1. Q2.a (taux 41,8%) — calcul de v₁/v₀ au lieu de démonstration générale vₙ₊₁=1,02·vₙ.\n"
                "2. Q3.a (taux 30,2%) — deux voies acceptées (forme explicite ou substitution) ; à signaler aux élèves.\n"
                "3. Q4 (taux 21,7%) — while u > 1000 (strict) au lieu de while u >= 1000 (large) ; pénalité −0,15/0,25."
            ),
        }

        exercise_analyses = []
        for ex in exercise_details:
            ex_name = ex.get('name', 'Exercice')
            max_pts = ex.get('max_points', 0)
            mean_sc = ex.get('mean_score', 0)
            mean_pct = ex.get('mean_pct', 0)
            subparts = ex.get('subparts', [])

            # Enrich subparts with catalogue
            ex_label_map = EAM_EXERCISE_LABEL_MAP.get(ex_name, {})
            enriched_subparts = []
            for sp in subparts:
                sp_label = str(sp.get('label') or sp.get('id') or '')
                cat_key = ex_label_map.get(sp_label)
                cat = EAM_QUESTION_CATALOGUE.get(cat_key, {}) if cat_key else {}
                sp_enriched = dict(sp)
                sp_enriched['notion'] = cat.get('notion', '')
                sp_enriched['capacite_bo'] = cat.get('capacite_bo', '')
                sp_enriched['distractor'] = cat.get('distractor')
                enriched_subparts.append(sp_enriched)

            subparts_text = self._format_subparts_premium(enriched_subparts)
            rag_ctx = rag_by_ex.get(ex_name, '')
            err_ctx = ex_context.get(ex_name, '')

            prompt = f"""Bilan EAM — {ex_name} (Partie B — Raisonnement et Rédaction).
Échantillon : 189 copies, Première Générale Spécialité Mathématiques.

STATISTIQUES {ex_name.upper()} :
- Maximum : {max_pts} pts | Moyenne : {mean_sc} pts ({mean_pct}% du barème)
- Copies analysées : {ex.get('n_copies', 189)}

DÉTAIL PAR SOUS-PARTIE (notion + capacité BO + taux réussite) :
{subparts_text}

{err_ctx}

RESSOURCES PÉDAGOGIQUES (RAG) :
{rag_ctx}

MISSION :
Paragraphe 1 : analyse des résultats par sous-partie — identifier les ruptures de progression (ex : chute B.2→B.3).
Paragraphe 2 : hypothèse principale sur l'erreur la plus fréquente — formuler une piste de diagnostic terrain.
Paragraphe 3 — intitulé OBLIGATOIRE « Leviers méthodologiques sur la fenêtre de remédiation 4 → 29 mai 2026 » : \
2 leviers concrets, chacun avec un indicateur observable associé à un dispositif daté dans la fenêtre 4 → 29 mai 2026.

Paragraphe 4 — intitulé OBLIGATOIRE « Prolongement en révision autonome (30 mai → 7 juin) » : \
lister les ressources du Pack EAM pour cet exercice : fiche méthode ciblée sur les erreurs typiques identifiées, \
QCM auto-corrigé de 6 à 8 questions, sujet d'annale corrigé sur les notions de cet exercice.

INTERDIT : '8 prochaines semaines', 'huit semaines', 'semaine N' non ancré par une date, cibles chiffrées sans dispositif programmé."""

            text = self._generate_with_validation(prompt, EAM_LLM_ANALYSIS, max_tokens=2048,
                                                   system_prompt_override=EAM_PREMIUM_SYSTEM_PROMPT)
            exercise_analyses.append({
                'id': ex.get('id'),
                'name': ex_name,
                'analysis': text,
                'max_points': max_pts,
                'mean_score': mean_sc,
                'mean_pct': mean_pct,
                'subparts': enriched_subparts,
            })

        return {
            'type': 'exercices',
            'title': 'Exercices de Raisonnement (Partie B — 14 pts)',
            'exercices_stats': exo_stats,
            'exercises': exercise_analyses,
        }

    def _generate_s3_questions(self, analytics: Dict) -> Dict[str, Any]:
        """S3 — Tableau complet question-par-question (Automatismes + Exercices)."""
        logger.info("EamBilanOrchestrator: Generating S3 questions table")

        all_questions = analytics.get('stats_by_question', [])

        return {
            'type': 'questions_table',
            'title': 'Analyse Question par Question',
            'questions': all_questions,
            'n_questions': len(all_questions),
            'auto_questions': analytics.get('auto_questions', []),
            'exo_questions': analytics.get('exo_questions', []),
        }

    def _generate_s4_recommendations(self, analytics: Dict) -> Dict[str, Any]:
        """S4 v2.1 — Recommandations recadrées sur 4 → 29 mai 2026 (15 jours ouvrés)."""
        logger.info("EamBilanOrchestrator: Generating S4 recommendations v2.1")

        gs = analytics['global_stats']
        auto = analytics.get('auto_stats', {})
        exo = analytics.get('exo_stats', {})
        pct10 = gs.get('pct_above_10', 67.2)
        n_sous_8 = round(189 * (1 - pct10 / 100))

        rag_auto = self.rag_retriever.search(
            query="entraînement automatismes QCM rituel Première taux évolution trigonométrie suites", top_k=3)
        rag_raison = self.rag_retriever.search(
            query="rédaction preuve démonstration exercice raisonnement démarche Première", top_k=3)
        rag_pilotage = self.rag_retriever.search(
            query="pilotage pédagogique suivi élèves progression évaluation formative lycée", top_k=3)

        # ── Bloc A — Automatismes (4 → 29 mai) ──
        prompt_a = f"""Contexte : bilan EAM Première Générale, 189 copies, lycée Pierre Mendès France Tunis.
Partie A (Automatismes, 6 pts) : moyenne {auto.get('mean','N/A')}/6 ({auto.get('mean_pct','N/A')}%).
Fenêtre opérationnelle : 4 → 29 mai 2026 (15 jours ouvrés, 3,5 semaines). Épreuve officielle : 8 juin 2026.
Volume réaliste : 6 à 8 séquences de 10 minutes, 2 par semaine (rituel en début de séance ordinaire).

Items PRIORITAIRES (non négociables) :
- Q2 (35,4%) : taux d'évolution réciproque — confusion avec taux opposé
- Q10 (28,6%) : image de [−3;2[ par x² — oubli du minimum en 0
- Q11 (38,6%) : somme géométrique — confusion avec terme général

Items de consolidation si temps disponible : Q6 (valeurs exactes sin/cos), Q8 (dérivée de 1/x).

INDICATEURS OBSERVABLES À UTILISER (verbatim, non modifiables) :
- Pour Q10 : Production écrite individuelle de 5 phrases de définition courte sur image d'intervalle par x², évaluée selon une grille à 3 niveaux : exact / partiel / erroné.
- Pour Q11 : Score au QCM ciblé de 6 questions sur sommes géométriques, administré la semaine du 25 mai 2026.
- Pour Q2 (et ensemble Partie A) : Score au QCM blanc de 12 items administré la semaine du 18 mai 2026, à comparer au score Partie A initial (4,05/6).

RESSOURCES :
{rag_auto}

Rédige le Bloc [A] — Automatismes : 3 recommandations (une par item prioritaire).
Format pour chaque :
  Action : [description — 1 phrase — préciser l'acteur génériquement (l'enseignant / l'équipe) et QUAND (date exacte dans 4 → 29 mai)]
  Modalité : [format exact, durée, fréquence]
  Indicateur observable : [reprendre mot pour mot l'indicateur fourni ci-dessus pour cet item]
INTERDIT : tout nom propre d'enseignant, 'M. BEN TIBA', 'EAM blanche n°2', 'Classes exclues', 'cahier de suivi individuel', 'qualité des interactions orales', 'appropriation des techniques', dates hors 4 → 29 mai, semaines abstraites 'S1'.."""

        # ── Bloc B — Raisonnement (4 → 29 mai) ──
        prompt_b = f"""Contexte : bilan EAM Première Générale, 189 copies.
Partie B (Exercices, 14 pts) : moyenne {exo.get('mean','N/A')}/14 ({exo.get('mean_pct','N/A')}%).
Fenêtre : 4 → 29 mai 2026 (15 jours ouvrés). Épreuve officielle : 8 juin 2026.
Volume réaliste : 3 ateliers de 30 à 45 minutes intégrés à des séances ordinaires.
1 devoir en temps libre unique : sujet type EAM, 1 h, restitué semaine du 25 mai.

GRILLE FORMATIVE COMMUNE (à citer une SEULE FOIS en tête du Bloc B, puis référencer par «cf. grille formative — tête de Bloc B») :
1. Identification de la propriété ou du théorème mobilisé
2. Formulation explicite des hypothèses utilisées
3. Enchaînement logique des étapes (pas de saut de raisonnement)
4. Conclusion rédigée complète (valeur numérique + unité + interprétation si contextualisée)

ATELIERS — cibles par ordre de retour sur investissement :
- Atelier B1 (semaine 11 → 15 mai, 45 min) : Ex1 B.1→B.3, loi de X avec gain net, espérance, équation E(Y)=0 (32,8%)
- Atelier B2 (semaine 18 → 22 mai, 45 min) : Ex2 Q2 (tableau de variations complet avec bornes) et Q4.b (signe de produit, facteur admis positif)
- Atelier B3 (semaine 19 → 20 mai, 30 min) : Ex3 Q3 (sens de variation suite récurrente) et Q4 (condition boucle while >=) — observable : devoir restitué semaine du 25 mai

RESSOURCES :
{rag_raison}

Rédige le Bloc [B] — Raisonnement et Rédaction.
Commence par un paragraphe «Grille formative commune» reproduisant les 4 critères.
Ensuite, 3 recommandations (B1, B2, B3), une par atelier.
Format pour chaque recommandation :
  Action : [description — 1 phrase — acteur générique (l'enseignant), date exacte dans 4 → 29 mai]
  Modalité : [copies-types anonymisées, durée]
  Grille formative : cf. grille formative — tête de Bloc B
  Observable : [production écrite observable ou score daté précisément — ex : taux de respect du canevas en 4 critères sur les copies rendues le 25 mai]
INTERDIT : tout nom propre d'enseignant, 'M. BEN TIBA', dupliquer la grille formative, 'Classes exclues', semaines abstraites 'S1'-'S8', dates hors 4 → 29 mai."""

        block_a = self._generate_with_validation(prompt_a, EAM_LLM_SYNTHESIS, max_tokens=650,
                                                   system_prompt_override=EAM_PREMIUM_SYSTEM_PROMPT)
        block_b = self._generate_with_validation(prompt_b, EAM_LLM_SYNTHESIS, max_tokens=750,
                                                   system_prompt_override=EAM_PREMIUM_SYSTEM_PROMPT)
        # Bloc C — statique verbatim brief v2.2 (zéro LLM — supprime hallucinations nominatives)
        block_c = EAM_BLOC_C_STATIC['recommandations']

        # Plan phases (remplace plan_8_semaines) — structuré sur le calendrier réel
        plan_phases = {
            'phase1': {
                'titre': 'Phase 1 — Remédiation encadrée',
                'periode': '4 → 29 mai 2026',
                'jours_ouvres': 15,
                'semaines': [
                    {
                        'label': 'Semaine 1 (4 → 8 mai)',
                        'focus': 'Restitution bilan aux élèves + Q10 et Q11 (automatismes)',
                        'modalite': 'Séance dédiée + 2 rituels 10 min',
                        'livrable': 'Fiche élève « 5 questions à ne plus rater »',
                    },
                    {
                        'label': 'Semaine 2 (11 → 15 mai)',
                        'focus': 'Ex1 B.1 → B.3 (variable aléatoire et jeu équitable)',
                        'modalite': '1 atelier 45 min + 2 rituels',
                        'livrable': 'Exercice d\'application en temps libre',
                    },
                    {
                        'label': 'Semaine 3 (18 → 22 mai)',
                        'focus': 'Ex2 Q2 et Q4.b (tableau de variations complet, signe d\'un produit) + QCM blanc',
                        'modalite': '1 atelier 45 min + QCM blanc 12 items',
                        'livrable': 'Score QCM blanc relevé (sans cible chiffrée)',
                    },
                    {
                        'label': 'Semaine 4 (25 → 29 mai)',
                        'focus': 'Ex3 Q3 et Q4 (variation d\'une suite, boucle while >=) + DST 1h type EAM',
                        'modalite': '1 atelier 30 min + DST + correction collective',
                        'livrable': 'Note DST + grille critères rédaction',
                    },
                ],
                'tampon': 'Prévoir un slot tampon par semaine (sortie, jour férié, devoir autre discipline).',
            },
            'phase2': {
                'titre': 'Phase 2 — Révision autonome',
                'periode': '30 mai → 7 juin 2026',
                'jours': 10,
                'pack_contenu': [
                    'Corrigé officiel commenté du sujet EAM blanche',
                    '4 fiches méthode courtes (1 page) ciblées sur les 5 items les plus discriminants',
                    '1 sujet d\'annales corrigé par chapitre : probabilités, optimisation, suites, trigonométrie',
                    '3 listes QCM avec corrigé immédiat (50 questions au total)',
                ],
                'pack_livraison': '29 mai — e-mail Pronote + dépôt Korrigo',
                'permanence': 'Forum Nexus Réussite EAM 2026 — réponses sous 24h — 30 mai → 7 juin',
                'recommandation_eleves': (
                    '45 minutes par jour : QCM (15 min) + exercice rédigé (20 min) + auto-correction (10 min). '
                    'La veille du 8 juin consacrée au repos. Ne pas excéder ce volume.'
                ),
            },
            'phase3': {
                'titre': 'Phase 3 — Continuité vers la Terminale',
                'periode': 'Rentrée septembre 2026',
                'note': 'Phase pour mémoire — ne s\'exécute pas sur la fenêtre du bilan. Voir Section 11.',
                'action': 'Alimenter le cahier de continuité pédagogique de l\'équipe à partir de la Section 11.',
            },
        }

        return {
            'type': 'recommendations',
            'title': 'Recommandations Différenciées (4 → 29 mai 2026)',
            'section_num': 8,
            'blocks': {
                'A': {
                    'title': 'Automatismes',
                    'content': block_a,
                    'fenetre': '4 → 29 mai 2026',
                    'volume': '6 à 8 séquences de 10 min, 2/semaine',
                    'items_prioritaires': ['Q2 (taux réciproque)', 'Q10 (image intervalle)', 'Q11 (somme géométrique)'],
                    'observable': 'QCM blanc 12 items — semaine du 18 mai 2026',
                },
                'B': {
                    'title': 'Raisonnement et Rédaction',
                    'content': block_b,
                    'grille_formative': EAM_GRILLE_FORMATIVE_B,
                    'fenetre': '4 → 29 mai 2026',
                    'volume': '3 ateliers 30-45 min + 1 DST 1h (semaine du 25 mai)',
                    'cibles': ['Ex1 B.1→B.3', 'Ex2 Q2 et Q4.b', 'Ex3 Q3 et Q4'],
                    'observable': 'Note DST type EAM — semaine du 25 mai 2026',
                },
                'C': {
                    'title': 'Pilotage Pédagogique',
                    'content': None,
                    'recommandations': block_c,
                    'fenetre': '4 → 29 mai 2026',
                    'volume': '1 concertation 20-30 min — semaine du 11 ou 18 mai',
                    'ressources_korrigo': 'Mise à disposition volontaire — dépôt Labo Maths semaine du 11 mai',
                    'observable': 'CR une page archivé cahier continuité + liste élèves < 8/20 avant 22 mai',
                },
            },
            'plan_phases': plan_phases,
        }

    def _generate_s5_mapping(self, analytics: Dict) -> Dict[str, Any]:
        """S5 — Table correspondance question ↔ programme BO ↔ sous-thème RAG (31 items)."""
        logger.info("EamBilanOrchestrator: Generating S5 question mapping")

        all_q = analytics.get('stats_by_question', [])
        table_rows = []

        for q in all_q:
            info = q.get('question', {})
            raw_label = str(info.get('label') or info.get('number') or info.get('id') or '')

            # Labels follow pattern: 'Automatismes — Q1', 'Exercice 1 — A.1', 'Exercice 3 — 2.a'
            cat_key = None
            if raw_label.startswith('Automatismes — '):
                sub_label = raw_label.replace('Automatismes — ', '').strip()
                cat_key = sub_label if sub_label in EAM_QUESTION_CATALOGUE else None
            else:
                # Parse 'Exercice N — sub_label'
                import re as _re
                m = _re.match(r'^(Exercice \d+)\s*[—-]\s*(.+)$', raw_label)
                if m:
                    ex_name = m.group(1).strip()
                    sub_label = m.group(2).strip()
                    lbl_map = EAM_EXERCISE_LABEL_MAP.get(ex_name, {})
                    cat_key = lbl_map.get(sub_label)
                else:
                    # Fallback: bare label (legacy format)
                    stripped = raw_label.strip()
                    if stripped in EAM_QUESTION_CATALOGUE:
                        cat_key = stripped

            cat = EAM_QUESTION_CATALOGUE.get(cat_key, {}) if cat_key else {}
            display_id = cat_key or raw_label.replace('Automatismes — ', '').strip()

            table_rows.append({
                'id_question': display_id,
                'notion': cat.get('notion', '[Non référencé]'),
                'capacite_bo': cat.get('capacite_bo', ''),
                'automatisme_bo': cat.get('automatisme_bo', ''),
                'rag_subtheme': cat.get('rag_subtheme', ''),
                'success_rate': q.get('success_rate'),
                'mean_score': q.get('mean_score'),
                'max_points': info.get('max_points'),
                'distractor': cat.get('distractor'),
            })

        return {
            'type': 'question_mapping',
            'title': 'Table Correspondance Question ↔ Programme BO ↔ RAG',
            'n_items': len(table_rows),
            'rows': table_rows,
        }

    def _generate_s11_terminale(self, analytics: Dict) -> Dict[str, Any]:
        """S11 — Anticipation Terminale Spécialité Mathématiques.
        5 domaines × 3 éléments : pré-requis observé, compétence Terminale, recommandation passerelle.
        Aucun objectif chiffré pour la Terminale — observables uniquement.
        """
        logger.info("EamBilanOrchestrator: Generating S11 Terminale anticipation")

        rag_suites = self.rag_retriever.search(
            query="suites récurrence convergence géométrique arithmétique Terminale Première", top_k=3)
        rag_probas = self.rag_retriever.search(
            query="loi binomiale espérance variable aléatoire probabilités Terminale", top_k=3)
        rag_derivation = self.rag_retriever.search(
            query="dérivation fonctions composées convexité exponentielle logarithme Terminale", top_k=3)
        rag_trigo = self.rag_retriever.search(
            query="équations trigonométriques cosinus sinus cercle Terminale dérivation", top_k=3)
        rag_algo = self.rag_retriever.search(
            query="algorithmique Python dichotomie Monte-Carlo listes boucle while Terminale", top_k=3)

        # Données d'ancrage par domaine (chiffrées, traçables)
        domain_data = {
            'suites': {
                'prereqs_obs': (
                    "Ex3 Q3.a : 30,2% — démonstration générale vₙ₊₁=1,02·vₙ non produite (calcul v₁/v₀ seulement). "
                    "Ex3 Q3.b : 36,0% — conclusion sur le sens de variation sans signe de la différence. "
                    "Ex3 Q4 : 21,7% — boucle while >= confondue avec while >."
                ),
                'competences_terminale': (
                    "BO Terminale : raisonnement par récurrence (attendu en Terminale, non au programme Première) ; "
                    "étude de la convergence d'une suite (lien suite/limite) ; "
                    "suites définies implicitement ; lien suites / fonctions exponentielles."
                ),
                'recommandation': (
                    "Prévoir 2 séances de réactivation en septembre 2026 sur les suites géométriques et arithmétiques, "
                    "avec focus sur la rédaction d'une démonstration de suite géométrique "
                    "(« montrer que (vₙ) est géométrique ») avant d'introduire le raisonnement par récurrence formalisé."
                ),
                'rag': rag_suites,
            },
            'probabilites': {
                'prereqs_obs': (
                    "Ex1 A.4 : 55,0% — confusion P_F(S) / P_S(F). "
                    "Ex1 A.5 : 58,7% — indépendance conclue sans calcul comparatif P(F∩S) vs P(F)·P(S). "
                    "Ex1 B.1 : 65,1% — loi de X incomplète, confusion gains bruts/nets. "
                    "Ex1 B.2 : 60,8% — espérance calculée avec gains bruts (+2 unités d'erreur). "
                    "Ex1 B.3 : 32,8% — équation E(Y)=0 mal posée, facteur (−t) omis."
                ),
                'competences_terminale': (
                    "BO Terminale : loi binomiale B(n,p) — modèle et calculs ; "
                    "espérance et variance d'une variable aléatoire discrète ; "
                    "somme de variables aléatoires indépendantes ; "
                    "concentration (inégalité de Bienaymé-Tchebychev) ; "
                    "échantillonnage et intervalle de fluctuation."
                ),
                'recommandation': (
                    "La maîtrise de la modélisation par variable aléatoire en Première conditionne directement "
                    "la loi binomiale en Terminale. Prévoir un test diagnostique en septembre 2026 "
                    "portant sur la loi de probabilité, l'espérance et l'indépendance, "
                    "puis cibler les remédiations sur les élèves sous 60% à ce test."
                ),
                'rag': rag_probas,
            },
            'derivation': {
                'prereqs_obs': (
                    "Ex2 Q1 : 66,1% — calcul de B'(x) et factorisation corrects. "
                    "Ex2 Q2 : 31,2% — tableau de variations incomplet (bornes B(0)=−20, B(5)=80, B(6)=70 omises). "
                    "Ex2 Q3 : 29,1% — x=5 trouvé mais non traduit en 500 articles et 80 000 €. "
                    "Ex2 Q4.b : 18,5% — lecture du signe d'un produit dont un facteur est admis positif par l'énoncé."
                ),
                'competences_terminale': (
                    "BO Terminale : dérivées des fonctions composées ; dérivée seconde et convexité ; "
                    "étude complète des fonctions exponentielle et logarithme ; "
                    "optimisation contextualisée avec modélisation ; "
                    "primitives et calcul intégral."
                ),
                'recommandation': (
                    "La rigueur du tableau de variations (bornes calculées, signe documenté) doit être un acquis "
                    "avant l'étude des fonctions exponentielle et logarithme en Terminale. "
                    "Distribuer à la rentrée une fiche méthode « tableau de variations en 5 étapes » "
                    "et l'exiger sur tous les devoirs jusqu'aux vacances de la Toussaint 2026."
                ),
                'rag': rag_derivation,
            },
            'trigonometrie': {
                'prereqs_obs': (
                    "Q6 : 60,3% — valeurs exactes sin(π/4), cos(2π/3) ; erreur de signe sur cos(2π/3)=−1/2. "
                    "Q7 : 73,5% — image de 13π/4 sur le cercle (deux réponses acceptées au barème)."
                ),
                'competences_terminale': (
                    "BO Terminale : équations trigonométriques (cos x = a et sin x = a) sur un intervalle donné ; "
                    "dérivation de cos et sin ; lien avec les fonctions périodiques et leur représentation."
                ),
                'recommandation': (
                    "Produire avant l'été une fiche « valeurs remarquables et angles associés » (recto-verso A4), "
                    "à imposer en début de Terminale avec interrogation orale rapide (5 items, 5 minutes) "
                    "en début de séance, jusqu'à atteindre la maîtrise de la table complète."
                ),
                'rag': rag_trigo,
            },
            'algorithmique': {
                'prereqs_obs': (
                    "Ex3 Q4 : 21,7% — confusion while u > 1000 (strict) / while u >= 1000 (large) ; "
                    "structure générale de la boucle correctement engagée par une partie de la cohorte."
                ),
                'competences_terminale': (
                    "BO Terminale : algorithmique sur les suites (calcul de seuils et termes) ; "
                    "méthode de dichotomie pour la résolution approchée d'équations ; "
                    "simulation Monte-Carlo en probabilités ; "
                    "manipulation de listes Python (append, len, indexation)."
                ),
                'recommandation': (
                    "Intégrer dès septembre 2026 un rituel hebdomadaire de 10 minutes de Python "
                    "en début de séance (alternance avec les rituels d'automatismes), "
                    "focalisé sur les boucles while à condition d'arrêt, les boucles for indexées "
                    "et la manipulation de listes. La dichotomie nécessitera une séance complète dédiée."
                ),
                'rag': rag_algo,
            },
        }

        # LLM prompt : un bloc par domaine, 3 éléments, sans objectif chiffré Terminale
        domain_prompt_template = """Bilan EAM Première Générale — Section Anticipation Terminale.
Domaine : {domaine}

PRÉ-REQUIS OBSERVÉS SUR L'EAM (données réelles, non modifiables) :
{prereqs_obs}

COMPÉTENCES TERMINALE CONCERNÉES (BO Terminale) :
{competences_terminale}

RECOMMANDATION PASSERELLE PRÉVUE :
{recommandation}

RESSOURCES RAG :
{rag}

MISSION : Rédige un encadré structuré en 3 parties pour le domaine "{domaine}" :
1. « Pré-requis observés sur l'EAM » : synthèse factuelle des items (citer les taux chiffrés fournis).
2. « Compétences attendues en Terminale » : reprendre les capacités BO fournies, en 2-3 lignes.
3. « Recommandation passerelle » : développer la recommandation fournie en 3-4 lignes concrètes.
CONTRAINTES : aucun objectif chiffré pour la Terminale. Seuls des observables. Pas de superlatif."""

        domains = []
        domain_labels = {
            'suites': 'Suites numériques',
            'probabilites': 'Probabilités et variable aléatoire',
            'derivation': 'Dérivation et étude de fonctions',
            'trigonometrie': 'Trigonométrie',
            'algorithmique': 'Algorithmique et programmation Python',
        }

        for key, data in domain_data.items():
            prompt = domain_prompt_template.format(
                domaine=domain_labels[key],
                prereqs_obs=data['prereqs_obs'],
                competences_terminale=data['competences_terminale'],
                recommandation=data['recommandation'],
                rag=data['rag'],
            )
            text = self._generate_with_validation(
                prompt, EAM_LLM_ANALYSIS, max_tokens=2048,
                system_prompt_override=EAM_PREMIUM_SYSTEM_PROMPT)

            domains.append({
                'key': key,
                'titre': domain_labels[key],
                'prereqs_obs': data['prereqs_obs'],
                'competences_terminale': data['competences_terminale'],
                'recommandation': data['recommandation'],
                'content': text,
            })

        # Note interne équipe Terminale (statique)
        note_interne = (
            "Note interne — Équipe Terminale Spécialité Mathématiques 2026-2027. "
            "Ce document identifie les fragilités observées sur la cohorte de Première Générale "
            "lors de l'EAM blanche du 4 mai 2026 (189 copies, barème harmonisé). "
            "Il est transmis à titre de continuité pédagogique ; les chiffres cités sont issus "
            "de la correction Korrigo et sont disponibles sur demande auprès du correcteur principal. "
            "Aucun objectif de résultat n'est fixé pour la Terminale : ce document documente des "
            "observables, non des engagements. À archiver dans le cahier de continuité pédagogique."
        )

        # Validation des termes requis par le brief v2.1
        required_terms = ['récurrence', 'loi binomiale', 'convexité',
                          'équations trigonométriques', 'dichotomie']
        full_text = ' '.join(d['content'] for d in domains)
        full_text += ' '.join(d['prereqs_obs'] + d['competences_terminale']
                              for d in domains)
        coverage = {t: (t.lower() in full_text.lower()) for t in required_terms}
        missing = [t for t, found in coverage.items() if not found]
        if missing:
            logger.warning(f"S11 missing required terms: {missing}")

        return {
            'type': 'terminale_anticipation',
            'title': 'Anticipation Terminale Spécialité Mathématiques',
            'section_num': 11,
            'domaines': domains,
            'n_domaines': len(domains),
            'terms_coverage': coverage,
            'note_interne': note_interne,
        }

    def _generate_s12_note_transmission(self) -> Dict[str, Any]:
        """S12 — Note de transmission correcteur principal (statique — ½ page)."""
        logger.info("EamBilanOrchestrator: Generating S12 note transmission")

        note = (
            "Le présent bilan a été produit dans la fenêtre 4 → 10 mai 2026 à partir de 189 copies "
            "dématérialisées via la plateforme Korrigo (lycée Pierre Mendès France, Tunis). "
            "Il est destiné à orienter les 15 derniers jours ouvrés de remédiation encadrée "
            "avant l'épreuve officielle du 8 juin 2026. "
            "La consolidation des copies papier corrigées par M. Sidi CHEINE et Mme Imen CHAHED "
            "reste à organiser hors plateforme et n'altère pas la lecture des items présentés ici. "
            "La continuité avec la classe de Terminale fera l'objet d'une note séparée "
            "transmise à l'équipe pédagogique de septembre 2026."
        )

        return {
            'type': 'note_transmission',
            'title': 'Note de Transmission',
            'section_num': 12,
            'auteur': 'Alaeddine Ben Rhouma — Correcteur principal',
            'date_production': '4 → 10 mai 2026',
            'content': note,
        }

    # ─────────────────────────────────────────── LLM + validation ──────────────

    @staticmethod
    def _is_complete(text: str) -> bool:
        """v2.3 — Vérifie que le texte se termine par une ponctuation forte (phrase non tronquée)."""
        stripped = text.rstrip()
        if not stripped:
            return False
        return stripped[-1] in '.!?:»)'

    def _generate_with_validation(
        self, prompt: str, model: str, max_tokens: int = 1000, max_retries: int = 3,
        system_prompt_override: Optional[str] = None
    ) -> str:
        """Generate text with anti-DNB + anti-name + anti-truncation validation and retry logic."""
        active_system = system_prompt_override or EAM_SYSTEM_PROMPT
        for attempt in range(max_retries):
            try:
                text = write(prompt, max_tokens=max_tokens, model=model, system_prompt=active_system)

                # v2.2 dual validation: DNB terms + nominative hallucinations
                is_dnb_ok, forbidden_dnb = validate_no_dnb_references(text)
                is_name_ok, forbidden_names = validate_no_name_hallucinations(text)
                all_forbidden = forbidden_dnb + forbidden_names

                # v2.3 anti-truncation check
                is_complete = self._is_complete(text)

                if is_dnb_ok and is_name_ok and is_complete:
                    return text

                if not is_complete:
                    logger.warning(
                        f"EamBilanOrchestrator: Truncated output (attempt {attempt + 1}/{max_retries}), "
                        f"last char: {repr(text.rstrip()[-1]) if text.rstrip() else 'EMPTY'}"
                    )
                if all_forbidden:
                    logger.warning(
                        f"EamBilanOrchestrator: Forbidden content (attempt {attempt + 1}/{max_retries}): "
                        f"DNB={forbidden_dnb} Names={forbidden_names}"
                    )

                if attempt < max_retries - 1:
                    addendum = "\n\nATTENTION :"
                    if not is_complete:
                        addendum += " Ta réponse précédente était incomplète (phrase tronquée). Termine la phrase précédente, puis continue normalement."
                    if all_forbidden:
                        addendum += (
                            " Ta réponse contenait des éléments interdits. Reformule sans employer : "
                            + ", ".join(all_forbidden)
                            + ". N'invente aucun nom propre. Désigne les acteurs génériquement."
                        )
                    prompt = prompt + addendum
                else:
                    logger.error(
                        f"EamBilanOrchestrator: Max retries exceeded. "
                        f"Forbidden={all_forbidden} Complete={is_complete}"
                    )
                    return text

            except Exception as e:
                logger.error(
                    f"EamBilanOrchestrator: Error attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt == max_retries - 1:
                    raise

        return ""

    # ─────────────────────────────────────────── formatters ────────────────────

    def _format_stats_text(self, analytics: Dict) -> str:
        """Format les stats globales + EAM pour les prompts LLM."""
        gs = analytics.get('global_stats', {})
        auto = analytics.get('auto_stats', {})
        exo = analytics.get('exo_stats', {})

        lines = [
            f"Copies analysées : {gs.get('n_copies', 0)}",
            f"Moyenne générale : {gs.get('mean', 'N/A')}/20 ({gs.get('pct_above_10', 'N/A')}% ≥ 10)",
            f"Médiane : {gs.get('median', 'N/A')}/20 | Écart-type : {gs.get('std', 'N/A')}",
            f"Min : {gs.get('min', 'N/A')} | Max : {gs.get('max', 'N/A')}",
        ]
        if auto:
            lines.append(
                f"Automatismes (6 pts) : moy={auto.get('mean', 'N/A')} "
                f"({auto.get('mean_pct', 'N/A')}% du barème)"
            )
        if exo:
            lines.append(
                f"Exercices (14 pts) : moy={exo.get('mean', 'N/A')} "
                f"({exo.get('mean_pct', 'N/A')}% du barème)"
            )
        return "\n".join(lines)

    def _format_question_list(self, questions: List[Dict]) -> str:
        """Format une liste de questions pour les prompts."""
        if not questions:
            return "Aucune donnée"
        lines = []
        for q in questions:
            info = q.get('question', {})
            label = info.get('label') or info.get('number') or info.get('id', '?')
            lines.append(
                f"- {label} : taux réussite {q.get('success_rate', 0)}%, "
                f"moyenne {q.get('mean_score', 0)}/{info.get('max_points', '?')}"
            )
        return "\n".join(lines)

    def _format_subparts_text(self, subparts: List[Dict]) -> str:
        """Format les sous-parties d'un exercice pour les prompts."""
        if not subparts:
            return "Aucune sous-partie disponible"
        lines = []
        for sp in subparts:
            lines.append(
                f"- {sp.get('label', sp.get('id', '?'))} : "
                f"moy={sp.get('mean_score', 0)}/{sp.get('max_points', '?')} pts | "
                f"réussite={sp.get('success_rate', 0)}%"
            )
        return "\n".join(lines)

    def _format_subparts_premium(self, subparts: List[Dict]) -> str:
        """Format enrichi sous-parties avec notion et capacité BO pour prompts premium."""
        if not subparts:
            return "Aucune sous-partie disponible"
        lines = []
        for sp in subparts:
            lbl = sp.get('label', sp.get('id', '?'))
            notion = sp.get('notion', '')
            cap = sp.get('capacite_bo', '')
            rate = sp.get('success_rate', 0)
            mean = sp.get('mean_score', 0)
            pts = sp.get('max_points', '?')
            dist = sp.get('distractor', '')
            line = f"- {lbl} ({notion}) : moy={mean}/{pts} pts | réussite={rate}% | Capacité : {cap}"
            if dist:
                line += f"\n    Erreur typique : {dist}"
            lines.append(line)
        return "\n".join(lines)
