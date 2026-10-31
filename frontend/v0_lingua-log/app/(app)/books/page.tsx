"use client"

import { useCallback, useEffect, useState, type FormEvent } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { BookMarked, Library, Plus } from "lucide-react"

import { LoadingSpinner } from "@/components/loading-spinner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useLocale } from "@/i18n/LocaleProvider"
import { resolveLanguage } from "@/i18n/languages"
import { createBook, getUserSettings, listBooks, type BookSummary } from "@/lib/api"
import { BAND_CLASS } from "@/lib/books"
import { studiedLanguages } from "@/lib/studied-languages"

function languageLabel(code: string) {
  const language = resolveLanguage(code)
  return `${language?.flag || "🌐"} ${language?.name || code.toUpperCase()}`
}

/** A tiny line of words-per-page, one point per finished session. It should fall. */
function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null
  const top = Math.max(...values, 1)
  const points = values
    .map((value, index) => `${(index / (values.length - 1)) * 80 + 2},${26 - (value / top) * 24}`)
    .join(" ")
  return (
    <svg viewBox="0 0 84 28" className="h-7 w-20 text-fun-purple" role="img" aria-label={values.join(", ")} data-testid="sparkline">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function BooksPage() {
  const { t } = useLocale()
  const [languages, setLanguages] = useState<string[]>([])
  const [books, setBooks] = useState<BookSummary[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [title, setTitle] = useState("")
  const [author, setAuthor] = useState("")
  const [language, setLanguage] = useState("es")
  const [adding, setAdding] = useState(false)
  const [addFailed, setAddFailed] = useState(false)

  const load = useCallback(async () => {
    try {
      setBooks(await listBooks())
      setFailed(false)
    } catch {
      setFailed(true)
    }
  }, [])

  useEffect(() => {
    getUserSettings()
      .then((settings) => {
        const studied = studiedLanguages(settings)
        setLanguages(studied)
        setLanguage(studied[0])
      })
      .catch(() => setLanguages(["es"]))
    void load()
  }, [load])

  const add = async (event: FormEvent) => {
    event.preventDefault()
    if (!title.trim()) return
    setAddFailed(false)
    try {
      await createBook({ title: title.trim(), author: author.trim() || undefined, language })
      setTitle("")
      setAuthor("")
      setAdding(false)
      await load()
    } catch {
      setAddFailed(true)
    }
  }

  return (
    <div className="container mx-auto max-w-3xl px-4 py-2">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 space-y-2">
        <h1 className="text-4xl font-bold"><span className="fun-heading">{t("books.title")}</span></h1>
        <p className="text-lg text-muted-foreground">{t("books.intro")}</p>
      </motion.div>

      {adding ? (
        <form onSubmit={add} className="mb-6 space-y-3 rounded-3xl border bg-card p-4" data-testid="add-book">
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder={t("books.titlePlaceholder")} aria-label={t("books.titleLabel")} className="sm:flex-1" autoFocus />
            <Input value={author} onChange={(event) => setAuthor(event.target.value)} placeholder={t("books.authorPlaceholder")} aria-label={t("books.authorLabel")} className="sm:w-56" />
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger className="sm:w-48" aria-label={t("books.languageLabel")}><SelectValue /></SelectTrigger>
              <SelectContent>
                {(languages.length ? languages : ["es"]).map((code) => (
                  <SelectItem key={code} value={code}>{languageLabel(code)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {addFailed && <p role="alert" className="text-sm text-red-600">{t("books.addFailed")}</p>}
          <div className="flex gap-2">
            <Button type="submit" disabled={!title.trim()}>{t("books.addBook")}</Button>
            <Button type="button" variant="ghost" onClick={() => setAdding(false)}>{t("common.cancel")}</Button>
          </div>
        </form>
      ) : (
        <Button className="mb-6" onClick={() => setAdding(true)}><Plus className="mr-2 h-4 w-4" />{t("books.newBook")}</Button>
      )}

      {failed && (
        <div className="py-8 text-center" role="alert">
          <p className="mb-3 text-muted-foreground">{t("books.loadFailed")}</p>
          <Button variant="outline" onClick={() => void load()}>{t("books.retry")}</Button>
        </div>
      )}

      {!failed && books === null && <div className="flex h-40 items-center justify-center"><LoadingSpinner text={t("books.loading")} /></div>}

      {books && books.length === 0 && (
        <div className="py-12 text-center" data-testid="books-empty">
          <Library className="mx-auto mb-4 h-14 w-14 text-fun-purple/70" />
          <p className="text-lg font-medium">{t("books.emptyTitle")}</p>
          <p className="mt-2 text-muted-foreground">{t("books.emptyBody")}</p>
        </div>
      )}

      <ul className="space-y-4">
        {books?.map((book) => (
          <li key={book.id}>
            <Card className="rounded-3xl" data-testid="book-card">
              <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <h2 className="truncate text-xl font-bold">{book.title}</h2>
                  <p className="text-sm text-muted-foreground">
                    {book.author && <>{book.author} · </>}
                    {languageLabel(book.language)}
                  </p>
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <Badge variant="outline">{t(`books.status_${book.status}`)}</Badge>
                    <span className="text-sm text-muted-foreground">
                      {t("books.cardStats", { sessions: book.sessions, words: book.words_marked })}
                    </span>
                    {book.last_band && <Badge variant="outline" className={BAND_CLASS[book.last_band]}>{t(`books.band_${book.last_band}`)}</Badge>}
                    <Sparkline values={book.rate_series} />
                  </div>
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  <Button asChild><Link href={`/books/${book.id}`}>{book.open_session_id ? t("books.continueReading") : t("books.open")}</Link></Button>
                  <Button asChild variant="outline"><Link href={`/books/${book.id}/glossary`}><BookMarked className="mr-2 h-4 w-4" />{t("books.glossary")}</Link></Button>
                </div>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  )
}
