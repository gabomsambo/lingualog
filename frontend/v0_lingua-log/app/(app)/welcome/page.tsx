"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, ArrowRight, Check } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useLocale } from "@/i18n/LocaleProvider"
import { getEntries, getLearningLevels, getUserSettings, postLogEntry, updateUserSettings } from "@/lib/api"
import type { FirstRunLevelCriteria, LanguageProfileData, UserSettingsData, UserSettingsUpdate } from "@/lib/api"
import { getLanguageDisplayName, LANGUAGES } from "@/i18n/languages"

type Goal = "class" | "exam" | "trip" | "work" | "just_for_me"
type Level = "A1" | "A2" | "B1" | "B2"

const firstRunLevels: Level[] = ["A1", "A2", "B1", "B2"]

const promptTranslation: Record<Level, string> = {
  A1: "welcome.entryPromptA1",
  A2: "welcome.entryPromptA2",
  B1: "welcome.entryPromptB1",
  B2: "welcome.entryPromptB2",
}

const frameTranslations = ["welcome.frameName", "welcome.frameOrigin", "welcome.frameHome", "welcome.frameLikes"]

function languageProfile(
  settings: UserSettingsData,
  l2: string,
  changes: Partial<LanguageProfileData> = {},
): LanguageProfileData {
  const saved = settings.language_profiles?.find((profile) => profile.l2 === l2)
  return {
    l2,
    immersion_level: changes.immersion_level ?? saved?.immersion_level ?? 0,
    proficiency: changes.proficiency ?? saved?.proficiency ?? "A1",
    active: true,
    ...changes,
  }
}

