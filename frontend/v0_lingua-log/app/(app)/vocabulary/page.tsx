"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import {
  BookOpen,
  Download,
  FileSpreadsheet,
  Hash,
  Languages,
  Layers,
  ListChecks,
  Search,
  Trash2,
  X,
} from "lucide-react"

import { LoadingSpinner } from "@/components/loading-spinner"
import { WordCard } from "@/components/word-card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useToast } from "@/components/ui/use-toast"
import { useLocale } from "@/i18n/LocaleProvider"
import { resolveLanguage } from "@/i18n/languages"
import {
  deleteVocabularyItem,
  exportVocabulary,
  getVocabularyItems,
  getVocabularyLists,
  type UserVocabularyItemResponse,
  type VocabularyLists,
  type VocabularyQuery,
} from "@/lib/api"
import { statusClass } from "@/lib/review"

function languageBadge(code: string) {
  const language = resolveLanguage(code)
  return `${language?.flag || "🌐"} ${language?.name || code.toUpperCase()}`
}

interface ListSelection extends VocabularyQuery {
  id: string
}

const ALL_WORDS: ListSelection = { id: "all" }

function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function ListButton({
  active,
  label,
  count,
  onClick,
}: {
  active: boolean
  label: string
  count?: number
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`flex w-full items-center justify-between gap-2 rounded-xl px-3 py-2 text-left text-sm transition-colors ${
        active ? "bg-fun-purple/15 font-medium text-fun-purple" : "hover:bg-muted"
      }`}
    >
      <span className="truncate">{label}</span>
      {count !== undefined && <span className="text-xs text-muted-foreground">{count}</span>}
    </button>
  )
}

