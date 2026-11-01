import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n/i18n"

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {},
  getEntryById: vi.fn(),
  postLogEntry: vi.fn(),
  getUserSettings: vi.fn(),
  getWordBank: vi.fn(),
  postSupportEvent: vi.fn(),
  getPrompts: vi.fn(),
}))
vi.mock("@/lib/api", () => api)

vi.mock("@/components/ui/use-toast", () => ({ useToast: () => ({ toast: vi.fn() }) }))
vi.mock("@/components/lookup-sheet", () => ({
  LookupSheet: ({ context, open }: { context?: { text?: string }; open: boolean }) =>
    open ? <div data-testid="selected-lookup">{context?.text}</div> : null,
}))

vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    uiLang: "en",
    t: (key: string, options?: Record<string, unknown>) => {
      const [ns, name] = key.split(".", 2)
      return i18n.t(name, { lng: "en", ...options, ns }) as string
    },
  }),
}))

import { JournalEditor } from "@/components/journal-editor"

const frenchLearner = {
  native_lang: "en",
  default_target_lang: "fr",
  immersion_level: 1,
  language_profiles: [{ l2: "fr", immersion_level: 2, proficiency: "B1", active: true }],
}

function fillEntry() {
  fireEvent.change(screen.getByPlaceholderText("Entry Title"), { target: { value: "Samedi" } })
  fireEvent.change(screen.getByPlaceholderText(/Write your thoughts/), { target: { value: "Je suis allé au marché." } })
}

beforeEach(() => {
  vi.clearAllMocks()
  api.getWordBank.mockResolvedValue({ language: "fr", words: [] })
  api.postSupportEvent.mockResolvedValue(undefined)
  api.getPrompts.mockResolvedValue({ l2: "fr", level: "B1", meaning: "rescue_only", gloss_available: false, topics: [], prompts: [] })
})

describe("JournalEditor when settings fail to load", () => {
  it("does not fall back to Spanish; it blocks submit and offers a retry", async () => {
    api.getUserSettings.mockRejectedValueOnce(new Error("500")).mockResolvedValueOnce(frenchLearner)
    render(<JournalEditor />)

    const alert = await screen.findByTestId("settings-load-error")
    expect(screen.queryByRole("radio")).toBeNull()
    fillEntry()
    const submit = screen.getByRole("button", { name: /submit/i })
    expect(submit).toBeDisabled()
    fireEvent.click(submit)
    expect(api.postLogEntry).not.toHaveBeenCalled()

    fireEvent.click(within(alert).getByRole("button"))
    await waitFor(() => expect(screen.queryByTestId("settings-load-error")).toBeNull())
    expect(screen.getAllByRole("radio").map((radio) => radio.getAttribute("aria-checked"))).toEqual(["true"])
    expect(screen.getByRole("radio")).toHaveTextContent(/French|Français/)
    expect(screen.getByRole("button", { name: /submit/i })).toBeEnabled()
  })
})

describe("JournalEditor lookup", () => {
  it("opens lookup for selected draft text", async () => {
    api.getUserSettings.mockResolvedValue(frenchLearner)
    render(<JournalEditor />)
    const editor = await screen.findByPlaceholderText(/Write your thoughts/)
    fireEvent.change(editor, { target: { value: "Je vais au marché." } })
    Object.defineProperty(editor, "selectionStart", { configurable: true, value: 11 })
    Object.defineProperty(editor, "selectionEnd", { configurable: true, value: 17 })
    fireEvent.mouseUp(editor)
    expect(screen.getByTestId("selected-lookup")).toHaveTextContent("marché")
  })

  it("does not open lookup on select-all, so typing over the selection keeps working", async () => {
    api.getUserSettings.mockResolvedValue(frenchLearner)
    render(<JournalEditor />)
    const editor = await screen.findByPlaceholderText(/Write your thoughts/)
    fireEvent.change(editor, { target: { value: "Je vais au marché." } })
    Object.defineProperty(editor, "selectionStart", { configurable: true, value: 0 })
    Object.defineProperty(editor, "selectionEnd", { configurable: true, value: 18 })
    fireEvent.keyUp(editor, { key: "a", ctrlKey: true })
    fireEvent.keyUp(editor, { key: "Control" })
    expect(screen.queryByTestId("selected-lookup")).toBeNull()
  })

  it("does not open lookup when Ctrl is released before the 'a' key", async () => {
    api.getUserSettings.mockResolvedValue(frenchLearner)
    render(<JournalEditor />)
    const editor = await screen.findByPlaceholderText(/Write your thoughts/)
    fireEvent.change(editor, { target: { value: "Je vais au marché." } })
    Object.defineProperty(editor, "selectionStart", { configurable: true, value: 0 })
    Object.defineProperty(editor, "selectionEnd", { configurable: true, value: 18 })
    fireEvent.keyUp(editor, { key: "Control" })
    fireEvent.keyUp(editor, { key: "a", ctrlKey: false })
    expect(screen.queryByTestId("selected-lookup")).toBeNull()
  })

  it("opens lookup after extending a selection with Shift+arrow", async () => {
    api.getUserSettings.mockResolvedValue(frenchLearner)
    render(<JournalEditor />)
    const editor = await screen.findByPlaceholderText(/Write your thoughts/)
    fireEvent.change(editor, { target: { value: "Je vais au marché." } })
    Object.defineProperty(editor, "selectionStart", { configurable: true, value: 11 })
    Object.defineProperty(editor, "selectionEnd", { configurable: true, value: 17 })
    fireEvent.keyUp(editor, { key: "ArrowRight", shiftKey: true })
    expect(screen.getByTestId("selected-lookup")).toHaveTextContent("marché")
  })
})


