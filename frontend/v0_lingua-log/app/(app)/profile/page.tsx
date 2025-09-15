"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Calendar, BookOpen, Target, TrendingUp, Award, Clock, Languages, Flame, Edit2, Camera } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/components/ui/use-toast"
import { NumberTicker } from "@/components/ui/number-ticker"
import { getUserProfile as getApiUserProfile, updateUserProfile, getUserStats, type UserProfile as ApiUserProfile, type UserStats } from "@/lib/api"
import { useLocale } from "@/i18n/LocaleProvider"

// Interface for display purposes (with additional fields not in backend)
interface DisplayUserProfile extends Omit<ApiUserProfile, 'id'> {
  bio?: string;
  username?: string;
}

// This will be moved inside the component to use translations

export default function ProfilePage() {
  const { toast } = useToast()
  const { t } = useLocale()
  const [userProfile, setUserProfile] = useState<DisplayUserProfile | null>(null)
  const [userStats, setUserStats] = useState<UserStats | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [editedProfile, setEditedProfile] = useState<Partial<DisplayUserProfile>>({})
  const [isLoading, setIsLoading] = useState(true)

  // Achievements with translations
  const recentAchievements = [
    { id: 1, title: t('common.firstEntry'), description: t('common.firstEntryDescription'), icon: "📝", date: "2024-01-15" },
    { id: 2, title: t('common.vocabularyMaster'), description: t('common.vocabularyMasterDescription'), icon: "📚", date: "2024-09-10" },
    { id: 3, title: t('common.streakChampion'), description: t('common.streakChampionDescription'), icon: "🔥", date: "2024-09-12" },
    { id: 4, title: t('common.languageExplorer'), description: t('common.languageExplorerDescription'), icon: "🌍", date: "2024-09-01" }
  ]

  useEffect(() => {
    async function loadProfileAndStats() {
      setIsLoading(true)
      try {
        // Load profile and stats in parallel
        const [profileData, statsData] = await Promise.all([
          getApiUserProfile(),
          getUserStats()
        ])
        
        // Transform API profile to display profile
        const displayProfile: DisplayUserProfile = {
          email: profileData.email,
          full_name: profileData.full_name,
          is_active: profileData.is_active,
          is_superuser: profileData.is_superuser,
          created_at: profileData.created_at,
          updated_at: profileData.updated_at,
          username: profileData.full_name || profileData.email.split('@')[0],
          bio: 'Language learner on an exciting journey! 🌟' // Default bio
        }
        
        setUserProfile(displayProfile)
        setUserStats(statsData)
        setEditedProfile(displayProfile)
      } catch (error) {
        console.error('Error loading profile and stats:', error)
        toast({
          title: t('common.errorLoadingProfile'),
          description: "Failed to load your profile data. Please try again.",
          variant: "destructive",
        })
      } finally {
        setIsLoading(false)
      }
    }
    loadProfileAndStats()
  }, [])

  const handleSaveProfile = async () => {
    try {
      // Only send the fields that can be updated
      const updateData = {
        full_name: editedProfile.username, // Use username from the input field
        email: editedProfile.email
      }
      
      // Call the backend API to update the profile
      const updatedProfile = await updateUserProfile(updateData)
      
      // Transform back to display profile
      const displayProfile: DisplayUserProfile = {
        email: updatedProfile.email,
        full_name: updatedProfile.full_name,
        is_active: updatedProfile.is_active,
        is_superuser: updatedProfile.is_superuser,
        created_at: updatedProfile.created_at,
        updated_at: updatedProfile.updated_at,
        username: updatedProfile.full_name || updatedProfile.email.split('@')[0],
        bio: editedProfile.bio || 'Language learner on an exciting journey! 🌟'
      }
      
      setUserProfile(displayProfile)
      setIsEditing(false)
      
      // Broadcast the profile update to update the navbar
      window.dispatchEvent(new CustomEvent('userProfileUpdated', {
        detail: { username: editedProfile.username }
      }))
      
      toast({
        title: "Profile Updated! ✨",
        description: "Your profile has been saved successfully.",
        variant: "fun",
      })
    } catch (error) {
      console.error('Error updating profile:', error)
      toast({
        title: t('common.errorUpdatingProfile'),
        description: "Failed to update your profile. Please try again.",
        variant: "destructive",
      })
    }
  }

  if (isLoading) {
    return (
      <div className="container max-w-6xl mx-auto py-8 px-4">
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-fun-purple mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading your profile...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!userProfile || !userStats) {
    return (
      <div className="container max-w-6xl mx-auto py-8 px-4">
        <div className="text-center">
          <p className="text-muted-foreground">Unable to load profile data.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container max-w-6xl mx-auto py-8 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header Section */}
        <div className="mb-8">
          <div className="relative">
            {/* Background gradient */}
            <div className="absolute inset-0 bg-gradient-to-r from-fun-purple/20 via-fun-blue/20 to-fun-pink/20 rounded-3xl blur-xl"></div>
            
            <Card className="relative border-2 border-fun-purple/20 shadow-2xl backdrop-blur-sm">
              <CardContent className="p-8">
                <div className="flex flex-col md:flex-row items-center gap-6">
                  {/* Avatar Section */}
                  <div className="relative group">
                    <Avatar className="h-32 w-32 ring-4 ring-fun-purple/30 transition-all duration-300 group-hover:ring-fun-purple/70">
                      <AvatarImage src="/mystical-forest-spirit.png" alt={t('common.profileAvatar')} />
                      <AvatarFallback className="bg-gradient-to-br from-fun-blue to-fun-purple text-white text-4xl">
                        {userProfile.email.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="absolute bottom-0 right-0 rounded-full h-10 w-10 p-0 bg-white dark:bg-gray-800 border-2 border-fun-purple/20 hover:border-fun-purple/50"
                    >
                      <Camera className="h-4 w-4" />
                    </Button>
                  </div>

                  {/* User Info */}
                  <div className="flex-1 text-center md:text-left">
                    {isEditing ? (
                      <div className="space-y-4">
                        <div>
                          <Label htmlFor="username">{t('common.displayName')}</Label>
                          <Input
                            id="username"
                            value={editedProfile.username || ""}
                            onChange={(e) => setEditedProfile(prev => ({ ...prev, username: e.target.value }))}
                            className="mt-1"
                          />
                        </div>
                        <div>
                          <Label htmlFor="bio">{t('common.bio')}</Label>
                          <Textarea
                            id="bio"
                            placeholder={t('common.tellUsAboutJourney')}
                            value={(editedProfile as any).bio || ""}
                            onChange={(e) => setEditedProfile(prev => ({ ...prev, bio: e.target.value }))}
                            className="mt-1"
                            rows={3}
                          />
                        </div>
                      </div>
                    ) : (
                      <>
                        <h1 className="text-4xl font-bold bg-gradient-to-r from-fun-purple to-fun-blue bg-clip-text text-transparent">
                          {userProfile.username || userProfile.email.split('@')[0]}
                        </h1>
                        <p className="text-xl text-muted-foreground mb-2">{userProfile.email}</p>
                        <p className="text-lg text-muted-foreground mb-4">
                          {(userProfile as any).bio || t('common.languageLearnerJourney')}
                        </p>
                        <div className="flex flex-wrap gap-2 justify-center md:justify-start">
                          <Badge variant="outline" className="bg-fun-purple/10 text-fun-purple border-fun-purple/20">
                            <Languages className="mr-1 h-3 w-3" />
                            {t('common.intermediate')}
                          </Badge>
                          <Badge variant="outline" className="bg-fun-blue/10 text-fun-blue border-fun-blue/20">
                            <Calendar className="mr-1 h-3 w-3" />
                            {t('common.joined')} {new Date(userProfile.created_at).toLocaleDateString()}
                          </Badge>
                          <Badge variant="outline" className="bg-fun-pink/10 text-fun-pink border-fun-pink/20">
                            <Flame className="mr-1 h-3 w-3" />
                            {userStats.streak.current} {t('common.dayStreak')}
                          </Badge>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Edit Button */}
                  <div className="flex gap-2">
                    {isEditing ? (
                      <>
                        <Button onClick={handleSaveProfile} className="bg-gradient-to-r from-fun-green to-fun-blue hover:shadow-lg">
                          {t('common.saveChanges')}
                        </Button>
                        <Button variant="outline" onClick={() => setIsEditing(false)}>
                          {t('common.cancel')}
                        </Button>
                      </>
                    ) : (
                      <Button onClick={() => setIsEditing(true)} variant="outline" className="gap-2">
                        <Edit2 className="h-4 w-4" />
                        {t('common.editProfile')}
                      </Button>
                    )}
                  </div>
                </div>

                {/* Level Progress */}
                <div className="mt-6 p-4 bg-gradient-to-r from-fun-purple/5 to-fun-blue/5 rounded-2xl">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">{t('common.currentStreak')}</span>
                    <span className="text-sm text-muted-foreground">{userStats.streak.current} / {userStats.streak.longest} days</span>
                  </div>
                  <Progress value={(userStats.streak.current / Math.max(userStats.streak.longest, 1)) * 100} className="h-3" />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="text-center border-fun-blue/20 hover:border-fun-blue/40 transition-all duration-300 hover:shadow-lg">
              <CardContent className="p-6">
                <BookOpen className="h-8 w-8 text-fun-blue mx-auto mb-2" />
                <NumberTicker 
                  value={userStats.wordCounts.length} 
                  className="text-3xl font-bold text-fun-blue"
                  delay={0.1}
                />
                <p className="text-sm text-muted-foreground">{t('common.journalEntries')}</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="text-center border-fun-purple/20 hover:border-fun-purple/40 transition-all duration-300 hover:shadow-lg">
              <CardContent className="p-6">
                <Languages className="h-8 w-8 text-fun-purple mx-auto mb-2" />
                <NumberTicker 
                  value={userStats.streak.totalWords} 
                  className="text-3xl font-bold text-fun-purple"
                  delay={0.2}
                />
                <p className="text-sm text-muted-foreground">{t('common.wordsLearned')}</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="text-center border-fun-pink/20 hover:border-fun-pink/40 transition-all duration-300 hover:shadow-lg">
              <CardContent className="p-6">
                <Flame className="h-8 w-8 text-fun-pink mx-auto mb-2" />
                <NumberTicker 
                  value={userStats.streak.current} 
                  className="text-3xl font-bold text-fun-pink"
                  delay={0.3}
                />
                <p className="text-sm text-muted-foreground">{t('common.currentStreak')}</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="text-center border-fun-green/20 hover:border-fun-green/40 transition-all duration-300 hover:shadow-lg">
              <CardContent className="p-6">
                <Clock className="h-8 w-8 text-fun-green mx-auto mb-2" />
                <div className="text-3xl font-bold text-fun-green">
                  <NumberTicker 
                    value={userStats.languageBreakdown.length} 
                    className="text-3xl font-bold text-fun-green"
                    delay={0.4}
                    decimalPlaces={0}
                  />
                </div>
                <p className="text-sm text-muted-foreground">{t('common.languages')}</p>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Detailed Sections */}
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid grid-cols-3 w-full max-w-md mx-auto">
            <TabsTrigger value="overview">{t('common.overview')}</TabsTrigger>
            <TabsTrigger value="achievements">{t('common.achievements')}</TabsTrigger>
            <TabsTrigger value="activity">{t('common.activity')}</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Learning Goals */}
              <Card className="border-fun-purple/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Target className="h-5 w-5 text-fun-purple" />
                    Learning Goals
                  </CardTitle>
                  <CardDescription>{t('common.currentLanguageObjectives')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>{t('common.dailyWritingGoal')}</span>
                      <span>7/10 days</span>
                    </div>
                    <Progress value={70} className="h-2" />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>{t('common.weeklyVocabularyGoal')}</span>
                      <span>18/25 words</span>
                    </div>
                    <Progress value={72} className="h-2" />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>{t('common.monthlyEntryGoal')}</span>
                      <span>12/20 entries</span>
                    </div>
                    <Progress value={60} className="h-2" />
                  </div>
                </CardContent>
              </Card>

              {/* Recent Activity */}
              <Card className="border-fun-blue/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-fun-blue" />
                    Recent Activity
                  </CardTitle>
                  <CardDescription>Your latest learning activities</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center gap-3 p-2 rounded-lg bg-fun-blue/5">
                    <div className="h-2 w-2 rounded-full bg-fun-blue"></div>
                    <span className="text-sm">Completed vocabulary review</span>
                    <span className="text-xs text-muted-foreground ml-auto">2 hours ago</span>
                  </div>
                  <div className="flex items-center gap-3 p-2 rounded-lg bg-fun-purple/5">
                    <div className="h-2 w-2 rounded-full bg-fun-purple"></div>
                    <span className="text-sm">Wrote journal entry</span>
                    <span className="text-xs text-muted-foreground ml-auto">1 day ago</span>
                  </div>
                  <div className="flex items-center gap-3 p-2 rounded-lg bg-fun-pink/5">
                    <div className="h-2 w-2 rounded-full bg-fun-pink"></div>
                    <span className="text-sm">Learned 5 new words</span>
                    <span className="text-xs text-muted-foreground ml-auto">2 days ago</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="achievements" className="space-y-6">
            <Card className="border-fun-pink/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Award className="h-5 w-5 text-fun-pink" />
                  Recent Achievements
                </CardTitle>
                <CardDescription>Milestones you've unlocked on your learning journey</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4">
                  {recentAchievements.map((achievement, index) => (
                    <motion.div
                      key={achievement.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="flex items-center gap-4 p-4 rounded-lg border border-fun-pink/20 bg-gradient-to-r from-fun-pink/5 to-transparent"
                    >
                      <div className="text-2xl">{achievement.icon}</div>
                      <div className="flex-1">
                        <h4 className="font-semibold">{achievement.title}</h4>
                        <p className="text-sm text-muted-foreground">{achievement.description}</p>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(achievement.date).toLocaleDateString()}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="activity" className="space-y-6">
            <Card className="border-fun-green/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-fun-green" />
                  Activity Calendar
                </CardTitle>
                <CardDescription>Your learning activity over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <Calendar className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">
                    Activity calendar visualization would go here
                  </p>
                  <p className="text-sm text-muted-foreground mt-2">
                    Track your daily learning progress and maintain your streak!
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </motion.div>
    </div>
  )
}
