"use client"

/**
 * WordBankPanel
 *
 * A few words from the learner's notebook to write today's entry with. Chips tick as the draft
 * uses a word (a client-side hint; the tutor decides after submit). The learner can shuffle,
 * pin the words they want to keep, or switch on challenge mode, where only meanings show and a
 * correct use of a word they never peeked at counts as real recall.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { BookMarked, Check, ChevronDown, Eye, Pin, PinOff, Shuffle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Switch } from "@/components/ui/switch"
import { useLocale } from "@/i18n/LocaleProvider"
import { isRTL } from "@/i18n/rtl"
import { getWordBank, postSupportEvent } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  BANK_SIZE,
  mergeShuffle,
  selectionFor,
  wordAppearsIn,
  type BankSelection,
  type WordBankWord,
} from "@/lib/word-bank"

interface WordBankPanelProps {
  language: string
  /** The draft, so chips can tick when a word appears in it. */
  text: string
  immersionLevel?: number
  disabled?: boolean
  /** Changing this loads a fresh bank, e.g. after the form is reset. */
  resetKey?: number
  onSelectionChange: (selection: BankSelection) => void
}

type LoadState = "loading" | "ready" | "failed"

/** The book named in the link, when the editor was opened from a book. */
function bookParam(): string | undefined {
  return new URLSearchParams(window.location.search).get("book") ?? undefined
}

