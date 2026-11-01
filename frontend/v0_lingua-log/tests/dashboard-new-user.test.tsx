import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n/i18n"

const toast = vi.hoisted(() => vi.fn())
const users = vi.hoisted(() => ({
  getUserProfile: vi.fn(),
  getUserEntries: vi.fn(),
  getUserStats: vi.fn(),
}))
const api = vi.hoisted(() => ({ getUserSettings: vi.fn() }))
vi.mock("@/lib/user-service", () => users)
vi.mock("@/lib/api", () => api)
vi.mock("@/components/ui/use-toast", () => ({ useToast: () => ({ toast }) }))
vi.mock("@/components/confetti", () => ({ Confetti: () => null }))
vi.mock("@/components/level-suggestion-card", () => ({ LevelSuggestionCard: () => null }))
vi.mock("@/components/review-due-card", () => ({ ReviewDueCard: () => null }))
vi.mock("@/components/lookup-sheet", () => ({
  GlobalLookupBox: ({ language }: { language: string }) => <div data-testid="global-lookup" data-language={language} />,
}))
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      const [ns, name] = key.split(".", 2)
      return i18n.t(name, { lng: "en", ...options, ns }) as string
    },
  }),
}))

import DashboardPage from "@/app/(app)/dashboard/page"

const stats = (streak: number) => ({ wordCount: 0, weeklyIncrease: 0, languages: [], languageEmojis: [], streak })

beforeEach(() => {
  vi.clearAllMocks()
  users.getUserProfile.mockResolvedValue({ id: "u", email: "new@example.com", username: null })
  api.getUserSettings.mockResolvedValue({ default_target_lang: "fr" })
})

describe("dashboard for a brand-new account", () => {
  beforeEach(() => {
    users.getUserEntries.mockResolvedValue([])
    users.getUserStats.mockResolvedValue(stats(0))
  })

  it("greets with no welcome-back toast and no streak talk", async () => {
    render(<DashboardPage />)
    expect(await screen.findByText("Write your first entry to start your streak.")).toBeInTheDocument()
    expect(toast).not.toHaveBeenCalled()
    expect(screen.queryByText(/no writing streak/i)).toBeNull()
    expect(screen.queryByText(/on fire/i)).toBeNull()
  })

  it("points the global lookup at the default target language", async () => {
    render(<DashboardPage />)
    await waitFor(() => expect(screen.getByTestId("global-lookup")).toHaveAttribute("data-language", "fr"))
  })
})

describe("dashboard for a returning learner", () => {
  const entry = { id: "e1", title: "Hola", language: "Spanish", languageEmoji: "🇪🇸", date: "2026-10-30", excerpt: "x" }

  it("welcomes them back and cheers an active streak", async () => {
    users.getUserEntries.mockResolvedValue([entry])
    users.getUserStats.mockResolvedValue(stats(3))
    render(<DashboardPage />)
    expect(await screen.findByText(/You're on fire/)).toBeInTheDocument()
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ title: "Welcome back!" }))
  })

  it("does not cheer a streak of 0 days", async () => {
    users.getUserEntries.mockResolvedValue([entry])
    users.getUserStats.mockResolvedValue(stats(0))
    render(<DashboardPage />)
    await screen.findAllByText("Write today to start your streak.")
    expect(screen.queryByText(/on fire/i)).toBeNull()
  })
})
