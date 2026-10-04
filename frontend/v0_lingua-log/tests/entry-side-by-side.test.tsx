import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n/i18n"
import type { LearningPolicySnapshot } from "@/lib/side-by-side"
import { toSideBySideEntry } from "@/lib/side-by-side"

const api = vi.hoisted(() => ({
  translateEntryPart: vi.fn(),
  postSupportEvent: vi.fn(),
  analyzeEntry: vi.fn(),
  getCurrentPolicy: vi.fn(),
  getLevelSuggestions: vi.fn(),
  acceptLevelSuggestion: vi.fn(),
  dismissLevelSuggestion: vi.fn(),
}))
vi.mock("@/lib/api", () => api)

vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    uiLang: "en",
    t: (key: string, options?: Record<string, unknown>) => {
      const [ns, k] = key.split(".", 2)
      return i18n.t(k, { lng: "en", ...options, ns }) as string
    },
  }),
}))

import { EntrySideBySide } from "@/components/entry-side-by-side"

const CONTENT =
  "Mi hermana es muy aburrida hoy porque está lloviendo. Quiero que ella viene conmigo al cine. Estoy muy embarazada porque olvidé su cumpleaños."
const CORRECTED =
  "Mi hermana está muy aburrida hoy porque está lloviendo. Quiero que ella venga conmigo al cine. Estoy muy avergonzada porque olvidé su cumpleaños."
const MEANING = [
  "My sister is very bored today because it's raining.",
  "I want her to come with me to the cinema.",
  "I'm very embarrassed because I forgot her birthday.",
]

const LEVELS: Record<number, Pick<LearningPolicySnapshot, "explanation" | "meaning" | "rewrite_gloss">> = {
  0: { explanation: "l1", meaning: "open", rewrite_gloss: "l1_open" },
  1: { explanation: "l1_with_l2_terms", meaning: "tap", rewrite_gloss: "l1_tap" },
  2: { explanation: "l2_then_l1", meaning: "tap_hidden", rewrite_gloss: "l2_tooltips" },
  3: { explanation: "l2", meaning: "rescue_only", rewrite_gloss: "l2_tooltips" },
}

function rawEntry(level: number | null, overrides: Record<string, unknown> = {}) {
  return {
    id: "entry-1",
    language: "es",
    content: CONTENT,
    corrected: CORRECTED,
    rewrite: "Hoy mi hermana está aburridísima porque no para de llover.",
    analysis_status: "ok",
    policy_snapshot:
      level === null ? null : { v: 1, l1: "en", l2: "es", immersion_level: level, proficiency: "B1", ...LEVELS[level] },
    ai_feedback: {
      score: 68,
      tone: "Reflective",
      explanation: "Good effort.\nWatch ser and estar.",
      rubric: {
        grammar: 65,
        vocabulary: 70,
        complexity: 70,
        intended_meaning: "Mi hermana está aburrida y quiero ir al cine con ella.",
        ambiguities: [{ question: "Did you mean embarrassed or pregnant?", span: "embarazada" }],
        rewrite_idioms: [{ phrase: "no para de llover", gloss: "it won't stop raining" }],
      },
      grammar_suggestions: [
        {
          original: "es muy aburrida",
          corrected: "está muy aburrida",
          note: "Use estar for feelings.",
          note_l1: "Use estar for feelings.",
          note_l2: "Usa estar para estados.",
          meaning_changing: true,
          literal_reading: "As written, a native reads 'My sister is a boring person'.",
        },
        { original: "viene", corrected: "venga", note: "Subjunctive.", note_l1: "Subjunctive.", note_l2: "Subjuntivo." },
        {
          original: "embarazada",
          corrected: "avergonzada",
          note: "False friend.",
          note_l1: "False friend.",
          note_l2: "Falso amigo.",
          meaning_changing: true,
          literal_reading: "I am very pregnant",
        },
      ],
      new_words: [{ term: "lloviendo", pos: "verb", definition: "raining", example: "Está lloviendo." }],
    },
    ...overrides,
  }
}

function translation(part: string) {
  if (part === "original") {
    return { status: "ok", sentences: MEANING, text: MEANING.join("\n\n"), provider_label: "Translated by Lara" }
  }
  if (part === "rewrite") {
    return { status: "ok", sentences: ["Today my sister is super bored."], text: "Today my sister is super bored.", provider_label: "Translated by Lara" }
  }
  return { status: "ok", sentences: ["<p>Use <span translate=\"no\">estar</span> for states.</p>"], text: "<p>Use <span translate=\"no\">estar</span> for states.</p>", provider_label: "Translated by Lara" }
}

function renderEntry(level: number | null, overrides: Record<string, unknown> = {}, props = {}) {
  return render(<EntrySideBySide entry={toSideBySideEntry(rawEntry(level, overrides))} {...props} />)
}

