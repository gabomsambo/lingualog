import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const api = vi.hoisted(() => ({
  getPlacementCheck: vi.fn(),
  submitPlacementCheck: vi.fn(),
}))
vi.mock("@/lib/api", () => api)
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    t: (key: string, vars?: Record<string, unknown>) => `${key.split(".").at(-1)}${vars ? JSON.stringify(vars) : ""}`,
    intl: { formatNumber: (value: number) => String(value) },
  }),
}))

import { PlacementCheck } from "@/components/placement-check"

const check = {
  language: "es",
  words: ["mesa", "silla", "casa"],
  bands: [["mesa", "silla"], ["casa"]],
  result: null,
}

describe("PlacementCheck", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getPlacementCheck.mockResolvedValue(check)
    api.submitPlacementCheck.mockResolvedValue({
      v: 1, estimate: 500, sample_size: 3, known: ["mesa"], checked_at: "2026-11-10T10:00:00Z",
    })
  })

  it("taps words and submits only the ones the learner knows", async () => {
    const onResult = vi.fn()
    render(<PlacementCheck language="es" open onOpenChange={vi.fn()} onResult={onResult} />)

    expect(await screen.findByTestId("placement-words")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "mesa" }))
    fireEvent.click(screen.getByRole("button", { name: "casa" }))
    expect(screen.getByRole("button", { name: "mesa" })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByRole("button", { name: "casa" })).toHaveAttribute("aria-pressed", "true")

    fireEvent.click(screen.getByRole("button", { name: "placementSubmit" }))
    await waitFor(() => expect(api.submitPlacementCheck).toHaveBeenCalledWith("es", ["mesa", "casa"]))
    expect(onResult).toHaveBeenCalledWith(expect.objectContaining({ estimate: 500 }))
  })

  it("lets a tap be undone", async () => {
    render(<PlacementCheck language="es" open onOpenChange={vi.fn()} />)
    const word = await screen.findByRole("button", { name: "mesa" })
    fireEvent.click(word)
    fireEvent.click(word)
    expect(word).toHaveAttribute("aria-pressed", "false")
  })

  it("reports a failed check without closing", async () => {
    api.submitPlacementCheck.mockRejectedValue(new Error("down"))
    const onOpenChange = vi.fn()
    render(<PlacementCheck language="es" open onOpenChange={onOpenChange} />)
    await screen.findByTestId("placement-words")
    fireEvent.click(screen.getByRole("button", { name: "placementSubmit" }))
    expect(await screen.findByText("placementFailed")).toBeInTheDocument()
    expect(onOpenChange).not.toHaveBeenCalled()
  })
})
