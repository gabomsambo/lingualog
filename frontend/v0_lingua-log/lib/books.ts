import type { CoverageBand, PageCandidate, VocabularyStatus } from "@/lib/api"

export interface Token {
  text: string
  /** True for a word the learner can tap; false for spaces and punctuation. */
  word: boolean
  /** Index of the token's sentence in `sentences(text)`. */
  sentence: number
}

const WORD = /[\p{L}\p{M}\p{N}]+(?:['’-][\p{L}\p{M}\p{N}]+)*/gu
const EDGE = /^[\s.,;:!?¿¡"'«»“”‘’()[\]{}—–\-…*]+|[\s.,;:!?¿¡"'«»“”‘’()[\]{}—–\-…*]+$/g

/** The form marks are grouped by; the server normalises the same way. */
export function normalizeWord(text: string): string {
  return text.replace(EDGE, "").replace(/\s+/g, " ").toLocaleLowerCase()
}

/** Split a page into sentences at . ! ? … and line breaks, keeping each sentence's own text. */
export function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.!?…])\s+|\n+/)
    .map((part) => part.trim())
    .filter(Boolean)
}

/** Where a gap between two words ends one sentence and begins the next: [end of the old, start of the new]. */
function splitGap(gap: string): [string, string] | null {
  const terminated = gap.match(/^([\s\S]*?[.!?…]+["'»”’)\]]*)(\s[\s\S]*)$/)
  if (terminated) return [terminated[1], terminated[2]]
  const newline = gap.indexOf("\n")
  return newline >= 0 ? [gap.slice(0, newline), gap.slice(newline)] : null
}

/** Split a transcription into tappable words and the text between them, each tagged with its sentence. */
export function tokenize(text: string): Token[] {
  const tokens: Token[] = []
  let sentence = 0
  const push = (piece: string, word: boolean) => {
    if (piece) tokens.push({ text: piece, word, sentence })
  }
  let last = 0
  for (const match of text.matchAll(WORD)) {
    const start = match.index ?? 0
    const gap = text.slice(last, start)
    const boundary = tokens.length > 0 ? splitGap(gap) : null
    if (boundary) {
      push(boundary[0], false)
      sentence += 1
      push(boundary[1], false)
    } else {
      push(gap, false)
    }
    push(match[0], true)
    last = start + match[0].length
  }
  push(text.slice(last), false)
  return tokens
}

/** The sentence a token sits in, rebuilt from its tokens so it matches the page text. */
export function sentenceOf(tokens: Token[], index: number): string {
  const target = tokens[index]?.sentence
  return tokens
    .filter((token) => token.sentence === target)
    .map((token) => token.text)
    .join("")
    .trim()
}

/** Candidates the model pre-highlighted, by the normalised surface a tapped word is compared with. */
export function candidateIndex(candidates: PageCandidate[]): Map<string, PageCandidate> {
  const index = new Map<string, PageCandidate>()
  for (const candidate of candidates) {
    index.set(normalizeWord(candidate.surface), candidate)
    if (!index.has(normalizeWord(candidate.lemma))) index.set(normalizeWord(candidate.lemma), candidate)
  }
  return index
}

const HAVE: ReadonlySet<string> = new Set(["known", "mastered", "ignored"])

/** Whether a pre-highlighted word is one the learner already has, so it is shown quietly. */
export function alreadyHave(status: VocabularyStatus | null | undefined): boolean {
  return !!status && HAVE.has(status)
}

export const BAND_CLASS: Record<CoverageBand, string> = {
  comfortable: "border-green-300 bg-green-100 text-green-800 dark:border-green-700 dark:bg-green-900/40 dark:text-green-200",
  study: "border-amber-300 bg-amber-100 text-amber-800 dark:border-amber-700 dark:bg-amber-900/40 dark:text-amber-200",
  demanding: "border-orange-300 bg-orange-100 text-orange-800 dark:border-orange-700 dark:bg-orange-900/40 dark:text-orange-200",
  hard: "border-red-300 bg-red-100 text-red-800 dark:border-red-700 dark:bg-red-900/40 dark:text-red-200",
}

/** Chart colours for the same bands. */
export const BAND_COLOR: Record<CoverageBand, string> = {
  comfortable: "#22c55e",
  study: "#f59e0b",
  demanding: "#f97316",
  hard: "#ef4444",
}

/** The soft band edges drawn on the chart: up to 6 comfortable, up to 15 study reading, 25 or more hard. */
export const BAND_EDGES = { comfortable: 6, study: 15, hard: 25 } as const

const MAX_SIDE = 1600
const JPEG_QUALITY = 0.85

/** Shrink a camera photo before sending it: a page is readable at 1600px and the upload stays small. */
export async function prepareImage(file: Blob): Promise<Blob> {
  const bitmap = await createImageBitmap(file)
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement("canvas")
  canvas.width = Math.round(bitmap.width * scale)
  canvas.height = Math.round(bitmap.height * scale)
  canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  bitmap.close()
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY))
  if (!blob) throw new Error("Could not prepare the photo")
  return blob
}
