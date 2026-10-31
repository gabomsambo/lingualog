"use client"

import { useMemo, useRef, useState } from "react"
import { Camera, Check, Loader2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useLocale } from "@/i18n/LocaleProvider"
import {
  ApiError,
  markWord,
  readPagePhoto,
  unmarkWord,
  type BookMark,
  type PagePhotoResult,
} from "@/lib/api"
import { alreadyHave, BAND_CLASS, candidateIndex, normalizeWord, prepareImage, sentenceOf, tokenize } from "@/lib/books"
import { statusClass } from "@/lib/review"
import { cn } from "@/lib/utils"

interface BookPagePhotoProps {
  bookId: string
  sessionId: string
  /** The page the learner is on; every word tapped from this photo is marked on it. */
  page?: number
  onMarked: (mark: BookMark) => void
  onUnmarked: (markId: string) => void
}

/** The server's refusal codes, each with the message key that explains it. */
const PHOTO_ERRORS: Record<string, string> = {
  photo_too_large: "books.photoTooLarge",
  photo_unsupported: "books.photoUnsupported",
  photo_rate_limited: "books.photoRateLimited",
  photo_daily_limit: "books.photoDailyLimit",
  photo_quota_reached: "books.photoQuotaReached",
}

function errorKey(error: unknown): string {
  const code = error instanceof ApiError ? (error.detail?.code as string | undefined) : undefined
  return (code && PHOTO_ERRORS[code]) || "books.photoFailed"
}

/** Photograph a page, then tap the words you did not know. The photo and its text live only in this component. */
export function BookPagePhoto({ bookId, sessionId, page, onMarked, onUnmarked }: BookPagePhotoProps) {
  const { t } = useLocale()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<PagePhotoResult | null>(null)
  // Marks made from this photo, by normalised word, so a second tap undoes the first.
  const [marked, setMarked] = useState<Record<string, string>>({})

  const tokens = useMemo(() => (result ? tokenize(result.transcription) : []), [result])
  const candidates = useMemo(() => candidateIndex(result?.candidates ?? []), [result])

  const choose = async (file: File | undefined) => {
    if (!file) return
    setBusy(true)
    setError(null)
    setMarked({})
    try {
      setResult(await readPagePhoto(bookId, await prepareImage(file)))
    } catch (failure) {
      setResult(null)
      setError(errorKey(failure))
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ""
    }
  }

  const toggle = async (index: number) => {
    const word = tokens[index].text
    const key = normalizeWord(word)
    try {
      if (marked[key]) {
        await unmarkWord(bookId, sessionId, marked[key])
        onUnmarked(marked[key])
        setMarked(({ [key]: _removed, ...rest }) => rest)
        return
      }
      const mark = await markWord(bookId, sessionId, { word, sentence: sentenceOf(tokens, index), page })
      onMarked(mark)
      setMarked((current) => ({ ...current, [key]: mark.id }))
    } catch {
      setError("books.markFailed")
    }
  }

  const estimate = result?.estimate

  return (
    <section className="space-y-3" data-testid="page-photo">
      <input
        ref={input}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        aria-label={t("books.photoInput")}
        data-testid="page-photo-input"
        onChange={(event) => void choose(event.target.files?.[0])}
      />
      <Button variant="outline" disabled={busy} onClick={() => input.current?.click()}>
        {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Camera className="mr-2 h-4 w-4" />}
        {busy ? t("books.photoReading") : t("books.photoButton")}
      </Button>

      {error && (
        <p role="alert" className="text-sm text-red-600">
          {t(error)}
        </p>
      )}

      {result && !result.readable && (
        <p role="status" className="text-sm text-muted-foreground" data-testid="page-photo-unreadable">
          {t("books.photoUnreadable")}
        </p>
      )}

      {result?.readable && (
        <div className="space-y-3 rounded-2xl border bg-card p-4">
          <p className="text-sm text-muted-foreground">{t("books.photoTapHint")}</p>
          <p className="font-serif text-lg leading-loose" data-testid="page-photo-text">
            {tokens.map((token, index) => {
              if (!token.word) return <span key={index}>{token.text}</span>
              const key = normalizeWord(token.text)
              const candidate = candidates.get(key)
              const isMarked = !!marked[key]
              return (
                <button
                  key={index}
                  type="button"
                  aria-pressed={isMarked}
                  onClick={() => void toggle(index)}
                  className={cn(
                    "rounded px-0.5 transition-colors",
                    !isMarked && "hover:bg-fun-purple/15",
                    candidate && !alreadyHave(candidate.status) && !isMarked && "bg-fun-yellow/30",
                    candidate && alreadyHave(candidate.status) && "text-muted-foreground underline decoration-dotted",
                    candidate?.status && !alreadyHave(candidate.status) && `border ${statusClass(candidate.status)}`,
                    isMarked && "bg-fun-purple text-white hover:bg-fun-purple/90",
                  )}
                  data-candidate={candidate ? "true" : undefined}
                >
                  {token.text}
                  {isMarked && <Check className="ml-0.5 inline h-3 w-3" aria-hidden />}
                </button>
              )
            })}
          </p>
          {estimate && (
            <div className="flex flex-wrap items-center gap-2 text-sm" data-testid="page-photo-estimate">
              <span>{t("books.photoEstimate", { count: estimate.unknown_estimate })}</span>
              {estimate.band && (
                <Badge variant="outline" className={BAND_CLASS[estimate.band]}>
                  {t(`books.band_${estimate.band}`)}
                </Badge>
              )}
              <span className="text-muted-foreground">{t("books.estimateLabel")}</span>
            </div>
          )}
          <Button variant="ghost" size="sm" onClick={() => setResult(null)}>
            {t("books.photoDismiss")}
          </Button>
        </div>
      )}
    </section>
  )
}
