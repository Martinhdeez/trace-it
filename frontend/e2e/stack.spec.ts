import { randomUUID } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { test, expect, request as requests, type APIRequestContext, type Page } from '@playwright/test'

// Writes are manager-only; ci-stack.sh loads the pack, which seeds this manager.
async function seededManager(request: APIRequestContext) {
  const login = await request.post('api/login', { data: { email: 'martin@trace-it.local' } })
  expect(login.status(), await login.text()).toBe(200)
  return { 'X-User-Id': String((await login.json()).id) }
}

async function managerFixture(request: APIRequestContext, page?: Page) {
  const email = `${randomUUID()}@ci.invalid`
  const created = await request.post('api/users', {
    headers: await seededManager(request), data: { name: 'CI manager', email, role: 'manager' },
  })
  expect(created.status()).toBe(201)
  const login = await request.post('api/login', { data: { email } })
  expect(login.status()).toBe(200)
  const headers = { 'X-User-Id': String((await login.json()).id) }
  if (page) {
    await page.goto('settings')
    const user = page.getByRole('button', { name: new RegExp(email.replaceAll('.', '\\.')) })
    await expect(user).toContainText('CI manager')
    await expect(user).toContainText(/responsable/i)
    await user.click()
    // The sidebar now names the chosen identity.
    await expect(page.getByRole('link', { name: /CI manager\s*Responsable/ })).toBeVisible()
  }
  return headers
}

