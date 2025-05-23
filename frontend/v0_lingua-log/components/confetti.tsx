"use client"

import { useEffect, useState } from "react"
import type { JSX } from "react"

interface ConfettiProps {
  count?: number
  duration?: number
}

export function Confetti({ count = 100, duration = 5 }: ConfettiProps) {
  const [confetti, setConfetti] = useState<JSX.Element[]>([])

  useEffect(() => {
    const colors = [
      "var(--fun-green)",
      "var(--fun-blue)",
      "var(--fun-purple)",
      "var(--fun-pink)",
      "var(--fun-yellow)",
      "var(--fun-orange)",
    ]

    const newConfetti = []

    for (let i = 0; i < count; i++) {
      const left = Math.random() * 100
      const color = colors[Math.floor(Math.random() * colors.length)]
      const delay = Math.random() * 3
      const size = Math.random() * 10 + 5
      const duration = Math.random() * 3 + 2

      newConfetti.push(
        <div
          key={i}
          className="confetti"
          style={{
            left: `${left}%`,
            width: `${size}px`,
            height: `${size}px`,
            animationDelay: `${delay}s`,
            animationDuration: `${duration}s`,
            backgroundColor: color,
            borderRadius: Math.random() > 0.5 ? "50%" : "0",
            transform: `rotate(${Math.random() * 360}deg)`,
          }}
        />,
      )
    }

    setConfetti(newConfetti)

    const timer = setTimeout(() => {
      setConfetti([])
    }, duration * 1000)

    return () => clearTimeout(timer)
  }, [count, duration])

  return <div className="fixed inset-0 pointer-events-none z-50">{confetti}</div>
}
