/**
 * E2E Authentication Helpers
 *
 * Credentials read from environment variables to maintain contract with seed.
 * Student auth: email + password (DOB in DDMMYYYY format by default).
 */

export const CREDS = {
  admin: {
    username: process.env.E2E_ADMIN_USERNAME || 'admin',
    password: process.env.E2E_ADMIN_PASSWORD || 'Korrigo2026!',
  },
  teacher: {
    username: process.env.E2E_TEACHER_USERNAME || 'prof1',
    password: process.env.E2E_TEACHER_PASSWORD || 'password',
  },
  student: {
    email: process.env.E2E_STUDENT_EMAIL || 'khalil.abdelmoula-e@ert.tn',
    password: process.env.E2E_STUDENT_PASSWORD || '26092007',
    first_name: 'KHALIL',
    last_name: 'ABDELMOULA',
  },
  other_student: {
    email: process.env.E2E_OTHER_STUDENT_EMAIL || 'amine.abouda-e@ert.tn',
    password: process.env.E2E_OTHER_STUDENT_PASSWORD || '10072008',
    first_name: 'AMINE',
    last_name: 'ABOUDA',
  },
};