const translatedParts = () => api.translateEntryPart.mock.calls.map((call) => call[1])
const eventKinds = () => api.postSupportEvent.mock.calls.map((call) => call[0].kind)

beforeEach(() => {
  vi.clearAllMocks()
  api.translateEntryPart.mockImplementation(async (_id: string, part: string) => translation(part))
  api.postSupportEvent.mockResolvedValue(undefined)
  api.analyzeEntry.mockResolvedValue(undefined)
  api.getCurrentPolicy.mockResolvedValue({ v: 1, l1: "en", l2: "es", ...LEVELS[1] })
  api.getLevelSuggestions.mockResolvedValue({ suggestions: [] })
  api.acceptLevelSuggestion.mockResolvedValue({})
  api.dismissLevelSuggestion.mockResolvedValue({})
})

describe("EntrySideBySide layout", () => {
  it("renders one row per sentence with errors underlined and the corrected diff", async () => {
    renderEntry(0)
    expect(screen.getAllByTestId("sbs-row")).toHaveLength(3)
    const marks = screen.getAllByTestId("error-mark")
    expect(marks.map((mark) => mark.textContent)).toEqual(["es muy aburrida", "viene", "embarazada"])
    expect(marks.map((mark) => mark.getAttribute("data-meaning-changing"))).toEqual(["true", "false", "true"])
    const corrected = screen.getAllByTestId("corrected")
    expect(within(corrected[0]).getByText("está").tagName).toBe("INS")
    expect(within(corrected[0]).getByText("es").tagName).toBe("DEL")
    expect(screen.getAllByTestId("fix-card")).toHaveLength(3)
    expect(screen.getByTestId("ambiguities")).toHaveTextContent("Did you mean embarrassed or pregnant?")
  })

  it("marks a sentence the correction merged into its neighbour instead of striking it out", () => {
    renderEntry(0, {
      corrected:
        "Mi hermana está muy aburrida hoy porque está lloviendo y quiero que ella venga conmigo al cine. Estoy muy avergonzada porque olvidé su cumpleaños.",
    })
    const rows = screen.getAllByTestId("sbs-row")
    expect(rows).toHaveLength(3)
    const merged = screen.getAllByTestId("corrected-merged")
    expect(merged).toHaveLength(1)
    expect(merged[0]).toHaveTextContent(/merged into the sentence (above|below)/i)
    const mergedRow = rows.findIndex((row) => within(row).queryByTestId("corrected-merged"))
    expect(within(rows[mergedRow]).queryByTestId("corrected")).toBeNull()
    expect(merged[0]).toHaveTextContent(mergedRow === 0 ? "Merged into the sentence below" : "Merged into the sentence above")
    expect(screen.getAllByTestId("corrected")).toHaveLength(2)
  })

  it("strikes out a sentence the correction removed and says so", () => {
    renderEntry(0, {
      corrected:
        "Mi hermana está muy aburrida hoy porque está lloviendo. Estoy muy avergonzada porque olvidé su cumpleaños.",
    })
    const rows = screen.getAllByTestId("sbs-row")
    expect(screen.queryAllByTestId("corrected-merged")).toHaveLength(0)
    const removed = within(rows[1]).getByTestId("corrected-removed")
    expect(removed).toHaveTextContent("Removed in the correction")
    expect(within(within(rows[1]).getByTestId("corrected")).getByText(/viene/).tagName).toBe("DEL")
  })

  it("uses an authoritative mapping for the el/es/que removal case", () => {
    renderEntry(0, {
      content: "El día es largo. Que es así.",
      corrected: "El día es largo.",
      sentence_mapping_status: "valid",
      sentence_mapping: [
        { source_sentence: 0, corrected_sentences: [0] },
        { source_sentence: 1, corrected_sentences: [] },
      ],
    })
    const rows = screen.getAllByTestId("sbs-row")
    expect(within(rows[1]).getByTestId("corrected-removed")).toBeInTheDocument()
    expect(within(rows[1]).queryByTestId("corrected-merged")).toBeNull()
  })

  it("warns visibly and does not guess merged or removed for an invalid mapping", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {})
    renderEntry(0, {
      content: "El día es largo. Que es así.",
      corrected: "El día es largo.",
      sentence_mapping_status: "invalid",
      sentence_mapping: null,
    })
    expect(screen.getByTestId("alignment-fallback-warning")).toBeInTheDocument()
    expect(warn).toHaveBeenCalledWith(expect.stringContaining("invalid sentence mapping"))
    const rows = screen.getAllByTestId("sbs-row")
    expect(within(rows[1]).getByTestId("corrected-unaligned")).toBeInTheDocument()
    expect(within(rows[1]).queryByTestId("corrected-merged")).toBeNull()
    expect(within(rows[1]).queryByTestId("corrected-removed")).toBeNull()
    warn.mockRestore()
  })

  it("switches to the native rewrite as one block with idiom glosses", async () => {
    renderEntry(0)
    fireEvent.click(screen.getByRole("button", { name: "Native" }))
    const block = screen.getByTestId("native-block")
    expect(block).toHaveTextContent("Hoy mi hermana está aburridísima")
    expect(screen.getByTestId("idiom")).toHaveTextContent("no para de llover · it won't stop raining")
    expect(screen.queryAllByTestId("corrected")).toHaveLength(0)
  })

  it("shows the overview only when asked", () => {
    const { unmount } = renderEntry(0)
    expect(screen.getByTestId("entry-overview")).toHaveTextContent("Watch ser and estar.")
    unmount()
    renderEntry(0, {}, { showOverview: false })
    expect(screen.queryByTestId("entry-overview")).toBeNull()
  })
})

