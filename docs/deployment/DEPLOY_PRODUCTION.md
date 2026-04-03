# Déploiement Production — Note de Référence

Ce document est conservé comme point d’entrée court.

Références normatives actuelles :
- [DEPLOYMENT_GUIDE](DEPLOYMENT_GUIDE.md) pour la procédure détaillée
- [RUNBOOK_PRODUCTION](RUNBOOK_PRODUCTION.md) pour l’exploitation quotidienne

État réel au 2026-04-03 :
- production active sur `https://korrigo.labomaths.tn`
- serveur `root@88.99.254.59`
- chemin applicatif `/var/www/labomaths/korrigo`
- stack pilotée par `infra/docker/docker-compose.prod.yml`
- sauvegardes automatiques toutes les 30 minutes vers Hetzner StorageBox

Les anciennes procédures basées sur `/home/ubuntu/korrigo`, sur des backups purement locaux, ou sur un simple `docker compose down/up` comme stratégie de reprise ne sont plus la référence.
