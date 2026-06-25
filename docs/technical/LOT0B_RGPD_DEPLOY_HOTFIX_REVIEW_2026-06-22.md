# Lot 0-B - Revue du hotfix RGPD/deploy

Date: 2026-06-22  
Branche locale: `fix/lot0-rgpd-deploy`  
Base de travail: `1958681b082402e06d0f463e685d8a9895c460c5` (`korrigo-step3-20260620-1958681`)  
Statut: implementation locale, non poussee, non buildee en image Docker, non deployee.

Ce document ne contient aucune donnee personnelle reelle, aucun secret et aucune valeur issue du `.env`.

---

## 1. Contexte

La production Korrigo est saine depuis la bascule Porte 3 et tourne sur l'image figée `1958681`. Le chantier post-bascule a identifie deux risques immediats a traiter avant de poursuivre les Portes 4 a 9:

1. des donnees personnelles reelles etaient codees dans des composants frontend et donc servies dans le bundle navigateur;
2. le workflow GitHub Actions de deploiement contenait un chemin automatique et des operations dangereuses vers la production.

Le Lot 0-B est un hotfix local de niveau 1. Il retire l'exposition frontend et neutralise le deploiement automatique, sans modifier la production.

---

## 2. Risques initiaux

### PII frontend exposee dans le bundle

Des composants Vue contenaient des noms, emails ou libelles nominaux reels. Comme le frontend est compile en assets statiques, ces donnees pouvaient etre telechargees par n'importe quel navigateur accedant a l'application.

### Workflow `deploy.yml` dangereux

Le workflow de deploiement contenait un risque de declenchement automatique et des etapes susceptibles de modifier ou reinitialiser la production sans runbook humain controle.

### Absence de gate anti-PII

Il n'existait pas de garde CI bloquant la reapparition de valeurs nominatives connues dans `frontend/src`.

---

## 3. Perimetre du hotfix

Inclus:

- neutralisation locale de `.github/workflows/deploy.yml`;
- ajout d'un job CI anti-PII par hashes;
- retrait des donnees nominatives statiques dans les composants frontend identifies;
- remplacement de l'autorisation frontend nominative par une capacite serveur `/api/me`;
- tests de contrat backend pour ces invariants;
- verification locale frontend/backend/build.

Exclus:

- aucun push;
- aucun build d'image Docker;
- aucun deploiement;
- aucune action production;
- pas de refonte complete des bilans;
- pas d'enforcement serveur complet de toutes les donnees statiques de la vue bilan;
- pas de traitement Porte 4 Docker/disque;
- pas de purge de donnees;
- pas de refonte UI globale.

---

## 4. Fichiers modifies

| Fichier | Changement | Risque traite | Risque residuel |
|---|---|---|---|
| `.github/workflows/deploy.yml` | Remplace par un stub manuel `workflow_dispatch` | empeche un deploiement prod automatique destructeur | le push du hotfix doit etre controle pour eviter toute surprise historique |
| `.github/workflows/ci.yml` | Ajoute le job `pii-gate` | bloque la reapparition des PII connues dans `frontend/src` | denylist hash a maintenir si de nouvelles PII sont decouvertes |
| `scripts/ci/check_frontend_pii_hashes.py` | Nouveau scanner par SHA-256 normalise; gestion accents, casse, espaces et caracteres invisibles simples | evite de stocker la PII en clair tout en detectant les valeurs connues | ne detecte que les valeurs hashées connues, pas toute PII inconnue |
| `backend/core/views.py` | Expose `can_view_direction_bilans` dans `/api/me` et `features` | retire les emails d'autorisation du bundle frontend | l'enforcement serveur complet de la vue bilan reste un chantier Lot 2/Porte 7 |
| `backend/core/tests/test_lot0_rgpd_deploy_contract.py` | Tests workflow, gate PII et capacite direction | verrouille les invariants du hotfix | les tests ne remplacent pas une revue RGPD generale du depot |
| `frontend/src/components/stats/StatsQcmTab.vue` | Supprime les tableaux nominatifs statiques; rend les details depuis `props.data` seulement | retire la PII navigateur la plus critique | les stats agregees restent statiques dans la vue |
| `frontend/src/components/stats/StatsQualityTab.vue` | Retire les mentions nominatives statiques | retire PII navigateur | composant a auditer plus largement en Porte 7 |
| `frontend/src/views/BilanBacBlanc.vue` | Supprime les emails de direction; consomme la capacite serveur | retire les ayants droit nominatifs du bundle | la vue reste largement statique; a refactorer via backend en Lot 2/Porte 7 |
| `frontend/src/views/HomeView.vue` | Retire un contact personnel code en dur | evite exposition nominative non necessaire | verifier contenu institutionnel lors de l'audit global |
| `frontend/src/views/admin/QuestionnaireBilan.vue` | Remplace des sources nominatives par libelles anonymises | retire PII navigateur | donnees statiques a auditer integralement en Porte 7 |

