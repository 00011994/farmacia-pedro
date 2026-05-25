/**
 * Variantes:
 *   offer      — vermelho, "Oferta Relâmpago" ⚡
 *   discount   — amarelo, "XX% OFF"
 *   category   — azul claro, categoria do produto
 *   stock-ok   — verde, em estoque
 *   stock-out  — vermelho claro, sem estoque
 *   new        — azul sólido, produto novo
 *   free-ship  — azul claro, frete grátis
 */
export default function Badge({ variant = 'category', children, className = '' }) {
  const styles = {
    'offer':      'bg-max-red text-white',
    'discount':   'bg-max-yellow text-gray-900',
    'category':   'bg-primary-50 text-primary-700',
    'stock-ok':   'bg-green-100 text-green-800',
    'stock-out':  'bg-red-50 text-max-red',
    'new':        'bg-primary-600 text-white',
    'free-ship':  'bg-primary-100 text-primary-800',
  }

  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-0.5 rounded-pill ${styles[variant] ?? styles.category} ${className}`}
    >
      {children}
    </span>
  )
}
