"use client"

import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { useLocale } from "@/i18n/LocaleProvider"
import { getUser } from "@/lib/auth"

const STORAGE_PREFIX = "lingualog.book-guide-dismissed"

function storageKey(userId: string | null): string {
  return `${STORAGE_PREFIX}:${userId ?? "anon"}`
}

/** The first-visit 3-step guide on an idle book page; dismissing it is remembered per learner. */
export function BookGuide() {
  const { t } = useLocale()
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    let cancelled = false
    void getUser()
      .then((user) => {
        if (cancelled) return
        try {
          setVisible(!localStorage.getItem(storageKey(user?.id ?? null)))
        } catch {
          setVisible(true)
        }
      })
      .catch(() => {
        if (!cancelled) setVisible(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const dismiss = () => {
    setVisible(false)
    void getUser()
      .then((user) => {
        try {
          localStorage.setItem(storageKey(user?.id ?? null), "1")
        } catch {
          // Storage unavailable: the guide simply shows again next visit.
        }
      })
      .catch(() => {})
  }

  if (!visible) return null

  const steps = [t("books.guideStep1"), t("books.guideStep2"), t("books.guideStep3")]
  return (
    <section className="mb-4 rounded-3xl border border-fun-purple/30 bg-fun-purple/5 p-5" data-testid="book-guide">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-bold">{t("books.guideTitle")}</h2>
        <Button size="sm" variant="outline" onClick={dismiss} data-testid="book-guide-dismiss">
          {t("books.guideDismiss")}
        </Button>
      </div>
      <ol className="mt-3 space-y-2">
        {steps.map((step, index) => (
          <li key={step} className="flex items-baseline gap-3">
            <span
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-fun-purple text-sm font-bold text-white"
              aria-hidden
            >
              {index + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}
