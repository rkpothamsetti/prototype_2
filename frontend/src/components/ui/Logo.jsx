import { APP_NAME, LOGO_SRC } from '../../constants'

export function Logo({ size = 'md', showText = false, className = '' }) {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <img
        src={LOGO_SRC}
        alt={`${APP_NAME} logo`}
        className={`${sizes[size] || sizes.md} object-contain shrink-0`}
      />
      {showText && (
        <div className="min-w-0">
          <p className="font-bold text-brand-900 text-sm leading-tight truncate">{APP_NAME}</p>
        </div>
      )}
    </div>
  )
}
