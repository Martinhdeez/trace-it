import { useState } from 'react'
import { AlertCircle, ArrowUpRight, CalendarDays, Download, FileSpreadsheet, WalletCards } from 'lucide-react'
import { Link } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import type { TreasuryInvoice, TreasuryPlan, TreasuryPlanRequest, TreasuryWeek } from '../api/contracts'
import { Button, Field, Input, SegmentedRail, SEGMENT_ITEM } from '../components/shell/Controls'
import { DataTable, type Column } from '../components/shell/DataTable'
import { EmptyState, ErrorNotice, Notice } from '../components/shell/Notice'
import { NestedCard } from '../components/shell/Well'
import { getLocale, t } from '../i18n'
import { cn } from '../lib/cn'
import { formatEuro } from '../lib/format'
import { paths } from '../lib/paths'

const HORIZONS = [4, 8, 12] as const

function money(value: string, currency = 'EUR') {
  const numeric = Number(value)
  const symbol = currency === 'EUR' ? '€' : currency
  return Number.isFinite(numeric) ? `${formatEuro(numeric)} ${symbol}` : `${value} ${symbol}`
}

function shortDate(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(`${value.slice(0, 10)}T12:00:00`)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(getLocale() === 'es' ? 'es-ES' : 'en-GB', { day: 'numeric', month: 'short' })
}

function weekLabel(week: TreasuryWeek) {
  return `${shortDate(week.start)} – ${shortDate(week.end)}`
}

function csvCell(value: string | number) {
  const text = String(value)
  const safe = /^[=+\-@\t\r]/.test(text.trimStart()) ? `'${text}` : text
  return `"${safe.replaceAll('"', '""')}"`
}

function dueSourceLabel(source: string) {
  if (source.startsWith('scenario:')) return t('treasury.dueSourceScenario')
  if (source.startsWith('source:')) return t('treasury.dueSourceSource')
  if (source.startsWith('symbol:')) return t('treasury.dueSourceInvoice')
  if (source.startsWith('symbol:')) return t('treasury.dueSourceSymbol')
  return t('treasury.dueSourceUnknown')
}

function reasonLabel(code: string, detail: string) {
  const key = `treasury.reasons.${code}`
  const label = t(key)
  return label === key ? detail : label
}

