import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  LayoutDashboard, ShoppingBag, Package, BarChart2,
  Users, MessageSquare, LogOut, Menu, X, ChevronDown,
  Bell
} from 'lucide-react'

const NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', roles: ['gestor', 'funcionario'] },
  { to: '/pedidos', icon: ShoppingBag, label: 'Pedidos', roles: ['gestor', 'funcionario'] },
  { to: '/produtos', icon: Package, label: 'Produtos', roles: ['gestor', 'funcionario'] },
  { to: '/relatorios', icon: BarChart2, label: 'Relatórios', roles: ['gestor'] },
  { to: '/atendimentos', icon: MessageSquare, label: 'Atendimentos', roles: ['gestor', 'funcionario'] },
  { to: '/usuarios', icon: Users, label: 'Usuários', roles: ['gestor'] },
]

export default function Layout() {
  const { user, logout, isGestor } = useAuth()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const visibleNav = NAV.filter(n => n.roles.includes(user?.role || ''))

  const navLinkClass = ({ isActive }) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-primary-600 text-white shadow-sm'
        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
    }`

  const Sidebar = ({ mobile }) => (
    <aside className={`${mobile ? 'w-64' : 'w-60 hidden lg:flex'} flex-col bg-white border-r border-gray-100 h-full`}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100">
        <img src="/logo.png" alt="Drogarias Max" className="h-9 w-auto" />
        <p className="text-xs text-gray-400 font-medium">Painel Gerencial</p>
        {mobile && (
          <button onClick={() => setSidebarOpen(false)} className="ml-auto text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        )}
      </div>

      {/* Role badge */}
      <div className="px-4 py-3">
        <div className={`text-xs font-semibold px-2.5 py-1 rounded-full inline-flex items-center gap-1 ${
          isGestor ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
        }`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          {isGestor ? 'Gestor' : 'Funcionário'}
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
        {visibleNav.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} className={navLinkClass} onClick={() => setSidebarOpen(false)}>
            <Icon size={18} /> {label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-gray-100 px-3 py-4">
        <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-gray-50 cursor-default">
          <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
            <span className="text-primary-700 font-bold text-sm">
              {(user?.nome_completo || user?.username || '?')[0].toUpperCase()}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-800 truncate">{user?.nome_completo || user?.username}</p>
            <p className="text-xs text-gray-400">{user?.username}</p>
          </div>
        </div>
        <button onClick={handleLogout} className="mt-2 w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors font-medium">
          <LogOut size={16} /> Sair
        </button>
      </div>
    </aside>
  )

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <Sidebar />

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="fixed inset-0 bg-gray-900/50" onClick={() => setSidebarOpen(false)} />
          <div className="relative flex flex-col h-full">
            <Sidebar mobile />
          </div>
        </div>
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="bg-white border-b border-gray-100 px-4 py-3 flex items-center gap-3 shrink-0">
          <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-gray-500 hover:text-gray-700">
            <Menu size={22} />
          </button>
          <div className="flex-1" />
          <button className="relative text-gray-500 hover:text-gray-700 p-1.5 rounded-lg hover:bg-gray-100">
            <Bell size={18} />
          </button>
          <div className="flex items-center gap-2 text-sm text-gray-600 font-medium border border-gray-200 rounded-lg px-3 py-1.5">
            <div className="w-6 h-6 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-primary-700 font-bold text-xs">
                {(user?.nome_completo || user?.username || '?')[0].toUpperCase()}
              </span>
            </div>
            <span className="hidden sm:block">{user?.nome_completo || user?.username}</span>
            <ChevronDown size={14} />
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto bg-gray-50">
          <div className="max-w-7xl mx-auto px-4 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
