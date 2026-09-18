import type { InstanceDetail, QueueItem, RuleHit } from '../api/types'
import { classifiedInvoices, type ClassifiedInvoice } from './invoices.generated'
import { extractedDocuments, imageOnlyFiles } from './documents.generated'
import { instanceId } from '../lib/ids'

const imageOnly = new Set(imageOnlyFiles)

export function invoiceById(fileId: string): ClassifiedInvoice | undefined {
  return classifiedInvoices.find((item) => item.fileId === fileId)
}

export function toQueueItem(invoice: ClassifiedInvoice, runId: string): QueueItem {
  const image = imageOnly.has(invoice.fileId)
  const state = image && invoice.result !== 'ESCALAR' ? 'OCR' : invoice.state
  const result = state === 'OCR' ? null : invoice.result
  return {
    id: instanceId(invoice.fileId),
    runId,
    fileId: invoice.fileId,
    result,
    reason: image && state === 'OCR' ? 'Sin texto extraíble' : invoice.reason,
    state,
    latencyMs: invoice.latencyMs,
  }
}

export function catalogQueue(runId: string): QueueItem[] {
  return classifiedInvoices.map((invoice) => toQueueItem(invoice, runId))
}

export function catalogCounts(runId: string) {
  return catalogQueue(runId).reduce(
    (acc, item) => {
      if (item.result === 'PAGAR') acc.pagar += 1
      else if (item.result === 'NO_PAGAR') acc.noPagar += 1
      else if (item.result === 'ESCALAR') acc.escalar += 1
      else acc.pending += 1
      return acc
    },
    { pagar: 0, noPagar: 0, escalar: 0, pending: 0 },
  )
}

function hitsFor(invoice: ClassifiedInvoice): RuleHit[] {
  if (invoice.state === 'OCR' || (imageOnly.has(invoice.fileId) && invoice.result !== 'ESCALAR')) {
    return [
      {
        id: 'ocr',
        ok: true,
        title: 'Render 300 dpi',
        detail: 'Imagen, esperando segundo lector',
        latencyMs: Math.min(invoice.latencyMs, 980),
      },
    ]
  }
  const doc = extractedDocuments[invoice.fileId]
  const ok = invoice.result === 'PAGAR'
  return [
    {
      id: 'extract',
      ok: true,
      title: 'Extraído de PDF',
      detail: doc ? 'Documento leído correctamente' : 'Campos parciales',
      latencyMs: 180,
    },
    {
      id: 'nif',
      ok: Boolean(doc?.nif && doc.nif !== '—'),
      title: doc ? `NIF ${doc.nif}` : 'NIF',
      detail: ok ? 'Proveedor identificado' : invoice.reason,
      latencyMs: 90,
    },
    {
      id: 'iban',
      ok,
      title: ok ? 'IBAN coincide' : 'IBAN / pedido',
      detail: doc?.iban ?? invoice.reason,
      latencyMs: 80,
    },
  ]
}

export function toDetail(invoice: ClassifiedInvoice, runId: string, versionLabel: string): InstanceDetail {
  const item = toQueueItem(invoice, runId)
  const doc = extractedDocuments[invoice.fileId] ?? null
  const image = imageOnly.has(invoice.fileId)
  return {
    id: item.id,
    fileId: invoice.fileId,
    runId,
    result: item.result,
    confidence: item.state === 'OCR' ? invoice.confidence : invoice.confidence,
    state: item.state,
    reason: item.reason,
    document: image ? null : doc,
    ocrNote: image ? 'Sin texto extraíble. Escaneada, fax o copia. Consenso OCR en curso.' : undefined,
    ruleHits: hitsFor(invoice),
    meta: {
      archivo: invoice.fileId,
      proveedor: doc?.supplierName ?? invoice.sector,
      herramienta: image ? 'vision · ocr_local' : 'pdf_text · erp_bridge',
      norma: versionLabel,
    },
    trace: [
      { step: 'RECIBIDA', input: invoice.fileId, output: 'nuevo', latencyMs: 4, retries: 0 },
      {
        step: item.state === 'OCR' ? 'OCR' : 'DECIDIDA',
        input: versionLabel,
        output: item.result ?? item.state,
        latencyMs: invoice.latencyMs,
        retries: 0,
      },
    ],
  }
}

export const cajaFileCount = classifiedInvoices.length
