import { describe, expect, it, vi } from "vitest"

import {
  alignSentences,
  cleanLiteralReading,
  htmlToText,
  diffWords,
  locateSuggestions,
  noteTexts,
  splitParagraphs,
  splitSentences,
  toSideBySideEntry,
} from "@/lib/side-by-side"

const ORIGINAL =
  "Mi hermana es muy aburrida hoy porque está lloviendo. Quiero que ella viene conmigo al cine para ver una película nueva. Despues comimos mucho palomitas y la película era muy divertido. Estoy muy embarazada porque olvidé su cumpleaños."

describe("splitSentences", () => {
  it("splits like the backend translation service", () => {
    expect(splitSentences(ORIGINAL)).toHaveLength(4)
    expect(splitSentences("¿Qué tal? ¡Muy bien! Vale…  Hasta luego")).toEqual(["¿Qué tal?", "¡Muy bien!", "Vale…", "Hasta luego"])
    expect(splitSentences("Una línea\nOtra línea\n\nTercera")).toEqual(["Una línea", "Otra línea", "Tercera"])
    expect(splitSentences("   ")).toEqual([])
    expect(splitSentences("Sin punto final")).toEqual(["Sin punto final"])
  })

  it("does not split inside a word or after a decimal point", () => {
    expect(splitSentences("Costó 3.50 euros. Barato.")).toEqual(["Costó 3.50 euros.", "Barato."])
  })
})

describe("alignSentences", () => {
  it("pairs one to one when the counts match", () => {
    expect(alignSentences(["a.", "b."], ["A.", "B."])).toEqual(["A.", "B."])
  })

  it("puts a merged correction beside the rows it came from", () => {
    const source = ["Fui al cine.", "Comimos palomitas.", "Volvimos a casa tarde."]
    const target = ["Fui al cine y comimos palomitas.", "Volvimos a casa tarde."]
    expect(alignSentences(source, target)).toEqual(["Fui al cine y comimos palomitas.", "", "Volvimos a casa tarde."])
  })

  it("joins a split correction back into one row", () => {
    const source = ["Fui al cine y comimos palomitas.", "Volvimos tarde."]
    const target = ["Fui al cine.", "Comimos palomitas.", "Volvimos tarde."]
    expect(alignSentences(source, target)).toEqual(["Fui al cine. Comimos palomitas.", "Volvimos tarde."])
  })

  it("keeps rows when there is nothing to align", () => {
    expect(alignSentences(["a.", "b."], [])).toEqual(["", ""])
    expect(alignSentences([], ["a."])).toEqual([])
  })
})

describe("diffWords", () => {
  it("marks the minimal word changes", () => {
    expect(diffWords("Mi hermana es muy aburrida", "Mi hermana está muy aburrida")).toEqual([
      { kind: "same", text: "Mi hermana" },
      { kind: "del", text: "es" },
      { kind: "ins", text: "está" },
      { kind: "same", text: "muy aburrida" },
    ])
  })

  it("returns a single unchanged part for identical text", () => {
    expect(diffWords("Hola amigo.", "Hola amigo.")).toEqual([{ kind: "same", text: "Hola amigo." }])
  })
})

describe("locateSuggestions", () => {
  const sentences = splitSentences(ORIGINAL)

  it("places each snippet once, in the sentence that contains it", () => {
    const marks = locateSuggestions(sentences, [
      { original: "es muy aburrida", corrected: "está muy aburrida" },
      { original: "viene", corrected: "venga" },
      { original: "Despues", corrected: "Después" },
      { original: "embarazada", corrected: "avergonzada" },
      { original: "not in the text", corrected: "x" },
    ])
    expect(marks.map((row) => row.map((mark) => mark.suggestion))).toEqual([[0], [1], [2], [3]])
    expect(sentences[0].slice(marks[0][0].start, marks[0][0].end)).toBe("es muy aburrida")
  })

  it("does not stack two suggestions on the same words", () => {
    const marks = locateSuggestions(["la casa y la casa."], [
      { original: "la casa", corrected: "el hogar" },
      { original: "la casa", corrected: "el hogar" },
    ])
    expect(marks[0].map((mark) => mark.start)).toEqual([0, 10])
  })

  it("falls back to a case-insensitive match", () => {
    const marks = locateSuggestions(["Despues fuimos."], [{ original: "despues", corrected: "después" }])
    expect(marks[0]).toHaveLength(1)
  })
})