describe("level 0 (meaning open, rewrite gloss open)", () => {
  it("shows the sentence-aligned meaning and the as-written warnings without logging", async () => {
    renderEntry(0)
    await waitFor(() => expect(screen.getAllByTestId("meaning-text")).toHaveLength(3))
    expect(screen.getAllByTestId("meaning-text").map((node) => node.textContent)).toEqual(MEANING)
    const warnings = screen.getAllByTestId("as-written")
    expect(warnings[0]).toHaveTextContent("As written, a native reads: “My sister is a boring person”")
    expect(warnings[1]).toHaveTextContent("I am very pregnant")
    expect(translatedParts()).toEqual(expect.arrayContaining(["original", "rewrite"]))
    fireEvent.click(screen.getByRole("button", { name: "Native" }))
    await waitFor(() => expect(screen.getByTestId("rewrite-gloss")).toHaveTextContent("Today my sister is super bored."))
    expect(api.postSupportEvent).not.toHaveBeenCalled()
  })

  it("writes notes in the learner's language with no rescue button", () => {
    renderEntry(0)
    expect(screen.getAllByTestId("note-primary")[0]).toHaveTextContent("Use estar for feelings.")
    expect(screen.queryByRole("button", { name: "Explain in English" })).toBeNull()
  })
})

describe("level 1 (meaning blurred, rewrite gloss on tap)", () => {
  it("blurs each meaning until tapped and logs one reveal per sentence", async () => {
    renderEntry(1)
    await waitFor(() => expect(screen.getAllByTestId("meaning-blurred")).toHaveLength(3))
    expect(screen.queryAllByTestId("meaning-text")).toHaveLength(0)
    fireEvent.click(screen.getAllByTestId("meaning-blurred")[0])
    expect(screen.getAllByTestId("meaning-text")[0]).toHaveTextContent(MEANING[0])
    expect(api.postSupportEvent).toHaveBeenCalledWith({ kind: "reveal_meaning", entry_id: "entry-1", immersion_level: 1, l2: "es" })
  })

  it("translates the rewrite only when the learner taps for it", async () => {
    renderEntry(1)
    await waitFor(() => expect(translatedParts()).toEqual(["original"]))
    fireEvent.click(screen.getByRole("button", { name: "Native" }))
    fireEvent.click(screen.getByRole("button", { name: "Show in English" }))
    await waitFor(() => expect(screen.getByTestId("rewrite-gloss")).toHaveTextContent("Today my sister is super bored."))
    expect(translatedParts()).toContain("rewrite")
    expect(eventKinds()).toEqual(["reveal_rewrite_gloss"])
  })
})

describe("level 2 (meaning behind Show meaning, L2 notes with an L1 gloss)", () => {
  it("hides the meaning behind a link and shows L2 notes first", async () => {
    renderEntry(2)
    await waitFor(() => expect(screen.getAllByRole("button", { name: "Show meaning" })).toHaveLength(3))
    expect(screen.queryAllByTestId("meaning-blurred")).toHaveLength(0)
    fireEvent.click(screen.getAllByRole("button", { name: "Show meaning" })[1])
    expect(screen.getByTestId("meaning-text")).toHaveTextContent(MEANING[1])
    expect(eventKinds()).toEqual(["reveal_meaning"])
    expect(screen.getAllByTestId("note-primary")[0]).toHaveTextContent("Usa estar para estados.")
    expect(screen.getAllByTestId("note-secondary")[0]).toHaveTextContent("Use estar for feelings.")
  })
})

