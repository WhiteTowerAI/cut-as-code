import { expect, test } from '@playwright/test'

test('shows the project Hub without a runtime project identity', async ({ page }) => {
  await page.route('**/v1/hub/projects', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, projects: [], updatePending: null }),
  }))
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Cut as Code' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible()
  await expect(page.getByText('No registered projects')).toBeVisible()
  await expect(page.locator('[data-hub-shell]')).toBeVisible()
  await expect(page.locator('[data-editor-shell]')).toHaveCount(0)
})
