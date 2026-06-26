import { useRef, useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import clsx from 'clsx'

const PROJECT_ID = 1

const FILE_TYPES = [
  { value: 'SGS',          label: 'Spools — SGS-SGM Excel' },
  { value: 'JOINTS',       label: 'Juntas — MAPA_JUNTA xlsb' },
  { value: 'MTO',          label: 'MTO — TYS-TUB-1 Excel' },
  { value: 'VALVULAS',     label: 'Válvulas Excel' },
  { value: 'DATABOOK_FULL',label: 'Databook completo (CSVs)' },
]

const STATUS_LABEL: Record<string, string> = {
  PENDING:   'Aguardando',
  RUNNING:   'Processando',
  COMPLETED: 'Concluído',
  FAILED:    'Erro',
}
const STATUS_COLOR: Record<string, string> = {
  PENDING:   'bg-gray-100 text-gray-500',
  RUNNING:   'bg-blue-100 text-blue-700',
  COMPLETED: 'bg-green-100 text-green-700',
  FAILED:    'bg-red-100 text-red-700',
}

interface Batch {
  id: number
  file_type: string
  original_name: string
  status: string
  rows_inserted: number | null
  rows_errored: number | null
  rows_processed: number | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  error_log: string | null
}

function ElapsedTimer({ startedAt }: { startedAt: string | null }) {
  const [secs, setSecs] = useState(0)
  useEffect(() => {
    if (!startedAt) return
    const t = setInterval(() => {
      setSecs(Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000))
    }, 1000)
    return () => clearInterval(t)
  }, [startedAt])
  if (!startedAt) return null
  const m = Math.floor(secs / 60), s = secs % 60
  return <span className="text-xs text-blue-600 tabular-nums">{m}:{String(s).padStart(2,'0')}</span>
}

