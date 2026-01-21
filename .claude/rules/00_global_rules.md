# Règles Globales du Projet Viatique

## Statut : OBLIGATOIRE

Ces règles s'appliquent à **l'ensemble du projet**, sans exception.

---

## 1. Règles de Développement

### 1.1 Pas de Code Sans Objectif

**INTERDIT** :
- Coder sans ticket, issue ou objectif explicite documenté
- Ajouter des fonctionnalités "au cas où"
- Créer des abstractions prématurées
- Refactoriser du code qui fonctionne sans raison valide

**OBLIGATOIRE** :
- Chaque modification doit répondre à un besoin métier explicite
- Chaque feature doit avoir une justification documentée
- Toute abstraction doit être justifiée par au moins 3 usages réels

### 1.2 Simplicité et Clarté

**INTERDIT** :
- Over-engineering
- Code "clever" au détriment de la lisibilité
- Optimisations prématurées
- Dépendances non justifiées

**OBLIGATOIRE** :
- Code simple et lisible
- Comments uniquement si la logique n'est pas évidente
- Naming explicite (variables, fonctions, classes)
- DRY (Don't Repeat Yourself) uniquement si pertinent

### 1.3 Production First

**INTERDIT** :
- Développer sans penser à la production
- Laisser des configurations de dev en prod
- Ignorer les contraintes de performance
- Négliger la sécurité "pour plus tard"

**OBLIGATOIRE** :
- Penser production dès la conception
- Configuration séparée dev/staging/prod
- Variables d'environnement pour toute configuration
- Logs structurés et traçabilité

---

## 2. Règles de Sécurité Fondamentales

### 2.1 Pas de Secrets en Dur

**INTERDIT** :
- Secrets (API keys, passwords, tokens) dans le code
- Secrets dans les fichiers de configuration versionnés
- Secrets dans les logs
- Secrets dans les URLs

**OBLIGATOIRE** :
- Variables d'environnement pour tous les secrets
- Fichiers `.env` dans `.gitignore`
- Documentation des secrets requis (sans les valeurs)
- Rotation régulière des secrets en production

### 2.2 Principe du Moindre Privilège

**INTERDIT** :
- Permissions larges par défaut
- Accès non restreints
- Escalade de privilèges possible
- Bypass des contrôles d'accès

**OBLIGATOIRE** :
- Permissions explicites et minimales
- Authentification obligatoire par défaut
- Isolation stricte des rôles (admin/prof/élève)
- Validation des permissions à chaque requête

---

## 3. Règles de Qualité

### 3.1 Tests

**INTERDIT** :
- Déployer en production sans tests
- Modifier du code critique sans tests de régression
- Ignorer les tests qui échouent
- Tester uniquement le "happy path"
- Tests qui ne testent rien (assertions vides)

**OBLIGATOIRE** :
- Tests unitaires pour la logique métier critique
- Tests d'intégration pour les workflows complets
- Tests de permissions pour tous les endpoints sensibles
- Coverage minimum de 70% pour le code critique

### 3.1.1 Tests Minimaux Obligatoires

**Pour Chaque Endpoint API** :
- [ ] Test avec authentification valide
- [ ] Test sans authentification (doit échouer 401/403)
- [ ] Test avec mauvaises permissions (doit échouer 403)
- [ ] Test validation des inputs (données invalides)
- [ ] Test cas limites (edge cases)

**Pour Chaque Permission Custom** :
- [ ] Test permission accordée (cas valide)
- [ ] Test permission refusée (cas invalide)
- [ ] Test permission object-level si applicable

**Pour Chaque Service Métier** :
- [ ] Test cas nominal (succès)
- [ ] Test cas d'erreur (exceptions)
- [ ] Test transactions (rollback si erreur)
- [ ] Test side effects (emails, logs, etc.)

**Pour Accès Élève** (CRITIQUE) :
- [ ] Élève peut accéder à SES copies GRADED
- [ ] Élève NE PEUT PAS accéder aux copies d'autres élèves
- [ ] Élève NE PEUT PAS accéder aux copies non GRADED
- [ ] Élève NE PEUT PAS modifier quoi que ce soit
- [ ] Élève NE PEUT PAS énumérer les copies

**Pour Pipeline PDF** :
- [ ] Split PDF produit bon nombre de pages
- [ ] Merge PDF contient toutes les pages
- [ ] Annotations préservées après export
- [ ] Coordonnées normalisées [0, 1]
- [ ] PDF final assigné à Copy

**Pour Workflows Critiques** :
- [ ] Workflow correction complet (lock → annotate → finalize)
- [ ] Workflow accès élève complet (login → list → view)
- [ ] Workflow ingestion PDF (upload → split → staging → copies)

### 3.1.2 Commandes de Test

```bash
# Backend (tous les tests)
pytest backend/ -v --cov --cov-report=term-missing

# Backend (tests rapides uniquement)
pytest backend/ -v -m "not slow"

# Frontend
npm run test

# E2E (si applicable)
npm run test:e2e
```

### 3.2 Code Review

**INTERDIT** :
- Merger sans review
- Approuver sans comprendre
- Ignorer les commentaires de review

**OBLIGATOIRE** :
- Review obligatoire pour tout PR
- Tests passing avant review
- Checklist de sécurité vérifiée
- Documentation à jour

---

## 4. Règles d'Architecture

### 4.1 Séparation des Responsabilités

**INTERDIT** :
- Logique métier dans les views/controllers
- Accès direct à la DB depuis le frontend
- Couplage fort entre composants
- Dépendances circulaires

**OBLIGATOIRE** :
- Architecture en couches (Views → Services → Models)
- API REST claire et versionnée
- Séparation frontend/backend stricte
- Contracts d'interface bien définis

### 4.2 Données et Migrations

**INTERDIT** :
- Créer un modèle sans migration
- Modifier un modèle sans migration
- Migrations non testées
- Perte de données lors de migrations

**OBLIGATOIRE** :
- Migration pour chaque modification de modèle
- Migrations réversibles (up/down)
- Tests de migration sur données réelles
- Backup avant migration en production

---

## 5. Règles de Documentation

### 5.1 Documentation du Code

**INTERDIT** :
- Code non documenté si non évident
- Documentation obsolète
- Documentation qui contredit le code

**OBLIGATOIRE** :
- Docstrings pour fonctions/classes complexes
- README.md à jour
- Documentation d'architecture (.claude/)
- Changelog maintenu

### 5.2 Documentation des Décisions

**INTERDIT** :
- Décisions architecturales non documentées
- Changements de direction non justifiés
- Workarounds non expliqués

**OBLIGATOIRE** :
- ADR (Architecture Decision Records) pour décisions majeures
- Commentaires expliquant le "pourquoi" (pas le "quoi")
- Documentation des limitations connues
- Documentation des dépendances externes

---

## 6. Règles Git et Versioning

### 6.1 Commits

**INTERDIT** :
- Commits avec message vague ("fix", "update")
- Commits mélangeant plusieurs features
- Commits de fichiers de configuration locale
- Commits de secrets

**OBLIGATOIRE** :
- Messages de commit descriptifs et contextuels
- Commits atomiques (une feature/fix par commit)
- Préfixes conventionnels (feat:, fix:, refactor:, docs:)
- Vérification pre-commit (linting, tests)

### 6.2 Branches

**INTERDIT** :
- Commit direct sur main/master
- Branches de longue durée (>1 semaine)
- Branches non synchronisées

**OBLIGATOIRE** :
- Feature branches pour toute nouvelle fonctionnalité
- Branches nommées explicitement (feature/*, fix/*, refactor/*)
- Rebase régulier sur main
- Suppression des branches mergées

---

## 7. Règles Métier Viatique

### 7.1 Intégrité des Données

**INTERDIT** :
- Perte d'annotations
- Perte de copies
- Incohérence entre modèles et migrations
- Données corrompues non détectées

**OBLIGATOIRE** :
- Transactions atomiques pour opérations critiques
- Validation des données à l'entrée
- Traçabilité complète (created_at, updated_at)
- Soft delete pour données importantes

### 7.2 Workflow Métier

**INTERDIT** :
- Court-circuiter les étapes du workflow
- Modifier une copie verrouillée sans déverrouillage
- Permettre l'accès élève avant validation complète

**OBLIGATOIRE** :
- Respect strict des workflows (voir .claude/workflows/)
- États cohérents (STAGING → READY → LOCKED → GRADED)
- Verrouillage effectif pendant correction
- Validation à chaque étape

---

## 8. Règles de Performance

### 8.1 Optimisations

**INTERDIT** :
- N+1 queries non optimisées
- Chargement complet de fichiers volumineux en mémoire
- Traitements synchrones longs bloquants
- Cache non invalidé

**OBLIGATOIRE** :
- Select related / prefetch pour relations
- Streaming pour fichiers volumineux
- Tasks asynchrones (Celery) pour traitements longs
- Cache avec invalidation appropriée

---

## 9. Règles de Déploiement

### 9.1 Environnements

**INTERDIT** :
- Configuration de dev en production
- DEBUG=True en production
- ALLOWED_HOSTS=* en production
- Logs verbeux en production

**OBLIGATOIRE** :
- Variables d'environnement pour configuration
- DEBUG=False en production
- ALLOWED_HOSTS explicites
- Logs de niveau WARNING ou ERROR en production

### 9.2 Monitoring

**INTERDIT** :
- Déployer sans monitoring
- Ignorer les erreurs 500
- Aucune alerte configurée

**OBLIGATOIRE** :
- Monitoring des erreurs (Sentry ou équivalent)
- Logs centralisés
- Métriques de performance
- Alertes sur anomalies

---

## 10. Conséquences des Violations

### Niveaux de Gravité

**CRITIQUE** (Blocage immédiat) :
- Faille de sécurité
- Perte de données
- AllowAny sur endpoint sensible
- Secret en dur dans le code

**MAJEUR** (Correction avant merge) :
- Modèle sans migration
- Logique métier dans views
- Tests manquants pour code critique
- Documentation manquante

**MINEUR** (À corriger rapidement) :
- Message de commit vague
- Code non optimisé
- Manque de comments
- Style inconsistant

### Actions

- **CRITIQUE** : Rollback immédiat si en production, blocage du PR
- **MAJEUR** : Refus du PR, corrections obligatoires
- **MINEUR** : Commentaire en review, correction dans PR suivant

---

## Validation

Avant tout commit, vérifier :
- [ ] Pas de secret en dur
- [ ] Permissions explicites (pas de AllowAny sauf justifié)
- [ ] Migrations créées pour changements de modèles
- [ ] Tests passent
- [ ] Documentation à jour
- [ ] Workflow métier respecté

**En cas de doute, appliquer la règle la plus stricte.**

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : Obligatoire et non négociable
