import { expect, test } from '@playwright/test'

test('content cards review keeps edits local until explicit save and invalidates the preview', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1200 })
  await page.goto('/?scenario=review-content-cards')

  await expect(page.getByRole('status', { name: 'Content Cards review status' })).toContainText('Preview current')
  await expect(page.getByLabel('Preview artifact metadata')).toContainText('Existing preview artifact: current')
  await page.getByRole('tab', { name: 'Cards' }).click()
  await page.getByLabel('Content card copy').fill('Revised lower third')

  await expect(page.getByRole('button', { name: 'Save Changes' })).toBeEnabled()
  await expect(page.getByRole('button', { name: 'Approve preview' })).toBeDisabled()
  await page.getByRole('button', { name: 'Save Changes' }).click()

  await expect(page.getByRole('status', { name: 'Content Cards review status' })).toContainText('Preview stale')
  await expect(page.getByRole('button', { name: 'Approve preview' })).toBeDisabled()
})

test('review rejection requires an explicit rationale and editor exposes no execution controls', async ({ page }) => {
  await page.goto('/?scenario=review-content-cards')

  await page.getByRole('button', { name: 'Reject preview' }).click()
  await expect(page.getByLabel('Rejection rationale')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Confirm rejection' })).toBeDisabled()
  await page.getByLabel('Rejection rationale').fill('Title obscures the speaker')
  await page.getByRole('button', { name: 'Confirm rejection' }).click()
  await expect(page.getByRole('status', { name: 'Content Cards review status' })).toContainText('Preview rejected')

  await expect(page.getByRole('button', { name: /render|generate preview|run skill|run agent/i })).toHaveCount(0)
  await expect(page.getByText(/codex exec/i)).toHaveCount(0)
})

test('conflicted card drafts cannot be saved or approved', async ({ page }) => {
  await page.goto('/?scenario=review-content-cards-conflict')

  await expect(page.getByRole('status', { name: 'Content Cards review status' })).toContainText('Conflict')
  await expect(page.getByRole('button', { name: 'Save Changes' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Approve preview' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Discard changes' })).toBeEnabled()
})
