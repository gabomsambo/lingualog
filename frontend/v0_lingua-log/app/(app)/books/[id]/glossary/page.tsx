"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { ArrowLeft, Eye, Printer } from "lucide-react"

import { LoadingSpinner } from "@/components/loading-spinner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useLocale } from "@/i18n/LocaleProvider"
import { getBookGlossary, type BookGlossary, type GlossaryWord } from "@/lib/api"
import { statusClass } from "@/lib/review"

type Recall = "remembered" | "not_yet"

function pagesLabel(pages: number[]): string {
  return pages.join(", ")
}

/** The book's index card: every marked word with its sentence and pages, printable, with a re-read self-quiz. */
export default function BookGlossaryPage() {
  const { t } = useLocale()
  const { id } = useParams<{ id: string }>()
  const [glossary, setGlossary] = useState<BookGlossary | null>(null)
  const [failed, setFailed] = useState(false)
  const [quiz, setQuiz] = useState(false)
  const [revealed, setRevealed] = useState<Set<string>>(new Set())
  const [recall, setRecall] = useState<Record<string, Recall>>({})

  useEffect(() => {
    getBookGlossary(id).then(setGlossary).catch(() => setFailed(true))
  }, [id])

  const words = glossary?.words ?? []
  const remembered = useMemo(() => Object.values(recall).filter((value) => value === "remembered").length, [recall])

  if (failed) return <p className="py-12 text-center text-muted-foreground" role="alert">{t("books.loadFailed")}</p>
  if (!glossary) return <div className="flex h-64 items-center justify-center"><LoadingSpinner text={t("books.loading")} /></div>

  const reveal = (key: string) => setRevealed((current) => new Set(current).add(key))
  const toggleQuiz = () => {
    setQuiz((on) => !on)
    setRevealed(new Set())
    setRecall({})
  }

  return (
    <div className="container mx-auto max-w-3xl px-4 py-2 print:max-w-none print:p-0" data-testid="glossary">
      <Button asChild variant="ghost" size="sm" className="mb-3 print:hidden">
        <Link href={`/books/${glossary.book.id}`}><ArrowLeft className="mr-2 h-4 w-4" />{glossary.book.title}</Link>
      </Button>

      <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold print:text-xl"><span className="fun-heading">{t("books.glossaryTitle", { title: glossary.book.title })}</span></h1>
          {glossary.book.author && <p className="text-muted-foreground">{glossary.book.author}</p>}
        </div>
        <div className="flex flex-wrap gap-2 print:hidden">
          <Button variant={quiz ? "default" : "outline"} onClick={toggleQuiz} aria-pressed={quiz} data-testid="quiz-toggle">
            <Eye className="mr-2 h-4 w-4" />{quiz ? t("books.quizOff") : t("books.quizOn")}
          </Button>
          <Button variant="outline" onClick={() => window.print()}><Printer className="mr-2 h-4 w-4" />{t("books.print")}</Button>
        </div>
      </header>

      {quiz && (
        <p className="mb-4 rounded-xl bg-fun-yellow/15 p-3 text-sm print:hidden" role="status" data-testid="quiz-score">
          {t("books.quizScore", { remembered, total: words.length })}
        </p>
      )}

      {words.length === 0 ? (
        <p className="py-12 text-center text-muted-foreground" data-testid="glossary-empty">{t("books.glossaryEmpty")}</p>
      ) : (
        <ul className="divide-y rounded-2xl border bg-card print:columns-2 print:gap-6 print:divide-y-0 print:border-0" data-testid="glossary-list">
          {words.map((word) => (
            <GlossaryRow
              key={word.key}
              word={word}
              quiz={quiz}
              revealed={!quiz || revealed.has(word.key)}
              recall={recall[word.key]}
              onReveal={() => reveal(word.key)}
              onRecall={(value) => setRecall((current) => ({ ...current, [word.key]: value }))}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

function GlossaryRow({
  word,
  quiz,
  revealed,
  recall,
  onReveal,
  onRecall,
}: {
  word: GlossaryWord
  quiz: boolean
  revealed: boolean
  recall?: Recall
  onReveal: () => void
  onRecall: (value: Recall) => void
}) {
  const { t } = useLocale()
  const sentence = word.sentences[0]
  return (
    <li className="break-inside-avoid space-y-1 p-4 print:px-0 print:py-2" data-testid="glossary-row">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <span className="font-serif text-xl">{word.lemma}</span>
        {word.surfaces.some((surface) => surface.toLocaleLowerCase() !== word.lemma.toLocaleLowerCase()) && (
          <span className="text-sm text-muted-foreground">{word.surfaces.join(", ")}</span>
        )}
        {word.pages.length > 0 && <span className="text-sm text-muted-foreground">{t("books.pagesShort", { pages: pagesLabel(word.pages) })}</span>}
        {word.times_marked > 1 && <Badge variant="outline" className="print:hidden">{t("books.markedTimes", { count: word.times_marked })}</Badge>}
        {word.status && <Badge variant="outline" className={`print:hidden ${statusClass(word.status)}`}>{t(`vocabulary.status_${word.status}`)}</Badge>}
      </div>
      {sentence && <p className="text-sm italic text-muted-foreground">{sentence.sentence}</p>}
      {revealed ? (
        word.has_card ? (
          <p data-testid="glossary-meaning">
            {word.meaning}
            {word.gloss && <span className="ml-2 text-fun-purple">{word.gloss}</span>}
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">{t("books.noMeaningYet")}</p>
        )
      ) : (
        <Button size="sm" variant="outline" onClick={onReveal} className="print:hidden">{t("books.showMeaning")}</Button>
      )}
      {quiz && revealed && (
        <div className="flex gap-2 print:hidden">
          <Button size="sm" variant={recall === "remembered" ? "default" : "outline"} onClick={() => onRecall("remembered")}>{t("books.remembered")}</Button>
          <Button size="sm" variant={recall === "not_yet" ? "secondary" : "outline"} onClick={() => onRecall("not_yet")}>{t("books.notYet")}</Button>
        </div>
      )}
    </li>
  )
}
