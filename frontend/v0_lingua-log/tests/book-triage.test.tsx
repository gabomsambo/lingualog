import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { Book, ReadingSessionSummary, TriageItem } from "@/lib/api"

const api = vi.hoisted(() => {
  class ApiError extends Error {
    status: number
    detail: unknown
    constructor(status: number, body: string, detail: unknown) {
      super(body)
      this.status = status
      this.detail = detail
    }
  }
  return {
    buildSessionCards: vi.fn(),
    addVocabularyItem: vi.fn(),
    updateVocabularyItem: vi.fn(),
    skipMarks: vi.fn(),
    ApiError,
  }
})
vi.mock("@/lib/api", () => api)
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({ t: (key: string, vars?: Record<string, unknown>) => `${key.split(".").at(-1)}${vars ? JSON.stringify(vars) : ""}` }),
}))

import { BookTriage } from "@/components/book-triage"

const book = { id: "book-1", title: "La sombra del viento", language: "es" } as Book
const session = {
  id: "session-1", page_from: 37, page_to: 52, words_marked: 14, words_per_page: 0.9, band: "comfortable",
} as ReadingSessionSummary

function item(overrides: Partial<TriageItem> = {}): TriageItem {
  return {
    key: "atar", lemma: "atar", surface: "atadas", sentence: "Tenía las manos atadas.", page: 3, times_marked: 3,
    recurring: true,
    card: { sense_in_context: "to tie", gloss_l1: "tie up" } as TriageItem["card"],
    card_status: "ok", encounter_id: "enc-1", encounter_ids: ["enc-1", "enc-2"],
    ...overrides,
  }
}

const cinta = item({ key: "cinta", lemma: "cinta", recurring: false, times_marked: 1, encounter_id: "enc-3", encounter_ids: ["enc-3"] })

function setup(items: TriageItem[]) {
  api.buildSessionCards.mockResolvedValue({ items, recurring: items.filter((i) => i.recurring).length })
  const onDone = vi.fn()
  render(<BookTriage book={book} session={session} onDone={onDone} />)
  return { onDone }
}

describe("BookTriage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.addVocabularyItem.mockResolvedValue({ id: "word-1" })
    api.updateVocabularyItem.mockResolvedValue({ id: "word-1" })
    api.skipMarks.mockResolvedValue({ skipped: 1 })
  })

  it("summarises the session and builds the cards once", async () => {
    setup([item()])
    await screen.findAllByTestId("triage-item")

    expect(screen.getByTestId("session-summary")).toHaveTextContent("summaryPages")
    expect(screen.getByTestId("session-summary")).toHaveTextContent("summaryRate")
    expect(api.buildSessionCards).toHaveBeenCalledTimes(1)
    expect(api.buildSessionCards).toHaveBeenCalledWith("book-1", "session-1")
  })

  it("lists words that came back before the one-offs", async () => {
    setup([item(), cinta])
    const rows = await screen.findAllByTestId("triage-item")

    expect(rows[0]).toHaveTextContent("atar")
    expect(rows[1]).toHaveTextContent("cinta")
    const headings = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)
    expect(headings).toEqual(["recurringTitle", "oneOffTitle"])
  })

  it("Study saves the word with its sentence and the cached card, then starts studying it", async () => {
    setup([item()])
    fireEvent.click(await screen.findByRole("button", { name: "study" }))

    await waitFor(() =>
      expect(api.addVocabularyItem).toHaveBeenCalledWith({
        term: "atar", language: "es", example_sentence: "Tenía las manos atadas.", encounter_id: "enc-1",
      }),
    )
    await waitFor(() => expect(api.updateVocabularyItem).toHaveBeenCalledWith("word-1", { status: "learning" }))
    expect(await screen.findByTestId("triage-empty")).toBeInTheDocument()
  })

  it("'I know it' saves the word as known", async () => {
    setup([item()])
    fireEvent.click(await screen.findByRole("button", { name: "iKnowIt" }))

    await waitFor(() => expect(api.updateVocabularyItem).toHaveBeenCalledWith("word-1", { status: "known" }))
  })

  it("keeps the word as New and says so when today's new-word limit is full", async () => {
    api.updateVocabularyItem.mockRejectedValue(new api.ApiError(409, "", { code: "daily_new_words_cap" }))
    setup([item()])
    fireEvent.click(await screen.findByRole("button", { name: "study" }))

    expect(await screen.findByRole("status")).toHaveTextContent("capReached")
    await waitFor(() => expect(screen.queryByTestId("triage-item")).not.toBeInTheDocument())
  })

  it("Skip leaves the marks in the glossary without saving a word", async () => {
    setup([item()])
    fireEvent.click(await screen.findByRole("button", { name: "skip" }))

    await waitFor(() => expect(api.skipMarks).toHaveBeenCalledWith("book-1", ["enc-1", "enc-2"]))
    expect(api.addVocabularyItem).not.toHaveBeenCalled()
  })

  it("skips every one-off at once and leaves the recurring words", async () => {
    setup([item(), cinta])
    fireEvent.click(await screen.findByTestId("skip-one-offs"))

    await waitFor(() => expect(api.skipMarks).toHaveBeenCalledWith("book-1", ["enc-3"]))
    await waitFor(() => expect(screen.getAllByTestId("triage-item")).toHaveLength(1))
    expect(screen.getByTestId("triage-item")).toHaveTextContent("atar")
  })

  it("offers a retry for a card the model could not build and never shows an error as the meaning", async () => {
    setup([item({ card: null, card_status: "failed", encounter_id: null })])
    const row = await screen.findByTestId("triage-item")

    expect(within(row).getByRole("button", { name: "retry" })).toBeInTheDocument()
    expect(within(row).queryByRole("button", { name: "study" })).not.toBeInTheDocument()
    expect(row).toHaveTextContent("cardUnavailable")
    fireEvent.click(within(row).getByRole("button", { name: "retry" }))
    await waitFor(() => expect(api.buildSessionCards).toHaveBeenCalledTimes(2))
  })

  it("offers the glossary when nothing is left to choose", async () => {
    const { onDone } = setup([])
    const empty = await screen.findByTestId("triage-empty")

    expect(empty).toHaveTextContent("nothingToChoose")
    fireEvent.click(within(empty).getByRole("button", { name: "backToBook" }))
    expect(onDone).toHaveBeenCalled()
  })
})

describe("BookTriage summary", () => {
  it("names a single page once", async () => {
    api.buildSessionCards.mockResolvedValue({ items: [], recurring: 0 })
    render(<BookTriage book={book} session={{ ...session, page_from: 41, page_to: 41 }} onDone={vi.fn()} />)

    expect(await screen.findByTestId("session-summary")).toHaveTextContent('summaryPage{"page":41}')
  })
})
