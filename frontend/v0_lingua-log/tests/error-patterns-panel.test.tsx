import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    t: (key: string, vars?: Record<string, unknown>) => `${key.split(".").at(-1)}${vars ? JSON.stringify(vars) : ""}`,
  }),
}))

import { ErrorPatternsPanel } from "@/components/error-patterns-panel"

describe("ErrorPatternsPanel", () => {
  it("shows the top three translated tags for each language", () => {
    render(
      <ErrorPatternsPanel
        loading={false}
        failed={false}
        patterns={{
          window_entries: 12,
          languages: [
            {
              language: "es",
              top_tags: [
                { error_type: "gender_agreement", count: 5 },
                { error_type: "ser_estar", count: 3 },
                { error_type: "article", count: 2 },
                { error_type: "other", count: 1 },
              ],
            },
            { language: "fr", top_tags: [{ error_type: "preposition", count: 2 }] },
          ],
        }}
      />,
    )

    expect(screen.getByText("errorPatternsTitle")).toBeInTheDocument()
    expect(screen.getByText("errorPatternsDesc{\"count\":12}")).toBeInTheDocument()
    expect(screen.getByText("errorTag_gender_agreement")).toBeInTheDocument()
    expect(screen.getByText("errorTag_ser_estar")).toBeInTheDocument()
    expect(screen.getByText("errorTag_article")).toBeInTheDocument()
    expect(screen.queryByText("other")).not.toBeInTheDocument()
    expect(screen.getByText("🇪🇸 Spanish")).toBeInTheDocument()
    expect(screen.getByText("🇫🇷 French")).toBeInTheDocument()
  })

  it("shows the empty state when no tagged entries are available", () => {
    render(<ErrorPatternsPanel loading={false} failed={false} patterns={{ window_entries: 0, languages: [] }} />)

    expect(screen.getByText("errorPatternsEmpty")).toBeInTheDocument()
  })

  it("keeps loading and request failure separate from the empty state", () => {
    const { rerender } = render(<ErrorPatternsPanel loading failed={false} patterns={null} />)
    expect(screen.getByText("calculatingProgress")).toBeInTheDocument()
    expect(screen.queryByText("errorPatternsEmpty")).not.toBeInTheDocument()

    rerender(<ErrorPatternsPanel loading={false} failed patterns={null} />)
    expect(screen.getByText("errorPatternsLoadError")).toBeInTheDocument()
    expect(screen.queryByText("errorPatternsEmpty")).not.toBeInTheDocument()
  })
})
