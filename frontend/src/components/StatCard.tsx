type StatCardProps = {
  label: string
  value: string
  color?: 'accent' | 'success' | 'danger' | 'muted'
  icon?: React.ReactNode
}

const styles = {
  accent: {
    bg: 'bg-accent/10 border-accent/30',
    value: 'text-accent',
    icon: 'text-accent',
  },
  success: {
    bg: 'bg-success/10 border-success/30',
    value: 'text-success',
    icon: 'text-success',
  },
  danger: {
    bg: 'bg-danger/10 border-danger/30',
    value: 'text-danger',
    icon: 'text-danger',
  },
  muted: {
    bg: 'bg-white/5 border-border',
    value: 'text-text-muted',
    icon: 'text-text-dim',
  },
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}
function AlertIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  )
}
function CameraIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  )
}
function ClockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}

const defaultIcons = {
  accent: <CameraIcon className="w-4 h-4" />,
  success: <CheckIcon className="w-4 h-4" />,
  danger: <AlertIcon className="w-4 h-4" />,
  muted: <ClockIcon className="w-4 h-4" />,
}

export default function StatCard({ label, value, color = 'muted', icon }: StatCardProps) {
  const s = styles[color]
  const iconNode = icon ?? defaultIcons[color]
  return (
    <div
      className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 min-w-0 transition-colors ${s.bg}`}
    >
      <div className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${s.icon} bg-black/20`}>
        {iconNode}
      </div>
      <div className="min-w-0 flex-1">
        <p className={`text-lg sm:text-xl font-bold tabular-nums leading-tight truncate ${s.value}`}>
          {value}
        </p>
        <p className="text-[11px] font-medium text-text-muted uppercase tracking-wider truncate">
          {label}
        </p>
      </div>
    </div>
  )
}
