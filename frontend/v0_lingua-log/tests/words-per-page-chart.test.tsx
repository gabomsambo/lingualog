import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import type { BookProgress, ReadingSessionSummary } from "@/lib/api"

vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({ t: (key: string, vars?: Record<string, unknown>) => `${key.split(".").at(-1)}${vars ? JSON.stringify(vars) : ""}` }),
}))

import { WordsPerPageChart } from "@/components/words-per-page-chart"

// jsdom has no layout, so the chart only needs the observer to exist.
vi.stubGlobal("ResizeObserver", class { observe() {} unobserve() {} disconnect() {} })

const session = (rate: number | null, n: number): ReadingSessionSummary => ({
  id: `s${n}`, started_at: "", ended_at: "x", page_from: 1, page_to: 10, pages_read: rate === null ? null : 10,
  words_marked: rate === null ? 4 : rate * 10, words_per_page: rate, band: null,
})
const progress = (overrides: Partial<BookProgress> = {}): BookProgress => ({
  book: { id: "b", title: "T", author: "Ana", language: "es", status: "reading", created_at: "", updated_at: "" },
  sessions: [session(9, 1), session(6, 2), session(3, 3)], pages: [{ page: 1, words: 3, band: "comfortable" }],
  trend: "falling", latest_band: "comfortable", stays_hard: false, estimate: true, ...overrides,
})

describe("WordsPerPageChart", () => {
  it("tells the falling-line story and labels the numbers as an estimate", () => {
    render(<WordsPerPageChart progress={progress()} />)

    expect(screen.getByTestId("trend-falling")).toBeInTheDocument()
    expect(screen.getAllByText("estimateLabel").length).toBeGreaterThan(0)
    expect(screen.getAllByRole("row")).toHaveLength(3)
    expect(screen.getByText('perPage{"count":9}')).toBeInTheDocument()
  })

  it("explains the soft bands without percentages", () => {
    render(<WordsPerPageChart progress={progress()} />)

    for (const band of ["comfortable", "study", "demanding", "hard"]) {
      expect(screen.getByText(`bandRange_${band}`)).toBeInTheDocument()
    }
  })

  it("asks for page numbers when no finished session has pages", () => {
    render(<WordsPerPageChart progress={progress({ sessions: [session(null, 1)], trend: null })} />)

    expect(screen.getByTestId("chart-empty")).toBeInTheDocument()
  })

  it("suggests an easier book, naming the author, once a book stays hard", () => {
    render(<WordsPerPageChart progress={progress({ stays_hard: true })} />)

    expect(screen.getByTestId("stays-hard")).toHaveTextContent("staysHardAuthor")
    expect(screen.getByTestId("stays-hard")).toHaveTextContent("Ana")
  })
})
