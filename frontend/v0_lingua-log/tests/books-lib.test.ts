import { describe, expect, it } from "vitest"

import { alreadyHave, candidateIndex, normalizeWord, sentenceOf, splitSentences, tokenize } from "@/lib/books"

const PAGE = "Tenía las manos atadas con una cinta. «Estremecí al verla», dijo.\nNada más."

describe("tokenize", () => {
  it("keeps every character, so the page can be rebuilt exactly", () => {
    expect(tokenize(PAGE).map((token) => token.text).join("")).toBe(PAGE)
  })

  it("makes words tappable and leaves spaces and punctuation alone", () => {
    const words = tokenize(PAGE).filter((token) => token.word).map((token) => token.text)
    expect(words.slice(0, 6)).toEqual(["Tenía", "las", "manos", "atadas", "con", "una"])
    expect(words).toContain("Estremecí")
    expect(tokenize("¿Qué?").filter((token) => token.word).map((token) => token.text)).toEqual(["Qué"])
  })

  it("keeps hyphenated and apostrophe words whole", () => {
    expect(tokenize("l'amour est peut-être").filter((token) => token.word).map((token) => token.text)).toEqual([
      "l'amour", "est", "peut-être",
    ])
  })

  it("splits sentences at stops and line breaks", () => {
    const tokens = tokenize(PAGE)
    const index = (word: string) => tokens.findIndex((token) => token.text === word)
    expect(sentenceOf(tokens, index("atadas"))).toBe("Tenía las manos atadas con una cinta.")
    expect(sentenceOf(tokens, index("Estremecí"))).toBe("«Estremecí al verla», dijo.")
    expect(sentenceOf(tokens, index("Nada"))).toBe("Nada más.")
  })

  it("agrees with how sentences are split for the server", () => {
    expect(splitSentences(PAGE)).toEqual([
      "Tenía las manos atadas con una cinta.",
      "«Estremecí al verla», dijo.",
      "Nada más.",
    ])
  })
})

describe("normalizeWord", () => {
  it("drops edge punctuation and case but keeps accents", () => {
    expect(normalizeWord("«Estremecí»,")).toBe("estremecí")
    expect(normalizeWord("  Echar   de menos. ")).toBe("echar de menos")
  })
})

describe("candidates", () => {
  const index = candidateIndex([
    { surface: "atadas", lemma: "atar", status: null },
    { surface: "cinta", lemma: "cinta", status: "known" },
  ])

  it("finds a tapped word by its printed form or its lemma", () => {
    expect(index.get(normalizeWord("Atadas"))?.lemma).toBe("atar")
    expect(index.get("atar")?.surface).toBe("atadas")
    expect(index.get("mesa")).toBeUndefined()
  })

  it("treats known, mastered and ignored words as already had", () => {
    expect(["known", "mastered", "ignored"].every((status) => alreadyHave(status as never))).toBe(true)
    expect([null, undefined, "new", "learning"].some((status) => alreadyHave(status as never))).toBe(false)
  })
})
