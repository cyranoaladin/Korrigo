Tu es un principal engineer / staff engineer / architecte DevSecOps senior chargé d’un audit complet, d’une stabilisation production et d’une remise en cohérence globale de la plateforme Korrigo.

CONTEXTE OPÉRATIONNEL
- Dépôt à auditer et corriger : https://github.com/cyranoaladin/Korrigo/
- Environnement de production : korrigo.labomaths.tn
- Accès serveur : ssh root@88.99.254.59
- Stack attendue : frontend Vue/Vite, backend Django/DRF, PostgreSQL, Redis, Celery, Nginx, médias protégés, OCR, génération PDF, LLM, export PRONOTE, dashboards admin et correcteurs.
- La plateforme a été historiquement conçue autour du BAC BLANC MATHS 2026 et a été mise à jour avec l’ajout du DNB BLANC MATHS 2026.
- Cette évolution ne doit créer AUCUN conflit entre examens, copies, correcteurs, dashboards, barèmes, CSV, paramètres, seed data, types d’examen, règles métier, export, permissions, routes ou configurations.

OBJECTIF ABSOLU
Je veux que la plateforme soit 100% propre et fonctionnelle en production, sans angle mort, avec cohérence totale entre :
- dépôt Git,
- code réellement exécuté sur le serveur,
- images Docker,
- overlays éventuels,
- backend Django,
- base PostgreSQL,
- Redis/Celery,
- frontend,
- dashboards,
- affectations admin,
- logique métier,
- sauvegardes,
- restauration,
- monitoring,
- sécurité.

EXIGENCES MÉTIER NON NÉGOCIABLES
1. Les examens BAC BLANC MATHS 2026 et DNB BLANC MATHS 2026 doivent être totalement séparés et cohérents :
   - pas de mélange de copies,
   - pas de mélange de correcteurs,
   - pas de mélange de barèmes,
   - pas de mélange de CSV,
   - pas de conflit de dashboards,
   - pas de conflit de stats,
   - pas de conflit de seed/config,
   - pas de hardcode dangereux qui suppose qu’il n’existe qu’un seul examen.
2. Lorsqu’un admin affecte des correcteurs à un examen, la configuration doit être immédiatement et correctement prise en compte :
   - dans la base,
   - dans Django,
   - dans les serializers,
   - dans les dashboards,
   - dans les dispatchs,
   - dans les permissions d’accès aux copies,
   - dans les statistiques,
   - dans les flux de correction.
3. Les copies ne doivent avoir que 3 états métier visibles et structurants :
   - Prêt
   - En cours
   - Finalisée
   Tu dois éliminer proprement toute incohérence actuelle si d’autres états existent encore techniquement. Si des états internes doivent subsister pour raisons techniques, ils doivent être encapsulés proprement sans casser la lisibilité métier et sans ambiguïté.
4. Toutes les données de correction doivent être intégralement récupérables :
   - copies,
   - pages,
   - annotations,
   - notes,
   - remarques,
   - appréciations,
   - historique,
   - affectations,
   - dispatch,
   - bilans LLM,
   - résultats OCR,
   - PDF finaux,
   - drafts/autosave,
   - journaux d’audit.
5. En cas de crash, panne, fausse manipulation, perte de données ou corruption partielle, il faut qu’on puisse restaurer la plateforme le plus finement possible.
6. Il faut auditer et fiabiliser :
   - les backups complets toutes les 30 minutes,
   - l’envoi vers le Storage Box Hetzner,
   - la rétention,
   - la restauration,
   - la vérification d’intégrité,
   - la traçabilité des sauvegardes.

MISSION GLOBALE
Tu dois :
- lire le dépôt en profondeur,
- lire les dossiers et fichiers dans leurs moindres détails,
- auditer le serveur de production,
- comparer code Git / code réellement exécuté,
- détecter tout doublon, overlay contradictoire, fichier zombie, fichier fantôme, code obsolète, migration incohérente, seed contradictoire, service cassé, volume incohérent, cron mort, conteneur inutile, route morte, composant orphelin,
- corriger tout ce qui doit l’être,
- sécuriser,
- tester,
- documenter,
- laisser la plateforme propre et robuste.

RÈGLES DE TRAVAIL
- Tu ne fais pas un audit superficiel.
- Tu ne te limites pas à quelques fichiers.
- Tu ne te contentes pas de faire “passer des tests”.
- Tu cherches les causes racines.
- Tu traites les conflits inter-stacks.
- Tu valides le comportement réel en mode production.
- Tu ne laisses aucune incohérence majeure sans traitement ou justification écrite précise.
- Tu n’ajoutes pas de hacks rapides ni de contournements sales.
- Tu n’éteins pas une fonctionnalité pour masquer un bug sans justification explicite et plan de correction propre.
- Si un contrat API change, tu corriges TOUS les consommateurs.
- Si un état métier change, tu corriges modèles, migrations, serializers, vues, dashboards, filtres, labels, tests, docs et scripts.
- Si une feature n’est pas fiable, tu la rends fiable ou tu documentes précisément la limite résiduelle.

