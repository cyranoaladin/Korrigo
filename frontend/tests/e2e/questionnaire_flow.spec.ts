import { test, expect } from '@playwright/test'
import { CREDS } from './helpers/auth'

const QUESTIONNAIRE_PAYLOAD = {
  _uid: 'prof1',
  q11: 4,
  q12: 5,
  q21: 'Utile',
  q25: ['Navigation entre les copies'],
  q33: 4,
  q41: 4,
  q51: 'Oui, avec quelques améliorations',
  q53: 9,
  q54: 'Ajouter plus de raccourcis clavier.',
  q55: 'Aucun bug bloquant.',
  q61: 'Satisfait(e) — bon outil, quelques ajustements à faire',
  q62: 'Très bonne expérience.'
}

async function loginAsTeacher(page) {
  await page.goto('/teacher/login')
  await page.fill('input[type="text"]', CREDS.teacher.username)
  await page.fill('input[type="password"]', CREDS.teacher.password)
  await page.click('button[type="submit"]')
  await page.waitForURL(/\/corrector-dashboard/)
  await page.waitForLoadState('networkidle')
}

async function loginAsAdmin(page) {
  await page.goto('/admin/login')
  await page.fill('[data-testid="login.username"]', CREDS.admin.username)
  await page.fill('[data-testid="login.password"]', CREDS.admin.password)
  await page.click('[data-testid="login.submit"]')
  await page.waitForURL(/\/admin-dashboard/)
  await page.waitForLoadState('networkidle')
}

async function ensureQuestionnaireSubmitted(page) {
  const statusResponse = await page.request.get('/api/grading/questionnaire/')
  const statusBody = await statusResponse.json()
  if (statusBody.has_response) {
    return
  }

  const submitStatus = await page.evaluate(async (payload) => {
    const csrfToken = document.cookie
      .split('; ')
      .find((cookie) => cookie.startsWith('csrftoken='))
      ?.split('=')[1]

    const response = await fetch('/api/grading/questionnaire/', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {})
      },
      body: JSON.stringify({ answers: payload })
    })

    return response.status
  }, QUESTIONNAIRE_PAYLOAD)

  expect(submitStatus).toBe(200)
}

test.describe('Questionnaire Flow', () => {
  test('teacher can access questionnaire from dashboard, submit it, then see the bilan button', async ({ page }) => {
    await loginAsTeacher(page)

    const questionnaireButton = page.getByRole('button', { name: /^Questionnaire$/i })
    const questionnaireButtonCount = await questionnaireButton.count()

    if (questionnaireButtonCount > 0) {
      await questionnaireButton.click()
      await page.waitForURL(/\/corrector\/questionnaire/)
      await page.waitForLoadState('networkidle')

      await expect(page.getByTestId('corrector-questionnaire-page')).toBeVisible()
      await expect(page.getByTestId('questionnaire-progress-card')).toBeVisible()
      await expect(page.getByTestId('question-q11')).toBeVisible()

      await ensureQuestionnaireSubmitted(page)
      await page.reload()
      await page.waitForLoadState('networkidle')

      await expect(page.getByTestId('questionnaire-completed-state')).toBeVisible()

      await page.getByRole('button', { name: /Retour au dashboard/i }).click()
      await page.waitForURL(/\/corrector-dashboard/)
      await page.waitForLoadState('networkidle')
    } else {
      await expect(page.getByRole('button', { name: /Bilan Questionnaire/i })).toBeVisible()
    }

    await expect(page.getByRole('button', { name: /^Questionnaire$/i })).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Bilan Questionnaire/i })).toBeVisible()
    await page.getByRole('button', { name: /Bilan Questionnaire/i }).click()
    await page.waitForURL(/\/questionnaire\/bilan/)
    await expect(page.getByTestId('questionnaire-bilan-page')).toBeVisible()
  })

  test('admin can access questionnaire bilan page once the questionnaire is completed', async ({ page }) => {
    await loginAsTeacher(page)
    await ensureQuestionnaireSubmitted(page)

    await page.goto('/corrector/questionnaire')
    await page.waitForLoadState('networkidle')
    await page.getByRole('button', { name: /Déconnexion/i }).click()
    await page.waitForURL(/\/$/)

    await loginAsAdmin(page)

    await expect(page.getByRole('button', { name: /Bilan Questionnaire/i })).toBeVisible()
    await page.getByRole('button', { name: /Bilan Questionnaire/i }).click()
    await page.waitForURL(/\/questionnaire\/bilan/)
    await page.waitForLoadState('networkidle')

    await expect(page.getByTestId('questionnaire-bilan-page')).toBeVisible()
    await expect(page.getByTestId('questionnaire-bilan-summary')).toBeVisible()
    await expect(page.getByText(/Bilan Questionnaire Correcteurs/i)).toBeVisible()
  })
})
