import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const api = vi.hoisted(() => ({
  getMiniLessonOffer: vi.fn(),
  getMiniLessonDrill: vi.fn(),
  markMiniLessonSeen: vi.fn(),
  snoozeMiniLesson: vi.fn(),
}))
vi.mock("@/lib/api", () => api)
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      Object.entries(options || {}).reduce((text, [name, value]) => text.replace(`{${name}}`, String(value)), key),
  }),
}))

import { MiniLessonOffer } from "@/components/mini-lesson-offer"

const OFFER = {
  l2: "es",
  tag: "ser_estar",
  count: 2,
  lesson: {
    id: "ser-estar-identity",
    tag: "ser_estar",
    title: "Use ser for identity and origin",
    level: "A1-B1",
    explanation: "Use ser for identity and origin.",
    examples: [{ es: "Soy estudiante.", en: "I am a student." }],
    trap_note: "A current feeling usually uses estar.",
  },
}

beforeEach(() => {
  vi.clearAllMocks()
  api.getMiniLessonOffer.mockResolvedValue(OFFER)
  api.getMiniLessonDrill.mockResolvedValue([
    { before: "Soy ", answer: "estudiante", after: "." },
    { before: "Ella es ", answer: "médica", after: "." },
    { before: "Somos de ", answer: "Madrid", after: "." },
  ])
  api.markMiniLessonSeen.mockResolvedValue(undefined)
  api.snoozeMiniLesson.mockResolvedValue(undefined)
})

describe("MiniLessonOffer", () => {
  it("offers a lesson inline, opens its sheet and marks it seen", async () => {
    render(<MiniLessonOffer entryId="entry-1" language="es" analysisStatus="ok" />)

    expect(await screen.findByTestId("mini-lesson-offer")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "feedback.miniLessonOpen" }))

    expect(await screen.findByRole("heading", { name: OFFER.lesson.title })).toBeInTheDocument()
    expect(screen.getByText("Soy estudiante.")).toBeInTheDocument()
    expect(api.markMiniLessonSeen).toHaveBeenCalledWith("es", "ser_estar")
  })

  it("shows the snoozed state after Not now", async () => {
    render(<MiniLessonOffer entryId="entry-1" language="es" analysisStatus="ok" />)
    fireEvent.click(await screen.findByRole("button", { name: "feedback.miniLessonNotNow" }))

    expect(await screen.findByTestId("mini-lesson-snoozed")).toHaveTextContent("feedback.miniLessonSnoozed")
    expect(api.snoozeMiniLesson).toHaveBeenCalledWith("es", "ser_estar")
  })

  it("checks the three personal clozes in the browser", async () => {
    render(<MiniLessonOffer entryId="entry-1" language="es" analysisStatus="ok" />)
    fireEvent.click(await screen.findByRole("button", { name: "feedback.miniLessonOpen" }))
    fireEvent.click(await screen.findByRole("button", { name: "feedback.miniLessonPractice" }))
    expect(await screen.findByTestId("mini-lesson-drill-3")).toBeInTheDocument()

    const firstInput = screen.getAllByLabelText("feedback.miniLessonInput")[0]
    fireEvent.change(firstInput, { target: { value: "estudiante" } })
    fireEvent.click(screen.getAllByRole("button", { name: "feedback.miniLessonCheck" })[0])

    expect(await screen.findByText("feedback.miniLessonCorrect")).toBeInTheDocument()
    await waitFor(() => expect(api.getMiniLessonDrill).toHaveBeenCalledWith("es", "ser_estar", "entry-1"))
  })

  it("does not request lesson offers for mock feedback or another language", async () => {
    const { rerender } = render(<MiniLessonOffer entryId="entry-1" language="es" analysisStatus="mock" />)
    expect(api.getMiniLessonOffer).not.toHaveBeenCalled()

    rerender(<MiniLessonOffer entryId="entry-2" language="fr" analysisStatus="ok" />)
    await waitFor(() => expect(api.getMiniLessonOffer).not.toHaveBeenCalled())
  })
})