PHASE 0 — AUDIT DU SERVEUR RÉEL
Tu commences par le serveur réel via SSH.
Tu dois établir une photographie complète de la prod.

0.1 — Cartographie système
- hostname, uptime, charge, mémoire, swap, disque
- arborescences pertinentes :
  - /var/www/
  - /home/
  - /opt/
  - /root/
  - chemins liés à korrigo
- utilisateurs techniques
- services systemd pertinents
- cron system
- timers systemd
- tâches planifiées liées à backup / restore / cleanup / monitoring

0.2 — Cartographie Docker / conteneurs
- docker ps -a
- docker images
- docker volume ls
- docker network ls
- docker inspect des services Korrigo
- docker compose files réellement utilisés
- vérifier si la prod correspond vraiment à l’image buildée ou si elle repose sur des overlays bind-mountés
- identifier toute divergence entre image et code monté en overlay

0.3 — Cartographie code prod réel
- localiser le code réellement exécuté
- localiser les overlays éventuels
- comparer le dépôt Git et les fichiers réellement montés dans les conteneurs
- lister tous les fichiers overlay qui remplacent le code applicatif
- déterminer si des fichiers du serveur prennent le dessus sur ceux du dépôt
- déterminer si certains overlays sont obsolètes, contradictoires, en doublon, orphelins ou dangereux

0.4 — Cartographie application active
- vérifier état de korrigo.labomaths.tn
- reverse proxy / nginx / conf active
- upstreams
- certificats TLS
- logs nginx
- logs backend
- logs celery
- logs beat
- logs postgres si utile
- endpoints health
- endpoints metrics
- erreurs récentes
- redémarrages récents
- timeouts, 4xx, 5xx
- workers bloqués, tâches coincées, copies coincées

PHASE 1 — CARTOGRAPHIE DU DÉPÔT
Lis et cartographie tout le dépôt.
Tu dois au minimum analyser :
- README
- docs techniques
- docs de déploiement
- docker-compose / infra
- backend/core
- backend/exams
- backend/grading
- backend/students
- backend/identification
- backend/processing
- frontend/src/router
- frontend/src/services
- frontend/src/stores
- frontend/src/views
- composants utilisés par admin/correcteur/élève
- migrations
- management commands
- scripts backup/restore/cleanup si présents
- tests existants
- seeds
- fichiers CSV ou conventions d’import

PHASE 2 — AUDIT MÉTIER EXHAUSTIF
Tu dois reconstituer et valider le fonctionnement complet des flux suivants :

2.1 — Examens
- création d’examen
- type d’examen
- séparation BAC / DNB
- impact sur visibilité dashboard correcteur
- impact sur dispatch
- impact sur imports
- impact sur barèmes
- impact sur stats
- impact sur exports
- impact sur jury reports
- impact sur questionnaires
- impact sur seeds initiaux

2.2 — Affectation des correcteurs
- depuis le dashboard admin
- persistance DB
- prise en compte immédiate backend
- visibilité côté correcteur
- filtrage des copies par correcteur
- cohérence avec exam_type
- cohérence avec dispatch
- cohérence avec permissions
- cohérence si admin modifie une affectation après import ou après début de correction

2.3 — États des copies
Objectif cible :
- Prêt
- En cours
- Finalisée
Tu dois :
- identifier tous les états actuels réellement utilisés,
- identifier les états en DB, dans Django, dans les services, dans les vues, dans les dashboards, dans les tests,
- supprimer les incohérences,
- proposer et implémenter une logique propre, simple et totalement cohérente.
Tu dois vérifier tous les cas :
- import
- validation
- identification
- correction commencée
- autosave
- finalisation
- réouverture éventuelle
- recovery
- dispatch
- portail élève
- export

2.4 — Import et CSV
Tu dois auditer :
- format CSV BAC
- format CSV DNB
- mapping élèves
- unicité des élèves
- cohérence email / date de naissance / classes / groupes
- création de comptes élèves
- robustesse aux erreurs de CSV
- non-régression entre examens
- cohérence entre CSV, Student, Copy, Exam

2.5 — Dashboards
Tu dois vérifier :
- dashboard admin
- dashboard correcteur
- dashboard / portail élève
- cohérence avec DB
- cohérence avec serializers
- cohérence avec l’API
- cohérence avec exam_type
- cohérence avec affectations
- cohérence des stats
- cohérence des actions affichées
- cohérence des badges/statuts
- cohérence des permissions
- cohérence des données visibles et cachées

2.6 — Correction
Tu dois auditer et tester :
- chargement des copies
- affichage des pages
- annotations
- notes
- remarques
- appréciations globales
- brouillons/autosave
- verrouillage éventuel
- progression
- finalisation
- génération du PDF final
- récupération des données après refresh/crash/reconnexion
- comportement offline / erreurs réseau
- récupération des données après restart serveur ou worker

2.7 — Intégrité et récupération
Je veux qu’on puisse tout récupérer.
Tu dois donc vérifier :
- structure de persistance des notes/remarques/annotations/appreciations
- PDF finaux
- données OCR
- bilans LLM
- events/audit trail
- versioning
- intégrité en cas de rollback
- intégrité en cas de panne
- possibilité de reconstituer une correction complète à partir des données stockées

