import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n/i18n"

const api = vi.hoisted(() => ({
  getCurrentPolicy: vi.fn(),
  getPrompts: vi.fn(),
  postSupportEvent: vi.fn(),
}))
vi.mock("@/lib/api", () => api)
vi.mock("@/components/review-due-card", () => ({
  ReviewDueCard: () => <div data-testid="today-review-due">Reviews</div>,
}))
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      const [ns, name] = key.split(".", 2)
      return i18n.t(name, { lng: "en", ...options, ns }) as string
    },
  }),
}))

import { TodayCard } from "@/components/today-card"

beforeEach(() => {
  vi.clearAllMocks()
  api.getCurrentPolicy.mockResolvedValue({ l2: "es", proficiency: "A1" })
  api.getPrompts.mockResolvedValue({
    prompts: [{
      id: "es-a1-01",
      title: "A favorite food",
      prompt: "Write about a food you like.",
      one_sentence_frame: "Me gusta ____.",
    }],
  })
  api.postSupportEvent.mockResolvedValue(undefined)
})

describe("Today card", () => {
  it("loads a level-sized prompt after due reviews and starts one-sentence writing", async () => {
    render(<TodayCard language="es" />)

    const card = await screen.findByTestId("today-card")
    expect(within(card).getByTestId("today-review-due")).toBeInTheDocument()
    expect(await within(card).findByText("A favorite food")).toBeInTheDocument()
    expect(api.getCurrentPolicy).toHaveBeenCalledWith("es")
    expect(api.getPrompts).toHaveBeenCalledWith({ l2: "es", level: "A1" })

    const link = within(card).getByRole("link", { name: "Write one sentence" })
    const href = new URL(link.getAttribute("href") || "", "http://localhost")
    expect(href.pathname).toBe("/entries/new")
    expect(href.searchParams.get("today_prompt_id")).toBe("es-a1-01")
    expect(href.searchParams.get("today_entry_mode")).toBe("one_sentence")
    expect(href.searchParams.get("today_prompt_frame")).toBe("Me gusta ____.")

    link.addEventListener("click", (event) => event.preventDefault(), { once: true })
    fireEvent.click(link)
    await waitFor(() => expect(api.postSupportEvent).toHaveBeenCalledWith({
      kind: "prompt_selected",
      l2: "es",
      prompt_id: "es-a1-01",
    }))
  })

  it("keeps free writing available when the prompt bank is unavailable", async () => {
    api.getPrompts.mockRejectedValue(new Error("offline"))
    render(<TodayCard language="es" />)
    expect(await screen.findByText("No prompt is available right now. You can still write freely.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Start New Entry" })).toHaveAttribute("href", "/entries/new")
  })
})
