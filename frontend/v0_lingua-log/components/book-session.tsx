"use client"

import { useCallback, useRef, useState, type FormEvent } from "react"
import { BookmarkCheck, Sparkles, X } from "lucide-react"

import { BookPagePhoto } from "@/components/book-page-photo"
import { LookupSheet, type LookupContext } from "@/components/lookup-sheet"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useLocale } from "@/i18n/LocaleProvider"
import {
  endReadingSession,
  getBook,
  markWord,
  unmarkWord,
  type Book,
  type BookMark,
  type ReadingSessionSummary,
} from "@/lib/api"

interface BookSessionProps {
  book: Book
  session: ReadingSessionSummary
  initialMarks: BookMark[]
  onEnded: (summary: ReadingSessionSummary) => void
}

function pageNumber(value: string): number | undefined {
  const page = Number.parseInt(value, 10)
  return Number.isFinite(page) && page > 0 ? page : undefined
}

/** The reading companion while a session is open: mark a word in a second and keep reading. */
export function BookSession({ book, session, initialMarks, onEnded }: BookSessionProps) {
  const { t } = useLocale()
  const wordInput = useRef<HTMLInputElement>(null)
  const [marks, setMarks] = useState<BookMark[]>(initialMarks)
  const [word, setWord] = useState("")
  const [sentence, setSentence] = useState("")
  const [page, setPage] = useState(session.page_from ? String(session.page_from) : "")
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const [needNow, setNeedNow] = useState<LookupContext | null>(null)
  const [ending, setEnding] = useState(false)
  const [lastPage, setLastPage] = useState("")

  const refresh = useCallback(async () => {
    try {
      const detail = await getBook(book.id)
      if (detail.session) setMarks(detail.session.marks)
    } catch {
      // The list is still right for what was marked here; the next change refreshes it.
    }
  }, [book.id])

  const addMark = (mark: BookMark) =>
    setMarks((current) => [mark, ...current.filter((existing) => existing.id !== mark.id)])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const text = word.trim()
    if (!text || busy) return
    setBusy(true)
    setFailed(false)
    try {
      addMark(await markWord(book.id, session.id, { word: text, sentence: sentence.trim(), page: pageNumber(page) }))
      setWord("")
      setSentence("")
      wordInput.current?.focus()
    } catch {
      setFailed(true)
    } finally {
      setBusy(false)
    }
  }

  const undo = async (mark: BookMark) => {
    try {
      await unmarkWord(book.id, session.id, mark.id)
      setMarks((current) => current.filter((existing) => existing.id !== mark.id))
    } catch {
      setFailed(true)
    }
  }

  const finish = async () => {
    setFailed(false)
    try {
      onEnded(await endReadingSession(book.id, session.id, pageNumber(lastPage) ?? pageNumber(page)))
    } catch {
      setFailed(true)
    }
  }

  return (
    <div className="space-y-5" data-testid="book-session">
      <form onSubmit={submit} className="space-y-3 rounded-3xl border bg-card p-4" data-testid="capture-bar">
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            ref={wordInput}
            value={word}
            onChange={(event) => setWord(event.target.value)}
            placeholder={t("books.wordPlaceholder")}
            aria-label={t("books.wordLabel")}
            className="sm:flex-1"
            autoFocus
          />
          <Input
            value={page}
            onChange={(event) => setPage(event.target.value.replace(/\D/g, ""))}
            inputMode="numeric"
            placeholder={t("books.pagePlaceholder")}
            aria-label={t("books.pageLabel")}
            className="sm:w-28"
          />
        </div>
        <Input
          value={sentence}
          onChange={(event) => setSentence(event.target.value)}
          placeholder={t("books.sentencePlaceholder")}
          aria-label={t("books.sentenceLabel")}
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button type="submit" disabled={!word.trim() || busy}>
            <BookmarkCheck className="mr-2 h-4 w-4" /> {t("books.mark")}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={!word.trim()}
            onClick={() =>
              setNeedNow({
                text: word.trim(),
                sentence: sentence.trim() || undefined,
                language: book.language,
                source: "book_session",
                sourceId: session.id,
                page: pageNumber(page),
              })
            }
          >
            <Sparkles className="mr-2 h-4 w-4" /> {t("books.needThisNow")}
          </Button>
          <p className="text-sm text-muted-foreground">{t("books.markHint")}</p>
        </div>
        {failed && (
          <p role="alert" className="text-sm text-red-600">
            {t("books.markFailed")}
          </p>
        )}
      </form>

      <BookPagePhoto
        bookId={book.id}
        sessionId={session.id}
        page={pageNumber(page)}
        onMarked={addMark}
        onUnmarked={(markId) => setMarks((current) => current.filter((mark) => mark.id !== markId))}
      />

      <section aria-label={t("books.marksTitle")} data-testid="marks-list">
        <h3 className="mb-2 text-lg font-semibold">{t("books.marksCount", { count: marks.length })}</h3>
        {marks.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("books.marksEmpty")}</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {marks.map((mark) => (
              <li key={mark.id}>
                <Badge variant="outline" className="gap-2 py-1 pl-3 pr-1 text-base" title={mark.sentence ?? undefined}>
                  <span>{mark.surface}</span>
                  {mark.page && <span className="text-xs text-muted-foreground">{t("books.pageShort", { page: mark.page })}</span>}
                  {mark.times_marked > 1 && (
                    <span className="rounded-full bg-fun-yellow/40 px-1.5 text-xs" data-testid="mark-times">
                      ×{mark.times_marked}
                    </span>
                  )}
                  <button
                    type="button"
                    className="rounded-full p-1 hover:bg-muted"
                    aria-label={t("books.unmark", { word: mark.surface })}
                    onClick={() => void undo(mark)}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="flex flex-wrap items-center gap-3 border-t pt-4">
        {ending ? (
          <>
            <Input
              value={lastPage}
              onChange={(event) => setLastPage(event.target.value.replace(/\D/g, ""))}
              inputMode="numeric"
              placeholder={t("books.lastPagePlaceholder")}
              aria-label={t("books.lastPageLabel")}
              className="w-40"
            />
            <Button onClick={() => void finish()}>{t("books.endConfirm")}</Button>
            <Button variant="ghost" onClick={() => setEnding(false)}>{t("common.cancel")}</Button>
          </>
        ) : (
          <Button variant="outline" onClick={() => setEnding(true)} data-testid="end-session">
            {t("books.endSession")}
          </Button>
        )}
      </div>

      <LookupSheet
        context={needNow}
        open={!!needNow}
        onOpenChange={(open) => {
          if (open) return
          setNeedNow(null)
          setWord("")
          setSentence("")
          void refresh()
        }}
      />
    </div>
  )
}