export function Treasury({ processId }: { processId: number }) {
  const [asOf, setAsOf] = useState('')
  const [weeklyBudget, setWeeklyBudget] = useState('')
  const [horizon, setHorizon] = useState<(typeof HORIZONS)[number]>(8)
  const [paymentTerms, setPaymentTerms] = useState('')
  const [selectedWeek, setSelectedWeek] = useState(0)
  const [downloaded, setDownloaded] = useState(false)

  const preview = useMutation({
    mutationFn: ({ body, key }: { body: TreasuryPlanRequest; key: string }) =>
      api.treasuryPreview(processId, body).then((plan) => ({ plan, key, processId })),
    onSuccess: () => {
      setSelectedWeek(0)
      setDownloaded(false)
    },
  })
  const currentKey = JSON.stringify({ asOf, weeklyBudget, horizon, paymentTerms })
  const plan = preview.data?.processId === processId && preview.data.key === currentKey ? preview.data.plan : undefined
  const activeWeek = plan?.weeks[selectedWeek]
  const activeRows = plan && activeWeek ? plan.rows.filter((row) => activeWeek.row_ids.includes(row.row_id)) : []
  const budgetValue = Number(weeklyBudget)
  const validBudget = /^(?:0|[1-9]\d*)(?:\.\d{1,2})?$/.test(weeklyBudget) && Number.isFinite(budgetValue) && budgetValue > 0
  const validDate = /^\d{4}-\d{2}-\d{2}$/.test(asOf)
  const validTerms = paymentTerms === '' || /^(?:0|[1-9]\d*)$/.test(paymentTerms) && Number(paymentTerms) <= 365
  const canPreview = validBudget && validDate && validTerms && !preview.isPending
  const hasUnsupportedError = preview.error && ('status' in preview.error) &&
    ((preview.error as { status?: number; code?: string }).status === 501 || (preview.error as { code?: string }).code === 'unsupported_process')

  const submit = () => {
    if (!canPreview) return
    preview.reset()
    preview.mutate({
      key: currentKey,
      body: {
        as_of: asOf,
        weekly_budget: weeklyBudget,
        horizon_weeks: horizon,
        ...(paymentTerms ? { default_payment_terms_days: Number(paymentTerms) } : {}),
      },
    })
  }

  const exportCsv = () => {
    if (!plan) return
    const rows = plan.rows.map((invoice) => [
      plan.as_of,
      plan.weekly_budget,
      plan.horizon_weeks,
      paymentTerms,
      plan.weeks[invoice.week_index]?.start ?? invoice.week_start,
      plan.weeks[invoice.week_index]?.end ?? invoice.week_start,
      invoice.vendor,
      invoice.name,
      invoice.due_date,
      invoice.provenance.due_date_source,
      invoice.amount,
      'PAGAR',
      invoice.instance_id,
      invoice.decision_id,
      invoice.provenance.version_id ?? '',
      invoice.provenance.execution_id ?? '',
      invoice.provenance.source_ids?.join(';') ?? '',
      invoice.provenance.decision_author,
      invoice.provenance.decision_at,
      invoice.provenance.rules_hash,
      invoice.provenance.amount_source,
      invoice.provenance.vendor_source,
      invoice.provenance.currency_source,
    ])
    const csv = [
      ['as_of', `weekly_budget_${plan.currency.toLowerCase()}`, 'horizon_weeks', 'default_payment_terms_days', 'week_start', 'week_end', 'vendor', 'invoice_name', 'due_date', 'due_date_source', `amount_${plan.currency.toLowerCase()}`, 'decision', 'instance_id', 'decision_id', 'version_id', 'execution_id', 'source_ids', 'decision_author', 'decision_at', 'rules_hash', 'amount_source', 'vendor_source', 'currency_source'],
      ...rows,
    ].map((row) => row.map(csvCell).join(',')).join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `payment-plan-${asOf}.csv`
    anchor.click()
    URL.revokeObjectURL(url)
    setDownloaded(true)
  }

  return (
    <section aria-label={t('treasury.title')}>
        <div className="mx-auto max-w-6xl">
          <header className="flex flex-wrap items-end justify-between gap-5 border-b border-hairline pb-5">
            <div className="max-w-2xl">
              <p className="font-mono text-[11px] uppercase tracking-[0.13em] text-faint">{t('treasury.kicker')}</p>
              <h1 className="mt-1 text-[28px] font-medium leading-[1.1] tracking-[-0.045em]">{t('treasury.title')}</h1>
              <p className="mt-2 max-w-xl text-[13.5px] leading-6 text-muted">{t('treasury.subtitle')}</p>
            </div>
            {plan ? (
              <Button tone="soft" onClick={exportCsv} aria-label={t('treasury.export')}>
                <Download size={13} strokeWidth={1.8} />
                {t('treasury.export')}
              </Button>
            ) : null}
          </header>

          <section aria-labelledby="treasury-controls" className="mt-6">
            <div className="flex items-center gap-2">
              <CalendarDays size={15} strokeWidth={1.65} className="text-muted" />
              <h2 id="treasury-controls" className="text-[13px] font-medium">{t('treasury.draft')}</h2>
              <span className="ml-1 text-[12px] text-faint">{t('treasury.previewOnly')}</span>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr_1fr_1fr_auto]">
              <Field label={t('treasury.asOf')} hint={t('treasury.asOfHint')}>
                <Input aria-label={t('treasury.asOf')} type="date" value={asOf} onChange={(event) => setAsOf(event.target.value)} />
              </Field>
              <Field label={t('treasury.weeklyBudget')} hint={t('treasury.weeklyBudgetHint')}>
                <div className="relative">
                  <Input aria-label={t('treasury.weeklyBudget')} inputMode="decimal" min="0" step="100" type="number" value={weeklyBudget} onChange={(event) => setWeeklyBudget(event.target.value)} className="pr-10" />
                  <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-[12px] text-faint">€</span>
                </div>
              </Field>
              <Field label={t('treasury.horizon')} hint={t('treasury.weeks')}>
                <SegmentedRail value={String(horizon)}>
                  {HORIZONS.map((weeks) => (
                    <button key={weeks} type="button" aria-label={`${weeks} ${t('treasury.weeks')}`} data-active={horizon === weeks || undefined} aria-pressed={horizon === weeks} onClick={() => setHorizon(weeks)} className={cn(SEGMENT_ITEM, horizon === weeks ? 'text-ink' : 'text-muted hover:text-ink')}>
                      {weeks}
                    </button>
                  ))}
                </SegmentedRail>
              </Field>
              <Field label={t('treasury.paymentTerms')} hint={t('treasury.paymentTermsHint')}>
                <Input aria-label={t('treasury.paymentTerms')} inputMode="numeric" min="0" max="365" placeholder={t('treasury.paymentTermsPlaceholder')} type="number" value={paymentTerms} onChange={(event) => setPaymentTerms(event.target.value)} />
              </Field>
              <div className="flex items-start pt-[18px]">
                <Button tone="primary" className="h-[34px] w-full justify-center whitespace-nowrap md:w-auto" onClick={submit} disabled={!canPreview}>
                  <WalletCards size={13} strokeWidth={1.8} />
                  {preview.isPending ? t('treasury.previewing') : t('treasury.preview')}
                </Button>
              </div>
            </div>
          </section>

      {preview.error ? (
            <div className="mt-5">
              {hasUnsupportedError ? (
                <Notice tone="warning" title={t('treasury.unsupported')}>
                  {t('treasury.unsupportedHint')}
                </Notice>
              ) : <ErrorNotice error={preview.error} action={<Button onClick={submit}>{t('common.retry')}</Button>} />}
            </div>
      ) : null}
      {preview.data && !plan && !preview.error ? <div className="mt-5"><Notice tone="warning" title={t('treasury.staleTitle')}>{t('treasury.staleHint')}</Notice></div> : null}
          {downloaded ? <div className="mt-4"><Notice title={t('treasury.exportDone')}>{t('treasury.exportHint')}</Notice></div> : null}

          {!plan && !preview.error ? (
            <EmptyState icon={FileSpreadsheet} title={t('treasury.noSchedule')} className="mt-10">
              {t('treasury.setup')}
            </EmptyState>
          ) : null}
          {plan && !plan.rows.length ? (
            <EmptyState icon={AlertCircle} title={t('treasury.noScheduled')} className="mt-10">
              {t('treasury.noScheduledHint')}
            </EmptyState>
          ) : null}
          {plan && plan.rows.length ? (
            <div className="mt-7 space-y-6">
              <div className="grid grid-cols-1 divide-y divide-hairline overflow-hidden rounded-[16px] bg-surface ring-1 ring-line sm:grid-cols-3 sm:divide-x sm:divide-y-0" aria-label={t('treasury.schedule')}>
                <SummaryCell label={`${t('treasury.totalPlanned')} · ${plan.totals.scheduled_count}`} value={money(plan.totals.scheduled_amount, plan.currency)} tone="positive" />
                <SummaryCell label={`${t('treasury.totalBacklog')} · ${plan.totals.backlog_count}`} value={money(plan.totals.backlog_amount, plan.currency)} tone={Number(plan.totals.backlog_amount) > 0 ? 'warning' : undefined} />
                <SummaryCell label={`${t('treasury.knownExcluded')} · ${plan.totals.excluded_count}`} value={money(plan.totals.excluded_amount, plan.currency)} tone={Number(plan.totals.excluded_amount) > 0 ? 'warning' : undefined} />
              </div>

              <section aria-labelledby="treasury-schedule-heading">
                <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
                  <div>
                    <h2 id="treasury-schedule-heading" className="text-[16px] font-medium tracking-[-0.03em]">{t('treasury.schedule')}</h2>
                    <p className="mt-1 text-[12.5px] text-muted">{t('treasury.scheduleHint')}</p>
                  </div>
                  <span className="font-mono text-[11px] text-faint">{plan.horizon_weeks} {t('treasury.weeks')}</span>
                </div>
                <div className="grid gap-5 lg:grid-cols-[minmax(0,1.6fr)_minmax(280px,1fr)]">
                  <NestedCard>
                    <DataTable columns={weekColumns(plan.currency)} rows={plan.weeks.map((week) => ({ ...week, id: String(week.index) }))} selectedId={activeWeek ? String(activeWeek.index) : undefined} onRowClick={(row) => setSelectedWeek(row.index)} />
                  </NestedCard>
                  <WeekDetail week={activeWeek} rows={activeRows} processId={processId} currency={plan.currency} />
                </div>
              </section>

              {plan.suppliers.length ? <VendorTotals vendors={plan.suppliers} currency={plan.currency} /> : null}

            </div>
          ) : null}
          {plan?.exclusions.length ? <div className="mt-7"><ExcludedRows rows={plan.exclusions} processId={processId} /></div> : null}
        </div>
    </section>
  )
}

