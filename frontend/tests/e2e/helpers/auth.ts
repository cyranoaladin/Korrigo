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
    birth_date: process.env.E2E_STUDENT_BIRTH_DATE || '2005-06-15',
  },
  other_student: {
    ine: '987654321',
    birth_date: '2005-03-20',
  },
};
