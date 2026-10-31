import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const api = vi.hoisted(() => ({ getReviewSummary: vi.fn() }))
vi.mock("@/lib/api", () => api)
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({ t: (key: string, vars?: Record<string, unknown>) => `${key.split(".").at(-1)}${vars ? JSON.stringify(vars) : ""}` }),
}))

import { ReviewDueCard } from "@/components/review-due-card"

const row = (language: string, total: number, newCount = 0) => ({
  language, due: total - newCount, new: newCount, new_available: newCount, new_remaining: 10, total, backlog: 0, at_risk: 0, suggest_catchup: false,
})

describe("ReviewDueCard", () => {
  beforeEach(() => vi.clearAllMocks())

  it("shows how many words are due and links into the review", async () => {
    api.getReviewSummary.mockResolvedValue({ languages: [row("es", 7)], total: 7, new: 0, at_risk: 0 })
    render(<ReviewDueCard />)
    expect(await screen.findByTestId("review-due-count")).toHaveTextContent('"count":7')
    expect(screen.getByRole("link", { name: "reviewStartReview" })).toHaveAttribute("href", "/review?language=es")
  })

  it("counts new words apart, like Anki", async () => {
    api.getReviewSummary.mockResolvedValue({ languages: [row("es", 3, 2)], total: 3, new: 2, at_risk: 0 })
    render(<ReviewDueCard />)

    expect(await screen.findByTestId("review-new-count")).toHaveTextContent('"count":2')
  })

  it("opens the first language that has something waiting", async () => {
    api.getReviewSummary.mockResolvedValue({ languages: [row("es", 0), row("fr", 3)], total: 3, at_risk: 2 })
    render(<ReviewDueCard />)
    await screen.findByTestId("review-due-count")
    expect(screen.getByRole("link", { name: "reviewStartReview" })).toHaveAttribute("href", "/review?language=fr")
    expect(screen.getByText(/reviewAtRiskCount/)).toHaveTextContent('"count":2')
  })

  it("says everything is caught up when nothing is due", async () => {
    api.getReviewSummary.mockResolvedValue({ languages: [row("es", 0)], total: 0, at_risk: 0 })
    render(<ReviewDueCard />)
    expect(await screen.findByTestId("review-all-clear")).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "reviewStartReview" })).not.toBeInTheDocument()
  })

  it("stays out of the way when the summary cannot be loaded", async () => {
    api.getReviewSummary.mockRejectedValue(new Error("down"))
    render(<ReviewDueCard />)
    await waitFor(() => expect(api.getReviewSummary).toHaveBeenCalled())
    expect(screen.queryByTestId("review-due-card")).not.toBeInTheDocument()
  })
})
