# PRODUCTION RELEASE VERIFICATION CHECKLIST (Phase 3.9 HARDENED)

**Objectif** : Valider le flux de correction complet et sécurisé.

## 0. Preflight Checks (Prod)
- [ ] **Config**: Teachers ont `is_staff=True`.
- [ ] **Deps**: PyMuPDF (`fitz`) est installé.
- [ ] **Media**: Volume `MEDIA_ROOT` est monté et persistant.
- [ ] **Security**: Si `MEDIA_URL` est public, vérifier risques de leakage des images pages.
      Reco minimale (P0 doc) : servir /media/ uniquement derrière auth (reverse-proxy) OU rendre le chemin non devinable + rotation (P1).
      Point critique : pages_images contiennent des extraits de copies => données potentiellement sensibles.

## 1. Import Réel & Sécurité (P0.1)

1.  **Restriction d'accès**:
    - [ ] Login `student_test`.
    - [ ] `POST /api/exams/<id>/copies/import/` -> **403 Forbidden**.
    - [ ] `GET /api/exams/` -> **403 Forbidden**.
2.  **Succès Teacher**:
    - [ ] Login `teacher_test`.
    - [ ] Import d'un **VRAI PDF**.
    - [ ] Succès, redirection, images visibles.

## 2. Workflow & Audit (P0.3)

1.  **Workflow**:
    - [ ] Mark READY -> Annoter -> Lock.
    - [ ] Vérifier que annoter sur LOCKED est bloqué (Backend + UI).
2.  **Audit**:
    - [ ] Onglet "History" montre `IMPORT`, `VALIDATE`, `CREATE_ANN`, `LOCK`.
    - [ ] Audit endpoint `/api/copies/<id>/audit/` -> **403** pour Student.

## 3. Export Final Sécurisé (P0.4)

1.  **Gate**:
    - [ ] Copie LOCKED (pas GRADED).
    - [ ] Tenter `GET /api/copies/<id>/final-pdf/` -> **403 Forbidden**.
2.  **Success**:
    - [ ] Finalize -> GRADED.
    - [ ] Download -> **200 OK**.
    - [ ] Vérifier nom de fichier: `copy_<anon_id>_corrected.pdf`.

## 4. Quick Regression
- [ ] Pages s'affichent (concaténation Booklets OK).
- [ ] Annotations se sauvegardent.

## 5. Security & Infra (Blocking)

- [ ] **NGINX GATE** (REQUIRED):
  ```nginx
  location /media/ {
      internal;
      alias /var/www/korrigo/media/; 
      # Or reverse proxy auth
  }
  ```
- [ ] **VERIFICATION**: `curl -I https://prod/media/test.pdf` MUST return **403 Forbidden** or **404 Not Found** (if internal).
- [ ] **NO-GO**: If media is publicly accessible without auth.
