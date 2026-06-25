export const KORRIGO_PUBLIC_PAGE_KEYS = ['home', 'teacherGuide', 'studentGuide', 'direction']

export const KORRIGO_PUBLIC_ROUTE_SEGMENTS = {
  home: '',
  teacherGuide: 'guide-enseignant',
  studentGuide: 'guide-eleve',
  direction: 'direction',
}

export const KORRIGO_PUBLIC_ROUTES = [
  { key: 'home', label: 'Accueil', path: '/korrigo' },
  { key: 'teacherGuide', label: 'Guide enseignant', path: '/korrigo/guide-enseignant' },
  { key: 'studentGuide', label: 'Guide élève', path: '/korrigo/guide-eleve' },
  { key: 'direction', label: 'Direction et conformité', path: '/korrigo/direction' },
]

export const KORRIGO_PUBLIC_ROUTE_PATHS = KORRIGO_PUBLIC_ROUTES.map((route) => route.path)

export const KORRIGO_PUBLIC_ROUTE_BY_KEY = Object.fromEntries(
  KORRIGO_PUBLIC_ROUTES.map((route) => [route.key, route])
)

export const KORRIGO_LOGIN_LINKS = [
  { label: 'Enseignant', to: '/teacher/login', icon: 'teacher-pen' },
  { label: 'Élève', to: '/student/login', icon: 'student' },
  { label: 'Administration', to: '/admin/login', icon: 'admin' },
]

export const KORRIGO_COPY_STATUSES = [
  {
    label: 'Prête',
    code: 'READY',
    description: 'La copie est identifiée, assignée et disponible pour correction.',
  },
  {
    label: 'En cours',
    code: 'IN_PROGRESS',
    description: 'La correction est ouverte par un correcteur et protégée contre les modifications concurrentes.',
  },
  {
    label: 'Finalisée',
    code: 'FINALIZED',
    description: 'La correction est terminée et le PDF final est disponible selon les droits du profil connecté.',
  },
]

export const KORRIGO_PUBLIC_WORKFLOW = [
  'Créer ou préparer un examen.',
  'Importer les informations nécessaires et les copies scannées.',
  'Identifier les copies et vérifier les associations.',
  'Répartir les copies aux correcteurs.',
  'Corriger avec barème, annotations et sauvegarde.',
  'Finaliser les copies et générer les PDF finaux.',
  'Publier les résultats lorsque la direction ou l’administration le décide.',
  'Consulter les copies et exporter les éléments autorisés.',
]

