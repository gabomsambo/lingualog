import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { UserVocabularyItemResponse, VocabularyCardPolicy } from "@/lib/api"

const api = vi.hoisted(() => ({
  updateVocabularyItem: vi.fn(),
  retryVocabularyCard: vi.fn(),
  postSupportEvent: vi.fn(),
}))

vi.mock("@/lib/api", () => api)
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    t: (key: string) => key.split(".").at(-1),
  }),
}))

import { WordCard } from "@/components/word-card"

const FLAGS: VocabularyCardPolicy["vocab_def"][] = ["l1", "l1_plus_l2", "l2_plus_l1", "l2"]

function item(level: number): UserVocabularyItemResponse {
  return {
    id: `word-${level}`,
    user_id: "user-1",
    term: "banco",
    lemma: "banco",
    language: "es",
    example_sentence: "Me senté en un banco del parque.",
    status: "new",
    card_status: "ok",
    card_policy: {
      v: 1,
      level,
      l1: "en",
      l2: "es",
      vocab_def: FLAGS[level],
      model: "gemini-3.5-flash-lite",
    },
    card: {
      lemma: "banco",
      surface: "banco",
      is_phrase: false,
      part_of_speech: "noun",
      gender: "m",
      sense_in_context: level < 2 ? "A bench in a park." : "Asiento largo en un parque.",
      gloss_l1: level === 3 ? "" : "park bench",
      other_senses: [{ meaning: "A bank.", example: "Voy al banco." }],
      register: "neutral",
      cefr: "A1",
      frequency_band: "top1k",
      examples: ["Nos sentamos en el banco.", "El banco era de madera."],
      collocations: ["banco del parque"],
      word_family: ["banquito"],
      common_mistake: "Check the context.",
      memory_hook: "Picture a bench.",
    },
    note: "",
    tags: [],
    created_at: "2026-10-30T12:00:00Z",
    updated_at: "2026-10-30T12:00:00Z",
  }
}

function renderLevel(level: number) {
  return render(<WordCard item={item(level)} open onOpenChange={vi.fn()} />)
}

describe("WordCard policy rendering", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.postSupportEvent.mockResolvedValue(undefined)
  })

  it.each([0, 1])("shows the native gloss immediately at level %i", (level) => {
    renderLevel(level)
    expect(screen.getByTestId("word-card-gloss")).toHaveTextContent("park bench")
  })

  it("hides the level 2 gloss until the learner asks", () => {
    renderLevel(2)
    expect(screen.queryByTestId("word-card-gloss")).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "revealGloss" }))
    expect(screen.getByTestId("word-card-gloss")).toHaveTextContent("park bench")
    expect(api.postSupportEvent).toHaveBeenCalledWith(expect.objectContaining({ kind: "reveal_gloss" }))
  })

  it("keeps level 3 target-language-only", () => {
    renderLevel(3)
    expect(screen.queryByTestId("word-card-gloss")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "revealGloss" })).not.toBeInTheDocument()
    expect(screen.getByText("Asiento largo en un parque.")).toBeInTheDocument()
  })

  it("renders the designed sections in order", () => {
    renderLevel(0)
    const headings = screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent)
    expect(headings).toEqual([
      "hereTitle",
      "meaningTitle",
      "hearTitle",
      "examplesTitle",
      "otherMeaningsTitle",
      "familyTitle",
      "watchOutTitle",
      "rememberTitle",
      "trailTitle",
    ])
  })
})
