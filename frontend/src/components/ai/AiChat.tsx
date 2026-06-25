import { useState, useRef, useEffect } from 'react'
import api from '../../api/client'

interface Msg { role: 'user' | 'ai'; text: string }

const SUGGESTIONS = [
  'Qual o status geral do projeto?',
  'Quais spools estão em hold?',
  'Mostre os soldadores com maior índice de reparo',
  'Quantas juntas estão liberadas?',
  'Quais são as NCRs abertas?',
]

export default function AiChat({ projectId }: { projectId: number }) {
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: 'ai', text: '👋 Olá! Sou o assistente IA do EPC BuildControl. Pergunte qualquer coisa sobre o projeto UGH.' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  async function send(text?: string) {
    const q = text ?? input.trim()
    if (!q || loading) return
    setInput('')
    setMsgs(m => [...m, { role: 'user', text: q }])
    setLoading(true)
    try {
      const { data } = await api.post(`/projects/${projectId}/ai/chat`, { message: q })
      setMsgs(m => [...m, { role: 'ai', text: data.reply }])
    } catch {
      setMsgs(m => [...m, { role: 'ai', text: '❌ Erro ao contatar o assistente.' }])
    } finally { setLoading(false) }
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-blue-600 text-white shadow-lg hover:bg-blue-700 flex items-center justify-center text-2xl transition-all"
        title="Assistente IA"
      >
        {open ? '×' : '✦'}
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-96 max-h-[70vh] flex flex-col bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-3 flex items-center gap-2">
            <span className="text-white text-lg">✦</span>
            <div>
              <p className="text-white font-semibold text-sm">Assistente IA</p>
              <p className="text-blue-200 text-xs">EPC BuildControl · UGH</p>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
            {msgs.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap ${
                  m.role === 'user'
                    ? 'bg-blue-600 text-white rounded-br-sm'
                    : 'bg-white text-gray-800 shadow-sm border border-gray-100 rounded-bl-sm'
                }`}>
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm px-4 py-2">
                  <span className="flex gap-1">
                    {[0,1,2].map(i => <span key={i} className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{animationDelay:`${i*0.15}s`}} />)}
                  </span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Suggestions */}
          {msgs.length === 1 && (
            <div className="px-3 py-2 border-t bg-white flex flex-wrap gap-1">
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => send(s)}
                  className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-full hover:bg-blue-100 transition">
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="px-3 py-2 border-t bg-white flex gap-2">
            <input
              value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
              placeholder="Pergunte sobre o projeto..."
              className="flex-1 text-sm border border-gray-200 rounded-xl px-3 py-2 outline-none focus:border-blue-400"
              disabled={loading}
            />
            <button onClick={() => send()} disabled={loading || !input.trim()}
              className="bg-blue-600 text-white px-3 py-2 rounded-xl hover:bg-blue-700 disabled:opacity-40 text-sm">
              ↑
            </button>
          </div>
        </div>
      )}
    </>
  )
}
