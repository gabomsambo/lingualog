import { render, screen, within } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

const locale = vi.hoisted(() => ({
  t: (key: string) => ({
    "feedback.focusTodayTitle": "Today's grammar focus",
    "feedback.focusUse_used_correctly": "Used well",
    "feedback.focusUse_not_used": "Not used",
    "feedback.focusUseNotUsed": "This focus does not appear in the entry.",
  }[key] || key),
}))
vi.mock("@/i18n/LocaleProvider", () => ({ useLocale: () => ({ t: locale.t }) }))

import { FocusUseRow } from "@/components/focus-use-row"

describe("FocusUseRow", () => {
  it("shows the same-call grammar focus verdict and its evidence", () => {
    render(<FocusUseRow uses={[
      { focus: "estar + gerundio", status: "used_correctly", evidence: "Estoy estudiando." },
    ]} language="es" />)

    const row = screen.getByTestId("focus-use-item")
    expect(screen.getByTestId("focus-use")).toHaveAccessibleName("Today's grammar focus")
    expect(row).toHaveAttribute("data-status", "used_correctly")
    expect(within(row).getByText("estar + gerundio")).toBeInTheDocument()
    expect(within(row).getByText("Used well")).toBeInTheDocument()
    expect(within(row).getByText("Estoy estudiando.")).toBeInTheDocument()
  })

  it("explains when the learner did not use the focus", () => {
    render(<FocusUseRow uses={[{ focus: "preterite", status: "not_used" }]} language="es" />)
    expect(screen.getByTestId("focus-use-item")).toHaveTextContent("This focus does not appear in the entry.")
  })
})
