"use client"

import { motion } from "framer-motion"

interface LoadingSpinnerProps {
  text?: string
}

export function LoadingSpinner({ text = "Loading..." }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center space-y-4">
      <div className="relative h-16 w-16">
        <motion.div
          className="absolute inset-0 rounded-full border-4 border-t-fun-mint border-r-fun-blue border-b-fun-purple border-l-fun-pink"
          animate={{ rotate: 360 }}
          transition={{ duration: 1.5, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
        />
      </div>
      <motion.p
        className="text-lg font-medium text-fun-purple"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        {text}
      </motion.p>
    </div>
  )
}
