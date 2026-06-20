import { test, expect } from '@playwright/test'

test.describe('Admin password reset UI', () => {
  test('resets a student password from exam results without displaying credentials', async ({ page }) => {
    let resetPayload: unknown = null

    await page.route('**/api/auth/status/', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          authenticated: true,
          role: 'Admin',
          user: { id: 1, username: 'admin', role: 'Admin' },
        }),
      })
    })

    await page.route('**/api/me/', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 1, username: 'admin', role: 'Admin' }),
      })
    })

    await page.route('**/api/exams/exam-123/student-list/', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          summary: {
            exam_name: 'Produit scalaire',
            total_students: 1,
            graded: 0,
            ready: 1,
            staging: 0,
            average: null,
            min_score: null,
            max_score: null,
            has_groups: false,
          },
          copies: [
            {
              student_id: 7,
              student_name: 'Dupont Ali',
              student_class: '1 EDS',
              anonymous_id: '4C9D-001',
              status: 'READY',
              has_copy: true,
              total_score: null,
              corrector: 'alaeddine.benrhouma@ert.tn',
              has_appreciation: false,
            },
          ],
        }),
      })
    })

    await page.route('**/api/students/admin/reset-password/', async (route) => {
      expect(route.request().method()).toBe('POST')
      resetPayload = route.request().postDataJSON()
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: "Mot de passe réinitialisé. L'élève devra le changer à sa prochaine connexion.",
          student_id: 7,
          student_name: 'Ali Dupont',
          must_change_password: true,
        }),
      })
    })

    await page.goto('/admin/exams/exam-123/results')
    await expect(page.getByRole('heading', { name: 'Liste des élèves' })).toBeVisible()
    await expect(page.getByText('4C9D-001')).toBeVisible()

    await page.getByTitle('Réinitialiser le mot de passe (date de naissance)').click()
    const resetDialog = page.getByTestId('password-reset-dialog')
    await expect(resetDialog).toBeVisible()
    await expect(resetDialog.getByText('Réinitialiser le mot de passe')).toBeVisible()
    await expect(resetDialog.getByText('Dupont Ali')).toBeVisible()

    await page.getByTestId('password-reset-confirm').click()
    await expect.poll(() => resetPayload).toEqual({ student_id: 7 })
    const successBox = page.getByTestId('password-reset-success')
    await expect(successBox).toBeVisible()
    await expect(successBox).toContainText('Mot de passe réinitialisé avec succès')
    const successMessage = await successBox.textContent()
    expect(successMessage).not.toContain('Nouveau mot de passe')
    expect(successMessage).not.toContain('new_password')
    expect(successMessage).not.toContain('undefined')
  })
})
