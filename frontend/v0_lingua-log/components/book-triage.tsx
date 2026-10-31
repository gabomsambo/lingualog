"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { Loader2, RotateCw } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { useToast } from "@/components/ui/use-toast"
import { useLocale } from "@/i18n/LocaleProvider"
import {
  addVocabularyItem,
  ApiError,
  buildSessionCards,
  skipMarks,
  updateVocabularyItem,
  type Book,
  type ReadingSessionSummary,
  type TriageItem,
} from "@/lib/api"
import { BAND_CLASS } from "@/lib/books"

interface BookTriageProps {
  book: Book
  session: ReadingSessionSummary
  onDone: () => void
}

type Choice = "study" | "known" | "skip"

/** After a session: cards for what you marked, recurring words first, then Study / I know it / Skip. */
export function BookTriage({ book, session, onDone }: BookTriageProps) {
  const { t } = useLocale()
  const { toast } = useToast()
  const [items, setItems] = useState<TriageItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [failedBuild, setFailedBuild] = useState(false)
  const [handled, setHandled] = useState(0)
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const build = useCallback(async () => {
    setLoading(true)
    setFailedBuild(false)
    try {
      setItems((await buildSessionCards(book.id, session.id)).items)
    } catch {
      setFailedBuild(true)
    } finally {
      setLoading(false)
    }
  }, [book.id, session.id])

  useEffect(() => {
    void build()
  }, [build])

  const remove = (item: TriageItem) => {
    setItems((current) => (current ?? []).filter((other) => other.key !== item.key))
    setHandled((count) => count + 1)
  }

  const choose = async (item: TriageItem, choice: Choice) => {
    setBusy(item.key)
    setMessage(null)
    try {
      if (choice === "skip") {
        await skipMarks(book.id, item.encounter_ids)
        remove(item)
        toast({ title: t("books.keptInGlossary") })
        return
      }
      const saved = await addVocabularyItem({
        term: item.lemma,
        language: book.language,
        example_sentence: item.sentence ?? undefined,
        encounter_id: item.encounter_id ?? undefined,
      })
      let capped = false
      try {
        await updateVocabularyItem(saved.id, { status: choice === "study" ? "learning" : "known" })
      } catch (error) {
        // Over today's new-word limit: the word is kept in the notebook as New and waits.
        if (!(error instanceof ApiError && error.status === 409)) throw error
        capped = true
        setMessage(t("books.capReached", { word: item.lemma }))
      }
      remove(item)
      toast({ title: choice === "study" && !capped ? t("books.addedToReview") : t("books.addedToNotebook") })
    } catch {
      setMessage(t("books.choiceFailed", { word: item.lemma }))
    } finally {
      setBusy(null)
    }
  }

  const skipOneOffs = async () => {
    const oneOffs = (items ?? []).filter((item) => !item.recurring && item.card_status === "ok")
    if (!oneOffs.length) return
    try {
      await skipMarks(book.id, oneOffs.flatMap((item) => item.encounter_ids))
      setItems((current) => (current ?? []).filter((item) => !oneOffs.includes(item)))
      setHandled((count) => count + oneOffs.length)
      toast({ title: t("books.keptInGlossary") })
    } catch {
      setMessage(t("books.choiceFailed", { word: "" }))
    }
  }

  const summary = [
    session.page_from && session.page_to
      ? session.page_from === session.page_to
        ? t("books.summaryPage", { page: session.page_from })
        : t("books.summaryPages", { from: session.page_from, to: session.page_to })
      : null,
    t("books.summaryMarked", { count: session.words_marked }),
    session.words_per_page !== null ? t("books.summaryRate", { rate: session.words_per_page }) : null,
  ].filter(Boolean)

  const recurring = (items ?? []).filter((item) => item.recurring)
  const oneOffs = (items ?? []).filter((item) => !item.recurring)

  return (
    <div className="space-y-5" data-testid="book-triage">
      <div>
        <h2 className="text-2xl font-bold">{t("books.sessionDone")}</h2>
        <p className="text-muted-foreground" data-testid="session-summary">{summary.join(" · ")}</p>
        {session.band && (
          <Badge variant="outline" className={`mt-2 ${BAND_CLASS[session.band]}`}>
            {t(`books.band_${session.band}`)} · {t("books.estimateLabel")}
          </Badge>
        )}
      </div>

      {loading && (
        <p className="flex items-center gap-2 text-muted-foreground" role="status">
          <Loader2 className="h-4 w-4 animate-spin" /> {t("books.buildingCards", { count: session.words_marked })}
        </p>
      )}

      {failedBuild && (
        <div role="alert" className="space-y-2">
          <p>{t("books.buildFailed")}</p>
          <Button variant="outline" onClick={() => void build()}><RotateCw className="mr-2 h-4 w-4" />{t("books.retry")}</Button>
        </div>
      )}

      {message && <p role="status" className="rounded-xl bg-fun-yellow/15 p-3 text-sm">{message}</p>}

      {!loading && items && items.length === 0 && (
        <Card className="rounded-3xl" data-testid="triage-empty">
          <CardContent className="space-y-3 p-6">
            <p className="text-lg font-medium">{handled > 0 ? t("books.allChosen") : t("books.nothingToChoose")}</p>
            <div className="flex flex-wrap gap-3">
              <Button asChild><Link href={`/books/${book.id}/glossary`}>{t("books.openGlossary")}</Link></Button>
              <Button variant="outline" onClick={onDone}>{t("books.backToBook")}</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {recurring.length > 0 && (
        <TriageGroup title={t("books.recurringTitle")} hint={t("books.recurringHint")}>
          {recurring.map((item) => (
            <TriageRow key={item.key} item={item} busy={busy === item.key} onChoose={choose} onRetry={build} />
          ))}
        </TriageGroup>
      )}

      {oneOffs.length > 0 && (
        <TriageGroup
          title={t("books.oneOffTitle")}
          hint={t("books.oneOffHint")}
          action={
            <Button variant="outline" size="sm" onClick={() => void skipOneOffs()} data-testid="skip-one-offs">
              {t("books.skipAllOneOffs")}
            </Button>
          }
        >
          {oneOffs.map((item) => (
            <TriageRow key={item.key} item={item} busy={busy === item.key} onChoose={choose} onRetry={build} />
          ))}
        </TriageGroup>
      )}
    </div>
  )
}

function TriageGroup({
  title,
  hint,
  action,
  children,
}: {
  title: string
  hint: string
  action?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold">{title}</h3>
          <p className="text-sm text-muted-foreground">{hint}</p>
        </div>
        {action}
      </div>
      <ul className="space-y-3">{children}</ul>
    </section>
  )
}

function TriageRow({
  item,
  busy,
  onChoose,
  onRetry,
}: {
  item: TriageItem
  busy: boolean
  onChoose: (item: TriageItem, choice: Choice) => Promise<void>
  onRetry: () => Promise<void>
}) {
  const { t } = useLocale()
  const ready = item.card_status === "ok" && !!item.card
  return (
    <li className="rounded-2xl border bg-card p-4" data-testid="triage-item">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <span className="font-serif text-2xl">{item.lemma}</span>
        {item.times_marked > 1 && <Badge variant="outline">{t("books.markedTimes", { count: item.times_marked })}</Badge>}
        {item.page && <span className="text-sm text-muted-foreground">{t("books.pageShort", { page: item.page })}</span>}
      </div>
      {item.sentence && <p className="mt-1 text-sm text-muted-foreground">{item.sentence}</p>}
      {ready ? (
        <p className="mt-2">
          {item.card?.sense_in_context}
          {item.card?.gloss_l1 && <span className="ml-2 text-fun-purple">{item.card.gloss_l1}</span>}
        </p>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground" role="status">{t("books.cardUnavailable")}</p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {ready && (
          <>
            <Button size="sm" disabled={busy} onClick={() => void onChoose(item, "study")}>{t("books.study")}</Button>
            <Button size="sm" variant="outline" disabled={busy} onClick={() => void onChoose(item, "known")}>{t("books.iKnowIt")}</Button>
          </>
        )}
        {!ready && (
          <Button size="sm" variant="outline" disabled={busy} onClick={() => void onRetry()}>{t("books.retry")}</Button>
        )}
        <Button size="sm" variant="ghost" disabled={busy} onClick={() => void onChoose(item, "skip")}>{t("books.skip")}</Button>
      </div>
    </li>
  )
}
