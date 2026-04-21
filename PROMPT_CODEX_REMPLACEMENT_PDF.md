# PROMPT POUR CODEX - Remplacement PDF MNIF YASMINE

## Contexte

L'utilisateur demande de remplacer la copie existante de **MNIF YASMINE** (née le 28/03/2011, classe 3.3) par un nouveau PDF fourni, tout en gardant les annotations, notes et métadonnées.

## Ce qui a déjà été fait (mais ne fonctionne pas visuellement)

### 1. Remplacement du PDF source
- Fichier uploadé : `/home/alaeddine/Bureau/KORRIGO/korrigo_v2_improved/MNIF_YASMINE_28032011_Complet.pdf`
- Copié sur le serveur : `/app/media/exams/individual/MNIF_YASMINE_28032011_Complet.pdf`
- La base de données pointe maintenant vers ce fichier (champ `pdf_source`)

### 2. Extraction des nouvelles images
- Script Python exécuté sur le serveur production
- 9 pages extraites du nouveau PDF en PNG (1240×1754 px, 150 DPI)
- Images stockées dans : `/app/media/copies/pages/copy_e4fab17c_page_001.png` à `page_009.png`
- Le booklet de la copie a été mis à jour avec les nouveaux chemins d'images

### 3. Modifications backend
- `CopySerializer` : ajout de `pdf_source_url` pour exposer le PDF source
- `views_my_students.py` : ajout de `pdf_source_url` dans l'API bilan

### 4. Modifications frontend
- `StudentBilan.vue` : modification de `openPdf()` pour utiliser `pdf_source_url` en priorité

## Le problème actuel

**L'utilisateur ne voit pas le changement dans l'interface admin** (page Résultats/CorrectorDesk).

Les images affichées dans le CorrectorDesk semblent toujours être les anciennes.

## Diagnostic probable

1. **Cache navigateur** : Les images ont les mêmes URLs (car les chemins n'ont pas changé, seulement les fichiers)
2. **Cache nginx** : Possible mise en cache des images au niveau du serveur
3. **Invalidation** : Le navigateur ou le serveur sert encore les anciennes versions

## Informations clés

### Copie concernée
- **ID** : `e4fab17c-b354-471d-9260-c380501880f0`
- **Anonymous ID** : `69CB-237`
- **Élève** : MNIF YASMINE (ID: 315)
- **Examen** : DNB_2026
- **Status** : FINALIZED
- **Booklet ID** : `13818846-5551-4024-a0c7-1bac60727af7`

### Serveur production
- **IP** : `88.99.254.59`
- **SSH** : `root@88.99.254.59`
- **Chemin projet** : `/var/www/labomaths/korrigo/`
- **Media** : `/app/media/` (dans le conteneur backend)

### URLs importantes
- **API Health** : `https://korrigo.labomaths.tn/api/health/`
- **CorrectorDesk** : `https://korrigo.labomaths.tn/corrector-desk/{copy_id}`

## Tâche exacte à réaliser

L'utilisateur doit **voir le nouveau PDF** dans l'interface. Il faut s'assurer que :

1. **Le cache est invalidé** (navigateur ET serveur)
2. **Les nouvelles images sont effectivement servies** quand on ouvre le CorrectorDesk
3. **La cohérence est vérifiée** entre :
   - Admin/CorrectorDesk (doit afficher les nouvelles images)
   - Correcteur/StudentBilan (doit afficher les nouvelles images)
   - PDF téléchargeable (doit être le nouveau PDF)

## Actions suggérées

1. **Vider le cache nginx** :
   ```bash
   ssh root@88.99.254.59 "docker exec docker-nginx-1 nginx -s reload"
   ```

2. **Vérifier que les nouvelles images sont bien accessibles** via l'API media :
   ```bash
   curl -I https://korrigo.labomaths.tn/api/media/copies/pages/copy_e4fab17c_page_001.png
   ```

3. **Ajouter des headers de cache-busting** dans la réponse API pour forcer le rechargement

4. **Vérifier dans le shell Django** que les booklets retournent bien les nouveaux chemins

5. **Tester directement** l'affichage d'une image dans le navigateur

6. **Si nécessaire** : modifier le frontend pour ajouter un paramètre de cache-busting (timestamp) aux URLs d'images

## Contraintes critiques

- **NE PAS** modifier les annotations (44 préservées)
- **NE PAS** modifier les scores (17.5/20 préservé)
- **NE PAS** toucher à la base de données des notes
- **NE PAS** régénérer le PDF final corrigé (c'est un autre fichier)

## Vérification finale

L'utilisateur doit confirmer qu'il voit :
- Le **nouveau contenu** du PDF dans le CorrectorDesk
- Les **annotations toujours présentes** sur les nouvelles images
- Le **PDF source téléchargeable** (via le bouton dans StudentBilan)
