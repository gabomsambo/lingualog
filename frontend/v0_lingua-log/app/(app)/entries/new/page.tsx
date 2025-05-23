"use client"

import { motion } from "framer-motion"

import { JournalEditor } from "@/components/journal-editor"

export default function NewEntryPage() {
  return (
    <div className="container max-w-4xl mx-auto py-8 px-4">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-8 text-center"
      >
        <h1 className="text-4xl md:text-5xl font-bold mb-3">
          <span className="fun-heading">New Journal Entry ✍️</span>
        </h1>
        <p className="text-xl text-muted-foreground">
          Reflect on your day, practice your skills, and grow your language journey!
        </p>
      </motion.div>

      {/* Journal Editor */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <JournalEditor />
      </motion.div>

      {/* Footer */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.3 }}
        className="mt-8 text-center"
      >
        <p className="text-sm text-muted-foreground">Built with love using Next.js, Supabase, and AI magic ✨</p>
      </motion.div>
    </div>
  )
}