describe("JournalEditor word bank", () => {
  const bankWord = (id: string, term: string) => ({
    word_id: id, lemma: term, term, status: "learning", reason: "never_used", forms: [term],
    hint: `meaning of ${term}`, hint_mode: "shown", use_days: 0,
  })

  beforeEach(() => {
    api.getUserSettings.mockResolvedValue(frenchLearner)
    api.getWordBank.mockResolvedValue({ language: "fr", words: [bankWord("w1", "marché"), bankWord("w2", "bouger")] })
    api.postLogEntry.mockResolvedValue({ id: "entry-1" })
    api.getEntryById.mockResolvedValue(null)
  })

  it("offers the bank for the chosen language and ticks a word once the draft uses it", async () => {
    render(<JournalEditor />)
    await screen.findAllByTestId("word-bank-chip")
    expect(api.getWordBank).toHaveBeenCalledWith("fr", { count: 6 })
    expect(screen.getByTestId("word-bank-count")).toHaveTextContent("0 of 2")
    fillEntry()
    expect(screen.getByTestId("word-bank-count")).toHaveTextContent("1 of 2")
  })

  it("sends the chosen words, and the hidden ones as challenge words, with the entry", async () => {
    render(<JournalEditor />)
    await screen.findAllByTestId("word-bank-chip")
    fireEvent.click(screen.getByRole("switch"))
    fireEvent.click(screen.getAllByRole("button", { name: "Show word" })[1])
    fillEntry()
    fireEvent.click(screen.getByRole("button", { name: /submit/i }))

    await waitFor(() => expect(api.postLogEntry).toHaveBeenCalled())
    const overrides = api.postLogEntry.mock.calls[0][3]
    expect(overrides).toMatchObject({
      target_language: "fr", target_word_ids: ["w1", "w2"], challenge_word_ids: ["w1"],
    })
  })

  it("sends no word fields when the bank is empty", async () => {
    api.getWordBank.mockResolvedValue({ language: "fr", words: [] })
    render(<JournalEditor />)
    await screen.findByTestId("word-bank-empty")
    fillEntry()
    fireEvent.click(screen.getByRole("button", { name: /submit/i }))
    await waitFor(() => expect(api.postLogEntry).toHaveBeenCalled())
    expect(api.postLogEntry.mock.calls[0][3]).not.toHaveProperty("target_word_ids")
  })
})

describe("JournalEditor without a title", () => {
  beforeEach(() => {
    api.getUserSettings.mockResolvedValue(frenchLearner)
    api.postLogEntry.mockResolvedValue({ id: "entry-1" })
    api.getEntryById.mockResolvedValue(null)
  })

  async function writeWithoutTitle(text: string) {
    render(<JournalEditor />)
    await screen.findByRole("radio")
    fireEvent.change(screen.getByPlaceholderText(/Write your thoughts/), { target: { value: text } })
    const submit = screen.getByRole("button", { name: /submit/i })
    expect(submit).toBeEnabled()
    fireEvent.click(submit)
    await waitFor(() => expect(api.postLogEntry).toHaveBeenCalled())
  }

  it("submits with an automatic title made of the first words", async () => {
    await writeWithoutTitle("Je suis allé au marché ce matin avec ma sœur.")
    expect(api.postLogEntry.mock.calls[0][1]).toBe("Je suis allé au marché ce…")
  })

  it("keeps a title the learner typed", async () => {
    render(<JournalEditor />)
    await screen.findByRole("radio")
    fillEntry()
    fireEvent.click(screen.getByRole("button", { name: /submit/i }))
    await waitFor(() => expect(api.postLogEntry).toHaveBeenCalled())
    expect(api.postLogEntry.mock.calls[0][1]).toBe("Samedi")
  })
})

