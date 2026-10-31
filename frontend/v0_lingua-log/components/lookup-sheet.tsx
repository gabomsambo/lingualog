"use client"

import { useEffect, useState } from "react"
import { BookmarkPlus, Loader2, Search } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { useToast } from "@/components/ui/use-toast"
import {
  addVocabularyItem,
  lookupWord,
  updateVocabularyItem,
  type LookupResult,
  type VocabularyStatus,
} from "@/lib/api"

export interface LookupContext {
  text: string
  sentence?: string
  language: string
  source: "entry" | "manual" | "book_session"
  sourceId?: string
  /** Book page, for a lookup made in a reading session. */
  page?: number
  kind?: "lookup" | "entry_text" | "entry_fix" | "entry_rewrite"
}

interface LookupSheetProps {
  context: LookupContext | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function LookupSheet({ context, open, onOpenChange }: LookupSheetProps) {
  const { toast } = useToast()
  const [result, setResult] = useState<LookupResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [sentenceField, setSentenceField] = useState("")

  // A top search looks up the bare word as its own "sentence": ask for the real one.
  const keptSentence =
    context?.sentence && context.sentence.trim() !== context.text.trim() ? context.sentence : undefined

  useEffect(() => {
    if (!open || !context) return
    setLoading(true)
    setResult(null)
    setSentenceField("")
    void lookupWord({
      text: context.text,
      sentence: context.sentence,
      language: context.language,
      source: context.source,
      source_id: context.sourceId,
      kind: context.kind,
      page: context.page,
    }).then(setResult).catch(() => {
      toast({ title: "Lookup failed", description: "Try again in a moment.", variant: "destructive" })
    }).finally(() => setLoading(false))
  }, [context, open])

  const save = async () => {
    if (!result) return
    setSaving(true)
    try {
      const saved = result.saved_item || await addVocabularyItem({
        term: result.text,
        language: result.language,
        example_sentence: sentenceField.trim() || keptSentence,
        entry_id: context?.source === "entry" ? context.sourceId : undefined,
        encounter_id: result.encounter_id,
      })
      setResult({ ...result, saved_item: saved })
      toast({ title: "Saved to your notebook (Vocabulary)" })
    } catch {
      toast({ title: "Could not save this word", variant: "destructive" })
    } finally {
      setSaving(false)
    }
  }

  const triage = async (status: VocabularyStatus) => {
    if (!result?.saved_item) return
    try {
      const saved = await updateVocabularyItem(result.saved_item.id, { status })
      setResult({ ...result, saved_item: saved })
      toast({
        title: status === "learning"
          ? "Added to your notebook - it will come up in Review"
          : "Saved to your notebook (Vocabulary)",
      })
    } catch {
      toast({
        title: status === "learning" ? "Today's new-word limit is full" : "Could not update this word",
        variant: "destructive",
      })
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg" data-testid="lookup-sheet">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2"><Search className="h-5 w-5" /> Look up</SheetTitle>
          <SheetDescription>Meaning in this sentence, with the context kept.</SheetDescription>
        </SheetHeader>
        {loading && <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /></div>}
        {!loading && result && (
          <div className="mt-6 space-y-5">
            <div>
              <h2 className="font-serif text-3xl">{result.lemma}</h2>
              {keptSentence && <p className="mt-2 text-sm text-muted-foreground">{keptSentence}</p>}
            </div>
            {result.card_status === "ok" && result.card ? (
              <>
                <p className="text-lg font-medium">{result.card.sense_in_context}</p>
                {result.card.gloss_l1 && <p className="text-fun-purple">{result.card.gloss_l1}</p>}
                <div className="space-y-2">
                  {result.card.examples.map((example) => <p key={example} className="rounded-xl bg-muted p-3">{example}</p>)}
                </div>
              </>
            ) : <p role="alert">The card could not be built. You can retry the lookup.</p>}
            {result.seen_count >= 3 && !result.saved_item && (
              <p className="rounded-xl bg-fun-yellow/15 p-3 text-sm font-medium">Seen {result.seen_count}× — worth saving?</p>
            )}
            {!result.saved_item ? (
              <>
                {!keptSentence && (
                  <div className="space-y-2">
                    <label htmlFor="lookup-sentence" className="text-sm font-medium">
                      The sentence you saw it in
                    </label>
                    <Input
                      id="lookup-sentence"
                      value={sentenceField}
                      onChange={(event) => setSentenceField(event.target.value)}
                      placeholder="e.g. Me senté en un banco."
                      data-testid="lookup-sentence-field"
                    />
                  </div>
                )}
                <Button onClick={save} disabled={saving || result.card_status !== "ok"}>
                  <BookmarkPlus className="mr-2 h-4 w-4" /> {saving ? "Saving…" : "Save to notebook"}
                </Button>
              </>
            ) : (
              <div className="flex flex-wrap gap-2" aria-label="Choose what to do with this word">
                <Button onClick={() => void triage("learning")}>Study</Button>
                <Button variant="outline" onClick={() => void triage("known")}>I know it</Button>
                <Button variant="ghost" onClick={() => void triage("ignored")}>Ignore</Button>
              </div>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}

export function GlobalLookupBox({ language }: { language: string }) {
  const [text, setText] = useState("")
  const [lookupLanguage, setLookupLanguage] = useState(language)
  const [context, setContext] = useState<LookupContext | null>(null)
  return (
    <div className="flex gap-2" data-testid="global-lookup">
      <select
        aria-label="Word language"
        className="rounded-xl border bg-background px-3"
        value={lookupLanguage}
        onChange={(event) => setLookupLanguage(event.target.value)}
      >
        <option value="es">Spanish</option>
        <option value="fr">French</option>
        <option value="en">English</option>
        <option value="ar">Arabic</option>
        <option value="he">Hebrew</option>
        <option value="ja">Japanese</option>
      </select>
      <Input value={text} onChange={(event) => setText(event.target.value)} placeholder="Look up a word or sentence" />
      <Button variant="outline" disabled={!text.trim()} onClick={() => {
        const value = text.trim()
        setContext({ text: value, sentence: value, language: lookupLanguage, source: "manual" })
      }}><Search className="mr-2 h-4 w-4" /> Look up</Button>
      <LookupSheet context={context} open={!!context} onOpenChange={(next) => !next && setContext(null)} />
    </div>
  )
}
