import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

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
  return { readPagePhoto: vi.fn(), markWord: vi.fn(), unmarkWord: vi.fn(), ApiError }
})
vi.mock("@/lib/api", () => api)
vi.mock("@/lib/books", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/books")>()),
  prepareImage: vi.fn(async (file: Blob) => file),
}))
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({ t: (key: string, vars?: Record<string, unknown>) => `${key.split(".").at(-1)}${vars ? JSON.stringify(vars) : ""}` }),
}))

import { BookPagePhoto } from "@/components/book-page-photo"

const PAGE = {
  readable: true,
  transcription: "Tenía las manos atadas con una cinta. Estremecí al verla.",
  candidates: [
    { surface: "atadas", lemma: "atar", status: null },
    { surface: "cinta", lemma: "cinta", status: "known" },
  ],
  estimate: { unknown_estimate: 1, page_words: 10, band: "comfortable" },
}

function setup(page = 37) {
  const onMarked = vi.fn()
  const onUnmarked = vi.fn()
  render(<BookPagePhoto bookId="book-1" sessionId="session-1" page={page} onMarked={onMarked} onUnmarked={onUnmarked} />)
  return { onMarked, onUnmarked }
}

async function takePhoto() {
  const file = new File(["jpeg"], "page.jpg", { type: "image/jpeg" })
  fireEvent.change(screen.getByTestId("page-photo-input"), { target: { files: [file] } })
  await screen.findByTestId("page-photo-text")
}

describe("BookPagePhoto", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.readPagePhoto.mockResolvedValue(PAGE)
    api.markWord.mockResolvedValue({ id: "m1", surface: "atadas", times_marked: 1, in_notebook: false, created: true })
    api.unmarkWord.mockResolvedValue(undefined)
  })

  it("shows the page text with the guessed words highlighted and the estimate labelled", async () => {
    setup()
    await takePhoto()

    expect(screen.getByRole("button", { name: "atadas" })).toHaveAttribute("data-candidate", "true")
    expect(screen.getByRole("button", { name: "Estremecí" })).not.toHaveAttribute("data-candidate")
    expect(screen.getByTestId("page-photo-estimate")).toHaveTextContent("photoEstimate")
    expect(screen.getByTestId("page-photo-estimate")).toHaveTextContent("estimateLabel")
    expect(api.readPagePhoto).toHaveBeenCalledWith("book-1", expect.any(Blob))
  })

  it("marks a tapped word with its own sentence and the current page, and a second tap undoes it", async () => {
    const { onMarked, onUnmarked } = setup(52)
    await takePhoto()

    fireEvent.click(screen.getByRole("button", { name: "Estremecí" }))
    await waitFor(() =>
      expect(api.markWord).toHaveBeenCalledWith("book-1", "session-1", {
        word: "Estremecí", sentence: "Estremecí al verla.", page: 52,
      }),
    )
    await waitFor(() => expect(onMarked).toHaveBeenCalled())
    expect(screen.getByRole("button", { name: "Estremecí" })).toHaveAttribute("aria-pressed", "true")

    fireEvent.click(screen.getByRole("button", { name: "Estremecí" }))
    await waitFor(() => expect(api.unmarkWord).toHaveBeenCalledWith("book-1", "session-1", "m1"))
    expect(onUnmarked).toHaveBeenCalledWith("m1")
  })

  it("says so when the page could not be read", async () => {
    api.readPagePhoto.mockResolvedValue({ readable: false, transcription: "", candidates: [], estimate: null })
    setup()
    fireEvent.change(screen.getByTestId("page-photo-input"), { target: { files: [new File(["x"], "p.jpg")] } })

    expect(await screen.findByTestId("page-photo-unreadable")).toBeInTheDocument()
  })

  it.each([
    ["photo_rate_limited", "photoRateLimited"],
    ["photo_quota_reached", "photoQuotaReached"],
    ["photo_too_large", "photoTooLarge"],
  ])("explains a refusal: %s", async (code, message) => {
    api.readPagePhoto.mockRejectedValue(new api.ApiError(429, "", { code }))
    setup()
    fireEvent.change(screen.getByTestId("page-photo-input"), { target: { files: [new File(["x"], "p.jpg")] } })

    expect(await screen.findByRole("alert")).toHaveTextContent(message)
    expect(screen.queryByTestId("page-photo-text")).not.toBeInTheDocument()
  })

  it("falls back to a general message for any other failure", async () => {
    api.readPagePhoto.mockRejectedValue(new Error("network"))
    setup()
    fireEvent.change(screen.getByTestId("page-photo-input"), { target: { files: [new File(["x"], "p.jpg")] } })

    expect(await screen.findByRole("alert")).toHaveTextContent("photoFailed")
  })
})
