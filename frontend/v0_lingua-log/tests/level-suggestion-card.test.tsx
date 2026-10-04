import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n/i18n"

const api = vi.hoisted(() => ({
  getLevelSuggestions: vi.fn(),
  acceptLevelSuggestion: vi.fn(),
  dismissLevelSuggestion: vi.fn(),
}))
vi.mock("@/lib/api", () => api)

vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    uiLang: "en",
    t: (key: string, options?: Record<string, unknown>) => {
      const [ns, name] = key.split(".", 2)
      return i18n.t(name, { lng: "en", ...options, ns }) as string
    },
  }),
}))

import { LevelSuggestionCard } from "@/components/level-suggestion-card"

const stepDown = { l2: "es", direction: "down" as const, from_level: 2, to_level: 1 }
const stepUp = { l2: "ja", direction: "up" as const, from_level: 1, to_level: 2 }

beforeEach(() => {
  vi.clearAllMocks()
  api.acceptLevelSuggestion.mockResolvedValue(stepDown)
  api.dismissLevelSuggestion.mockResolvedValue({ ...stepUp, snoozed_until: "2026-10-11T00:00:00+00:00" })
})

describe("LevelSuggestionCard", () => {
  it("shows one step-down card and accepts it in one tap", async () => {
    api.getLevelSuggestions
      .mockResolvedValueOnce({ suggestions: [stepDown, stepUp] })
      .mockResolvedValueOnce({ suggestions: [] })

    render(<LevelSuggestionCard />)

    expect(await screen.findByTestId("level-suggestion-card")).toHaveAttribute("data-direction", "down")
    expect(screen.getByText("Try level 1 for a while?")).toBeInTheDocument()
    expect(screen.queryByText("Ready for level 2?")).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId("level-suggestion-accept"))

    await waitFor(() => expect(api.acceptLevelSuggestion).toHaveBeenCalledWith("es"))
    await waitFor(() => expect(screen.queryByTestId("level-suggestion-card")).not.toBeInTheDocument())
  })

  it("shows the entry language and dismisses that suggestion", async () => {
    api.getLevelSuggestions
      .mockResolvedValueOnce({ suggestions: [stepDown, stepUp] })
      .mockResolvedValueOnce({ suggestions: [stepDown] })

    render(<LevelSuggestionCard l2="ja" />)

    expect(await screen.findByText("Ready for level 2?")).toBeInTheDocument()
    fireEvent.click(screen.getByTestId("level-suggestion-dismiss"))

    await waitFor(() => expect(api.dismissLevelSuggestion).toHaveBeenCalledWith("ja"))
    await waitFor(() => expect(screen.queryByText("Ready for level 2?")).not.toBeInTheDocument())
  })
})
