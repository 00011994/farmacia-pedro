import { ShoppingBag, Package, ShoppingCart } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const CATEGORY_BADGE = {
  Analgesico:  'bg-primary-50 text-primary-700',
  Antibiotico: 'bg-purple-100 text-purple-700',
  Higiene:     'bg-cyan-100 text-cyan-700',
  Suplemento:  'bg-orange-100 text-orange-700',
}

export default function ProductCard({ product }) {
  const navigate  = useNavigate()
  const inStock   = product.stock > 0
  const badgeClass = CATEGORY_BADGE[product.category] || 'bg-gray-100 text-gray-600'

  const discountPct = product.originalPrice
    ? Math.round((1 - product.price / product.originalPrice) * 100)
    : null

  return (
    <div className="card card-hover group relative flex flex-col">
      {/* Offer badge */}
      {discountPct > 0 && (
        <span className="absolute top-2 left-2 z-10 badge-discount">
          {discountPct}% OFF
        </span>
      )}

      {/* Image area */}
      <div className="h-40 bg-primary-50 flex items-center justify-center relative overflow-hidden">
        <Package size={52} className="text-primary-200" />
        {!inStock && (
          <div className="absolute inset-0 bg-gray-900/50 flex items-center justify-center">
            <span className="badge-offer">Indisponível</span>
          </div>
        )}
        <span className={`absolute top-2 right-2 text-xs font-semibold px-2.5 py-0.5 rounded-pill ${badgeClass}`}>
          {product.category}
        </span>
      </div>

      {/* Content */}
      <div className="p-4 flex flex-col flex-1">
        <p className="text-[11px] text-gray-400 font-mono mb-1">{product.sku}</p>
        <h3 className="font-semibold text-gray-800 text-sm mb-3 line-clamp-2 flex-1">
          {product.name}
        </h3>

        {/* Pricing */}
        <div className="mb-3">
          {product.originalPrice && (
            <span className="block text-xs text-gray-400 line-through">
              R$ {product.originalPrice.toFixed(2).replace('.', ',')}
            </span>
          )}
          <span className="text-max-red font-extrabold text-2xl leading-none">
            R$ {product.price.toFixed(2).replace('.', ',')}
          </span>
          <span className={`mt-1 block text-xs font-semibold ${inStock ? 'text-success' : 'text-max-red'}`}>
            {inStock ? `${product.stock} em estoque` : 'Sem estoque'}
          </span>
        </div>

        {/* CTA buttons */}
        <div className="flex flex-col gap-2">
          <button
            onClick={() => navigate('/chat')}
            disabled={!inStock}
            className="w-full flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-800 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed text-white font-bold py-2 rounded-pill text-sm transition-colors"
          >
            <ShoppingCart size={14} />
            Adicionar ao carrinho
          </button>
          <button
            onClick={() => navigate('/chat')}
            disabled={!inStock}
            className="w-full flex items-center justify-center gap-2 bg-max-red hover:bg-max-red-dark disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed text-white font-bold py-2 rounded-pill text-sm transition-colors"
          >
            <ShoppingBag size={14} />
            Comprar agora
          </button>
        </div>
      </div>
    </div>
  )
}