export default function VocabularyPage() {
  const { toast } = useToast()
  const { t } = useLocale()
  const [items, setItems] = useState<UserVocabularyItemResponse[]>([])
  const [lists, setLists] = useState<VocabularyLists | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [language, setLanguage] = useState("all")
  const [selection, setSelection] = useState<ListSelection>(ALL_WORDS)
  const [selected, setSelected] = useState<UserVocabularyItemResponse | null>(null)
  const [exporting, setExporting] = useState<"csv" | "apkg" | null>(null)

  const query: VocabularyQuery = useMemo(() => {
    const { id, ...rest } = selection
    void id
    return rest
  }, [selection])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [rows, listData] = await Promise.all([
        getVocabularyItems(language === "all" ? undefined : language, query),
        getVocabularyLists(language === "all" ? undefined : language),
      ])
      setItems(rows || [])
      setLists(listData)
    } catch (error) {
      toast({
        title: t("vocabulary.errorFetchingVocabulary"),
        description: error instanceof Error ? error.message : "",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language, selection])

  useEffect(() => {
    void load()
  }, [load])

  const languages = useMemo(
    () => ["all", ...Array.from(new Set(items.map((item) => item.language))).sort()],
    [items],
  )

  const filtered = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase()
    return items.filter((item) => {
      const matchesLanguage = language === "all" || item.language === language
      const haystack = [item.lemma, item.term, item.sense, item.definition, item.example_sentence]
        .filter(Boolean)
        .join(" ")
        .toLocaleLowerCase()
      return matchesLanguage && (!needle || haystack.includes(needle))
    })
  }, [items, language, search])

  const remove = async (item: UserVocabularyItemResponse) => {
    try {
      await deleteVocabularyItem(item.id)
      setItems((current) => current.filter((candidate) => candidate.id !== item.id))
      toast({
        title: t("vocabulary.vocabularyItemDeleted"),
        description: `“${item.lemma || item.term}” ${t("vocabulary.vocabularyItemRemoved")}`,
      })
      void load()
    } catch (error) {
      toast({
        title: t("vocabulary.errorDeletingItem"),
        description: error instanceof Error ? error.message : "",
        variant: "destructive",
      })
    }
  }

  const replace = (updated: UserVocabularyItemResponse) => {
    setItems((current) => current.map((item) => item.id === updated.id ? updated : item))
    setSelected(updated)
  }

  const runExport = async (format: "csv" | "apkg") => {
    setExporting(format)
    try {
      const blob = await exportVocabulary(format, language === "all" ? undefined : language, query)
      download(blob, `lingualog-vocabulary.${format}`)
    } catch (error) {
      toast({
        title: t("vocabulary.exportFailed"),
        description: error instanceof Error ? error.message : "",
        variant: "destructive",
      })
    } finally {
      setExporting(null)
    }
  }

  const smartCounts = new Map((lists?.smart ?? []).map((row) => [row.id, row.count]))

  return (
    <div className="container mx-auto max-w-6xl px-4 py-8">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="text-4xl font-bold"><span className="fun-heading">{t("vocabulary.myVocabulary")}</span> 📖</h1>
        <p className="mt-2 text-xl text-muted-foreground">{t("vocabulary.reviewAndManage")}</p>
      </motion.div>

      <div className="mb-8 flex flex-col gap-4 rounded-xl border bg-card p-4 shadow-sm sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("vocabulary.searchPlaceholder")}
            className="h-12 pl-10"
          />
          {search && (
            <Button variant="ghost" size="icon" className="absolute right-1 top-1/2 -translate-y-1/2" onClick={() => setSearch("")}>
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
        <Select value={language} onValueChange={setLanguage}>
          <SelectTrigger className="h-12 w-full sm:w-56">
            <Languages className="mr-2 h-5 w-5 text-muted-foreground" />
            <SelectValue placeholder={t("vocabulary.filterByLanguage")} />
          </SelectTrigger>
          <SelectContent>
            {languages.map((code) => (
              <SelectItem value={code} key={code}>
                {code === "all" ? t("vocabulary.allLanguages") : languageBadge(code)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="h-12"
            disabled={exporting !== null}
            onClick={() => runExport("csv")}
          >
            <FileSpreadsheet className="mr-2 h-4 w-4" />
            {t("vocabulary.exportCsv")}
          </Button>
          <Button
            variant="outline"
            className="h-12"
            disabled={exporting !== null}
            onClick={() => runExport("apkg")}
          >
            <Download className="mr-2 h-4 w-4" />
            {t("vocabulary.exportAnki")}
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        <aside className="w-full shrink-0 space-y-4 lg:w-64">
          <div>
            <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <ListChecks className="mr-1 inline h-3.5 w-3.5" />
              {t("vocabulary.listsTitle")}
            </p>
            <ListButton
              active={selection.id === "all"}
              label={t("vocabulary.listAll")}
              count={lists?.total}
              onClick={() => setSelection(ALL_WORDS)}
            />
            <ListButton
              active={selection.id === "due"}
              label={t("vocabulary.listDue")}
              count={smartCounts.get("due")}
              onClick={() => setSelection({ id: "due", list: "due" })}
            />
            <ListButton
              active={selection.id === "never_used"}
              label={t("vocabulary.listNeverUsed")}
              count={smartCounts.get("never_used")}
              onClick={() => setSelection({ id: "never_used", list: "never_used" })}
            />
          </div>

          {(lists?.tags ?? []).length > 0 && (
            <div>
              <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <Hash className="mr-1 inline h-3.5 w-3.5" />
                {t("vocabulary.listTags")}
              </p>
              {(lists?.tags ?? []).map((tag) => (
                <ListButton
                  key={tag.id}
                  active={selection.id === tag.id}
                  label={tag.name}
                  count={tag.count}
                  onClick={() => setSelection({ id: tag.id, tag: tag.name })}
                />
              ))}
            </div>
          )}

          {(lists?.entries ?? []).length > 0 && (
            <div>
              <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <BookOpen className="mr-1 inline h-3.5 w-3.5" />
                {t("vocabulary.listFromEntries")}
              </p>
              {(lists?.entries ?? []).map((entry) => (
                <ListButton
                  key={entry.id}
                  active={selection.id === entry.id}
                  label={entry.title || t("vocabulary.listEntryFallback", { date: entry.date || "" })}
                  count={entry.count}
                  onClick={() => setSelection({ id: entry.id, entry_id: entry.entry_id })}
                />
              ))}
            </div>
          )}

          {(lists?.books ?? []).length > 0 && (
            <div>
              <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <Layers className="mr-1 inline h-3.5 w-3.5" />
                {t("vocabulary.listFromBooks")}
              </p>
              {(lists?.books ?? []).map((book) => (
                <ListButton
                  key={book.id}
                  active={selection.id === book.id}
                  label={book.title || book.book_id}
                  count={book.count}
                  onClick={() => setSelection({ id: book.id, book_id: book.book_id })}
                />
              ))}
            </div>
          )}
        </aside>

        <div className="min-w-0 flex-1">
          {loading ? (
            <div className="flex h-64 items-center justify-center"><LoadingSpinner text={t("vocabulary.loadingVocabulary")} /></div>
          ) : filtered.length === 0 ? (
            <div className="py-16 text-center">
              <BookOpen className="mx-auto mb-6 h-16 w-16 text-fun-purple/70" />
              <h2 className="text-2xl font-bold">{t("vocabulary.noVocabularyFound")}</h2>
              <p className="mt-3 text-muted-foreground">
                {items.length || selection.id !== "all"
                  ? t("vocabulary.tryAdjustingSearch")
                  : t("vocabulary.startSavingWords")}
              </p>
              <Button asChild className="mt-6 rounded-full"><Link href="/entries/new">{t("vocabulary.writeNewEntry")}</Link></Button>
            </div>
          ) : (
            <motion.div layout className="grid gap-6 md:grid-cols-2">
              {filtered.map((item) => (
                <Card key={item.id} className="flex h-full flex-col rounded-2xl">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-3">
                      <CardTitle className="font-serif text-xl">{item.lemma || item.term}</CardTitle>
                      <Badge variant="outline">{languageBadge(item.language)}</Badge>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge className={statusClass(item.status)}>{t(`vocabulary.status_${item.status || "new"}`)}</Badge>
                      {item.review?.at_risk && (
                        <span
                          className="inline-flex items-center gap-1 text-xs font-medium text-red-600"
                          title={t("vocabulary.reviewAtRiskTitle")}
                          data-testid="at-risk-flag"
                        >
                          <span className="inline-block h-2 w-2 rounded-full bg-red-500" aria-hidden />
                          {t("vocabulary.reviewAtRisk")}
                        </span>
                      )}
                      {item.card?.part_of_speech && <span className="text-xs text-muted-foreground">{item.card.part_of_speech}</span>}
                      {item.review && item.status === "learning" && (
                        <span className="text-xs text-muted-foreground">
                          {t("vocabulary.reviewDueOn", { date: new Date(item.review.due).toLocaleDateString() })}
                        </span>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="flex-1 space-y-3 text-sm">
                    <p>{item.card?.sense_in_context || item.sense || item.definition}</p>
                    {item.example_sentence && <p className="rounded-xl bg-muted/60 p-3 italic">“{item.example_sentence}”</p>}
                  </CardContent>
                  <CardFooter className="gap-2">
                    <Button className="flex-1" variant="outline" onClick={() => setSelected(item)}>
                      <BookOpen className="mr-2 h-4 w-4" /> {t("vocabulary.openCard")}
                    </Button>
                    <Button variant="ghost" size="icon" className="text-destructive" onClick={() => remove(item)}>
                      <Trash2 className="h-4 w-4" /><span className="sr-only">{t("vocabulary.remove")}</span>
                    </Button>
                  </CardFooter>
                </Card>
              ))}
            </motion.div>
          )}
        </div>
      </div>

      <WordCard
        item={selected}
        open={selected !== null}
        onOpenChange={(open) => !open && setSelected(null)}
        onUpdated={replace}
      />
    </div>
  )
}
