# Architecture Decision Records (ADR)

## Objectif

Ce dossier documente les **décisions architecturales majeures** du projet Viatique.

Ces décisions sont :
- **Irréversibles** ou coûteuses à changer
- **Structurantes** pour le projet
- **Documentées** pour éviter les remises en question

## Format ADR

Chaque ADR suit le template :

```markdown
# ADR-XXX : [Titre de la décision]

## Statut
[Proposé | Accepté | Déprécié | Remplacé par ADR-YYY]

## Contexte
Quel problème devons-nous résoudre ?

## Décision
Quelle solution avons-nous choisie ?

## Conséquences
- Positives : ...
- Négatives : ...
- Risques : ...

## Alternatives considérées
1. Alternative A : pourquoi rejetée
2. Alternative B : pourquoi rejetée

## Date
YYYY-MM-DD
```

## Liste des ADR

- [ADR-001](./ADR-001-student-authentication-model.md) - Modèle d'authentification élève sans Django User
- [ADR-002](./ADR-002-pdf-coordinate-normalization.md) - Normalisation des coordonnées d'annotations [0, 1]
- [ADR-003](./ADR-003-copy-status-state-machine.md) - Machine à états pour le statut des copies

---

## Quand Créer un ADR

Créer un ADR pour toute décision :
- Qui impacte l'architecture globale
- Qui choisit une technologie majeure
- Qui définit un pattern obligatoire
- Qui a des conséquences long terme
- Qui est débattue au sein de l'équipe

**Ne PAS créer d'ADR pour** :
- Choix d'implémentation locale
- Configuration temporaire
- Décisions facilement réversibles

---

**Version** : 1.0
**Date** : 2026-01-21
