import { expect, test } from '@playwright/test'

const scenarioIds = [
  '1-60',
  '1-1373',
  '1-84',
  '1-282',
  '57-152',
  '1-1026',
  '1-324',
  '1-1115',
  '1-754',
  '1-528',
  '18-3',
  '76-2',
  '123-2',
  '123-79',
  '123-167',
  '126-2',
  'graphic-motion',
] as const

for (const scenarioId of scenarioIds) {
  test(`${scenarioId} renders without a browser exception`, async ({ page }) => {
    const exceptions: string[] = []
    page.on('pageerror', (error) => exceptions.push(error.message))

    await page.goto(`/?scenario=${scenarioId}`)

    await expect(page.locator('[data-scenario-id]')).toHaveAttribute('data-scenario-id', scenarioId)
    expect(exceptions).toEqual([])
  })
}

for (const scenarioId of ['1-60', '1-1373'] as const) {
  test(`${scenarioId} assembles the existing editor panels`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1200 })
    await page.goto(`/?scenario=${scenarioId}`)

    await expect(page.getByRole('region', { name: 'Library', exact: true })).toHaveCount(1)
    await expect(page.getByRole('region', { name: 'Viewer', exact: true })).toHaveCount(1)
    await expect(page.getByRole('region', { name: 'Timeline', exact: true })).toHaveCount(1)

    if (scenarioId === '1-60') {
      await expect(page.getByLabel('Selection actions')).toBeVisible()
    } else {
      await expect(page.locator('[data-preview-media]')).toHaveCount(0)
    }
  })
}

test('76-2 exposes the icon library as a verification surface', async ({ page }) => {
  await page.setViewportSize({ width: 1785, height: 1746 })
  await page.goto('/?scenario=76-2')

  await expect(page.locator('[data-icon-library]')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Icon Library' })).toBeVisible()
  await expect(page.locator('.library-panel')).toHaveCount(0)
  await expect(page.locator('.viewer-panel')).toHaveCount(0)
  await expect(page.locator('.timeline-panel')).toHaveCount(0)
})
