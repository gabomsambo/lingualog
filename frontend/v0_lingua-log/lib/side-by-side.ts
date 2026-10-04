/**
 * Pure helpers for the side-by-side entry result: sentence alignment, the corrected diff,
 * error spans, and the stored LearningPolicy flags. No React and no network here.
 */

export type MeaningFlag = "open" | "tap" | "tap_hidden" | "rescue_only"
export type RewriteGlossFlag = "l1_open" | "l1_tap" | "l2_tooltips"
export type ExplanationFlag = "l1" | "l1_with_l2_terms" | "l2_then_l1" | "l2"

/** The backend's LearningPolicy.to_dict(), stored on each entry as policy_snapshot. */
export interface LearningPolicySnapshot {
  v: number
  l1: string
  l2: string
  ui_language?: string
  immersion_level?: number
  proficiency?: string
  strictness?: string
  formality?: string
  explanation: ExplanationFlag | string
  meaning: MeaningFlag | string
  rewrite_gloss: RewriteGlossFlag | string
  vocab_def?: string
  quiz?: string
  explanation_mode?: string
  translation_policy?: string
}

export interface SuggestionData {
  id?: string | null
  original: string
  corrected: string
  note?: string
  note_l1?: string
  note_l2?: string
  meaning_changing?: boolean
  literal_reading?: string
}

export interface Ambiguity {
  question: string
  span?: string
}

export interface RewriteIdiom {
  phrase: string
  gloss: string
}

export interface EntryWord {
  term: string
  pos?: string
  definition?: string
  example?: string
  reading?: string | null
}

export interface SentenceMapping {
  source_sentence: number
  corrected_sentences: number[]
}

export interface SideBySideEntry {
  id: string
  title?: string
  language: string
  content: string
  corrected: string
  rewrite: string
  analysisStatus: string
  analysisErrorCode?: string | null
  policy: LearningPolicySnapshot | null
  score?: number
  tone?: string
  explanation?: string
  rubric?: { grammar?: number; vocabulary?: number; complexity?: number }
  intendedMeaning: string
  ambiguities: Ambiguity[]
  rewriteIdioms: RewriteIdiom[]
  suggestions: SuggestionData[]
  newWords: EntryWord[]
  sentenceMapping: SentenceMapping[] | null
  sentenceMappingStatus: string | null
}

const asArray = <T,>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : [])

/** Normalise the GET /entries/{id} payload. Tutor extras live inside the rubric column. */
export function toSideBySideEntry(raw: any): SideBySideEntry {
  const ai = raw?.ai_feedback || {}
  const rubric = ai.rubric && typeof ai.rubric === "object" ? ai.rubric : {}
  const snapshot = raw?.policy_snapshot
  return {
    id: String(raw?.id ?? ""),
    title: raw?.title || undefined,
    language: raw?.language || snapshot?.l2 || "",
    content: raw?.content || raw?.original_text || "",
    corrected: raw?.corrected ?? ai.corrected ?? "",
    rewrite: raw?.rewrite ?? raw?.rewritten ?? ai.rewrite ?? "",
    analysisStatus: raw?.analysis_status || "legacy",
    analysisErrorCode: raw?.analysis_error_code ?? null,
    policy: snapshot && typeof snapshot === "object" && snapshot.meaning ? snapshot : null,
    score: typeof ai.score === "number" ? ai.score : undefined,
    tone: typeof ai.tone === "string" ? ai.tone : undefined,
    explanation: ai.explanation || undefined,
    rubric: {
      grammar: rubric.grammar,
      vocabulary: rubric.vocabulary,
      complexity: rubric.complexity,
    },
    intendedMeaning: typeof rubric.intended_meaning === "string" ? rubric.intended_meaning : "",
    ambiguities: asArray<Ambiguity>(rubric.ambiguities).filter((item) => item && item.question),
    rewriteIdioms: asArray<RewriteIdiom>(rubric.rewrite_idioms).filter((item) => item && item.phrase),
    suggestions: asArray<SuggestionData>(ai.grammar_suggestions).filter(
      (item) => item && typeof item.original === "string",
    ),
    newWords: asArray<EntryWord>(ai.new_words).filter((item) => item && item.term),
    sentenceMapping: Array.isArray(raw?.sentence_mapping ?? ai.sentence_mapping)
      ? asArray<SentenceMapping>(raw?.sentence_mapping ?? ai.sentence_mapping)
      : null,
    sentenceMappingStatus: raw?.sentence_mapping_status ?? ai.sentence_mapping_status ?? null,
  }
}

// Same rule as backend/app/services/entry_translation_service.py split_sentences, so the
// per-sentence translations the API returns line up with these rows.
const SENTENCE_SPLIT = /(?<=[.!?…])\s+|\n+/