async function processFixture(request: APIRequestContext) {
  const name = `Browser CI ${randomUUID()}`
  const response = await request.post('api/processes/definition', { headers: await seededManager(request), data: {
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

test('Bearer API, public documentation and database boundaries through the real gateway', async ({ baseURL, request }) => {
  const api = await requests.newContext({
    baseURL,
    httpCredentials: { username: '', password: '' },
    extraHTTPHeaders: { Authorization: 'Bearer ci-only-api-token' },
  })
  try {
    expect((await api.get('')).status()).toBe(401)
    expect((await api.get('api/processes')).status()).toBe(200)
    const identity = await api.get('api/me', { headers: { 'X-User-Id': '999999' } })
    expect((await identity.json()).email).toBe('trace-it-api@localhost')
    expect((await api.get('api/db/tables')).status()).toBe(200)
    expect((await request.get('api/db/tables')).status()).toBe(401)
    for (const path of ['api/docs', 'api/openapi.json', 'api/guide']) {
      expect((await api.get(path, { headers: { Authorization: '' } })).status()).toBe(200)
    }
    for (const path of ['api/processes', 'api/db/tables', 'api/ready']) {
      expect((await api.get(path, { headers: { Authorization: 'Bearer wrong' } })).status()).toBe(401)
      expect((await api.get(path, { headers: { Authorization: '' } })).status()).toBe(401)
    }
    for (const name of ['pg_authid', 'alembic_version', 'other_app', 'public.users']) {
      expect((await api.get(`api/db/tables/${name}/rows`)).status()).toBe(404)
    }
    const created = await api.post('api/db/tables/users/rows', { data: {
      values: { name: 'Gateway API test', email: `${randomUUID()}@ci.invalid`, role: 'operator' },
      reason: 'Verify gateway CRUD',
    } })
    expect(created.status(), await created.text()).toBe(201)
    const row = await created.json()
    const updated = await api.patch('api/db/tables/users/row', { data: {
      key: row.key, expected_etag: row.etag, values: { name: 'Updated gateway test' },
      reason: 'Verify gateway update',
    } })
    expect(updated.status(), await updated.text()).toBe(200)
    const changed = await updated.json()
    const removed = await api.delete('api/db/tables/users/row', { data: {
      key: row.key, expected_etag: changed.etag, reason: 'Remove gateway test record',
    } })
    expect(removed.status(), await removed.text()).toBe(200)
  } finally { await api.dispose() }
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
  await expect(page.getByText('El backend no responde').first()).toBeVisible()
  await expect(page.getByRole('link', { name: process.name })).toHaveCount(0)
  await expect(page.getByRole('link', { name: /Pago de facturas/i })).toHaveCount(0)
})

test('HTTP flow persists PDF evidence, decisions, human resolution and export', async ({ request, page }, testInfo) => {
  const headers = await managerFixture(request, page)
  const process = await processFixture(request)
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
  const run = await request.post(`api/processes/${process.id}/run`, { headers })
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

  // The generic process field must open its own source, without invoice-specific UI code.
  const failures: string[] = []
  page.on('pageerror', error => failures.push(error.message))
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto(`processes/${process.id}/instances?i=${instanceId}`)
  await page.getByRole('button', { name: 'símbolos · 1', exact: true }).click()
  await page.getByRole('button', { name: 'View holder in original PDF' }).click()
  const dialog = page.getByRole('dialog', { name: 'Original document' })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText('Exact text', { exact: false })).toBeVisible()
  await expect(dialog.getByRole('img', { name: `${filename}, page 1` })).toBeVisible()
  const box = dialog.getByTestId('source-box')
  await expect(box).toHaveCount(1)
  const source = (await (await request.get(`api/instances/${instanceId}/document/locations`, { headers })).json()).fields.holder[0]
  const original = await box.boundingBox()
  expect(original!.width).toBeGreaterThan(5)
  expect(original!.width).toBeLessThan(100)
  expect(source.raw).toBe('Ana')
  await page.screenshot({ path: testInfo.outputPath('pdf-desktop.png') })
  await dialog.getByRole('button', { name: 'Zoom in', exact: true }).click()
  await expect.poll(async () => (await box.boundingBox())!.width).toBeCloseTo(original!.width * 1.25, 0)
  await dialog.getByRole('button', { name: 'Rotate page', exact: true }).click()
  await expect.poll(async () => (await box.boundingBox())!.height).toBeCloseTo(original!.width * 1.25, 0)
  await dialog.getByRole('button', { name: 'Reset view' }).click()
  // Trackpad pinch / ctrl+wheel zooms the sheet and its evidence together.
  const paper = dialog.getByRole('img', { name: `${filename}, page 1` })
  const bounds = await paper.boundingBox()
  await paper.dispatchEvent('wheel', {
    deltaY: -40, ctrlKey: true,
    clientX: bounds!.x + bounds!.width / 2,
    clientY: bounds!.y + Math.min(200, bounds!.height / 2),
  })
  await expect.poll(async () => (await box.boundingBox())!.width)
    .toBeCloseTo(original!.width * Math.exp(0.2), 0)
  const zoomed = await paper.boundingBox()
  const fractionY = Math.min(200, bounds!.height / 2) / bounds!.height
  expect(zoomed!.y + fractionY * zoomed!.height)
    .toBeCloseTo(bounds!.y + fractionY * bounds!.height, 0)
  await dialog.getByRole('button', { name: 'Reset view' }).click()
  await dialog.getByRole('button', { name: 'Info', exact: true }).click()
  await expect(dialog.getByRole('complementary', { name: 'Document information' })).toBeVisible()
  await dialog.getByRole('button', { name: 'Info', exact: true }).click()
  await page.setViewportSize({ width: 390, height: 844 })
  await expect.poll(async () => (await dialog.boundingBox())!.width).toBeLessThanOrEqual(358)
  await expect(box).toBeInViewport()
  await page.screenshot({ path: testInfo.outputPath('pdf-mobile.png') })
  const downloadEvent = page.waitForEvent('download')
  await dialog.getByRole('button', { name: 'Download original PDF' }).click()
  const downloaded = await downloadEvent
  expect(downloaded.suggestedFilename()).toBe(filename)
  expect(readFileSync((await downloaded.path())!)).toEqual(readFileSync(resolve('e2e/fixtures', filename)))
  await dialog.getByRole('button', { name: 'Cerrar', exact: true }).click()
  await expect(dialog).toHaveCount(0)
  expect(failures).toEqual([])
})
