"use client"

import { CSSProperties, Fragment, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { AlertCircle, FlaskConical, HelpCircle, Languages, Loader2, RotateCcw } from "lucide-react"

import { LevelSuggestionCard } from "@/components/level-suggestion-card"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useLocale } from "@/i18n/LocaleProvider"
import { isRTL } from "@/i18n/rtl"
import { getLanguageDisplayName } from "@/i18n/languages"
import {
  analyzeEntry,
  getCurrentPolicy,
  getUserSettings,
  keepEntryLanguage,
  postSupportEvent,
  translateEntryPart,
  type EntryTranslationResult,
  type SupportEventKind,
} from "@/lib/api"
import {
  alignSentences,
  alignSentencesFromMapping,
  cleanLiteralReading,
  diffWords,
  htmlToText,
  languageMismatch,
  locateSuggestions,
  sameLanguage,
  noteTexts,
  splitParagraphs,
  splitSentences,
  type ErrorMark,
  type LearningPolicySnapshot,
  type SideBySideEntry,
} from "@/lib/side-by-side"
import { studiedLanguages } from "@/lib/studied-languages"
import { cn } from "@/lib/utils"

type Fetched = { status: "idle" | "loading" | "ok" | "unavailable"; sentences: string[]; text: string; label?: string | null }
const IDLE: Fetched = { status: "idle", sentences: [], text: "" }

// Used only when an entry has no stored snapshot and the current policy cannot be loaded:
// everything visible, nothing hidden behind a tap.
const OPEN_POLICY: Omit<LearningPolicySnapshot, "l1" | "l2"> = {
  v: 1,
  explanation: "l1",
  meaning: "open",
  rewrite_gloss: "l1_open",
}

interface EntrySideBySideProps {
  entry: SideBySideEntry
  /** Score, rubric, tone, summary and new words. The entry page already renders its own. */
  showOverview?: boolean
  /** Called after a successful analysis retry so the parent can reload the entry. */
  onReanalyzed?: () => void | Promise<void>
  /** Called after the learner accepts a suggested immersion change. */
  onLevelAccepted?: () => void
}

function languageName(code: string, uiLang: string): string {
  try {
    const name = new Intl.DisplayNames([uiLang.split("-")[0] || "en"], { type: "language" }).of(code)
    if (name && name !== code) return name
  } catch {
    // Older runtimes without Intl.DisplayNames fall through to the static list.
  }
  return getLanguageDisplayName(code)
}

/**
 * "This looks like French, but you're set to Spanish": shown only when the tutor read the entry as
 * another language. Never switches on its own; switching is offered only for a studied language.
 */
