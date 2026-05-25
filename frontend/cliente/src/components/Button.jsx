/**
 * Variantes:
 *   primary   — vermelho, CTA de compra
 *   secondary — azul, ação institucional
 *   outline   — borda azul, sem fundo
 *   whatsapp  — verde WhatsApp
 *   ghost     — branco/cinza, ação neutra
 */
export default function Button({
  variant = 'secondary',
  size = 'md',
  disabled = false,
  fullWidth = false,
  children,
  className = '',
  ...props
}) {
  const base = 'inline-flex items-center justify-center gap-2 font-bold rounded-pill transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed'

  const variants = {
    primary:   'bg-max-red hover:bg-max-red-dark text-white',
    secondary: 'bg-primary-600 hover:bg-primary-800 text-white',
    outline:   'border-2 border-primary-600 text-primary-600 hover:bg-primary-600 hover:text-white',
    whatsapp:  'bg-whatsapp hover:opacity-90 text-white',
    ghost:     'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200',
  }

  const sizes = {
    sm: 'text-xs px-4 py-1.5',
    md: 'text-sm px-6 py-2.5',
    lg: 'text-base px-8 py-3',
  }

  return (
    <button
      disabled={disabled}
      className={`${base} ${variants[variant]} ${sizes[size]} ${fullWidth ? 'w-full' : ''} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
