import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n/i18n"

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {},
  getEntryById: vi.fn(),
  postLogEntry: vi.fn(),
  getUserSettings: vi.fn(),
}))
vi.mock("@/lib/api", () => api)

vi.mock("@/components/ui/use-toast", () => ({ useToast: () => ({ toast: vi.fn() }) }))

vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    uiLang: "en",
    t: (key: string, options?: Record<string, unknown>) => {
      const [ns, name] = key.split(".", 2)
      return i18n.t(name, { lng: "en", ...options, ns }) as string
    },
  }),
}))

import { JournalEditor } from "@/components/journal-editor"

const frenchLearner = {
  native_lang: "en",
  default_target_lang: "fr",
  immersion_level: 1,
  language_profiles: [{ l2: "fr", immersion_level: 2, proficiency: "B1", active: true }],
}

function fillEntry() {
  fireEvent.change(screen.getByPlaceholderText("Entry Title"), { target: { value: "Samedi" } })
  fireEvent.change(screen.getByPlaceholderText(/Write your thoughts/), { target: { value: "Je suis allé au marché." } })
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe("JournalEditor when settings fail to load", () => {
  it("does not fall back to Spanish; it blocks submit and offers a retry", async () => {
    api.getUserSettings.mockRejectedValueOnce(new Error("500")).mockResolvedValueOnce(frenchLearner)
    render(<JournalEditor />)

    const alert = await screen.findByTestId("settings-load-error")
    expect(screen.queryByRole("radio")).toBeNull()
    fillEntry()
    const submit = screen.getByRole("button", { name: /submit/i })
    expect(submit).toBeDisabled()
    fireEvent.click(submit)
    expect(api.postLogEntry).not.toHaveBeenCalled()

    fireEvent.click(within(alert).getByRole("button"))
    await waitFor(() => expect(screen.queryByTestId("settings-load-error")).toBeNull())
    expect(screen.getAllByRole("radio").map((radio) => radio.getAttribute("aria-checked"))).toEqual(["true"])
    expect(screen.getByRole("radio")).toHaveTextContent(/French|Français/)
    expect(screen.getByRole("button", { name: /submit/i })).toBeEnabled()
  })
})
