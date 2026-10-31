import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { BookDetail, BookGlossary, BookProgress, BookSummary } from "@/lib/api"

const api = vi.hoisted(() => ({
  getUserSettings: vi.fn(),
  listBooks: vi.fn(),
  createBook: vi.fn(),
  getBook: vi.fn(),
  getBookProgress: vi.fn(),
  getBookGlossary: vi.fn(),
  getWritingWords: vi.fn(),
  startReadingSession: vi.fn(),
  updateBook: vi.fn(),
}))
vi.mock("@/lib/api", () => api)
vi.mock("next/navigation", () => ({ useParams: () => ({ id: "book-1" }) }))
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({ t: (key: string, vars?: Record<string, unknown>) => `${key.split(".").at(-1)}${vars ? JSON.stringify(vars) : ""}` }),
}))
vi.mock("@/components/book-session", () => ({ BookSession: () => <div data-testid="book-session" /> }))
vi.mock("@/components/book-triage", () => ({ BookTriage: () => <div data-testid="book-triage" /> }))
vi.mock("@/components/words-per-page-chart", () => ({ WordsPerPageChart: () => <div data-testid="chart" /> }))

import BooksPage from "@/app/(app)/books/page"
import BookPage from "@/app/(app)/books/[id]/page"
import BookGlossaryPage from "@/app/(app)/books/[id]/glossary/page"
import { BookWordsStrip } from "@/components/book-words-strip"

const book = {
  id: "book-1", title: "La sombra del viento", author: "Carlos Ruiz Zafón", language: "es", status: "reading",
  created_at: "2026-10-31T00:00:00Z", updated_at: "2026-10-31T00:00:00Z",
}
const summary: BookSummary = {
  ...book, sessions: 3, words_marked: 40, open_session_id: null, rate_series: [9, 6, 3], last_band: "comfortable",
} as BookSummary
const settings = { default_target_lang: "es", language_profiles: [{ l2: "es", active: true }, { l2: "fr", active: true }] }

describe("BooksPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getUserSettings.mockResolvedValue(settings)
    api.listBooks.mockResolvedValue([summary])
    api.createBook.mockResolvedValue(book)
  })

  it("lists books with their sessions, band and a falling line", async () => {
    render(<BooksPage />)
    const card = await screen.findByTestId("book-card")

    expect(card).toHaveTextContent("La sombra del viento")
    expect(card).toHaveTextContent("band_comfortable")
    expect(screen.getByTestId("sparkline")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /glossary/ })).toHaveAttribute("href", "/books/book-1/glossary")
    expect(screen.getByRole("link", { name: "open" })).toHaveAttribute("href", "/books/book-1")
  })

  it("offers to continue a book with an open session", async () => {
    api.listBooks.mockResolvedValue([{ ...summary, open_session_id: "s1" }])
    render(<BooksPage />)

    expect(await screen.findByRole("link", { name: "continueReading" })).toBeInTheDocument()
  })

  it("adds a book in a studied language", async () => {
    api.listBooks.mockResolvedValue([])
    render(<BooksPage />)
    expect(await screen.findByTestId("books-empty")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /newBook/ }))
    fireEvent.change(screen.getByLabelText("titleLabel"), { target: { value: " Marianela " } })
    fireEvent.change(screen.getByLabelText("authorLabel"), { target: { value: "Galdós" } })
    fireEvent.click(screen.getByRole("button", { name: "addBook" }))

    await waitFor(() => expect(api.createBook).toHaveBeenCalledWith({ title: "Marianela", author: "Galdós", language: "es" }))
  })

  it("says so when the books cannot be loaded", async () => {
    api.listBooks.mockRejectedValue(new Error("down"))
    render(<BooksPage />)

    expect(await screen.findByRole("alert")).toHaveTextContent("loadFailed")
  })
})

