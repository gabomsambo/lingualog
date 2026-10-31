import { describe, expect, it } from "vitest"

import { BANK_SIZE, mergeShuffle, selectionFor, wordAppearsIn, type WordBankWord } from "@/lib/word-bank"

const word = (id: string, forms: string[] = [id]): WordBankWord => ({
  word_id: id, lemma: id, term: id, status: "learning", reason: "never_used", forms, hint: "meaning",
  hint_mode: "shown", use_days: 0,
})

describe("wordAppearsIn", () => {
  it("matches a stored form as a whole word, ignoring case and accents", () => {
    expect(wordAppearsIn("Ayer MADRUGUÉ para correr.", ["madrugué"], "es")).toBe(true)
    expect(wordAppearsIn("Ayer madrugue para correr.", ["madrugué"], "es")).toBe(true)
    expect(wordAppearsIn("Ayer madrugué.", ["madrugar", "madrugué"], "es")).toBe(true)
  })

  it("does not tick for a form that is only part of another word", () => {
    expect(wordAppearsIn("Un abrato largo", ["rato"], "es")).toBe(false)
    expect(wordAppearsIn("Un rato largo", ["rato"], "es")).toBe(true)
    expect(wordAppearsIn("ratones", ["rato"], "es")).toBe(false)
  })

  it("matches phrases and words next to punctuation", () => {
    expect(wordAppearsIn("Te echo de menos, mucho.", ["echar de menos", "echo de menos"], "es")).toBe(true)
    expect(wordAppearsIn("¿Aprovechas?", ["aprovechas"], "es")).toBe(true)
  })

  it("treats unspaced languages as substrings", () => {
    expect(wordAppearsIn("今日は勉強しました", ["勉強"], "ja")).toBe(true)
    expect(wordAppearsIn("今日は散歩しました", ["勉強"], "ja")).toBe(false)
  })

  it("handles regex characters, empty drafts and empty forms", () => {
    expect(wordAppearsIn("what (is) this", ["(is)"], "en")).toBe(true)
    expect(wordAppearsIn("", ["rato"], "es")).toBe(false)
    expect(wordAppearsIn("rato", ["", "  "], "es")).toBe(false)
  })
})

describe("selectionFor", () => {
  const words = [word("a"), word("b"), word("c")]

  it("sends every shown word and no challenge by default", () => {
    expect(selectionFor(words, false, new Set())).toEqual({ targetWordIds: ["a", "b", "c"], challengeWordIds: [] })
  })

  it("in challenge mode only the words never peeked at are challenge words", () => {
    expect(selectionFor(words, true, new Set(["b"]))).toEqual({
      targetWordIds: ["a", "b", "c"],
      challengeWordIds: ["a", "c"],
    })
  })
})

describe("mergeShuffle", () => {
  it("keeps pinned words first and fills the rest from the offer", () => {
    const current = ["a", "b", "c", "d", "e", "f"].map((id) => word(id))
    const offered = ["g", "h", "i", "j", "k"].map((id) => word(id))
    const merged = mergeShuffle(current, new Set(["b", "e"]), offered)
    expect(merged.map((w) => w.word_id)).toEqual(["b", "e", "g", "h", "i", "j"])
    expect(merged).toHaveLength(BANK_SIZE)
  })

  it("never offers a pinned word twice", () => {
    const merged = mergeShuffle([word("a")], new Set(["a"]), [word("a"), word("b")])
    expect(merged.map((w) => w.word_id)).toEqual(["a", "b"])
  })
})
