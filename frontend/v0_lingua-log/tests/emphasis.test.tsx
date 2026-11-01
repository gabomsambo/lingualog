import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { renderEmphasis } from "@/lib/emphasis"

function Note({ text }: { text: string }) {
  return <p data-testid="note">{renderEmphasis(text)}</p>
}

describe("renderEmphasis", () => {
  it("renders *x* as emphasis and **x** as strong, without asterisks", () => {
    const { container } = render(<Note text="Use *gustar* with **me** here." />)
    expect(container.querySelector("em")).toHaveTextContent("gustar")
    expect(container.querySelector("strong")).toHaveTextContent("me")
    expect(screen.getByTestId("note")).toHaveTextContent("Use gustar with me here.")
    expect(screen.getByTestId("note").textContent).not.toContain("*")
  })

  it("never turns text into HTML", () => {
    const { container } = render(<Note text={'<img src=x onerror=alert(1)> *ok* <b>bold</b>'} />)
    expect(container.querySelector("img")).toBeNull()
    expect(container.querySelector("b")).toBeNull()
    expect(container.querySelector("em")).toHaveTextContent("ok")
    expect(screen.getByTestId("note").textContent).toContain("<b>bold</b>")
  })

  it("leaves unmatched asterisks as they are", () => {
    render(<Note text="2 * 3 and a lone * star" />)
    expect(screen.getByTestId("note")).toHaveTextContent("2 * 3 and a lone * star")
  })
})
