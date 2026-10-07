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

test('keeps registered projects usable when a Hub action fails', async ({ page }) => {
  await page.route('**/v1/hub/projects', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      ok: true,
      projects: [{ projectId: 'project_1', displayName: 'Existing cut', rootFingerprint: 'abc', lastOpenedAt: '2026-08-21T00:00:00Z', available: true, running: false }],
      candidates: [], updatePending: null,
    }),
  }))
  await page.route('**/v1/hub/projects/select', (route) => route.fulfill({
    status: 400, contentType: 'application/json',
    body: JSON.stringify({ ok: false, error: 'Project folder "33-cc" was not found next to the registered projects' }),
  }))
  await page.goto('/')

  await page.locator('.hub-folder-input').evaluate((input) => {
    const file = new File(['{}'], 'project.json', { type: 'application/json' })
    Object.defineProperty(file, 'webkitRelativePath', { value: '33-cc/work/project.json' })
    const transfer = new DataTransfer()
    transfer.items.add(file)
    Object.defineProperty(input, 'files', { value: transfer.files, configurable: true })
    input.dispatchEvent(new Event('change', { bubbles: true }))
  })

  await expect(page.getByRole('alert')).toContainText('33-cc')
  await expect(page.getByText('Existing cut', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Refresh projects' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Quit Editor Service' })).toBeVisible()
  await page.getByRole('button', { name: 'Dismiss error' }).click()
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.getByText('Existing cut', { exact: true })).toBeVisible()
})

test('registers discovered projects and selects a project folder from the Hub', async ({ page }) => {
  let created = false
  let registered = false
  await page.route('**/v1/hub/projects', async (route) => {
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify({
      ok: true,
      projects: created || registered ? [{ projectId: 'project_1', displayName: created ? 'Launch cut' : 'Candidate', rootFingerprint: 'abc', lastOpenedAt: '2026-08-21T00:00:00Z', available: true, running: false }] : [],
      candidates: created || registered ? [] : [{ candidateId: 'a'.repeat(24), displayName: 'Candidate', rootFingerprint: 'def' }],
      suggestedParent: 'D:\\Projects', updatePending: null,
    }) })
  })
  await page.route('**/v1/hub/projects/select', async (route) => {
    created = true
    expect(route.request().postDataJSON()).toEqual({ name: 'Candidate' })
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true }) })
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
  await page.locator('.hub-folder-input').evaluate((input) => {
    const file = new File(['{}'], 'project.json', { type: 'application/json' })
    Object.defineProperty(file, 'webkitRelativePath', { value: 'Candidate/work/project.json' })
    const transfer = new DataTransfer()
    transfer.items.add(file)
    Object.defineProperty(input, 'files', { value: transfer.files, configurable: true })
    input.dispatchEvent(new Event('change', { bubbles: true }))
  })
  await expect(page.getByText('Launch cut', { exact: true })).toBeVisible()
})
