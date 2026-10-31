import { describe, expect, it } from "vitest"

import { isCorrectAnswer, normalizeAnswer, statusClass } from "@/lib/review"

describe("normalizeAnswer", () => {
  it.each([
    ["  Aproveché ", "aproveche"],
    ["ECHAR   de  menos", "echar de menos"],
    ["niño", "nino"],
    ["", ""],
  ])("%j -> %j", (input, expected) => expect(normalizeAnswer(input)).toBe(expected))
})

describe("isCorrectAnswer", () => {
  const card = { accepted: ["aproveche", "aprovechar"] }
  it("matches any accepted form regardless of case and accents", () => {
    expect(isCorrectAnswer(card, "APROVECHÉ")).toBe(true)
    expect(isCorrectAnswer(card, "aprovechar")).toBe(true)
  })
  it("rejects other words and empty input", () => {
    expect(isCorrectAnswer(card, "aprobar")).toBe(false)
    expect(isCorrectAnswer(card, "   ")).toBe(false)
  })
})

describe("statusClass", () => {
  it("colours New blue, Learning amber and Known green", () => {
    expect(statusClass("new")).toContain("bg-blue-100")
    expect(statusClass("learning")).toContain("bg-amber-100")
    expect(statusClass("known")).toContain("bg-green-100")
    expect(statusClass("mastered")).toContain("bg-green-100")
  })
  it("mutes ignored words and treats a missing state as New", () => {
    expect(statusClass("ignored")).toContain("text-muted-foreground")
    expect(statusClass(undefined)).toBe(statusClass("new"))
    expect(statusClass("???")).toBe(statusClass("ignored"))
  })
})
