import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { ReviewCard, ReviewResult } from "@/lib/api"

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
  return { submitReview: vi.fn(), ApiError }
})
vi.mock("@/lib/api", () => api)
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({ t: (key: string) => key.split(".").at(-1) }),
}))

import { ReviewSession } from "@/components/review-session"

function card(overrides: Partial<ReviewCard> = {}): ReviewCard {
  return {
    card_id: "card-1",
    word_id: "word-1",
    card_type: "recognition",
    format: "recognition",
    language: "es",
    lemma: "aprovechar",
    reps: 0,
    is_new: true,
    front: { before: "Hay que ", target: "aprovechar", after: " el día." },
    meaning: "to make good use of",
    gloss: "make use of",
    tap_gloss: "",
    hint: "",
    answer: "aprovechar",
    typed: false,
    accepted: ["aprovechar"],
    status: "learning",
    at_risk: false,
    ...overrides,
  }
}

function result(overrides: Partial<ReviewResult> = {}): ReviewResult {
  return {
    card_id: "card-1", rating: "got_it", due: "2026-11-02T10:00:00Z", reps: 1,
    requeue: false, status: "learning", production_card_added: false, ...overrides,
  }
}

const click = (name: string) => fireEvent.click(screen.getByRole("button", { name }))

describe("ReviewSession", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.submitReview.mockResolvedValue(result())
  })

  it("shows the learner's own sentence with the word marked, and hides the meaning until asked", () => {
    render(<ReviewSession cards={[card()]} onFinished={vi.fn()} />)
    expect(screen.getByTestId("review-front")).toHaveTextContent("Hay que aprovechar el día.")
    expect(screen.getByTestId("review-target")).toHaveTextContent("aprovechar")
    expect(screen.queryByTestId("review-meaning")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "reviewAgain" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "reviewGotIt" })).not.toBeInTheDocument()
  })

  it("offers exactly two answers once the answer is shown", () => {
    render(<ReviewSession cards={[card()]} onFinished={vi.fn()} />)
    click("reviewShowAnswer")
    expect(screen.getByTestId("review-meaning")).toHaveTextContent("to make good use of")
    expect(screen.getByTestId("review-gloss")).toHaveTextContent("make use of")
    const buttons = screen.getAllByRole("button").map((button) => button.textContent?.trim())
    expect(buttons).toEqual(["reviewAgain", "reviewGotIt"])
  })

  it("sends Got it with the card's reps and how long the learner took", async () => {
    const onFinished = vi.fn()
    render(<ReviewSession cards={[card({ reps: 4 })]} onFinished={onFinished} />)
    click("reviewShowAnswer")
    click("reviewGotIt")
    await waitFor(() => expect(onFinished).toHaveBeenCalled())
    expect(api.submitReview).toHaveBeenCalledWith(
      "card-1",
      expect.objectContaining({ rating: "got_it", reps: 4, duration_ms: expect.any(Number) }),
    )
    expect(onFinished).toHaveBeenCalledWith({ reviewed: 1, again: 0, gotIt: 1, nowKnown: 0 })
  })

  it("sends Again and counts it", async () => {
    const onFinished = vi.fn()
    render(<ReviewSession cards={[card()]} onFinished={onFinished} />)
    click("reviewShowAnswer")
    click("reviewAgain")
    await waitFor(() => expect(onFinished).toHaveBeenCalledWith({ reviewed: 1, again: 1, gotIt: 0, nowKnown: 0 }))
    expect(api.submitReview.mock.calls[0][1].rating).toBe("again")
  })

  it("moves through the cards in order and finishes after the last", async () => {
    const onFinished = vi.fn()
    render(
      <ReviewSession
        cards={[card(), card({ card_id: "card-2", front: { before: "", target: "rato", after: "" }, lemma: "rato" })]}
        onFinished={onFinished}
      />,
    )
    expect(screen.getByTestId("review-progress")).toHaveTextContent("reviewProgress")
    click("reviewShowAnswer")
    click("reviewGotIt")
    await waitFor(() => expect(screen.getByTestId("review-front")).toHaveTextContent("rato"))
    expect(onFinished).not.toHaveBeenCalled()
    click("reviewShowAnswer")
    click("reviewGotIt")
    await waitFor(() => expect(onFinished).toHaveBeenCalledTimes(1))
    expect(api.submitReview.mock.calls.map((call) => call[0])).toEqual(["card-1", "card-2"])
  })

  it("shows a card again at the end when it comes due within the session", async () => {
    api.submitReview
      .mockResolvedValueOnce(result({ rating: "again", requeue: true, reps: 1 }))
      .mockResolvedValue(result({ reps: 2 }))
    const onFinished = vi.fn()
    render(
      <ReviewSession
        cards={[card(), card({ card_id: "card-2", front: { before: "", target: "rato", after: "" }, lemma: "rato" })]}
        onFinished={onFinished}
      />,
    )
    click("reviewShowAnswer")
    click("reviewAgain")
    await waitFor(() => expect(screen.getByTestId("review-front")).toHaveTextContent("rato"))
    click("reviewShowAnswer")
    click("reviewGotIt")
    await waitFor(() => expect(screen.getByTestId("review-front")).toHaveTextContent("aprovechar"))
    click("reviewShowAnswer")
    click("reviewGotIt")
    await waitFor(() => expect(onFinished).toHaveBeenCalledWith({ reviewed: 3, again: 1, gotIt: 2, nowKnown: 0 }))
    expect(api.submitReview.mock.calls.map((call) => [call[0], call[1].reps])).toEqual([
      ["card-1", 0], ["card-2", 0], ["card-1", 1],
    ])
  })

  it("counts words that became known", async () => {
    api.submitReview.mockResolvedValue(result({ status: "known" }))
    const onFinished = vi.fn()
    render(<ReviewSession cards={[card()]} onFinished={onFinished} />)
    click("reviewShowAnswer")
    click("reviewGotIt")
    await waitFor(() => expect(onFinished).toHaveBeenCalledWith(expect.objectContaining({ nowKnown: 1 })))
  })

  it("keeps the card and shows an error when the answer cannot be saved", async () => {
    api.submitReview.mockRejectedValueOnce(new Error("offline"))
    const onFinished = vi.fn()
    render(<ReviewSession cards={[card()]} onFinished={onFinished} />)
    click("reviewShowAnswer")
    click("reviewGotIt")
    expect(await screen.findByRole("alert")).toHaveTextContent("reviewSaveFailed")
    expect(onFinished).not.toHaveBeenCalled()
    click("reviewGotIt")
    await waitFor(() => expect(onFinished).toHaveBeenCalledWith(expect.objectContaining({ reviewed: 1 })))
  })

  it("skips a card that was already reviewed elsewhere", async () => {
    api.submitReview.mockRejectedValueOnce(new api.ApiError(409, "stale", { code: "stale_review" }))
    const onFinished = vi.fn()
    render(<ReviewSession cards={[card()]} onFinished={onFinished} />)
    click("reviewShowAnswer")
    click("reviewGotIt")
    await waitFor(() => expect(onFinished).toHaveBeenCalledWith({ reviewed: 0, again: 0, gotIt: 0, nowKnown: 0 }))
  })

  it("ignores a second tap while an answer is being saved", async () => {
    let resolve: (value: ReviewResult) => void = () => undefined
    api.submitReview.mockReturnValue(new Promise<ReviewResult>((done) => (resolve = done)))
    render(<ReviewSession cards={[card()]} onFinished={vi.fn()} />)
    click("reviewShowAnswer")
    click("reviewGotIt")
    fireEvent.click(screen.getByRole("button", { name: "reviewGotIt" }))
    expect(api.submitReview).toHaveBeenCalledTimes(1)
    resolve(result())
  })

  it("answers with the keyboard: space shows the answer, 1 is Again, 2 is Got it", async () => {
    const onFinished = vi.fn()
    render(<ReviewSession cards={[card(), card({ card_id: "card-2" })]} onFinished={onFinished} />)
    fireEvent.keyDown(window, { key: " " })
    expect(screen.getByTestId("review-answer")).toBeInTheDocument()
    fireEvent.keyDown(window, { key: "1" })
    await waitFor(() => expect(api.submitReview).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(screen.queryByTestId("review-answer")).not.toBeInTheDocument())
    fireEvent.keyDown(window, { key: "Enter" })
    fireEvent.keyDown(window, { key: "2" })
    await waitFor(() => expect(api.submitReview).toHaveBeenCalledTimes(2))
    expect(api.submitReview.mock.calls.map((call) => call[1].rating)).toEqual(["again", "got_it"])
  })

  describe("production formats", () => {
    const cloze = card({
      card_type: "production",
      format: "cloze",
      front: { before: "Hay que ", target: "aprovechar", after: " el día." },
      hint: "to make good use of",
      is_new: false,
    })

    it("hides the word in a cloze until the answer is shown", () => {
      render(<ReviewSession cards={[cloze]} onFinished={vi.fn()} />)
      expect(screen.getByTestId("review-blank")).toBeInTheDocument()
      expect(screen.getByTestId("review-front")).not.toHaveTextContent("aprovechar")
      expect(screen.getByTestId("review-hint")).toHaveTextContent("to make good use of")
      click("reviewShowAnswer")
      expect(screen.getByTestId("review-answer-word")).toHaveTextContent("aprovechar")
      expect(screen.getByTestId("review-target")).toHaveTextContent("aprovechar")
    })

    it("keeps the native gloss behind a tap at balanced immersion", () => {
      render(<ReviewSession cards={[{ ...cloze, tap_gloss: "make use of", hint: "" }]} onFinished={vi.fn()} />)
      expect(screen.queryByTestId("review-tap-gloss")).not.toBeInTheDocument()
      click("reviewShowHint")
      expect(screen.getByTestId("review-tap-gloss")).toHaveTextContent("make use of")
    })

    it("asks for the word from its meaning", () => {
      render(
        <ReviewSession
          cards={[card({ card_type: "production", format: "meaning_to_word", hint: "make use of", front: { before: "", target: "", after: "" } })]}
          onFinished={vi.fn()}
        />,
      )
      expect(screen.getByTestId("review-front")).toHaveTextContent("make use of")
      click("reviewShowAnswer")
      expect(screen.getByTestId("review-answer-word")).toHaveTextContent("aprovechar")
    })

    it("checks a typed answer ignoring case and accents, then lets the learner choose", () => {
      const typedCard = { ...cloze, format: "typed_recall" as const, typed: true, answer: "aproveché", accepted: ["aproveche", "aprovechar"] }
      render(<ReviewSession cards={[typedCard]} onFinished={vi.fn()} />)
      expect(screen.queryByRole("button", { name: "reviewShowAnswer" })).not.toBeInTheDocument()
      fireEvent.change(screen.getByLabelText("reviewTypeAnswer"), { target: { value: " APROVECHÉ " } })
      click("reviewCheck")
      expect(screen.getByTestId("review-check-result")).toHaveTextContent("reviewCorrect")
      expect(screen.getByRole("button", { name: "reviewAgain" })).toBeEnabled()
      expect(screen.getByRole("button", { name: "reviewGotIt" })).toBeEnabled()
    })

    it("says so when the typed answer does not match, and still shows the word", () => {
      const typedCard = { ...cloze, format: "typed_recall" as const, typed: true, accepted: ["aprovechar"] }
      render(<ReviewSession cards={[typedCard]} onFinished={vi.fn()} />)
      fireEvent.change(screen.getByLabelText("reviewTypeAnswer"), { target: { value: "aprobar" } })
      click("reviewCheck")
      expect(screen.getByTestId("review-check-result")).toHaveTextContent("reviewNotQuite")
      expect(screen.getByTestId("review-answer-word")).toHaveTextContent("aprovechar")
    })

    it("does not treat an empty typed answer as correct", () => {
      const typedCard = { ...cloze, format: "typed_recall" as const, typed: true }
      render(<ReviewSession cards={[typedCard]} onFinished={vi.fn()} />)
      click("reviewCheck")
      expect(screen.getByTestId("review-check-result")).toHaveTextContent("reviewNotQuite")
    })
  })

  it("flags new and at-risk cards", () => {
    render(<ReviewSession cards={[card({ at_risk: true })]} onFinished={vi.fn()} />)
    expect(screen.getByText("reviewNewWord")).toBeInTheDocument()
    expect(screen.getByText("reviewAtRisk")).toBeInTheDocument()
  })

  it("shows the word on its own when it has no sentence", () => {
    render(<ReviewSession cards={[card({ front: { before: "", target: "rato", after: "" } })]} onFinished={vi.fn()} />)
    expect(screen.getByTestId("review-front")).toHaveTextContent("rato")
  })
})
