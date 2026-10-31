"use client"

import { useEffect, useMemo, useState } from "react"
import {
  Activity,
  BookOpen,
  Languages,
  PenLine,
  Sparkles,
  TrendingUp,
  Trophy,
  Type,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { PlacementCheck } from "@/components/placement-check"
import { WritingAnimation } from "@/components/writing-animation"
import { useLocale } from "@/i18n/LocaleProvider"
import { resolveLanguage } from "@/i18n/languages"
import {
  getUserSettings,
  getUserStats,
  getVocabularyProgress,
  type PlacementResult,
  type UserStats,
  type VocabularyProgress,
} from "@/lib/api"
import { studiedLanguages } from "@/lib/studied-languages"

const ALL = "all"

function languageLabel(code: string) {
  const language = resolveLanguage(code)
  return `${language?.flag || "🌐"} ${language?.name || code.toUpperCase()}`
}

function Bars({ data, color }: { data: Array<{ label: string; value: number }>; color: string }) {
  const max = Math.max(1, ...data.map((row) => row.value))
  return (
    <div className="flex h-32 items-end gap-1">
      {data.map((row) => (
        <div key={row.label} className="group flex flex-1 flex-col items-center">
          <div
            className="w-full rounded-t-md transition-all duration-300"
            style={{ height: `${Math.max(2, (row.value / max) * 100)}%`, background: color }}
            title={`${row.label}: ${row.value}`}
          />
          <span className="mt-1 text-[10px] text-muted-foreground">{row.label}</span>
        </div>
      ))}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border bg-card p-3 text-center">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  )
}

export default function StatsPage() {
  const { t, intl } = useLocale()
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<UserStats | null>(null)
  const [progress, setProgress] = useState<VocabularyProgress | null>(null)
  const [languages, setLanguages] = useState<string[]>([])
  const [language, setLanguage] = useState<string>(ALL)
  const [placementOpen, setPlacementOpen] = useState(false)

  useEffect(() => {
    Promise.all([getUserStats(), getUserSettings()])
      .then(([userStats, settings]) => {
        setStats(userStats)
        setLanguages(studiedLanguages(settings))
      })
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    let cancelled = false
    getVocabularyProgress(language === ALL ? undefined : language)
      .then((result) => {
        if (!cancelled) setProgress(result)
      })
      .catch(() => {
        if (!cancelled) setProgress(null)
      })
    return () => {
      cancelled = true
    }
  }, [language])

  useEffect(() => {
    const wanted = new URLSearchParams(window.location.search).get("placement")
    if (wanted && languages.includes(wanted)) {
      setLanguage(wanted)
      setPlacementOpen(true)
    }
  }, [languages])

  const wordCounts = useMemo(
    () =>
      (stats?.wordCounts ?? []).map((row) => ({
        label: new Date(row.date).toLocaleDateString(undefined, { weekday: "short" }),
        value: row.count,
      })),
    [stats],
  )

  const forecast = useMemo(
    () =>
      (progress?.review.forecast ?? []).map((row) => ({
        label: new Date(row.date).toLocaleDateString(undefined, { weekday: "short" }),
        value: row.count,
      })),
    [progress],
  )

  const trend = useMemo(
    () => (progress?.trend ?? []).map((row) => ({ label: row.date.slice(5), value: row.count })),
    [progress],
  )

  const encounterRows = useMemo(() => {
    const kinds = progress?.encounters.by_kind ?? {}
    return Object.entries(kinds)
      .filter(([, count]) => count > 0)
      .sort((a, b) => b[1] - a[1])
  }, [progress])

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">
          <span className="fun-heading">{t("common.yourLearningStats")} 📊</span>
        </h2>
        <p className="mt-2 text-lg text-muted-foreground">{t("common.trackLanguageProgress")}</p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Select value={language} onValueChange={setLanguage}>
          <SelectTrigger className="h-11 w-full sm:w-64">
            <Languages className="mr-2 h-5 w-5 text-muted-foreground" />
            <SelectValue placeholder={t("vocabulary.filterByLanguage")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>{t("vocabulary.allLanguages")}</SelectItem>
            {languages.map((code) => (
              <SelectItem value={code} key={code}>
                {languageLabel(code)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <WritingAnimation text={t("common.calculatingProgress")} />
        </div>
      ) : (
        <>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <Card className="fun-card border-fun-green/30">
              <CardHeader>
                <CardTitle className="flex items-center text-xl">
                  <TrendingUp className="mr-2 h-5 w-5 text-fun-green" />
                  {t("vocabulary.wordsWrittenTitle")}
                </CardTitle>
                <CardDescription>{t("vocabulary.wordsWrittenDesc")}</CardDescription>
              </CardHeader>
              <CardContent>
                {wordCounts.length ? (
                  <Bars data={wordCounts} color="linear-gradient(to top, hsl(var(--fun-green)), hsl(var(--fun-blue)))" />
                ) : (
                  <p className="py-10 text-center text-sm text-muted-foreground">{t("vocabulary.wordsWrittenEmpty")}</p>
                )}
              </CardContent>
            </Card>

            <Card className="fun-card border-fun-blue/30">
              <CardHeader>
                <CardTitle className="flex items-center text-xl">
                  <Languages className="mr-2 h-5 w-5 text-fun-blue" />
                  {t("common.languages")}
                </CardTitle>
                <CardDescription>{t("common.breakdownLanguagesPracticed")}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {(stats?.languageBreakdown ?? []).map((row) => (
                  <div key={row.language} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline">{languageLabel(row.language)}</Badge>
                      <span className="text-sm text-muted-foreground">
                        {row.count} {t("common.words")} · {Math.round(row.percentage)}%
                      </span>
                    </div>
                    <div className="h-2.5 w-full rounded-full bg-fun-blue/10">
                      <div
                        className="h-2.5 rounded-full bg-gradient-to-r from-fun-blue to-fun-teal"
                        style={{ width: `${row.percentage}%` }}
                      />
                    </div>
                  </div>
                ))}
                {!(stats?.languageBreakdown ?? []).length && (
                  <p className="py-6 text-center text-sm text-muted-foreground">{t("vocabulary.wordsWrittenEmpty")}</p>
                )}
              </CardContent>
            </Card>

            <Card className="fun-card border-fun-purple/30">
              <CardHeader>
                <CardTitle className="flex items-center text-xl">
                  <Trophy className="mr-2 h-5 w-5 text-fun-purple" />
                  {t("common.writingStreak")}
                </CardTitle>
                <CardDescription>{t("common.consistentWritingProgress")}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col items-center justify-center gap-4 py-4 text-center">
                  <div className="streak-counter rounded-full p-2">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white text-4xl font-bold">
                      {stats?.streak.current ?? 0}
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">{t("vocabulary.streakDays")}</div>
                  {(stats?.streak.current ?? 0) > 5 && (
                    <div className="rounded-full border-2 border-fun-purple/30 bg-gradient-to-r from-fun-purple/20 to-fun-pink/20 px-6 py-2 text-sm font-medium">
                      <Sparkles className="mr-2 inline h-4 w-4 text-fun-yellow" />
                      {t("vocabulary.streakFire")}
                    </div>
                  )}
                  <div className="grid w-full grid-cols-2 gap-4">
                    <Stat label={t("common.longestStreak")} value={stats?.streak.longest ?? 0} />
                    <Stat label={t("common.totalWords")} value={stats?.streak.totalWords ?? 0} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div>
            <h3 className="mb-4 text-2xl font-bold tracking-tight">
              <span className="fun-heading">{t("vocabulary.progressHeading")}</span>
            </h3>
            {progress ? (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                <Card className="fun-card border-fun-pink/30">
                  <CardHeader>
                    <CardTitle className="flex items-center text-xl">
                      <BookOpen className="mr-2 h-5 w-5 text-fun-pink" />
                      {t("vocabulary.notebookTitle")}
                    </CardTitle>
                    <CardDescription>{t("vocabulary.notebookDesc")}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <Stat label={t("vocabulary.status_new")} value={progress.notebook.new} />
                      <Stat label={t("vocabulary.status_learning")} value={progress.notebook.learning} />
                      <Stat label={t("vocabulary.status_known")} value={progress.notebook.known} />
                      <Stat label={t("vocabulary.status_mastered")} value={progress.notebook.mastered} />
                    </div>
                    <div>
                      <p className="mb-2 text-xs font-medium text-muted-foreground">{t("vocabulary.trend30")}</p>
                      <Bars data={trend} color="linear-gradient(to top, hsl(var(--fun-pink)), hsl(var(--fun-purple)))" />
                    </div>
                  </CardContent>
                </Card>

                <Card className="fun-card border-fun-yellow/30">
                  <CardHeader>
                    <CardTitle className="flex items-center text-xl">
                      <PenLine className="mr-2 h-5 w-5 text-fun-yellow" />
                      {t("vocabulary.activeWordsTitle")}
                    </CardTitle>
                    <CardDescription>{t("vocabulary.activeWordsDesc")}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Stat label={t("vocabulary.activeWordsTitle")} value={progress.active_words} />
                    <div>
                      <p className="mb-2 text-xs font-medium text-muted-foreground">
                        {t("vocabulary.encountersTitle")}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {t("vocabulary.encountersPerWord", {
                          count: progress.encounters.per_word,
                          min: progress.encounters.guide_min,
                          max: progress.encounters.guide_max,
                        })}
                      </p>
                      <div className="mt-3 space-y-1.5">
                        {encounterRows.map(([kind, count]) => (
                          <div key={kind} className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">{t(`vocabulary.kind_${kind}`)}</span>
                            <span className="font-medium">{count}</span>
                          </div>
                        ))}
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">{t("vocabulary.kind_reviews")}</span>
                          <span className="font-medium">{progress.encounters.reviews}</span>
                        </div>
                        {!encounterRows.length && (
                          <p className="text-xs text-muted-foreground">{t("vocabulary.encountersEmpty")}</p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="fun-card border-fun-teal/30">
                  <CardHeader>
                    <CardTitle className="flex items-center text-xl">
                      <Activity className="mr-2 h-5 w-5 text-fun-teal" />
                      {t("vocabulary.reviewHealthTitle")}
                    </CardTitle>
                    <CardDescription>{t("vocabulary.reviewHealthDesc")}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <Stat label={t("vocabulary.dueToday")} value={progress.review.due_today} />
                      <Stat
                        label={t("vocabulary.trueRetention")}
                        value={
                          progress.review.true_retention === null
                            ? "—"
                            : `${Math.round(progress.review.true_retention * 100)}%`
                        }
                      />
                    </div>
                    <Bars data={forecast} color="linear-gradient(to top, hsl(var(--fun-teal)), hsl(var(--fun-blue)))" />
                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                      <span>{t("vocabulary.reviewsLast7", { count: progress.review.reviews_last_7_days })}</span>
                      <span>{t("vocabulary.minutesLast7", { minutes: progress.review.minutes_last_7_days })}</span>
                      {progress.review.at_risk > 0 && (
                        <span className="inline-flex items-center gap-1 font-medium text-red-600">
                          <span className="inline-block h-2 w-2 rounded-full bg-red-500" aria-hidden />
                          {t("vocabulary.reviewAtRiskCount", { count: progress.review.at_risk })}
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card className="fun-card border-fun-orange/30">
                  <CardHeader>
                    <CardTitle className="flex items-center text-xl">
                      <Type className="mr-2 h-5 w-5 text-fun-orange" />
                      {t("vocabulary.weekTitle")}
                    </CardTitle>
                    <CardDescription>{t("vocabulary.weekDesc")}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-3 gap-3">
                      <Stat label={t("vocabulary.weekReading")} value={progress.week.reading} />
                      <Stat label={t("vocabulary.weekJournal")} value={progress.week.journal} />
                      <Stat label={t("vocabulary.weekReviews")} value={progress.week.reviews} />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {t("vocabulary.minutesLast7", { minutes: progress.week.review_minutes })}
                    </p>
                    {progress.week.over_budget && (
                      <p className="rounded-xl bg-fun-orange/10 p-3 text-sm">{t("vocabulary.weekNote")}</p>
                    )}
                  </CardContent>
                </Card>

                <Card className="fun-card border-fun-purple/30">
                  <CardHeader>
                    <CardTitle className="flex items-center text-xl">
                      <Sparkles className="mr-2 h-5 w-5 text-fun-purple" />
                      {t("vocabulary.placementTitle")}
                    </CardTitle>
                    <CardDescription>{t("vocabulary.placementEstimateHint")}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {progress.placement ? (
                      <>
                        <Stat
                          label={t("vocabulary.placementEstimateLabel")}
                          value={intl.formatNumber(Number(progress.placement.estimate))}
                        />
                        <Button onClick={() => setPlacementOpen(true)} variant="outline" className="w-full">
                          {t("vocabulary.placementRetake")}
                        </Button>
                      </>
                    ) : progress.placement_available ? (
                      <Button onClick={() => setPlacementOpen(true)} className="w-full">
                        {t("vocabulary.placementTake")}
                      </Button>
                    ) : (
                      <p className="py-6 text-center text-sm text-muted-foreground">
                        {language === ALL
                          ? t("vocabulary.placementPickLanguage")
                          : t("vocabulary.placementUnavailable")}
                      </p>
                    )}
                  </CardContent>
                </Card>
              </div>
            ) : (
              <p className="py-10 text-center text-sm text-muted-foreground">{t("vocabulary.progressFailed")}</p>
            )}
          </div>
        </>
      )}

      {language !== ALL && (
        <PlacementCheck
          language={language}
          open={placementOpen}
          onOpenChange={setPlacementOpen}
          onResult={(result: PlacementResult) => setProgress((current) => (current ? { ...current, placement: result } : current))}
        />
      )}
    </div>
  )
}
