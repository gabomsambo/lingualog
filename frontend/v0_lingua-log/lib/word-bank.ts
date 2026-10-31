/**
 * Pure helpers for the word bank beside the editor: matching a word against the draft and
 * choosing what the next submission sends. No React and no network here.
 */

export type WordBankReason = "at_risk" | "due" | "never_used" | "to_master"

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
}

export interface BankSelection {
  targetWordIds: string[]
  challengeWordIds: string[]
}

export const BANK_SIZE = 6

// Languages written without spaces: a word has no boundary around it.
const UNSPACED = new Set(["ja", "zh", "th"])
const WORD_CHAR = "\\p{L}\\p{M}\\p{N}"

/** Case and accent insensitive form used to compare the draft with a stored form. */
export function foldForMatch(text: string): string {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLocaleLowerCase()
}

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")

/**
 * Whether the draft contains one of the word's forms as a whole word. A hint only: the tutor
 * decides, after the entry is submitted, whether the word was really used and used well.
 */
export function wordAppearsIn(text: string, forms: string[], language = ""): boolean {
  const haystack = foldForMatch(text)
  if (!haystack.trim()) return false
  const spaced = !UNSPACED.has(language.split("-")[0].toLowerCase())
  return forms.some((form) => {
    const needle = foldForMatch(form).trim()
    if (!needle) return false
    const pattern = spaced
      ? `(?<![${WORD_CHAR}])${escapeRegExp(needle)}(?![${WORD_CHAR}])`
      : escapeRegExp(needle)
    return new RegExp(pattern, "u").test(haystack)
  })
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
