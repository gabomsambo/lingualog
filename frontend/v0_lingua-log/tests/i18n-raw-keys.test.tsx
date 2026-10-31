/**
 * The stats page and user-facing toast/menu must never show raw i18n keys (V1 defects 3 and 4).
 * Every key those two files use resolves in every locale instead of rendering its name,
 * and the keys they share live in locales/<lang>/common.json for every locale as well.
 */
import { readFileSync } from "node:fs"
import path from "node:path"
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import i18n from "@/i18n/i18n"
import en from "@/locales/en/common.json"
import es from "@/locales/es/common.json"
import ar from "@/locales/ar/common.json"

const api = vi.hoisted(() => ({
  getUserStats: vi.fn(),
  getUserSettings: vi.fn(),
  getVocabularyProgress: vi.fn(),
  getPlacementCheck: vi.fn(),
  submitPlacementCheck: vi.fn(),
}))
vi.mock("@/lib/api", () => api)

import { LocaleProvider } from "@/i18n/LocaleProvider"
import StatsPage from "@/app/(app)/stats/page"

const FILES = ["app/(app)/stats/page.tsx", "components/user-nav.tsx"]
const LOCALES = ["en", "es", "ar"]
const COMMON_KEYS = ["yourLearningStats", "writingStreak", "signOut", "words", "welcomeBack", "readyToContinue"]

function usedKeys(file: string): string[] {
  const text = readFileSync(path.join(__dirname, "..", file), "utf8")
  return [...new Set([...text.matchAll(/\bt\(\s*["']([\w.]+)["']/g)].map((match) => match[1]))]
}

describe("no raw key renders on the stats page and the user menu", () => {
  it.each(FILES)("every key used by %s resolves in every locale", async (file) => {
    const keys = usedKeys(file)
    expect(keys.length).toBeGreaterThan(0)
    for (const key of keys) {
      const [ns, ...rest] = key.split(".")
      const name = rest.length ? rest.join(".") : ns
      const namespace = rest.length ? ns : "common"
      for (const lng of ["en", "es"]) {
        expect(i18n.exists(name, { ns: namespace, lng }), `${key} missing in ${lng}`).toBe(true)
      }
      for (const lng of LOCALES) {
        await i18n.changeLanguage(lng)
        const rendered = i18n.t(name, { ns: namespace })
        expect(rendered, `${key} in ${lng}`).toBeTruthy()
        expect(rendered, `${key} in ${lng}`).not.toBe(key)
      }
    }
    await i18n.changeLanguage("en")
  })

  it("keeps the shared keys in every locales/<lang>/common.json", () => {
    for (const bundle of [{ ...en }, { ...es }, { ...ar }]) {
      for (const key of COMMON_KEYS) {
        expect(bundle, key).toHaveProperty(key)
      }
    }
  })

  it("translates the dashboard welcome toast instead of rendering key names", async () => {
    for (const lng of ["en", "es", "ar"]) {
      await i18n.changeLanguage(lng)
      for (const key of ["welcomeBack", "readyToContinue"]) {
        const rendered = i18n.t(key, { ns: "common" })
        expect(rendered, `${key} in ${lng}`).toBeTruthy()
        expect(rendered, `${key} in ${lng}`).not.toBe(key)
      }
    }
    await i18n.changeLanguage("en")
  })

  it("renders the stats page with real translations, never key names", async () => {
    api.getUserStats.mockResolvedValue({
      wordCounts: [], languageBreakdown: [], streak: { current: 0, longest: 0, totalWords: 0 },
    })
    api.getUserSettings.mockResolvedValue({
      default_target_lang: "es", language_profiles: [{ l2: "es", immersion_level: 1, proficiency: "B1", active: true }],
    })
    api.getVocabularyProgress.mockResolvedValue({
      language: "es",
      notebook: { new: 0, learning: 0, known: 0, mastered: 0, ignored: 0, total: 0 },
      trend: [], active_words: 0,
      encounters: { by_kind: {}, reviews: 0, per_word: 0, guide_min: 10, guide_max: 12 },
      review: { due_today: 0, new_today: 0, forecast: [], at_risk: 0, true_retention: null, reviews_last_7_days: 0, minutes_last_7_days: 0 },
      week: { reading: 0, journal: 0, reviews: 0, review_minutes: 0, review_share: 0, over_budget: false },
      placement: null, placement_available: false,
    })
    localStorage.setItem("uiLang", "en")

    render(<LocaleProvider><StatsPage /></LocaleProvider>)

    expect(await screen.findByText(/Your Learning Stats/)).toBeInTheDocument()
    expect(screen.getByText(/Writing Streak/)).toBeInTheDocument()
    expect(screen.queryByText(/yourLearningStats/)).not.toBeInTheDocument()
    expect(screen.queryByText(/writingStreak/)).not.toBeInTheDocument()
    expect(screen.queryByText(/common\.words/)).not.toBeInTheDocument()
  })
})
