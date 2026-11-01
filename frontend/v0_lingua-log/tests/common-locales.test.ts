import { describe, expect, it } from "vitest"

import ar from "@/locales/ar/common.json"
import en from "@/locales/en/common.json"
import es from "@/locales/es/common.json"
import he from "@/locales/he/common.json"

const locales = { en, es, ar, he }

describe("common namespace", () => {
  it.each(Object.entries(locales))("%s has the entry page keys", (_lang, bundle) => {
    const keys = ["copyText", "copied", "addToFavorites", "removeFromFavorites", "entryNotFound"]
    for (const key of keys) {
      expect((bundle as Record<string, string>)[key], key).toBeTruthy()
    }
  })

  it("en copyText is Copy Text", () => {
    expect(en.copyText).toBe("Copy Text")
  })
})
