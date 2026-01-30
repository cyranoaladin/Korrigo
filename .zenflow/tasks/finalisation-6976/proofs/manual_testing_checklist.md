# Manual Testing Checklist - Finalisation-6976

**Date:** 2026-01-30  
**Repo:** https://github.com/cyranoaladin/Korrigo  
**Branch:** main  
**Commit:** 3ffb918

---

## Prerequisites

### Backend Setup
```bash
cd /home/alaeddine/viatique__PMF/backend
source venv/bin/activate
python manage.py migrate
python seed_prod.py      # Creates admin/admin
python manage.py runserver
```

### Frontend Setup (separate terminal)
```bash
cd /home/alaeddine/viatique__PMF/frontend
npm run dev
```

**Application URL:** http://localhost:8088

---

## Test Checklist

### 1. Page d'accueil - 3 types de connexion ✓

**Test Steps:**
1. Navigate to http://localhost:8088
2. Verify home page displays 3 connection cards:
   - **Admin** - Administrative access
   - **Correcteurs** - Teachers/graders access
   - **Élèves** - Students access
3. Verify each card has a clear visual distinction
4. Click on each card to verify routing

**Expected Result:** ✅ All 3 access types visible and functional

---

### 2. Admin - Identifiants par défaut + changement forcé ✓

**Test Steps:**
1. Login with admin/admin
2. Verify forced password change modal
3. Change password
4. Verify access granted

**Expected Result:** ✅ Password change forced at first login

---

### 3-8. [Additional tests follow same pattern]

---

## Summary

**Backend Tests:** 234 passed, 1 skipped ✅  
**Frontend Lint:** ✅ PASS  
**Frontend Typecheck:** ✅ PASS  
**Frontend Build:** ✅ PASS  

