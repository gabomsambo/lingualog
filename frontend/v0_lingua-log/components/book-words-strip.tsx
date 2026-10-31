"use client"

import { useEffect, useState } from "react"
import { BookOpen } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { useLocale } from "@/i18n/LocaleProvider"
import { getWritingWords, type WritingWords } from "@/lib/api"
import { statusClass } from "@/lib/review"

/** "Write about what you read": this week's words from the book named in `?book=`, as chips above the editor. */
export function BookWordsStrip() {
  const { t } = useLocale()
  const [writing, setWriting] = useState<WritingWords | null>(null)

  useEffect(() => {
    const bookId = new URLSearchParams(window.location.search).get("book")
    if (!bookId) return
    getWritingWords(bookId).then(setWriting).catch(() => setWriting(null))
  }, [])

  if (!writing || writing.words.length === 0) return null

  return (
    <section className="mb-6 rounded-3xl border border-fun-purple/30 bg-fun-purple/5 p-4" data-testid="book-words-strip">
      <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold">
        <BookOpen className="h-5 w-5" /> {t("books.writeAboutTitle", { title: writing.book.title })}
      </h2>
      <p className="mb-3 text-sm text-muted-foreground">{t("books.writeAboutHint")}</p>
      <ul className="flex flex-wrap gap-2">
        {writing.words.map((word) => (
          <li key={word.lemma}>
            <Badge variant="outline" className={`text-base ${statusClass(word.status ?? "new")}`} title={word.gloss || undefined}>
              {word.lemma}
            </Badge>
          </li>
        ))}
      </ul>
    </section>
  )
}
