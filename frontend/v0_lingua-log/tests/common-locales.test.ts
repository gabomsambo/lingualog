import { describe, expect, it } from "vitest"

import i18n from "@/i18n/i18n"
import ar from "@/locales/ar/common.json"
import en from "@/locales/en/common.json"
import es from "@/locales/es/common.json"
import he from "@/locales/he/common.json"

const jsonBundles = { en, es, ar, he }
const keys = ["copyText", "copied", "addToFavorites", "removeFromFavorites", "entryNotFound", "entry"]

describe("common namespace", () => {
  it.each(["en", "es", "ar", "he"])("%s resolves the entry page keys inline", (lang) => {
    for (const key of keys) {
      expect(i18n.getResource(lang, "common", key), `${lang}.${key}`).toBeTruthy()
    }
  })

  it.each(Object.entries(jsonBundles))("%s common.json has the entry page keys", (_lang, bundle) => {
    for (const key of keys) {
      expect((bundle as Record<string, string>)[key], key).toBeTruthy()
    }
  })

  it("english copyText is Copy Text", () => {
    expect(i18n.getResource("en", "common", "copyText")).toBe("Copy Text")
  })
})
