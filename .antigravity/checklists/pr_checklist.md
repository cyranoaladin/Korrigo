# Pull Request Checklist

## Avant de Soumettre un PR

Cette checklist doit être complétée **avant** de créer une Pull Request.

---

## 1. Code Quality

- [ ] Le code compile/run sans erreur
- [ ] Pas de code commenté ou de debug statements (console.log, print)
- [ ] Pas de TODOs non résolus (ou documentés dans issue)
- [ ] Code formaté selon standards (PEP 8 pour Python, ESLint pour JS)
- [ ] Pas de warnings du linter
- [ ] Pas de code dupliqué (DRY respecté)
- [ ] Naming clair et explicite (variables, fonctions, classes)

---

## 2. Fonctionnalité

- [ ] La feature/fix fonctionne comme attendu
- [ ] Edge cases testés
- [ ] Erreurs gérées gracefully
- [ ] Messages d'erreur clairs pour l'utilisateur
- [ ] Pas de régression sur fonctionnalités existantes

---

## 3. Tests

- [ ] Tests unitaires écrits pour nouvelle logique métier
- [ ] Tests d'intégration pour workflows complets
- [ ] Tests de permissions pour endpoints sensibles
- [ ] Tous les tests passent (`pytest` backend, `vitest` frontend)
- [ ] Coverage acceptable (>70% pour code critique)
- [ ] Tests lisibles et maintenables

---

## 4. Backend Spécifique

- [ ] Modèles Django cohérents avec migrations
- [ ] Migrations créées et testées (`makemigrations`, `migrate`)
- [ ] Migrations nommées explicitement (--name)
- [ ] Permissions explicites sur tous les endpoints (pas de AllowAny sauf justifié)
- [ ] Validation des inputs (serializers)
- [ ] Queries optimisées (select_related, prefetch_related)
- [ ] Transactions atomiques pour opérations critiques
- [ ] Logique métier dans services, pas dans views
- [ ] Logging approprié pour actions importantes

---

## 5. Frontend Spécifique

- [ ] Composition API utilisée (pas Options API)
- [ ] Props et emits typés
- [ ] Pas de logique métier dans composants
- [ ] Services API pour toutes les calls backend
- [ ] CSRF token configuré
- [ ] Pas de v-html avec input utilisateur non sanitisé
- [ ] Keys uniques sur v-for
- [ ] Loading states et error handling
- [ ] Responsive design vérifié

---

## 6. Sécurité

### CRITIQUE (Obligatoire)

- [ ] Pas de secrets en dur (API keys, passwords, tokens)
- [ ] Pas de AllowAny sur endpoints sensibles
- [ ] Validation des entrées utilisateur (backend + frontend)
- [ ] Permissions vérifiées pour accès données sensibles
- [ ] CSRF protection active
- [ ] Pas de SQL injection possible (ORM utilisé)
- [ ] Pas de XSS possible (v-html validé, inputs sanitisés)
- [ ] File uploads validés (type, taille)

### Si Applicable

- [ ] Authentification testée
- [ ] Autorisation testée (rôles, permissions)
- [ ] Rate limiting configuré sur endpoints sensibles
- [ ] Logs de sécurité ajoutés pour actions critiques
- [ ] Pas de données sensibles dans logs

---

## 7. Database & Migrations

- [ ] Migrations cohérentes avec modèles
- [ ] Migrations testées localement
- [ ] Pas de perte de données (ou documentée et acceptée)
- [ ] Migrations réversibles (ou non-réversible justifié)
- [ ] Indexes ajoutés pour queries fréquentes
- [ ] Contraintes DB-level ajoutées si nécessaire
- [ ] Relations avec on_delete explicite

---

## 8. PDF Processing (si applicable)

- [ ] Pas de perte de pages
- [ ] Pas de perte d'annotations
- [ ] Coordonnées normalisées [0, 1]
- [ ] PDF final assigné à Copy
- [ ] Qualité visuelle validée
- [ ] Gestion mémoire OK (streaming si gros fichiers)
- [ ] Logging complet du pipeline

---

## 9. Documentation

- [ ] README mis à jour si nécessaire
- [ ] Docstrings ajoutés pour fonctions/classes complexes
- [ ] Comments ajoutés où logique non évidente
- [ ] ADR (Architecture Decision Record) si décision architecturale majeure
- [ ] API endpoints documentés (si nouveaux)
- [ ] Variables d'environnement documentées dans .env.example

---

## 10. Git

- [ ] Commit messages clairs et descriptifs
- [ ] Commits atomiques (une feature/fix par commit)
- [ ] Pas de fichiers non nécessaires (.pyc, __pycache__, node_modules, .env)
- [ ] .gitignore à jour
- [ ] Branch nommée explicitement (feature/*, fix/*, refactor/*)
- [ ] Rebase sur main récent (pas de conflits)

---

## 11. Review Preparation

- [ ] PR title clair et descriptif
- [ ] PR description explique quoi, pourquoi, comment
- [ ] Screenshots/GIFs si changements UI
- [ ] Breaking changes documentés
- [ ] Migrations listées dans description
- [ ] Dépendances nouvelles listées
- [ ] Self-review effectué (relu son propre code)

---

## 12. Performance

- [ ] Pas de N+1 queries
- [ ] Pas de boucles lourdes dans le code critique
- [ ] Pas de chargement complet de gros fichiers en mémoire
- [ ] Celery utilisé pour tâches longues (>5s)
- [ ] Caching approprié (si applicable)
- [ ] Lazy loading / code splitting frontend (si applicable)

---

## 13. Production Readiness

- [ ] Configuration via variables d'environnement
- [ ] Pas de hardcoded URLs/paths
- [ ] Logs de niveau approprié (INFO/WARNING/ERROR)
- [ ] Pas de DEBUG statements en production
- [ ] Error handling pour tous les cas d'erreur
- [ ] Graceful degradation si service externe down

---

## Template PR Description

```markdown
## Description

[Décrire la feature/fix en quelques lignes]

## Type de changement

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Documentation
- [ ] Breaking change

## Quoi

- [Liste des changements]

## Pourquoi

- [Raison de ce changement]

## Comment

- [Approche technique utilisée]

## Tests

- [Description des tests ajoutés]
- [ ] Tous les tests passent

## Migrations

- [ ] Pas de migration
- [ ] Migration incluse : `0003_add_student_to_copy.py`

## Screenshots (si UI)

[Ajouter screenshots]

## Checklist

- [ ] Code review effectué par moi-même
- [ ] Tests écrits et passent
- [ ] Documentation mise à jour
- [ ] Pas de breaking change (ou documenté)
- [ ] PR Checklist complète

## Notes pour Reviewers

[Points d'attention spécifiques]
```

---

## Après Création du PR

- [ ] CI/CD pass (tests automatiques)
- [ ] Pas de conflits avec main
- [ ] Au moins 1 reviewer assigné
- [ ] Labels ajoutés (bug, feature, security, etc.)
- [ ] Milestone/Sprint assigné (si applicable)

---

## Review Reçue

- [ ] Commentaires review lus et compris
- [ ] Questions des reviewers répondues
- [ ] Modifications demandées implémentées
- [ ] Self-review après modifications
- [ ] Re-request review après modifications

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : Obligatoire pour tous les PRs
