# Korrigo — Exploitation et déploiement production

Le fichier canonique est [`infra/docker/docker-compose.prod.yml`](infra/docker/docker-compose.prod.yml).
Il lance sept services : PostgreSQL, Redis, backend, worker Celery, Celery Beat,
frontend Nginx et proxy d'inférence privé. Les images applicatives sont des références
de release vérifiées ; Compose ne construit pas le code sur le serveur.

L'[état des lieux du 12 octobre 2026](docs/ops/PRODUCTION_STATE_2026-10-12.md)
documente les preuves de fonctionnement, les volumes conservés, les images actives,
les sauvegardes et les blocages externes. Il reste la référence pour le serveur
`88.99.254.59`, notamment tant que le DNS public n'est pas rétabli.

## Serveur existant

La release active est `/var/www/labomaths/korrigo_current`, un lien vers une archive
Git sous `/var/www/labomaths/korrigo_releases/`. Les secrets restent hors Git dans
`/etc/korrigo-ops/runtime.env` et `/etc/korrigo-ops/inference-proxy.conf`, mode `0600`
dans un répertoire `0700`. Le wrapper installé `/opt/korrigo-ops/korrigo-compose`
utilise ces chemins explicitement. Les anciens dossiers ne servent plus de source
pour un déploiement.

Ne pas recopier un exemple d'environnement sur ces fichiers existants. Conserver
les volumes PostgreSQL, médias, sauvegardes, cache et Redis identifiés dans l'état
des lieux. Le nom du projet Compose reste `docker`, pour conserver leurs noms.

```bash
/opt/korrigo-ops/korrigo-compose config --quiet
/opt/korrigo-ops/korrigo-compose ps
```

Utiliser `config --quiet` pour la validation : `config` sans cette option affiche
les valeurs interpolées, donc les secrets. Ne pas publier de fichier `.env`, de
configuration privée du proxy ou d'inspection complète de conteneur dans les logs.

## Préparer une installation ou une nouvelle release

Docker avec le plugin **Compose v2** est requis. Les scripts et le Makefile utilisent
un fichier explicite via `KORRIGO_ENV_FILE`, qui vaut par défaut
`/etc/korrigo-ops/runtime.env`. Ils fonctionnent depuis le checkout ou l'archive de
la release ; le script `prod_up.sh` fonctionne aussi depuis un autre répertoire.

1. Choisir une release dont les contrôles GitHub sont verts et disposer d'une
   sauvegarde restaurable avant une modification de production.
2. Pour une installation neuve seulement, copier [`.env.prod.example`](.env.prod.example)
   hors du dépôt dans un fichier privé `0600`. Renseigner chaque valeur obligatoire,
   avec des secrets uniques. [`.env.example`](.env.example) utilise les mêmes noms
   canoniques : `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `ALLOWED_HOSTS`.
   Compose transmet ensuite les alias attendus par Django.
3. Définir `KORRIGO_BACKEND_IMAGE` et `KORRIGO_NGINX_IMAGE` à partir des images
   vérifiées de cette release, de préférence `image@sha256:<digest du manifeste>`.
   Pour une image chargée localement, contrôler son ID et sa révision source avant
   d'utiliser sa référence. Les exemples laissent ces valeurs vides pour empêcher
   un démarrage avec d'anciens digests. Vérifier ou charger les images avant `up`.
4. Définir `KORRIGO_REDIS_VOLUME` avec le **volume existant** monté sur `/data`.
   Le nom peut être identifié sans lire les secrets :

   ```bash
   docker inspect docker-redis-1 --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{println .Name}}{{end}}{{end}}'
   ```

   Le volume est externe et obligatoire ; Compose ne crée pas un remplacement.
   Pour une installation réellement neuve, provisionner explicitement le volume
   choisi avant le premier démarrage. Ne pas appliquer cette procédure au serveur
   existant. Redis conserve AOF et `noeviction` pour préserver les tâches.
5. Vérifier les réseaux externes `korrigo_ai` (réseau interne) et
   `compose_rag_ui_net`, ainsi que les services amont `ingestor:8001` et
   `ollama:11434` sur ce dernier. Une absence de réseau ou d'amont demande un
   provisionnement explicite ; les scripts ne le créent pas silencieusement.
6. Préparer le fichier `KORRIGO_PROXY_CONFIG` avant tout démarrage. Pour une nouvelle
   configuration, réutiliser
   [`infra/nginx/inference-proxy.conf.template`](infra/nginx/inference-proxy.conf.template)
   et [`scripts/ops/render_inference_proxy.py`](scripts/ops/render_inference_proxy.py).
   Le renderer prend ses secrets uniquement depuis l'environnement et écrit en
   mode `0600`, sans les afficher. Le token client `KORRIGO_SEARCH_TOKEN` doit être
   **identique à `RAG_TOKEN`** dans le runtime ; `KORRIGO_UPSTREAM_TOKEN` est le token
   privé de l'amont, absent du runtime applicatif.

   Depuis une session privée, saisir les tokens sans les placer dans l'historique :

   ```bash
   read -r -s -p 'Token client (identique à RAG_TOKEN) : ' KORRIGO_SEARCH_TOKEN
   printf '\n'
   read -r -s -p 'Token privé amont : ' KORRIGO_UPSTREAM_TOKEN
   printf '\n'
   export KORRIGO_SEARCH_TOKEN KORRIGO_UPSTREAM_TOKEN
   python3 scripts/ops/render_inference_proxy.py \
       infra/nginx/inference-proxy.conf.template \
       /etc/korrigo-ops/inference-proxy.conf
   unset KORRIGO_SEARCH_TOKEN KORRIGO_UPSTREAM_TOKEN
   ```

   Ce rendu remplace le fichier cible : conserver la configuration active et sa
   sauvegarde sur le serveur existant. Vérifier que le fichier privé existe avant
   `up`. Le proxy n'expose aucun port hôte ; seul `POST /search`
   est autorisé côté RAG, et les routes d'administration restent inaccessibles.
7. Les applications utilisent par défaut `RAG_URL=http://korrigo-rag:8001` et
   `OLLAMA_URL=http://korrigo-ollama:11434`. `RAG_TOKEN` non vide est obligatoire.
   Renseigner également le fournisseur OCR/LLM et les modèles adaptés à la release ;
   des valeurs vides ne permettent pas de produire des bilans complets.