function SummaryCell({ label, value, tone }: { label: string; value: string; tone?: 'positive' | 'warning' }) {
  return <div className="px-4 py-3.5"><p className="text-[11px] text-muted">{label}</p><p className={cn('mt-1 font-mono text-[17px] tabular-nums tracking-[-0.045em]', tone === 'positive' && 'text-pagar', tone === 'warning' && 'text-escalar')}>{value}</p></div>
}

function weekColumns(currency: string): Column<TreasuryWeek & { id: string }>[] {
  return [
    { key: 'week', header: t('treasury.week'), render: (week) => <span className="text-[12.5px] font-medium">{weekLabel(week)}</span> },
    { key: 'invoices', header: t('treasury.invoices'), render: (week) => <span className="font-mono text-[11px] text-muted">{week.row_ids.length}</span> },
    { key: 'planned', header: t('treasury.planned'), render: (week) => <span className="whitespace-nowrap font-mono text-[12px] tabular-nums">{money(week.total, currency)}</span> },
    { key: 'remaining', header: t('treasury.remaining'), render: (week) => <span className={cn('whitespace-nowrap font-mono text-[12px] tabular-nums', Number(week.remaining_budget) < 0 ? 'text-escalar' : 'text-pagar')}>{money(week.remaining_budget, currency)}</span> },
  ]
}

