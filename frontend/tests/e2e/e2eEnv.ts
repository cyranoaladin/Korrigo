// Centralised E2E env contract for Playwright specs.
//
// Defaults are aligned with `backend/scripts/seed_e2e.py` and `.env.e2e.example`.

export const ADMIN_USER =
  process.env.E2E_ADMIN_USERNAME ||
  process.env.E2E_ADMIN_USER ||
  'admin'

export const ADMIN_PASS =
  process.env.E2E_ADMIN_PASSWORD ||
  process.env.E2E_ADMIN_PASS ||
  'admin'

export const TEACHER_USER =
  process.env.E2E_TEACHER_USERNAME ||
  process.env.E2E_TEACHER_USER ||
  'prof1'

export const TEACHER_PASS =
  process.env.E2E_TEACHER_PASSWORD ||
  process.env.E2E_TEACHER_PASS ||
  'password'

export const DIRECTION_USER =
  process.env.E2E_DIRECTION_USERNAME ||
  process.env.E2E_DIRECTION_USER ||
  'direction_e2e'

export const DIRECTION_PASS =
  process.env.E2E_DIRECTION_PASSWORD ||
  process.env.E2E_DIRECTION_PASS ||
  'direction-password'

export const STUDENT_EMAIL =
  process.env.E2E_STUDENT_EMAIL ||
  'student-e2e-001@example.test'

export const STUDENT_PASS =
  process.env.E2E_STUDENT_PASSWORD ||
  process.env.E2E_STUDENT_PASS ||
  '15032005'
