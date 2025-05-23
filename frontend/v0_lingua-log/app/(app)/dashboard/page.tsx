"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { BookOpen, Edit, Languages, Trophy, Star } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { LoadingSpinner } from "@/components/loading-spinner"
import { Confetti } from "@/components/confetti"
import { getUserProfile, getUserEntries, getUserStats, UserEntry, UserStats } from "@/lib/user-service"

// Badge variants for languages
const languageBadgeVariants: Record<string, "pink" | "blue" | "purple" | "green" | "yellow" | "default" | "outline"> = {
  Spanish: "pink",
  French: "blue",
  German: "purple",
  Japanese: "green",
  English: "yellow",
  Other: "default",
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)
  const [entries, setEntries] = useState<UserEntry[]>([])
  const [stats, setStats] = useState<UserStats | null>(null)
  const [showConfetti, setShowConfetti] = useState(false)
  const [userName, setUserName] = useState("Friend")
  const { toast } = useToast()

  // Counter animation values
  const [countedWordCount, setCountedWordCount] = useState(0)
  const [countedStreak, setCountedStreak] = useState(0)

  useEffect(() => {
    // Load user data
    async function loadUserData() {
      try {
        // Get user profile
        const profile = await getUserProfile();
        if (profile) {
          setUserName(profile.username || profile.email.split('@')[0]);
        }

        // Get user entries
        const userEntries = await getUserEntries();
        setEntries(userEntries);

        // Get user stats
        const userStats = await getUserStats();
        if (userStats) {
          setStats(userStats);
        }

        setLoading(false);
        setShowConfetti(true);

        // Welcome toast
        toast({
          title: "Welcome back! ✨",
          description: "Ready to continue your language journey?",
          variant: "fun",
        });
      } catch (error) {
        console.error("Error loading user data:", error);
        setLoading(false);
        toast({
          title: "Error loading data",
          description: "Please try refreshing the page",
          variant: "destructive",
        });
      }
    }

    loadUserData();
  }, [toast])

  // Counter animation effect
  useEffect(() => {
    if (!stats || loading) return

    let wordInterval: NodeJS.Timeout
    let streakInterval: NodeJS.Timeout

    const wordStep = Math.ceil(stats.wordCount / 30)
    const streakStep = Math.ceil(stats.streak / 20)

    wordInterval = setInterval(() => {
      setCountedWordCount((prev) => {
        if (prev + wordStep >= stats.wordCount) {
          clearInterval(wordInterval)
          return stats.wordCount
        }
        return prev + wordStep
      })
    }, 50)

    streakInterval = setInterval(() => {
      setCountedStreak((prev) => {
        if (prev + streakStep >= stats.streak) {
          clearInterval(streakInterval)
          return stats.streak
        }
        return prev + streakStep
      })
    }, 100)

    return () => {
      clearInterval(wordInterval)
      clearInterval(streakInterval)
    }
  }, [stats, loading])

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
    }).format(date)
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh]">
        <LoadingSpinner text="Loading your journal..." />
      </div>
    )
  }

  return (
    <>
      {showConfetti && <Confetti />}

      {/* Hero Section */}
      <section className="mb-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6"
        >
          <div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-2">
              <span className="fun-heading">Hi {userName}! ✨</span>
            </h1>
            <p className="text-xl text-muted-foreground">
              You're on a <span className="font-bold text-fun-purple">{stats?.streak}-day</span> writing streak! 🔥
            </p>
          </div>

          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
            <Button
              size="lg"
              className="bg-gradient-to-r from-fun-mint to-fun-pink text-white hover:opacity-90 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 text-lg h-14 px-8"
              asChild
            >
              <Link href="/entries/new">
                <Edit className="mr-2 h-5 w-5" /> Start New Entry
              </Link>
            </Button>
          </motion.div>
        </motion.div>
      </section>

      {/* Stats Section */}
      <section className="mb-10">
        <h2 className="text-2xl font-bold mb-6">
          <span className="fun-heading">Your Progress 📊</span>
        </h2>

        <div className="grid gap-6 md:grid-cols-3">
          {/* Words Written Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <Card className="border-fun-mint/30 hover:border-fun-mint/50 transition-colors duration-300 rounded-3xl shadow-lg hover:shadow-xl overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-fun-mint to-fun-blue"></div>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base font-medium">Words Written</CardTitle>
                <BookOpen className="h-5 w-5 text-fun-mint" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{countedWordCount}</div>
                <div className="flex items-center text-sm text-muted-foreground mt-1">
                  <div className="flex items-center text-fun-green">
                    <svg
                      className="w-4 h-4 mr-1"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 10l7-7m0 0l7 7m-7-7v18"
                      />
                    </svg>
                    {stats?.weeklyIncrease} from last week
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Languages Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Card className="border-fun-blue/30 hover:border-fun-blue/50 transition-colors duration-300 rounded-3xl shadow-lg hover:shadow-xl overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-fun-blue to-fun-purple"></div>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base font-medium">Languages Practiced</CardTitle>
                <Languages className="h-5 w-5 text-fun-blue" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats?.languages.length}</div>
                <div className="flex flex-wrap gap-2 mt-2">
                  {stats?.languageEmojis.map((emoji, i) => (
                    <div key={i} className="text-2xl animate-bounce-slight" style={{ animationDelay: `${i * 0.1}s` }}>
                      {emoji}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Streak Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Card className="border-fun-purple/30 hover:border-fun-purple/50 transition-colors duration-300 rounded-3xl shadow-lg hover:shadow-xl overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-fun-purple to-fun-pink"></div>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base font-medium">Current Streak</CardTitle>
                <Trophy className="h-5 w-5 text-fun-purple" />
              </CardHeader>
              <CardContent>
                <div className="flex items-center">
                  <div className="streak-counter bg-white p-1 rounded-full mr-2">
                    <div className="bg-white rounded-full h-8 w-8 flex items-center justify-center text-2xl font-bold">
                      {countedStreak}
                    </div>
                  </div>
                  <span className="text-2xl font-bold">days</span>
                </div>
                <p className="text-sm text-muted-foreground mt-1 flex items-center">
                  <Star className="h-4 w-4 text-fun-yellow mr-1" />
                  You're on fire! Keep going! 🔥
                </p>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Recent Entries Section */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">
            <span className="fun-heading">Recent Entries 📝</span>
          </h2>
          <Button
            variant="outline"
            size="sm"
            asChild
            className="rounded-full border-fun-purple/30 hover:border-fun-purple/50"
          >
            <Link href="/entries">View all</Link>
          </Button>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {entries.length > 0 ? (
            entries.map((entry, index) => (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 * index }}
              >
                <Card className="fun-card group border-fun-purple/20 hover:border-fun-purple/40 h-full flex flex-col">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <Badge variant={languageBadgeVariants[entry.language] || "default"} className="mb-2">
                        {entry.languageEmoji} {entry.language}
                      </Badge>
                      <span className="text-sm text-muted-foreground">{formatDate(entry.date)}</span>
                    </div>
                    <CardTitle className="group-hover:text-fun-purple transition-colors duration-300 text-xl">
                      {entry.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex-grow">
                    <p className="line-clamp-3 text-base text-muted-foreground">{entry.excerpt}</p>
                  </CardContent>
                  <CardFooter className="pt-2">
                    <Button
                      variant="outline"
                      className="w-full rounded-full border-fun-purple/30 hover:border-fun-purple/50 hover:bg-fun-purple/5"
                      asChild
                    >
                      <Link href={`/entries/${entry.id}`}>Read Entry</Link>
                    </Button>
                  </CardFooter>
                </Card>
              </motion.div>
            ))
          ) : (
            <div className="col-span-3 text-center py-10">
              <p className="text-muted-foreground mb-4">You haven't created any journal entries yet.</p>
              <Button asChild>
                <Link href="/entries/new">Create Your First Entry</Link>
              </Button>
            </div>
          )}
        </div>
      </section>
    </>
  )
}
