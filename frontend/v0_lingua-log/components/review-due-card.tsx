"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Repeat } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useLocale } from "@/i18n/LocaleProvider"
import { resolveLanguage } from "@/i18n/languages"
import { getReviewSummary, type ReviewSummary } from "@/lib/api"

/** "N due" for the dashboard: reviews waiting plus the new words still allowed today. */
export function ReviewDueCard() {
  const { t } = useLocale()
  const [summary, setSummary] = useState<ReviewSummary | null>(null)

  useEffect(() => {
    getReviewSummary().then(setSummary).catch(() => setSummary(null))
  }, [])

  if (!summary) return null

  const waiting = summary.languages.filter((row) => row.total > 0)
  const first = waiting[0]?.language

  return (
    <section
      className="mb-8 flex flex-col gap-4 rounded-3xl border border-fun-yellow/30 bg-fun-yellow/10 p-5 sm:flex-row sm:items-center sm:justify-between"
      data-testid="review-due-card"
    >
      <div>
        <h2 className="flex items-center gap-2 text-lg font-bold">
          <Repeat className="h-5 w-5" /> {t("vocabulary.reviewDueCard")}
        </h2>
        {summary.total > 0 ? (
          <>
            <p className="text-3xl font-bold" data-testid="review-due-count">
              {t("vocabulary.reviewDueCount", { count: summary.total })}
              {summary.new > 0 && (
                <span className="ml-3 align-middle text-base font-medium text-muted-foreground" data-testid="review-new-count">
                  {t("vocabulary.reviewNewCount", { count: summary.new })}
                </span>
              )}
            </p>
            <p className="mt-1 flex flex-wrap gap-x-4 text-sm text-muted-foreground">
              {waiting.length > 1 &&
                waiting.map((row) => (
                  <span key={row.language}>
                    {resolveLanguage(row.language)?.flag} {row.total}
                  </span>
                ))}
              {summary.at_risk > 0 && (
                <span className="flex items-center gap-1 text-red-600">
                  <span className="inline-block h-2 w-2 rounded-full bg-red-500" aria-hidden />
                  {t("vocabulary.reviewAtRiskCount", { count: summary.at_risk })}
                </span>
              )}
            </p>
          </>
        ) : (
          <p className="text-xl font-semibold text-muted-foreground" data-testid="review-all-clear">
            {t("vocabulary.reviewAllClear")}
          </p>
        )}
      </div>
      {summary.total > 0 && (
        <Button asChild size="lg">
          <Link href={first ? `/review?language=${encodeURIComponent(first)}` : "/review"}>
            {t("vocabulary.reviewStartReview")}
          </Link>
        </Button>
      )}
    </section>
  )
}
