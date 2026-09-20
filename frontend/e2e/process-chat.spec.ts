import { expect, test, type Page } from '@playwright/test'

const activeRule = {
  id: 42,
  process_id: 6,
  summary: 'Escalate severe incidents',
  text: 'Escalate an incident when its severity is at least 8.',
  decision: 'ESCALATE',
  type: 'constraint',
  status: 'active',
}

async function fixture(page: Page, conversation: 'none' | 'empty' | 'proposed') {
  const process = { id: 6, name: 'Crisis incident triage', symbols: [], decision_types: [] }
  const session = {
    id: 9,
    process_id: 6,
    published_process_id: null,
    revision: conversation === 'proposed' ? 2 : 1,
    name: process.name,
    plan: {
      ...process,
      description: '',
      connectors: [],
      sources: [],
      rules: conversation === 'proposed'
        ? [{ ...activeRule, name: 'new-threshold', summary: 'Proposed lower threshold', evidence: [] }]
        : [],
      guidance: [],
      examples: [],
      questions: [],
    },
    messages: [],
    reviews: {},
    snapshots: [],
    changes: conversation === 'proposed' ? [{ field: 'rules', before: [], after: [] }] : [],
  }
  const writes: string[] = []
  const ruleQueries: URL[] = []
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.pathname.includes('/src/')) return route.continue()
    const path = url.pathname.split('/api')[1]
    if (request.method() !== 'GET' && path !== '/login') writes.push(path)
    let body: unknown = []
    if (path === '/login') body = { id: 1, name: 'Manager', email: 'manager@test.invalid', role: 'manager' }
    if (path === '/processes') body = [process]
    if (path === '/processes/6') body = process
    if (path === '/processes/6/summary') body = { queue: 0 }
    if (path === '/processes/6/execution') body = { revision: null, version_id: 46 }
    if (path === '/process-drafts') body = conversation === 'none' ? [] : [session]
    if (path === '/process-drafts/9') body = session
    if (path === '/processes/6/rules') {
      ruleQueries.push(url)
      body = [activeRule]
    }
    if (path?.includes('/mail-ingestion/activity'))
      body = { initialized: true, latest_id: 0, items: [], has_more: false }
    if (path === '/health') body = { status: 'ok' }
    await route.fulfill({ json: body })
  })
  return { writes, ruleQueries }
}

for (const conversation of ['none', 'empty', 'proposed'] as const) {
  test(`existing process shows current rules with ${conversation} conversation`, async ({ page }) => {
    const state = await fixture(page, conversation)
    await page.goto('processes/6/chat')
    const rules = page.getByRole('region', { name: 'Current rules', exact: true })
    await expect(rules.getByRole('link', { name: activeRule.summary })).toBeVisible()
    await expect(rules).not.toContainText(activeRule.text)
    await expect(rules.getByRole('link', { name: activeRule.summary })).toHaveAttribute('title', activeRule.text)
    await expect(rules).toContainText('Activa')
    await expect(rules.getByRole('link', { name: activeRule.summary })).toHaveAttribute(
      'href', /\/processes\/6\/rules\/42$/,
    )
    // Viewing the published rules must not request approval or mutate a draft.
    await expect(rules.getByRole('button')).toHaveCount(0)
    await expect(rules).not.toContainText('Proposed lower threshold')
    expect(state.ruleQueries.length).toBeGreaterThan(0)
    expect(state.ruleQueries.every((url) => url.searchParams.get('status') === 'active')).toBe(true)
    expect(state.writes).toEqual([])
    if (conversation === 'proposed')
      await expect(page.getByRole('button', { name: 'Aprobar Proposed lower threshold', exact: true })).toBeVisible()
  })
}

test('a new process does not show another process rules', async ({ page }) => {
  const state = await fixture(page, 'none')
  await page.goto('processes/new')
  await expect(page.getByRole('button', { name: 'Empezar conversación', exact: true })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Current rules', exact: true })).toHaveCount(0)
  expect(state.ruleQueries).toEqual([])
})
