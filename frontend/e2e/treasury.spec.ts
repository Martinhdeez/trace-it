import { mkdirSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test, type Page } from '@playwright/test'
import type { TreasuryPlan } from '../src/api/contracts'

async function fixture(page: Page) {
  const state = { mode: 'ok' as 'ok' | 'empty' | 'error', delay: false, foreign: false }
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    const apiMarker = url.pathname.indexOf('/api')
    if (apiMarker < 0) return route.continue()
    const path = apiMarker >= 0 ? url.pathname.slice(apiMarker + 4) : url.pathname
    if (!['/login', '/health', '/processes', '/processes/1', '/processes/1/summary', '/processes/1/queue', '/processes/1/sources', '/processes/1/rules', '/processes/1/instances', '/processes/1/treasury/preview'].includes(path) && !path.includes('/mail-ingestion/activity')) return route.continue()
    let body: unknown = []
    if (path === '/login') body = { id: 1, email: 'treasury@test.invalid', name: 'Treasury reviewer', role: 'manager' }
    if (path === '/health') body = { status: 'ok' }
    if (path === '/processes') body = [{ id: 1, name: 'Treasury fixture', description: '', decision_types: [], symbols: [] }]
    if (path === '/processes/1') body = { id: 1, name: 'Treasury fixture', description: '', decision_types: [], symbols: [] }
    if (path === '/processes/1/summary') body = { queue: 0, by_status: { PENDING: 0 }, by_decision: {} }
    if (path.includes('/mail-ingestion/activity')) body = { initialized: true, latest_id: 0, items: [], has_more: false }
    if (path === '/processes/1/treasury/preview') {
      if (state.delay) await new Promise((resolve) => setTimeout(resolve, 350))
      if (state.mode === 'error') return route.fulfill({ status: 503, json: { code: 'unavailable', message: 'Treasury preview unavailable' } })
      const requestBody = route.request().postDataJSON() as { as_of: string; weekly_budget: string; horizon_weeks: number }
      const budget = Number(requestBody.weekly_budget)
      body = {
        process_id: 1,
        as_of: requestBody.as_of,
        weekly_budget: requestBody.weekly_budget,
        horizon_weeks: requestBody.horizon_weeks,
        currency: 'EUR',
        rows: [
          { row_id: '42:7', instance_id: 42, decision_id: 7, name: 'NP-204.pdf', vendor: 'Norte Papel', amount: '2300.00', currency: 'EUR', due_date: '2026-09-24', week_index: 0, week_start: '2026-09-21', provenance: { decision_id: 7, decision_author: 'Martín', decision_at: '2026-09-20T09:00:00Z', execution_id: 8, version_id: 2, rules_hash: 'rules', source_ids: [3], amount_source: 'symbol:total', vendor_source: 'symbol:issuer_name', due_date_source: 'source:erp' , currency_source: 'invoice-policy-default:EUR' } },
          { row_id: '43:9', instance_id: 43, decision_id: 9, name: 'LS-19.pdf', vendor: '=SUM(A1:A2)', amount: '300.00', currency: 'EUR', due_date: '2026-10-01', week_index: 1, week_start: '2026-09-28', provenance: { decision_id: 9, decision_author: 'Martín', decision_at: '2026-09-20T09:00:00Z', execution_id: 8, version_id: 2, rules_hash: 'rules', source_ids: [3], amount_source: 'symbol:total', vendor_source: 'symbol:issuer_name', due_date_source: 'scenario:default_payment_terms_days', currency_source: 'invoice-policy-default:EUR' } },
        ],
        weeks: [
          {
            index: 0, start: '2026-09-21', end: '2026-09-27', total: '2300.00', remaining_budget: (budget - 2300).toFixed(2), row_ids: ['42:7'], backlog_count: 0, backlog_amount: '0.00',
          },
          {
            index: 1, start: '2026-09-28', end: '2026-10-04', total: '300.00', remaining_budget: (budget - 300).toFixed(2), row_ids: ['43:9'], backlog_count: 0, backlog_amount: '0.00',
          },
          { index: 2, start: '2026-10-05', end: '2026-10-11', total: '0.00', remaining_budget: requestBody.weekly_budget, row_ids: [], backlog_count: 0, backlog_amount: '0.00' },
          { index: 3, start: '2026-10-12', end: '2026-10-18', total: '0.00', remaining_budget: requestBody.weekly_budget, row_ids: [], backlog_count: 0, backlog_amount: '0.00' },
        ],
        suppliers: [{ vendor: 'Norte Papel', invoice_count: 1, scheduled_count: 1, scheduled_amount: '2300.00', backlog_count: 0, backlog_amount: '0.00' }, { vendor: '=SUM(A1:A2)', invoice_count: 1, scheduled_count: 1, scheduled_amount: '300.00', backlog_count: 0, backlog_amount: '0.00' }],
        exclusions: [{ instance_id: 44, name: 'Pending.pdf', decision_id: null, reason_code: 'pending', reason: 'outside_horizon', amount: '900.00', currency: state.foreign ? 'USD' : 'EUR', due_date: null, details: {} }],
        totals: { scheduled_count: 2, scheduled_amount: '2600.00', backlog_count: 0, backlog_amount: '0.00', excluded_count: 1, excluded_amount: '900.00' },
      }
      if (state.mode === 'empty') body = { ...body, rows: [], weeks: (body as TreasuryPlan).weeks.map((week) => ({ ...week, row_ids: [], total: '0.00', remaining_budget: requestBody.weekly_budget })), suppliers: [], exclusions: [], totals: { scheduled_count: 0, scheduled_amount: '0.00', backlog_count: 0, backlog_amount: '0.00', excluded_count: 0, excluded_amount: '0.00' } }
      if (state.foreign) body = { ...(body as Record<string, unknown>), totals: { scheduled_count: 2, scheduled_amount: '2600.00', backlog_count: 0, backlog_amount: '0.00', excluded_count: 1, excluded_amount: '0.00' } }
    }
    await route.fulfill({ json: body })
  })
  return state
}

