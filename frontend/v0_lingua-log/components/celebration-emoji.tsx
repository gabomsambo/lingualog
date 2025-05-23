"use client"

import { useEffect, useState } from "react"
import type { JSX } from "react"

interface CelebrationEmojiProps {
  emoji: string
  count?: number
}

export function CelebrationEmoji({ emoji, count = 3 }: CelebrationEmojiProps) {
  const [emojis, setEmojis] = useState<JSX.Element[]>([])

  useEffect(() => {
    const newEmojis = []

    for (let i = 0; i < count; i++) {
      const left = 40 + Math.random() * 20
      const delay = Math.random() * 0.5
      const size = Math.random() * 10 + 20

      newEmojis.push(
        <div
          key={i}
          className="fixed z-50 pointer-events-none celebrate float-away"
          style={{
            left: `${left}%`,
            top: "50%",
            fontSize: `${size}px`,
            animationDelay: `${delay}s`,
          }}
        >
          {emoji}
        </div>,
      )
    }

    setEmojis(newEmojis)

    const timer = setTimeout(() => {
      setEmojis([])
    }, 3000)

    return () => clearTimeout(timer)
  }, [emoji, count])

  return <>{emojis}</>
}
