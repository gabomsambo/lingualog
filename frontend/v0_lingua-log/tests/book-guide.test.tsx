import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const auth = vi.hoisted(() => ({ getUser: vi.fn() }))
vi.mock("@/lib/auth", () => auth)
vi.mock("@/i18n/LocaleProvider", () => ({
  useLocale: () => ({
    t: (key: string) => key.split(".").at(-1) ?? key,
  }),
}))

import { BookGuide } from "@/components/book-guide"

describe("BookGuide", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    auth.getUser.mockResolvedValue({ id: "user-1" })
  })

  it("shows the three steps to a learner who has not dismissed it", async () => {
    render(<BookGuide />)

    expect(await screen.findByTestId("book-guide")).toHaveTextContent("guideStep1")
    expect(screen.getByTestId("book-guide")).toHaveTextContent("guideStep2")
    expect(screen.getByTestId("book-guide")).toHaveTextContent("guideStep3")
    expect(screen.getByRole("button", { name: "guideDismiss" })).toBeInTheDocument()
  })

  it("hides for good once dismissed, remembered per learner", async () => {
    const { unmount } = render(<BookGuide />)
    fireEvent.click(await screen.findByTestId("book-guide-dismiss"))

    expect(screen.queryByTestId("book-guide")).not.toBeInTheDocument()
    await waitFor(() =>
      expect(localStorage.getItem("lingualog.book-guide-dismissed:user-1")).toBe("1"),
    )

    unmount()
    render(<BookGuide />)
    await waitFor(() => expect(screen.queryByTestId("book-guide")).not.toBeInTheDocument())
  })

  it("does not borrow another learner's dismissal", async () => {
    localStorage.setItem("lingualog.book-guide-dismissed:user-2", "1")
    render(<BookGuide />)

    expect(await screen.findByTestId("book-guide")).toBeInTheDocument()
  })
})
