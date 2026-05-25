import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Eye, EyeOff, LogIn, Pill } from 'lucide-react'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '' })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(form.username, form.password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Credenciais inválidas. Verifique usuário e senha.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 bg-gradient-to-br from-primary-600 to-primary-900 p-12 text-white">
        <div className="flex items-center gap-3">
          <div className="bg-white rounded-xl p-2">
            <img src="/logo.png" alt="Drogarias Max" className="h-8 w-auto" />
          </div>
          <p className="text-primary-200 text-sm font-medium">Painel Gerencial</p>
        </div>
        <div>
          <h2 className="text-4xl font-black leading-tight mb-4">
            Gestão inteligente<br />para sua farmácia
          </h2>
          <p className="text-primary-200 text-lg">
            Controle pedidos, estoque, relatórios e atendimentos em um só lugar.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {[
            ['Pedidos em tempo real', 'Via chat com IA'],
            ['Relatórios automáticos', 'Gerados por agentes'],
            ['Controle de estoque', 'Alertas inteligentes'],
            ['Dois perfis de acesso', 'Gestor e Funcionário'],
          ].map(([title, sub]) => (
            <div key={title} className="bg-white/10 rounded-xl p-4">
              <p className="font-semibold text-sm">{title}</p>
              <p className="text-primary-300 text-xs mt-0.5">{sub}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-6 bg-gray-50">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="flex flex-col items-center gap-1 mb-8 lg:hidden">
            <img src="/logo.png" alt="Drogarias Max" className="h-10 w-auto" />
            <p className="text-gray-400 text-xs">Painel Gerencial</p>
          </div>

          <div className="card p-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-1">Entrar</h1>
            <p className="text-gray-500 text-sm mb-6">Acesse o painel gerencial</p>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="label">Usuário</label>
                <input
                  type="text"
                  value={form.username}
                  onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                  className="input"
                  placeholder="gestor ou funcionario"
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="label">Senha</label>
                <div className="relative">
                  <input
                    type={showPass ? 'text' : 'password'}
                    value={form.password}
                    onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                    className="input pr-10"
                    placeholder="••••••••"
                    required
                  />
                  <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                    {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 py-3 mt-2">
                <LogIn size={16} />
                {loading ? 'Entrando...' : 'Entrar'}
              </button>
            </form>

            <div className="mt-6 p-4 bg-gray-50 rounded-lg text-xs text-gray-500">
              <p className="font-semibold text-gray-700 mb-1">Usuários demo:</p>
              <p><code className="bg-gray-200 px-1 rounded">gestor</code> / farmacia123 (acesso total)</p>
              <p><code className="bg-gray-200 px-1 rounded">funcionario</code> / farmacia456 (acesso limitado)</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
