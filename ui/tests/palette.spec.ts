import { expect, test } from '@playwright/test'

test('editor interaction states use the approved teal palette without purple UI', async ({ page }) => {
  await page.goto('/?scenario=1-60')

  const colors = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement)
    const rgb = (value: string) => {
      const probe = document.createElement('div')
      probe.style.color = value
      document.body.append(probe)
      const resolved = getComputedStyle(probe).color
      probe.remove()
      return resolved
    }
    return {
      accent: rgb(root.getPropertyValue('--color-accent')),
      selection: rgb(root.getPropertyValue('--color-selection')),
      focus: rgb(root.getPropertyValue('--color-focus')),
      primaryButton: getComputedStyle(document.querySelector('.workspace-operation-bar button')!).backgroundColor,
      selectedClip: getComputedStyle(document.querySelector('.timeline-clip[aria-pressed="true"]')!).backgroundColor,
    }
  })

  expect(colors).toEqual({
    accent: 'rgb(62, 139, 130)',
    selection: 'rgb(41, 78, 74)',
    focus: 'rgb(121, 183, 167)',
    primaryButton: 'rgb(62, 139, 130)',
    selectedClip: 'rgb(41, 78, 74)',
  })
})
