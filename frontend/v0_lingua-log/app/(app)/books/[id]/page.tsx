"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { ArrowLeft, BookMarked, BookOpen, Edit, ListChecks } from "lucide-react"

import { BookSession } from "@/components/book-session"
import { BookTriage } from "@/components/book-triage"
import { LoadingSpinner } from "@/components/loading-spinner"
import { WordsPerPageChart } from "@/components/words-per-page-chart"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useLocale } from "@/i18n/LocaleProvider"
import { resolveLanguage } from "@/i18n/languages"
import {
  getBook,
  getBookProgress,
  startReadingSession,
  updateBook,
  type BookDetail,
  type BookProgress,
  type BookStatus,
  type ReadingSessionSummary,
} from "@/lib/api"

export default function BookPage() {
  const { t } = useLocale()
  const { id } = useParams<{ id: string }>()
  const [detail, setDetail] = useState<BookDetail | null>(null)
  const [progress, setProgress] = useState<BookProgress | null>(null)
  const [failed, setFailed] = useState(false)
  const [startPage, setStartPage] = useState("")
  // The session whose marks are being turned into cards, once it has ended.
  const [finished, setFinished] = useState<ReadingSessionSummary | null>(null)

  const load = useCallback(async () => {
    try {
      const [next, charts] = await Promise.all([getBook(id), getBookProgress(id)])
      setDetail(next)
      setProgress(charts)
      setFailed(false)
    } catch {
      setFailed(true)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  if (failed) {
    return (
      <div className="py-12 text-center" role="alert">
        <p className="mb-4 text-muted-foreground">{t("books.loadFailed")}</p>
        <Button variant="outline" onClick={() => void load()}>{t("books.retry")}</Button>
      </div>
    )
  }
  if (!detail) {
    return <div className="flex h-64 items-center justify-center"><LoadingSpinner text={t("books.loading")} /></div>
  }

  const { book, session } = detail
  const language = resolveLanguage(book.language)
  const lastEnded = progress?.sessions.at(-1) ?? null

  const start = async () => {
    const page = Number.parseInt(startPage, 10)
    try {
      await startReadingSession(book.id, Number.isFinite(page) && page > 0 ? page : undefined)
    } catch {
      setFailed(true)
      return
    }
    setFinished(null)
    await load()
  }

  return (
    <div className="container mx-auto max-w-3xl px-4 py-2">
      <Button asChild variant="ghost" size="sm" className="mb-3">
        <Link href="/books"><ArrowLeft className="mr-2 h-4 w-4" />{t("books.allBooks")}</Link>
      </Button>

      <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold"><span className="fun-heading">{book.title}</span></h1>
          <p className="text-muted-foreground">
            {book.author && <>{book.author} · </>}
            {language?.flag} {language?.name ?? book.language}
          </p>
        </div>
        <Select
          value={book.status}
          onValueChange={async (status) => {
            await updateBook(book.id, { status: status as BookStatus })
            await load()
          }}
        >
          <SelectTrigger className="w-full sm:w-40" aria-label={t("books.statusLabel")}><SelectValue /></SelectTrigger>
          <SelectContent>
            {(["reading", "paused", "finished"] as const).map((status) => (
              <SelectItem key={status} value={status}>{t(`books.status_${status}`)}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </header>

      {finished ? (
        <BookTriage
          book={book}
          session={finished}
          onDone={() => {
            setFinished(null)
            void load()
          }}
        />
      ) : session ? (
        <BookSession
          key={session.id}
          book={book}
          session={session}
          initialMarks={session.marks}
          onEnded={(summary) => {
            setFinished(summary)
            void load()
          }}
        />
      ) : (
        <Card className="rounded-3xl" data-testid="start-reading">
          <CardContent className="space-y-4 p-6">
            <h2 className="flex items-center gap-2 text-2xl font-bold"><BookOpen className="h-6 w-6" />{t("books.startTitle")}</h2>
            <p className="text-muted-foreground">{t("books.startBody")}</p>
            <div className="flex flex-wrap items-center gap-3">
              <Input
                value={startPage}
                onChange={(event) => setStartPage(event.target.value.replace(/\D/g, ""))}
                inputMode="numeric"
                placeholder={t("books.startPagePlaceholder")}
                aria-label={t("books.startPageLabel")}
                className="w-40"
              />
              <Button onClick={() => void start()}>{t("books.startReading")}</Button>
              {lastEnded && (
                <Button variant="outline" onClick={() => setFinished(lastEnded)} data-testid="finish-last">
                  <ListChecks className="mr-2 h-4 w-4" />{t("books.finishLast")}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {!finished && (
        <>
          <section className="mt-8 flex flex-wrap gap-3">
            <Button asChild variant="outline"><Link href={`/books/${book.id}/glossary`}><BookMarked className="mr-2 h-4 w-4" />{t("books.openGlossary")}</Link></Button>
            <Button asChild variant="outline"><Link href={`/entries/new?book=${book.id}`}><Edit className="mr-2 h-4 w-4" />{t("books.writeAbout")}</Link></Button>
          </section>

          {progress && (
            <section className="mt-8" aria-labelledby="progress-title">
              <div className="mb-3 flex items-center gap-3">
                <h2 id="progress-title" className="text-2xl font-bold">{t("books.progressTitle")}</h2>
                <Badge variant="outline">{t("books.sessionsCount", { count: progress.sessions.length })}</Badge>
              </div>
              <WordsPerPageChart progress={progress} />
            </section>
          )}
        </>
      )}
    </div>
  )
}
