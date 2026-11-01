"use client"

import { Activity } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useLocale } from "@/i18n/LocaleProvider"
import { resolveLanguage } from "@/i18n/languages"
import type { ErrorPatterns } from "@/lib/api"

interface ErrorPatternsPanelProps {
  patterns: ErrorPatterns | null
  loading: boolean
  failed: boolean
}

function languageLabel(code: string) {
  const language = resolveLanguage(code)
  return `${language?.flag || "🌐"} ${language?.name || code.toUpperCase()}`
}

export function ErrorPatternsPanel({ patterns, loading, failed }: ErrorPatternsPanelProps) {
  const { t } = useLocale()

  return (
    <section aria-labelledby="error-patterns-title" data-testid="error-patterns-panel">
      <Card className="fun-card border-fun-teal/30">
        <CardHeader>
          <CardTitle id="error-patterns-title" className="flex items-center text-xl">
            <Activity className="mr-2 h-5 w-5 text-fun-teal" />
            {t("feedback.errorPatternsTitle")}
          </CardTitle>
          <CardDescription>
            {t("feedback.errorPatternsDesc", { count: patterns?.window_entries ?? 0 })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              {t("common.calculatingProgress")}
            </p>
          ) : failed ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              {t("feedback.errorPatternsLoadError")}
            </p>
          ) : patterns?.languages.length ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {patterns.languages.map((language) => (
                <div className="rounded-2xl border bg-card/70 p-4" key={language.language}>
                  <h3 className="mb-3 text-sm font-semibold">{languageLabel(language.language)}</h3>
                  <ol className="space-y-2">
                    {language.top_tags.slice(0, 3).map((tag) => (
                      <li
                        className="flex items-center justify-between gap-3 rounded-xl bg-muted/50 px-3 py-2"
                        key={tag.error_type}
                      >
                        <span className="text-sm">{t(`feedback.errorTag_${tag.error_type}`)}</span>
                        <Badge variant="secondary" className="shrink-0">
                          {t("feedback.errorPatternsCount", { count: tag.count })}
                        </Badge>
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-muted-foreground">
              {t("feedback.errorPatternsEmpty")}
            </p>
          )}
        </CardContent>
      </Card>
    </section>
  )
}
