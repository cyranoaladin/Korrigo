export const BLOCK_OPTIONS = [
  'Chargement des pages PDF',
  'Placement précis des annotations',
  'Saisie des scores dans le barème',
  "Anonymat (difficile de se repérer)",
  'Navigation entre les copies',
  'Connexion réseau instable',
  'Rien — la correction était fluide'
]

export const UTILITY_LEVELS = ['Inutile', 'Utile', 'Indispensable']

export const TOOL_QUESTION_IDS = ['q21', 'q22', 'q23', 'q24']

export const ERGONOMICS_QUESTION_IDS = ['q11', 'q12', 'q13', 'q14']

export const QUESTIONNAIRE_SECTIONS = [
  {
    id: 's1',
    title: 'Ergonomie & Prise en main',
    sub: "Évaluez votre expérience de l'interface de correction (1 = très négatif, 5 = excellent).",
    questions: [
      { id: 'q11', type: 'lk', req: true, label: "Clarté générale de l'interface du Bureau de Correction", low: 'Très confuse', high: 'Très claire' },
      { id: 'q12', type: 'lk', req: true, label: 'Navigation entre les copies et les pages PDF', low: 'Très difficile', high: 'Très fluide' },
      { id: 'q13', type: 'lk', req: true, label: 'Utilisation du barème interactif (panneau latéral)', low: 'Difficile à maîtriser', high: 'Parfaitement intuitif' },
      { id: 'q14', type: 'lk', req: true, label: 'Fluidité du zoom et du déplacement sur les copies', low: 'Lent / saccadé', high: 'Très réactif' },
      { id: 'q15', type: 'ro', req: true, label: "Combien de temps avant de vous sentir à l'aise avec l'interface ?", opts: ['Moins de 15 minutes', '15 à 30 minutes', '30 minutes à 1 heure', "Plus d'1 heure", "Je ne me suis jamais vraiment senti(e) à l'aise"] }
    ]
  },
  {
    id: 's2',
    title: 'Outils de correction',
    sub: "Évaluez l'utilité de chaque fonctionnalité de votre point de vue.",
    questions: [
      { id: 'q21', type: 'ut', req: true, label: 'Annotation / commentaire avec retrait ou ajout de points' },
      { id: 'q22', type: 'ut', req: true, label: 'Surlignage de passages' },
      { id: 'q23', type: 'ut', req: true, label: 'Raccourcis clavier (navigation, zoom)' },
      { id: 'q24', type: 'ut', req: true, label: 'Banque de commentaires personnels (auto-complétion)' },
      { id: 'q25', type: 'ck', req: false, label: "Qu'est-ce qui vous a le plus ralenti lors de la correction ?", note: 'Plusieurs réponses possibles.', opts: BLOCK_OPTIONS },
      { id: 'q25b', type: 'ta', req: false, label: 'Autre frein non listé (optionnel)', ph: 'Décrivez un obstacle spécifique rencontré…' }
    ]
  },
  {
    id: 's3',
    title: 'Fiabilité & Incident du 26 février',
    sub: 'Votre ressenti sur la robustesse de la plateforme et la gestion de crise.',
    questions: [
      { id: 'q31', type: 'lk', req: true, label: 'Durant la correction : aviez-vous peur de perdre votre travail ?', low: 'Très inquiet(e)', high: 'Totalement serein(e)' },
      { id: 'q32', type: 'ro', req: true, label: "Suite à l'incident et à la récupération à 100 %, votre confiance dans Korrigo est :", opts: ['Renforcée — la récupération complète prouve la résilience', 'Inchangée — erreur humaine, pas un défaut structurel', 'Légèrement ébranlée — le risque zéro n\'existe pas', 'Sérieusement affectée — difficile de corriger sereinement'] },
      { id: 'q33', type: 'lk', req: true, label: 'Les mesures correctives (sauvegardes hors-site, monitoring) vous rassurent-elles ?', low: 'Pas du tout', high: 'Entièrement' },
      { id: 'q34', type: 'lk', req: true, label: 'La transparence du post-mortem publié a-t-elle été appréciée ?', low: 'Inutile / trop technique', high: 'Très appréciée / rassurante' }
    ]
  },
  {
    id: 's4',
    title: 'Impact pédagogique',
    sub: 'Comparaison avec la correction papier et effets sur vos pratiques.',
    questions: [
      { id: 'q41', type: 'lk', req: true, label: 'Comparé à la correction papier, Korrigo est :', low: 'Beaucoup plus chronophage', high: 'Gain de temps massif' },
      { id: 'q42', type: 'lk', req: true, label: 'Qualité des retours aux élèves (correction numérique vs papier) :', low: "Moins bien qu'en papier", high: 'Nettement meilleur' },
      { id: 'q43', type: 'ro', req: true, label: "L'anonymisation des copies a-t-elle influencé votre façon de corriger ?", opts: ['Oui, je me sens plus objectif(ve) sans voir le nom', "Peu d'effet — j'aurais corrigé pareil", "L'anonymat m'a parfois perturbé(e) (difficile de se repérer)", 'Difficile à évaluer sur un seul exercice'] },
      { id: 'q44', type: 'ro', req: true, label: 'Le numérique a-t-il modifié la rigueur de vos corrections ?', opts: ["Plus rigoureux(se) — les outils m'ont aidé à être plus précis(e)", 'Identique à la correction papier', "Moins rigoureux(se) — l'interface distrait ou fatigue"] }
    ]
  },
  {
    id: 's5',
    title: 'Recommandation & Avenir',
    sub: 'Votre vision pour la suite de Korrigo.',
    questions: [
      { id: 'q51', type: 'ro', req: true, label: 'Recommanderiez-vous Korrigo pour le prochain bac blanc ?', opts: ["Absolument — c'est l'avenir de la correction", 'Oui, avec quelques améliorations techniques', "Plutôt non — j'attends une version plus stable", 'Non — je reste sur la correction papier'] },
      { id: 'q52', type: 'ck', req: false, label: "Pour quels types d'évaluations Korrigo est-il le plus adapté ?", note: 'Plusieurs réponses possibles.', opts: ['Bac Blanc (examens importants)', 'Devoirs communs inter-classes', 'Contrôles continus', 'NSI / Projets numériques', 'Épreuves de fin de semestre'] },
      { id: 'q53', type: 'nps', req: true, label: "Sur une échelle de 0 à 10, recommanderiez-vous Korrigo à un collègue d'un autre lycée ?", note: '0 = certainement pas — 10 = absolument' },
      { id: 'q54', type: 'ta', req: false, label: 'La fonctionnalité qui manque le plus selon vous :', ph: 'Ex : export Pronote automatique, notifications élèves, suivi de progression...' },
      { id: 'q55', type: 'ta', req: false, label: 'Bug ou problème technique rencontré :', ph: "Décrivez le problème et dans quel contexte il s'est produit..." }
    ]
  },
  {
    id: 's6',
    title: 'Mot de la fin',
    sub: 'Votre bilan global.',
    questions: [
      { id: 'q61', type: 'ro', req: true, label: 'Votre sentiment global sur Korrigo après ce bac blanc :', opts: ['Enthousiaste — je suis convaincu(e) par l\'outil', 'Satisfait(e) — bon outil, quelques ajustements à faire', "Mitigé(e) — autant d'avantages que d'inconvénients", 'Déçu(e) — les promesses ne sont pas au rendez-vous', "Neutre — je n'ai pas d'opinion tranchée"] },
      { id: 'q62', type: 'ta', req: false, label: 'Commentaire libre, suggestion ou message pour Alaeddine :', ph: 'Tout ce que vous souhaitez partager...' }
    ]
  }
]

export const SENTIMENT_PREFIXES = ['Enthousiaste', 'Satisfait', 'Mitigé', 'Déçu', 'Neutre']

export const RECOMMENDATION_PREFIXES = ['Absolument', 'Oui, avec quelques', 'Plutôt non', 'Non']

export const TOOL_LABELS = {
  q21: 'Annotation / commentaires',
  q22: 'Surlignage',
  q23: 'Raccourcis clavier',
  q24: 'Banque commentaires'
}
