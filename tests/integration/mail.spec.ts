import { expect, test } from '@playwright/test'

const API = process.env.MAIL_TEST_API_URL ?? 'http://127.0.0.1:18285'

test('gathering email routes local IMAP PDFs through the worker to decisions and the UI', async ({ page, request }, testInfo) => {
  const state = await (await request.get(`${API}/_mail-test/state`)).json()
  await page.goto(`/processes/${state.process_id}/settings`)
  // The app identifies the configured test manager through its real login API.
  const email = page.getByLabel('Correo de recepción (gathering)')
  await expect(email).toHaveValue('')
  await email.selectOption('migration-test@j-aautomation.com')
  await page.getByRole('button', { name: 'Guardar correo', exact: true }).click()
  await expect(email).toHaveValue('migration-test@j-aautomation.com')
  await expect(page.getByText('Pendiente de inicializar', { exact: true })).toBeVisible()
  const start = await request.post(`${API}/_mail-test/start`)
  expect(start.ok(), await start.text()).toBeTruthy()
  expect((await request.post(`${API}/_mail-test/deliver`)).ok()).toBeTruthy()
  await expect(page.getByText('Synthetic automatic invoice batch', { exact: true })).toBeVisible()
  await expect(page.getByText(/^(· )?Completado$/)).toHaveCount(4)
  for (const result of ['PAGAR', 'NO_PAGAR', 'ESCALAR']) {
    await expect(page.getByRole('link', { name: new RegExp(`^${result} · #`) })).toBeVisible()
  }
  await expect(page.getByText('Todavía no se ha consultado el buzón')).toHaveCount(0)
  const after = await (await request.get(`${API}/_mail-test/state`)).json()
  expect(after.unchanged).toBe(true)
  expect(after.forbidden).toEqual([])
  await page.screenshot({ path: testInfo.outputPath('mail-settings.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(email).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('mail-settings-mobile.png'), fullPage: true })
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.getByRole('link', { name: /^PAGAR · #/ }).click()
  await expect(page.getByText('Recibido por correo · pay.pdf')).toBeVisible()
})
