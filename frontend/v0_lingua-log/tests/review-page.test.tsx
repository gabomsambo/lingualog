import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { ReviewCard, ReviewSession } from "@/lib/api"

const api = vi.hoisted(() => ({
  getUserSettings: vi.fn(),
  getReviewSession: vi.fn(),
  submitReview: vi.fn(),
}))
vi.mock("@/lib/api", () => api)
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({ t: (key: string, vars?: Record<string, unknown>) => `${key.split(".").at(-1)}${vars ? JSON.stringify(vars) : ""}` }),
}))

import ReviewPage from "@/app/(app)/review/page"

const settings = (languages: string[]) => ({
  default_target_lang: languages[0],
  language_profiles: languages.map((l2) => ({ l2, immersion_level: 1, proficiency: "B1", active: true })),
})

function card(id: string, lemma = "aprovechar"): ReviewCard {
  return {
    card_id: id, word_id: `w-${id}`, card_type: "recognition", format: "recognition", language: "es", lemma,
    reps: 0, is_new: true, front: { before: "", target: lemma, after: "" }, meaning: "to use well", gloss: "",
    tap_gloss: "", hint: "", answer: lemma, typed: false, accepted: [lemma], status: "learning", at_risk: false,
  }
}

function session(overrides: Partial<ReviewSession> = {}): ReviewSession {
  return {
    language: "es", mode: "normal", cards: [card("c1")],
    counts: { due: 0, new_available: 1, new_remaining: 10, total: 1, backlog: 0, at_risk: 0, suggest_catchup: false },
    settings: { daily_new_words: 10, desired_retention: 0.9, catchup_daily_budget: 30 },
    catchup: null, ...overrides,
  }
}

describe("ReviewPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.history.pushState({}, "", "/review")
    api.getUserSettings.mockResolvedValue(settings(["es", "fr"]))
    api.getReviewSession.mockResolvedValue(session())
    api.submitReview.mockResolvedValue({ card_id: "c1", rating: "got_it", due: "", reps: 1, requeue: false, status: "learning", production_card_added: false })
  })

  it("starts straight into a session for the default language", async () => {
    render(<ReviewPage />)
    expect(await screen.findByTestId("review-session")).toBeInTheDocument()
    expect(api.getReviewSession).toHaveBeenCalledWith("es", "normal")
  })

  it("opens the language named in the link", async () => {
    window.history.pushState({}, "", "/review?language=fr")
    render(<ReviewPage />)
    await screen.findByTestId("review-session")
    expect(api.getReviewSession).toHaveBeenCalledWith("fr", "normal")
  })

  it("ignores a language the learner does not study", async () => {
    window.history.pushState({}, "", "/review?language=ja")
    render(<ReviewPage />)
    await screen.findByTestId("review-session")
    expect(api.getReviewSession).toHaveBeenCalledWith("es", "normal")
  })

  it("offers a gentle catch-up when a backlog has built up", async () => {
    api.getReviewSession.mockResolvedValueOnce(
      session({ counts: { due: 90, new_available: 0, new_remaining: 10, total: 90, backlog: 90, at_risk: 40, suggest_catchup: true } }),
    )
    render(<ReviewPage />)
    const offer = await screen.findByTestId("catchup-offer")
    expect(offer).toHaveTextContent('"backlog":90')
    expect(offer).toHaveTextContent('"budget":30')
    expect(screen.queryByTestId("review-session")).not.toBeInTheDocument()

    api.getReviewSession.mockResolvedValueOnce(
      session({ mode: "catchup", catchup: { daily_budget: 30, done_today: 0 }, cards: [card("c1"), card("c2")] }),
    )
    fireEvent.click(screen.getByRole("button", { name: "reviewCatchupStart" }))
    expect(await screen.findByTestId("review-session")).toBeInTheDocument()
    expect(api.getReviewSession).toHaveBeenLastCalledWith("es", "catchup")
    expect(screen.getByTestId("catchup-badge")).toHaveTextContent("reviewCatchupProgress")
  })

  it("lets the learner review normally despite a backlog, without another request", async () => {
    api.getReviewSession.mockResolvedValueOnce(
      session({ counts: { due: 90, new_available: 0, new_remaining: 10, total: 90, backlog: 90, at_risk: 0, suggest_catchup: true } }),
    )
    render(<ReviewPage />)
    await screen.findByTestId("catchup-offer")
    fireEvent.click(screen.getByRole("button", { name: "reviewNormalStart" }))
    expect(await screen.findByTestId("review-session")).toBeInTheDocument()
    expect(api.getReviewSession).toHaveBeenCalledTimes(1)
  })

  it.each([
    ["nothing in study", { due: 0, new_available: 0, new_remaining: 10 }, "reviewNoWordsInStudy"],
    ["today's new words used up", { due: 0, new_available: 4, new_remaining: 0 }, "reviewNewDone"],
    ["reviews waiting but today's budget spent", { due: 50, new_available: 0, new_remaining: 10, backlog: 50 }, "reviewNothingDueBody"],
  ])("explains an empty session: %s", async (_name, counts, message) => {
    api.getReviewSession.mockResolvedValue(
      session({ cards: [], counts: { total: 0, backlog: 0, at_risk: 0, suggest_catchup: false, ...counts } }),
    )
    render(<ReviewPage />)
    expect(await screen.findByTestId("review-empty")).toHaveTextContent(message)
    expect(screen.getByRole("link", { name: /reviewGoVocabulary/ })).toHaveAttribute("href", "/vocabulary")
  })

  it("shows when the review cannot be loaded and retries", async () => {
    api.getReviewSession.mockRejectedValueOnce(new Error("down"))
    render(<ReviewPage />)
    expect(await screen.findByRole("alert")).toHaveTextContent("reviewLoadFailed")
    fireEvent.click(screen.getByRole("button", { name: "reviewRetry" }))
    expect(await screen.findByTestId("review-session")).toBeInTheDocument()
  })

  it("summarises the session and starts another on request", async () => {
    render(<ReviewPage />)
    await screen.findByTestId("review-session")
    fireEvent.click(screen.getByRole("button", { name: "reviewShowAnswer" }))
    fireEvent.click(screen.getByRole("button", { name: /reviewGotIt/ }))
    const done = await screen.findByTestId("review-finished")
    expect(done).toHaveTextContent('"reviewed":1')

    api.getReviewSession.mockResolvedValueOnce(session({ cards: [card("c9", "rato")] }))
    fireEvent.click(screen.getByRole("button", { name: "reviewMore" }))
    await waitFor(() => expect(screen.getByTestId("review-front")).toHaveTextContent("rato"))
    expect(api.getReviewSession).toHaveBeenCalledTimes(2)
  })

  it("offers a language picker only when more than one language is studied", async () => {
    render(<ReviewPage />)
    await screen.findByTestId("review-session")
    expect(screen.getByRole("combobox", { name: "reviewLanguage" })).toBeInTheDocument()
  })

  it("has no picker for a single language", async () => {
    api.getUserSettings.mockResolvedValue(settings(["es"]))
    render(<ReviewPage />)
    await screen.findByTestId("review-session")
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument()
  })
})
