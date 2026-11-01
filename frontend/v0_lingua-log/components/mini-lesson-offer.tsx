"use client"

import { useEffect, useState } from "react"
import { BookOpen, Check, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { useLocale } from "@/i18n/LocaleProvider"
import { sameLanguage } from "@/lib/side-by-side"
import {
  getMiniLessonDrill,
  getMiniLessonOffer,
  markMiniLessonSeen,
  snoozeMiniLesson,
  type MiniLessonCloze,
  type MiniLessonOffer as MiniLessonOfferData,
} from "@/lib/api"
import { compareRetypedText, matchesRetypedText } from "@/lib/side-by-side"
import { cn } from "@/lib/utils"

type Panel = "lesson" | "drill"

export function MiniLessonOffer({ entryId, language, analysisStatus }: {
  entryId: string
  language: string
  analysisStatus: string
}) {
  const { t } = useLocale()
  const [offer, setOffer] = useState<MiniLessonOfferData | null>(null)
  const [loading, setLoading] = useState(true)
  const [snoozed, setSnoozed] = useState(false)
  const [open, setOpen] = useState(false)
  const [panel, setPanel] = useState<Panel>("lesson")
  const [drill, setDrill] = useState<MiniLessonCloze[] | null>(null)
  const [drillLoading, setDrillLoading] = useState(false)
  const [answers, setAnswers] = useState<string[]>([])
  const [checked, setChecked] = useState<boolean[]>([])

  useEffect(() => {
    let cancelled = false
    if (!entryId || !sameLanguage(language, "es") || analysisStatus === "mock" || analysisStatus === "failed") {
      setLoading(false)
      setOffer(null)
      return
    }
    setLoading(true)
    getMiniLessonOffer(entryId)
      .then((result) => !cancelled && setOffer(result))
      .catch(() => !cancelled && setOffer(null))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [analysisStatus, entryId, language])

  if (loading || !offer) return null

  const tagLabel = t(`feedback.errorTag_${offer.tag}`)
  const openLesson = () => {
    setPanel("lesson")
    setOpen(true)
    markMiniLessonSeen(offer.l2, offer.tag).catch(() => undefined)
  }

  const snooze = async () => {
    try {
      await snoozeMiniLesson(offer.l2, offer.tag)
      setSnoozed(true)
    } catch {
      // The card remains available if the snooze could not be saved.
    }
  }

  const startDrill = async () => {
    setDrillLoading(true)
    try {
      const items = await getMiniLessonDrill(offer.l2, offer.tag, entryId)
      setDrill(items)
      setAnswers(Array(items.length).fill(""))
      setChecked(Array(items.length).fill(false))
      setPanel("drill")
    } catch {
      setDrill([])
      setPanel("drill")
    } finally {
      setDrillLoading(false)
    }
  }

  return (
    <>
      <Card
        className={cn(
          "overflow-hidden border-fun-blue/25 shadow-sm",
          snoozed && "border-fun-purple/20 bg-fun-purple/5",
        )}
        data-testid={snoozed ? "mini-lesson-snoozed" : "mini-lesson-offer"}
      >
        <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <BookOpen className="mt-0.5 h-5 w-5 shrink-0 text-fun-purple" />
            <div>
              <p className="font-bold">
                {snoozed
                  ? t("feedback.miniLessonSnoozed")
                  : t("feedback.miniLessonPrompt", { tag: tagLabel })}
              </p>
              {!snoozed && (
                <p className="mt-1 text-sm text-muted-foreground">{offer.lesson.title}</p>
              )}
            </div>
          </div>
          {!snoozed && (
            <div className="flex shrink-0 flex-wrap gap-2">
              <Button type="button" size="sm" onClick={openLesson}>
                {t("feedback.miniLessonOpen")}
              </Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => void snooze()}>
                {t("feedback.miniLessonNotNow")}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl" data-testid="mini-lesson-sheet">
          <SheetHeader className="pr-8 text-left">
            <SheetTitle className="text-2xl">{offer.lesson.title}</SheetTitle>
            <SheetDescription>
              {panel === "drill" ? t("feedback.miniLessonDrillIntro") : t("feedback.miniLessonSheetIntro")}
            </SheetDescription>
          </SheetHeader>

          {panel === "lesson" ? (
            <div className="mt-6 space-y-5">
              <p className="leading-relaxed">{offer.lesson.explanation}</p>
              <section aria-label={t("feedback.miniLessonExamples")}>
                <h3 className="mb-2 font-bold">{t("feedback.miniLessonExamples")}</h3>
                <ul className="space-y-2">
                  {offer.lesson.examples.map((example, index) => (
                    <li key={`${example.es}-${index}`} className="rounded-xl bg-muted/60 p-3">
                      <p lang="es" className="font-serif text-lg">{example.es}</p>
                      <p className="text-sm text-muted-foreground">{example.en}</p>
                    </li>
                  ))}
                </ul>
              </section>
              <aside className="rounded-2xl border border-fun-yellow/50 bg-fun-yellow/10 p-4">
                <h3 className="font-bold">{t("feedback.miniLessonTrap")}</h3>
                <p className="mt-1 text-sm leading-relaxed">{offer.lesson.trap_note}</p>
              </aside>
              <Button type="button" onClick={() => void startDrill()} disabled={drillLoading}>
                {drillLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {t("feedback.miniLessonPractice")}
              </Button>
            </div>
          ) : (
            <div className="mt-6 space-y-5">
              {drillLoading ? (
                <p className="text-sm text-muted-foreground">{t("feedback.miniLessonLoading")}</p>
              ) : drill && drill.length < 3 ? (
                <p className="rounded-xl bg-muted/60 p-4 text-sm text-muted-foreground">
                  {t("feedback.miniLessonDrillUnavailable")}
                </p>
              ) : (
                drill?.map((item, index) => (
                  <DrillItem
                    key={`${item.before}-${item.answer}-${index}`}
                    item={item}
                    index={index}
                    value={answers[index] || ""}
                    checked={checked[index] || false}
                    onChange={(value) => {
                      setAnswers((current) => current.map((answer, i) => i === index ? value : answer))
                      setChecked((current) => current.map((wasChecked, i) => i === index ? false : wasChecked))
                    }}
                    onCheck={() => setChecked((current) => current.map((value, i) => i === index ? true : value))}
                    t={t}
                  />
                ))
              )}
              <Button type="button" variant="outline" onClick={() => setPanel("lesson")}>
                {t("feedback.miniLessonBack")}
              </Button>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </>
  )
}

function DrillItem({
  item,
  index,
  value,
  checked,
  onChange,
  onCheck,
  t,
}: {
  item: MiniLessonCloze
  index: number
  value: string
  checked: boolean
  onChange: (value: string) => void
  onCheck: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}) {
  const isCorrect = matchesRetypedText(item.answer, value)
  const diff = checked && !isCorrect ? compareRetypedText(item.answer, value) : []
  return (
    <section className="rounded-2xl border border-border p-4" data-testid={`mini-lesson-drill-${index + 1}`}>
      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">
        {t("feedback.miniLessonQuestion", { number: index + 1 })}
      </p>
      <div className="flex flex-wrap items-baseline gap-y-2 font-serif text-lg leading-relaxed" lang="es">
        <span>{item.before}</span>
        <label className="mx-1 inline-flex">
          <span className="sr-only">{t("feedback.miniLessonInput")}</span>
          <input
            value={value}
            onChange={(event) => onChange(event.target.value)}
            disabled={checked && isCorrect}
            className={cn(
              "min-w-24 border-b-2 border-fun-purple bg-fun-purple/5 px-2 text-center outline-none",
              "focus:border-fun-blue",
            )}
            autoComplete="off"
          />
        </label>
        <span>{item.after}</span>
      </div>
      {!checked ? (
        <Button type="button" size="sm" variant="outline" className="mt-3" onClick={onCheck} disabled={!value.trim()}>
          {t("feedback.miniLessonCheck")}
        </Button>
      ) : isCorrect ? (
        <p className="mt-3 flex items-center gap-2 text-sm font-semibold text-green-700">
          <Check className="h-4 w-4" /> {t("feedback.miniLessonCorrect")}
        </p>
      ) : (
        <div className="mt-3 space-y-1 text-sm">
          <p className="text-muted-foreground">{t("feedback.miniLessonTryAgain")}</p>
          <p aria-label={t("feedback.miniLessonAnswer")}>
            {diff.map((part, partIndex) => part.kind === "del" ? (
              <del key={`del-${partIndex}`} className="rounded bg-red-100 px-1 text-red-800">{part.text}</del>
            ) : part.kind === "ins" ? (
              <ins
                key={`ins-${partIndex}`}
                className="rounded bg-green-100 px-1 text-green-800 no-underline"
              >
                {part.text}
              </ins>
            ) : <span key={`same-${partIndex}`}>{part.text} </span>)}
          </p>
        </div>
      )}
    </section>
  )
}
