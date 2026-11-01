/**
 * Pure helpers for the word bank beside the editor: matching a word against the draft and
 * choosing what the next submission sends. No React and no network here.
 */

export type WordBankReason = "at_risk" | "due" | "never_used" | "to_master" | "from_book" | "from_class"

export interface WordBankWord {
  word_id: string
  lemma: string
  term: string
  status: string
  reason: WordBankReason
  /** The forms the learner has met or written; the draft is matched against these. */
  forms: string[]
  /** The word's meaning, already chosen by the learner's policy. */
  hint: string
  /** `tap` keeps the meaning hidden until the learner asks for it. */
  hint_mode: "shown" | "tap"
  use_days: number
}

export interface WordBank {
  language: string
  words: WordBankWord[]
  /** The book whose words come first, when the editor was opened to write about it. */
  book?: { id: string; title: string } | null
}

export interface BankSelection {
  targetWordIds: string[]
  challengeWordIds: string[]
}

export const BANK_SIZE = 6

// Languages written without spaces: a word has no boundary around it.
const UNSPACED = new Set(["ja", "zh", "th"])
const WORD_CHAR = "\\p{L}\\p{M}\\p{N}"
const SPANISH_ENDINGS: Record<string, string[]> = {
  ar: [
    "o", "as", "a", "amos", "ais", "an", "e", "aste", "asteis", "aron", "aba", "abas",
    "abamos", "abais", "aban", "ara", "aras", "aramos", "arais", "aran", "ase", "ases",
    "asemos", "aseis", "asen", "ando", "ado",
  ],
  er: [
    "o", "es", "e", "emos", "eis", "en", "i", "iste", "isteis", "ieron", "ia", "ias",
    "iamos", "iais", "ian", "iera", "ieras", "ieramos", "ierais", "ieran", "iese", "ieses",
    "iesemos", "ieseis", "iesen", "iendo", "ido",
  ],
  ir: [
    "o", "es", "e", "imos", "is", "en", "i", "iste", "isteis", "ieron", "ia", "ias",
    "iamos", "iais", "ian", "iera", "ieras", "ieramos", "ierais", "ieran", "iese", "ieses",
    "iesemos", "ieseis", "iesen", "iendo", "ido",
  ],
}
const SPANISH_FUTURE_ENDINGS = ["e", "as", "a", "emos", "eis", "an"]
const SPANISH_CONDITIONAL_ENDINGS = ["ia", "ias", "iamos", "iais", "ian"]

/** Case and accent insensitive form used to compare the draft with a stored form. */
export function foldForMatch(text: string): string {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLocaleLowerCase()
}

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")

function spanishVerbForms(lemma: string): string[] {
  const normalized = foldForMatch(lemma).trim()
  const ending = normalized.slice(-2)
  const endings = SPANISH_ENDINGS[ending]
  if (!endings || normalized.length < 4) return [normalized]

  const stem = normalized.slice(0, -2)
  const forms = new Set([normalized, ...endings.map((suffix) => stem + suffix)])
  for (const suffix of SPANISH_FUTURE_ENDINGS) forms.add(normalized + suffix)
  for (const suffix of SPANISH_CONDITIONAL_ENDINGS) forms.add(normalized + suffix)

  if (ending === "ar" && stem.endsWith("c")) {
    forms.add(`${stem.slice(0, -1)}que`)
  } else if (ending === "ar" && stem.endsWith("g")) {
    forms.add(`${stem}ue`)
  } else if (ending === "ar" && stem.endsWith("z")) {
    forms.add(`${stem.slice(0, -1)}ce`)
  }
  return [...forms]
}

function formPattern(form: string, language: string): RegExp | null {
  const normalized = foldForMatch(form).trim()
  if (!normalized) return null
  const baseLanguage = language.split("-")[0].toLowerCase()
  if (UNSPACED.has(baseLanguage)) return new RegExp(escapeRegExp(normalized), "u")

  const tokens = normalized.split(/\s+/)
  const spanishInfinitive = baseLanguage === "es" && /(?:ar|er|ir)$/.test(tokens[0])
  const heads = spanishInfinitive ? spanishVerbForms(tokens[0]) : [tokens[0]]
  const escapedHeads = heads.map(escapeRegExp).join("|")
  const tail = tokens.slice(1).map(escapeRegExp).join("\\s+")
  const boundary = `(?<![${WORD_CHAR}])`
  const endBoundary = `(?![${WORD_CHAR}])`
  const gap = spanishInfinitive && tail ? `(?:\\s+[${WORD_CHAR}]+){0,3}\\s+` : "\\s+"
  const source = tail
    ? `${boundary}(?:${escapedHeads})${gap}${tail}${endBoundary}`
    : `${boundary}(?:${escapedHeads})${endBoundary}`
  return new RegExp(source, "u")
}

/**
 * Whether the draft contains one of the word's forms as a whole word. A hint only: the tutor
 * decides, after the entry is submitted, whether the word was really used and used well.
 */
export function wordAppearsIn(text: string, forms: string[], language = ""): boolean {
  const haystack = foldForMatch(text)
  if (!haystack.trim()) return false
  return forms.some((form) => formPattern(form, language)?.test(haystack) ?? false)
}

/**
 * What a submission sends. In challenge mode the words still hidden count as challenge: a
 * correct use of one is real recall. A word the learner peeked at is an ordinary target.
 */
export function selectionFor(words: WordBankWord[], challenge: boolean, revealed: ReadonlySet<string>): BankSelection {
  return {
    targetWordIds: words.map((word) => word.word_id),
    challengeWordIds: challenge ? words.filter((word) => !revealed.has(word.word_id)).map((word) => word.word_id) : [],
  }
}

/** A shuffle keeps the pinned words and fills the rest from the words offered. */
export function mergeShuffle(current: WordBankWord[], pinned: ReadonlySet<string>, offered: WordBankWord[]): WordBankWord[] {
  const kept = current.filter((word) => pinned.has(word.word_id))
  const fresh = offered.filter((word) => !pinned.has(word.word_id))
  return [...kept, ...fresh].slice(0, Math.max(BANK_SIZE, kept.length))
}
