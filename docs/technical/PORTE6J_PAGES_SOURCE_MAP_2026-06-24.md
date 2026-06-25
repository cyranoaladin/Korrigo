# Porte 6J - Cartographie des pages publiques Korrigo

## Contexte

Cette cartographie couvre les quatre routes publiques Korrigo auditées en Porte 6J :

- `/korrigo`
- `/korrigo/guide-enseignant`
- `/korrigo/guide-eleve`
- `/korrigo/direction`

L'audit production Playwright a été capturé dans :

`/tmp/korrigo_pages_audit_20260624T163657Z`

Aucune donnée élève, aucun compte réel, aucun email réel et aucun contenu de copie ne sont repris dans ce document.

## Source commune

La source de vérité éditoriale et de navigation est :

- `frontend/src/features/korrigo/content/korrigoPublicContent.js`

Elle contient :

- les quatre routes publiques canoniques ;
- les segments de route utilisés par le router ;
- les libellés de navigation ;
- les liens de connexion génériques ;
- les statuts de copie non sensibles ;
- le workflow public générique ;
- les contenus des quatre pages.

Le composant de rendu commun est :

- `frontend/src/features/korrigo/components/KorrigoPublicPage.vue`

Les pages publiques ne portent plus de grands blocs éditoriaux locaux.

## Routes

| Route | Composant route | Clé contenu | Source textes | Source liens |
| --- | --- | --- | --- | --- |
| `/korrigo` | `frontend/src/views/HomeView.vue` | `home` | `KORRIGO_PUBLIC_PAGES.home` | `KORRIGO_PUBLIC_ROUTES`, CTA centralisés |
| `/korrigo/guide-enseignant` | `frontend/src/views/GuideEnseignant.vue` | `teacherGuide` | `KORRIGO_PUBLIC_PAGES.teacherGuide` | `KORRIGO_PUBLIC_ROUTES`, `KORRIGO_LOGIN_LINKS` |
| `/korrigo/guide-eleve` | `frontend/src/views/GuideEtudiant.vue` | `studentGuide` | `KORRIGO_PUBLIC_PAGES.studentGuide` | `KORRIGO_PUBLIC_ROUTES`, `KORRIGO_LOGIN_LINKS` |
| `/korrigo/direction` | `frontend/src/views/DirectionConformite.vue` | `direction` | `KORRIGO_PUBLIC_PAGES.direction` | `KORRIGO_PUBLIC_ROUTES`, portail de connexion |

## Router et navigation

- `frontend/src/router/index.js` consomme `KORRIGO_PUBLIC_ROUTE_SEGMENTS`.
- `frontend/src/components/Navbar.vue` consomme `KORRIGO_PUBLIC_ROUTES` et `KORRIGO_LOGIN_LINKS`.
- `frontend/src/components/Footer.vue` consomme `KORRIGO_PUBLIC_ROUTE_BY_KEY`.

Les chemins publics ne sont plus recopiés dans les composants de page, la barre de navigation et le footer.

## Problèmes observés en production

L'audit production a montré que les quatre routes étaient accessibles, sans 500, sans lien interne cassé, sans erreur console et sans erreur réseau critique.

Les problèmes étaient éditoriaux et maintenabilité :

- textes publics dispersés dans plusieurs composants ;
- liens et libellés de routes recopiés dans plusieurs composants ;
- affichage public de compteurs dynamiques de plateforme ;
- présence d'informations opérationnelles trop spécifiques ou non vérifiées pour une page publique ;
- références à des mécanismes IA/OCR/LLM et à des métriques chiffrées qui ne doivent pas être publiées sans contrat clair ;
- ancien footer public affichant des contacts réels ;
- page direction contenant des informations détaillées qui relèvent d'un espace authentifié ou d'une documentation interne.

## Données conservées

Les pages corrigées ne conservent que des informations structurelles non sensibles :

- rôles génériques : administration, enseignants, élèves, direction ;
- étapes génériques du workflow ;
- statuts techniques principaux : `READY`, `IN_PROGRESS`, `FINALIZED` ;
- principes de correction humaine, accès par rôle et traçabilité ;
- limites claires sur les données détaillées, qui restent derrière authentification.

## Données retirées des pages publiques

- compteurs de copies, élèves, correcteurs, examens ou annotations ;
- emails réels ;
- noms réels ;
- promesses chiffrées ou non contractualisées ;
- détails d'architecture ou d'outillage qui ne sont pas nécessaires à l'utilisateur public ;
- mentions de fonctionnalités non garanties par les pages publiques ;
- chemins et informations opérationnelles sensibles.

