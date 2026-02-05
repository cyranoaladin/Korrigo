# ADR-001 : Modèle d'Authentification Élève Sans Django User

## Statut
✅ **Accepté** (2026-01-21)

## Contexte

Les élèves doivent pouvoir consulter leurs copies corrigées via une interface web. Nous devons décider comment gérer leur authentification et leurs permissions.

**Contraintes** :
- Accès lecture seule uniquement
- Pas de gestion de compte complexe
- Timeout court (consultation ponctuelle)
- Isolation stricte (élève A ne voit jamais copie élève B)
- Pas de système de permissions complexe nécessaire

**Options** :
1. Django User classique pour élèves
2. Session personnalisée avec `student_id` uniquement (CHOISI)
3. JWT temporaire sans compte

## Décision

**Utiliser une session personnalisée Django avec `student_id` uniquement, SANS créer de Django User.**

### Implémentation

```python
# Login élève
request.session['student_id'] = student.id
request.session.set_expiry(14400)  # 4h

# Permission custom
class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.session.get('student_id') is not None
```

### Raisons

1. **Simplicité** : Pas de gestion User/Password/Profile
2. **Sécurité** : Isolation par conception (pas d'escalade possible vers User Django)
3. **Performance** : Pas de jointure User à chaque requête
4. **Maintenance** : Moins de code, moins de complexité
5. **Expérience** : Timeout court adapté à usage ponctuel

## Conséquences

### Positives
- ✅ Isolation totale élèves ↔ système d'authentification principal
- ✅ Impossible d'escalader vers permissions Django
- ✅ Code plus simple et maintenable
- ✅ Pas de gestion mot de passe élèves
- ✅ Timeout court par défaut (4h)

### Négatives
- ❌ Pas de réutilisation du système d'auth Django
- ❌ Permissions custom nécessaires (IsStudent, IsOwnerStudent)
- ❌ Pas d'audit trail automatique via Django User

### Risques
- ⚠️ Session hijacking (mitigé par HTTPS + secure cookies)
- ⚠️ Besoin de tester exhaustivement les permissions custom

## Alternatives Considérées

### Alternative A : Django User pour élèves
**Rejetée car** :
- Complexité inutile (password reset, profile, etc.)
- Risque d'escalade de privilèges si mal configuré
- Couplage fort avec système d'auth principal

### Alternative B : JWT temporaire
**Rejetée car** :
- Pas de révocation facile
- Complexité supplémentaire côté frontend
- Session Django suffit pour usage ponctuel

## Validation

Cette décision respecte :
- ✅ Principe du moindre privilège
- ✅ Isolation stricte des rôles (règle 01_security_rules.md)
- ✅ Simplicité architecturale (règle 00_global_rules.md)

## Implémentation Requise

- [x] Modèle Student (sans User Django)
- [x] Permissions IsStudent, IsOwnerStudent
- [x] ViewSet lecture seule avec filtrage strict
- [x] Tests de sécurité (pas d'accès autres copies)
- [x] Workflow authentication_flow.md documenté

## Date
2026-01-21

## Auteur
Alaeddine BEN RHOUMA (Architecture Lead)
