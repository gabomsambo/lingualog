import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n/i18n"
import type { WordBankWord } from "@/lib/word-bank"

const api = vi.hoisted(() => ({ getWordBank: vi.fn(), postSupportEvent: vi.fn() }))
vi.mock("@/lib/api", () => api)
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    uiLang: "en",
    t: (key: string, options?: Record<string, unknown>) => {
      const [ns, name] = key.split(".", 2)
      return i18n.t(name, { lng: "en", ...options, ns }) as string
    },
  }),
}))

import { WordBankPanel } from "@/components/word-bank-panel"

const word = (id: string, over: Partial<WordBankWord> = {}): WordBankWord => ({
  word_id: id, lemma: id, term: id, status: "learning", reason: "never_used", forms: [id],
  hint: `meaning of ${id}`, hint_mode: "shown", use_days: 0, ...over,
})
const bank = (...words: WordBankWord[]) => ({ language: "es", words })

function setup(text = "", onSelectionChange = vi.fn(), preferredWordIds: string[] = []) {
  const view = render(
    <WordBankPanel language="es" text={text} preferredWordIds={preferredWordIds} onSelectionChange={onSelectionChange} />,
  )
  return { onSelectionChange, ...view }
}

const lastSelection = (fn: ReturnType<typeof vi.fn>) => fn.mock.calls.at(-1)![0]

beforeEach(() => {
  vi.clearAllMocks()
  api.postSupportEvent.mockResolvedValue(undefined)
})

