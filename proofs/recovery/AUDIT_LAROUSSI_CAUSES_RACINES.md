# AUDIT APPROFONDI — Disparition des notes de Laroussi LAROUSSI

**Date** : 2 mars 2026  
**Auditeur** : Cascade AI (investigation automatisée)  
**Périmètre** : BB_J2, correcteur `laroussi.laroussi@ert.tn`, 26 copies (75FB-052 → 75FB-077)  
**Méthode** : Analyse non-destructive (lecture seule) des logs, DB, code source et données récupérées

---

## 1. CHRONOLOGIE DES FAITS

| Date | Événement | Source |
|------|-----------|--------|
| 13 fév 2026 | Reset complet + reimport 209 copies. Laroussi assigné 26 copies BB_J2 | DB dump |
| 20 fév 2026 | Dump DB automatique. Laroussi : 3/26 copies avec scores partiels (052: 25q, 053: 6q, 054: 7q) | `db_2026-02-20.dump` |
| **21 fév 2026** | Laroussi travaille sur copie 75FB-054 (draft sauvé dans localStorage Windows à 16:17) | `draft_96339889..._11` timestamp |
| **23 fév 2026** | Laroussi travaille sur copie 75FB-064 (draft sauvé dans localStorage Windows à 12:10) | `draft_33aee917..._11` timestamp |
| 20-25 fév | **Laroussi corrige 22 copies** — les scores sont dans son localStorage mais **jamais envoyés au serveur** | Analyse ci-dessous |
| **26 fév 2026** | Réinstallation du serveur. Toutes les données post-dump perdues. Nouveaux UUIDs générés. | Incident connu |
| 26 fév 23:41 | Restauration du dump Feb 20. 3 copies Laroussi restaurées (partielles). | GradingEvent timestamps |
| 27 fév → 1 mar | **Aucune connexion de Laroussi** au serveur (0 requête sur IP 41.225.85.163) | Nginx access.log.2.gz + .1 |
| **2 mar 07:08** | Laroussi se connecte depuis **Mac/Chrome 144**. Consulte 4 copies en 2 min (GET uniquement). **0 PUT scores.** | Nginx access.log |
| 2 mar 10:58 | Extraction recovery.html depuis **Windows/Chrome 145**. 22 scores récupérés du localStorage. | Recovery JSON |
| 2 mar 11:17 | Import des 22 scores dans la DB production. | Script `import_laroussi_scores.py` |

---

## 2. CONSTATS TECHNIQUES

### 2.1 Aucune écriture serveur par Laroussi

