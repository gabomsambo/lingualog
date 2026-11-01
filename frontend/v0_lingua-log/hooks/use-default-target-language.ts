"use client"

import { useEffect, useState } from "react"

import { getUserSettings } from "@/lib/api"

export const FALLBACK_TARGET_LANGUAGE = "es"

/** The learner's default target language; Spanish only until settings load or when they cannot. */
export function useDefaultTargetLanguage(): string {
  const [language, setLanguage] = useState(FALLBACK_TARGET_LANGUAGE)
  useEffect(() => {
    let active = true
    getUserSettings()
      .then((settings) => {
        if (active && settings.default_target_lang) setLanguage(settings.default_target_lang)
      })
      .catch(() => undefined)
    return () => {
      active = false
    }
  }, [])
  return language
}
