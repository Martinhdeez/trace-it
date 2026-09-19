/**
 * The demo path through the real console and the real API (docs/backend-plan.md, B0).
 *
 * `make e2e-integration` recreates the database and publishes the frozen pack; the config
 * starts the challenge ERP, the API and the console. No LLM key: the pack is frozen, so
 * nothing compiles, and the assistant's proposal is not part of the path (D4).
 *
 * A step waiting for one of Carlos's packages is `test.fixme('pkg n')`, and goes live in
 * the PR that lands package n (docs/frontend-handoff.md).
 */
import { resolve } from 'node:path'
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

const API = `http://127.0.0.1:${process.env.E2E_PORTS!.split(',')[1]}`
const MANAGER = { email: 'martin@trace-it.local', name: 'Martín' }
const PROCESS = 'Invoice payment - frozen 2026-09-19'
const INVOICES = resolve(import.meta.dirname, '../../.context/500-sombras-de-alberto/facturas')
// Two text PDFs on the same order: the golden says both end ESCALAR (DUPLICATE_PO).
const ESCALATED = ['2026-0233-A_catering.pdf', 'factura_41082.pdf']
// An image-only scan, read by the local OCR weights (`make ocr-models`).
const SCAN = 'scan_001.pdf'
const RESOLVED = 'factura_41082.pdf'
const NOTE = 'Pedido duplicado revisado: esta es la factura buena'

test.describe.configure({ mode: 'serial' })

let page: Page
let processId: number
// API responses that failed, for the error check on every screen. With no key, the
// assistant's proposal answers 502 `llm_error`; it is not part of the path (D4).
let failures: string[] = []
const ASSISTANT = /^502 (GET|POST) .*\/(suggestion|proposal)$/

test.beforeAll(async ({ browser, request }) => {
  const processes: { id: number; name: string }[] = await (await request.get(`${API}/processes`)).json()
  processId = processes.find((item) => item.name === PROCESS)!.id
  page = await browser.newPage()
  page.on('response', (response) => {
    if (response.url().includes('/api/') && response.status() >= 400) {
      failures.push(`${response.status()} ${response.request().method()} ${response.url()}`)
    }
  })
})

test.afterAll(async () => {
  await page.close()
})

/**
 * The data is real (no MOCK DATA badge) and no `ErrorNotice` is on screen, found by its
 * titles or by the "<status> · <code>" line under a backend message. `allow` lists the
 * codes one screen may show, e.g. the assistant's `llm_error` with no key.
 */
async function realAndClean(allow: string[] = []) {
  await expect(page.getByText('MOCK DATA', { exact: true })).toHaveCount(0)
  for (const title of ['El backend no responde', 'Endpoint pendiente', 'Algo ha fallado']) {
    await expect(page.getByText(title, { exact: true })).toHaveCount(0)
  }
  const codes = await page.getByText(/^\d{3} · [a-z_]+$/).allTextContents()
  expect(codes.filter((text) => !allow.some((code) => text.endsWith(` · ${code}`)))).toEqual([])
  expect(failures.filter((line) => !ASSISTANT.test(line))).toEqual([])
  failures = []
}

async function instanceByName(request: APIRequestContext, name: string) {
  const items: { id: number; name: string }[] = await (
    await request.get(`${API}/processes/${processId}/instances`)
  ).json()
  const id = items.find((item) => item.name === name)!.id
  return (await request.get(`${API}/instances/${id}`)).json()
}

test('the console acts as the manager, with no login screen', async () => {
  await page.goto('/processes')
  await page.waitForLoadState('networkidle')
  await realAndClean()
  await expect(page).toHaveURL(/\/processes$/)
  await expect(page.getByRole('link', { name: new RegExp(MANAGER.name) })).toBeVisible()
})

test('process panel shows the real process', async () => {
  await page.getByRole('link', { name: PROCESS }).first().click()
  await expect(page.getByRole('heading', { level: 1, name: PROCESS })).toBeVisible()
  await realAndClean()
})

test.fixme('pkg 2: process panel shows the published version', async () => {
  await expect(page.getByText(/v1\b|versión 1/)).toBeVisible()
  await realAndClean()
})