export default function WelcomePage() {
  const router = useRouter()
  const { t, uiLang } = useLocale()
  const [step, setStep] = useState(1)
  const [settings, setSettings] = useState<UserSettingsData | null>(null)
  const [levels, setLevels] = useState<Record<string, FirstRunLevelCriteria> | null>(null)
  const [targetLanguage, setTargetLanguage] = useState("es")
  const [nativeLanguage, setNativeLanguage] = useState("en")
  const [proficiency, setProficiency] = useState<Level>("A1")
  const [choiceId, setChoiceId] = useState("brand-new")
  const [goal, setGoal] = useState<Goal | null>(null)
  const [frameValues, setFrameValues] = useState<string[]>(["", "", "", ""])
  const [freeWrite, setFreeWrite] = useState(false)
  const [entryText, setEntryText] = useState("")
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState("")
  const loadErrorText = t("welcome.loadError")

  useEffect(() => {
    let active = true
    Promise.all([getUserSettings(), getEntries(), getLearningLevels()])
      .then(([savedSettings, entries, criteria]) => {
        if (!active) return
        const profile = savedSettings.language_profiles?.find(
          (item) => item.l2 === savedSettings.default_target_lang,
        )
        if (profile?.onboarded_at || entries.length > 0) {
          router.replace("/dashboard")
          return
        }

        const savedLevel = (profile?.proficiency || "A1") as Level
        setSettings(savedSettings)
        setLevels(criteria)
        setTargetLanguage(savedSettings.default_target_lang || "es")
        setNativeLanguage(savedSettings.native_lang || "en")
        setProficiency(savedLevel)
        setChoiceId(savedLevel === "A1" ? "brand-new" : savedLevel.toLowerCase())
        setGoal((profile?.goal as Goal | null) || null)
        setIsLoading(false)
      })
      .catch((loadError) => {
        console.error("Could not load first-run details:", loadError)
        if (active) {
          setError(loadErrorText)
          setIsLoading(false)
        }
      })
    return () => {
      active = false
    }
  }, [router, loadErrorText])

  const selectedCriteria = levels?.[proficiency]
  const assembledFrames = useMemo(() => {
    const frames = levels?.[proficiency]?.first_entry.frames
    if (!frames) return ""
    return frames
      .map((frame, index) => frameValues[index].trim() ? `${frame.prefix} ${frameValues[index].trim()}.` : "")
      .filter(Boolean)
      .join(" ")
  }, [frameValues, levels, proficiency])
  const currentText = freeWrite || targetLanguage !== "es" || selectedCriteria?.first_entry.kind !== "frames"
    ? entryText
    : assembledFrames
  const wordCount = currentText.trim().split(/\s+/).filter(Boolean).length
  const languageName = getLanguageDisplayName(targetLanguage)

  const saveSettings = async (update: UserSettingsUpdate): Promise<boolean> => {
    setIsSaving(true)
    setError("")
    try {
      const updated = await updateUserSettings(update)
      setSettings(updated)
      return true
    } catch (saveError) {
      console.error("Could not save first-run settings:", saveError)
      setError(loadErrorText)
      return false
    } finally {
      setIsSaving(false)
    }
  }

  const saveLanguage = async () => {
    if (!settings) return false
    return saveSettings({
      native_lang: nativeLanguage,
      default_target_lang: targetLanguage,
      language_profiles: [languageProfile(settings, targetLanguage)],
    })
  }

  const saveLevel = async () => {
    if (!settings || !levels) return false
    const criteria = levels[proficiency]
    if (!criteria) return false
    return saveSettings({
      language_profiles: [languageProfile(settings, targetLanguage, {
        proficiency,
        immersion_level: criteria.default_immersion,
      })],
    })
  }

  const saveGoal = async () => {
    if (!settings || !goal) return true
    return saveSettings({
      language_profiles: [languageProfile(settings, targetLanguage, { goal })],
    })
  }

  const handleContinue = async () => {
    if (step === 1) {
      if (await saveLanguage()) setStep(2)
      return
    }
    if (step === 2) {
      if (await saveLevel()) setStep(3)
      return
    }
    if (step === 3) {
      if (await saveGoal()) setStep(4)
    }
  }

  const handleSkip = () => {
    if (step === 1 && settings) {
      setTargetLanguage(settings.default_target_lang || "es")
      setNativeLanguage(settings.native_lang || "en")
    }
    if (step === 2 && settings) {
      const savedLevel = (settings.language_profiles?.find((profile) => profile.l2 === targetLanguage)?.proficiency || "A1") as Level
      setProficiency(savedLevel)
      setChoiceId(savedLevel === "A1" ? "brand-new" : savedLevel.toLowerCase())
    }
    if (step === 3) {
      setGoal(settings?.language_profiles?.find((profile) => profile.l2 === targetLanguage)?.goal as Goal || null)
    }
    if (step < 4) {
      setError("")
      setStep((current) => current + 1)
    } else {
      router.replace("/dashboard")
    }
  }

  const handlePlacementChange = (id: string, level: Level) => {
    setChoiceId(id)
    setProficiency(level)
  }

  const submitFirstEntry = async () => {
    if (currentText.trim().length < 5) return
    setIsSaving(true)
    setError("")
    try {
      const result = await postLogEntry(currentText.trim(), t("welcome.firstEntryTitle"), targetLanguage)
      if (!result.id) throw new Error("The saved entry did not include an id")
      router.push(`/entries/${result.id}`)
    } catch (submitError) {
      console.error("Could not submit first entry:", submitError)
      setError(t("welcome.saveError"))
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return <div className="mx-auto max-w-3xl py-16 text-center text-muted-foreground">{t("common.loading")}</div>
  }

  const title = step === 1
    ? "welcome.titleLanguage"
    : step === 2
      ? "welcome.titleLevel"
      : step === 3
        ? "welcome.titleGoal"
        : "welcome.titleEntry"
  const description = step === 1
    ? "welcome.descLanguage"
    : step === 2
      ? "welcome.descLevel"
      : step === 3
        ? "welcome.descGoal"
        : "welcome.descEntry"

  return (
    <div className="mx-auto max-w-3xl px-4 py-8" dir={uiLang.startsWith("ar") || uiLang.startsWith("he") ? "rtl" : "ltr"}>
      <div className="mb-6 flex items-center justify-between gap-4">
        <Button variant="ghost" onClick={() => step > 1 && setStep((current) => current - 1)} disabled={step === 1 || isSaving}>
          <ArrowLeft className="mr-2 h-4 w-4" />{t("welcome.back")}
        </Button>
        <p className="text-sm font-semibold text-muted-foreground" aria-live="polite">
          {t("welcome.stepProgress", { step })}
        </p>
        <div className="flex gap-1.5" aria-hidden="true">
          {[1, 2, 3, 4].map((item) => (
            <span key={item} className={`h-2.5 w-2.5 rounded-full ${item === step ? "bg-fun-purple" : item < step ? "bg-fun-blue" : "bg-muted"}`} />
          ))}
        </div>
      </div>

      <Card className="border-pastel-purple/30 shadow-soft-lg">
        <CardHeader className="space-y-3">
          <CardTitle className="text-3xl font-bold text-fun-purple">
            {step === 2 ? t(title, { language: languageName }) : t(title)}
          </CardTitle>
          <CardDescription className="text-base">{t(description)}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {step === 1 && (
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="welcome-target">{t("welcome.learningLabel")}</Label>
                <select
                  id="welcome-target"
                  value={targetLanguage}
                  onChange={(event) => setTargetLanguage(event.target.value)}
                  className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {LANGUAGES.map((language) => (
                    <option key={language.code} value={language.code}>{language.flag} {language.name}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="welcome-native">{t("welcome.explainLabel")}</Label>
                <select
                  id="welcome-native"
                  value={nativeLanguage}
                  onChange={(event) => setNativeLanguage(event.target.value)}
                  className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {LANGUAGES.map((language) => (
                    <option key={language.code} value={language.code}>{language.flag} {language.name}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <p className="text-sm font-medium text-fun-purple">{t("welcome.startFromScratch")}</p>
              <div className="space-y-3">
                {[
                  { id: "brand-new", level: "A1" as Level, translation: "welcome.brandNew" },
                  ...firstRunLevels.map((level) => ({
                    id: level.toLowerCase(),
                    level,
                    translation: level === "A2" && targetLanguage !== "es"
                      ? "welcome.canDoA2Other"
                      : `welcome.${levels?.[level]?.can_do_key || `canDo${level}`}`,
                  })),
                ].map((choice) => (
                  <button
                    key={choice.id}
                    type="button"
                    aria-pressed={choiceId === choice.id}
                    onClick={() => handlePlacementChange(choice.id, choice.level)}
                    className={`flex w-full items-start justify-between gap-4 rounded-xl border-2 p-4 text-left transition-colors ${choiceId === choice.id ? "border-fun-purple bg-fun-purple/5" : "border-border hover:border-fun-purple/40"}`}
                  >
                    <span className="text-sm leading-6">{t(choice.translation, { language: languageName })}</span>
                    <span className="shrink-0 rounded-full bg-muted px-2.5 py-1 text-xs font-semibold text-muted-foreground">{choice.level}</span>
                  </button>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">{t("welcome.descLevel")}</p>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-5">
              <div className="grid gap-3 sm:grid-cols-2">
                {([
                  ["class", "welcome.goalClass"],
                  ["exam", "welcome.goalExam"],
                  ["trip", "welcome.goalTrip"],
                  ["work", "welcome.goalWork"],
                  ["just_for_me", "welcome.goalPersonal"],
                ] as Array<[Goal, string]>).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    aria-pressed={goal === value}
                    onClick={() => setGoal(value)}
                    className={`rounded-xl border-2 px-4 py-4 text-sm font-semibold transition-colors ${goal === value ? "border-fun-purple bg-fun-purple/5 text-fun-purple" : "border-border hover:border-fun-purple/40"}`}
                  >
                    {goal === value && <Check className="mr-2 inline h-4 w-4" />}
                    {t(label)}
                  </button>
                ))}
              </div>
              {goal === "class" && <p className="rounded-lg bg-fun-blue/5 p-4 text-sm text-muted-foreground">{t("welcome.classNoteTeaser")}</p>}
            </div>
          )}

          {step === 4 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-semibold">{t(promptTranslation[proficiency])}</h2>
                {proficiency === "A2" && (
                  <p className="mt-2 text-sm text-muted-foreground">
                    {t(targetLanguage === "es" ? "welcome.entryHintA2" : "welcome.entryHintA2Other")}
                  </p>
                )}
                {targetLanguage !== "es" && <p className="mt-2 text-sm text-muted-foreground">{t("welcome.languagesComingSoon")}</p>}
              </div>

              {targetLanguage === "es" && selectedCriteria?.first_entry.kind === "frames" && !freeWrite ? (
                <div className="space-y-4">
                  {selectedCriteria.first_entry.frames?.map((frame, index) => (
                    <div key={frame.prefix} className="grid items-center gap-3 sm:grid-cols-[minmax(140px,0.55fr)_1fr]">
                      <Label htmlFor={`welcome-frame-${index}`} className="text-sm font-medium">{frame.prefix}…</Label>
                      <Input
                        id={`welcome-frame-${index}`}
                        value={frameValues[index] || ""}
                        onChange={(event) => setFrameValues((values) => values.map((value, at) => at === index ? event.target.value : value))}
                        placeholder={t(frameTranslations[index] || "welcome.frameName")}
                      />
                    </div>
                  ))}
                  <Button type="button" variant="ghost" size="sm" onClick={() => setFreeWrite(true)}>
                    {t("welcome.writeFreely")} <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <Textarea
                    value={entryText}
                    onChange={(event) => setEntryText(event.target.value)}
                    placeholder={t("welcome.entryPlaceholder", { language: languageName })}
                    className="min-h-[180px] text-base font-serif"
                    lang={targetLanguage}
                    dir={targetLanguage === "ar" || targetLanguage === "he" ? "rtl" : "ltr"}
                  />
                  {targetLanguage === "es" && selectedCriteria?.first_entry.kind === "frames" && freeWrite && (
                    <Button type="button" variant="ghost" size="sm" onClick={() => setFreeWrite(false)}>
                      <ArrowLeft className="mr-2 h-4 w-4" />{t("welcome.useFrames")}
                    </Button>
                  )}
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
                <span>{t("welcome.wordCount")}: {wordCount}</span>
                {selectedCriteria && (
                  <span>{t("welcome.softTarget", { min: selectedCriteria.soft_entry_words[0], max: selectedCriteria.soft_entry_words[1] })}</span>
                )}
              </div>
            </div>
          )}

          {error && <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</p>}

          <div className="flex flex-col-reverse justify-between gap-3 border-t pt-5 sm:flex-row sm:items-center">
            <Button variant="ghost" onClick={handleSkip} disabled={isSaving}>
              {t("welcome.skip")}
            </Button>
            {step < 4 ? (
              <Button onClick={handleContinue} disabled={isSaving} className="bg-gradient-to-r from-fun-blue to-fun-purple text-white hover:opacity-90">
                {t("welcome.continue")} <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            ) : (
              <Button onClick={submitFirstEntry} disabled={isSaving || currentText.trim().length < 5} className="bg-gradient-to-r from-fun-green to-fun-blue text-white hover:opacity-90">
                {isSaving ? t("welcome.checking") : t("welcome.checkWriting")}
                {!isSaving && <ArrowRight className="ml-2 h-4 w-4" />}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
