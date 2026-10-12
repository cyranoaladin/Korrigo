# Remise en service Korrigo

Validation utilisateur : 12 octobre 2026, autorisation de correction, amélioration et mise en service stable, robuste, cohérente et fonctionnelle.

## Objectif

Rétablir l'accès public et les fonctions métier, rendre le runtime reproductible depuis le dépôt, protéger les données existantes et fournir un état d'exploitation vérifiable.

## État constaté

Le dépôt local et GitHub sont à `4e85f49`. Le répertoire serveur Git `/var/www/labomaths/korrigo_release` est sur une branche divergente à `6131bd4`. Les 249 fichiers Python métier de l'image backend correspondent exactement à `c38a586`; le runtime ajoute un correctif Pillow de septembre. Le frontend est basé sur `ac5487c`. Le dossier `/var/www/labomaths/korrigo` fournit notamment l'environnement serveur.

La base, les médias, les six conteneurs et les sauvegardes sont fonctionnels. Les 733 copies passent le contrôle d'intégrité. Le DNS autoritaire `.tn` renvoie NXDOMAIN pour `labomaths.tn`. Les règles de transfert Docker référencent un ancien pont au lieu du pont actuel Korrigo. Les alias IA ne sont pas joignables depuis Korrigo. Le modèle OCR est vide et le modèle bilan configuré n'apparaît plus dans le catalogue OpenRouter.

## Architecture retenue

Conserver les volumes et le projet Compose `docker`. Corriger les règles réseau uniquement pour le pont Korrigo et les sorties nécessaires, avec un mécanisme idempotent résistant au changement d'identifiant de réseau. Utiliser les services RAG/Ollama déjà présents, après validation des endpoints et modèles, par une connectivité explicite et persistante. Conserver la protection des ports de base de données et de Redis.

Réconcilier Compose et les images par références explicites; sortir les valeurs secrètes des overrides, préserver les anciennes clés de chiffrement des sauvegardes et remplacer les secrets de service quand leur autorité est disponible. Réintroduire les deux fichiers de migration identification perdus par main. Corriger l'OCR face aux variables vides et rendre les builds reproductibles.

## Déploiement et vérification

Sauvegarder la configuration exacte et un retour arrière avant changement. Tester chaque bug de code en RED/GREEN. Contrôler la parité des modèles Compose sans imprimer les environnements. Déployer uniquement les services modifiés, sans suppression de volumes ni reconstruction des bases. Vérifier santé, migrations, worker, intégrité, accès aux dépendances IA, tests authentifiés non destructifs et navigateur desktop/mobile. Le succès complet exige aussi un DNS public normal et une génération IA de contrôle sans données personnelles.

## Dépendances externes

La restauration de la délégation/du renouvellement de `labomaths.tn` exige l'accès au gestionnaire du domaine. La rotation d'une clé OpenRouter nécessite une autorité de gestion, distincte de la clé d'inférence. Ces accès sont recherchés; leur absence doit rester explicite dans le bilan.

## Cas fonctionnel précisé pendant la vérification

Les essais authentifiés ont reproduit un blocage pour un enseignant sans examen ni copie assignés : la liste des types disponibles est vide et la fenêtre de choix masque notamment la déconnexion. Dans le périmètre de remise en fonctionnement autorisé, une réponse réussie contenant une liste vide doit afficher le tableau de bord vide et arrêter le chargement, sans sélection fictive ni requête de copies. Une réponse en erreur ou encore en chargement garde son état actuel ; la sélection automatique d'un seul type et le choix obligatoire entre plusieurs types restent inchangés.

La cohérence des validations comprend le contrôle de release : son lot complet doit utiliser la base PostgreSQL de sa stack locale dédiée, puisque ce lot inclut des tests PostgreSQL et lents. La politique de zéro test ignoré reste obligatoire ; l'expression de détection doit reconnaître une vraie ligne de résumé pytest. Aucune exécution de ce script destructif de réinitialisation/seed n'est autorisée sur la stack de production ou sur le Docker partagé de travail.

Les échecs GitHub ont précisé deux exigences déjà comprises dans la remise en service autorisée. Une installation de validation vierge doit démarrer DB/Redis, appliquer explicitement les migrations, puis démarrer les services applicatifs : le garde de schéma reste actif et les migrations automatiques restent désactivées. Le contrôle de confidentialité doit refuser une clé ou une liste de références manquantes, utiliser le secret réellement transmis et analyser aussi les fichiers compilés. Ses références sont des HMAC générés en mémoire sur le serveur ; seules des empreintes et des étiquettes génériques entrent dans Git.