function WeekDetail({ week, rows, processId, currency }: { week?: TreasuryWeek; rows: TreasuryInvoice[]; processId: number; currency: string }) {
  if (!week) return <EmptyState title={t('treasury.emptyWeek')} className="rounded-[16px] bg-well" />
  return <section aria-labelledby="treasury-week-detail" className="overflow-hidden rounded-[16px] bg-surface ring-1 ring-line">
    <div className="flex items-start justify-between border-b border-hairline px-3.5 py-3">
      <div><h3 id="treasury-week-detail" className="text-[13px] font-medium">{t('treasury.selectedWeek')}</h3><p className="mt-0.5 font-mono text-[11px] text-faint">{weekLabel(week)}</p></div>
      <span className={cn('whitespace-nowrap font-mono text-[12px] tabular-nums', Number(week.remaining_budget) < 0 ? 'text-escalar' : 'text-pagar')}>{Number(week.remaining_budget) < 0 ? t('treasury.overBudget') : t('treasury.withinBudget')}</span>
    </div>
    <div>
      {rows.map((invoice) => <article key={invoice.row_id} className="border-b border-hairline px-3.5 py-3 last:border-0">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0"><p className="truncate text-[12.5px] font-medium">{invoice.name}</p><p className="mt-0.5 truncate text-[11px] text-muted">{invoice.vendor}</p></div>
          <span className="shrink-0 whitespace-nowrap font-mono text-[12px] tabular-nums">{money(invoice.amount, currency)}</span>
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-[11px] text-muted">
          <span className="font-mono">{t('treasury.due')}: {shortDate(invoice.due_date)} · {dueSourceLabel(invoice.provenance.due_date_source)}</span>
          <Link aria-label={`${t('treasury.evidence')}: ${invoice.vendor}`} to={paths.instance(processId, invoice.instance_id)} className="inline-flex shrink-0 items-center gap-1 text-muted hover:text-ink"><span>{t('treasury.evidence')}</span><ArrowUpRight size={12} /></Link>
        </div>
      </article>)}
    </div>
  </section>
}

function VendorTotals({ vendors, currency }: { vendors: TreasuryPlan['suppliers']; currency: string }) {
  return <section aria-labelledby="treasury-vendors"><div className="mb-3"><h2 id="treasury-vendors" className="text-[16px] font-medium tracking-[-0.03em]">{t('treasury.vendorTotals')}</h2></div><NestedCard><DataTable columns={[{ key: 'vendor', header: t('treasury.vendor'), render: (row) => <span className="text-[12.5px] font-medium">{row.vendor}</span> }, { key: 'count', header: t('treasury.count'), render: (row) => <span className="font-mono text-[11px] text-muted">{row.scheduled_count} / {row.invoice_count}</span> }, { key: 'amount', header: t('treasury.amount'), render: (row) => <span className="whitespace-nowrap font-mono text-[12px] tabular-nums">{money(row.scheduled_amount, currency)}</span> }]} rows={vendors.map((vendor) => ({ ...vendor, id: vendor.vendor }))} /></NestedCard></section>
}

function ExcludedRows({ rows, processId }: { rows: TreasuryPlan['exclusions']; processId: number }) {
  return <section aria-labelledby="treasury-excluded"><div className="mb-3"><h2 id="treasury-excluded" className="text-[16px] font-medium tracking-[-0.03em]">{t('treasury.excluded')}</h2><p className="mt-1 max-w-xl text-[12.5px] text-muted">{t('treasury.excludedHint')}</p></div><NestedCard><DataTable columns={[{ key: 'invoice', header: t('treasury.invoice'), render: (row) => <Link to={paths.instance(processId, row.instance_id)} className="text-[12.5px] font-medium hover:underline">{row.name}</Link> }, { key: 'amount', header: t('treasury.amount'), render: (row) => <span className="whitespace-nowrap font-mono text-[12px] tabular-nums">{row.amount != null && row.currency ? money(row.amount, row.currency) : t('treasury.unknownAmount')}</span> }, { key: 'reason', header: t('treasury.reason'), render: (row) => <span className="text-[12px] text-muted" title={row.reason}>{reasonLabel(row.reason_code, row.reason)}</span> }]} rows={rows.map((row) => ({ ...row, id: String(row.instance_id) }))} /></NestedCard></section>
}
