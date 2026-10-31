import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { Book, BookMark, ReadingSessionSummary } from "@/lib/api"

const api = vi.hoisted(() => ({
  markWord: vi.fn(),
  unmarkWord: vi.fn(),
  endReadingSession: vi.fn(),
  getBook: vi.fn(),
  readPagePhoto: vi.fn(),
}))
vi.mock("@/lib/api", () => api)
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({ t: (key: string, vars?: Record<string, unknown>) => `${key.split(".").at(-1)}${vars ? JSON.stringify(vars) : ""}` }),
}))
const lookupSheet = vi.hoisted(() => ({ context: null as unknown }))
vi.mock("@/components/lookup-sheet", () => ({
  LookupSheet: ({ context, open }: { context: unknown; open: boolean }) => {
    lookupSheet.context = open ? context : null
    return open ? <div data-testid="lookup-open" /> : null
  },
}))
vi.mock("@/components/book-page-photo", () => ({ BookPagePhoto: () => <div data-testid="page-photo" /> }))

import { BookSession } from "@/components/book-session"

const book: Book = {
  id: "book-1", title: "La sombra del viento", author: null, language: "es", status: "reading",
  created_at: "2026-10-31T00:00:00Z", updated_at: "2026-10-31T00:00:00Z",
}
const session: ReadingSessionSummary = {
  id: "session-1", started_at: "2026-10-31T10:00:00Z", ended_at: null, page_from: 37, page_to: null,
  pages_read: null, words_marked: 0, words_per_page: null, band: null,
}

function mark(overrides: Partial<BookMark> = {}): BookMark & { created: boolean } {
  return {
    id: "m1", surface: "estremecí", sentence: "Me estremecí.", page: 37, created_at: "2026-10-31T10:01:00Z",
    times_marked: 1, in_notebook: false, created: true, ...overrides,
  }
}

function setup(initialMarks: BookMark[] = []) {
  const onEnded = vi.fn()
  render(<BookSession book={book} session={session} initialMarks={initialMarks} onEnded={onEnded} />)
  return { onEnded }
}

describe("BookSession capture bar", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.markWord.mockResolvedValue(mark())
    api.unmarkWord.mockResolvedValue(undefined)
    api.getBook.mockResolvedValue({ book, session: { ...session, marks: [mark({ id: "m9", surface: "cinta" })] } })
  })

  it("only marks: sends the word, sentence and page and keeps the page for the next word", async () => {
    setup()
    fireEvent.change(screen.getByLabelText("wordLabel"), { target: { value: " estremecí " } })
    fireEvent.change(screen.getByLabelText("sentenceLabel"), { target: { value: "Me estremecí." } })
    fireEvent.click(screen.getByRole("button", { name: /mark$/ }))

    await waitFor(() => expect(api.markWord).toHaveBeenCalledWith("book-1", "session-1", { word: "estremecí", sentence: "Me estremecí.", page: 37 }))
    expect(await screen.findByText("estremecí")).toBeInTheDocument()
    expect(screen.getByLabelText("wordLabel")).toHaveValue("")
    expect(screen.getByLabelText("sentenceLabel")).toHaveValue("")
    expect(screen.getByLabelText("pageLabel")).toHaveValue("37")
    expect(api.getBook).not.toHaveBeenCalled()
  })

  it("marks with Enter and shows how often a word came back", async () => {
    api.markWord.mockResolvedValue(mark({ times_marked: 3 }))
    setup()
    fireEvent.change(screen.getByLabelText("wordLabel"), { target: { value: "estremecí" } })
    fireEvent.submit(screen.getByTestId("capture-bar"))

    expect(await screen.findByTestId("mark-times")).toHaveTextContent("×3")
  })

  it("will not mark an empty word", () => {
    setup()
    expect(screen.getByRole("button", { name: /mark$/ })).toBeDisabled()
    expect(screen.getByRole("button", { name: /needThisNow/ })).toBeDisabled()
  })

  it("undoes a mark made by mistake", async () => {
    setup([mark()])
    fireEvent.click(screen.getByRole("button", { name: /unmark/ }))

    await waitFor(() => expect(api.unmarkWord).toHaveBeenCalledWith("book-1", "session-1", "m1"))
    await waitFor(() => expect(screen.queryByText("estremecí")).not.toBeInTheDocument())
  })

  it("shows the card at once for 'I need this now', in this session on this page, then refreshes the marks", async () => {
    setup()
    fireEvent.change(screen.getByLabelText("wordLabel"), { target: { value: "cinta" } })
    fireEvent.change(screen.getByLabelText("pageLabel"), { target: { value: "41" } })
    fireEvent.click(screen.getByRole("button", { name: /needThisNow/ }))

    expect(await screen.findByTestId("lookup-open")).toBeInTheDocument()
    expect(lookupSheet.context).toEqual({
      text: "cinta", sentence: undefined, language: "es", source: "book_session", sourceId: "session-1", page: 41,
    })
    expect(api.markWord).not.toHaveBeenCalled()
  })

  it("ends the session on the page you stopped at", async () => {
    api.endReadingSession.mockResolvedValue({ ...session, ended_at: "2026-10-31T11:00:00Z", page_to: 52 })
    const { onEnded } = setup()
    fireEvent.click(screen.getByTestId("end-session"))
    fireEvent.change(screen.getByLabelText("lastPageLabel"), { target: { value: "52" } })
    fireEvent.click(screen.getByRole("button", { name: /endConfirm/ }))

    await waitFor(() => expect(api.endReadingSession).toHaveBeenCalledWith("book-1", "session-1", 52))
    await waitFor(() => expect(onEnded).toHaveBeenCalled())
  })

  it("says so when a mark could not be saved and keeps the word", async () => {
    api.markWord.mockRejectedValue(new Error("down"))
    setup()
    fireEvent.change(screen.getByLabelText("wordLabel"), { target: { value: "cinta" } })
    fireEvent.submit(screen.getByTestId("capture-bar"))

    expect(await screen.findByRole("alert")).toHaveTextContent("markFailed")
    expect(screen.getByLabelText("wordLabel")).toHaveValue("cinta")
  })
})
