"use client"

import { useCallback, useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { useLocale } from "@/i18n/LocaleProvider"
import { getLanguageDisplayName } from "@/i18n/languages"
import {
  acceptLevelSuggestion,
  dismissLevelSuggestion,
  getLevelSuggestions,
  type LevelSuggestion,
} from "@/lib/api"

interface LevelSuggestionCardProps {
  /** When set, only the suggestion for this target language is shown. */
  l2?: string
  /** Called after the learner accepts, so open settings state can reload. */
  onAccepted?: () => void
}

export function LevelSuggestionCard({ l2, onAccepted }: LevelSuggestionCardProps) {
  const { t } = useLocale()
  const [suggestion, setSuggestion] = useState<LevelSuggestion | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const payload = await getLevelSuggestions()
      const rows = payload.suggestions || []
      const match = l2 ? rows.find((row) => row.l2 === l2) : rows[0]
      setSuggestion(match || null)
    } catch {
      setSuggestion(null)
    }
  }, [l2])

  useEffect(() => {
    void load()
  }, [load])

  if (!suggestion) return null

  const language = getLanguageDisplayName(suggestion.l2)
  const down = suggestion.direction === "down"
  const title = down
    ? t("feedback.levelSuggestionDown", { level: suggestion.to_level })
    : t("feedback.levelSuggestionUp", { level: suggestion.to_level })
  const detail = down
    ? t("feedback.levelSuggestionDownBody", { language })
    : t("feedback.levelSuggestionUpBody", { language })

  const respond = async (action: "accept" | "dismiss") => {
    setBusy(true)
    try {
      if (action === "accept") {
        await acceptLevelSuggestion(suggestion.l2)
        onAccepted?.()
      } else {
        await dismissLevelSuggestion(suggestion.l2)
      }
      await load()
    } catch {
      setBusy(false)
      return
    }
    setBusy(false)
  }

  return (
    <Card
      className="rounded-3xl border-fun-purple/30 bg-fun-purple/5 shadow-lg"
      data-testid="level-suggestion-card"
      data-direction={suggestion.direction}
      data-l2={suggestion.l2}
    >
      <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-lg font-bold">{title}</p>
          <p className="mt-1 text-sm text-muted-foreground">{detail}</p>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button
            type="button"
            className="rounded-full bg-gradient-to-r from-fun-mint to-fun-blue text-white"
            disabled={busy}
            data-testid="level-suggestion-accept"
            onClick={() => void respond("accept")}
          >
            {t("feedback.levelSuggestionAccept")}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="rounded-full"
            disabled={busy}
            data-testid="level-suggestion-dismiss"
            onClick={() => void respond("dismiss")}
          >
            {t("feedback.levelSuggestionDismiss")}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