describe("cleanLiteralReading", () => {
  it("drops a repeated lead-in and quotes", () => {
    expect(cleanLiteralReading("As written, a native reads 'I am very pregnant because I forgot her birthday'.")).toBe(
      "I am very pregnant because I forgot her birthday",
    )
    expect(cleanLiteralReading("Tal como está escrito: «Ella es una persona tediosa»")).toBe("Ella es una persona tediosa")
    expect(cleanLiteralReading("My sister is a boring person today")).toBe("My sister is a boring person today")
    expect(cleanLiteralReading('Como está escrito, un nativo lee: "un hispanohablante entiende que vas a tener un bebé"')).toBe(
      "un hispanohablante entiende que vas a tener un bebé",
    )
  })
})

describe("noteTexts", () => {
  const suggestion = { original: "es", corrected: "está", note: "fallback", note_l1: "In English", note_l2: "En español" }

  it("follows the stored explanation flag", () => {
    expect(noteTexts(suggestion, "l1")).toEqual({ primary: "In English", secondary: "" })
    expect(noteTexts(suggestion, "l1_with_l2_terms")).toEqual({ primary: "In English", secondary: "" })
    expect(noteTexts(suggestion, "l2_then_l1")).toEqual({ primary: "En español", secondary: "In English" })
    expect(noteTexts(suggestion, "l2")).toEqual({ primary: "En español", secondary: "" })
  })

  it("falls back to the legacy note", () => {
    expect(noteTexts({ original: "a", corrected: "b", note: "only note" }, "l2")).toEqual({ primary: "only note", secondary: "" })
  })
})

describe("splitParagraphs", () => {
  it("splits real newlines and the literal backslash-n older rows stored", () => {
    expect(splitParagraphs("One.\nTwo.\\nThree.")).toEqual(["One.", "Two.", "Three."])
  })
})

describe("toSideBySideEntry", () => {
  it("reads the tutor extras from the rubric column and keeps the snapshot", () => {
    const entry = toSideBySideEntry({
      id: "e1",
      language: "es",
      content: "Hola.",
      corrected: "Hola.",
      rewrite: "¡Hola!",
      analysis_status: "ok",
      policy_snapshot: { v: 1, l1: "en", l2: "es", meaning: "tap", explanation: "l1", rewrite_gloss: "l1_tap" },
      ai_feedback: {
        score: 80,
        grammar_suggestions: [{ original: "a", corrected: "b", note: "n" }],
        rubric: {
          grammar: 70,
          intended_meaning: "Hello.",
          ambiguities: [{ question: "Did you mean…?", span: "Hola" }],
          rewrite_idioms: [{ phrase: "¡Hola!", gloss: "hi" }],
        },
      },
    })
    expect(entry.policy?.meaning).toBe("tap")
    expect(entry.intendedMeaning).toBe("Hello.")
    expect(entry.ambiguities).toHaveLength(1)
    expect(entry.rewriteIdioms).toHaveLength(1)
    expect(entry.suggestions).toHaveLength(1)
    expect(entry.rubric?.grammar).toBe(70)
  })

  it("treats rows without a status or snapshot as legacy", () => {
    const entry = toSideBySideEntry({ id: "e2", language: "es", content: "Hola.", ai_feedback: null })
    expect(entry.analysisStatus).toBe("legacy")
    expect(entry.policy).toBeNull()
    expect(entry.suggestions).toEqual([])
  })
})

describe("resolveLanguage", () => {
  it("accepts the codes entries store and the names older rows used", async () => {
    const { resolveLanguage } = await import("@/i18n/languages")
    expect(resolveLanguage("es")?.flag).toBe("🇪🇸")
    expect(resolveLanguage("pt-BR")?.name).toBe("Portuguese")
    expect(resolveLanguage("Japanese")?.code).toBe("ja")
    expect(resolveLanguage("tone-like value")).toBeUndefined()
    expect(resolveLanguage(undefined)).toBeUndefined()
  })
})

describe("dashboard languages practiced", () => {
  it("counts languages, not tones", async () => {
    vi.doMock("@/lib/supabase", () => ({ supabase: {} }))
    vi.doMock("@/lib/auth", () => ({ getUser: vi.fn() }))
    const { practicedLanguages } = await import("@/lib/user-service")
    const result = practicedLanguages([
      { language: "es" },
      { language: "es" },
      { language: "Spanish" },
      { language: "fr" },
      { language: null },
    ])
    expect(result).toEqual({ languages: ["Spanish", "French"], languageEmojis: ["🇪🇸", "🇫🇷"] })
  })
})

describe("htmlToText", () => {
  it("turns a translated HTML note into plain text", () => {
    expect(htmlToText('<p>\'<span translate="no">Embarazada</span>\' means &quot;pregnant&quot;.</p>')).toBe(
      "'Embarazada' means \"pregnant\".",
    )
    expect(htmlToText("Plain note.")).toBe("Plain note.")
  })
})