export function splitSentences(text: string): string[] {
  const stripped = (text || "").trim()
  if (!stripped) return []
  const parts = stripped
    .split(SENTENCE_SPLIT)
    .map((part) => part.trim())
    .filter(Boolean)
  return parts.length ? parts : [stripped]
}

function wordSet(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .split(/[^\p{L}\p{N}]+/u)
      .filter(Boolean),
  )
}

function overlap(a: Set<string>, b: Set<string>): number {
  if (!a.size || !b.size) return 0
  let shared = 0
  a.forEach((word) => {
    if (b.has(word)) shared += 1
  })
  return shared / Math.max(a.size, b.size)
}

/**
 * Line `target` sentences up with `source` rows. Equal counts pair one to one. Otherwise each
 * target sentence goes to the source row it shares most words with, keeping order, so a
 * correction that merged or split sentences still lands beside the words it fixes.
 * Returns one string per source row ("" when nothing maps there).
 */
export function alignSentences(source: string[], target: string[]): string[] {
  if (!source.length) return []
  if (source.length === target.length) return [...target]
  if (!target.length) return source.map(() => "")

  const n = source.length
  const m = target.length
  const src = source.map(wordSet)
  const tgt = target.map(wordSet)
  // best[j][i]: best score with target j assigned to row i, all earlier targets to rows <= i.
  const best: number[][] = Array.from({ length: m }, () => Array(n).fill(-Infinity))
  const from: number[][] = Array.from({ length: m }, () => Array(n).fill(-1))
  for (let i = 0; i < n; i++) best[0][i] = overlap(src[i], tgt[0]) - i * 1e-6
  for (let j = 1; j < m; j++) {
    let runMax = -Infinity
    let runArg = -1
    for (let i = 0; i < n; i++) {
      if (best[j - 1][i] > runMax) {
        runMax = best[j - 1][i]
        runArg = i
      }
      best[j][i] = runMax + overlap(src[i], tgt[j]) - Math.abs(i - (j * n) / m) * 1e-6
      from[j][i] = runArg
    }
  }
  let row = best[m - 1].indexOf(Math.max(...best[m - 1]))
  const rows: string[][] = source.map(() => [])
  for (let j = m - 1; j >= 0; j--) {
    rows[row].unshift(target[j])
    row = j > 0 ? from[j][row] : row
  }
  return rows.map((parts) => parts.join(" "))
}

export type EmptyRowFate = "merged_above" | "merged_below" | "removed"

export interface SentenceAlignment {
  rows: string[]
  fates: Array<EmptyRowFate | null>
  authoritative: boolean
}

/** Use a validated model mapping; return null when persisted data is inconsistent. */
export function alignSentencesFromMapping(
  source: string[],
  target: string[],
  mapping: SentenceMapping[] | null,
): SentenceAlignment | null {
  if (!mapping) return null
  if (mapping.length !== source.length) return null
  if (mapping.some((item, index) => item?.source_sentence !== index || !Array.isArray(item.corrected_sentences))) {
    return null
  }
  if (mapping.some((item) => item.corrected_sentences.length !== new Set(item.corrected_sentences).size)) return null
  const indexes = mapping.flatMap((item) => item.corrected_sentences)
  if (indexes.some((index) => !Number.isInteger(index) || index < 0 || index >= target.length)) return null
  if (new Set(indexes).size !== target.length || target.some((_, index) => !indexes.includes(index))) return null
  if (indexes.some((value, index) => index > 0 && value < indexes[index - 1])) return null

  const owner = new Map<number, number>()
  mapping.forEach((item, sourceIndex) => {
    item.corrected_sentences.forEach((targetIndex) => {
      if (!owner.has(targetIndex)) owner.set(targetIndex, sourceIndex)
    })
  })
  const rows = mapping.map((item, sourceIndex) =>
    item.corrected_sentences
      .filter((targetIndex) => owner.get(targetIndex) === sourceIndex)
      .map((targetIndex) => target[targetIndex])
      .join(" "),
  )
  const fates = mapping.map((item, sourceIndex): EmptyRowFate | null => {
    if (rows[sourceIndex]) return null
    if (!item.corrected_sentences.length) return "removed"
    const targetOwner = owner.get(item.corrected_sentences[0])
    if (targetOwner === undefined) return "removed"
    return targetOwner < sourceIndex ? "merged_above" : "merged_below"
  })
  return { rows, fates, authoritative: true }
}

/**
 * Explain an empty aligned corrected row: merged into the nearest corrected neighbour that shares
 * words with the source sentence (the one sharing more), otherwise removed in the correction.
 */