function LanguageMismatchPrompt({
  entry,
  onSwitched,
}: {
  entry: SideBySideEntry
  onSwitched?: () => void | Promise<void>
}) {
  const { t, uiLang } = useLocale()
  const detected = languageMismatch(entry)
  const [studied, setStudied] = useState<string[] | null>(null)
  const [busy, setBusy] = useState<"switch" | "keep" | null>(null)
  const [failed, setFailed] = useState(false)
  const [kept, setKept] = useState(false)
  const [loadFailed, setLoadFailed] = useState(false)
  const [loadAttempt, setLoadAttempt] = useState(0)

  useEffect(() => {
    if (!detected) return
    let cancelled = false
    getUserSettings()
      .then((settings) => {
        if (cancelled) return
        setStudied(studiedLanguages(settings))
        setLoadFailed(false)
      })
      .catch(() => !cancelled && setLoadFailed(true))
    return () => {
      cancelled = true
    }
  }, [detected, loadAttempt])

  if (!detected || kept || (studied === null && !loadFailed)) return null
  const detectedName = languageName(detected, uiLang)
  const chosenName = languageName(entry.language, uiLang)
  const canSwitch = !!studied?.some((code) => sameLanguage(code, detected))
  const switchTo = studied?.find((code) => sameLanguage(code, detected)) || detected

  const switchLanguage = async () => {
    setBusy("switch")
    setFailed(false)
    try {
      await analyzeEntry(entry.id, switchTo)
      await onSwitched?.()
    } catch {
      setFailed(true)
    } finally {
      setBusy(null)
    }
  }

  const keep = async () => {
    setBusy("keep")
    setKept(true)
    try {
      await keepEntryLanguage(entry.id)
    } catch {
      // Hidden for this view either way; the prompt returns next time if the save failed.
    } finally {
      setBusy(null)
    }
  }

  const button =
    "inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-bold disabled:opacity-60"
  return (
    <div
      className="flex flex-wrap items-start gap-3 rounded-3xl border border-fun-blue/40 bg-fun-blue/5 p-4"
      role="status"
      data-testid="language-mismatch"
    >
      <Languages className="mt-0.5 h-5 w-5 text-fun-blue" />
      <div className="min-w-0 flex-1">
        <p className="font-bold">{t("feedback.mismatchTitle", { detected: detectedName, chosen: chosenName })}</p>
        <p className="text-sm text-muted-foreground">
          {studied === null
            ? t("feedback.mismatchLoadFailed")
            : canSwitch
              ? t("feedback.mismatchStudied", { detected: detectedName, chosen: chosenName })
              : t("feedback.mismatchNotStudied", { detected: detectedName, chosen: chosenName })}
        </p>
        {failed && <p className="mt-1 text-sm text-destructive">{t("feedback.mismatchFailed")}</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        {studied === null ? (
          <button
            type="button"
            onClick={() => setLoadAttempt((attempt) => attempt + 1)}
            disabled={busy !== null}
            className={cn(button, "bg-gradient-green-blue text-white")}
            data-testid="mismatch-retry-load"
          >
            {t("feedback.retry")}
          </button>
        ) : canSwitch ? (
          <button
            type="button"
            onClick={() => void switchLanguage()}
            disabled={busy !== null}
            className={cn(button, "bg-gradient-green-blue text-white")}
            data-testid="mismatch-switch"
          >
            {busy === "switch" && <Loader2 className="h-4 w-4 animate-spin" />}
            {t("feedback.mismatchSwitch", { detected: detectedName })}
          </button>
        ) : (
          <Link
            href={`/settings?tab=languages&add=${encodeURIComponent(detected)}`}
            className={cn(button, "bg-gradient-green-blue text-white")}
            data-testid="mismatch-add"
          >
            {t("feedback.mismatchAdd", { detected: detectedName })}
          </Link>
        )}
        <button
          type="button"
          onClick={() => void keep()}
          disabled={busy !== null}
          className={cn(button, "border border-fun-blue text-fun-blue hover:bg-fun-blue/10")}
          data-testid="mismatch-keep"
        >
          {t("feedback.mismatchKeep", { chosen: chosenName })}
        </button>
      </div>
    </div>
  )
}

function useEntryPolicy(entry: SideBySideEntry) {
  const [fallback, setFallback] = useState<LearningPolicySnapshot | null>(null)
  useEffect(() => {
    if (entry.policy) return
    let cancelled = false
    getCurrentPolicy(entry.language || undefined)
      .then((policy) => !cancelled && setFallback(policy))
      .catch(() => !cancelled && setFallback({ ...OPEN_POLICY, l1: "en", l2: entry.language } as LearningPolicySnapshot))
    return () => {
      cancelled = true
    }
  }, [entry.policy, entry.language])
  return { policy: entry.policy || fallback, fromSnapshot: !!entry.policy }
}

const rowStyle = (row: string | number) => ({ "--sbs-row": String(row) }) as CSSProperties

function MobileLabel({ children }: { children: ReactNode }) {
  return <div className="md:hidden mb-1 text-[11px] font-extrabold uppercase tracking-wide text-muted-foreground">{children}</div>
}

function PillButton({ onClick, children, busy }: { onClick: () => void; children: ReactNode; busy?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className="mt-2 inline-flex items-center gap-1 rounded-full border border-fun-purple px-3 py-1 text-xs font-bold text-fun-purple hover:bg-fun-purple/10 disabled:opacity-60"
    >
      {busy && <Loader2 className="h-3 w-3 animate-spin" />}
      {children}
    </button>
  )
}

interface ComputeFateArgs {
  corrected: string
  index: number
  showFate: boolean
  fates: Array<"merged_above" | "merged_below" | "removed" | null>
  hasAction: boolean
}

/**
 * Decide what label to render for an empty corrected row.
 *
 * - When the model mapping is authoritative AND an action explanation is
 *   present, the fate label from the mapping is authoritative.
 * - When the mapping is authoritative but the model forgot the explanation,
 *   fall back to a neutral "no explanation" state so the page never shows
 *   a removed or merged label beside an empty What to fix list.
 * - Otherwise (legacy entries, rejected mappings, etc.) the row is left
 *   unlabelled rather than guessed.
 */
function computeFate({
  corrected,
  index,
  showFate,
  fates,
  hasAction,
}: ComputeFateArgs): "merged_above" | "merged_below" | "removed" | null {
  if (corrected.trim() || !showFate || !hasAction) return null
  return fates[index] ?? null
}

function renderEmptyFate(
  fate: "merged_above" | "merged_below" | "removed" | null,
  t: (key: string, options?: Record<string, unknown>) => string,
): ReactNode {
  if (!fate) {
    return (
      <span className="text-sm italic text-muted-foreground" data-testid="corrected-unaligned">
        {t("feedback.unalignedRow")}
      </span>
    )
  }
  if (fate === "removed") {
    return (
      <span className="text-sm italic text-muted-foreground" data-testid="corrected-removed">
        {t("feedback.removedInCorrection")}
      </span>
    )
  }
  return (
    <span className="text-sm italic text-muted-foreground" data-testid="corrected-merged">
      {fate === "merged_above" ? t("feedback.mergedIntoAbove") : t("feedback.mergedIntoBelow")}
    </span>
  )
}

function LinkButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick} className="text-xs font-bold text-fun-purple hover:underline">
      {children}
    </button>
  )
}

