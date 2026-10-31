"use client"

/**
 * WordsTodayRow
 *
 * The result of writing with the word bank: how many of today's words were used well, which
 * need a fix, which were not used, and any use the tutor wants to ask about. An unclear use is
 * a question to the learner, never marked wrong.
 */

import { Check, CircleHelp, Minus, PenLine, Wrench } from "lucide-react"

import { useLocale } from "@/i18n/LocaleProvider"
import { cn } from "@/lib/utils"
import type { TargetWordStatus, TargetWordUse } from "@/lib/side-by-side"

/** Days of correct use, in the learner's own entries, a Known word needs to become Mastered. */
const DAYS_TO_MASTER = 2

const SUMMARY_ORDER: Array<{ status: TargetWordStatus; key: string }> = [
  { status: "used_correctly", key: "feedback.wordsTodayUsedWell" },
  { status: "used_with_error", key: "feedback.wordsTodayToFix" },
  { status: "unclear", key: "feedback.wordsTodayToCheck" },
  { status: "not_used", key: "feedback.wordsTodayNotUsed" },
]

const TONE: Record<TargetWordStatus, string> = {
  used_correctly: "border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-950/30",
  used_with_error: "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/30",
  unclear: "border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-950/30",
  not_used: "border-border bg-background",
}

function StatusIcon({ status }: { status: TargetWordStatus }) {
  const className = "h-4 w-4 shrink-0"
  if (status === "used_correctly") return <Check className={cn(className, "text-green-600")} aria-hidden />
  if (status === "used_with_error") return <Wrench className={cn(className, "text-amber-600")} aria-hidden />
  if (status === "unclear") return <CircleHelp className={cn(className, "text-blue-600")} aria-hidden />
  return <Minus className={cn(className, "text-muted-foreground")} aria-hidden />
}

export function WordsTodayRow({ uses, l2, l2Dir }: { uses: TargetWordUse[]; l2: string; l2Dir: "rtl" | "ltr" }) {
  const { t } = useLocale()
  if (uses.length === 0) return null

  const counts = new Map<TargetWordStatus, number>()
  for (const use of uses) counts.set(use.status, (counts.get(use.status) ?? 0) + 1)

  return (
    <section
      className="rounded-3xl border border-fun-yellow/40 bg-fun-yellow/10 p-4 shadow-fun"
      data-testid="words-today"
      aria-label={t("feedback.wordsTodayTitle")}
    >
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-lg font-bold">{t("feedback.wordsTodayTitle")}</h2>
        <p className="text-sm font-semibold" data-testid="words-today-summary">
          {SUMMARY_ORDER.filter(({ status }) => counts.get(status))
            .map(({ status, key }) => t(key, { count: counts.get(status) }))
            .join(" · ")}
        </p>
      </div>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {uses.map((use) => {
          const needsDays =
            use.status === "used_correctly" &&
            use.word_status === "known" &&
            !use.became_mastered &&
            typeof use.use_days === "number" &&
            use.use_days < DAYS_TO_MASTER
          return (
            <li
              key={use.word_id}
              data-testid="word-use"
              data-status={use.status}
              className={cn("min-w-0 rounded-2xl border p-3 text-sm", TONE[use.status])}
            >
              <p className="flex items-center gap-2">
                <StatusIcon status={use.status} />
                <span lang={l2} dir={l2Dir} className="truncate font-serif text-base font-bold">
                  {use.term}
                </span>
                <span className="sr-only">{t(`feedback.wordUse_${use.status}`)}</span>
              </p>
              {use.form_in_text && use.status !== "used_with_error" && (
                <p lang={l2} dir={l2Dir} className="mt-1 font-serif italic text-muted-foreground">
                  {use.form_in_text}
                </p>
              )}
              {use.status === "used_with_error" && (
                <div className="mt-1 space-y-1">
                  <p lang={l2} dir={l2Dir} className="font-serif">
                    <span className="text-muted-foreground line-through">{use.form_in_text}</span>
                    {use.fix && <span className="font-semibold"> → {use.fix}</span>}
                  </p>
                  {use.note && <p>{use.note}</p>}
                </div>
              )}
              {use.status === "unclear" && (
                <div className="mt-1 space-y-1">
                  {use.note && <p className="font-semibold">{use.note}</p>}
                  <p className="text-muted-foreground">{t("feedback.wordUseUnclearHint")}</p>
                </div>
              )}
              {use.status === "not_used" && (
                <p className="mt-1 text-muted-foreground">{t("feedback.wordUseNotUsed")}</p>
              )}
              {use.became_mastered && (
                <p className="mt-2 flex items-center gap-1 font-bold text-green-700 dark:text-green-300" data-testid="word-mastered">
                  <PenLine className="h-4 w-4" aria-hidden />
                  {t("feedback.wordUseMastered")}
                </p>
              )}
              {needsDays && (
                <p className="mt-2 text-xs text-muted-foreground">
                  {t("feedback.wordUseMasteryProgress", { days: use.use_days, total: DAYS_TO_MASTER })}
                </p>
              )}
              {use.credited && <p className="mt-1 text-xs text-muted-foreground">{t("feedback.wordUseCredited")}</p>}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
