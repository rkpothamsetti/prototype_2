export function Skeleton({ className = '' }) {
  return <div className={`skeleton ${className}`} />
}

export function StatCardSkeleton() {
  return (
    <div className="card-sm space-y-3">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-16" />
      <Skeleton className="h-2 w-32" />
    </div>
  )
}

export function ChartSkeleton() {
  return (
    <div className="card h-80 space-y-4">
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-full min-h-[200px] w-full rounded-xl" />
    </div>
  )
}

export function ListSkeleton({ rows = 4 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="card-sm flex gap-3">
          <Skeleton className="h-12 w-12 rounded-lg shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  )
}
