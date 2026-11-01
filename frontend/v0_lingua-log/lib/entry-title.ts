const MAX_WORDS = 6
const MAX_CHARS = 60

/** Title for an entry written without one: its first words, ellipsised when cut. */
export function autoTitle(text: string): string {
  const words = text.trim().split(/\s+/).filter(Boolean)
  if (words.length === 0) return ""
  let title = words.slice(0, MAX_WORDS).join(" ").replace(/[.,;:!?¡¿\s]+$/u, "")
  let cut = words.length > MAX_WORDS
  if (title.length > MAX_CHARS) {
    title = title.slice(0, MAX_CHARS).trimEnd()
    cut = true
  }
  return cut ? `${title}…` : title
}
