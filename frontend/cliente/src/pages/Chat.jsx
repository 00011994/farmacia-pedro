import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Send, Bot, User, RefreshCw, UserCheck } from 'lucide-react'
import { sendMessage } from '../api/chat'
import { useCustomerAuth } from '../contexts/CustomerAuthContext'

const SESSION_KEY = 'farmacia_chat_session'

function generateSessionId() {
  return 'web_' + Math.random().toString(36).slice(2, 10) + '_' + Date.now()
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2">
      <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center shrink-0">
        <Bot size={16} className="text-white" />
      </div>
      <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
        <div className="flex gap-1">
          <span className="typing-dot w-2 h-2 bg-gray-400 rounded-full" />
          <span className="typing-dot w-2 h-2 bg-gray-400 rounded-full" />
          <span className="typing-dot w-2 h-2 bg-gray-400 rounded-full" />
        </div>
      </div>
    </div>
  )
}

export default function Chat() {
  const { customer, isLoggedIn } = useCustomerAuth()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(() => {
    return sessionStorage.getItem(SESSION_KEY) || generateSessionId()
  })
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    sessionStorage.setItem(SESSION_KEY, sessionId)
  }, [sessionId])

  useEffect(() => {
    if (messages.length === 0) {
      const greeting = isLoggedIn && customer
        ? `Olá, ${customer.nome.split(' ')[0]}! 😊 Sou a Mariana da Drogarias Max.\n\nJá tenho seus dados cadastrados, então posso agilizar seu pedido!\n\nMe diz o produto que você procura!`
        : 'Olá! Sou a Mariana da Drogarias Max 👋\n\nPosso ajudar com:\n• Verificar disponibilidade de produtos\n• Informar preços\n• Realizar pedidos (retirada ou entrega)\n\nMe diga o produto que você procura!'
      setMessages([{ role: 'assistant', content: greeting }])
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendText = async (text) => {
    if (!text || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)
    try {
      const res = await sendMessage(sessionId, text, isLoggedIn ? customer?.id : null)
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.reply }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro de conexão. Tente novamente em instantes.',
      }])
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }

  const handleSend = () => sendText(input.trim())

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleReset = () => {
    const newSession = generateSessionId()
    setSessionId(newSession)
    sessionStorage.setItem(SESSION_KEY, newSession)
    setMessages([{
      role: 'assistant',
      content: 'Olá! Sou a IA da Drogarias Max 👋\n\nNovo atendimento iniciado. Me diga o produto que você procura!',
    }])
    setInput('')
  }

  const quickReplies = ['Tem dipirona?', 'Vitamina C disponível?', 'Fazer entrega em casa', 'Quanto custa amoxicilina?']

  return (
    <main className="max-w-2xl mx-auto px-4 py-6">
      {isLoggedIn && customer && (
        <div className="mb-3 flex items-center justify-between bg-primary-50 border border-primary-200 rounded-lg px-4 py-2.5 text-sm">
          <span className="flex items-center gap-2 text-primary-700">
            <UserCheck size={15} />
            Logado como <strong>{customer.nome.split(' ')[0]}</strong>
            {customer.endereco_bairro && <span className="text-primary-500">· {customer.endereco_bairro}</span>}
          </span>
          <Link to="/minha-conta" className="text-primary-600 hover:underline text-xs font-medium">Editar dados</Link>
        </div>
      )}
      {!isLoggedIn && (
        <div className="mb-3 flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-4 py-2.5 text-sm text-gray-600">
          <span>Faça login para agilizar seus pedidos com seus dados salvos</span>
          <Link to="/entrar" className="text-primary-600 hover:underline text-xs font-medium ml-3 shrink-0">Entrar</Link>
        </div>
      )}
      <div className="card flex flex-col h-[calc(100vh-240px)] min-h-[500px]">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100 bg-primary-600 rounded-t-xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
              <Bot size={22} className="text-white" />
            </div>
            <div>
              <h2 className="text-white font-semibold">Assistente Drogarias Max</h2>
              <span className="text-primary-200 text-xs flex items-center gap-1">
                <span className="w-2 h-2 bg-green-400 rounded-full" /> Online agora
              </span>
            </div>
          </div>
          <button
            onClick={handleReset}
            title="Reiniciar conversa"
            className="text-white/70 hover:text-white p-2 rounded-lg hover:bg-white/10 transition-colors"
          >
            <RefreshCw size={18} />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 chat-messages bg-gray-50">
          {messages.map((msg, i) => (
            <div key={i} className={`flex items-end gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                msg.role === 'user' ? 'bg-gray-700' : 'bg-primary-600'
              }`}>
                {msg.role === 'user' ? <User size={16} className="text-white" /> : <Bot size={16} className="text-white" />}
              </div>
              <div className={`max-w-xs sm:max-w-sm px-4 py-3 rounded-2xl shadow-sm text-sm whitespace-pre-line ${
                msg.role === 'user'
                  ? 'bg-primary-600 text-white rounded-br-sm'
                  : 'bg-white border border-gray-100 text-gray-800 rounded-bl-sm'
              }`}>
                {msg.content}
              </div>
            </div>
          ))}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>

        {/* Quick replies */}
        {messages.length <= 2 && !loading && (
          <div className="px-4 py-2 border-t border-gray-100 flex gap-2 overflow-x-auto">
            {quickReplies.map(q => (
              <button
                key={q}
                onClick={() => sendText(q)}
                className="shrink-0 text-xs bg-primary-50 hover:bg-primary-100 text-primary-700 border border-primary-200 px-3 py-1.5 rounded-full transition-colors whitespace-nowrap"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="p-4 border-t border-gray-100">
          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Digite sua mensagem..."
              rows={1}
              className="flex-1 resize-none border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-primary-500 max-h-28"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="w-11 h-11 bg-primary-600 hover:bg-primary-800 disabled:bg-gray-200 text-white disabled:text-gray-400 rounded-xl flex items-center justify-center transition-colors shrink-0"
            >
              <Send size={18} />
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2 text-center">
            Pressione Enter para enviar · Shift+Enter para nova linha
          </p>
        </div>
      </div>
    </main>
  )
}