PHASE 3 — AUDIT SÉCURITÉ ET RÔLES
Tu dois auditer de façon exhaustive :
- authentification admin / teacher / student
- groupes Django
- is_staff / is_superuser / groupes métiers
- permissions DRF
- accès aux copies
- accès aux PDF finaux
- accès aux médias protégés
- accès aux résultats élèves
- routes publiques
- routes csrf_exempt
- CORS / CSP / cookies / sessions
- exposition de metrics
- données sensibles dans logs
- séparation stricte des rôles

Tu dois vérifier qu’un correcteur ne puisse jamais :
- voir des données d’un autre examen non autorisé,
- voir les copies d’un autre correcteur si non prévu,
- voir des identités élèves là où il ne doit pas,
- agir hors de son périmètre.

PHASE 4 — AUDIT BACKUP / RESTORE / STORAGE BOX
Tu dois auditer le backup réel de la plateforme.
Je veux des preuves, pas des suppositions.

Vérifie :
- existence réelle du mécanisme de backup toutes les 30 minutes,
- source exacte des sauvegardes,
- contenu exact des sauvegardes :
  - base,
  - médias,
  - fichiers utiles,
  - configs,
  - éventuellement overlays,
- mécanisme d’envoi vers Hetzner Storage Box,
- connectivité,
- authentification,
- logs de succès/échec,
- politique de rotation/rétention,
- intégrité des archives,
- tests de restauration,
- délai de restauration,
- scripts utilisés,
- cron / celery beat / command management / shell scripts réellement actifs.

Si le backup n’est pas complet, robuste ou vérifié, tu dois le corriger.
Je veux que le backup couvre réellement la plateforme entière.

PHASE 5 — AUDIT DE PROPRETÉ PROD
Je veux un audit très sévère de la propreté du serveur et du déploiement.

Tu dois identifier :
- fichiers obsolètes,
- overlays contradictoires,
- vieux backups non gérés,
- scripts dupliqués,
- compose files morts,
- migrations dupliquées ou suspectes,
- images Docker inutiles,
- volumes non utilisés,
- conteneurs zombies,
- restes de versions précédentes,
- fichiers fantômes,
- fichiers non suivis mais critiques,
- divergence entre Git et prod,
- chemins incohérents,
- variables d’environnement incohérentes,
- paramètres hérités d’anciens contextes,
- hardcodes d’examens,
- seed data contradictoires,
- routes ou composants morts.

PHASE 6 — CORRECTIONS
Tu corriges tout ce qui doit l’être :
- code,
- config,
- déploiement,
- backup,
- restore,
- rôles,
- permissions,
- états,
- dashboards,
- routes,
- serializers,
- scripts,
- cron,
- compose,
- docs,
- tests.

PHASE 7 — TESTS DE NIVEAU PRODUCTION
C’est crucial.
Je veux une batterie de tests la plus complète possible.

Tu dois ajouter ou corriger des tests de tous types :
1. tests unitaires
2. tests d’intégration
3. tests API
4. tests de permissions
5. tests de concurrence / race conditions
6. tests de migrations
7. tests de serializers
8. tests de services métier
9. tests frontend si présents
10. tests E2E / parcours critiques en mode prod-like
11. tests de backup/restore
12. tests de reprise après erreur

Tu dois impérativement tester en mode production ou prod-like :
- création examen BAC
- création examen DNB
- séparation totale entre les deux
- import CSV BAC
- import CSV DNB
- affectation de correcteurs
- prise en compte immédiate dans backend/db/dashboard
- dispatch de copies
- correction d’une copie
- sauvegarde notes/remarques/appreciation/annotations
- récupération après refresh
- finalisation
- génération PDF final
- portail élève
- export PRONOTE
- sauvegarde complète
- restauration complète ou partielle
- redémarrage des services sans perte de cohérence

PHASE 8 — LIVRABLE FINAL
À la fin, tu dois rendre un rapport professionnel extrêmement détaillé, structuré ainsi :

1. Executive summary
2. Architecture réelle constatée
3. État réel du serveur
4. Différences Git / prod
5. Problèmes critiques
6. Problèmes majeurs
7. Problèmes mineurs
8. Corrections effectuées
9. Justification métier et technique de chaque correction importante
10. Tests exécutés
11. Résultats des tests
12. État final des backups
13. État final de la restauration
14. État final de la sécurité
15. État final de la cohérence BAC / DNB
16. État final des rôles et permissions
17. État final des dashboards
18. État final des états de copies
19. État final du déploiement
20. Risques résiduels
21. Recommandations ultérieures non critiques

EXIGENCE FINALE
Je ne veux pas un audit descriptif.
Je veux :
- un audit,
- des preuves,
- des corrections,
- des tests,
- une validation production,
- un nettoyage de la plateforme,
- et un état final propre, robuste, cohérent, traçable et défendable.

Commence immédiatement par :
1. audit SSH du serveur réel,
2. cartographie docker/overlays/services,
3. cartographie du dépôt,
4. liste des écarts Git/prod,
5. plan d’action priorisé,
puis exécute le plan sans attendre.
