# Zenflow Compliance – Korrigo

## Règles minimales (exécution)
- Travailler dans le repo principal : `/home/alaeddine/viatique__PMF`
- Ne pas livrer depuis un worktree.
- Avant commit/push : `git status --porcelain` doit être vide.
- Toute modification CI/CD doit être vérifiée par une exécution GitHub Actions verte.

## Preuves attendues
- SHA de commit + `origin/main` synchronisé
- Logs de tests backend (pytest) et build frontend
- Lien(s) des runs CI GitHub Actions

## Sécurité
- Ne jamais logger des secrets (PAT, clés SSH, mots de passe).
- Ne jamais committer des `.env` réels.

## Politique de commits
- Commits clairs (conventional commits recommandés)
- Pas de force-push sur `main` (sauf décision explicitement actée)
