import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const api = vi.hoisted(() => ({
  getVocabularyItems: vi.fn(),
  getVocabularyLists: vi.fn(),
  deleteVocabularyItem: vi.fn(),
  exportVocabulary: vi.fn(),
}))
vi.mock("@/lib/api", () => api)
vi.mock("@/components/word-card", () => ({ WordCard: () => null }))
vi.mock("@/components/ui/use-toast", () => ({ useToast: () => ({ toast: vi.fn() }) }))
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    t: (key: string, vars?: Record<string, unknown>) => `${key.split(".").at(-1)}${vars ? JSON.stringify(vars) : ""}`,
    intl: { formatNumber: (value: number) => String(value) },
  }),
}))

import VocabularyPage from "@/app/(app)/vocabulary/page"

const item = {
  id: "w1",
  user_id: "u1",
  term: "aprovechar",
  lemma: "aprovechar",
  language: "es",
  status: "learning",
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-01T10:00:00Z",
  card_status: "ok",
  card: { sense_in_context: "to make use of", part_of_speech: "verb" },
  example_sentence: "Voy a aprovechar el día.",
  tags: [],
}

const lists = {
  total: 12,
  smart: [
    { id: "due", count: 5 },
    { id: "never_used", count: 7 },
  ],
  tags: [{ id: "tag:travel", name: "travel", count: 3 }],
  entries: [{ id: "entry:e1", entry_id: "e1", title: "Mi día", date: "2026-11-01", count: 2 }],
  books: null,
}

describe("VocabularyPage lists and export", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getVocabularyItems.mockResolvedValue([item])
    api.getVocabularyLists.mockResolvedValue(lists)
    api.exportVocabulary.mockResolvedValue(new Blob(["csv"]))
    window.URL.createObjectURL = vi.fn(() => "blob:mock")
    window.URL.revokeObjectURL = vi.fn()
  })

  it("shows the lists with their counts", async () => {
    render(<VocabularyPage />)
    expect(await screen.findByRole("button", { name: /listDue/ })).toHaveTextContent("5")
    expect(screen.getByRole("button", { name: /listNeverUsed/ })).toHaveTextContent("7")
    expect(screen.getByRole("button", { name: /travel/ })).toHaveTextContent("3")
    expect(screen.getByRole("button", { name: /Mi día/ })).toHaveTextContent("2")
    expect(api.getVocabularyItems).toHaveBeenCalledWith(undefined, {})
  })

  it("opens a smart list and loads its words", async () => {
    render(<VocabularyPage />)
    fireEvent.click(await screen.findByRole("button", { name: /listDue/ }))
    await waitFor(() =>
      expect(api.getVocabularyItems).toHaveBeenLastCalledWith(undefined, { list: "due" }),
    )
  })

  it("keeps the book list hidden until the books table exists", async () => {
    render(<VocabularyPage />)
    await screen.findByRole("button", { name: /listAll/ })
    expect(screen.queryByText("listFromBooks")).not.toBeInTheDocument()

    api.getVocabularyLists.mockResolvedValue({
      ...lists,
      books: [{ id: "book:b1", book_id: "b1", title: "El principito", count: 1 }],
    })
    render(<VocabularyPage />)
    expect(await screen.findByText("listFromBooks")).toBeInTheDocument()
  })

  it("exports the current selection as CSV or Anki", async () => {
    render(<VocabularyPage />)
    fireEvent.click(await screen.findByRole("button", { name: /exportCsv/ }))
    await waitFor(() => expect(api.exportVocabulary).toHaveBeenCalledWith("csv", undefined, {}))
    expect(window.URL.createObjectURL).toHaveBeenCalled()

    fireEvent.click(screen.getByRole("button", { name: /exportAnki/ }))
    await waitFor(() => expect(api.exportVocabulary).toHaveBeenCalledWith("apkg", undefined, {}))
  })
})