describe("WordBankPanel", () => {
  it("offers the words with their meaning and sends them as the entry's targets", async () => {
    api.getWordBank.mockResolvedValue(bank(word("madrugar"), word("rato")))
    const { onSelectionChange } = setup()
    const chips = await screen.findAllByTestId("word-bank-chip")
    expect(chips).toHaveLength(2)
    expect(within(chips[0]).getByText("madrugar")).toBeInTheDocument()
    expect(within(chips[0]).getByTestId("word-bank-hint")).toHaveTextContent("meaning of madrugar")
    expect(lastSelection(onSelectionChange)).toEqual({ targetWordIds: ["madrugar", "rato"], challengeWordIds: [] })
    expect(screen.getByTestId("word-bank-prompt")).toHaveTextContent("madrugar and rato")
    expect(api.getWordBank).toHaveBeenCalledWith("es", { count: 6 })
  })

  it("starts with the words from a book when the editor was opened to write about it", async () => {
    window.history.pushState({}, "", "/entries/new?book=book-1")
    api.getWordBank.mockResolvedValue({
      ...bank(word("cinta", { reason: "from_book" }), word("rato")),
      book: { id: "book-1", title: "La sombra del viento" },
    })
    setup()
    const chips = await screen.findAllByTestId("word-bank-chip")

    expect(api.getWordBank).toHaveBeenCalledWith("es", { count: 6, book: "book-1" })
    expect(screen.getByTestId("word-bank-book")).toHaveTextContent("Write about La sombra del viento")
    expect(chips[0]).toHaveTextContent("From your book this week")
    window.history.pushState({}, "", "/")
  })

  it("preselects confirmed class words and keeps them visible beside the editor", async () => {
    api.getWordBank.mockResolvedValue(bank(word("clase"), word("rato")))
    setup("", vi.fn(), ["clase"])
    const chips = await screen.findAllByTestId("word-bank-chip")

    expect(api.getWordBank).toHaveBeenCalledWith("es", { count: 6, include: ["clase"] })
    expect(screen.getByTestId("word-bank-class-note")).toHaveTextContent("Confirmed words from class")
    expect(within(chips[0]).getByRole("img", { name: "Confirmed words from class are ready to try. Choose what fits." })).toBeInTheDocument()
    expect(within(chips[0]).getByRole("button", { name: "Stop keeping clase" })).toHaveAttribute("aria-pressed", "true")
    expect(chips[0]).toHaveAttribute("data-used", "false")
  })

  it("is the plain bank, with no book banner, on an ordinary new entry", async () => {
    window.history.pushState({}, "", "/entries/new")
    api.getWordBank.mockResolvedValue(bank(word("rato")))
    setup()
    await screen.findAllByTestId("word-bank-chip")

    expect(screen.queryByTestId("word-bank-book")).toBeNull()
    expect(api.getWordBank.mock.calls[0][1].book).toBeUndefined()
    window.history.pushState({}, "", "/")
  })

  it("ticks a chip as the draft uses the word and counts them", async () => {
    api.getWordBank.mockResolvedValue(bank(word("madrugar", { forms: ["madrugar", "madrugué"] }), word("rato")))
    const { rerender } = setup("Hoy no escribí nada.")
    await screen.findAllByTestId("word-bank-chip")
    expect(screen.getAllByTestId("word-bank-chip").map((chip) => chip.dataset.used)).toEqual(["false", "false"])

    rerender(<WordBankPanel language="es" text="Ayer madrugué mucho." onSelectionChange={vi.fn()} />)
    expect(screen.getAllByTestId("word-bank-chip").map((chip) => chip.dataset.used)).toEqual(["true", "false"])
    expect(screen.getByTestId("word-bank-count")).toHaveTextContent("1 of 2")
  })

  it("keeps the meaning behind a tap when the policy says so, and logs the tap", async () => {
    api.getWordBank.mockResolvedValue(bank(word("rato", { hint_mode: "tap" })))
    setup()
    const chip = await screen.findByTestId("word-bank-chip")
    expect(within(chip).queryByTestId("word-bank-hint")).toBeNull()
    fireEvent.click(within(chip).getByRole("button", { name: "Show meaning" }))
    expect(within(chip).getByTestId("word-bank-hint")).toHaveTextContent("meaning of rato")
    expect(api.postSupportEvent).toHaveBeenCalledWith(expect.objectContaining({ kind: "reveal_gloss", l2: "es" }))
  })

  it("shuffle keeps pinned words and asks for others", async () => {
    api.getWordBank
      .mockResolvedValueOnce(bank(word("a"), word("b"), word("c")))
      .mockResolvedValueOnce(bank(word("d"), word("e")))
    const { onSelectionChange } = setup()
    await screen.findAllByTestId("word-bank-chip")
    fireEvent.click(screen.getByRole("button", { name: "Keep b" }))
    fireEvent.click(screen.getByRole("button", { name: /Shuffle/ }))

    await waitFor(() =>
      expect(screen.getAllByTestId("word-bank-chip").map((chip) => within(chip).getByText(/^[a-e]$/).textContent)).toEqual([
        "b", "d", "e",
      ]),
    )
    expect(api.getWordBank).toHaveBeenLastCalledWith("es", { count: 5, exclude: ["a", "b", "c"] })
    expect(lastSelection(onSelectionChange).targetWordIds).toEqual(["b", "d", "e"])
  })

  it("challenge mode hides the words, shows the meanings, and a peeked word stops being a challenge", async () => {
    api.getWordBank.mockResolvedValue(bank(word("madrugar", { hint_mode: "tap" }), word("rato", { hint_mode: "tap" })))
    const { onSelectionChange } = setup()
    await screen.findAllByTestId("word-bank-chip")
    fireEvent.click(screen.getByRole("switch"))

    expect(screen.queryByText("madrugar")).toBeNull()
    expect(screen.getAllByTestId("word-bank-hint")).toHaveLength(2)
    expect(screen.queryByTestId("word-bank-prompt")).toBeNull()
    expect(lastSelection(onSelectionChange)).toEqual({
      targetWordIds: ["madrugar", "rato"], challengeWordIds: ["madrugar", "rato"],
    })

    fireEvent.click(screen.getAllByRole("button", { name: "Show word" })[0])
    expect(screen.getByText("madrugar")).toBeInTheDocument()
    expect(lastSelection(onSelectionChange)).toEqual({
      targetWordIds: ["madrugar", "rato"], challengeWordIds: ["rato"],
    })
  })

  it("never hides a word that has no meaning to go on", async () => {
    api.getWordBank.mockResolvedValue(bank(word("madrugar", { hint: "" })))
    const { onSelectionChange } = setup()
    await screen.findByTestId("word-bank-chip")
    fireEvent.click(screen.getByRole("switch"))
    expect(screen.getByText("madrugar")).toBeInTheDocument()
    expect(lastSelection(onSelectionChange).challengeWordIds).toEqual([])
  })

  it("points to the notebook when there is nothing to offer", async () => {
    api.getWordBank.mockResolvedValue(bank())
    const { onSelectionChange } = setup()
    expect(await screen.findByTestId("word-bank-empty")).toHaveTextContent("Save a few words")
    expect(screen.getByRole("link", { name: "Open your notebook" })).toHaveAttribute("href", "/vocabulary")
    expect(lastSelection(onSelectionChange)).toEqual({ targetWordIds: [], challengeWordIds: [] })
  })

  it("says so and offers a retry when the bank cannot load, and sends no words", async () => {
    api.getWordBank.mockRejectedValueOnce(new Error("500")).mockResolvedValueOnce(bank(word("rato")))
    const { onSelectionChange } = setup()
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded")
    expect(lastSelection(onSelectionChange).targetWordIds).toEqual([])
    fireEvent.click(screen.getByRole("button", { name: "Try again" }))
    expect(await screen.findByTestId("word-bank-chip")).toBeInTheDocument()
  })

  it("loads a fresh bank when the language changes", async () => {
    api.getWordBank.mockResolvedValueOnce(bank(word("rato"))).mockResolvedValueOnce({ language: "fr", words: [word("bouger")] })
    const { rerender } = setup()
    await screen.findByText("rato")
    rerender(<WordBankPanel language="fr" text="" onSelectionChange={vi.fn()} />)
    expect(await screen.findByText("bouger")).toBeInTheDocument()
    expect(api.getWordBank).toHaveBeenLastCalledWith("fr", { count: 6 })
  })
})
