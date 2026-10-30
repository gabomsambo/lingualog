import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const api = vi.hoisted(() => ({
  lookupWord: vi.fn(),
  addVocabularyItem: vi.fn(),
  updateVocabularyItem: vi.fn(),
}))
vi.mock("@/lib/api", () => api)
vi.mock("@/components/ui/use-toast", () => ({ useToast: () => ({ toast: vi.fn() }) }))

import { LookupSheet } from "@/components/lookup-sheet"

const card = {
  lemma: "banco", surface: "banco", is_phrase: false, part_of_speech: "noun", gender: "m",
  sense_in_context: "A bench in a park.", gloss_l1: "park bench", other_senses: [],
  register: "neutral", cefr: "A1", frequency_band: "top1k",
  examples: ["El banco es de madera."], example_translations: ["The bench is made of wood."],
  collocations: [], word_family: [], common_mistake: "", memory_hook: "",
}
const saved = {
  id: "word-1", user_id: "user-1", term: "banco", lemma: "banco", language: "es",
  status: "new", card, card_status: "ok", card_policy: null, tags: [],
  created_at: "2026-10-31T00:00:00Z", updated_at: "2026-10-31T00:00:00Z",
}

describe("LookupSheet triage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.lookupWord.mockResolvedValue({
      encounter_id: "enc-1", text: "banco", language: "es", lemma: "banco", sense: "bench",
      card, card_status: "ok", card_policy: { v: 1 }, seen_count: 3, saved_item: null,
    })
    api.addVocabularyItem.mockResolvedValue(saved)
    api.updateVocabularyItem.mockResolvedValue({ ...saved, status: "learning" })
  })

  it("saves the cached lookup and offers Study / I know it / Ignore", async () => {
    render(<LookupSheet
      context={{ text: "banco", sentence: "Me senté en un banco.", language: "es", source: "manual" }}
      open onOpenChange={vi.fn()}
    />)
    expect(await screen.findByText("Seen 3× — worth saving?")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Save to notebook" }))
    await waitFor(() => expect(api.addVocabularyItem).toHaveBeenCalledWith(expect.objectContaining({
      encounter_id: "enc-1", example_sentence: "Me senté en un banco.",
    })))
    expect(await screen.findByRole("button", { name: "I know it" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Ignore" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Study" }))
    await waitFor(() => expect(api.updateVocabularyItem).toHaveBeenCalledWith("word-1", { status: "learning" }))
  })
})
