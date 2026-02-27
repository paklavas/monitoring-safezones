export type AlertItem = {
  id: string
  message: string
  type: 'info' | 'success' | 'warning' | 'danger'
  time: string
  zoneId?: number
}

const typeStyles = {
  info: 'border-l-text-muted',
  success: 'border-l-success',
  warning: 'border-l-accent',
  danger: 'border-l-danger',
}

export default function AlertList({ items }: { items: AlertItem[] }) {
  return (
    <div className="flex flex-col gap-2 overflow-y-auto pr-1">
      {items.length === 0 ? (
        <p className="text-sm text-text-dim py-4">No alerts yet</p>
      ) : (
        items.map((a) => (
          <div
            key={a.id}
            className={`bg-card border border-border rounded p-3 border-l-4 ${typeStyles[a.type]}`}
          >
            <p className="text-sm text-white">{a.message}</p>
            <p className="text-xs text-text-dim mt-1">{a.time}</p>
          </div>
        ))
      )}
    </div>
  )
}
