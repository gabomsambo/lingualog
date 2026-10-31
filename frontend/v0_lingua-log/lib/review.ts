import type { ReviewCard } from "@/lib/api"

/** Case, accent and spacing insensitive form of a typed answer; the server sends `accepted` the same way. */
export function normalizeAnswer(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLocaleLowerCase()
    .trim()
    .replace(/\s+/g, " ")
}

export function isCorrectAnswer(card: Pick<ReviewCard, "accepted">, typed: string): boolean {
  const attempt = normalizeAnswer(typed)
  return attempt !== "" && card.accepted.includes(attempt)
}

const GREEN = "border-green-300 bg-green-100 text-green-800 dark:border-green-700 dark:bg-green-900/40 dark:text-green-200"

/** Notebook state colours: New blue, Learning amber, Known green. Mastered is green too; its label carries the pen mark. */
export const STATUS_CLASS = {
  new: "border-blue-300 bg-blue-100 text-blue-800 dark:border-blue-700 dark:bg-blue-900/40 dark:text-blue-200",
  learning: "border-amber-300 bg-amber-100 text-amber-800 dark:border-amber-700 dark:bg-amber-900/40 dark:text-amber-200",
  known: GREEN,
  mastered: GREEN,
  ignored: "border-muted bg-muted text-muted-foreground",
} as const

export function statusClass(status: string | undefined): string {
  return STATUS_CLASS[(status || "new") as keyof typeof STATUS_CLASS] ?? STATUS_CLASS.ignored
}

export interface SessionTally {
  reviewed: number
  again: number
  gotIt: number
  /** Words that became Known during this session. */
  nowKnown: number
}

export const emptyTally: SessionTally = { reviewed: 0, again: 0, gotIt: 0, nowKnown: 0 }
