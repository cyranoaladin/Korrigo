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

export const STUDENT_EMAIL =
  process.env.E2E_STUDENT_EMAIL ||
  'jean.e2e@example.com'

export const STUDENT_PASS =
  process.env.E2E_STUDENT_PASSWORD ||
  process.env.E2E_STUDENT_PASS ||
  'StudentE2E!2026'
