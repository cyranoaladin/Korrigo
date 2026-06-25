# Porte 6J - Audit et refactor des pages publiques Korrigo

## Contexte

La Porte 6J traite uniquement les pages publiques Korrigo. Aucun déploiement, build Docker, redémarrage, migration, SQL, backup manuel, sync manuel, prune ou nettoyage Docker n'a été réalisé.

Le déploiement reste bloqué tant que la Porte 6H-C n'a pas validé le backup automatique postérieur à `20260624T124211Z` et la synchronisation StorageBox associée.

## Audit production avant correction

Audit Playwright production :

`/tmp/korrigo_pages_audit_20260624T163657Z`

| Route | Status | H1 | Headings | Liens internes | Liens cassés | Console | Réseau |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `/korrigo` | 200 | 1 | 29 | 19 | 0 | 0 | 0 |
| `/korrigo/guide-enseignant` | 200 | 1 | 2 | 17 | 0 | 0 | 0 |
| `/korrigo/guide-eleve` | 200 | 1 | 2 | 17 | 0 | 0 | 0 |
| `/korrigo/direction` | 200 | 1 | 13 | 17 | 0 | 0 | 0 |

Les captures production sont dans :

`/tmp/korrigo_pages_audit_20260624T163657Z/screenshots/`

## Problèmes trouvés

Les routes étaient techniquement accessibles, mais le contenu public n'était pas assez borné :

- contenu éditorial dispersé dans plusieurs vues ;
- routes publiques recopiées dans les vues, le router, le navbar et le footer ;
- affichage public de compteurs dynamiques de plateforme ;
- mentions trop spécifiques sur des mécanismes IA/OCR/LLM ;
- promesses et chiffres non nécessaires aux pages publiques ;
- page direction trop détaillée pour un espace public ;
- contacts réels visibles dans le footer ;
- risque de divergence future entre pages et navigation.

## Cartographie source

La cartographie détaillée est documentée dans :

`docs/technical/PORTE6J_PAGES_SOURCE_MAP_2026-06-24.md`

## Architecture après correction

Nouvelle source de vérité :

- `frontend/src/features/korrigo/content/korrigoPublicContent.js`

Nouveau renderer commun :

- `frontend/src/features/korrigo/components/KorrigoPublicPage.vue`

Vues publiques minces :

- `frontend/src/views/HomeView.vue`
- `frontend/src/views/GuideEnseignant.vue`
- `frontend/src/views/GuideEtudiant.vue`
- `frontend/src/views/DirectionConformite.vue`

Consommateurs des constantes centralisées :

- `frontend/src/router/index.js`
- `frontend/src/components/Navbar.vue`
- `frontend/src/components/Footer.vue`

## Corrections par route

### `/korrigo`

- remplacement de la page marketing détaillée par une page d'entrée sobre ;
- suppression des compteurs publics ;
- suppression des promesses chiffrées et des détails techniques non nécessaires ;
- présentation des rôles, du workflow et des statuts principaux.

### `/korrigo/guide-enseignant`

- remplacement par un guide enseignant borné au parcours réel : accès, tableau de bord, copie assignée, correction, finalisation et vigilance ;
- suppression des exemples de comptes, chiffres, promesses et détails non vérifiés ;
- maintien des liens de connexion génériques.

### `/korrigo/guide-eleve`

- remplacement par un guide de consultation des copies finalisées ;
- suppression de toute donnée personnelle, exemple de compte ou indicateur ;
- clarification : les copies apparaissent selon finalisation et publication.

### `/korrigo/direction`

- remplacement de la page publique détaillée par une page de cadre d'usage ;
- suppression des indicateurs publics ;
- suppression des contacts réels ;
- rappel que les tableaux de bord détaillés sont authentifiés et périmétrés.

## Tests ajoutés

- `frontend/tests/unit/korrigoPublicContent.contract.test.ts`
- `frontend/tests/e2e/korrigo-public-pages.spec.ts`

Les tests couvrent :

- routes publiques canoniques ;
- absence de typo `guide-enseignanthttps` ;
- contenu centralisé ;
- absence de placeholder ;
- absence d'email dans le contenu public corrigé ;
- CTA sur routes internes connues ;
- usage du renderer central par les vues ;
- usage des constantes centrales par router/navbar/footer ;
- rendu Playwright des quatre routes avec H1, liens internes sans 500, zéro erreur console et zéro erreur réseau.

## Audit local après correction

Audit Playwright local :

`/tmp/korrigo_pages_local_audit_20260624T164737Z`

| Route | Status | H1 | Headings | Liens | Console | Réseau |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `/korrigo` | 200 | 1 | 15 | 20 | 0 | 0 |
| `/korrigo/guide-enseignant` | 200 | 1 | 8 | 19 | 0 | 0 |
| `/korrigo/guide-eleve` | 200 | 1 | 7 | 19 | 0 | 0 |
| `/korrigo/direction` | 200 | 1 | 8 | 19 | 0 | 0 |

Captures locales :

`/tmp/korrigo_pages_local_audit_20260624T164737Z/screenshots/`

## Vérifications locales

- Contrat public ciblé : PASS.
- Suite Vitest frontend complète : PASS.
- Build Vite : PASS.
- E2E Playwright public pages : PASS sur le frontend courant avec proxy API local.
- Pipeline local officiel : PASS.
- E2E officiel : `PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS`.

Audit du pipeline local officiel :

`/tmp/korrigo_porte6j_pages_release_check_20260624T165441Z`

## Limites

- Aucun déploiement n'a été effectué.
- Aucun build Docker n'a été effectué.
- La correction ne peut pas être livrée tant que 6H-C n'est pas clôturée.
- Les pages restent volontairement descriptives et ne publient aucun chiffre opérationnel.

## Verdict

`PAGES_READY_FOR_DIRECT_DEPLOY_AFTER_6HC`
