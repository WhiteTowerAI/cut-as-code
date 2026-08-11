import { expect, test } from '@playwright/test'

test('renders the editor application shell', async ({ page }) => {
  await page.goto('/')

  await expect(page.locator('[data-editor-shell]')).toBeVisible()
})
