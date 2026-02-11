/**
 * E2E Authentication Helpers
 *
 * Credentials read from environment variables to maintain contract with seed.
 */

export const CREDS = {
  admin: {
    username: process.env.E2E_ADMIN_USERNAME || 'admin',
    password: process.env.E2E_ADMIN_PASSWORD || 'admin',
  },
  teacher: {
    username: process.env.E2E_TEACHER_USERNAME || 'prof1',
    password: process.env.E2E_TEACHER_PASSWORD || 'password',
  },
  student: {
    ine: process.env.E2E_STUDENT_INE || '123456789',
    lastname: process.env.E2E_STUDENT_LASTNAME || 'E2E_STUDENT',
  },
};
