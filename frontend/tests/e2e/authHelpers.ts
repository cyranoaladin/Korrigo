import { expect, type Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { ADMIN_PASS, ADMIN_USER, STUDENT_EMAIL, STUDENT_PASS, TEACHER_PASS, TEACHER_USER } from './e2eEnv'

let teacherStorageState: any = null
let adminStorageState: any = null
let directionStorageState: any = null

const PROD_HOST = 'korrigo.labomaths.tn'
const isProdE2E = (process.env.E2E_BASE_URL || '').includes(PROD_HOST)

function createProdSession(username: string) {
  const script = `
from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, get_user_model
from django.utils.module_loading import import_string
SessionStore = import_string(settings.SESSION_ENGINE + ".SessionStore")
user = get_user_model().objects.get(username="${username.replace(/"/g, '\\"')}")
session = SessionStore()
session[SESSION_KEY] = str(user.pk)
session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
session[HASH_SESSION_KEY] = user.get_session_auth_hash()
session.save()
print(session.session_key)
`.trim()
  const encodedScript = Buffer.from(script, 'utf8').toString('base64')
  const remoteCommand = `docker exec docker-backend-1 bash -lc 'python manage.py shell -c "$(printf %s ${encodedScript} | base64 -d)"'`

  return execFileSync('ssh', [
    'root@88.99.254.59',
    remoteCommand,
  ], { encoding: 'utf8' }).trim()
}

function runProdDjangoScript(script: string) {
  const encodedScript = Buffer.from(script.trim(), 'utf8').toString('base64')
  const remoteCommand = `docker exec docker-backend-1 bash -lc 'python manage.py shell -c "$(printf %s ${encodedScript} | base64 -d)"'`

  return execFileSync('ssh', [
    'root@88.99.254.59',
    remoteCommand,
  ], { encoding: 'utf8' }).trim()
}

function resetProdPassword(username: string, password: string) {
  if (!isProdE2E) return

  if (username === ADMIN_USER) adminStorageState = null
  if (username === TEACHER_USER) teacherStorageState = null
  if (username === process.env.E2E_DIRECTION_USER) directionStorageState = null

  runProdDjangoScript(`
from django.contrib.auth import get_user_model
user = get_user_model().objects.get(username=${JSON.stringify(username)})
user.set_password(${JSON.stringify(password)})
user.is_active = True
user.save(update_fields=["password", "is_active"])
if hasattr(user, "profile"):
    user.profile.must_change_password = False
    user.profile.save(update_fields=["must_change_password"])
print("password reset")
  `)
}

export function resetProdAdminPassword() {
  resetProdPassword(ADMIN_USER, ADMIN_PASS)
}

export function resetProdTeacherPassword() {
  resetProdPassword(TEACHER_USER, TEACHER_PASS)
}

export function resetProdStudentPassword() {
  resetProdPassword(STUDENT_EMAIL, STUDENT_PASS)
}

async function applyProdSession(page: Page, username: string, path: string) {
  const sessionKey = createProdSession(username)
  await page.context().clearCookies()
  await page.context().addCookies([{
    name: 'sessionid',
    value: sessionKey,
    domain: PROD_HOST,
    path: '/',
    httpOnly: true,
    secure: true,
    sameSite: 'Lax',
  }])
  await page.goto(path)
}

export async function loginAsTeacher(page: Page) {
  await page.context().clearCookies()
  if (teacherStorageState) {
    await page.context().addCookies(teacherStorageState.cookies)
    await page.goto('/corrector-dashboard')
    const validCachedSession = await page.waitForURL('**/corrector-dashboard', { timeout: 10000 })
      .then(() => page.locator('[data-testid="corrector-dashboard"]').isVisible({ timeout: 10000 }))
      .catch(() => false)
    if (validCachedSession) {
      return
    }
    teacherStorageState = null
    await page.context().clearCookies()
  }

  if (isProdE2E) {
    await applyProdSession(page, TEACHER_USER, '/corrector-dashboard')
    await page.waitForURL('**/corrector-dashboard', { timeout: 10000 })
    await expect(page.locator('[data-testid="corrector-dashboard"]')).toBeVisible({ timeout: 10000 })
    teacherStorageState = await page.context().storageState()
    return
  }

  await page.goto('/teacher/login')
  await page.locator('[data-testid="login.username"]').fill(TEACHER_USER)
  await page.locator('[data-testid="login.password"]').fill(TEACHER_PASS)
  await page.locator('[data-testid="login.submit"]').click()
  await page.waitForURL('**/corrector-dashboard', { timeout: 10000 })
  await expect(page.locator('[data-testid="corrector-dashboard"]')).toBeVisible({ timeout: 10000 })
  teacherStorageState = await page.context().storageState()
}

export async function loginAsAdmin(page: Page) {
  await page.context().clearCookies()
  if (adminStorageState) {
    await page.context().addCookies(adminStorageState.cookies)
    await page.goto('/admin/dashboard')
    const validCachedSession = await page.waitForURL('**/admin/dashboard', { timeout: 10000 })
      .then(() => page.locator('[data-testid="admin-dashboard"]').isVisible({ timeout: 10000 }))
      .catch(() => false)
    if (validCachedSession) {
      return
    }
    adminStorageState = null
    await page.context().clearCookies()
  }

  if (isProdE2E) {
    await applyProdSession(page, ADMIN_USER, '/admin/dashboard')
    await page.waitForURL('**/admin/dashboard', { timeout: 10000 })
    await expect(page.locator('[data-testid="admin-dashboard"]')).toBeVisible({ timeout: 10000 })
    adminStorageState = await page.context().storageState()
    return
  }

  await page.goto('/admin/login')
  await page.locator('[data-testid="login.username"]').fill(ADMIN_USER)
  await page.locator('[data-testid="login.password"]').fill(ADMIN_PASS)
  await page.locator('[data-testid="login.submit"]').click()
  await page.waitForURL('**/admin/dashboard', { timeout: 10000 })
  await expect(page.locator('[data-testid="admin-dashboard"]')).toBeVisible({ timeout: 10000 })
  adminStorageState = await page.context().storageState()
}

export async function loginAsDirection(page: Page) {
  const directionUser = process.env.E2E_DIRECTION_USER || 'gilles.emardlacroix@ert.tn'
  await page.context().clearCookies()
  if (directionStorageState) {
    await page.context().addCookies(directionStorageState.cookies)
    await page.goto('/direction/dashboard')
    const validCachedSession = await page.waitForURL('**/direction/dashboard', { timeout: 10000 })
      .then(() => !page.url().includes('/admin/login') && !page.url().endsWith('/'))
      .catch(() => false)
    if (validCachedSession) {
      return
    }
    directionStorageState = null
    await page.context().clearCookies()
  }

  if (isProdE2E) {
    await applyProdSession(page, directionUser, '/direction/dashboard')
    await page.waitForURL('**/direction/dashboard', { timeout: 10000 })
    directionStorageState = await page.context().storageState()
    return
  }

  const directionPass = process.env.E2E_DIRECTION_PASS
  if (!directionPass) {
    throw new Error('E2E_DIRECTION_PASS is required for non-production Direction login')
  }
  await page.goto('/admin/login')
  await page.waitForLoadState('networkidle')
  await page.locator('[data-testid="login.username"]').fill(directionUser)
  await page.locator('[data-testid="login.password"]').fill(directionPass)
  await page.locator('[data-testid="login.submit"]').click()
  await page.waitForURL('**/direction/dashboard', { timeout: 10000 })
  directionStorageState = await page.context().storageState()
}

export function clearAdminSessionCache() {
  adminStorageState = null
}
