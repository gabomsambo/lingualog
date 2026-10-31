"use client"

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import { Check, RotateCcw } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { useLocale } from "@/i18n/LocaleProvider"
import { ApiError, submitReview, type ReviewCard, type ReviewRating } from "@/lib/api"
import { emptyTally, isCorrectAnswer, statusClass, type SessionTally } from "@/lib/review"

interface ReviewSessionProps {
  cards: ReviewCard[]
  onFinished: (tally: SessionTally) => void
}

function Marked({ children }: { children: ReactNode }) {
  return (
    <mark className="rounded bg-fun-yellow/30 px-1 font-semibold text-foreground" data-testid="review-target">
      {children}
    </mark>
  )
}

function Blank() {
  return (
    <span
      aria-label="blank"
      data-testid="review-blank"
      className="mx-1 inline-block min-w-[5rem] border-b-2 border-fun-purple align-baseline"
    >
      &nbsp;
    </span>
  )
}

function Front({ card, revealed }: { card: ReviewCard; revealed: boolean }) {
  const { before, target, after } = card.front
  const asksForWord = card.format !== "recognition"

  if (card.format === "meaning_to_word") {
    return (
      <p className="font-serif text-2xl leading-relaxed" data-testid="review-front">
        {card.hint || card.meaning}
      </p>
    )
  }
  return (
    <p className="font-serif text-2xl leading-relaxed" data-testid="review-front">
      {before}
      {asksForWord && !revealed ? <Blank /> : target ? <Marked>{target}</Marked> : null}
      {after}
    </p>
  )
}