export function EntrySideBySide({ entry, showOverview = true, onReanalyzed, onLevelAccepted }: EntrySideBySideProps) {
  const { t, uiLang } = useLocale()
  const { policy, fromSnapshot } = useEntryPolicy(entry)

  const [view, setView] = useState<"corrected" | "native">("corrected")
  const [meaning, setMeaning] = useState<Fetched>(IDLE)
  const [rewriteGloss, setRewriteGloss] = useState<Fetched>(IDLE)
  const [rewriteGlossShown, setRewriteGlossShown] = useState(false)
  const [revealed, setRevealed] = useState<Set<number>>(new Set())
  const [meaningRescued, setMeaningRescued] = useState(false)
  const [noteRescues, setNoteRescues] = useState<Record<number, Fetched>>({})
  const [retrying, setRetrying] = useState(false)
  const [retryFailed, setRetryFailed] = useState(false)
  const [highlighted, setHighlighted] = useState<number | null>(null)
  const logged = useRef<Set<string>>(new Set())

  const failed = entry.analysisStatus === "failed"
  const isMock = entry.analysisStatus === "mock"
  const l1 = policy?.l1 || "en"
  const l2 = policy?.l2 || entry.language
  const l2Dir = isRTL(l2.split("-")[0]) ? "rtl" : "ltr"
  const l1Name = languageName(l1, uiLang)
  const l2Name = languageName(l2, uiLang)
  const rescueOnly = policy?.meaning === "rescue_only"
  // Studying your own language: there is nothing to translate into, so no meaning or rescue fetches.
  const canTranslate = !sameLanguage(l1, l2)

  const sentences = useMemo(() => splitSentences(entry.content), [entry.content])
  const mappingStatus = entry.sentenceMappingStatus
  const alignment = useMemo(() => {
    if (!entry.corrected) return { rows: [], fates: [], authoritative: false }
    const targets = splitSentences(entry.corrected)
    if (mappingStatus === "valid") {
      const mapped = alignSentencesFromMapping(sentences, targets, entry.sentenceMapping)
      if (mapped) return mapped
    }
    return {
      rows: alignSentences(sentences, targets),
      fates: [],
      authoritative: false,
    }
  }, [sentences, entry.corrected, entry.sentenceMapping, mappingStatus])
  const correctedRows = alignment.rows
  const mappingRejected =
    mappingStatus === "invalid" ||
    mappingStatus === "invalid_no_explanation" ||
    (!!entry.sentenceMapping && !alignment.authoritative)
  // A mapping is only authoritative when the server accepted it AND every
  // removed/merged source sentence carries an explanation. The server already
  // drops the mapping when that is not the case, but the check stays for
  // legacy rows and any front-end-only inconsistency.
  const mappingIsAuthoritative =
    alignment.authoritative && mappingStatus === "valid" && !mappingRejected

  useEffect(() => {
    if (!mappingRejected) return
    const reason = mappingStatus === "invalid_no_explanation"
      ? "model mapping explained a removal or merge without a reason"
      : mappingStatus === "invalid"
        ? "model mapping was structurally invalid"
        : "model mapping did not match the sentences"
    console.warn(`Entry ${entry.id}: ${reason}; rows will be shown unaligned`)
  }, [entry.id, mappingRejected, mappingStatus])

  const actionsByRow = useMemo(() => {
    const map = new Map<number, NonNullable<typeof entry.sentenceActions>[number]>()
    entry.sentenceActions?.forEach((action) => {
      if (action.source_sentence >= 0 && action.source_sentence < sentences.length) {
        map.set(action.source_sentence, action)
      }
    })
    return map
  }, [entry.sentenceActions, sentences.length])
  const marks = useMemo(() => locateSuggestions(sentences, entry.suggestions), [sentences, entry.suggestions])
  const rowOfSuggestion = useMemo(() => {
    const rows = new Map<number, number>()
    marks.forEach((row, index) => row.forEach((mark) => rows.set(mark.suggestion, index)))
    return rows
  }, [marks])

  const logEvent = useCallback(
    (kind: SupportEventKind, key: string) => {
      const id = `${kind}:${key}`
      if (!entry.id || logged.current.has(id)) return
      logged.current.add(id)
      postSupportEvent({ kind, entry_id: entry.id, immersion_level: policy?.immersion_level, l2 }).catch(() => {})
    },
    [entry.id, policy?.immersion_level, l2],
  )

  const fetchPart = useCallback(
    async (part: string, set: (value: Fetched) => void) => {
      set({ ...IDLE, status: "loading" })
      try {
        const result: EntryTranslationResult = await translateEntryPart(entry.id, part, l1)
        if (result.status !== "ok" || !result.text) set({ ...IDLE, status: "unavailable" })
        else set({ status: "ok", sentences: result.sentences || [], text: result.text, label: result.provider_label })
      } catch {
        set({ ...IDLE, status: "unavailable" })
      }
    },
    [entry.id, l1],
  )

  const loadMeaning = useCallback(() => fetchPart("original", setMeaning), [fetchPart])
  const loadRewriteGloss = useCallback(() => fetchPart("rewrite", setRewriteGloss), [fetchPart])

  // Which translations run up front is the policy's call: the meaning at open/tap/tap_hidden
  // (visibility is presentation), the rewrite gloss only when it is shown open.
  useEffect(() => {
    if (!policy || !entry.id || !entry.content || !canTranslate) return
    if (policy.meaning !== "rescue_only") void loadMeaning()
  }, [policy, entry.id, entry.content, canTranslate, loadMeaning])

  useEffect(() => {
    if (!policy || !entry.id || !entry.rewrite || failed || !canTranslate) return
    if (policy.rewrite_gloss === "l1_open") void loadRewriteGloss()
  }, [policy, entry.id, entry.rewrite, failed, canTranslate, loadRewriteGloss])

  const revealSentence = (index: number) => {
    setRevealed((prev) => new Set(prev).add(index))
    logEvent("reveal_meaning", `sentence-${index}`)
  }

  const rescueMeaning = () => {
    setMeaningRescued(true)
    logEvent("reveal_meaning", "rescue")
    if (meaning.status !== "ok") void loadMeaning()
  }

  const showRewriteGloss = () => {
    setRewriteGlossShown(true)
    logEvent("reveal_rewrite_gloss", "rewrite")
    if (rewriteGloss.status !== "ok") void loadRewriteGloss()
  }

  const rescueNote = (index: number) => {
    const suggestion = entry.suggestions[index]
    const noteId = suggestion?.id != null && suggestion.id !== "" ? String(suggestion.id) : String(index)
    logEvent("rescue_note", noteId)
    void fetchPart(`note:${noteId}`, (value) => setNoteRescues((prev) => ({ ...prev, [index]: value })))
  }

  const retryAnalysis = async () => {
    setRetrying(true)
    setRetryFailed(false)
    try {
      await analyzeEntry(entry.id)
      await onReanalyzed?.()
    } catch {
      setRetryFailed(true)
    } finally {
      setRetrying(false)
    }
  }

  const jumpToFix = (index: number) => {
    const card = document.getElementById(`fix-${entry.id}-${index}`)
    card?.scrollIntoView?.({ behavior: "smooth", block: "center" })
    setHighlighted(index)
    window.setTimeout(() => setHighlighted((current) => (current === index ? null : current)), 1800)
  }

  if (!policy) {
    return (
      <div className="flex justify-center py-8" data-testid="side-by-side-loading">
        <Loader2 className="h-6 w-6 animate-spin text-fun-purple" />
      </div>
    )
  }

  const rows = sentences.length
  const meaningAligned = meaning.status === "ok" && meaning.sentences.length === rows
  const hasRewrite = !!entry.rewrite && !failed
  const l2Label = (key: string, options?: Record<string, unknown>) =>
    rescueOnly ? t(key, { ...options, lng: l2.split("-")[0] }) : t(key, options)

  const renderWritten = (sentence: string, rowMarks: ErrorMark[]) => {
    const pieces: ReactNode[] = []
    let at = 0
    rowMarks.forEach((mark) => {
      if (mark.start > at) pieces.push(sentence.slice(at, mark.start))
      const suggestion = entry.suggestions[mark.suggestion]
      pieces.push(
        <button
          key={`${mark.start}-${mark.suggestion}`}
          type="button"
          onClick={() => jumpToFix(mark.suggestion)}
          title={suggestion.corrected}
          data-testid="error-mark"
          data-meaning-changing={suggestion.meaning_changing ? "true" : "false"}
          className={cn(
            "inline align-baseline underline decoration-wavy underline-offset-4 decoration-[1.5px] cursor-pointer",
            suggestion.meaning_changing ? "decoration-fun-orange" : "decoration-red-500",
          )}
        >
          {sentence.slice(mark.start, mark.end)}
        </button>,
      )
      at = mark.end
    })
    if (at < sentence.length) pieces.push(sentence.slice(at))
    return pieces
  }

  const asWritten = (index: number) => {
    const suggestion = entry.suggestions[index]
    const reading = cleanLiteralReading(suggestion.literal_reading || "")
    if (!suggestion.meaning_changing || !reading) return null
    return (
      <div
        key={`warn-${index}`}
        data-testid="as-written"
        className="mt-2 rounded-lg border-l-4 border-fun-orange bg-fun-orange/10 px-3 py-1.5 text-[13px]"
      >
        {l2Label("feedback.asWrittenNativeReads")}: &ldquo;
        <span lang={rescueOnly ? l2 : l1}>{reading}</span>&rdquo;
      </div>
    )
  }

  const meaningUnavailable = (
    <div className="flex flex-wrap items-center gap-2 text-sm text-destructive" data-testid="meaning-unavailable">
      <AlertCircle className="h-4 w-4" />
      {t("feedback.translationUnavailable")}
      <LinkButton onClick={() => void loadMeaning()}>{t("feedback.retry")}</LinkButton>
    </div>
  )

  const renderMeaningCell = (index: number) => {
    if (meaning.status === "loading" || meaning.status === "idle") {
      return index === 0 ? <span className="text-sm text-muted-foreground">{t("feedback.loadingMeaning")}</span> : null
    }
    if (meaning.status === "unavailable") return index === 0 ? meaningUnavailable : null
    const text = meaning.sentences[index] || ""
    if (policy.meaning === "open" || revealed.has(index)) return <span data-testid="meaning-text">{text}</span>
    if (policy.meaning === "tap") {
      return (
        <button type="button" onClick={() => revealSentence(index)} className="block text-left" data-testid="meaning-blurred">
          <span className="select-none blur-[6px]" aria-hidden="true">
            {text}
          </span>
          <span className="mt-1 block text-xs font-bold text-fun-purple">{t("feedback.tapToReveal")}</span>
        </button>
      )
    }
    return <LinkButton onClick={() => revealSentence(index)}>{t("feedback.showMeaning")}</LinkButton>
  }

  const meaningHeader = rescueOnly ? l2Label("feedback.whatYouMeant") : t("feedback.whatItMeans")
  const meaningTag = rescueOnly
    ? t("feedback.paraphraseBy", { language: l2Name })
    : meaning.status === "ok"
      ? meaning.label || ""
      : ""

  const cell = "min-w-0 px-4 py-3 md:border-b md:border-border"
  const rowHover = "transition-colors group-hover:bg-fun-yellow/10"

  const notesForRow = (index: number) =>
    entry.suggestions.map((_, k) => k).filter((k) => rowOfSuggestion.get(k) === index)

  return (
    <div className="space-y-6" data-testid="entry-side-by-side">
      <LanguageMismatchPrompt entry={entry} onSwitched={onReanalyzed} />
      <LevelSuggestionCard l2={entry.policy?.l2 || entry.language} onAccepted={onLevelAccepted} />
      {failed && (
        <div className="rounded-3xl border border-destructive/30 bg-destructive/5 p-4" role="alert" data-testid="analysis-failed">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 text-destructive" />
            <div className="flex-1">
              <p className="font-bold">{t("feedback.analysisFailedTitle")}</p>
              <p className="text-sm text-muted-foreground">
                {t("feedback.analysisFailedDesc")}
                {entry.analysisErrorCode ? ` (${entry.analysisErrorCode})` : ""}
              </p>
              {retryFailed && <p className="mt-1 text-sm text-destructive">{t("feedback.retryFailed")}</p>}
            </div>
            <button
              type="button"
              onClick={() => void retryAnalysis()}
              disabled={retrying}
              className="inline-flex items-center gap-2 rounded-full bg-gradient-green-blue px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
            >
              {retrying ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
              {retrying ? t("feedback.retrying") : t("feedback.retryAnalysis")}
            </button>
          </div>
        </div>
      )}

      {isMock && (
        <div className="flex items-start gap-3 rounded-3xl border border-fun-yellow/60 bg-fun-yellow/10 p-4" data-testid="sample-banner">
          <FlaskConical className="mt-0.5 h-5 w-5 text-fun-orange" />
          <div>
            <p className="font-bold">{t("feedback.sampleFeedbackTitle")}</p>
            <p className="text-sm text-muted-foreground">{t("feedback.sampleFeedbackDesc")}</p>
          </div>
        </div>
      )}

      <Card className="overflow-hidden rounded-3xl border-fun-purple/20 shadow-fun">
        <CardHeader className="bg-gradient-to-r from-fun-purple/10 to-fun-blue/10 pb-4">
          <CardTitle className="text-xl">{t("feedback.sideBySideTitle")}</CardTitle>
          {!fromSnapshot && <p className="text-xs text-muted-foreground">{t("feedback.currentPolicyNote")}</p>}
          {mappingRejected && (
            <p className="text-xs text-fun-orange" role="status" data-testid="alignment-fallback-warning">
              {mappingStatus === "invalid_no_explanation"
                ? t("feedback.alignmentContractWarning")
                : t("feedback.alignmentFallbackWarning")}
            </p>
          )}
        </CardHeader>
        <CardContent className="p-0">
          <div className="grid grid-cols-1 md:grid-cols-3" data-testid="side-by-side-grid">
            <div className={cn(cell, "hidden md:flex md:col-start-1 md:row-start-1 items-center text-[13px] font-extrabold uppercase tracking-wide text-muted-foreground")}>
              {t("feedback.whatYouWrote")}
            </div>
            <div className={cn(cell, "hidden md:flex md:col-start-2 md:row-start-1 items-center justify-between gap-2 text-[13px] font-extrabold uppercase tracking-wide text-muted-foreground")}>
              <span data-testid="meaning-header">{meaningHeader}</span>
              {meaningTag && <span className="text-[11px] font-bold normal-case tracking-normal">{meaningTag}</span>}
            </div>
            <div className={cn(cell, "flex md:col-start-3 md:row-start-1 items-center justify-between gap-2 text-[13px] font-extrabold uppercase tracking-wide text-muted-foreground")}>
              <span className="hidden md:inline">{t("feedback.howToWriteIt")}</span>
              <span className="inline-flex rounded-full bg-muted p-0.5 normal-case tracking-normal" role="group">
                {(["corrected", "native"] as const).map((option) => (
                  <button
                    key={option}
                    type="button"
                    disabled={option === "native" && !hasRewrite}
                    aria-pressed={view === option}
                    onClick={() => setView(option)}
                    className={cn(
                      "rounded-full px-3 py-1 text-xs font-bold disabled:opacity-40",
                      view === option ? "bg-background text-foreground shadow" : "text-muted-foreground",
                    )}
                  >
                    {option === "corrected" ? t("feedback.correctedView") : t("feedback.nativeView")}
                  </button>
                ))}
              </span>
            </div>

            {sentences.map((sentence, index) => {
              const corrected = correctedRows[index] || ""
              const action = actionsByRow.get(index)
              const fate = computeFate({
                corrected,
                index,
                showFate: mappingIsAuthoritative,
                fates: alignment.fates,
                hasAction: !!action,
              })
              return (
                <div key={index} className="group contents" data-testid="sbs-row">
                  <div
                    className={cn(cell, rowHover, "border-t md:border-t-0 md:col-start-1 md:[grid-row:var(--sbs-row)]")}
                    style={rowStyle(index + 2)}
                  >
                    <MobileLabel>{t("feedback.whatYouWrote")}</MobileLabel>
                    <p lang={l2} dir={l2Dir} className="font-serif text-base leading-relaxed" data-testid="written">
                      {renderWritten(sentence, marks[index])}
                    </p>
                  </div>
                  {!rescueOnly && meaning.status === "ok" && !meaningAligned ? null : !rescueOnly ? (
                    <div className={cn(cell, rowHover, "md:col-start-2 md:[grid-row:var(--sbs-row)] text-[15px] leading-relaxed")} style={rowStyle(index + 2)}>
                      <MobileLabel>{meaningHeader}</MobileLabel>
                      <div lang={l1}>{renderMeaningCell(index)}</div>
                      {notesForRow(index).map(asWritten)}
                    </div>
                  ) : null}
                  {view === "corrected" && (
                    <div className={cn(cell, rowHover, "md:col-start-3 md:[grid-row:var(--sbs-row)]")} style={rowStyle(index + 2)}>
                      <MobileLabel>{t("feedback.howToWriteIt")}</MobileLabel>
                      {!entry.corrected || failed ? (
                        index === 0 ? <span className="text-sm text-muted-foreground">{t("feedback.noCorrectionYet")}</span> : null
                      ) : !corrected.trim() ? (
                        renderEmptyFate(fate, t)
                      ) : (
                        <>
                        <p lang={l2} dir={l2Dir} className="font-serif text-base leading-relaxed" data-testid="corrected">
                          {diffWords(sentence, corrected).map((part, k) => (
                            <Fragment key={k}>
                              {k > 0 && " "}
                              {part.kind === "same" ? (
                                part.text
                              ) : part.kind === "del" ? (
                                <del className="bg-red-500/10 text-red-600">{part.text}</del>
                              ) : (
                                <ins className="rounded bg-fun-green/15 px-0.5 text-green-700 no-underline">{part.text}</ins>
                              )}
                            </Fragment>
                          ))}
                        </p>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )
            })}

            {rescueOnly && (
              <div
                className={cn(cell, "border-t md:border-t-0 md:col-start-2 md:[grid-row:var(--sbs-row)] text-[15px] leading-relaxed")}
                style={rowStyle(`2 / span ${Math.max(rows, 1)}`)}
                data-testid="meaning-paraphrase"
              >
                <MobileLabel>{meaningHeader}</MobileLabel>
                {entry.intendedMeaning && (
                  <p lang={l2} dir={l2Dir}>
                    {entry.intendedMeaning}
                  </p>
                )}
                {!canTranslate ? null : !meaningRescued ? (
                  <PillButton onClick={rescueMeaning}>{t("feedback.explainIn", { language: l1Name })}</PillButton>
                ) : meaning.status === "unavailable" ? (
                  <div className="mt-2">{meaningUnavailable}</div>
                ) : meaning.status === "ok" ? (
                  <div className="mt-2 text-sm text-muted-foreground" lang={l1} data-testid="meaning-rescue">
                    {meaning.text.split(/\n+/).join(" ")}
                    {meaning.label && <span className="block text-[11px]">{meaning.label}</span>}
                  </div>
                ) : (
                  <span className="mt-2 block text-sm text-muted-foreground">{t("feedback.loadingMeaning")}</span>
                )}
                {entry.suggestions.map((_, k) => asWritten(k))}
              </div>
            )}

            {!rescueOnly && meaning.status === "ok" && !meaningAligned && (
              <div
                className={cn(cell, "border-t md:border-t-0 md:col-start-2 md:[grid-row:var(--sbs-row)] text-[15px] leading-relaxed")}
                style={rowStyle(`2 / span ${Math.max(rows, 1)}`)}
                data-testid="meaning-block"
              >
                <MobileLabel>{meaningHeader}</MobileLabel>
                {policy.meaning === "open" || revealed.has(0) ? (
                  <p lang={l1}>{meaning.text.split(/\n+/).join(" ")}</p>
                ) : (
                  <LinkButton onClick={() => revealSentence(0)}>
                    {policy.meaning === "tap" ? t("feedback.tapToReveal") : t("feedback.showMeaning")}
                  </LinkButton>
                )}
                {entry.suggestions.map((_, k) => asWritten(k))}
              </div>
            )}

            {view === "native" && hasRewrite && (
              <div
                className={cn(cell, "border-t md:border-t-0 md:col-start-3 md:[grid-row:var(--sbs-row)]")}
                style={rowStyle(`2 / span ${Math.max(rows, 1)}`)}
                data-testid="native-block"
              >
                <MobileLabel>{t("feedback.howToWriteIt")}</MobileLabel>
                <p lang={l2} dir={l2Dir} className="text-[15px] leading-relaxed">
                  {entry.rewrite}
                </p>
                {entry.rewriteIdioms.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {entry.rewriteIdioms.map((idiom, k) => (
                      <span key={k} className="rounded-full bg-fun-purple/10 px-2.5 py-1 text-xs text-fun-purple" data-testid="idiom">
                        <b lang={l2}>{idiom.phrase}</b> · {idiom.gloss}
                      </span>
                    ))}
                  </div>
                )}
                {canTranslate && (
                <div className="mt-3 text-sm text-muted-foreground" data-testid="rewrite-gloss">
                  {policy.rewrite_gloss === "l1_open" || rewriteGlossShown ? (
                    rewriteGloss.status === "ok" ? (
                      <p lang={l1}>{rewriteGloss.text.split(/\n+/).join(" ")}</p>
                    ) : rewriteGloss.status === "unavailable" ? (
                      <span className="inline-flex items-center gap-2 text-destructive">
                        {t("feedback.translationUnavailable")}
                        <LinkButton onClick={() => void loadRewriteGloss()}>{t("feedback.retry")}</LinkButton>
                      </span>
                    ) : (
                      <span>{t("feedback.loadingMeaning")}</span>
                    )
                  ) : policy.rewrite_gloss === "l1_tap" ? (
                    <LinkButton onClick={showRewriteGloss}>{t("feedback.showIn", { language: l1Name })}</LinkButton>
                  ) : (
                    <PillButton onClick={showRewriteGloss}>{t("feedback.explainIn", { language: l1Name })}</PillButton>
                  )}
                </div>
                )}
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-x-3 px-4 py-2 text-xs text-muted-foreground">
            <span>
              <span className="underline decoration-wavy decoration-red-500 underline-offset-4">{t("feedback.legendError")}</span>
            </span>
            <span>
              <span className="underline decoration-wavy decoration-fun-orange underline-offset-4">{t("feedback.legendMeaning")}</span>
            </span>
            <span className="hidden md:inline">{t("feedback.legendHover")}</span>
          </div>
        </CardContent>
      </Card>

      {!failed && (
        <Card className="overflow-hidden rounded-3xl border-fun-purple/20 shadow-fun">
          <CardHeader className="bg-gradient-to-r from-fun-purple/10 to-fun-blue/10 pb-4">
            <CardTitle className="text-xl">{t("feedback.whatToFix")}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-3">
            {entry.suggestions.length === 0 && (entry.sentenceActions?.length ?? 0) === 0 && !mappingRejected && (
              <p className="text-sm text-muted-foreground">{t("feedback.nothingToFix")}</p>
            )}
            {mappingRejected && (
              <div
                data-testid="unexplained-change-card"
                className="min-w-0 rounded-2xl border border-fun-orange/40 bg-fun-orange/5 p-3"
              >
                <div className="text-[11px] font-extrabold uppercase text-fun-orange">
                  {t("feedback.unexplainedChangeLabel")}
                </div>
                <p className="mt-1.5 text-sm">{t("feedback.unexplainedChangeBody")}</p>
              </div>
            )}
            {entry.sentenceActions?.map((action, index) => {
              const sourceSentence = sentences[action.source_sentence] || ""
              return (
                <div
                  key={`action-${action.source_sentence}-${index}`}
                  id={`action-${entry.id}-${action.source_sentence}`}
                  data-testid="action-card"
                  data-action-kind={action.action}
                  className="min-w-0 rounded-2xl border border-fun-purple/40 bg-fun-purple/5 p-3"
                >
                  <div className="text-[11px] font-extrabold uppercase text-fun-purple">
                    {action.action === "removed"
                      ? t("feedback.sentenceRemovedLabel")
                      : t("feedback.sentenceMergedLabel")}
                  </div>
                  {sourceSentence && (
                    <p lang={l2} dir={l2Dir} className="my-1.5 font-serif text-base">
                      <del className="bg-red-500/10 text-red-600">{sourceSentence}</del>
                    </p>
                  )}
                  <p className="text-sm" data-testid="action-reason">
                    <span className="font-bold">{t("feedback.whyRemovedOrMerged")}: </span>
                    {action.reason}
                  </p>
                </div>
              )
            })}
            {entry.suggestions.map((suggestion, index) => {
              const { primary, secondary } = noteTexts(suggestion, policy.explanation)
              const rescue = noteRescues[index]
              return (
                <div
                  key={index}
                  id={`fix-${entry.id}-${index}`}
                  data-testid="fix-card"
                  className={cn(
                    "min-w-0 rounded-2xl border p-3 transition-shadow",
                    suggestion.meaning_changing ? "border-fun-orange" : "border-border",
                    highlighted === index && "ring-2 ring-fun-yellow",
                  )}
                >
                  <div className="text-[11px] font-extrabold uppercase text-muted-foreground">
                    {suggestion.meaning_changing ? t("feedback.changesMeaning") : t("feedback.fixLabel")}
                  </div>
                  <p lang={l2} dir={l2Dir} className="my-1.5 font-serif">
                    <del className="bg-red-500/10 text-red-600">{suggestion.original}</del> →{" "}
                    <ins className="rounded bg-fun-green/15 px-0.5 text-green-700 no-underline">{suggestion.corrected}</ins>
                  </p>
                  {primary && <p className="text-sm" data-testid="note-primary">{primary}</p>}
                  {secondary && <p className="mt-1 text-[13px] text-muted-foreground" data-testid="note-secondary">{secondary}</p>}
                  {policy.explanation === "l2" &&
                    canTranslate &&
                    (!rescue ? (
                      <PillButton onClick={() => rescueNote(index)}>{t("feedback.explainIn", { language: l1Name })}</PillButton>
                    ) : rescue.status === "ok" ? (
                      <p className="mt-2 text-[13px] text-muted-foreground" lang={l1} data-testid="note-rescue">
                        {htmlToText(rescue.text)}
                      </p>
                    ) : rescue.status === "unavailable" ? (
                      <span className="mt-2 inline-flex items-center gap-2 text-[13px] text-destructive">
                        {t("feedback.translationUnavailable")}
                        <LinkButton onClick={() => rescueNote(index)}>{t("feedback.retry")}</LinkButton>
                      </span>
                    ) : (
                      <PillButton onClick={() => undefined} busy>
                        {t("feedback.explainIn", { language: l1Name })}
                      </PillButton>
                    ))}
                </div>
              )
            })}
          </CardContent>
        </Card>
      )}

      {entry.ambiguities.length > 0 && (
        <Card className="overflow-hidden rounded-3xl border-fun-blue/20 shadow-fun" data-testid="ambiguities">
          <CardHeader className="bg-gradient-to-r from-fun-blue/10 to-fun-teal/10 pb-4">
            <CardTitle className="flex items-center gap-2 text-xl">
              <HelpCircle className="h-5 w-5 text-fun-blue" />
              {t("feedback.questionsTitle")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 p-4">
            {entry.ambiguities.map((item, index) => (
              <div key={index} className="rounded-2xl border border-border p-3">
                <p className="font-semibold">{item.question}</p>
                {item.span && (
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t("feedback.questionAbout")}: <span lang={l2} className="font-serif">&ldquo;{item.span}&rdquo;</span>
                  </p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {showOverview && !failed && <EntryOverview entry={entry} l2={l2} l2Dir={l2Dir} />}
    </div>
  )
}

function EntryOverview({ entry, l2, l2Dir }: { entry: SideBySideEntry; l2: string; l2Dir: "rtl" | "ltr" }) {
  const { t } = useLocale()
  const rubric: [string, number | undefined][] = [
    ["feedback.rubricGrammar", entry.rubric?.grammar],
    ["feedback.rubricVocabulary", entry.rubric?.vocabulary],
    ["feedback.rubricComplexity", entry.rubric?.complexity],
  ]
  return (
    <div className="grid gap-6 md:grid-cols-2" data-testid="entry-overview">
      <Card className="overflow-hidden rounded-3xl border-fun-green/20 shadow-fun">
        <CardHeader className="bg-gradient-to-r from-fun-green/10 to-fun-blue/10 pb-4">
          <CardTitle className="flex items-center justify-between text-xl">
            <span>{t("feedback.scoreLabel")}</span>
            <span className="text-fun-green">
              {entry.score ?? "—"}
              <span className="text-sm text-muted-foreground">/100</span>
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 p-4">
          {rubric.map(([key, value]) => (
            <div key={key}>
              <div className="flex justify-between text-sm">
                <span>{t(key)}</span>
                <span>{value ?? "—"}</span>
              </div>
              <div className="mt-1 h-2 rounded-full bg-muted">
                <div className="h-2 rounded-full bg-gradient-green-blue" style={{ width: `${value ?? 0}%` }} />
              </div>
            </div>
          ))}
          {entry.tone && (
            <p className="text-sm">
              {t("feedback.toneLabel")}: <span className="rounded-full bg-fun-blue/10 px-2 py-0.5 font-bold text-fun-blue">{entry.tone}</span>
            </p>
          )}
        </CardContent>
      </Card>
      <Card className="overflow-hidden rounded-3xl border-fun-blue/20 shadow-fun">
        <CardHeader className="bg-gradient-to-r from-fun-blue/10 to-fun-purple/10 pb-4">
          <CardTitle className="text-xl">{t("feedback.summaryTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 p-4 text-sm leading-relaxed">
          {splitParagraphs(entry.explanation || "").map((paragraph, index) => (
            <p key={index}>{paragraph}</p>
          ))}
        </CardContent>
      </Card>
      {entry.newWords.length > 0 && (
        <Card className="overflow-hidden rounded-3xl border-fun-yellow/40 shadow-fun md:col-span-2">
          <CardHeader className="bg-gradient-to-r from-fun-yellow/10 to-fun-orange/10 pb-4">
            <CardTitle className="text-xl">{t("feedback.newWordsTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-3">
            {entry.newWords.map((word, index) => (
              <div key={index} className="min-w-0 rounded-2xl border border-border p-3 text-sm">
                <p lang={l2} dir={l2Dir} className="font-serif text-base font-bold">
                  {word.term}
                  {word.pos && <span className="ml-2 text-xs font-normal text-muted-foreground">{word.pos}</span>}
                </p>
                {word.definition && <p className="mt-1">{word.definition}</p>}
                {word.example && (
                  <p lang={l2} className="mt-1 italic text-muted-foreground">
                    {word.example}
                  </p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
