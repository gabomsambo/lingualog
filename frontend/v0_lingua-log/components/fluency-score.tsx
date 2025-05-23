"use client"

import { motion } from "framer-motion"
import { TrendingUp, Award, BookOpen, Sparkles } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"

interface FluencyScoreProps {
  score: {
    overall: number
    level: string
    grammar: number
    vocabulary: number
    complexity: number
    improvement: string
  }
}

export function FluencyScore({ score }: FluencyScoreProps) {
  // Function to determine level badge color
  const getLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case "beginner":
        return "bg-fun-blue text-white"
      case "intermediate":
        return "bg-fun-purple text-white"
      case "advanced":
        return "bg-fun-pink text-white"
      case "fluent":
        return "bg-fun-green text-white"
      default:
        return "bg-fun-blue text-white"
    }
  }

  // Animation variants for the score circle
  const circleVariants = {
    hidden: { scale: 0.8, opacity: 0 },
    visible: {
      scale: 1,
      opacity: 1,
      transition: {
        type: "spring",
        stiffness: 200,
        damping: 15,
      },
    },
  }

  return (
    <Card className="border-fun-purple/20 shadow-fun rounded-3xl overflow-hidden h-full">
      <CardHeader className="bg-gradient-to-r from-fun-purple/10 to-fun-pink/10 pb-4">
        <CardTitle className="text-2xl flex items-center">
          <span className="fun-heading">Fluency Score</span> 📊
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        <div className="flex flex-col items-center mb-6">
          <motion.div className="relative mb-4" initial="hidden" animate="visible" variants={circleVariants}>
            <div className="w-32 h-32 rounded-full bg-gradient-to-br from-fun-purple/20 to-fun-pink/20 flex items-center justify-center">
              <div className="w-28 h-28 rounded-full bg-white flex items-center justify-center">
                <div className="text-4xl font-bold text-fun-purple">{score.overall}</div>
              </div>
            </div>
            <div className="absolute -top-2 -right-2 bg-fun-yellow rounded-full p-1">
              <Award className="h-5 w-5 text-white" />
            </div>
          </motion.div>

          <div className={`px-4 py-1 rounded-full text-sm font-medium ${getLevelColor(score.level)}`}>
            {score.level}
          </div>

          <p className="text-center text-muted-foreground mt-3 text-sm">{score.improvement}</p>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <div className="flex items-center text-sm font-medium">
                <BookOpen className="h-4 w-4 mr-2 text-fun-blue" />
                Grammar
              </div>
              <span className="text-sm">{score.grammar}%</span>
            </div>
            <Progress value={score.grammar} className="h-2" indicatorClassName="bg-fun-blue" />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <div className="flex items-center text-sm font-medium">
                <Sparkles className="h-4 w-4 mr-2 text-fun-purple" />
                Vocabulary
              </div>
              <span className="text-sm">{score.vocabulary}%</span>
            </div>
            <Progress value={score.vocabulary} className="h-2" indicatorClassName="bg-fun-purple" />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <div className="flex items-center text-sm font-medium">
                <TrendingUp className="h-4 w-4 mr-2 text-fun-pink" />
                Complexity
              </div>
              <span className="text-sm">{score.complexity}%</span>
            </div>
            <Progress value={score.complexity} className="h-2" indicatorClassName="bg-fun-pink" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
