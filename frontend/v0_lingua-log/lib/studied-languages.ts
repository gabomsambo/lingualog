import type { UserSettingsData } from "@/lib/api"

/** The languages the learner studies, default first. Settings is the only place this list changes. */
export function studiedLanguages(
  settings: Pick<UserSettingsData, "language_profiles" | "default_target_lang"> | null,
): string[] {
  const active = (settings?.language_profiles ?? []).filter((row) => row.active !== false).map((row) => row.l2)
  const fallback = settings?.default_target_lang || "es"
  return [fallback, ...active.filter((code) => code !== fallback)]
}