describe("BookPage", () => {
  const idle: BookDetail = { book: book as BookDetail["book"], session: null }
  const progress = { book, sessions: [{ id: "s0" }], pages: [], trend: null, latest_band: null, stays_hard: false, estimate: true } as unknown as BookProgress

  beforeEach(() => {
    vi.clearAllMocks()
    api.getBook.mockResolvedValue(idle)
    api.getBookProgress.mockResolvedValue(progress)
    api.startReadingSession.mockResolvedValue({ id: "s1" })
  })

  it("starts a session from the page you begin on", async () => {
    render(<BookPage />)
    fireEvent.change(await screen.findByLabelText("startPageLabel"), { target: { value: "37" } })
    fireEvent.click(screen.getByRole("button", { name: "startReading" }))

    await waitFor(() => expect(api.startReadingSession).toHaveBeenCalledWith("book-1", 37))
  })

  it("resumes an open session straight into the capture bar", async () => {
    api.getBook.mockResolvedValue({ book, session: { id: "s1", marks: [] } })
    render(<BookPage />)

    expect(await screen.findByTestId("book-session")).toBeInTheDocument()
    expect(screen.queryByTestId("start-reading")).not.toBeInTheDocument()
  })

  it("links to the glossary and to writing about what you read, and shows the chart", async () => {
    render(<BookPage />)

    expect(await screen.findByRole("link", { name: /openGlossary/ })).toHaveAttribute("href", "/books/book-1/glossary")
    expect(screen.getByRole("link", { name: /writeAbout/ })).toHaveAttribute("href", "/entries/new?book=book-1")
    expect(screen.getByTestId("chart")).toBeInTheDocument()
  })

  it("lets you choose words from the last session again", async () => {
    render(<BookPage />)
    fireEvent.click(await screen.findByTestId("finish-last"))

    expect(await screen.findByTestId("book-triage")).toBeInTheDocument()
  })
})

describe("BookGlossaryPage", () => {
  const glossary: BookGlossary = {
    book: book as BookGlossary["book"],
    words: [
      { key: "atar", lemma: "atar", surfaces: ["atadas"], times_marked: 2, pages: [3, 9], status: "learning", skipped: false,
        sentences: [{ sentence: "Tenía las manos atadas.", page: 3 }], meaning: "to tie", gloss: "tie up", has_card: true },
      { key: "cinta", lemma: "cinta", surfaces: ["cinta"], times_marked: 1, pages: [4], status: null, skipped: true,
        sentences: [], meaning: "", gloss: "", has_card: false },
    ],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    api.getBookGlossary.mockResolvedValue(glossary)
  })

  it("lists every word with its sentence, pages and meaning", async () => {
    render(<BookGlossaryPage />)
    const rows = await screen.findAllByTestId("glossary-row")

    expect(rows).toHaveLength(2)
    expect(rows[0]).toHaveTextContent("Tenía las manos atadas.")
    expect(rows[0]).toHaveTextContent("pagesShort")
    expect(rows[0]).toHaveTextContent("to tie")
    expect(rows[1]).toHaveTextContent("noMeaningYet")
  })

  it("hides each meaning in the self-quiz until you reveal it, and counts what you remembered", async () => {
    render(<BookGlossaryPage />)
    await screen.findAllByTestId("glossary-row")
    fireEvent.click(screen.getByTestId("quiz-toggle"))

    expect(screen.queryByText("to tie")).not.toBeInTheDocument()
    fireEvent.click(screen.getAllByRole("button", { name: "showMeaning" })[0])
    expect(screen.getByTestId("glossary-meaning")).toHaveTextContent("to tie")
    fireEvent.click(screen.getByRole("button", { name: "remembered" }))

    expect(screen.getByTestId("quiz-score")).toHaveTextContent('"remembered":1')
    fireEvent.click(screen.getByTestId("quiz-toggle"))
    expect(screen.getByTestId("glossary-meaning")).toBeInTheDocument()
  })

  it("is empty before anything is marked", async () => {
    api.getBookGlossary.mockResolvedValue({ ...glossary, words: [] })
    render(<BookGlossaryPage />)

    expect(await screen.findByTestId("glossary-empty")).toBeInTheDocument()
  })
})

describe("BookWordsStrip", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getWritingWords.mockResolvedValue({
      book: { id: "book-1", title: "La sombra del viento", language: "es" },
      words: [{ lemma: "atar", surface: "atadas", gloss: "tie up", status: "learning", times_marked: 2 }],
    })
  })

  it("pre-fills the week's book words when the editor is opened from a book", async () => {
    window.history.pushState({}, "", "/entries/new?book=book-1")
    render(<BookWordsStrip />)

    expect(await screen.findByTestId("book-words-strip")).toHaveTextContent("atar")
    expect(api.getWritingWords).toHaveBeenCalledWith("book-1")
  })

  it("stays out of the way on a plain new entry", async () => {
    window.history.pushState({}, "", "/entries/new")
    render(<BookWordsStrip />)

    await waitFor(() => expect(screen.queryByTestId("book-words-strip")).not.toBeInTheDocument())
    expect(api.getWritingWords).not.toHaveBeenCalled()
  })
})