---

## 5. Ce que le hotfix corrige

- Le workflow de deploiement ne contient plus de trigger automatique.
- `deploy.yml` ne contient plus les operations de production dangereuses connues.
- Les composants frontend identifies ne contiennent plus les valeurs nominatives connues par le gate hash.
- La vue Bac Blanc ne contient plus d'emails direction codés en dur.
- `/api/me` expose une capacite serveur `can_view_direction_bilans`.
- Le frontend consomme cette capacite au lieu d'une liste nominative.
- La CI contient un job anti-PII localisable et portable.
- Le gate ne stocke pas les valeurs reelles: uniquement des hashes SHA-256 normalises.
- Le gate echoue sur une valeur synthetique denylistée, y compris avec un caractere invisible intramot, et n'imprime pas la valeur detectee.
- Les hashes SHA-256 de PII connue sont une mesure de reduction de risque, pas une anonymisation. Ils doivent etre traites comme des marqueurs pseudonymises et ne doivent pas etre diffuses hors perimetre autorise.

---

## 6. Ce que le hotfix ne corrige pas encore

- Il ne deploie pas la correction en production: la prod reste sur `1958681` jusqu'a un deploiement controle.
- Il ne remplace pas toutes les donnees statiques de `BilanBacBlanc.vue` par des endpoints backend.
- Il ne cree pas d'enforcement serveur complet pour chaque fragment de contenu bilan.
- Il ne detecte pas automatiquement toute PII inconnue; il bloque les valeurs connues par hash.
- Il ne remplace pas encore les hashes SHA-256 nus par des HMAC-SHA256 avec pepper non committe. Cette evolution est a planifier en Lot 0-E ou dans le prochain durcissement CI, apres regeneration controlee des digests sans exposer les valeurs sources.
- Il ne corrige pas les backups planifies suspendus ni leur chiffrement.
- Il ne traite pas les Portes 4 a 9.

---

## 7. Verifications executees

### Preflight Git

- branche courante: `fix/lot0-rgpd-deploy`;
- HEAD initial: `1958681b082402e06d0f463e685d8a9895c460c5`;
- tag sur HEAD: `korrigo-step3-20260620-1958681`;
- branche locale non rattachee a un upstream;
- aucun `git push` execute.

### Syntaxe diff

Commande:

```bash
git diff --check
```

Resultat: OK.

### Gate PII source

Commande:

```bash
python scripts/ci/check_frontend_pii_hashes.py frontend/src
```

Resultat:

```text
PII_HASH_MATCH_COUNT=0
```

### Gate PII bundle local

Apres build local frontend, scan additionnel:

```bash
python scripts/ci/check_frontend_pii_hashes.py frontend/dist
```

Resultat:

```text
PII_HASH_MATCH_COUNT=0
```

### Tests backend cibles

Commande:

```bash
pytest -q -p no:cacheprovider backend/core/tests/test_lot0_rgpd_deploy_contract.py
```

