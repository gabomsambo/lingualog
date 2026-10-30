"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { BookOpen, Languages, Search, Trash2, X } from "lucide-react"

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
  getVocabularyItems,
  type UserVocabularyItemResponse,
} from "@/lib/api"

function languageBadge(code: string) {
  const language = resolveLanguage(code)
  return `${language?.flag || "🌐"} ${language?.name || code.toUpperCase()}`
}

export default function VocabularyPage() {
  const { toast } = useToast()
  const { t } = useLocale()
  const [items, setItems] = useState<UserVocabularyItemResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [language, setLanguage] = useState("all")
  const [selected, setSelected] = useState<UserVocabularyItemResponse | null>(null)

  useEffect(() => {
    getVocabularyItems()
      .then((result) => setItems(result || []))
      .catch((error) => {
        toast({
          title: t("vocabulary.errorFetchingVocabulary"),
          description: error instanceof Error ? error.message : "",
          variant: "destructive",
        })
      })
      .finally(() => setLoading(false))
  }, [])

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

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
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
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center"><LoadingSpinner text={t("vocabulary.loadingVocabulary")} /></div>
      ) : filtered.length === 0 ? (
        <div className="py-16 text-center">
          <BookOpen className="mx-auto mb-6 h-16 w-16 text-fun-purple/70" />
          <h2 className="text-2xl font-bold">{t("vocabulary.noVocabularyFound")}</h2>
          <p className="mt-3 text-muted-foreground">
            {items.length ? t("vocabulary.tryAdjustingSearch") : t("vocabulary.startSavingWords")}
          </p>
          <Button asChild className="mt-6 rounded-full"><Link href="/entries/new">{t("vocabulary.writeNewEntry")}</Link></Button>
        </div>
      ) : (
        <motion.div layout className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((item) => (
            <Card key={item.id} className="flex h-full flex-col rounded-2xl">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <CardTitle className="font-serif text-xl">{item.lemma || item.term}</CardTitle>
                  <Badge variant="outline">{languageBadge(item.language)}</Badge>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="purple">{t(`vocabulary.status_${item.status || "new"}`)}</Badge>
                  {item.card?.part_of_speech && <span className="text-xs text-muted-foreground">{item.card.part_of_speech}</span>}
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

      <WordCard
        item={selected}
        open={selected !== null}
        onOpenChange={(open) => !open && setSelected(null)}
        onUpdated={replace}
      />
    </div>
  )
}
