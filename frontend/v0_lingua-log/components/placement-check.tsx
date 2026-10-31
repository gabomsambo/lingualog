"use client"

import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingSpinner } from "@/components/loading-spinner"
import { useLocale } from "@/i18n/LocaleProvider"
import { getPlacementCheck, submitPlacementCheck, type PlacementResult } from "@/lib/api"

interface PlacementCheckProps {
  language: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onResult?: (result: PlacementResult) => void
}

/** The optional 2-minute check: tap the words you know, get a size estimate. Never a score. */
export function PlacementCheck({ language, open, onOpenChange, onResult }: PlacementCheckProps) {
  const { t } = useLocale()
  const [words, setWords] = useState<string[]>([])
  const [bands, setBands] = useState<string[][]>([])
  const [known, setKnown] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError("")
    setKnown(new Set())
    getPlacementCheck(language)
      .then((check) => {
        setWords(check.words)
        setBands(check.bands)
      })
      .catch(() => setError(t("vocabulary.placementFailed")))
      .finally(() => setLoading(false))
  }, [open, language])

  const toggle = (word: string) => {
    setKnown((current) => {
      const next = new Set(current)
      if (next.has(word)) next.delete(word)
      else next.add(word)
      return next
    })
  }

  const submit = async () => {
    setSubmitting(true)
    setError("")
    try {
      const result = await submitPlacementCheck(language, [...known])
      onResult?.(result)
      onOpenChange(false)
    } catch {
      setError(t("vocabulary.placementFailed"))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("vocabulary.placementDialogTitle")}</DialogTitle>
          <DialogDescription>{t("vocabulary.placementDialogBody")}</DialogDescription>
        </DialogHeader>
        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <LoadingSpinner text={t("vocabulary.placementLoading")} />
          </div>
        ) : (
          <div className="space-y-4" data-testid="placement-words">
            {bands.map((band, index) => (
              <div key={index} className="flex flex-wrap gap-2">
                {band.map((word) => (
                  <Button
                    key={word}
                    type="button"
                    size="sm"
                    variant={known.has(word) ? "default" : "outline"}
                    className="rounded-full"
                    aria-pressed={known.has(word)}
                    onClick={() => toggle(word)}
                  >
                    {word}
                  </Button>
                ))}
              </div>
            ))}
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
        <DialogFooter>
          <span className="mr-auto text-xs text-muted-foreground">
            {t("vocabulary.placementTapped", { count: known.size, total: words.length })}
          </span>
          <Button onClick={submit} disabled={loading || submitting || words.length === 0}>
            {submitting ? t("vocabulary.placementSubmitting") : t("vocabulary.placementSubmit")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