## Valider puis démarrer

Depuis la release préparée, valider sans afficher les secrets :

```bash
KORRIGO_ENV_FILE=/etc/korrigo-ops/runtime.env bash scripts/prod_compose.sh config --quiet
```

Pour une **installation neuve**, ou une release qui demande une migration, démarrer
d'abord les dépendances et appliquer la migration avec un conteneur ponctuel. Un
backend sans schéma initial valide peut refuser de démarrer ; une migration en
`exec` dans ce backend ne permettrait pas de le rétablir. Après validation préalable
de la migration sur une restauration de test, exécuter dans cet ordre :

```bash
bash scripts/prod_compose.sh up --no-build --wait -d db redis
make migrate
bash scripts/prod_up.sh
```

Ces commandes héritent de `KORRIGO_ENV_FILE`, dont le défaut est le fichier canonique.
Pour un autre chemin, l'exporter avant cette séquence. `make migrate` exécute
`run --rm --no-deps -T backend python manage.py migrate --noinput`, indépendamment
de l'état de démarrage du backend. Les dépendances doivent être saines au préalable.

Pour un serveur existant dont le schéma est déjà à jour, après contrôle des images,
réseaux, proxy privé et volumes, démarrer directement :

```bash
KORRIGO_ENV_FILE=/etc/korrigo-ops/runtime.env bash scripts/prod_up.sh
# Même commande via Make :
make up KORRIGO_ENV_FILE=/etc/korrigo-ops/runtime.env
```

Le script valide d'abord avec `config --quiet`, puis exécute
`up --no-build --wait -d`. Il attend les healthchecks des services. Les migrations,
imports et créations de comptes sont explicites : ni migration ni seed au démarrage.
Les migrations validées précèdent donc le démarrage des applications et la
vérification fonctionnelle finale.

Contrôler ensuite les sept services, `/api/health/`, les trois rôles, Celery, un bilan
avec RAG, l'OCR et une sauvegarde chiffrée restaurable. Un healthcheck vert couvre
seulement sa dépendance immédiate ; il ne remplace pas ces contrôles fonctionnels.

```bash
KORRIGO_ENV_FILE=/etc/korrigo-ops/runtime.env bash scripts/prod_compose.sh ps
make logs KORRIGO_ENV_FILE=/etc/korrigo-ops/runtime.env
```

Ne pas exécuter `down -v`, de purge Docker ou de script de release qui réinitialise
les données sur un serveur partagé. Le retour arrière documenté conserve les volumes
et les nouveaux secrets ; restaurer des données demande une procédure séparée.

## Documentation complémentaire

- [README principal](README.md) — Présentation générale du projet
- [État de production et preuves actuelles](docs/ops/PRODUCTION_STATE_2026-10-12.md)
- [Documentation technique de juin 2026](docs/technical/KORRIGO_FULL_STACK_PRODUCTION_README_AND_AUDIT_2026-06-25.md)
  — Historique ; consulter la configuration canonique actuelle pour le déploiement
- [Architecture technique](docs/technical/ARCHITECTURE.md)
- [Politique RGPD](docs/security/POLITIQUE_RGPD.md)
