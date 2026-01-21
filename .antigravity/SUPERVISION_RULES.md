# Règles de Supervision d'Antigravity

## Statut : OBLIGATOIRE POUR TOUTE IA/DÉVELOPPEUR

Ces règles définissent comment Antigravity (ou tout développeur) doit utiliser le système de gouvernance `.antigravity/`.

---

## ⛔ Règle n°1 — Interdiction de Coder Hors Gouvernance

### Principe

> **Aucune fonctionnalité, aucun refactor, aucun fix**
> tant que Antigravity n'a pas :
> 1. Identifié les règles concernées dans `rules/`
> 2. Référencé le workflow impacté dans `workflows/`
> 3. Activé les skills requis dans `skills/`

### Application

**Avant tout code, Antigravity DOIT** :

```
1. Lire la demande utilisateur
2. Identifier les règles applicables
   → "Cette fonctionnalité touche à [authentification / PDF / sécurité / etc.]"
   → "Je dois respecter : rules/01_security_rules.md section X"
3. Identifier le workflow concerné
   → "Je suis dans workflow/correction_flow.md étape Y"
4. Activer les skills appropriés
   → "J'active skills/backend_architect.md pour cette décision"
5. Vérifier la checklist applicable
   → "Avant de committer, je dois valider checklists/pr_checklist.md"
6. SEULEMENT ALORS : coder
```

### Validation

Chaque réponse d'Antigravity contenant du code doit inclure :

```markdown
## Conformité Gouvernance

**Règles respectées** :
- `rules/01_security_rules.md` § 2.3 (Permissions élève)
- `rules/05_pdf_processing_rules.md` § 5.2 (Coordonnées normalisées)

**Workflow suivi** :
- `workflows/correction_flow.md` étapes 3-4

**Skills activés** :
- `skills/backend_architect.md` (Service layer)
- `skills/security_auditor.md` (Validation permissions)

**Checklist** :
- [ ] Tests écrits
- [ ] Permissions vérifiées
- [ ] Documentation à jour
```

### Conséquences

Si Antigravity code sans avoir :
- Identifié les règles → **Code rejeté**
- Consulté le workflow → **Code rejeté**
- Activé les skills → **Code rejeté**

---

## ⛔ Règle n°2 — Toute PR Doit Citer `.antigravity/`

### Principe

> Chaque Pull Request (ou équivalent) doit **explicitement** mentionner :
> - Règles respectées
> - Workflows suivis
> - Checklist validée

### Template PR Obligatoire

```markdown
## Description
[Description de la feature/fix]

## Conformité .antigravity/

### Règles Respectées
- [ ] `rules/00_global_rules.md` - Production first ✅
- [ ] `rules/01_security_rules.md` § 2.1 - Permissions explicites ✅
- [ ] `rules/02_backend_rules.md` § 4.2 - Service layer ✅

### Workflows Suivis
- [ ] `workflows/correction_flow.md` - Étapes 1-7 complètes ✅

### Skills Activés
- [x] Backend Architect (service layer design)
- [x] Security Auditor (permissions review)
- [ ] PDF Processing Expert (non applicable)

### Checklist Validée
- [ ] `checklists/pr_checklist.md` - 100% complète ✅

### ADR (si applicable)
- Aucune nouvelle décision architecturale
- Conforme à ADR-001 (authentification élève)

## Tests
[Description des tests ajoutés]

## Notes
[Notes additionnelles]
```

### Validation

**Critères de refus PR** :
- Pas de section "Conformité .antigravity/" → ❌ REFUSÉ
- Règles non citées → ❌ REFUSÉ
- Checklist non complétée → ❌ REFUSÉ
- Violation d'une règle critique → ❌ REFUSÉ IMMÉDIATEMENT

---

## ⛔ Règle n°3 — Le `.antigravity/` Est la Source d'Autorité

### Principe

> En cas de conflit entre :
> - Intuition vs `.antigravity/` → `.antigravity/` gagne
> - Rapidité vs `.antigravity/` → `.antigravity/` gagne
> - "Solution facile" vs `.antigravity/` → `.antigravity/` gagne

### Hiérarchie des Décisions

```
1. `.antigravity/rules/` ← NON NÉGOCIABLE
2. `.antigravity/workflows/` ← OBLIGATOIRE
3. `.antigravity/skills/` ← GUIDE
4. Intuition/expérience ← SI CONFORME AUX 3 CI-DESSUS
```

### Exemples de Conflits

#### Exemple 1 : Rapidité vs Sécurité