describe("level 3 (paraphrase in L2, rescue only)", () => {
  it("replaces the meaning with the L2 paraphrase and fetches nothing until a rescue", async () => {
    renderEntry(3)
    expect(screen.getByTestId("meaning-header")).toHaveTextContent("Lo que quisiste decir")
    expect(screen.getByTestId("meaning-paraphrase")).toHaveTextContent("Mi hermana está aburrida y quiero ir al cine con ella.")
    expect(screen.getAllByTestId("as-written")[0]).toHaveTextContent("Tal como está escrito, un nativo lee")
    expect(api.translateEntryPart).not.toHaveBeenCalled()

    fireEvent.click(within(screen.getByTestId("meaning-paraphrase")).getByRole("button", { name: "Explain in English" }))
    await waitFor(() => expect(screen.getByTestId("meaning-rescue")).toHaveTextContent(MEANING[0]))
    expect(translatedParts()).toEqual(["original"])
    expect(eventKinds()).toEqual(["reveal_meaning"])
  })

  it("rescues one note in the learner's language and logs rescue_note", async () => {
    renderEntry(3)
    const cards = screen.getAllByTestId("fix-card")
    expect(within(cards[0]).getByTestId("note-primary")).toHaveTextContent("Usa estar para estados.")
    expect(within(cards[0]).queryByTestId("note-secondary")).toBeNull()
    fireEvent.click(within(cards[1]).getByRole("button", { name: "Explain in English" }))
    await waitFor(() => expect(within(cards[1]).getByTestId("note-rescue")).toHaveTextContent(/^Use estar for states\.$/))
    expect(within(cards[1]).getByTestId("note-rescue").innerHTML).not.toContain("<p>")
    expect(api.translateEntryPart).toHaveBeenCalledWith("entry-1", "note:1", "en")
    expect(eventKinds()).toEqual(["rescue_note"])
  })

  it("offers the rewrite in the learner's language as a rescue", async () => {
    renderEntry(3)
    fireEvent.click(screen.getByRole("button", { name: "Native" }))
    fireEvent.click(within(screen.getByTestId("rewrite-gloss")).getByRole("button", { name: "Explain in English" }))
    await waitFor(() => expect(screen.getByTestId("rewrite-gloss")).toHaveTextContent("Today my sister is super bored."))
    expect(eventKinds()).toEqual(["reveal_rewrite_gloss"])
  })
})

describe("policy source", () => {
  it("falls back to the learner's current policy when the entry has no snapshot", async () => {
    renderEntry(null)
    await waitFor(() => expect(screen.getAllByTestId("meaning-blurred")).toHaveLength(3))
    expect(api.getCurrentPolicy).toHaveBeenCalledWith("es")
    expect(screen.getByText(/uses your current settings/)).toBeInTheDocument()
  })

  it("never asks for the current policy when a snapshot is stored", () => {
    renderEntry(2)
    expect(api.getCurrentPolicy).not.toHaveBeenCalled()
  })
})

describe("failure states", () => {
  it("shows a failed analysis with Retry, then reloads", async () => {
    const onReanalyzed = vi.fn()
    renderEntry(
      1,
      { analysis_status: "failed", analysis_error_code: "ai_unavailable", corrected: null, rewrite: null, ai_feedback: {} },
      { onReanalyzed },
    )
    expect(screen.getByTestId("analysis-failed")).toHaveTextContent("ai_unavailable")
    expect(screen.getByText("No correction yet")).toBeInTheDocument()
    expect(screen.queryByTestId("fix-card")).toBeNull()
    fireEvent.click(screen.getByRole("button", { name: "Retry analysis" }))
    await waitFor(() => expect(onReanalyzed).toHaveBeenCalled())
    expect(api.analyzeEntry).toHaveBeenCalledWith("entry-1")
  })

  it("keeps the failure visible when the retry fails again", async () => {
    api.analyzeEntry.mockRejectedValueOnce(new Error("503"))
    renderEntry(1, { analysis_status: "failed", ai_feedback: {} })
    fireEvent.click(screen.getByRole("button", { name: "Retry analysis" }))
    await waitFor(() => expect(screen.getByText(/Still unavailable/)).toBeInTheDocument())
  })

  it("offers Retry when the translation is unavailable", async () => {
    api.translateEntryPart.mockResolvedValueOnce({ status: "unavailable", sentences: [], text: "" })
    renderEntry(0)
    const unavailable = await screen.findByTestId("meaning-unavailable")
    fireEvent.click(within(unavailable).getByRole("button", { name: "Retry" }))
    await waitFor(() => expect(screen.getAllByTestId("meaning-text")).toHaveLength(3))
    expect(translatedParts().filter((part) => part === "original")).toHaveLength(2)
  })

  it("labels mock feedback as a sample", () => {
    renderEntry(0, { analysis_status: "mock" })
    expect(screen.getByTestId("sample-banner")).toHaveTextContent("Sample feedback")
  })
})
