"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { BookOpen, CheckCircle2, Edit, Flame } from "lucide-react"

import { LoadingSpinner } from "@/components/loading-spinner"
import { ReviewSession } from "@/components/review-session"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useLocale } from "@/i18n/LocaleProvider"
import { resolveLanguage } from "@/i18n/languages"
import { getReviewSession, getUserSettings, type ReviewMode, type ReviewSession as Session } from "@/lib/api"
import type { SessionTally } from "@/lib/review"
import { studiedLanguages } from "@/lib/studied-languages"

type Phase = "loading" | "failed" | "choose" | "session" | "finished"

function languageLabel(code: string) {
  const language = resolveLanguage(code)
  return `${language?.flag || "🌐"} ${language?.name || code.toUpperCase()}`
}

export default function ReviewPage() {
  const { t } = useLocale()
  const [languages, setLanguages] = useState<string[]>([])
  const [language, setLanguage] = useState<string | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [mode, setMode] = useState<ReviewMode>("normal")
  const [phase, setPhase] = useState<Phase>("loading")
  const [tally, setTally] = useState<SessionTally | null>(null)
  // Bumped to start a fresh session for the same language, even when nothing else changed.
  const [round, setRound] = useState(0)

  useEffect(() => {
    getUserSettings()
      .then((settings) => {
        const studied = studiedLanguages(settings)
        const requested = new URLSearchParams(window.location.search).get("language")
        setLanguages(studied)
        setLanguage(requested && studied.includes(requested) ? requested : studied[0])
      })
      .catch(() => setPhase("failed"))
  }, [])

  const load = useCallback(async (code: string, nextMode: ReviewMode, offerCatchup: boolean) => {
    setPhase("loading")
    try {
      const next = await getReviewSession(code, nextMode)
      setSession(next)
      setMode(nextMode)
      setPhase(offerCatchup && next.counts.suggest_catchup ? "choose" : "session")
    } catch {
      setPhase("failed")
    }
  }, [])

  useEffect(() => {
    if (language) void load(language, "normal", true)
  }, [language, round, load])

  const finished = useCallback((result: SessionTally) => {
    setTally(result)
    setPhase("finished")
  }, [])

  const picker = languages.length > 1 && language && (
    <Select value={language} onValueChange={setLanguage}>
      <SelectTrigger className="w-full sm:w-56" aria-label={t("vocabulary.reviewLanguage")}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {languages.map((code) => (
          <SelectItem key={code} value={code}>{languageLabel(code)}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  )

  const counts = session?.counts
  const hasCards = (session?.cards.length ?? 0) > 0

  return (
    <div className="container mx-auto max-w-3xl px-4 py-8">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h1 className="text-4xl font-bold"><span className="fun-heading">{t("vocabulary.reviewTitle")}</span></h1>
          {picker}
        </div>
        <p className="text-lg text-muted-foreground">{t("vocabulary.reviewIntro")}</p>
      </motion.div>

      {phase === "loading" && (
        <div className="flex h-64 items-center justify-center"><LoadingSpinner text={t("vocabulary.reviewLoading")} /></div>
      )}

      {phase === "failed" && (
        <div className="py-12 text-center" role="alert">
          <p className="mb-4 text-muted-foreground">{t("vocabulary.reviewLoadFailed")}</p>
          <Button variant="outline" onClick={() => (language ? void load(language, mode, true) : setRound((n) => n + 1))}>
            {t("vocabulary.reviewRetry")}
          </Button>
        </div>
      )}

      {phase === "choose" && counts && (
        <Card className="rounded-3xl border-fun-yellow/40 bg-fun-yellow/10" data-testid="catchup-offer">
          <CardContent className="space-y-4 p-6">
            <h2 className="text-2xl font-bold">{t("vocabulary.reviewCatchupTitle", { backlog: counts.backlog })}</h2>
            <p className="text-muted-foreground">
              {t("vocabulary.reviewCatchupBody", { budget: session?.settings.catchup_daily_budget })}
            </p>
            <div className="flex flex-wrap gap-3">
              <Button onClick={() => language && void load(language, "catchup", false)}>
                {t("vocabulary.reviewCatchupStart")}
              </Button>
              <Button variant="outline" onClick={() => setPhase("session")}>
                {t("vocabulary.reviewNormalStart")}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {phase === "session" && session && hasCards && (
        <div className="space-y-3">
          {session.mode === "catchup" && session.catchup && (
            <Badge variant="outline" data-testid="catchup-badge">
              {t("vocabulary.reviewCatchupBadge")} ·{" "}
              {t("vocabulary.reviewCatchupProgress", {
                done: session.catchup.done_today,
                budget: session.catchup.daily_budget,
              })}
            </Badge>
          )}
          <ReviewSession key={`${session.language}-${session.mode}-${round}-${session.cards[0].card_id}`} cards={session.cards} onFinished={finished} />
        </div>
      )}

      {phase === "session" && session && !hasCards && (
        <EmptyState session={session} />
      )}

      {phase === "finished" && tally && (
        <Card className="rounded-3xl" data-testid="review-finished">
          <CardContent className="space-y-5 p-8 text-center">
            <CheckCircle2 className="mx-auto h-14 w-14 text-fun-green" />
            <h2 className="text-3xl font-bold">{t("vocabulary.reviewDoneTitle")}</h2>
            <p className="text-lg text-muted-foreground">
              {t("vocabulary.reviewDoneSummary", { reviewed: tally.reviewed, again: tally.again })}
            </p>
            {tally.nowKnown > 0 && (
              <p className="flex items-center justify-center gap-2 font-medium text-fun-green">
                <Flame className="h-5 w-5" /> {t("vocabulary.reviewNowKnown", { count: tally.nowKnown })}
              </p>
            )}
            {session?.mode === "catchup" && counts && (
              <p className="text-sm text-muted-foreground">
                {t("vocabulary.reviewCatchupDone", { backlog: Math.max(0, counts.backlog - tally.reviewed) })}
              </p>
            )}
            <div className="flex flex-wrap justify-center gap-3">
              {session?.mode !== "catchup" && (
                <Button onClick={() => setRound((n) => n + 1)}>{t("vocabulary.reviewMore")}</Button>
              )}
              <Button variant="outline" asChild><Link href="/dashboard">{t("vocabulary.reviewBackToDashboard")}</Link></Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function EmptyState({ session }: { session: Session }) {
  const { t } = useLocale()
  const { counts } = session
  const waitingForTomorrow = counts.new_available > 0 && counts.new_remaining === 0
  const nothingInStudy = counts.new_available === 0 && counts.due === 0
  return (
    <div className="py-12 text-center" data-testid="review-empty">
      <BookOpen className="mx-auto mb-6 h-16 w-16 text-fun-purple/70" />
      <h2 className="text-2xl font-bold">{t("vocabulary.reviewNothingDue")}</h2>
      <p className="mt-3 text-muted-foreground">
        {waitingForTomorrow
          ? t("vocabulary.reviewNewDone")
          : nothingInStudy
            ? t("vocabulary.reviewNoWordsInStudy")
            : t("vocabulary.reviewNothingDueBody")}
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Button asChild variant="outline"><Link href="/vocabulary"><BookOpen className="mr-2 h-4 w-4" />{t("vocabulary.reviewGoVocabulary")}</Link></Button>
        <Button asChild className="rounded-full"><Link href="/entries/new"><Edit className="mr-2 h-4 w-4" />{t("vocabulary.reviewWriteEntry")}</Link></Button>
      </div>
    </div>
  )
}
