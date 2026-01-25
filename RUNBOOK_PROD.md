# Runbook Production - Korrigo PMF

**Date**: 25 janvier 2026  
**Version**: 1.0  
**Auditeur**: Codex

## 1. Statut Production

**Verdict**: ❌ **NON DÉPLOYABLE** - Plusieurs critères de production non remplis

## 2. Critères de Production

### 2.1 Critères Techniques

| Critère | Requis | Actuel | Statut | Commentaire |
|---------|--------|--------|--------|-------------|
| Docker prod fonctionnel | ✅ | ✅ | ✅ | OK |
| Nginx reverse proxy | ✅ | ✅ | ✅ | OK |
| Gunicorn serveur | ✅ | ✅ | ✅ | OK |
| PostgreSQL 15 | ✅ | ✅ | ✅ | OK |
| Redis cache | ✅ | ✅ | ✅ | OK |
| Volumes persistants | ✅ | ✅ | ✅ | OK |
| OCR fonctionnel | ✅ | ❌ | ❌ | **BLOCKER** |
| Triple portail | ✅ | ⚠️ | ❌ | **BLOCKER** |
| Tests E2E passants | ✅ | ❌ | ❌ | **BLOCKER** |

### 2.2 Critères Fonctionnels

| Critère | Requis | Actuel | Statut | Commentaire |
|---------|--------|--------|--------|-------------|
| Workflow Bac Blanc complet | ✅ | ❌ | ❌ | **BLOCKER** |
| Identification sans QR Code | ✅ | ❌ | ❌ | **BLOCKER** |
| Sécurité PDF | ✅ | ✅ | ✅ | OK |
| Gestion concurrence | ✅ | ✅ | ✅ | OK |
| Audit trail | ✅ | ✅ | ✅ | OK |

## 3. Déploiement

### 3.1 Commandes Déploiement

```bash
# Déploiement prod
KORRIGO_SHA=<commit_sha> docker-compose -f infra/docker/docker-compose.prod.yml up -d --build

# Migrations
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py migrate

# Collect static
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# Superuser
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py createsuperuser
```

### 3.2 Vérification Post-Déploiement

```bash
# Health check
curl http://localhost:8088/api/health/

# Vérification services
docker-compose -f infra/docker/docker-compose.prod.yml ps

# Logs
docker-compose -f infra/docker/docker-compose.prod.yml logs backend
```

## 4. Backup & Restore

### 4.1 Backup

```bash
# Backup DB
docker-compose -f infra/docker/docker-compose.prod.yml exec db pg_dump -U viatique_user viatique > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup media
tar -czf media_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C backend/media .
```

### 4.2 Restore

```bash
# Restore DB
docker-compose -f infra/docker/docker-compose.prod.yml exec -T db psql -U viatique_user viatique < backup.sql

# Restore media
tar -xzf media_backup.tar.gz -C backend/media/
```

### 4.3 Test Backup/Restore

**Statut**: ❌ **NON TESTÉ** - Procédures non validées

## 5. Surveillance & Monitoring

### 5.1 Points de Surveillance

| Composant | Métrique | Seuil | Statut |
|-----------|----------|-------|--------|
| Backend | Disponibilité | 99.9% | ❌ |
| DB | Connexions | <100 | ❓ |
| Redis | Hit ratio | >95% | ❓ |
| Disk | Espace | >20% libre | ❓ |

### 5.2 Alertes

| Type | Seuil | Canal | Statut |
|------|-------|-------|--------|
| Backend down | 0% dispo | Email | ❌ |
| DB slow | >1s req | Email | ❌ |
| Disk full | <5% libre | SMS | ❌ |

## 6. Gestion des Incidents

### 6.1 Procédures d'Urgence

| Incident | Procédure | Statut |
|----------|-----------|--------|
| Backend down | Redémarrer service | Documenté |
| DB inaccessible | Vérifier connexions | Documenté |
| Performances basses | Vérifier charge | ❌ |
| Sécurité compromise | Arrêt immédiat | ❌ |

### 6.2 Contacts

| Rôle | Contact | Disponibilité |
|------|---------|---------------|
| DevOps | ? | ? |
| Sécurité | ? | ? |
| Support | ? | ? |

## 7. Non-Conformités Critiques

### 7.1 Fonctionnalités Manquantes

1. **OCR pour identification** - Fonctionnalité centrale absente
2. **Interface "Video-Coding"** - Impossible d'associer copies/élèves
3. **Authentification triple portail** - Séparation rôles incomplète
4. **Tests E2E complets** - Impossible de valider workflow

### 7.2 Risques de Sécurité

1. **Authentification incomplète** - Risque d'accès non autorisé
2. **Validation entrées insuffisante** - Risque d'injection
3. **Gestion erreurs** - Risque de fuite d'informations

## 8. Recommandations

### 8.1 Actions Immédiates (BLOCKERS)

1. **Implémenter OCR** - Fonctionnalité centrale de "sans QR Code"
2. **Compléter authentification** - Triple portail fonctionnel
3. **Créer tests E2E complets** - Validation workflow Bac Blanc
4. **Tester backup/restore** - Validation procédures

### 8.2 Actions à Moyen Terme

1. **Améliorer surveillance** - Monitoring et alertes
2. **Documenter incidents** - Procédures complètes
3. **Renforcer sécurité** - Tests de pénétration
4. **Optimiser performances** - Tests charge

## 9. Conclusion

Le projet **n'est PAS prêt pour la production**. Plusieurs **fonctionnalités critiques sont manquantes**:

- Le workflow d'identification sans QR Code n'est pas implémenté
- L'authentification triple portail est incomplète  
- Aucun test E2E complet n'a été exécuté
- Les procédures de backup/restore n'ont pas été testées

**Recommandation**: Ne pas déployer en production tant que les BLOCKERS critiques ne sont pas résolus.

**Prochaines étapes**:
1. Implémenter le module d'identification OCR
2. Compléter l'authentification triple portail
3. Créer et exécuter les tests E2E complets
4. Valider les procédures backup/restore
5. Réévaluer le projet