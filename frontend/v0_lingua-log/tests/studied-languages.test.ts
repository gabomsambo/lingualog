import { describe, expect, it } from "vitest"

import { studiedLanguages } from "@/lib/studied-languages"

describe("studiedLanguages", () => {
  it("lists the default first, then active profiles, never removed ones", () => {
    expect(
      studiedLanguages({
        default_target_lang: "fr",
        language_profiles: [
          { l2: "en", immersion_level: 1, proficiency: "B2", active: true },
          { l2: "fr", immersion_level: 2, proficiency: "A2", active: true },
          { l2: "ja", immersion_level: 0, proficiency: "A1", active: false },
          { l2: "es", immersion_level: 3, proficiency: "C1" },
        ],
      }),
    ).toEqual(["fr", "en", "es"])
  })

  it("falls back to Spanish before settings load", () => {
    expect(studiedLanguages(null)).toEqual(["es"])
  })
})
