import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import PageHeader from '../components/PageHeader'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

type ZoneInfo = {
  zone_id: number
  name: string
  cameras: number[]
  total_violations: number
}

type ByTimeRow = {
  zone_id: number
  zone_name: string
  date: string
  count: number
}

type HeatmapApi = {
  zones: ZoneInfo[]
  by_time: ByTimeRow[]
  period_days: number
}

type TrendsApi = {
  labels: string[]
  violations: number[]
  compliance_rate: number[]
  granularity: string
  period_days: number
}

export default function Analytics() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [heatmapPeriod, setHeatmapPeriod] = useState(7)
  const [trendsGranularity, setTrendsGranularity] = useState<'hour' | 'day' | 'week'>('day')
  const [trendsPeriod, setTrendsPeriod] = useState(7)
  const [heatmap, setHeatmap] = useState<HeatmapApi | null>(null)
  const [trends, setTrends] = useState<TrendsApi | null>(null)
  const [loadingHeatmap, setLoadingHeatmap] = useState(true)
  const [loadingTrends, setLoadingTrends] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    setLoadingHeatmap(true)
    setError(null)
    fetch(`/api/analytics/heatmap?user_id=${user.id}&period=${heatmapPeriod}`)
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load heatmap')
        return r.json()
      })
      .then(setHeatmap)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingHeatmap(false))
  }, [user?.id, heatmapPeriod])

  useEffect(() => {
    if (!user) return
    setLoadingTrends(true)
    fetch(`/api/analytics/trends?user_id=${user.id}&granularity=${trendsGranularity}&period=${trendsPeriod}`)
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load trends')
        return r.json()
      })
      .then(setTrends)
      .catch(() => setTrends(null))
      .finally(() => setLoadingTrends(false))
  }, [user?.id, trendsGranularity, trendsPeriod])

  const heatmapGrid = useMemo(() => {
    if (!heatmap?.zones.length) return null
    const datesFromData = [...new Set(heatmap.by_time.map((r) => r.date))].sort()
    const dates =
      datesFromData.length > 0
        ? datesFromData
        : heatmap.period_days === 0
          ? [new Date().toISOString().slice(0, 10)]
          : []
    if (dates.length === 0 && heatmap.period_days !== 0) return null
    const countMap = new Map<string, number>()
    heatmap.by_time.forEach((r) => {
      countMap.set(`${r.zone_id}-${r.date}`, r.count)
    })
    const maxCount = Math.max(1, ...heatmap.by_time.map((r) => r.count))
    return {
      zones: heatmap.zones,
      dates,
      getCount: (zoneId: number, date: string) => countMap.get(`${zoneId}-${date}`) ?? 0,
      maxCount,
    }
  }, [heatmap])

  const trendsChartData = useMemo(() => {
    if (!trends?.labels.length) return []
    return trends.labels.map((label, i) => ({
      label: trends.granularity === 'hour' ? label.slice(0, 16) : label,
      violations: trends.violations[i] ?? 0,
      compliance: trends.compliance_rate[i] ?? 100,
    }))
  }, [trends])

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-surface">
      <PageHeader
        title="Analytics"
        subtitle="Violation heatmaps and trend charts"
        showBack
        onBack={() => navigate('/')}
      />

      <div className="flex-1 overflow-auto p-3 sm:p-6">
        <div className="max-w-6xl mx-auto space-y-8">
          {error && (
            <div className="bg-danger/10 border border-danger/30 text-danger px-4 py-3 rounded text-sm">
              {error}
            </div>
          )}

          {/* Violation heatmap */}
          <section>
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <h2 className="text-sm font-semibold text-accent uppercase tracking-wider">
                Violation heatmap by zone
              </h2>
              <label className="flex items-center gap-2 text-xs text-text-muted">
                Period:
                <select
                  value={heatmapPeriod}
                  onChange={(e) => setHeatmapPeriod(Number(e.target.value))}
                  className="bg-card border border-border rounded px-2 py-1.5 text-white text-xs focus:outline-none focus:ring-1 focus:ring-accent"
                >
                  <option value={0}>Today</option>
                  <option value={7}>Last 7 days</option>
                  <option value={14}>Last 14 days</option>
                  <option value={30}>Last 30 days</option>
                </select>
              </label>
            </div>
            <div className="bg-card border border-border rounded-lg p-4 overflow-x-auto">
              {loadingHeatmap ? (
                <p className="text-text-muted text-sm py-8 text-center">Loading heatmap...</p>
              ) : !heatmapGrid ? (
                <p className="text-text-muted text-sm py-8 text-center">
                  No violation data in this period. Heatmap shows which zones had the most violations per day.
                </p>
              ) : (
                <div className="min-w-[400px]">
                  <div className="grid gap-px mb-2" style={{ gridTemplateColumns: `120px repeat(${heatmapGrid.dates.length}, minmax(32px, 1fr))` }}>
                    <div className="text-xs text-text-muted font-medium py-1.5">Zone / Date</div>
                    {heatmapGrid.dates.map((d) => (
                      <div key={d} className="text-xs text-text-muted text-center py-1.5 truncate" title={d}>
                        {d.slice(5)}
                      </div>
                    ))}
                  </div>
                  {heatmapGrid.zones.map((zone) => (
                    <div
                      key={zone.zone_id}
                      className="grid gap-px border-t border-border/50 first:border-t-0"
                      style={{ gridTemplateColumns: `120px repeat(${heatmapGrid.dates.length}, minmax(32px, 1fr))` }}
                    >
                      <div className="text-xs text-white py-2 truncate pr-2" title={zone.name}>
                        {zone.name}
                      </div>
                      {heatmapGrid.dates.map((date) => {
                        const count = heatmapGrid.getCount(zone.zone_id, date)
                        const intensity = heatmapGrid.maxCount > 0 ? count / heatmapGrid.maxCount : 0
                        const bg = intensity === 0
                          ? 'bg-surface'
                          : `rgba(239, 68, 68, ${0.2 + 0.8 * intensity})`
                        return (
                          <div
                            key={date}
                            className="h-8 flex items-center justify-center text-xs"
                            style={{ backgroundColor: bg }}
                            title={`${date}: ${count} violation(s)`}
                          >
                            {count > 0 ? count : ''}
                          </div>
                        )
                      })}
                    </div>
                  ))}
                  <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border text-xs text-text-muted">
                    <span>Low</span>
                    <div className="flex-1 h-3 flex gap-0.5 rounded overflow-hidden">
                      {[0, 0.25, 0.5, 0.75, 1].map((v) => (
                        <div
                          key={v}
                          className="flex-1"
                          style={{ backgroundColor: `rgba(239, 68, 68, ${0.2 + 0.8 * v})` }}
                        />
                      ))}
                    </div>
                    <span>High</span>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Trend charts */}
          <section>
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <h2 className="text-sm font-semibold text-accent uppercase tracking-wider">
                Violations over time
              </h2>
              <div className="flex flex-wrap items-center gap-3 text-xs">
                <label className="flex items-center gap-2 text-text-muted">
                  Granularity:
                  <select
                    value={trendsGranularity}
                    onChange={(e) => setTrendsGranularity(e.target.value as 'hour' | 'day' | 'week')}
                    className="bg-card border border-border rounded px-2 py-1.5 text-white focus:outline-none focus:ring-1 focus:ring-accent"
                  >
                    <option value="hour">Per hour</option>
                    <option value="day">Per day</option>
                    <option value="week">Per week</option>
                  </select>
                </label>
                <label className="flex items-center gap-2 text-text-muted">
                  Period:
                  <select
                    value={trendsPeriod}
                    onChange={(e) => setTrendsPeriod(Number(e.target.value))}
                    className="bg-card border border-border rounded px-2 py-1.5 text-white focus:outline-none focus:ring-1 focus:ring-accent"
                  >
                    <option value={0}>Today</option>
                    <option value={7}>7 days</option>
                    <option value={14}>14 days</option>
                    <option value={30}>30 days</option>
                  </select>
                </label>
              </div>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              {loadingTrends ? (
                <p className="text-text-muted text-sm py-8 text-center">Loading trends...</p>
              ) : trendsChartData.length === 0 ? (
                <p className="text-text-muted text-sm py-8 text-center">
                  No violation data for this period.
                </p>
              ) : (
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trendsChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <XAxis dataKey="label" stroke="#9ca3af" fontSize={11} tick={{ fill: '#9ca3af' }} />
                      <YAxis yAxisId="left" stroke="#9ca3af" fontSize={11} tick={{ fill: '#9ca3af' }} />
                      <YAxis yAxisId="right" orientation="right" stroke="#6ee7b7" fontSize={11} tick={{ fill: '#6ee7b7' }} domain={[0, 100]} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                        labelStyle={{ color: '#d1d5db' }}
                        formatter={(value: unknown, name?: unknown) => {
                          const v = typeof value === 'number' && !Number.isNaN(value) ? value : 0
                          const label = name === 'violations' ? 'Violations' : 'Compliance'
                          return [name === 'violations' ? v : `${v.toFixed(0)}%`, label]
                        }}
                      />
                      <Legend />
                      <Line yAxisId="left" type="monotone" dataKey="violations" name="Violations" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
                      <Line yAxisId="right" type="monotone" dataKey="compliance" name="Compliance %" stroke="#6ee7b7" strokeWidth={2} dot={{ r: 3 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </section>

          {/* Bar chart: violations per bucket */}
          <section>
            <h2 className="text-sm font-semibold text-accent uppercase tracking-wider mb-4">
              Violations per period (bar)
            </h2>
            <div className="bg-card border border-border rounded-lg p-4">
              {loadingTrends || trendsChartData.length === 0 ? (
                <p className="text-text-muted text-sm py-8 text-center">
                  {loadingTrends ? 'Loading...' : 'No data for this period.'}
                </p>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={trendsChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <XAxis dataKey="label" stroke="#9ca3af" fontSize={11} tick={{ fill: '#9ca3af' }} />
                      <YAxis stroke="#9ca3af" fontSize={11} tick={{ fill: '#9ca3af' }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                        formatter={(value: unknown) => [typeof value === 'number' ? value : 0, 'Violations']}
                      />
                      <Bar dataKey="violations" name="Violations" fill="#ef4444" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