test('upload two text PDFs and run', async ({ request }) => {
  await page.getByRole('button', { name: 'Ejecutar', exact: true }).click()
  await page
    .locator('input[type=file][multiple]')
    .setInputFiles(ESCALATED.map((name) => resolve(INVOICES, name)))
  await page.getByRole('button', { name: `Ejecutar ${ESCALATED.length}` }).click()
  await expect(page.getByText('Lote completado')).toBeVisible({ timeout: 120_000 })
  for (const name of ESCALATED) {
    expect((await instanceByName(request, name)).decision).toBe('ESCALAR')
  }
  await page.getByRole('button', { name: 'Cerrar' }).click()
  await realAndClean()
})

test.fixme('pkg 3: the run shows real progress and `by_decision`', async () => {
  // The bar goes 1/n ... n/n with each file name, then the split by decision.
})

test('upload a scan and run', async ({ request }) => {
  await page.getByRole('button', { name: 'Ejecutar', exact: true }).click()
  await page.locator('input[type=file][multiple]').setInputFiles(resolve(INVOICES, SCAN))
  await page.getByRole('button', { name: 'Ejecutar 1' }).click()
  await expect(page.getByText('Lote completado')).toBeVisible({ timeout: 300_000 })
  // Local OCR alone cannot read every field of this scan, so it escalates, never guesses.
  const scan = await instanceByName(request, SCAN)
  expect(scan.decision).toBe('ESCALAR')
  expect(scan.reason).toMatch(/^MISSING_DATA: /)
  await page.getByRole('button', { name: 'Cerrar' }).click()
  await realAndClean()
})

test('the queue shows the escalated invoices', async () => {
  await page.goto(`/processes/${processId}/review`)
  await expect(page.getByRole('heading', { name: 'ESCALAR' })).toBeVisible()
  for (const name of [...ESCALATED, SCAN]) {
    await expect(page.getByRole('button', { name })).toBeVisible()
  }
  await realAndClean(['llm_error'])
})

test('open the escalation detail', async () => {
  await page.getByRole('button', { name: RESOLVED }).click()
  await expect(page.getByRole('link', { name: 'Ver traza →' })).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Decisión' })).toBeVisible()
  await realAndClean(['llm_error'])
})

test.fixme('pkg 5: the detail says why it escalated, as the API does', async ({ request }) => {
  const instance = await instanceByName(request, RESOLVED)
  await expect(page.getByText('Por qué se escaló')).toBeVisible()
  await expect(page.getByText(instance.reason)).toBeVisible()
  await realAndClean(['llm_error'])
})

test.fixme('pkg 5: accept the assistant proposal', async () => {
  // Needs a proposal with no LLM key (D4), e.g. one stored by the learning flow.
})

test('resolve as the manager', async ({ request }) => {
  await page.getByRole('combobox', { name: 'Decisión' }).selectOption('PAGAR')
  await page.getByRole('textbox', { name: /^Motivo/ }).fill(NOTE)
  await page.getByRole('button', { name: 'Resolver sin regla' }).click()
  // Resolved, the case leaves the ESCALAR list.
  await expect(page.getByRole('button', { name: RESOLVED })).toHaveCount(0)
  const instance = await instanceByName(request, RESOLVED)
  expect(instance.decision).toBe('PAGAR')
  expect(instance.decisions.at(-1)).toMatchObject({ decision: 'PAGAR', reason: NOTE })
  expect(instance.decisions.at(-1).author).not.toBe('engine')
  await realAndClean(['llm_error'])
})

test('trace view shows the decisions and the escalation reason', async ({ request }) => {
  await page.getByRole('link', { name: 'Ejecuciones' }).click()
  await page.getByRole('button', { name: new RegExp(RESOLVED.replace('.', '\\.')) }).click()
  await expect(page.getByText('Decisión final')).toBeVisible()
  await expect(page.getByText(NOTE).first()).toBeVisible()
  await expect(page.getByText('histórico · 2')).toBeVisible()

  // The one still escalated: its reason on screen is the one the API stored.
  const other = await instanceByName(request, ESCALATED[0])
  await page.getByRole('button', { name: new RegExp(ESCALATED[0].replace('.', '\\.')) }).click()
  await expect(page.getByText(other.reason, { exact: true }).first()).toBeVisible()
  await realAndClean()
})

test.fixme('pkg 8: the proposals inbox lists the resolution', async () => {
  // Accept or reject from the inbox, with `proposal_id` on resolve (#93).
})

test.fixme('pkg 7: run history lists the run', async () => {
  // Panel -> Historial: the run from this test, with its counts and the manager as author.
})
