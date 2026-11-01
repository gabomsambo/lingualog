import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const api = vi.hoisted(() => ({
  lookupWord: vi.fn(),
  addVocabularyItem: vi.fn(),
  updateVocabularyItem: vi.fn(),
}))
vi.mock("@/lib/api", () => api)
const toastSpy = vi.hoisted(() => vi.fn())
vi.mock("@/components/ui/use-toast", () => ({ useToast: () => ({ toast: toastSpy }) }))

import { GlobalLookupBox, LookupSheet } from "@/components/lookup-sheet"

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
    expect(toastSpy).toHaveBeenCalledWith({ title: "Saved to your notebook (Vocabulary)" })
    expect(await screen.findByRole("button", { name: "I know it" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Ignore" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Study" }))
    await waitFor(() => expect(api.updateVocabularyItem).toHaveBeenCalledWith("word-1", { status: "learning" }))
    expect(toastSpy).toHaveBeenCalledWith({ title: "Added to your notebook - it will come up in Review" })
    expect(screen.queryByTestId("lookup-sentence-field")).not.toBeInTheDocument()
  })

  it("asks for the sentence you saw it in when the lookup has none", async () => {
    render(<LookupSheet
      context={{ text: "madrugar", sentence: "madrugar", language: "es", source: "manual" }}
      open onOpenChange={vi.fn()}
    />)
    expect(await screen.findByTestId("lookup-sentence-field")).toBeInTheDocument()
    expect(screen.queryByText("madrugar", { selector: "p" })).not.toBeInTheDocument()

    fireEvent.change(screen.getByTestId("lookup-sentence-field"), { target: { value: "Tuve que madrugar." } })
    fireEvent.click(screen.getByRole("button", { name: "Save to notebook" }))

    await waitFor(() => expect(api.addVocabularyItem).toHaveBeenCalledWith(expect.objectContaining({
      example_sentence: "Tuve que madrugar.",
    })))
  })

  it("saves no example sentence when none was typed, never the bare word", async () => {
    render(<LookupSheet
      context={{ text: "madrugar", sentence: "madrugar", language: "es", source: "manual" }}
      open onOpenChange={vi.fn()}
    />)
    fireEvent.click(await screen.findByRole("button", { name: "Save to notebook" }))

    await waitFor(() => expect(api.addVocabularyItem).toHaveBeenCalledWith(expect.objectContaining({
      example_sentence: undefined,
    })))
  })
})

describe("GlobalLookupBox language", () => {
  it("starts on the given language and follows it when it changes", () => {
    const { rerender } = render(<GlobalLookupBox language="es" />)
    const select = screen.getByLabelText("Word language") as HTMLSelectElement
    expect(select.value).toBe("es")
    rerender(<GlobalLookupBox language="fr" />)
    expect(select.value).toBe("fr")
    rerender(<GlobalLookupBox language="de" />)
    expect(select.value).toBe("de")
  })
})
