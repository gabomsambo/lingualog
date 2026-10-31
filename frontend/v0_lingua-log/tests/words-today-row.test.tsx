import { render, screen, within } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import i18n from "@/i18n/i18n"
import type { TargetWordUse } from "@/lib/side-by-side"

vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    uiLang: "en",
    t: (key: string, options?: Record<string, unknown>) => {
      const [ns, name] = key.split(".", 2)
      return i18n.t(name, { lng: "en", ...options, ns }) as string
    },
  }),
}))

import { WordsTodayRow } from "@/components/words-today-row"

const use = (over: Partial<TargetWordUse>): TargetWordUse => ({
  word_id: over.term || "w", term: "madrugar", status: "used_correctly", form_in_text: "", fix: "", note: "",
  sentence: "", ...over,
})

const row = (uses: TargetWordUse[]) => render(<WordsTodayRow uses={uses} l2="es" l2Dir="ltr" />)

describe("WordsTodayRow", () => {
  it("summarises how the words went", () => {
    row([
      use({ term: "a", status: "used_correctly", form_in_text: "a" }),
      use({ term: "b", status: "used_correctly", form_in_text: "b" }),
      use({ term: "c", status: "used_correctly", form_in_text: "c" }),
      use({ term: "d", status: "used_with_error", form_in_text: "dd", fix: "d", note: "why" }),
      use({ term: "e", status: "not_used" }),
    ])
    expect(screen.getByTestId("words-today-summary")).toHaveTextContent("3 used well · 1 to fix · 1 not used")
  })

  it("shows an error with its fix and reason", () => {
    row([use({ term: "aprovechar", status: "used_with_error", form_in_text: "Aproveché de la tarde", fix: "Aproveché la tarde", note: "No lleva «de»." })])
    const item = screen.getByTestId("word-use")
    expect(item).toHaveTextContent("Aproveché de la tarde")
    expect(item).toHaveTextContent("→ Aproveché la tarde")
    expect(item).toHaveTextContent("No lleva «de».")
  })

  it("asks about an unclear use instead of marking it wrong", () => {
    row([use({ term: "sobremesa", status: "unclear", form_in_text: "sobremesa", note: "¿Querías decir «después de comer»?" })])
    const item = screen.getByTestId("word-use")
    expect(item).toHaveTextContent("¿Querías decir")
    expect(item).toHaveTextContent("not marked wrong")
    expect(screen.getByTestId("words-today-summary")).toHaveTextContent("1 to check")
    expect(screen.getByTestId("words-today-summary")).not.toHaveTextContent("to fix")
  })

  it("celebrates a word that just became Mastered and explains progress for a Known one", () => {
    row([
      use({ term: "a", form_in_text: "a", word_status: "mastered", became_mastered: true, use_days: 2 }),
      use({ term: "b", form_in_text: "b", word_status: "known", use_days: 1 }),
      use({ term: "c", form_in_text: "c", word_status: "learning", use_days: 1 }),
    ])
    const [mastered, known, learning] = screen.getAllByTestId("word-use")
    expect(within(mastered).getByTestId("word-mastered")).toHaveTextContent("Mastered")
    expect(known).toHaveTextContent("1 of 2 days")
    expect(learning).not.toHaveTextContent("of 2 days")
  })

  it("says a hidden word used from memory counted as a review", () => {
    row([use({ term: "a", form_in_text: "a", credited: true })])
    expect(screen.getByTestId("word-use")).toHaveTextContent("counted as a review")
  })

  it("renders nothing when no words were chosen", () => {
    const { container } = row([])
    expect(container).toBeEmptyDOMElement()
  })
})