**Situation** : "Pour aller plus vite, je mets AllowAny temporairement"

**Décision** :
- ❌ **INTERDIT** par `rules/01_security_rules.md`
- ✅ Solution conforme : Implémenter permission explicite immédiatement

**Rationale** : La sécurité n'est JAMAIS "temporaire"

#### Exemple 2 : Simplicité vs Workflow

**Situation** : "Je skip l'étape de staging et crée directement les copies"

**Décision** :
- ❌ **INTERDIT** par `workflows/pdf_ingestion_flow.md`
- ✅ Solution conforme : Suivre le workflow complet avec validation manuelle

**Rationale** : Le workflow garantit la qualité et la traçabilité

#### Exemple 3 : Expérience vs Règle

**Situation** : "Dans mon expérience, les coordonnées absolues suffisent"

**Décision** :
- ❌ **INTERDIT** par `rules/05_pdf_processing_rules.md` + `decisions/ADR-002`
- ✅ Solution conforme : Coordonnées normalisées [0, 1]

**Rationale** : L'ADR documente la décision et les alternatives rejetées

### Procédure de Contestation

Si Antigravity estime qu'une règle doit être modifiée :

1. **NE PAS** ignorer la règle actuelle
2. **APPLIQUER** la règle en vigueur
3. **DOCUMENTER** la proposition de modification
4. **SOUMETTRE** un ADR proposant le changement
5. **ATTENDRE** validation avant application

**En aucun cas** : coder en contradiction avec `.antigravity/` actuel

---

## Application Pratique

### Workflow d'Antigravity

```
Requête utilisateur
    ↓
Analyse de la demande
    ↓
Consultation .antigravity/
├─ rules/ (que dois-je respecter ?)
├─ workflows/ (quelle étape suis-je ?)
├─ skills/ (quelles compétences activer ?)
└─ decisions/ (y a-t-il un ADR ?)
    ↓
Validation conformité
    ↓
SI conforme → Coder
SI non conforme → Proposer solution conforme ou ADR
    ↓
Tests + Checklist
    ↓
PR avec section Conformité
```

### Indicateurs de Conformité

Antigravity (ou reviewer) doit vérifier :

- [ ] Section "Conformité .antigravity/" présente dans chaque PR
- [ ] Règles citées sont correctes et applicables
- [ ] Workflow suivi est documenté
- [ ] Skills activés sont pertinents
- [ ] Checklist applicable est complétée à 100%
- [ ] Aucune violation de règle critique
- [ ] ADR consulté si décision architecturale

**Si UN SEUL indicateur est faux → PR à retravailler**

---

## Exceptions

### Cas Exceptionnels

Les seuls cas où `.antigravity/` peut être contourné :

1. **Urgence sécurité critique** (faille 0-day)
   - Action immédiate autorisée
   - Documentation a posteriori OBLIGATOIRE
   - ADR de l'exception dans les 24h

2. **Bug bloquant production**
   - Hotfix minimal autorisé
   - Conformité `.antigravity/` restaurée dans PR suivant
   - Post-mortem documenté

**Toute autre exception est interdite.**

---

## Responsabilités

### Antigravity (IA Développeur)
- Consulter `.antigravity/` avant tout code
- Citer `.antigravity/` dans chaque PR
- Respecter hiérarchie des règles
- Proposer ADR si modification nécessaire

### Reviewer (Humain)
- Vérifier conformité `.antigravity/`
- Refuser PR non conforme
- Valider checklists
- Signaler incohérences dans `.antigravity/`

### Lead Technique
- Maintenir `.antigravity/` à jour
- Valider les ADR proposés
- Faire respecter les règles
- Former l'équipe sur `.antigravity/`

---

## Sanctions (Développement)

### Violations

| Type | Sanction |
|------|----------|
| Code sans consultation `.antigravity/` | PR refusé, à retravailler |
| PR sans section Conformité | PR refusé automatiquement |
| Violation règle critique (sécurité) | Rollback + audit |
| Contournement intentionnel | Review d'équipe |

### Mesures Correctives

1. **Première violation** : Feedback + demande correction
2. **Deuxième violation** : Review obligatoire de `.antigravity/`
3. **Troisième violation** : Audit complet du code produit

---

## Conclusion

Le `.antigravity/` n'est pas une suggestion, c'est un **contrat**.

**Règle d'or** : Si vous hésitez, consultez `.antigravity/`. Si `.antigravity/` est ambigu, appliquez la règle la plus stricte.

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : OBLIGATOIRE pour tout développement sur Viatique
