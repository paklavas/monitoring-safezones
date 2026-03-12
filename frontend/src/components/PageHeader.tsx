import { useState, useEffect } from 'react'

type PageHeaderProps = {
  title: string
  subtitle?: string
  showBack?: boolean
  onBack?: () => void
  showTime?: boolean
}

export default function PageHeader({ title, subtitle, showBack, onBack, showTime = true }: PageHeaderProps) {
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="shrink-0 border-b border-border bg-surface/95 px-4 sm:px-6 py-3">
      <div className="flex items-center justify-between gap-3 min-w-0">
        <div className="flex items-center gap-3 min-w-0">
          {showBack && onBack && (
            <button
              onClick={onBack}
              className="text-text-muted hover:text-white transition-colors text-sm shrink-0"
            >
              ← Back
            </button>
          )}
          <div className="min-w-0">
            <h1 className="text-sm sm:text-base font-semibold text-white truncate">{title}</h1>
            {subtitle && (
              <p className="text-xs text-text-muted truncate hidden sm:block">{subtitle}</p>
            )}
          </div>
        </div>
        {showTime && (
          <p className="text-xs text-text-muted tabular-nums shrink-0" title={now.toLocaleString()}>
            {now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </p>
        )}
      </div>
    </div>
  )
}
