"use client"

import { Check, CircleHelp, Minus, Wrench } from "lucide-react"

import { useLocale } from "@/i18n/LocaleProvider"
import type { FocusUse, TargetWordStatus } from "@/lib/side-by-side"
import { cn } from "@/lib/utils"

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

export function FocusUseRow({ uses, language }: { uses: FocusUse[]; language: string }) {
  const { t } = useLocale()
  if (!uses.length) return null

  return (
    <section
      className="rounded-3xl border border-fun-blue/25 bg-fun-blue/5 p-4 shadow-fun"
      data-testid="focus-use"
      aria-label={t("feedback.focusTodayTitle")}
    >
      <h2 className="text-lg font-bold">{t("feedback.focusTodayTitle")}</h2>
      <ul className="mt-3 space-y-2">
        {uses.map((use, index) => (
          <li
            key={`${use.focus}-${index}`}
            data-testid="focus-use-item"
            data-status={use.status}
            className={cn("rounded-2xl border p-3", TONE[use.status])}
          >
            <div className="flex flex-wrap items-center gap-2">
              <StatusIcon status={use.status} />
              <span lang={language} className="font-semibold">{use.focus}</span>
              <span className="text-xs font-bold text-muted-foreground">
                {t(`feedback.focusUse_${use.status}`)}
              </span>
            </div>
            {use.status === "used_correctly" && use.evidence && (
              <p lang={language} className="mt-2 font-serif italic">{use.evidence}</p>
            )}
            {use.status === "used_with_error" && (
              <div className="mt-2 space-y-1 text-sm">
                {use.evidence && <p lang={language}><span className="text-muted-foreground line-through">{use.evidence}</span>{use.fix && <span className="font-semibold"> → {use.fix}</span>}</p>}
                {use.note && <p>{use.note}</p>}
              </div>
            )}
            {use.status === "unclear" && use.note && <p className="mt-2 text-sm">{use.note}</p>}
            {use.status === "not_used" && <p className="mt-2 text-sm text-muted-foreground">{t("feedback.focusUseNotUsed")}</p>}
          </li>
        ))}
      </ul>
    </section>
  )
}
