"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { CheckCircle, AlertCircle, ChevronDown, ChevronUp, Check } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface GrammarFeedbackItem {
  id: string
  original: string
  suggested: string
  explanation: string
  type: "positive" | "suggestion" | "error"
  dismissed: boolean
}

interface GrammarFeedbackProps {
  feedback: GrammarFeedbackItem[]
  onDismiss: (id: string) => void
}

export function GrammarFeedback({ feedback, onDismiss }: GrammarFeedbackProps) {
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({})

  const toggleItem = (id: string) => {
    setExpandedItems((prev) => ({
      ...prev,
      [id]: !prev[id],
    }))
  }

  const activeFeedback = feedback.filter((item) => !item.dismissed)
  const dismissedFeedback = feedback.filter((item) => item.dismissed)

  const getFeedbackTypeIcon = (type: string) => {
    switch (type) {
      case "positive":
        return <CheckCircle className="h-5 w-5 text-fun-green" />
      case "suggestion":
        return <AlertCircle className="h-5 w-5 text-fun-yellow" />
      case "error":
        return <AlertCircle className="h-5 w-5 text-fun-pink" />
      default:
        return <AlertCircle className="h-5 w-5 text-fun-yellow" />
    }
  }

  const getFeedbackTypeColor = (type: string) => {
    switch (type) {
      case "positive":
        return "bg-fun-green/10 border-fun-green/20"
      case "suggestion":
        return "bg-fun-yellow/10 border-fun-yellow/20"
      case "error":
        return "bg-fun-pink/10 border-fun-pink/20"
      default:
        return "bg-fun-yellow/10 border-fun-yellow/20"
    }
  }

  return (
    <Card className="border-fun-green/20 shadow-fun rounded-3xl overflow-hidden">
      <CardHeader className="bg-gradient-to-r from-fun-green/10 to-fun-teal/10 pb-4">
        <CardTitle className="text-2xl flex items-center">
          <span className="fun-heading">Grammar Suggestions</span> ✏️
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        {activeFeedback.length === 0 && dismissedFeedback.length === 0 ? (
          <div className="text-center py-8">
            <CheckCircle className="h-12 w-12 text-fun-green mx-auto mb-4" />
            <h3 className="text-xl font-medium mb-2">Perfect Grammar!</h3>
            <p className="text-muted-foreground">No grammar issues were found in your writing. Great job!</p>
          </div>
        ) : (
          <div className="space-y-4">
            {activeFeedback.map((item) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                className={`rounded-2xl border-2 overflow-hidden ${getFeedbackTypeColor(item.type)}`}
              >
                <div
                  className="p-4 flex justify-between items-start cursor-pointer"
                  onClick={() => toggleItem(item.id)}
                >
                  <div className="flex items-start gap-3">
                    {getFeedbackTypeIcon(item.type)}
                    <div>
                      <div className="font-medium">
                        {item.type === "positive" ? (
                          <span className="text-fun-green">Well done!</span>
                        ) : item.type === "suggestion" ? (
                          <span className="text-fun-yellow">Suggestion</span>
                        ) : (
                          <span className="text-fun-pink">Correction needed</span>
                        )}
                      </div>
                      <div className="text-sm font-serif mt-1">{item.original}</div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="rounded-full h-8 w-8 p-0"
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleItem(item.id)
                    }}
                  >
                    {expandedItems[item.id] ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                  </Button>
                </div>

                <AnimatePresence>
                  {expandedItems[item.id] && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <div className="px-4 pb-4 pt-0">
                        <div className="mt-2 space-y-3">
                          {item.type !== "positive" && (
                            <div>
                              <div className="text-sm text-muted-foreground mb-1">Suggested:</div>
                              <div className="text-sm font-serif text-fun-green">{item.suggested}</div>
                            </div>
                          )}

                          <div>
                            <div className="text-sm text-muted-foreground mb-1">Explanation:</div>
                            <div className="text-sm">{item.explanation}</div>
                          </div>

                          <div className="pt-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation()
                                onDismiss(item.id)
                              }}
                              className="rounded-full border-fun-green/30 hover:bg-fun-green/10 text-fun-green"
                            >
                              <Check className="mr-1 h-4 w-4" />
                              Understood
                            </Button>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}

            {dismissedFeedback.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-medium text-muted-foreground mb-3">Dismissed Feedback</h3>
                <div className="space-y-2">
                  {dismissedFeedback.map((item) => (
                    <div
                      key={item.id}
                      className="p-3 rounded-xl bg-muted/30 text-sm text-muted-foreground flex items-center"
                    >
                      {getFeedbackTypeIcon(item.type)}
                      <span className="ml-2 line-clamp-1">{item.original}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
