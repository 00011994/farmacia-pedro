import { Link } from 'react-router-dom'
import { Phone, MapPin, Clock, MessageCircle, Instagram, Facebook } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="bg-primary-800 text-white mt-16">
      <div className="max-w-[1200px] mx-auto px-6 py-14 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10">

        {/* Brand */}
        <div>
          <div className="mb-4">
            <div className="inline-block bg-white rounded-xl p-2">
              <img src="/logo.png" alt="Drogarias Max" className="h-9 w-auto" />
            </div>
          </div>
          <p className="text-sm text-primary-200 leading-relaxed">
            Sua saúde em boas mãos há mais de 40 anos. Medicamentos, higiene e suplementos com atendimento personalizado.
          </p>
          <div className="flex gap-3 mt-4">
            <a href="#" aria-label="Instagram" className="text-primary-300 hover:text-white transition-colors">
              <Instagram size={18} />
            </a>
            <a href="#" aria-label="Facebook" className="text-primary-300 hover:text-white transition-colors">
              <Facebook size={18} />
            </a>
          </div>
        </div>

        {/* Produtos */}
        <div>
          <h4 className="text-white font-bold mb-4 text-sm uppercase tracking-wider">Produtos</h4>
          <ul className="space-y-2.5 text-sm">
            {[
              { to: '/catalogo?category=Analgesico', label: 'Analgésicos' },
              { to: '/catalogo?category=Antibiotico', label: 'Antibióticos' },
              { to: '/catalogo?category=Higiene', label: 'Higiene' },
              { to: '/catalogo?category=Suplemento', label: 'Suplementos' },
            ].map(({ to, label }) => (
              <li key={to}>
                <Link to={to} className="text-primary-200 hover:text-white transition-colors">
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {/* Atendimento */}
        <div>
          <h4 className="text-white font-bold mb-4 text-sm uppercase tracking-wider">Atendimento</h4>
          <ul className="space-y-3 text-sm text-primary-200">
            <li className="flex items-center gap-2.5">
              <Phone size={14} className="text-primary-300 shrink-0" />
              (21) 3000-0000
            </li>
            <li className="flex items-start gap-2.5">
              <MapPin size={14} className="text-primary-300 shrink-0 mt-0.5" />
              Av. das Américas, 12.700 – Barra Blue
            </li>
            <li className="flex items-center gap-2.5">
              <Clock size={14} className="text-primary-300 shrink-0" />
              24 horas, 7 dias por semana
            </li>
          </ul>
        </div>

        {/* Chat */}
        <div>
          <h4 className="text-white font-bold mb-4 text-sm uppercase tracking-wider">Atendimento Online</h4>
          <p className="text-sm text-primary-200 mb-4 leading-relaxed">
            Consulte disponibilidade, preços e faça seu pedido pelo nosso chat com IA.
          </p>
          <Link
            to="/chat"
            className="inline-flex items-center gap-2 bg-whatsapp hover:opacity-90 text-white px-5 py-2.5 rounded-pill text-sm font-bold transition-opacity"
          >
            <MessageCircle size={15} />
            Abrir Chat
          </Link>
        </div>
      </div>

      <div className="border-t border-primary-700 py-5">
        <p className="text-center text-xs text-primary-400">
          © {new Date().getFullYear()} Drogarias Max · Todos os direitos reservados · CNPJ: 00.000.000/0001-00
        </p>
      </div>
    </footer>
  )
}
