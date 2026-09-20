import { expect, test, type Page } from '@playwright/test'

const filename = 'factura á + #&?.pdf'

async function fixture(page: Page) {
  const state = { id: 21, missing: false, requested: [] as number[], searches: [] as string[], errors: [] as string[] }
  page.on('pageerror', (error) => state.errors.push(error.message))
  const process = {
    id: 1, name: 'Trace links fixture', description: '', symbols: [],
    decision_types: [
      { name: 'PAGAR', priority: 0, is_default: true, requires_human: false },
      { name: 'ESCALAR', priority: 10, is_default: false, requires_human: true },
    ],
  }
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.includes('/src/')) return route.continue()
    const path = url.pathname.split('/api')[1]
    let body: unknown = []
    if (path === '/login') body = { id: 1, name: 'Reviewer', email: 'test@ci.invalid', role: 'manager' }
    if (path === '/processes') body = [process]
    if (path === '/processes/1') body = process
    if (path === '/processes/1/summary') body = { queue: 0 }
    if (path?.includes('/mail-ingestion/activity')) body = { initialized: true, latest_id: 0, items: [], has_more: false }
    if (path === '/processes/1/instances') {
      state.searches.push(url.searchParams.get('q') ?? '')
      // A substring match with a larger ID must never override the requested document.
      body = [
        { id: 99999, name: `${filename}.backup`, status: 'DECIDED', decision: 'PAGAR' },
        ...(!state.missing ? [
          { id: state.id - 1, name: filename, status: 'DECIDED', decision: 'PAGAR' },
          { id: state.id, name: filename, status: 'DECIDED', decision: 'PAGAR' },
        ] : []),
      ]
    }
    const instance = path?.match(/^\/instances\/(\d+)$/)
    if (instance) {
      const id = Number(instance[1])
      state.requested.push(id)
      body = { id, process_id: 1, name: filename, status: 'DECIDED', decision: 'PAGAR',
        decisions: [], reviews: [], events: [], symbols: {}, values: {}, review_pending: false }
    }
    await route.fulfill({ json: body })
  })
  return state
}

test('exported document link opens the latest exact case after its ID changes', async ({ page }) => {
  const state = await fixture(page)
  const link = `processes/1/review?${new URLSearchParams({ file: filename })}`
  await page.goto(link)
  await expect(page.getByRole('link', { name: 'Ver traza →' })).toHaveAttribute('href', /instances\?i=21$/)
  expect(state.searches).toContain(filename)
  expect(state.requested).toEqual([21])
  state.id = 501 // A reset creates a new instance for the same document.
  await page.reload()
  await expect(page.getByRole('link', { name: 'Ver traza →' })).toHaveAttribute('href', /instances\?i=501$/)
  expect(state.requested).toEqual([21, 501])
  await expect(page).toHaveURL(new RegExp('file='))
  expect(state.errors).toEqual([])
})

test('missing document shows a notice instead of another case', async ({ page }) => {
  const state = await fixture(page)
  state.missing = true
  await page.goto(`processes/1/review?${new URLSearchParams({ file: filename })}`)
  await expect(page.getByText('Documento no encontrado', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Ver traza →' })).toHaveCount(0)
  expect(state.requested).toEqual([])
  expect(state.errors).toEqual([])
})

test('existing numeric case links remain supported', async ({ page }) => {
  const state = await fixture(page)
  await page.goto('processes/1/review?i=21')
  await expect(page.getByRole('link', { name: 'Ver traza →' })).toHaveAttribute('href', /instances\?i=21$/)
  expect(state.searches).toEqual([])
  expect(state.errors).toEqual([])
})
