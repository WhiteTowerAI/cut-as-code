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

test('registers discovered projects and creates a project from the Hub', async ({ page }) => {
  let created = false
  let registered = false
  await page.route('**/v1/hub/projects', async (route) => {
    if (route.request().method() === 'POST') {
      created = true
      expect(route.request().postDataJSON()).toEqual({ name: 'Launch cut', parent: 'D:\\Projects', source: 'D:\\Media\\launch.mp4' })
      return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ ok: true }) })
    }
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify({
      ok: true,
      projects: created || registered ? [{ projectId: 'project_1', displayName: created ? 'Launch cut' : 'Candidate', rootFingerprint: 'abc', lastOpenedAt: '2026-08-21T00:00:00Z', available: true, running: false }] : [],
      candidates: created || registered ? [] : [{ candidateId: 'a'.repeat(24), displayName: 'Candidate', rootFingerprint: 'def' }],
      suggestedParent: 'D:\\Projects', updatePending: null,
    }) })
  })
  await page.route('**/v1/hub/candidates/*/register', (route) => {
    registered = true
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true }) })
  })
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Available projects' })).toBeVisible()
  await page.getByRole('button', { name: 'Register' }).click()
  await expect(page.getByText('Candidate', { exact: true })).toBeVisible()

  registered = false
  await page.getByRole('button', { name: 'New project' }).click()
  await page.getByLabel('Project name').fill('Launch cut')
  await expect(page.getByLabel('Parent folder')).toHaveValue('D:\\Projects')
  await page.getByLabel('Source video').fill('D:\\Media\\launch.mp4')
  await page.getByRole('button', { name: 'Create' }).click()
  await expect(page.getByText('Launch cut', { exact: true })).toBeVisible()
})
