"use client"

import { useEffect, useState, type ReactNode } from "react"
import Link from "next/link"
import { BookOpen, RefreshCw, Save, Volume2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/components/ui/use-toast"
import { useLocale } from "@/i18n/LocaleProvider"
import {
  retryVocabularyCard,
  postSupportEvent,
  updateVocabularyItem,
  type UserVocabularyItemResponse,
} from "@/lib/api"

interface WordCardProps {
  item: UserVocabularyItemResponse | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onUpdated?: (item: UserVocabularyItemResponse) => void
}

function speak(text: string, language: string) {
  if (typeof window === "undefined" || !("speechSynthesis" in window) || !text) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = language
  window.speechSynthesis.speak(utterance)
}

function HighlightedSentence({ sentence, surface }: { sentence: string; surface: string }) {
  if (!surface || !sentence.toLocaleLowerCase().includes(surface.toLocaleLowerCase())) {
    return <>{sentence}</>
  }
  const start = sentence.toLocaleLowerCase().indexOf(surface.toLocaleLowerCase())
  return (
    <>
      {sentence.slice(0, start)}
      <mark className="rounded bg-fun-yellow/30 px-0.5 font-semibold text-foreground">
        {sentence.slice(start, start + surface.length)}
      </mark>
      {sentence.slice(start + surface.length)}
    </>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2 border-t pt-5">
      <h3 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">{title}</h3>
      {children}
    </section>
  )
}

export function WordCard({ item, open, onOpenChange, onUpdated }: WordCardProps) {
  const { t } = useLocale()
  const { toast } = useToast()
  const [current, setCurrent] = useState(item)
  const [note, setNote] = useState(item?.note || "")
  const [tags, setTags] = useState((item?.tags || []).join(", "))
  const [glossRevealed, setGlossRevealed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [retrying, setRetrying] = useState(false)

  useEffect(() => {
    setCurrent(item)
    setNote(item?.note || "")
    setTags((item?.tags || []).join(", "))
    setGlossRevealed(false)
  }, [item])

  const card = current?.card
  const vocabDef = current?.card_policy?.vocab_def || "l1"
  const showGloss = vocabDef === "l1" || vocabDef === "l1_plus_l2" || glossRevealed

  const commit = (updated: UserVocabularyItemResponse) => {
    setCurrent(updated)
    onUpdated?.(updated)
  }

  const saveNotes = async () => {
    if (!current) return
    setSaving(true)
    try {
      const updated = await updateVocabularyItem(current.id, {
        note,
        tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
      })
      commit(updated)
      toast({ title: t("vocabulary.notesSaved") })
    } catch {
      toast({ title: t("vocabulary.notesFailed"), variant: "destructive" })
    } finally {
      setSaving(false)
    }
  }

  const retry = async () => {
    if (!current) return
    setRetrying(true)
    try {
      commit(await retryVocabularyCard(current.id))
    } catch {
      toast({ title: t("vocabulary.cardRetryFailed"), variant: "destructive" })
    } finally {
      setRetrying(false)
    }
  }

  const revealGloss = () => {
    setGlossRevealed(true)
    if (!current) return
    void postSupportEvent({
      kind: "reveal_gloss",
      entry_id: current.entry_id,
      immersion_level: current.card_policy?.level,
      l2: current.language,
    }).catch(() => undefined)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
        {current && (
          <>
            <SheetHeader className="pr-8">
              <div className="flex flex-wrap items-center gap-2">
                <SheetTitle className="font-serif text-3xl">{current.lemma || current.term}</SheetTitle>
                <Badge variant="purple">{t(`vocabulary.status_${current.status || "new"}`)}</Badge>
              </div>
              <SheetDescription>
                {[card?.part_of_speech || current.part_of_speech, card?.gender].filter(Boolean).join(" · ")}
              </SheetDescription>
            </SheetHeader>

            {!card || current.card_status !== "ok" ? (
              <div className="mt-8 rounded-2xl border border-dashed p-6 text-center">
                <p className="text-sm text-muted-foreground">{t("vocabulary.cardUnavailable")}</p>
                <Button className="mt-4" variant="outline" onClick={retry} disabled={retrying}>
                  <RefreshCw className={`mr-2 h-4 w-4 ${retrying ? "animate-spin" : ""}`} />
                  {retrying ? t("vocabulary.retryingCard") : t("vocabulary.retryCard")}
                </Button>
              </div>
            ) : (
              <div className="mt-6 space-y-5" data-testid="word-card-content">
                <Section title={t("vocabulary.hereTitle")}>
                  <p className="text-base leading-relaxed">
                    <HighlightedSentence
                      sentence={current.example_sentence || card.surface}
                      surface={card.surface}
                    />
                  </p>
                  <p className="font-medium">{card.sense_in_context}</p>
                </Section>

                <Section title={t("vocabulary.meaningTitle")}>
                  {card.gloss_l1 && showGloss && (
                    <p className="text-xl font-bold text-fun-purple" data-testid="word-card-gloss">
                      {card.gloss_l1}
                    </p>
                  )}
                  {card.gloss_l1 && !showGloss && (
                    <Button variant="outline" size="sm" onClick={revealGloss}>
                      {t("vocabulary.revealGloss")}
                    </Button>
                  )}
                </Section>

                <Section title={t("vocabulary.hearTitle")}>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" size="sm" onClick={() => speak(card.lemma, current.language)}>
                      <Volume2 className="mr-2 h-4 w-4" /> {t("vocabulary.hearWord")}
                    </Button>
                    {current.example_sentence && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => speak(current.example_sentence || "", current.language)}
                      >
                        <Volume2 className="mr-2 h-4 w-4" /> {t("vocabulary.hearSentence")}
                      </Button>
                    )}
                  </div>
                </Section>

                <Section title={t("vocabulary.examplesTitle")}>
                  <ol className="space-y-2">
                    {card.examples.map((example, index) => (
                      <li key={`${example}-${index}`} className="rounded-xl bg-muted/60 p-3">
                        {example}
                      </li>
                    ))}
                  </ol>
                </Section>

                {card.other_senses.length > 0 && (
                  <Section title={t("vocabulary.otherMeaningsTitle")}>
                    <div className="space-y-3">
                      {card.other_senses.map((sense, index) => (
                        <div key={`${sense.meaning}-${index}`}>
                          <p className="font-medium">{sense.meaning}</p>
                          <p className="text-sm italic text-muted-foreground">{sense.example}</p>
                        </div>
                      ))}
                    </div>
                  </Section>
                )}

                <Section title={t("vocabulary.familyTitle")}>
                  <div className="flex flex-wrap gap-2">
                    {[...card.collocations, ...card.word_family].map((term, index) => (
                      <Badge key={`${term}-${index}`} variant="outline">{term}</Badge>
                    ))}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {[card.register, card.cefr, card.frequency_band].filter(Boolean).join(" · ")}
                  </p>
                </Section>

                {card.common_mistake && (
                  <Section title={t("vocabulary.watchOutTitle")}>
                    <p>{card.common_mistake}</p>
                  </Section>
                )}

                {card.memory_hook && (
                  <Section title={t("vocabulary.rememberTitle")}>
                    <p>{card.memory_hook}</p>
                  </Section>
                )}

                <Section title={t("vocabulary.trailTitle")}>
                  {current.entry_id && (
                    <Link className="inline-flex items-center text-sm text-fun-blue hover:underline" href={`/entries/${current.entry_id}`}>
                      <BookOpen className="mr-2 h-4 w-4" /> {t("vocabulary.sourceEntry")}
                    </Link>
                  )}
                  <Textarea
                    aria-label={t("vocabulary.noteLabel")}
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    placeholder={t("vocabulary.notePlaceholder")}
                  />
                  <Input
                    aria-label={t("vocabulary.tagsLabel")}
                    value={tags}
                    onChange={(event) => setTags(event.target.value)}
                    placeholder={t("vocabulary.tagsPlaceholder")}
                  />
                  <Button onClick={saveNotes} disabled={saving}>
                    <Save className="mr-2 h-4 w-4" />
                    {saving ? t("vocabulary.savingNotes") : t("vocabulary.saveNotes")}
                  </Button>
                </Section>
              </div>
            )}
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
