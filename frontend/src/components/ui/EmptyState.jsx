export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center animate-fade-in">
      {Icon && (
        <div className="w-14 h-14 rounded-2xl bg-green-50 border border-surface-border flex items-center justify-center mb-4">
          <Icon className="w-7 h-7 text-brand-600" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-brand-900">{title}</h3>
      {description && <p className="text-sm text-gray-500 mt-2 max-w-sm">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}