test('treasury previews approved payments, keeps evidence links, and invalidates stale drafts', async ({ page }) => {
  await fixture(page)
  await page.goto('processes/1')
  await page.getByRole('button', { name: 'Historial', exact: true }).click()
  await expect(page).toHaveURL(/vista=historial/)
  await page.getByRole('button', { name: 'Plan de pagos', exact: true }).click()
  await expect(page).toHaveURL(/vista=pagos/)
  await expect(page.getByRole('button', { name: /^Te esperan/ })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Historial', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Plan de pagos', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('heading', { name: 'Plan de pagos', exact: true })).toBeVisible()
  await page.getByLabel('Inicio del plan').fill('2026-09-21')
  await page.getByLabel('Presupuesto semanal').fill('2500.00')
  await page.getByRole('button', { name: '4 semanas', exact: true }).click()
  await page.getByLabel('Presupuesto semanal').fill('2500.999')
  await expect(page.getByRole('button', { name: 'Previsualizar plan', exact: true })).toBeDisabled()
  await page.getByLabel('Presupuesto semanal').fill('2500.00')
  await page.getByLabel('Días de pago por defecto').fill('366')
  await expect(page.getByRole('button', { name: 'Previsualizar plan', exact: true })).toBeDisabled()
  await page.getByLabel('Días de pago por defecto').fill('')
  await page.getByRole('button', { name: 'Previsualizar plan', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Calendario semanal', exact: true })).toBeVisible()
  await expect(page.getByText('Norte Papel', { exact: true }).first()).toBeVisible()
  await expect(page.getByRole('link', { name: /Ver evidencia/ })).toHaveAttribute('href', /instances\?i=42/)
  await expect(page.getByRole('heading', { name: 'Totales por proveedor', exact: true })).toBeVisible()
  await page.getByRole('row').nth(2).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('row').nth(2)).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByText('=SUM(A1:A2)', { exact: true }).first()).toBeVisible()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar borrador CSV', exact: true }).click()
  const download = await downloadPromise
  expect(readFileSync(await download.path()!, 'utf8')).toContain("'=SUM(A1:A2)")

  await page.getByLabel('Presupuesto semanal').fill('2800.00')
  await expect(page.getByText('Los parámetros han cambiado', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Exportar borrador CSV', exact: true })).toHaveCount(0)

  await page.getByRole('button', { name: 'Previsualizar plan', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Exportar borrador CSV', exact: true })).toBeVisible()
})

test('treasury handles empty, foreign amounts, and failed or stale previews', async ({ page }) => {
  const state = await fixture(page)
  await page.goto('processes/1/treasury')
  await page.getByLabel('Inicio del plan').fill('2026-09-21')
  await page.getByLabel('Presupuesto semanal').fill('2500.00')
  await page.getByRole('button', { name: '4 semanas', exact: true }).click()

  state.mode = 'empty'
  await page.getByRole('button', { name: 'Previsualizar plan', exact: true }).click()
  await expect(page.getByText('No hay pagos asignados en este horizonte.', { exact: true })).toBeVisible()

  state.mode = 'ok'
  state.foreign = true
  await page.getByRole('button', { name: 'Previsualizar plan', exact: true }).click()
  await expect(page.getByText('900,00 USD', { exact: true })).toBeVisible()

  state.delay = true
  await page.getByLabel('Presupuesto semanal').fill('2800.00')
  await page.getByRole('button', { name: 'Previsualizar plan', exact: true }).click()
  await page.getByLabel('Presupuesto semanal').fill('2700.00')
  await page.waitForTimeout(500)
  await expect(page.getByText('Los parámetros han cambiado', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Exportar borrador CSV', exact: true })).toHaveCount(0)

  state.delay = false
  state.mode = 'error'
  await page.getByLabel('Presupuesto semanal').fill('2600.00')
  await page.getByRole('button', { name: 'Previsualizar plan', exact: true }).click()
  await expect(page.getByText('Treasury preview unavailable', { exact: true })).toBeVisible()
})

test('treasury remains readable on a narrow viewport and captures review artifacts', async ({ page }) => {
  await fixture(page)
  await page.goto('processes/1/treasury')
  await page.getByLabel('Inicio del plan').fill('2026-09-21')
  await page.getByLabel('Presupuesto semanal').fill('2500.00')
  await page.getByRole('button', { name: '4 semanas', exact: true }).click()
  await page.getByRole('button', { name: 'Previsualizar plan', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Calendario semanal', exact: true })).toBeVisible()
  const artifactDir = resolve(process.cwd(), '../.artifacts/treasury')
  mkdirSync(artifactDir, { recursive: true })
  await page.screenshot({ path: resolve(artifactDir, 'desktop.png'), fullPage: true })
  await page.getByTestId('inbox-content').evaluate((element) => element.scrollTo(0, element.scrollHeight))
  await page.screenshot({ path: resolve(artifactDir, 'desktop-detail.png'), fullPage: false })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByTestId('inbox-content').evaluate((element) => element.scrollTo(0, 0))
  await expect(page).toHaveURL(/vista=pagos/)
  await expect(page.getByRole('button', { name: /^Te esperan/ })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Historial', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Plan de pagos', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('heading', { name: 'Plan de pagos', exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.body.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: resolve(artifactDir, 'mobile.png'), fullPage: true })
  await page.getByTestId('inbox-content').evaluate((element) => element.scrollTo(0, element.scrollHeight))
  await page.screenshot({ path: resolve(artifactDir, 'mobile-detail.png'), fullPage: false })
})
