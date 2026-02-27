type StatCardProps = {
  label: string
  value: string
  color?: 'accent' | 'success' | 'danger' | 'muted'
}

const dotClass = {
  accent: 'bg-accent',
  success: 'bg-success',
  danger: 'bg-danger',
  muted: 'bg-text-dim',
}

const valueClass = {
  accent: 'text-accent',
  success: 'text-success',
  danger: 'text-danger',
  muted: 'text-text-muted',
}

export default function StatCard({ label, value, color = 'muted' }: StatCardProps) {
  return (
    <div className="flex items-center gap-2.5 rounded-lg bg-card/60 border border-border px-3 py-1.5">
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotClass[color]}`} />
      <span className={`text-base font-semibold tabular-nums leading-tight ${valueClass[color]}`}>{value}</span>
      <span className="text-[11px] text-text-dim uppercase tracking-wide truncate">{label}</span>
    </div>
  )
}