export function WordBankPanel({
  language,
  text,
  immersionLevel,
  disabled,
  resetKey = 0,
  onSelectionChange,
}: WordBankPanelProps) {
  const { t, uiLang } = useLocale()
  const [words, setWords] = useState<WordBankWord[]>([])
  const [state, setState] = useState<LoadState>("loading")
  const [open, setOpen] = useState(true)
  const [pinned, setPinned] = useState<Set<string>>(new Set())
  const [challenge, setChallenge] = useState(false)
  const [peeked, setPeeked] = useState<Set<string>>(new Set())
  const [meaningShown, setMeaningShown] = useState<Set<string>>(new Set())
  const [shuffling, setShuffling] = useState(false)
  // Set when the editor was opened from a book ("write about what you read"): its words come first.
  const [bookTitle, setBookTitle] = useState<string | null>(null)
  const ticket = useRef(0)

  const load = useCallback(async () => {
    const mine = ++ticket.current
    setWords([])
    setState("loading")
    try {
      const bank = await getWordBank(language, { count: BANK_SIZE, book: bookParam() })
      if (mine !== ticket.current) return
      setBookTitle(bank.book?.title ?? null)
      setWords(bank.words)
      setPinned(new Set())
      setPeeked(new Set())
      setMeaningShown(new Set())
      setState("ready")
    } catch {
      if (mine === ticket.current) setState("failed")
    }
  }, [language])

  useEffect(() => {
    void load()
  }, [load, resetKey])

  // A word with no meaning to show stays visible: hiding it would leave the learner nothing to go on.
  const shownWords = useMemo(
    () => new Set([...peeked, ...words.filter((word) => !word.hint).map((word) => word.word_id)]),
    [peeked, words],
  )

  useEffect(() => {
    onSelectionChange(selectionFor(words, challenge, shownWords))
  }, [words, challenge, shownWords, onSelectionChange])

  const ticked = useMemo(
    () => new Set(words.filter((word) => wordAppearsIn(text, word.forms, language)).map((word) => word.word_id)),
    [words, text, language],
  )

  const shuffle = async () => {
    const kept = words.filter((word) => pinned.has(word.word_id))
    if (kept.length >= BANK_SIZE) return
    setShuffling(true)
    try {
      const count = BANK_SIZE - kept.length
      let bank = await getWordBank(language, { count, exclude: words.map((word) => word.word_id), book: bookParam() })
      // Nothing new left to offer: start the rest again rather than leave the bank short.
      if (bank.words.length === 0) {
        bank = await getWordBank(language, { count, exclude: kept.map((word) => word.word_id), book: bookParam() })
      }
      setWords(mergeShuffle(words, pinned, bank.words))
      setPeeked(new Set())
      setMeaningShown(new Set())
    } catch {
      // Keep the words on screen; the learner can try again.
    } finally {
      setShuffling(false)
    }
  }

  const togglePin = (wordId: string) =>
    setPinned((current) => {
      const next = new Set(current)
      if (!next.delete(wordId)) next.add(wordId)
      return next
    })

  const showMeaning = (word: WordBankWord) => {
    setMeaningShown((current) => new Set(current).add(word.word_id))
    void postSupportEvent({ kind: "reveal_gloss", l2: language, immersion_level: immersionLevel }).catch(
      () => undefined,
    )
  }

  const dir = isRTL(language.split("-")[0]) ? "rtl" : "ltr"
  const promptWords = words.slice(0, 3).map((word) => word.term)
  const promptList = promptWords.length > 1 ? formatList(promptWords, uiLang) : promptWords[0]

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <section
        className="rounded-3xl border border-fun-yellow/40 bg-fun-yellow/10 p-4"
        data-testid="word-bank"
        aria-label={t("journal.wordBankTitle")}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CollapsibleTrigger asChild>
            <button type="button" className="flex items-center gap-2 text-left font-bold" aria-label={t("journal.wordBankToggle")}>
              <BookMarked className="h-5 w-5 text-fun-orange" />
              <span>{t("journal.wordBankTitle")}</span>
              {state === "ready" && words.length > 0 && (
                <span className="text-sm font-normal text-muted-foreground" data-testid="word-bank-count">
                  {t("journal.wordBankUsed", { used: ticked.size, total: words.length })}
                </span>
              )}
              <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
            </button>
          </CollapsibleTrigger>
          {state === "ready" && words.length > 0 && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void shuffle()}
              disabled={disabled || shuffling || pinned.size >= Math.min(words.length, BANK_SIZE)}
            >
              <Shuffle className="mr-2 h-4 w-4" />
              {t("journal.wordBankShuffle")}
            </Button>
          )}
        </div>

        <CollapsibleContent className="space-y-3 pt-3">
          {bookTitle && state === "ready" && (
            <p className="text-sm font-medium text-fun-purple" data-testid="word-bank-book">
              {t("journal.wordBankFromBook", { title: bookTitle })}
            </p>
          )}
          {state === "loading" && (
            <p className="text-sm text-muted-foreground" role="status">
              {t("journal.wordBankLoading")}
            </p>
          )}
          {state === "failed" && (
            <p className="flex flex-wrap items-center gap-2 text-sm" role="alert">
              {t("journal.wordBankFailed")}
              <Button type="button" variant="outline" size="sm" onClick={() => void load()}>
                {t("journal.retryLoadSettings")}
              </Button>
            </p>
          )}
          {state === "ready" && words.length === 0 && (
            <p className="text-sm text-muted-foreground" data-testid="word-bank-empty">
              {t("journal.wordBankEmpty")}{" "}
              <Link href="/vocabulary" className="font-semibold text-fun-purple hover:underline">
                {t("journal.wordBankOpenNotebook")}
              </Link>
            </p>
          )}

          {words.length > 0 && (
            <>
              {!challenge && promptList && (
                <p className="text-sm" data-testid="word-bank-prompt">
                  {t("journal.wordBankPrompt", { words: promptList })}
                </p>
              )}

              <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {words.map((word) => {
                  const hidden = challenge && !shownWords.has(word.word_id)
                  const used = ticked.has(word.word_id)
                  const meaningOpen = challenge || word.hint_mode === "shown" || meaningShown.has(word.word_id)
                  return (
                    <li
                      key={word.word_id}
                      data-testid="word-bank-chip"
                      data-used={used}
                      className={cn(
                        "min-w-0 rounded-2xl border bg-background p-3",
                        used ? "border-green-400 bg-green-50 dark:border-green-700 dark:bg-green-950/30" : "border-border",
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex min-w-0 items-center gap-2">
                          {hidden ? (
                            <button
                              type="button"
                              className="inline-flex items-center gap-1 text-sm font-semibold text-fun-purple hover:underline"
                              onClick={() => setPeeked((current) => new Set(current).add(word.word_id))}
                            >
                              <Eye className="h-4 w-4" />
                              {t("journal.wordBankShowWord")}
                            </button>
                          ) : (
                            <span lang={language} dir={dir} className="truncate font-serif text-lg font-bold">
                              {word.term}
                            </span>
                          )}
                          {used && (
                            <Check className="h-4 w-4 shrink-0 text-green-600" aria-label={t("journal.wordBankInDraft")} />
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={() => togglePin(word.word_id)}
                          aria-pressed={pinned.has(word.word_id)}
                          aria-label={t(pinned.has(word.word_id) ? "journal.wordBankUnpin" : "journal.wordBankPin", {
                            word: word.term,
                          })}
                          disabled={disabled}
                          className={cn(
                            "shrink-0 rounded-full p-1 text-muted-foreground hover:text-foreground",
                            pinned.has(word.word_id) && "text-fun-purple",
                          )}
                        >
                          {pinned.has(word.word_id) ? <PinOff className="h-4 w-4" /> : <Pin className="h-4 w-4" />}
                        </button>
                      </div>
                      {word.hint &&
                        (meaningOpen ? (
                          <p className="mt-1 text-sm text-muted-foreground" data-testid="word-bank-hint">
                            {word.hint}
                          </p>
                        ) : (
                          <button
                            type="button"
                            className="mt-1 text-sm font-semibold text-fun-purple hover:underline"
                            onClick={() => showMeaning(word)}
                          >
                            {t("journal.wordBankShowMeaning")}
                          </button>
                        ))}
                      <p className="mt-1 text-xs text-muted-foreground">{t(`journal.wordBankReason_${word.reason}`)}</p>
                    </li>
                  )
                })}
              </ul>

              <label className="flex items-start gap-3 text-sm">
                <Switch checked={challenge} onCheckedChange={setChallenge} disabled={disabled} aria-label={t("journal.wordBankChallenge")} />
                <span>
                  <span className="font-semibold">{t("journal.wordBankChallenge")}</span>
                  <span className="block text-muted-foreground">{t("journal.wordBankChallengeHint")}</span>
                </span>
              </label>
            </>
          )}
        </CollapsibleContent>
      </section>
    </Collapsible>
  )
}

function formatList(items: string[], locale: string): string {
  try {
    return new Intl.ListFormat(locale, { style: "long", type: "conjunction" }).format(items)
  } catch {
    return items.join(", ")
  }
}