export function emptyRowFate(source: string[], correctedRows: string[], index: number): EmptyRowFate {
  const words = wordSet(source[index] ?? "")
  const shared = (row: string | undefined) => {
    if (!row) return 0
    let count = 0
    wordSet(row).forEach((word) => {
      if (words.has(word)) count += 1
    })
    return count
  }
  let above: string | undefined
  for (let i = index - 1; i >= 0 && above === undefined; i--) if (correctedRows[i]?.trim()) above = correctedRows[i]
  let below: string | undefined
  for (let i = index + 1; i < correctedRows.length && below === undefined; i++) {
    if (correctedRows[i]?.trim()) below = correctedRows[i]
  }
  const up = shared(above)
  const down = shared(below)
  if (!up && !down) return "removed"
  return up >= down ? "merged_above" : "merged_below"
}

export type DiffKind = "same" | "del" | "ins"
export interface DiffPart {
  kind: DiffKind
  text: string
}

/** Word-level minimal diff (longest common subsequence), deletions before insertions. */
export function diffWords(before: string, after: string): DiffPart[] {
  const a = (before || "").split(/\s+/).filter(Boolean)
  const b = (after || "").split(/\s+/).filter(Boolean)
  const lcs: number[][] = Array.from({ length: a.length + 1 }, () => Array(b.length + 1).fill(0))
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1])
    }
  }
  const parts: DiffPart[] = []
  const push = (kind: DiffKind, word: string) => {
    const last = parts[parts.length - 1]
    if (last && last.kind === kind) last.text += ` ${word}`
    else parts.push({ kind, text: word })
  }
  let i = 0
  let j = 0
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      push("same", a[i])
      i++
      j++
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      push("del", a[i++])
    } else {
      push("ins", b[j++])
    }
  }
  while (i < a.length) push("del", a[i++])
  while (j < b.length) push("ins", b[j++])
  return parts
}

export interface ErrorMark {
  start: number
  end: number
  suggestion: number
}

/**
 * Find each suggestion's `original` snippet in the learner's sentences. Every suggestion is
 * placed at most once, never overlapping another mark; search starts at the sentence where
 * the previous suggestion was found, since Gemini lists errors in reading order.
 */
export function locateSuggestions(sentences: string[], suggestions: SuggestionData[]): ErrorMark[][] {
  const marks: ErrorMark[][] = sentences.map(() => [])
  let cursor = 0
  const free = (row: number, start: number, end: number) =>
    marks[row].every((mark) => end <= mark.start || start >= mark.end)

  suggestions.forEach((suggestion, index) => {
    const needle = (suggestion.original || "").trim()
    if (!needle || !sentences.length) return
    const order = [...sentences.keys()].map((k) => (cursor + k) % sentences.length)
    for (const caseless of [false, true]) {
      for (const row of order) {
        const hay = caseless ? sentences[row].toLowerCase() : sentences[row]
        const target = caseless ? needle.toLowerCase() : needle
        let at = hay.indexOf(target)
        while (at !== -1 && !free(row, at, at + target.length)) at = hay.indexOf(target, at + 1)
        if (at !== -1) {
          marks[row].push({ start: at, end: at + target.length, suggestion: index })
          cursor = row
          return
        }
      }
    }
  })
  marks.forEach((row) => row.sort((x, y) => x.start - y.start))
  return marks
}

/** Gemini sometimes repeats the "As written, a native reads" lead-in; the UI already shows it. */
export function cleanLiteralReading(text: string): string {
  let value = (text || "").trim()
  value = value.replace(
    /^(as written,?\s*a native( speaker)? (reads|would read|understands|hears)|(tal (y )?)?como est[aá] escrito,?(\s*un nativo (lee|entiende))?)\s*[:,]?\s*/i,
    "",
  )
  const quoted = value.match(/^["'“‘«]([\s\S]*)["'”’»]\s*\.?$/)
  return (quoted ? quoted[1] : value).trim()
}

/** Which note text leads and which follows, from the explanation flag stored with the entry. */
export function noteTexts(suggestion: SuggestionData, explanation: string): { primary: string; secondary: string } {
  const l1 = (suggestion.note_l1 || "").trim()
  const l2 = (suggestion.note_l2 || "").trim()
  const note = (suggestion.note || "").trim()
  if (explanation === "l2") return { primary: l2 || note, secondary: "" }
  if (explanation === "l2_then_l1") {
    const primary = l2 || note
    return { primary, secondary: l1 && l1 !== primary ? l1 : "" }
  }
  return { primary: l1 || note, secondary: "" }
}

/** Paragraphs from stored text; older rows hold a literal backslash-n instead of a newline. */
export function splitParagraphs(text: string): string[] {
  return (text || "")
    .split(/\\n|\r?\n/)
    .map((part) => part.trim())
    .filter(Boolean)
}

/** Note rescues are translated as HTML (quoted terms sit in translate="no" spans); show them as text. */
export function htmlToText(value: string): string {
  if (!value || !/[<&]/.test(value)) return value || ""
  if (typeof DOMParser !== "undefined") {
    const doc = new DOMParser().parseFromString(value, "text/html")
    return (doc.body.textContent || "").replace(/\s+/g, " ").trim()
  }
  return value
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim()
}
