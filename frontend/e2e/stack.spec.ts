import { randomUUID } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { test, expect, request as requests, type APIRequestContext, type Page } from '@playwright/test'

async function managerFixture(request: APIRequestContext, page?: Page) {
  const email = `${randomUUID()}@ci.invalid`
  const created = await request.post('api/users', { data: { name: 'CI manager', email, role: 'manager' } })
  expect(created.status()).toBe(201)
  const login = await request.post('api/login', { data: { email } })
  expect(login.status()).toBe(200)
  const headers = { 'X-User-Id': String((await login.json()).id) }
  if (page) {
    await page.goto('settings')
    const user = page.getByRole('button', { name: new RegExp(email.replaceAll('.', '\\.')) })
    await expect(user).toContainText('CI manager')
    await expect(user).toContainText('responsable')
    await user.click()
    await expect(page.getByRole('button', { name: 'Salir', exact: true })).toBeVisible()
  }
  return headers
}

async function processFixture(request: APIRequestContext) {
  const name = `Browser CI ${randomUUID()}`
  const response = await request.post('api/processes/definition', { data: {
    name, description: 'Isolated end-to-end test',
    decision_types: [
      { name: 'ACCEPT', priority: 0, is_default: true },
      { name: 'REVIEW', priority: 10, requires_human: true },
    ],
    symbols: [{ name: 'holder', type: 'text', required: true }],
  } })
  expect(response.ok(), await response.text()).toBeTruthy()
  return { name, id: (await response.json()).process.id as number }
}

test('gateway protects both the console and API', async ({ baseURL, request }) => {
  // newContext inherits Playwright's configured defaults; override the CI credentials.
  const anonymous = await requests.newContext({ baseURL, httpCredentials: { username: '', password: '' } })
  try {
    expect((await anonymous.get('')).status()).toBe(401)
    expect((await anonymous.get('api/users')).status()).toBe(401)
    expect((await anonymous.get('api/ready')).status()).toBe(401)
  } finally { await anonymous.dispose() }
  expect((await request.get('api/ready')).status()).toBe(200)
  expect((await request.get('assets/missing.js')).status()).toBe(404)
})

test('production assets and navigation stay inside the deployment prefix', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('response', response => {
    if (['script', 'stylesheet', 'image'].includes(response.request().resourceType())) {
      expect(response.status(), response.url()).toBeLessThan(400)
      expect(new URL(response.url()).pathname).toMatch(/^\/nexia\/trace-it\//)
    }
  })
  await page.goto('')
  await expect(page.getByRole('main')).toContainText('La consola escribe la norma')
  await page.getByRole('link', { name: 'Abrir la consola' }).first().click()
  await expect(page).toHaveURL(/\/nexia\/trace-it\/processes$/)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Procesos', exact: true })).toBeVisible()
  expect(errors).toEqual([])
})

test('console displays a process created in the real PostgreSQL database', async ({ page, request }) => {
  await managerFixture(request, page)
  const process = await processFixture(request)
  await page.goto('processes')
  // A mock cannot know this randomly generated process name.
  await expect(page.getByRole('link', { name: process.name }).first()).toBeVisible()
  await page.getByRole('link', { name: process.name }).first().click()
  await expect(page).toHaveURL(new RegExp(`/processes/${process.id}$`))
  for (const route of ['instances', 'review', 'definition', 'definition/sources', 'settings']) {
    const failures: string[] = []
    const listener = (response: import('@playwright/test').Response) => {
      if (response.url().includes('/api/') && response.status() >= 400) {
        failures.push(`${response.status()} ${response.url()}`)
      }
    }
    page.on('response', listener)
    await page.goto(`processes/${process.id}/${route}`)
    await page.waitForLoadState('networkidle')
    page.off('response', listener)
    expect(failures, route).toEqual([])
  }
})

test('production never substitutes mock data for an unavailable API', async ({ page, request }) => {
  const process = await processFixture(request)
  await page.route('**/api/**', route => route.fulfill({ status: 503, body: 'Unavailable' }))
  await page.goto('processes')
  await expect(page.getByText('503 Service Unavailable', { exact: false })).toBeVisible()
  await expect(page.getByRole('link', { name: process.name })).toHaveCount(0)
  await expect(page.getByRole('link', { name: /Pago de facturas/i })).toHaveCount(0)
})

test('HTTP flow persists PDF evidence, decisions, human resolution and export', async ({ request }) => {
  const process = await processFixture(request)
  const headers = await managerFixture(request)
  const validated = await request.post(`api/processes/${process.id}/draft/validate`, { headers })
  expect(validated.status(), await validated.text()).toBe(200)
  const draft = await validated.json()
  expect(draft.validation.valid, JSON.stringify(draft.validation)).toBe(true)
  const published = await request.post(`api/processes/${process.id}/draft/publish`, {
    headers, data: { revision: draft.revision, validation_hash: draft.validation.hash, reason: 'Approve CI certificate contract' },
  })
  expect(published.status(), await published.text()).toBe(201)
  const filename = 'certificate.pdf'
  const upload = await request.post(`api/processes/${process.id}/files`, {
    headers,
    multipart: {
      file: { name: filename, mimeType: 'application/pdf', buffer: readFileSync(resolve('e2e/fixtures', filename)) },
      ocr: 'false', vlm: 'false', jev: 'false',
    },
  })
  expect(upload.status(), await upload.text()).toBe(201)
  const document = await upload.json()
  const instanceId = document.instance_id
  expect(document.symbols.holder.value).toBe('Ana')
  const evidence = await request.get(`api/instances/${instanceId}/document`, { headers })
  expect(evidence.status()).toBe(200)
  const run = await request.post(`api/processes/${process.id}/run`)
  expect(run.status(), await run.text()).toBe(200)
  expect((await run.json()).decided, 'Uploaded PDF must reach the decision engine').toBe(1)
  const before = await (await request.get(`api/instances/${instanceId}`)).json()
  expect(before.decisions.at(-1).decision).toBe('ACCEPT')
  const resolved = await request.post(`api/instances/${instanceId}/resolve`, {
    headers, data: { decision: 'ACCEPT', reason: 'CI verified evidence' },
  })
  expect(resolved.status(), await resolved.text()).toBe(200)
  const after = await resolved.json()
  expect(after.decisions).toHaveLength(before.decisions.length + 1)
  expect(after.decisions.slice(0, -1)).toEqual(before.decisions)
  expect(after.decisions.at(-1).author).toBe('CI manager')
  const exported = await request.get(`api/processes/${process.id}/export`)
  expect(exported.status()).toBe(200)
  expect(JSON.parse((await exported.text()).trim()).file_id).toBe(filename)
})
