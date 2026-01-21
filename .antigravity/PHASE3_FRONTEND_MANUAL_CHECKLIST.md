# PHASE 3.8: Final Production Verification Checklist

**Objectif** : Valider CorrectorDesk avec données réalistes, UX robuste et raccourcis.

## 1. Génération de Données

- [ ] Lancer : `./scripts/generate_test_fixtures.sh`
- [ ] Noter les **UUIDs** (READY, STAGING, LOCKED).
- [ ] Vérifier que le script affiche bien "Validation -> READY -> Add Annotations -> Lock" pour la copie Locked (pas de flip bizarre).

## 2. Validation UX (Copie READY)

1.  **Image Error** : Modifier le code ou couper internet/server -> Vérifier que l'image affiche une bannière d'erreur et un bouton "Retry". 
2.  **Raccourcis Clavier** :
    - [ ] Tracer un rectangle. L'éditeur s'ouvre.
    - [ ] Ne pas focus le bouton Cancel. Appuyer sur **Esc**. L'éditeur doit fermer.
    - [ ] Tracer un nouveau rectangle. Taper du texte.
    - [ ] Faire **Ctrl+Enter** (ou Cmd+Enter). L'annotation doit se sauvegarder.
3.  **Pagination Robuste** :
    - [ ] Aller à la dernière page.
    - [ ] Vérifier que "Next" est désactivé.
4.  **Auto Close** :
    - [ ] Ouvrir l'éditeur d'annotation.
    - [ ] Dans un autre onglet/terminal, locker la copie (ou cliquer "Lock" si accessible).
    - [ ] L'éditeur doit se fermer automatiquement (car annotations revenues disabled).

## 3. Validation Read-Only (LOCKED)

1.  **Curseur** : Survoler l'image. Le curseur doit être "not-allowed" (interdit).
2.  **Selection** : Essayer de sélectionner du texte sur l'image ou tracer. Rien ne se passe.

## 4. Robustesse Technique

- [ ] **Delete 204** : Vérifier que la suppression marche sans erreur JSON (parfois 204 No Content ne renvoie rien, le front doit gérer).
- [ ] **Pages=0** : Si une copie n'a pas d'image, le viewer doit afficher "No Pages" proprement sans crash console.

## Troubleshooting

- **403 Forbidden** : Vérifier credentials `teacher_test`.
- **Images 404** : Vérifier `MEDIA_URL` et montage volume docker.