function BatchRow({ b, expanded, onToggle }: { b: Batch; expanded: boolean; onToggle: () => void }) {
  const isRunning = b.status === 'RUNNING'
  const processed = b.rows_processed ?? 0

  return (
    <>
      <tr className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer" onClick={onToggle}>
        <td className="px-3 py-2 text-xs font-mono text-gray-700 max-w-xs truncate" title={b.original_name}>
          {b.original_name}
        </td>
        <td className="px-3 py-2 text-xs text-gray-500">{b.file_type}</td>
        <td className="px-3 py-2">
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATUS_COLOR[b.status]}`}>
              {isRunning && <span className="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse mr-1" />}
              {STATUS_LABEL[b.status] ?? b.status}
            </span>
            {isRunning && <ElapsedTimer startedAt={b.started_at} />}
          </div>
          {isRunning && processed > 0 && (
            <div className="mt-1.5 w-full bg-gray-200 rounded-full h-1.5">
              <div className="bg-blue-500 h-1.5 rounded-full animate-pulse" style={{ width: '60%' }} />
            </div>
          )}
        </td>
        <td className="px-3 py-2 text-right text-xs text-green-600 font-medium">
          {isRunning && processed > 0 ? (
            <span className="animate-pulse">{processed.toLocaleString('pt-BR')} ↑</span>
          ) : (b.rows_inserted?.toLocaleString('pt-BR') ?? '—')}
        </td>
        <td className="px-3 py-2 text-right text-xs text-red-500">{b.rows_errored ?? '—'}</td>
        <td className="px-3 py-2 text-xs text-gray-400">
          {b.started_at?.slice(0,16).replace('T',' ') ?? '—'}
        </td>
        <td className="px-3 py-2 text-xs text-gray-400">
          {b.completed_at?.slice(0,16).replace('T',' ') ?? '—'}
        </td>
        <td className="px-3 py-2 text-xs text-gray-400 text-center">{expanded ? '▲' : '▼'}</td>
      </tr>
      {expanded && b.error_log && b.error_log !== '[]' && (
        <tr className="bg-red-50 border-b">
          <td colSpan={8} className="px-4 py-2">
            <p className="text-xs font-semibold text-red-600 mb-1">Log de erros:</p>
            <pre className="text-xs text-red-700 whitespace-pre-wrap break-all max-h-32 overflow-y-auto">
              {b.error_log}
            </pre>
          </td>
        </tr>
      )}
    </>
  )
}

export default function UploadPage() {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [fileType, setFileType] = useState('SGS')
  const [dragging, setDragging] = useState(false)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const hasRunning = (batches: Batch[]) => batches.some(b => b.status === 'RUNNING' || b.status === 'PENDING')

  const { data: batches = [] } = useQuery<Batch[]>({
    queryKey: ['uploads'],
    queryFn: () => api.get(`/projects/${PROJECT_ID}/uploads`).then(r => r.data),
    refetchInterval: (query) => hasRunning(query.state.data ?? []) ? 3000 : false,
  })

  const resetDb = useMutation({
    mutationFn: () => api.delete(`/projects/${PROJECT_ID}/uploads/reset-data`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['uploads'] }),
  })

  const upload = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      form.append('file_type', fileType)
      return api.post(`/projects/${PROJECT_ID}/uploads`, form)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['uploads'] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">Importar Dados</h1>
        <button
          onClick={() => confirm('Apagar TODOS os dados do projeto?') && resetDb.mutate()}
          disabled={resetDb.isPending}
          className="text-xs px-3 py-1.5 rounded border border-red-300 text-red-600 hover:bg-red-50 transition disabled:opacity-50"
        >
          {resetDb.isPending ? 'Limpando...' : '⚠ Limpar BD'}
        </button>
      </div>

      {/* Upload zone */}
      <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-6 space-y-4">
        <select value={fileType} onChange={e => setFileType(e.target.value)}
          className="border border-gray-200 rounded px-3 py-2 text-sm w-full sm:w-auto">
          {FILE_TYPES.map(ft => <option key={ft.value} value={ft.value}>{ft.label}</option>)}
        </select>

        <div
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) upload.mutate(f) }}
          onClick={() => fileRef.current?.click()}
          className={clsx(
            'border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors',
            dragging ? 'border-blue-400 bg-blue-50' : 'border-gray-200 hover:border-blue-300',
            upload.isPending && 'opacity-50 pointer-events-none'
          )}>
          <p className="text-3xl mb-2">{upload.isPending ? '⏳' : '↑'}</p>
          <p className="text-sm text-gray-600">
            {upload.isPending ? 'Enviando arquivo...' : 'Arraste o arquivo ou clique para selecionar'}
          </p>
          <p className="text-xs text-gray-400 mt-1">.xlsx · .xlsb · .csv</p>
          <input ref={fileRef} type="file" className="hidden" accept=".xlsx,.xlsb,.csv"
            onChange={e => { const f = e.target.files?.[0]; if (f) upload.mutate(f) }} />
        </div>

        {upload.isSuccess && !upload.isPending && (
          <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 rounded p-3">
            <span>✓</span>
            <span>Arquivo enviado. ETL em processamento — acompanhe abaixo.</span>
          </div>
        )}
        {upload.isError && (
          <div className="text-sm text-red-600 bg-red-50 rounded p-3">
            ✕ Erro ao enviar arquivo. Verifique o tipo selecionado.
          </div>
        )}
      </div>

      {/* Histórico */}
      <div className="bg-white rounded-lg border border-gray-100 shadow-sm">
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-600">Histórico de Importações</h2>
          {hasRunning(batches) && (
            <span className="flex items-center gap-1.5 text-xs text-blue-600">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              Processando…
            </span>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr className="text-left text-xs text-gray-500">
                <th className="px-3 py-2">Arquivo</th>
                <th className="px-3 py-2">Tipo</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 text-right">Inseridos</th>
                <th className="px-3 py-2 text-right">Erros</th>
                <th className="px-3 py-2">Início</th>
                <th className="px-3 py-2">Fim</th>
                <th className="px-3 py-2 text-center w-8" />
              </tr>
            </thead>
            <tbody>
              {batches.length === 0 && (
                <tr><td colSpan={8} className="text-center py-8 text-gray-400">Nenhuma importação ainda</td></tr>
              )}
              {batches.map(b => (
                <BatchRow key={b.id} b={b}
                  expanded={expandedId === b.id}
                  onToggle={() => setExpandedId(expandedId === b.id ? null : b.id)} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
