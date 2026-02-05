# Runbook Production - Korrigo PMF

**Date**: 26 janvier 2026
**Version**: 1.3.0
**Statut**: ✅ **DÉPLOYABLE**

---

## 1. Statut Production

**Verdict**: ✅ **READY FOR PRODUCTION**
Tous les tests (Unitaires, Intégration, E2E, Backup/Restore) passent. L'authentification RBAC est corrigée.

## 2. Critères de Production

### 2.1 Critères Techniques

| Critère | Statut | Commentaire |
|---------|--------|-------------|
| **Docker Build** | ✅ | Images backend/frontend build OK |
| **Python Version** | ✅ | 3.9 (aligné CI/Prod) |
| **CI Pipeline** | ✅ | GitHub Actions Green (Lint, Unit, E2E) |
| **RBAC Security** | ✅ | Permissions Teacher/Admin/Student strictes |
| **Dependencies** | ✅ | Tesseract OCR intégré |

### 2.2 Critères Fonctionnels

| Critère | Statut | Commentaire |
|---------|--------|-------------|
| **Identification** | ✅ | OCR + Validation manuelle ("Video-Coding") |
| **Authentification** | ✅ | Triple portail (Admin/Prof/Élève) fonctionnel |
| **Correction** | ✅ | Annotation vectorielle + verrouillage |
| **Backup/Restore** | ✅ | Commande `restore` réparée (Multi-pass) |

---

## 3. Commandes Opérationnelles

### 3.1 Déploiement

```bash
# 1. Démarrer la stack
make up

# 2. Initialiser les données (Groupes, Admin)
make init_pmf
```

### 3.2 Backup & Restore (CRITIQUE)

Le système utilise deux commandes de management Django personnalisées.

**Backup Manuel**:
```bash
# Créer un backup complet (DB + Media) dans un dossier temp
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py backup --include-media
```

**Restore (En cas de désastre)**:
⚠️ **ATTENTION**: Cette commande écrase la base de données actuelle !

```bash
# Restaurer à partir d'un dossier de backup
docker-compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py restore /path/to/backup/dir
```
*Note: La commande restore gère intelligemment les dépendances clés étrangères via une insertion multi-passes.*

---

## 4. Surveillance & Monitoring

### Points de contrôle
1. **API Health**: `GET /api/health/` (doit retourner 200 OK)
2. **Logs Backend**: `make logs` (surveiller les erreurs 500)
3. **Espace Disque**: Surveiller le volume `media_volume` (stockage PDF).

---

## 5. Gestion des Incidents

| Incident | Sévérité | Action |
|----------|----------|--------|
| **Erreur 500 Import PDF** | Moyenne | Vérifier logs rasterization (Tesseract/Poppler). |
| **Lock bloqué** | Basse | Admin peut force-unlock via API ou Admin Panel. |
| **Perte de données** | **CRITIQUE** | Utiliser procédure `restore` avec le dernier backup valide. |

---

## 6. Historique des Audits

- **26/01/2026**: Audit de Sécurité & Robustesse (Alaeddine BEN RHOUMA). **Status: PASS**.
  - Fix: RBAC Permissions.
  - Fix: Restore Command.
  - Fix: CI Pipeline Downgrade (Actions v3/v4).