Resultat: `6 passed`.

### Tests backend complets

Commande executee depuis `backend/` avec l'environnement Python local:

```bash
pytest -q -p no:cacheprovider
```

Resultat: `996 passed, 1 skipped, 3 deselected`.

Note: `pytest -q` depuis la racine collecte aussi des scripts hors rootdir backend et n'est pas la commande fiable pour cette suite; la configuration projet est `backend/pytest.ini`.

### Tests frontend

Commande:

```bash
cd frontend
npm test -- --run
```

Resultat: `27 passed`, `334 passed`.

### Build frontend local

Commande:

```bash
cd frontend
npm run build
```

Resultat: build Vite OK. Avertissements de chunking dynamique/statique observes, non bloquants et non introduits par ce hotfix.

---

## 8. Risques residuels

1. La prod publique sert encore l'image `1958681`; le retrait PII navigateur ne sera effectif publiquement qu'apres build/deploiement controle du hotfix.
2. La denylist hash couvre les valeurs connues; elle ne remplace pas un audit general anti-PII.
3. Les digests SHA-256 nus restent attaquables par dictionnaire si le depot est diffuse a un adversaire connaissant le corpus probable de noms/emails. Ils doivent etre remplaces par HMAC-SHA256 avec `PII_GATE_PEPPER` non committe lorsque les valeurs sources pourront etre regenerees sous controle administrateur.
4. `BilanBacBlanc.vue` reste trop statique. Le hotfix retire les emails et PII connues mais ne transforme pas encore la page en vue entierement alimentee par backend.
5. Les backups/sync StorageBox restent suspendus apres bascule et doivent etre remis en service seulement apres correction RGPD/chiffrement.
6. Les Portes 4 a 9 restent ouvertes.

---

## 9. Conditions de GO pour push ulterieur

Avant tout push:

- revue humaine de ce hotfix;
- confirmation que `deploy.yml` ne contient que `workflow_dispatch`;
- confirmation qu'aucun secret ni PII reelle n'apparait dans le diff affiche;
- `git diff --check` OK;
- gate PII `frontend/src` OK;
- tests backend cibles OK;
- tests frontend OK;
- decision explicite sur la strategie de PR non deployante.

Le push doit etre volontaire et controle. Il ne doit pas declencher de deploiement automatique.

---

## 10. Conditions de GO pour build et deploiement controle

Avant build image:

- commit hotfix pousse/revu;
- tag ou revision source stable;
- build complet backend/nginx depuis Dockerfiles committes;
- labels OCI vers le commit hotfix;
- image prod sans dependances dev;
- staging sans overlay;
- tests backend/frontend/staging;
- scan du bundle construit confirmant `PII_HASH_MATCH_COUNT=0`;
- backup point-in-time prod et test de restaurabilite;
- runbook de deploiement avec rollback.

Avant prod:

- accord humain explicite;
- pas de migration destructive attendue pour ce hotfix;
- health avant/apres;
- verification que le bundle public ne contient plus les hashes connus;
- logs sans PII/secret.

---

## 11. Rollback logique prevu

Ce hotfix ne change pas le schema DB. Le rollback attendu apres deploiement serait donc:

1. revenir au digest de l'image production precedente validee (`1958681`);
2. redemarrer les services applicatifs selon runbook controle;
3. verifier health public et absence d'overlay;
4. aucune restauration DB requise sauf incident externe non lie au hotfix.

Les images de rollback doivent rester conservees jusqu'a validation post-deploiement.

---

## 12. Regle de confidentialite sur le diff

Ne pas coller le diff brut de ce hotfix dans un outil de conversation ou ticket non expurge: les lignes supprimees contiennent des donnees personnelles reelles. Pour revue externe, fournir:

- `git diff --stat`;
- liste de fichiers;
- synthese par fichier;
- extraits ajoutes uniquement s'ils ne contiennent aucune PII;
- ou diff redige/expurge.
