import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  addVocabularyItem: vi.fn(),
  confirmClassNote: vi.fn(),
  createClassNote: vi.fn(),
  getClassNote: vi.fn(),
  getUserSettings: vi.fn(),
  push: vi.fn(),
  t: vi.fn((key: string) => key),
}))

vi.mock("@/lib/api", () => ({
  addVocabularyItem: mocks.addVocabularyItem,
  confirmClassNote: mocks.confirmClassNote,
  createClassNote: mocks.createClassNote,
  getClassNote: mocks.getClassNote,
  getUserSettings: mocks.getUserSettings,
}))
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push }) }))
vi.mock("@/i18n/LocaleProvider", () => ({ useLocale: () => ({ t: mocks.t }) }))

import ClassPage from "@/app/(app)/class/page"

const words = [
  { term: "la casa", lemma: "casa", gloss: "house", part_of_speech: "noun", example: "La casa es grande.", reading: "" },
  { term: "estudiar", lemma: "estudiar", gloss: "to study", part_of_speech: "verb", example: "Estudio español.", reading: "" },
]
const tasks = [1, 2, 3].map((index) => ({
  title: `Task ${index}`,
  prompt: `Write task ${index}`,
  length_hint: "25–50 words",
  grammar_scope: "present tense",
}))
const note = {
  id: "class-note-1",
  user_id: "user-1",
  l2: "es",
  raw_text: "la casa, estudiar",
  source: "paste",
  created_at: "2026-11-01T10:00:00Z",
  extracted: {
    words,
    grammar_focus: "estar + gerundio",
    phrases: ["Estoy estudiando"],
    tasks,
    level: "A1",
    length_hint: "25–50 words",
    grammar_scope: "present tense",
  },
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.getUserSettings.mockResolvedValue({
    default_target_lang: "es",
    language_profiles: [{ l2: "es", active: true, proficiency: "A1" }],
  })
  mocks.getClassNote.mockResolvedValue(null)
  mocks.createClassNote.mockResolvedValue(note)
  mocks.confirmClassNote.mockResolvedValue({
    ...note,
    extracted: {
      ...note.extracted,
      words: words.map((word, index) => ({ ...word, word_id: `word-${index}`, encounter_id: `encounter-${index}` })),
    },
  })
  mocks.addVocabularyItem.mockResolvedValue({ id: "word-id" })
})

describe("Class page", () => {
  it("extracts editable chips, offers three tasks, and saves confirmed words before writing", async () => {
    render(<ClassPage />)

    fireEvent.change(await screen.findByLabelText("journal.classPastePlaceholder"), {
      target: { value: "la casa, estudiar" },
    })
    fireEvent.click(screen.getByRole("button", { name: "journal.classExtract" }))

    expect(await screen.findByTestId("class-note-words")).toBeInTheDocument()
    expect(screen.getAllByRole("button", { name: /Task/ })).toHaveLength(3)
    const terms = screen.getAllByLabelText("journal.classWordTerm")
    fireEvent.change(terms[0], { target: { value: "la vivienda" } })
    fireEvent.change(screen.getByLabelText("journal.classPhraseTerm 1"), { target: { value: "Estoy aprendiendo" } })
    fireEvent.click(screen.getByRole("button", { name: /Task 2/ }))
    fireEvent.click(screen.getByRole("button", { name: "journal.classOpenEditor" }))

    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/entries/new?class_note_id=class-note-1&class_task=1"))
    expect(mocks.createClassNote).toHaveBeenCalledWith("la casa, estudiar", "es")
    expect(mocks.confirmClassNote).toHaveBeenCalledWith("class-note-1", expect.objectContaining({
      grammar_focus: "estar + gerundio",
      phrases: ["Estoy aprendiendo"],
      words: expect.arrayContaining([expect.objectContaining({ term: "la vivienda", lemma: "la vivienda" })]),
    }))
    expect(mocks.addVocabularyItem).toHaveBeenCalledTimes(2)
    expect(mocks.addVocabularyItem).toHaveBeenCalledWith(expect.objectContaining({
      term: "casa",
      language: "es",
      encounter_id: "encounter-0",
    }))
  })
})
