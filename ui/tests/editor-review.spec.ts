import { expect, test } from '@playwright/test'

test('content cards review keeps the cue list without redundant editable details', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1200 })
  await page.goto('/?scenario=review-content-cards')

  await expect(page.getByRole('status', { name: 'Content Cards review status' })).toContainText('Preview current')
  await expect(page.getByLabel('Preview artifact metadata')).toContainText('Existing preview artifact: current')
  await page.getByRole('tab', { name: 'Cards' }).click()
  await expect(page.locator('.library-tile')).toHaveCount(1)
  await expect(page.getByRole('group', { name: 'Content Card fields' })).toHaveCount(0)
  await expect(page.getByLabel('Content card copy')).toHaveCount(0)
  await expect(page.getByLabel('Content card layout')).toHaveCount(0)
  await expect(page.getByLabel('Content card placement')).toHaveCount(0)
  await expect(page.getByLabel('Content card enabled')).toHaveCount(0)
})

test('review rejection requires an explicit rationale and editor exposes no execution controls', async ({ page }) => {
  await page.goto('/?scenario=review-content-cards')

  await page.getByRole('button', { name: 'Reject preview' }).click()
  await expect(page.getByLabel('Decision rationale')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Confirm rejection' })).toBeDisabled()
  await page.getByLabel('Decision rationale').fill('Title obscures the speaker')
  await page.getByRole('button', { name: 'Confirm rejection' }).click()
  await expect(page.getByRole('status', { name: 'Content Cards review status' })).toContainText('Preview rejected')

  await expect(page.getByRole('button', { name: /render|generate preview|run skill|run agent/i })).toHaveCount(0)
  await expect(page.getByText(/codex exec/i)).toHaveCount(0)
})

test('conflicted card drafts cannot be saved or approved', async ({ page }) => {
  await page.goto('/?scenario=review-content-cards-conflict')

  await expect(page.getByRole('status', { name: 'Content Cards review status' })).toContainText('Conflict')
  await expect(page.getByRole('button', { name: 'Save All' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Approve preview' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Reject preview' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Discard changes' })).toBeEnabled()
})