export const KORRIGO_PUBLIC_PAGES = {
  home: {
    eyebrow: 'Plateforme de correction numérique',
    title: 'Korrigo',
    subtitle:
      'Korrigo accompagne la correction dématérialisée des examens, depuis l’import des copies scannées jusqu’à la consultation sécurisée des copies finalisées.',
    intro:
      'La plateforme organise les rôles, les copies, les statuts et les accès sans exposer de données nominatives sur les pages publiques.',
    ctas: [
      { label: 'Guide enseignant', to: KORRIGO_PUBLIC_ROUTE_BY_KEY.teacherGuide.path, icon: 'teacher-pen' },
      { label: 'Guide élève', to: KORRIGO_PUBLIC_ROUTE_BY_KEY.studentGuide.path, icon: 'student' },
      { label: 'Accès direction', to: KORRIGO_PUBLIC_ROUTE_BY_KEY.direction.path, icon: 'building' },
    ],
    sections: [
      {
        title: 'À qui s’adresse Korrigo ?',
        cards: [
          {
            title: 'Administration',
            icon: 'settings',
            text: 'Prépare les examens, gère les comptes, suit les imports et supervise les étapes de publication.',
          },
          {
            title: 'Enseignants',
            icon: 'edit',
            text: 'Corrigent les copies assignées avec un barème, des annotations et une finalisation contrôlée.',
          },
          {
            title: 'Élèves',
            icon: 'student',
            text: 'Consultent leurs copies finalisées et les documents disponibles depuis leur espace personnel.',
          },
          {
            title: 'Direction',
            icon: 'bar-chart-3',
            text: 'Suit l’avancement et consulte les vues autorisées par le périmètre configuré.',
          },
        ],
      },
      {
        title: 'Workflow de correction',
        body: 'Le workflow reste volontairement borné : préparation, import, identification, répartition, correction, finalisation, publication et consultation.',
        steps: KORRIGO_PUBLIC_WORKFLOW,
      },
      {
        title: 'Statuts principaux d’une copie',
        cards: KORRIGO_COPY_STATUSES.map((status) => ({
          title: `${status.label} (${status.code})`,
          icon: 'file-check',
          text: status.description,
        })),
      },
      {
        title: 'Principes de sécurité',
        cards: [
          {
            title: 'Accès par rôle',
            icon: 'lock',
            text: 'Les espaces enseignant, élève, direction et administration appliquent des droits distincts.',
          },
          {
            title: 'Correction humaine',
            icon: 'user-check',
            text: 'La notation reste effectuée par des correcteurs habilités.',
          },
          {
            title: 'Traçabilité',
            icon: 'clipboard',
            text: 'Les actions importantes de correction et d’administration sont suivies par l’application.',
          },
        ],
      },
    ],
  },
  teacherGuide: {
    eyebrow: 'Guide enseignant',
    title: 'Corriger avec Korrigo',
    subtitle:
      'Ce guide décrit le parcours enseignant sans utiliser de compte réel ni de donnée nominative.',
    intro:
      'Les fonctions visibles dépendent des examens assignés et du périmètre de votre compte.',
    ctas: [
      { label: 'Connexion enseignant', to: '/teacher/login', icon: 'login' },
      { label: 'Guide élève', to: KORRIGO_PUBLIC_ROUTE_BY_KEY.studentGuide.path, icon: 'student' },
    ],
    sections: [
      {
        title: 'Accès et tableau de bord',
        steps: [
          'Se connecter avec le compte fourni par l’établissement.',
          'Consulter les examens et lots de copies disponibles.',
          'Ouvrir une copie assignée depuis la liste de correction.',
        ],
      },
      {
        title: 'Correction',
        cards: [
          {
            title: 'Barème',
            icon: 'bar-chart-3',
            text: 'La notation suit la structure de barème associée à l’examen.',
          },
          {
            title: 'Annotations',
            icon: 'message',
            text: 'Les remarques et marqueurs servent à expliciter la correction sur la copie.',
          },
          {
            title: 'Sauvegarde',
            icon: 'check-circle-2',
            text: 'Les modifications sont sauvegardées pendant le travail de correction.',
          },
        ],
      },
      {
        title: 'Finalisation',
        body:
          'La finalisation clôt la correction de la copie, génère le PDF final lorsque les prérequis sont satisfaits et rend la copie consultable selon la publication décidée.',
      },
      {
        title: 'Points de vigilance',
        steps: [
          'Vérifier le total avant finalisation.',
          'Éviter les informations nominatives inutiles dans les annotations.',
          'Se déconnecter après usage sur un poste partagé.',
          'Contacter l’administration si une copie semble bloquée ou incohérente.',
        ],
      },
    ],
  },
  studentGuide: {
    eyebrow: 'Guide élève',
    title: 'Consulter ses copies finalisées',
    subtitle:
      'L’espace élève permet de consulter uniquement les copies et documents rendus disponibles pour le compte connecté.',
    intro:
      'Les copies apparaissent après finalisation et publication selon l’organisation de l’établissement.',
    ctas: [
      { label: 'Connexion élève', to: '/student/login', icon: 'login' },
      { label: 'Page d’accueil Korrigo', to: KORRIGO_PUBLIC_ROUTE_BY_KEY.home.path, icon: 'dashboard' },
    ],
    sections: [
      {
        title: 'Connexion',
        steps: [
          'Ouvrir la page de connexion élève.',
          'Utiliser les identifiants transmis par l’établissement.',
          'Changer le mot de passe si l’application le demande.',
        ],
      },
      {
        title: 'Consultation',
        cards: [
          {
            title: 'Copies disponibles',
            icon: 'file-text',
            text: 'Les copies visibles sont celles finalisées et publiées pour votre compte.',
          },
          {
            title: 'Annotations',
            icon: 'message',
            text: 'Les annotations aident à comprendre la correction et les points à retravailler.',
          },
          {
            title: 'PDF',
            icon: 'download',
            text: 'Le téléchargement est proposé lorsque le PDF final est disponible.',
          },
        ],
      },
      {
        title: 'Confidentialité',
        body:
          'Un élève ne consulte que son propre espace. Toute demande de correction administrative ou pédagogique passe par les interlocuteurs de l’établissement.',
      },
    ],
  },
  direction: {
    eyebrow: 'Direction et conformité',
    title: 'Suivi et cadre d’usage',
    subtitle:
      'Cette page résume les accès direction et les principes de protection des données sans publier d’indicateurs sensibles.',
    intro:
      'Les tableaux de bord détaillés nécessitent une authentification et un périmètre direction configuré.',
    ctas: [
      { label: 'Accès authentifié', to: '/admin/login', icon: 'login' },
      { label: 'Guide enseignant', to: KORRIGO_PUBLIC_ROUTE_BY_KEY.teacherGuide.path, icon: 'teacher-pen' },
    ],
    sections: [
      {
        title: 'Rôle direction',
        cards: [
          {
            title: 'Vue d’ensemble',
            icon: 'bar-chart-3',
            text: 'Consulter les examens et résultats autorisés par le périmètre du compte.',
          },
          {
            title: 'Suivi',
            icon: 'stats',
            text: 'Suivre l’avancement sans exposer d’informations nominatives sur les pages publiques.',
          },
          {
            title: 'Cadre d’accès',
            icon: 'lock',
            text: 'Les données détaillées restent derrière authentification et contrôle d’accès.',
          },
        ],
      },
      {
        title: 'Données personnelles',
        body:
          'Korrigo traite des informations nécessaires à l’organisation de la correction et à la consultation des copies. Les pages publiques ne publient ni listes nominatives, ni copies, ni chemins de fichiers.',
      },
      {
        title: 'Principes de conformité',
        steps: [
          'Limiter les accès aux rôles nécessaires.',
          'Ne publier aucun indicateur sensible sur les pages publiques.',
          'Conserver une traçabilité des actions applicatives importantes.',
          'Documenter les incidents et les réparations sans exposer de donnée personnelle.',
        ],
      },
      {
        title: 'Limites',
        body:
          'Les indicateurs chiffrés, exports et résultats détaillés ne sont disponibles que dans les espaces authentifiés prévus à cet effet.',
      },
    ],
  },
}
