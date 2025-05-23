"use client"

import { useState, useEffect } from "react"
import { Languages, TrendingUp, Award, Sparkles, Trophy } from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { WritingAnimation } from "@/components/writing-animation"

// Badge variants for languages
const languageBadgeVariants: Record<string, string> = {
  Spanish: "pink",
  French: "blue",
  German: "purple",
  Japanese: "green",
  English: "yellow",
  Other: "default",
}

// Mock stats data
const mockStats = {
  wordCounts: [
    { date: "2023-04-14", count: 120 },
    { date: "2023-04-15", count: 150 },
    { date: "2023-04-16", count: 200 },
    { date: "2023-04-17", count: 180 },
    { date: "2023-04-18", count: 250 },
    { date: "2023-04-19", count: 220 },
    { date: "2023-04-20", count: 300 },
  ],
  languageBreakdown: [
    { language: "Spanish", percentage: 45, count: 870 },
    { language: "French", percentage: 30, count: 580 },
    { language: "German", percentage: 15, count: 290 },
    { language: "Japanese", percentage: 10, count: 193 },
  ],
  streak: {
    current: 7,
    longest: 14,
    total: 1933,
  },
}

export default function StatsPage() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<typeof mockStats | null>(null)

  useEffect(() => {
    // Simulate API call
    const timer = setTimeout(() => {
      setStats(mockStats)
      setLoading(false)
    }, 1500)

    return () => clearTimeout(timer)
  }, [])

  // Calculate max word count for scaling the chart
  const maxWordCount = stats ? Math.max(...stats.wordCounts.map((day) => day.count)) : 0
  const chartHeight = 200

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">
          <span className="fun-heading">Your Learning Stats 📊</span>
        </h2>
        <p className="text-muted-foreground mt-2 text-lg">Track your language learning progress over time</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {loading ? (
          <>
            {[...Array(3)].map((_, i) => (
              <Card key={i} className="fun-card border-fun-purple/20">
                <CardHeader className="pb-2">
                  <Skeleton className="h-6 w-40 mb-1" />
                  <Skeleton className="h-5 w-24" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-[200px] w-full" />
                </CardContent>
              </Card>
            ))}
          </>
        ) : stats ? (
          <>
            {/* Word Count Chart */}
            <Card className="fun-card border-fun-green/30 hover:border-fun-green/50 transition-colors duration-300 shadow-fun hover:shadow-fun-lg">
              <CardHeader>
                <CardTitle className="flex items-center text-xl">
                  <TrendingUp className="mr-2 h-5 w-5 text-fun-green" />
                  Word Count
                </CardTitle>
                <CardDescription className="text-base">Words written over the last 7 days</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[200px] w-full">
                  <div className="flex h-full items-end gap-2">
                    {stats.wordCounts.map((day, i) => {
                      const height = (day.count / maxWordCount) * chartHeight
                      const date = new Date(day.date)
                      const dayName = date.toLocaleDateString("en-US", { weekday: "short" })

                      return (
                        <div key={i} className="flex flex-col items-center flex-1 group">
                          <div
                            className="w-full rounded-t-xl transition-all duration-300 group-hover:scale-105"
                            style={{
                              height: `${height}px`,
                              background: `linear-gradient(to top, hsl(var(--fun-green)), hsl(var(--fun-blue)))`,
                            }}
                          />
                          <div className="mt-2 text-sm text-muted-foreground">{dayName}</div>
                          <div className="text-sm font-medium mt-1">{day.count}</div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Language Breakdown */}
            <Card className="fun-card border-fun-blue/30 hover:border-fun-blue/50 transition-colors duration-300 shadow-fun hover:shadow-fun-lg">
              <CardHeader>
                <CardTitle className="flex items-center text-xl">
                  <Languages className="mr-2 h-5 w-5 text-fun-blue" />
                  Languages
                </CardTitle>
                <CardDescription className="text-base">Breakdown of languages practiced</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-5">
                  {stats.languageBreakdown.map((lang) => (
                    <div key={lang.language} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <Badge variant={languageBadgeVariants[lang.language] || "default"} className="mr-2">
                            {lang.language}
                          </Badge>
                          <span className="text-base font-medium">{lang.count} words</span>
                        </div>
                        <span className="text-base text-muted-foreground">{lang.percentage}%</span>
                      </div>
                      <div className="h-3 w-full rounded-full bg-fun-blue/10">
                        <div
                          className="h-3 rounded-full transition-all duration-500"
                          style={{
                            width: `${lang.percentage}%`,
                            background:
                              lang.language === "Spanish"
                                ? "linear-gradient(to right, hsl(var(--fun-pink)), hsl(var(--fun-purple)))"
                                : lang.language === "French"
                                  ? "linear-gradient(to right, hsl(var(--fun-blue)), hsl(var(--fun-teal)))"
                                  : lang.language === "German"
                                    ? "linear-gradient(to right, hsl(var(--fun-purple)), hsl(var(--fun-blue)))"
                                    : lang.language === "Japanese"
                                      ? "linear-gradient(to right, hsl(var(--fun-green)), hsl(var(--fun-teal)))"
                                      : "linear-gradient(to right, hsl(var(--fun-yellow)), hsl(var(--fun-orange)))",
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Streak Stats */}
            <Card className="fun-card border-fun-purple/30 hover:border-fun-purple/50 transition-colors duration-300 shadow-fun hover:shadow-fun-lg">
              <CardHeader>
                <CardTitle className="flex items-center text-xl">
                  <Trophy className="mr-2 h-5 w-5 text-fun-purple" />
                  Writing Streak
                </CardTitle>
                <CardDescription className="text-base">Your consistent writing progress</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col items-center justify-center h-[200px] text-center space-y-6">
                  <div className="relative">
                    <div className="streak-counter p-2 rounded-full">
                      <div className="bg-white rounded-full h-16 w-16 flex items-center justify-center text-4xl font-bold">
                        {stats.streak.current}
                      </div>
                    </div>
                    <div className="text-base text-muted-foreground mt-2">days in a row</div>
                    <Sparkles className="absolute -top-4 -right-4 h-6 w-6 text-fun-yellow animate-pulse-gentle" />
                  </div>

                  {stats.streak.current > 5 && (
                    <div className="bg-gradient-to-r from-fun-purple/20 to-fun-pink/20 text-primary px-6 py-3 rounded-full font-medium border-2 border-fun-purple/30 shadow-md animate-float">
                      <Award className="inline-block mr-2 h-5 w-5 text-fun-purple" />
                      You're on fire! Keep going! 🔥
                    </div>
                  )}

                  <div className="grid grid-cols-2 w-full gap-4 text-base">
                    <div className="bg-fun-blue/10 rounded-2xl p-4 text-center border-2 border-fun-blue/20">
                      <div className="font-bold text-xl">{stats.streak.longest}</div>
                      <div className="text-muted-foreground">Longest streak</div>
                    </div>
                    <div className="bg-fun-pink/10 rounded-2xl p-4 text-center border-2 border-fun-pink/20">
                      <div className="font-bold text-xl">{stats.streak.total}</div>
                      <div className="text-muted-foreground">Total words</div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>

      {loading && (
        <div className="flex justify-center py-8">
          <WritingAnimation text="Calculating your progress" />
        </div>
      )}
    </div>
  )
}
