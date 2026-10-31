"use client"

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { Badge } from "@/components/ui/badge"
import { useLocale } from "@/i18n/LocaleProvider"
import type { BookProgress, CoverageBand } from "@/lib/api"
import { BAND_CLASS, BAND_COLOR, BAND_EDGES } from "@/lib/books"

const BAND_FILL: Array<{ from: number; to: number; band: CoverageBand }> = [
  { from: 0, to: BAND_EDGES.comfortable, band: "comfortable" },
  { from: BAND_EDGES.comfortable, to: BAND_EDGES.study, band: "study" },
  { from: BAND_EDGES.study, to: BAND_EDGES.hard, band: "demanding" },
]
const RECENT_PAGES = 40

/** Words marked per page, session by session: the line that should fall as the pages get easier. */
export function WordsPerPageChart({ progress }: { progress: BookProgress }) {
  const { t } = useLocale()
  const sessions = progress.sessions
    .map((session, index) => ({ n: index + 1, rate: session.words_per_page, marked: session.words_marked, pages: session.pages_read }))
    .filter((point) => point.rate !== null)
  const pages = progress.pages.slice(-RECENT_PAGES)
  const top = Math.max(BAND_EDGES.hard + 5, ...sessions.map((point) => point.rate ?? 0))

  if (sessions.length === 0) {
    return <p className="text-sm text-muted-foreground" data-testid="chart-empty">{t("books.chartEmpty")}</p>
  }

  return (
    <div className="space-y-6" data-testid="words-per-page-chart">
      <div className="flex flex-wrap items-center gap-2">
        {progress.trend === "falling" && (
          <Badge variant="outline" className={BAND_CLASS.comfortable} data-testid="trend-falling">{t("books.trendFalling")}</Badge>
        )}
        {progress.trend === "rising" && <Badge variant="outline">{t("books.trendRising")}</Badge>}
        {progress.latest_band && (
          <Badge variant="outline" className={BAND_CLASS[progress.latest_band]}>{t(`books.band_${progress.latest_band}`)}</Badge>
        )}
        <span className="text-xs text-muted-foreground">{t("books.estimateLabel")}</span>
      </div>

      <div>
        <h3 className="mb-2 text-lg font-semibold">{t("books.chartSessions")}</h3>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sessions} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              {BAND_FILL.map((area) => (
                <ReferenceArea key={area.band} y1={area.from} y2={area.to} fill={BAND_COLOR[area.band]} fillOpacity={0.1} ifOverflow="hidden" />
              ))}
              <ReferenceArea y1={BAND_EDGES.hard} y2={top} fill={BAND_COLOR.hard} fillOpacity={0.1} ifOverflow="hidden" />
              <XAxis dataKey="n" tickFormatter={(value) => `#${value}`} />
              <YAxis domain={[0, top]} allowDecimals={false} width={32} />
              <Tooltip formatter={(value: number) => [t("books.perPage", { count: value }), ""]} labelFormatter={(value) => t("books.sessionN", { n: value })} />
              <Line type="monotone" dataKey="rate" stroke="#7c3aed" strokeWidth={3} dot={{ r: 4 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <table className="sr-only" aria-label={t("books.chartSessions")}>
          <tbody>
            {sessions.map((point) => (
              <tr key={point.n}><th scope="row">{t("books.sessionN", { n: point.n })}</th><td>{t("books.perPage", { count: point.rate ?? 0 })}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      {pages.length > 0 && (
        <div>
          <h3 className="mb-2 text-lg font-semibold">{t("books.chartPages")}</h3>
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={pages} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="page" />
                <YAxis allowDecimals={false} width={32} />
                <Tooltip formatter={(value: number) => [t("books.perPage", { count: value }), ""]} labelFormatter={(value) => t("books.pageShort", { page: value })} />
                <Bar dataKey="words" isAnimationActive={false}>
                  {pages.map((page) => (
                    <Cell key={page.page} fill={BAND_COLOR[page.band ?? "comfortable"]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <ul className="flex flex-wrap gap-2 text-xs" aria-label={t("books.bandsTitle")}>
        {(["comfortable", "study", "demanding", "hard"] as const).map((band) => (
          <li key={band}><Badge variant="outline" className={BAND_CLASS[band]}>{t(`books.bandRange_${band}`)}</Badge></li>
        ))}
      </ul>

      {progress.stays_hard && (
        <p className="rounded-xl bg-fun-yellow/15 p-3 text-sm" role="note" data-testid="stays-hard">
          {progress.book.author ? t("books.staysHardAuthor", { author: progress.book.author }) : t("books.staysHard")}
        </p>
      )}
    </div>
  )
}