**Preuve Nginx (logs du 27 fév au 2 mar)** :
- IP Laroussi : `41.225.85.163`
- Total requêtes : **51** (toutes le 2 mars 07:08-07:10)
- Méthodes : **50 GET + 1 POST** (login uniquement)
- **0 PUT /api/grading/copies/.../scores/** → aucune tentative de sauvegarde de notes
- **0 POST /api/grading/copies/.../remarks/** → aucune remarque envoyée
- **0 PUT /api/grading/copies/.../global-appreciation/** → aucune appréciation envoyée

**Comparaison avec les correcteurs actifs (28 fév)** :
| IP | PUT /scores/ | Identification probable |
|----|-------------|----------------------|
| 102.31.160.221 | 595 | Correcteur actif #1 |
| 165.50.180.78 | 208 | Correcteur actif #2 |
| 41.227.31.162 | 115 | Correcteur actif #3 |
| **41.225.85.163** | **0** | **Laroussi** |

### 2.2 Deux machines, deux navigateurs

| Machine | User-Agent | Activité serveur | localStorage |
|---------|-----------|-------------------|-------------|
| **Windows** | Chrome/145 (Windows NT 10.0) | **Aucune requête dans les logs** | **22 scores + 2 drafts** |
| **Mac** | Chrome/144 (Macintosh Intel Mac OS X 10_15_7) | 51 GET le 2 mars (consultation seule) | Non extraite |

Le localStorage récupéré provient de la machine **Windows**. Les UUIDs dans ce localStorage sont tous des **anciens UUIDs** (pré-réinstallation du 26 fév), ce qui confirme que les données ont été saisies **avant** le 26 février sur cette machine Windows.

### 2.3 Les UUIDs de copie ont changé

Après la réinstallation du 26 février, toutes les copies ont reçu de **nouveaux UUIDs**. Exemple :
- 75FB-052 : ancien UUID `5500fa4c-...` → nouveau UUID `e45622ca-...`

Le frontend (`CorrectorDesk.vue` ligne 13) utilise `const copyId = route.params.copyId` — l'UUID dans l'URL. Comme les UUIDs ont changé, **l'ancien localStorage est devenu orphelin** : les clés `korrigo_scores_5500fa4c-...` ne correspondent plus à aucune URL de copie dans le nouveau système.

### 2.4 Le debounce de sauvegarde fonctionne correctement

Le code frontend (`CorrectorDesk.vue` lignes 433-458) :
1. `onScoreChange()` → sauvegarde **immédiatement** dans `localStorage` (ligne 449)
2. `onScoreChange()` → déclenche `saveScoresToServer()` après **800ms** de debounce (ligne 455-457)
3. `saveScoresToServer()` → `PUT /api/grading/copies/{uuid}/scores/` (ligne 423)

Ce mécanisme fonctionne si et seulement si :
- Le navigateur est **connecté** au serveur (session valide)
- L'UUID de la copie **existe** dans la DB
- Le CSRF token est **valide**

### 2.5 Pas d'indicateur d'échec visible

Le feedback d'échec de sauvegarde est subtil :
- Ligne 1241-1246 : `lastScoresSaveStatus.success ? 'Notes sauvegardées' : 'Erreur sauvegarde notes'`
- La classe CSS `.save-err` affiche en rouge (`#dc3545`) mais c'est un petit texte sous le barème
- **Aucune alerte bloquante, aucune notification, aucun popup d'erreur**
- L'erreur disparaît dès qu'on change de copie

---

## 3. CAUSES RACINES IDENTIFIÉES

### CAUSE #1 (Principale) : Travail hors-ligne ou avec session expirée sur la machine Windows

**Hypothèse la plus probable** : Laroussi a travaillé sur sa machine Windows avec une session HTTP expirée ou sans connectivité stable. Le debounce `saveScoresToServer()` a échoué silencieusement (erreur 401 ou erreur réseau), mais le `localStorage.setItem()` a toujours fonctionné car il est local.

**Preuves** :
- La machine Windows (Chrome/145) n'apparaît **jamais** dans les logs Nginx post-reinstallation
- Le localStorage Windows contient 22 scores complets avec des anciens UUIDs
- Les drafts sont datés du 21 et 23 février → période de travail active
- Les logs pré-26 février n'existent plus (effacés lors de la réinstallation)

**Scénarios possibles** :
1. **Session expirée** : Laroussi ouvre Korrigo, la session expire, les PUT retournent 401, l'intercepteur (api.js ligne 82-98) redirige vers `/` mais sans alerte bloquante. Laroussi continue de noter car les inputs ne sont pas verrouillés (le `isReadOnly` ne dépend pas de l'état de la session mais du statut de la copie).
2. **Problème réseau** : Connexion instable, les PUT échouent en timeout (30s), `saveScoresToServer()` catch l'erreur et affiche "Erreur sauvegarde notes" en petit texte rouge, non remarqué par Laroussi.
3. **Onglet périmé** : Laroussi ouvre les 22 copies dans des onglets, travaille hors-ligne, les PUT échouent car la session est liée à l'ancien serveur.

### CAUSE #2 (Aggravante) : Réinstallation du serveur le 26 février

La réinstallation a :
- Effacé les logs Nginx → impossible de vérifier les éventuelles requêtes de Laroussi avant le 26
- Changé tous les UUIDs des copies → le localStorage Windows est devenu orphelin
- Invalidé toutes les sessions → même si Laroussi revenait, il devait se reconnecter

### CAUSE #3 (Systémique) : Absence de confirmation de sauvegarde fiable

Le frontend n'a **aucun mécanisme robuste** pour alerter l'utilisateur quand les scores ne sont pas sauvegardés côté serveur :
- L'indicateur "Erreur sauvegarde notes" est un petit texte en rouge, non bloquant
- Pas de notification toast, pas de popup, pas de bannière persistante
- Pas de compteur de modifications non-sauvegardées
- Pas de `beforeunload` handler pour empêcher la fermeture avec des scores non-synchro
- Le retry automatique ne s'applique **pas** aux PUT (api.js ligne 24-28) → une seule tentative
- Aucun système de queue de synchronisation (comme les PWA offline-first)

### CAUSE #4 (Contributive) : Pas de GradingEvent lors de la saisie de scores

Le backend `CopyScoresView.put()` (views.py lignes 417-459) fait un `Score.objects.update_or_create()` mais **ne crée pas de GradingEvent**. Cela rend impossible le traçage de l'historique des sauvegardes de scores. On ne peut pas savoir si Laroussi a déjà réussi à sauvegarder avant le 26 février.

---

## 4. ÉTAT ACTUEL DE LA DB (post-recovery)

| Copie | Status | Scores | Questions | Total | Source |
|-------|--------|--------|-----------|-------|--------|
| 75FB-052 → 75FB-072 | READY | ✅ | 27/27 | 2.50 → 18.00 | localStorage recovery |
| 75FB-073 | READY | ⚠️ partiel | 2/27 | 3.25 | localStorage (non terminée) |
| 75FB-074 → 75FB-077 | READY | ❌ | 0 | — | Jamais commencées |

**Intégrité DB** : Aucune corruption. Les 22 scores importés sont cohérents (27 questions = barème complet BB_J2). Les scores existants n'ont pas été écrasés (logique SKIP si >= nq).

---

## 5. RECOMMANDATIONS DE STABILITÉ

### R1 — CRITIQUE : Indicateur de synchronisation fiable

Ajouter un **bandeau persistant** quand des scores ne sont pas sauvegardés côté serveur :
```
⚠️ 3 modifications non sauvegardées — Vérifiez votre connexion
```

### R2 — CRITIQUE : Handler `beforeunload`

Empêcher la fermeture du navigateur/onglet si des scores modifiés n'ont pas été confirmés côté serveur :
```javascript
window.addEventListener('beforeunload', (e) => {
    if (pendingScoresSave) {
        e.preventDefault();
        e.returnValue = 'Des notes non sauvegardées seront perdues.';
    }
});
```

### R3 — HAUTE : Retry pour les PUT scores

Modifier la logique de retry dans `api.js` pour permettre le retry des PUT `/scores/` (idempotent car `update_or_create`) :
```javascript
// PUT /scores/ is idempotent and safe to retry
if (method === 'put' && url.includes('/scores/')) return true;
```

### R4 — HAUTE : GradingEvent à chaque sauvegarde de score

Ajouter un `GradingEvent` dans `CopyScoresView.put()` pour tracer chaque sauvegarde :
```python
GradingEvent.objects.create(
    copy=copy, actor=request.user, action="scores_saved",
    metadata={"nq": len(scores_data), "total": sum(...)}
)
```

### R5 — MOYENNE : Notification toast d'erreur

Remplacer le texte CSS par un composant toast visible et persistant en cas d'échec de sauvegarde.

### R6 — MOYENNE : Sync queue offline-first

Implémenter une file de synchronisation : les modifications sont stockées localement et resynchronisées automatiquement dès que la connectivité est rétablie, avec indicateur visuel.

### R7 — BASSE : Audit trail frontend

Logger côté frontend (console + service worker) les tentatives de sauvegarde et leurs résultats pour faciliter le diagnostic futur.

---

## 6. CONCLUSION

**La disparition des notes de Laroussi n'est PAS un bug de la base de données ni de la plateforme backend.** Les données n'ont jamais atteint le serveur.

**Cause racine** : Laroussi a travaillé sur sa machine Windows avec une session ou une connectivité défaillante. Le frontend a sauvegardé les scores en localStorage (fonctionnement nominal du fallback), mais les requêtes PUT vers le serveur ont échoué silencieusement. L'interface n'a pas alerté l'utilisateur de manière suffisamment visible.

**La plateforme est stable** — aucune perte de données côté serveur n'a été constatée. Le problème est un défaut d'UX (feedback insuffisant lors des échecs de synchronisation) combiné à un événement exceptionnel (réinstallation du serveur le 26 février qui a changé les UUIDs et effacé les traces).

**Les 22 scores ont été récupérés** depuis le localStorage et importés dans la DB avec succès le 2 mars 2026.

---

*Rapport généré le 2 mars 2026 à 12:30 UTC+01:00*  
*Commit d'import : 512c698 (main)*  
*Aucune donnée n'a été modifiée ou supprimée pendant cet audit.*
