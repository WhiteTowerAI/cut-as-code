import { expect, test } from '@playwright/test'

test('shows an explicit project error instead of a fixture shell without runtime identity', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('alert', { name: 'Project unavailable' })).toContainText('No Protocol V1 project was selected.')
  await expect(page.locator('[data-editor-shell]')).toHaveCount(0)
})