describe("JournalEditor prompt bank", () => {
  const frame = "Me llamo [__]. Soy de [__]."
  const prompt = {
    id: "es-a1-01",
    level: "A1",
    topics: ["identidad_personal"],
    title: "Preséntate",
    prompt: "Completa una ficha breve con tu nombre y lugar de origen.",
    sentence_frame: frame,
    one_sentence_frame: "Me llamo [__] y soy de [__].",
    structure_hint: "Usa me llamo, tengo y soy.",
    suggested_words: ["me llamo", "años", "de"],
    gloss: {
      prompt: "Complete a short profile.",
      sentence_frame: "My name is [__]. I am from [__].",
      one_sentence_frame: "My name is [__] and I am from [__].",
      structure_hint: "Use me llamo, tengo and soy.",
    },
  }
  const spanishA1 = {
    native_lang: "en",
    default_target_lang: "es",
    immersion_level: 0,
    language_profiles: [{ l2: "es", immersion_level: 0, proficiency: "A1", active: true }],
  }
  const promptResponse = {
    l2: "es",
    level: "A1",
    meaning: "open",
    gloss_available: true,
    topics: ["identidad_personal"],
    prompts: [prompt],
  }

  beforeEach(() => {
    api.getUserSettings.mockResolvedValue(spanishA1)
    api.getWordBank.mockResolvedValue({ language: "es", words: [] })
    api.getPrompts.mockResolvedValue(promptResponse)
    api.postLogEntry.mockResolvedValue({ id: "entry-prompt" })
    api.getEntryById.mockResolvedValue(null)
  })

  it("shows all three starts and submits a filled frame in three taps", async () => {
    render(<JournalEditor />)

    await screen.findByTestId("word-bank-empty")
    const mode = screen.getByRole("button", { name: "Fill in the blanks" })
    expect(screen.getByRole("button", { name: "Give me an idea" })).toBeVisible()
    expect(mode).toBeVisible()
    expect(screen.getByRole("button", { name: "Just one sentence" })).toBeVisible()

    fireEvent.click(mode)
    const useFrame = await screen.findByRole("button", { name: "Use this frame" })
    fireEvent.click(useFrame)
    expect(screen.getByPlaceholderText("Entry Title")).toHaveValue(prompt.title)
    expect(screen.getByPlaceholderText(/Write your thoughts/)).toHaveValue(frame)

    fireEvent.click(screen.getByRole("button", { name: /submit/i }))
    await waitFor(() => expect(api.postLogEntry).toHaveBeenCalled())
    expect(api.postLogEntry.mock.calls[0][3]).toMatchObject({
      target_language: "es",
      prompt_id: "es-a1-01",
      entry_mode: "frame",
    })
    expect(api.postSupportEvent).toHaveBeenCalledWith({
      kind: "prompt_selected",
      l2: "es",
      prompt_id: "es-a1-01",
    })
  })

  it("excludes a used prompt when the learner starts another entry", async () => {
    render(<JournalEditor />)
    await screen.findByTestId("word-bank-empty")
    fireEvent.click(screen.getByRole("button", { name: "Fill in the blanks" }))
    fireEvent.click(await screen.findByRole("button", { name: "Use this frame" }))
    fireEvent.click(screen.getByRole("button", { name: /submit/i }))
    await waitFor(() => expect(api.postLogEntry).toHaveBeenCalled())

    fireEvent.click(await screen.findByRole("button", { name: "Reset" }))
    fireEvent.click(screen.getByRole("button", { name: "Fill in the blanks" }))
    await waitFor(() => expect(api.getPrompts).toHaveBeenCalledTimes(2))
    expect(api.getPrompts.mock.calls[1][0].exclude).toContain("es-a1-01")
  })
})
