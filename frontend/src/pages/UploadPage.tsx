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
  { value: 'DATABOOK_FULL','label': 'Databook completo (CSVs extraídos)' },
]

const STATUS_COLORS: Record<string, string> = {
  PENDING:   'bg-gray-100 text-gray-600',
  RUNNING:   'bg-yellow-100 text-yellow-700',
  COMPLETED: 'bg-green-100 text-green-700',
  FAILED:    'bg-red-100 text-red-700',
  SKIPPED:   'bg-gray-100 text-gray-400',
}

interface Batch {
  id: number
  file_type: string
  original_name: string
  status: string
  rows_inserted: number | null
  rows_errored: number | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export default function UploadPage() {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [fileType, setFileType] = useState('SGS')
  const [dragging, setDragging] = useState(false)
  const [runningId, setRunningId] = useState<number | null>(null)

  const { data: batches = [] } = useQuery<Batch[]>({
    queryKey: ['uploads'],
    queryFn: () => api.get(`/projects/${PROJECT_ID}/uploads`).then(r => r.data),
    refetchInterval: runningId ? 3000 : false,
  })

  // Para polling quando batch está rodando
  useEffect(() => {
    const running = batches.find(b => b.status === 'RUNNING' || b.status === 'PENDING')
    setRunningId(running?.id ?? null)
    if (running?.status === 'COMPLETED' || running?.status === 'FAILED') {
      qc.invalidateQueries({ queryKey: ['uploads'] })
    }
  }, [batches, qc])

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
    onSuccess: () => qc.invalidateQueries({ queryKey: ['uploads'] }),
  })

  function handleFile(file: File) {
    upload.mutate(file)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">Importar Dados</h1>
        <button
          onClick={() => {
            if (confirm('Apagar TODOS os dados do projeto? Esta ação não pode ser desfeita.')) {
              resetDb.mutate()
            }
          }}
          disabled={resetDb.isPending}
          className="text-xs px-3 py-1.5 rounded border border-red-300 text-red-600 hover:bg-red-50 transition disabled:opacity-50"
        >
          {resetDb.isPending ? 'Limpando...' : 'Limpar BD'}
        </button>
      </div>

      {/* Upload zone */}
      <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-6 space-y-4">
        <div className="flex gap-3 items-center">
          <select value={fileType} onChange={e => setFileType(e.target.value)}
            className="border border-gray-200 rounded px-3 py-2 text-sm">
            {FILE_TYPES.map(ft => (
              <option key={ft.value} value={ft.value}>{ft.label}</option>
            ))}
          </select>
        </div>

        <div
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={e => {
            e.preventDefault(); setDragging(false)
            const f = e.dataTransfer.files[0]
            if (f) handleFile(f)
          }}
          onClick={() => fileRef.current?.click()}
          className={clsx(
            'border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors',
            dragging ? 'border-blue-400 bg-blue-50' : 'border-gray-200 hover:border-blue-300'
          )}>
          <p className="text-2xl mb-2">↑</p>
          <p className="text-sm text-gray-600">Arraste o arquivo ou clique para selecionar</p>
          <p className="text-xs text-gray-400 mt-1">.xlsx · .xlsb · .csv</p>
          <input ref={fileRef} type="file" className="hidden"
            accept=".xlsx,.xlsb,.csv"
            onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }} />
        </div>

        {upload.isPending && (
          <p className="text-sm text-yellow-600 animate-pulse">Enviando arquivo...</p>
        )}
        {upload.isSuccess && (
          <p className="text-sm text-green-600">Arquivo enviado. ETL em processamento...</p>
        )}
        {upload.isError && (
          <p className="text-sm text-red-600">Erro ao enviar arquivo.</p>
        )}
      </div>

      {/* Histórico */}
      <div className="bg-white rounded-lg border border-gray-100 shadow-sm">
        <div className="px-4 py-3 border-b">
          <h2 className="text-sm font-semibold text-gray-600">Histórico de Importações</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr className="text-left text-xs text-gray-500">
              <th className="px-3 py-2">Arquivo</th>
              <th className="px-3 py-2">Tipo</th>
              <th className="px-3 py-2 text-center">Status</th>
              <th className="px-3 py-2 text-right">Inseridos</th>
              <th className="px-3 py-2 text-right">Erros</th>
              <th className="px-3 py-2">Início</th>
              <th className="px-3 py-2">Fim</th>
            </tr>
          </thead>
          <tbody>
            {batches.length === 0 && (
              <tr><td colSpan={7} className="text-center py-6 text-gray-400">Nenhuma importação ainda</td></tr>
            )}
            {batches.map(b => (
              <tr key={b.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-3 py-2 text-xs font-mono text-gray-700">{b.original_name}</td>
                <td className="px-3 py-2 text-xs">{b.file_type}</td>
                <td className="px-3 py-2 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATUS_COLORS[b.status]}`}>
                    {b.status === 'RUNNING' ? '⟳ ' : ''}{b.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-right text-green-600">{b.rows_inserted ?? '—'}</td>
                <td className="px-3 py-2 text-right text-red-500">{b.rows_errored ?? '—'}</td>
                <td className="px-3 py-2 text-xs text-gray-500">{b.started_at?.slice(0,19).replace('T',' ') ?? '—'}</td>
                <td className="px-3 py-2 text-xs text-gray-500">{b.completed_at?.slice(0,19).replace('T',' ') ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