export function ReviewSession({ cards, onFinished }: ReviewSessionProps) {
  const { t } = useLocale()
  const [queue, setQueue] = useState<ReviewCard[]>(cards)
  const [revealed, setRevealed] = useState(false)
  const [typed, setTyped] = useState("")
  const [checked, setChecked] = useState<boolean | null>(null)
  const [tapGloss, setTapGloss] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [failed, setFailed] = useState(false)
  const [tally, setTally] = useState<SessionTally>(emptyTally)
  // A card that comes due again within the session is shown once more, so the total can grow.
  const [total, setTotal] = useState(cards.length)
  const shownAt = useRef(Date.now())

  const card = queue[0]

  useEffect(() => {
    shownAt.current = Date.now()
    setRevealed(false)
    setTyped("")
    setChecked(null)
    setTapGloss(false)
    setFailed(false)
  }, [card?.card_id, card?.reps])

  useEffect(() => {
    if (!card) onFinished(tally)
    // Fires once when the queue empties.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [card])

  const reveal = useCallback(() => {
    if (!card) return
    if (card.typed && checked === null) setChecked(isCorrectAnswer(card, typed))
    setRevealed(true)
  }, [card, checked, typed])

  const answer = useCallback(
    async (rating: ReviewRating) => {
      if (!card || submitting) return
      setSubmitting(true)
      setFailed(false)
      try {
        const result = await submitReview(card.card_id, {
          rating,
          reps: card.reps,
          duration_ms: Date.now() - shownAt.current,
        })
        setTally((current) => ({
          reviewed: current.reviewed + 1,
          again: current.again + (rating === "again" ? 1 : 0),
          gotIt: current.gotIt + (rating === "got_it" ? 1 : 0),
          nowKnown: current.nowKnown + (result.status === "known" && card.status !== "known" ? 1 : 0),
        }))
        setQueue((current) => {
          const [, ...rest] = current
          return result.requeue ? [...rest, { ...card, reps: result.reps, is_new: false }] : rest
        })
        if (result.requeue) setTotal((count) => count + 1)
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) {
          // Already reviewed elsewhere (another tab, or a repeated tap): move on.
          setQueue((current) => current.slice(1))
          setTotal((count) => count - 1)
        } else {
          setFailed(true)
        }
      } finally {
        setSubmitting(false)
      }
    },
    [card, submitting],
  )

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) return
      if (!revealed && (event.key === " " || event.key === "Enter")) {
        event.preventDefault()
        reveal()
      } else if (revealed && event.key === "1") void answer("again")
      else if (revealed && event.key === "2") void answer("got_it")
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [revealed, reveal, answer])

  if (!card) return null

  const question =
    card.format === "recognition"
      ? t("vocabulary.reviewWhatMeans")
      : card.format === "meaning_to_word"
        ? t("vocabulary.reviewWhichWord")
        : t("vocabulary.reviewFillBlank")
  const showAnswerWord = card.format !== "recognition"

  return (
    <div className="mx-auto max-w-2xl space-y-4" data-testid="review-session">
      <div className="space-y-1">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span data-testid="review-progress">
            {t("vocabulary.reviewProgress", { current: Math.min(tally.reviewed + 1, total), total })}
          </span>
          <span>{t("vocabulary.reviewLeft", { count: queue.length })}</span>
        </div>
        <Progress value={(tally.reviewed / Math.max(1, total)) * 100} aria-label={t("vocabulary.reviewTitle")} />
      </div>

      <Card className="rounded-3xl">
        <CardContent className="space-y-5 p-6 sm:p-8">
          <div className="flex flex-wrap items-center gap-2">
            {card.is_new && <Badge className={statusClass("new")}>{t("vocabulary.reviewNewWord")}</Badge>}
            {card.at_risk && (
              <Badge variant="outline" className="border-red-400 text-red-600">
                <span className="mr-1 inline-block h-2 w-2 rounded-full bg-red-500" aria-hidden />
                {t("vocabulary.reviewAtRisk")}
              </Badge>
            )}
            <span className="text-sm font-medium text-muted-foreground">{question}</span>
          </div>

          <Front card={card} revealed={revealed} />

          {!revealed && card.format !== "meaning_to_word" && card.hint && (
            <p className="text-sm text-muted-foreground" data-testid="review-hint">
              {card.hint}
            </p>
          )}
          {!revealed && card.tap_gloss && card.format !== "recognition" && (
            tapGloss ? (
              <p className="text-sm text-fun-purple" data-testid="review-tap-gloss">{card.tap_gloss}</p>
            ) : (
              <Button variant="outline" size="sm" onClick={() => setTapGloss(true)}>
                {t("vocabulary.reviewShowHint")}
              </Button>
            )
          )}

          {!revealed && card.typed && (
            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault()
                reveal()
              }}
            >
              <Input
                autoFocus
                value={typed}
                onChange={(event) => setTyped(event.target.value)}
                aria-label={t("vocabulary.reviewTypeAnswer")}
                placeholder={t("vocabulary.reviewTypeAnswer")}
                autoComplete="off"
                autoCapitalize="off"
              />
              <Button type="submit">{t("vocabulary.reviewCheck")}</Button>
            </form>
          )}

          {revealed && (
            <div className="space-y-3 border-t pt-5" data-testid="review-answer">
              {card.typed && checked !== null && (
                <p
                  role="status"
                  className={checked ? "font-semibold text-green-600" : "font-semibold text-red-600"}
                  data-testid="review-check-result"
                >
                  {checked ? t("vocabulary.reviewCorrect") : t("vocabulary.reviewNotQuite")}
                </p>
              )}
              {showAnswerWord && (
                <p className="text-2xl font-bold text-fun-purple" data-testid="review-answer-word">
                  {card.answer}
                </p>
              )}
              <p className="text-lg font-medium" data-testid="review-meaning">{card.meaning}</p>
              {card.gloss && <p className="text-fun-purple" data-testid="review-gloss">{card.gloss}</p>}
              {card.tap_gloss &&
                (tapGloss ? (
                  <p className="text-fun-purple" data-testid="review-tap-gloss">{card.tap_gloss}</p>
                ) : (
                  <Button variant="outline" size="sm" onClick={() => setTapGloss(true)}>
                    {t("vocabulary.reviewShowHint")}
                  </Button>
                ))}
            </div>
          )}

          {failed && (
            <p role="alert" className="text-sm text-red-600">{t("vocabulary.reviewSaveFailed")}</p>
          )}
        </CardContent>
      </Card>

      {!revealed ? (
        !card.typed && (
          <Button className="h-14 w-full rounded-2xl text-lg" onClick={reveal}>
            {t("vocabulary.reviewShowAnswer")}
          </Button>
        )
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <Button
            variant="outline"
            className="h-14 rounded-2xl text-lg"
            disabled={submitting}
            onClick={() => void answer("again")}
          >
            <RotateCcw className="mr-2 h-5 w-5" /> {t("vocabulary.reviewAgain")}
          </Button>
          <Button className="h-14 rounded-2xl text-lg" disabled={submitting} onClick={() => void answer("got_it")}>
            <Check className="mr-2 h-5 w-5" /> {t("vocabulary.reviewGotIt")}
          </Button>
        </div>
      )}
    </div>
  )
}
