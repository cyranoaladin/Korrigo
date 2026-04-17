# Corrector Desk Score Limit Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corriger l'affichage et la logique de dépassement de note dans le bureau correcteur pour utiliser partout le maximum réel du barème.

**Architecture:** Extraire une petite utilité testable pour calculer et formater la borne de score, puis brancher `CorrectorDesk.vue` dessus. Le changement reste strictement frontend afin de préserver les données et le workflow backend existants.

**Tech Stack:** Vue 3, Vitest, Vite

---

### Task 1: Encadrer la logique de borne par un test unitaire

**Files:**
- Create: `frontend/tests/unit/correctorDeskScoreLimits.test.ts`
- Create: `frontend/src/utils/correctorDeskScoreLimits.ts`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify it passes**

### Task 2: Brancher le composant sur la borne dynamique

**Files:**
- Modify: `frontend/src/views/admin/CorrectorDesk.vue`

- [ ] **Step 1: Remplacer les références résiduelles à `scoreExceeds20`**
- [ ] **Step 2: Afficher le message de dépassement basé sur le maximum réel**
- [ ] **Step 3: Garder inchangée la logique de finalisation déjà correcte**

### Task 3: Vérifier puis déployer le frontend

**Files:**
- Modify: `frontend/src/views/admin/CorrectorDesk.vue`
- Test: `frontend/tests/unit/correctorDeskScoreLimits.test.ts`

- [ ] **Step 1: Run targeted unit test**
- [ ] **Step 2: Run frontend build**
- [ ] **Step 3: Déployer le frontend uniquement sur la production**
- [ ] **Step 4: Vérifier le bundle servi et la page**
