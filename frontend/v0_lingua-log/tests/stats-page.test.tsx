import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const api = vi.hoisted(() => ({
  getUserStats: vi.fn(),
  getUserSettings: vi.fn(),
  getVocabularyProgress: vi.fn(),
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

import StatsPage from "@/app/(app)/stats/page"

const userStats = {
  wordCounts: [{ date: "2026-11-09", count: 120 }],
  languageBreakdown: [{ language: "es", count: 870, percentage: 45 }],
  streak: { current: 7, longest: 14, totalWords: 1933 },
}

const settings = {
  default_target_lang: "es",
  language_profiles: [{ l2: "es", immersion_level: 1, proficiency: "B1", active: true }],
}

function progress(overrides: Record<string, unknown> = {}) {
  return {
    language: "es",
    notebook: { new: 3, learning: 2, known: 1, mastered: 1, ignored: 0, total: 7 },
    trend: [
      { date: "2026-11-09", count: 6 },
      { date: "2026-11-10", count: 7 },
    ],
    active_words: 2,
    encounters: {
      by_kind: { lookup: 4, entry_text: 1 },
      reviews: 3,
      per_word: 1.2,
      guide_min: 10,
      guide_max: 12,
    },
    review: {
      due_today: 5,
      new_today: 2,
      forecast: Array.from({ length: 7 }, (_, day) => ({ date: `2026-11-1${day}`, count: day })),
      at_risk: 1,
      true_retention: 0.8,
      reviews_last_7_days: 12,
      minutes_last_7_days: 15,
    },
    week: { reading: 0, journal: 2, reviews: 12, review_minutes: 15, review_share: 0.8, over_budget: true },
    placement: null,
    placement_available: false,
    ...overrides,
  }
}

describe("StatsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.history.pushState({}, "", "/stats")
    api.getUserStats.mockResolvedValue(userStats)
    api.getUserSettings.mockResolvedValue(settings)
    api.getVocabularyProgress.mockResolvedValue(progress())
  })

  it("shows the real writing stats and the notebook counts", async () => {
    render(<StatsPage />)
    expect(await screen.findByText("streakDays")).toBeInTheDocument()
    expect(screen.getByText("1933")).toBeInTheDocument()
    expect(screen.getByText("notebookTitle")).toBeInTheDocument()
    expect(screen.getByText("wordsWrittenTitle")).toBeInTheDocument()
    expect(api.getVocabularyProgress).toHaveBeenCalledWith(undefined)
  })

  it("shows review health with true retention and the at-risk flag", async () => {
    render(<StatsPage />)
    expect(await screen.findByText("dueToday")).toBeInTheDocument()
    expect(screen.getByText("newToday")).toBeInTheDocument()
    expect(screen.getByText("trueRetention")).toBeInTheDocument()
    expect(screen.getByText("80%")).toBeInTheDocument()
    expect(screen.getByText(/reviewAtRiskCount/)).toHaveTextContent('"count":1')
  })

  it("gently notes a review-heavy week", async () => {
    render(<StatsPage />)
    expect(await screen.findByText("weekNote")).toBeInTheDocument()
  })

  it("stays quiet when the week is balanced", async () => {
    api.getVocabularyProgress.mockResolvedValue(progress({
      week: { reading: 2, journal: 4, reviews: 3, review_minutes: 6, review_share: 0.3, over_budget: false },
    }))
    render(<StatsPage />)
    expect(await screen.findByText("weekTitle")).toBeInTheDocument()
    expect(screen.queryByText("weekNote")).not.toBeInTheDocument()
  })

  it("offers the placement check and shows the stored estimate", async () => {
    api.getVocabularyProgress.mockResolvedValue(progress({
      placement_available: true,
      placement: { v: 1, estimate: 3200, sample_size: 40, known: ["mesa"], checked_at: "2026-11-10T10:00:00Z" },
    }))
    render(<StatsPage />)
    expect(await screen.findByText("placementEstimateLabel")).toBeInTheDocument()
    expect(screen.getByText("3200")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "placementRetake" })).toBeInTheDocument()
  })

  it("asks for a language before the check in the all-languages view", async () => {
    api.getVocabularyProgress.mockResolvedValue(progress())
    render(<StatsPage />)
    expect(await screen.findByText("placementPickLanguage")).toBeInTheDocument()
    expect(api.getVocabularyProgress).toHaveBeenCalledWith(undefined)
  })
})
