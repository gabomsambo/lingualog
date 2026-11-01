import type { ReactNode } from "react"

const EMPHASIS = /\*\*(?=\S)([^*\n]*?\S)\*\*|\*(?=\S)([^*\n]*?\S)\*/g

/** Turns **x** into <strong> and *x* into <em>; any other text, including HTML, stays plain text. */
export function renderEmphasis(text: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let last = 0
  for (const match of text.matchAll(EMPHASIS)) {
    const start = match.index ?? 0
    if (start > last) nodes.push(text.slice(last, start))
    nodes.push(
      match[1] !== undefined
        ? <strong key={start}>{match[1]}</strong>
        : <em key={start}>{match[2]}</em>,
    )
    last = start + match[0].length
  }
  if (last < text.length) nodes.push(text.slice(last))
  return nodes
}
