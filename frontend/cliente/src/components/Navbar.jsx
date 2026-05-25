import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Search, MessageCircle, Menu, X, Phone, User, LogOut, ChevronDown, ShoppingCart } from 'lucide-react'
import { useCustomerAuth } from '../contexts/CustomerAuthContext'

const NAV_LINKS = [
  { to: '/',                            label: 'Início' },
  { to: '/catalogo',                    label: 'Todos os Produtos' },
  { to: '/catalogo?category=Analgesico',label: 'Analgésicos' },
  { to: '/catalogo?category=Antibiotico',label: 'Antibióticos' },
  { to: '/catalogo?category=Higiene',   label: 'Higiene' },
  { to: '/catalogo?category=Suplemento',label: 'Suplementos' },
]

export default function Navbar() {
  const [menuOpen, setMenuOpen]       = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [query, setQuery]             = useState('')
  const navigate                      = useNavigate()
  const { customer, isLoggedIn, logout } = useCustomerAuth()

  const handleSearch = (e) => {
    e.preventDefault()
    if (query.trim()) {
      navigate(`/catalogo?q=${encodeURIComponent(query.trim())}`)
      setQuery('')
      setMenuOpen(false)
    }
  }

  const handleLogout = () => {
    logout()
    setUserMenuOpen(false)
    navigate('/')
  }

  return (
    <header className="bg-white sticky top-0 z-40 shadow-sm">
      {/* Top bar */}
      <div className="bg-primary-600 text-white text-xs py-1.5">
        <div className="max-w-[1200px] mx-auto px-6 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Phone size={11} /> (21) 3000-0000
          </span>
          <span className="hidden sm:block">Entrega rápida · Plantão 24h · Barra Blue</span>
          <Link to="/chat" className="flex items-center gap-1 font-semibold hover:text-primary-200 transition-colors">
            <MessageCircle size={11} /> Chat IA
          </Link>
        </div>
      </div>

      {/* Main nav */}
      <div className="max-w-[1200px] mx-auto px-6 py-3 flex items-center gap-4">
        {/* Logo */}
        <Link to="/" className="shrink-0">
          <img src="/logo.png" alt="Drogarias Max" className="h-10 w-auto" />
        </Link>

        {/* Search */}
        <form onSubmit={handleSearch} className="flex-1 max-w-2xl">
          <div className="relative">
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar remédios, higiene, suplementos..."
              className="w-full pl-4 pr-12 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:border-primary-500 text-sm font-medium"
            />
            <button
              type="submit"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-primary-600 hover:text-primary-800 p-1 transition-colors"
            >
              <Search size={18} />
            </button>
          </div>
        </form>

        {/* Actions */}
        <div className="hidden sm:flex items-center gap-2">
          <Link
            to="/chat"
            className="flex items-center gap-2 bg-primary-600 hover:bg-primary-800 text-white px-4 py-2.5 rounded-pill text-sm font-bold transition-colors"
          >
            <MessageCircle size={15} /> Falar com IA
          </Link>

          {isLoggedIn ? (
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(v => !v)}
                className="flex items-center gap-2 border border-gray-200 hover:border-primary-400 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 transition-colors"
              >
                <div className="w-6 h-6 bg-primary-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">{customer?.nome?.[0]?.toUpperCase()}</span>
                </div>
                <span className="max-w-24 truncate">{customer?.nome?.split(' ')[0]}</span>
                <ChevronDown size={14} />
              </button>
              {userMenuOpen && (
                <div className="absolute right-0 top-full mt-1 w-44 bg-white rounded-xl shadow-card-hover border border-gray-100 py-1 z-50">
                  <Link
                    to="/minha-conta"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  >
                    <User size={14} /> Minha conta
                  </Link>
                  <hr className="my-1 border-gray-100" />
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-max-red hover:bg-red-50"
                  >
                    <LogOut size={14} /> Sair
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/entrar" className="text-sm text-gray-600 hover:text-primary-600 font-semibold px-3 py-2 transition-colors">
                Entrar
              </Link>
              <Link to="/cadastro" className="text-sm border-2 border-primary-600 text-primary-600 hover:bg-primary-600 hover:text-white font-bold px-4 py-2 rounded-pill transition-colors">
                Cadastrar
              </Link>
            </div>
          )}
        </div>

        {/* Mobile menu button */}
        <button className="sm:hidden text-gray-600" onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Nav links bar */}
      <nav className="border-t border-gray-100">
        <div className="max-w-[1200px] mx-auto px-6">
          <ul className={`${menuOpen ? 'flex flex-col py-3 gap-1' : 'hidden sm:flex'} sm:flex-row sm:items-center sm:gap-6 sm:py-2 text-sm font-semibold`}>
            {NAV_LINKS.map(({ to, label }) => (
              <li key={to}>
                <Link
                  to={to}
                  className="text-gray-600 hover:text-primary-600 py-1.5 block transition-colors"
                  onClick={() => setMenuOpen(false)}
                >
                  {label}
                </Link>
              </li>
            ))}
            {/* Mobile extras */}
            <li className="sm:hidden pt-2 border-t border-gray-100">
              <Link to="/chat" className="flex items-center gap-2 text-primary-600 font-bold py-1" onClick={() => setMenuOpen(false)}>
                <MessageCircle size={15} /> Falar com IA
              </Link>
            </li>
            {!isLoggedIn && (
              <li className="sm:hidden">
                <Link to="/entrar" className="text-gray-600 hover:text-primary-600 py-1 block" onClick={() => setMenuOpen(false)}>
                  Entrar / Cadastrar
                </Link>
              </li>
            )}
            {isLoggedIn && (
              <li className="sm:hidden">
                <Link to="/minha-conta" className="text-gray-600 hover:text-primary-600 py-1 block" onClick={() => setMenuOpen(false)}>
                  Minha conta ({customer?.nome?.split(' ')[0]})
                </Link>
              </li>
            )}
          </ul>
        </div>
      </nav>
    </header>
  )
}
