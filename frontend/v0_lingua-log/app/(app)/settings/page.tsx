"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { 
  Settings, 
  User, 
  Bell, 
  Globe, 
  Shield, 
  Download, 
  Trash2, 
  Moon, 
  Sun, 
  Volume2,
  VolumeX,
  Eye,
  EyeOff,
  Save,
  Target,
  Languages,
  Mail,
  Smartphone
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Slider } from "@/components/ui/slider"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/components/ui/use-toast"
import { getUserProfile, type UserProfile } from "@/lib/user-service"
import { getUserSettings, updateUserSettings, updateUserProfile, type UserSettingsData, type UserSettingsUpdate } from "@/lib/api"

const languages = [
  { code: "en", name: "English", flag: "🇺🇸" },
  { code: "es", name: "Spanish", flag: "🇪🇸" },
  { code: "fr", name: "French", flag: "🇫🇷" },
  { code: "de", name: "German", flag: "🇩🇪" },
  { code: "it", name: "Italian", flag: "🇮🇹" },
  { code: "pt", name: "Portuguese", flag: "🇵🇹" },
  { code: "ja", name: "Japanese", flag: "🇯🇵" },
  { code: "ko", name: "Korean", flag: "🇰🇷" },
  { code: "zh", name: "Chinese", flag: "🇨🇳" },
  { code: "ru", name: "Russian", flag: "🇷🇺" },
]

interface SettingsState {
  // Account
  email: string
  username: string
  password: string
  
  // Language Preferences
  nativeLanguage: string
  targetLanguages: string[]
  
  // Notifications
  emailNotifications: boolean
  pushNotifications: boolean
  dailyReminders: boolean
  weeklyProgress: boolean
  reminderTime: string
  
  // App Preferences
  theme: string
  appLanguage: string
  soundEffects: boolean
  animations: boolean
  
  // Learning Preferences
  difficultyLevel: string
  dailyGoal: number
  weeklyGoal: number
  autoSave: boolean
  showHints: boolean
  
  // Privacy
  publicProfile: boolean
  shareProgress: boolean
  analyticsOptIn: boolean
}

export default function SettingsPage() {
  const { toast } = useToast()
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null)
  const [settings, setSettings] = useState<SettingsState>({
    email: "",
    username: "",
    password: "",
    nativeLanguage: "en",
    targetLanguages: ["es"],
    emailNotifications: true,
    pushNotifications: true,
    dailyReminders: true,
    weeklyProgress: true,
    reminderTime: "09:00",
    theme: "light",
    appLanguage: "en",
    soundEffects: true,
    animations: true,
    difficultyLevel: "intermediate",
    dailyGoal: 1,
    weeklyGoal: 5,
    autoSave: true,
    showHints: true,
    publicProfile: false,
    shareProgress: true,
    analyticsOptIn: true,
  })
  
  const [showPassword, setShowPassword] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [userSettingsData, setUserSettingsData] = useState<UserSettingsData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    async function loadProfileAndSettings() {
      setIsLoading(true)
      try {
        // Load profile and settings in parallel
        const [profile, settingsData] = await Promise.all([
          getUserProfile(),
          getUserSettings()
        ])
        
        if (profile) {
          setUserProfile(profile)
        }
        
        if (settingsData) {
          setUserSettingsData(settingsData)
          // Map API data to frontend state format
          setSettings(prev => ({
            ...prev,
            email: profile?.email || "",
            username: profile?.username || "",
            nativeLanguage: settingsData.native_language,
            targetLanguages: settingsData.target_languages,
            emailNotifications: settingsData.email_notifications,
            pushNotifications: settingsData.push_notifications,
            dailyReminders: settingsData.daily_reminders,
            weeklyProgress: settingsData.weekly_progress,
            reminderTime: settingsData.reminder_time,
            theme: settingsData.theme,
            appLanguage: settingsData.app_language,
            soundEffects: settingsData.sound_effects,
            animations: settingsData.animations,
            difficultyLevel: settingsData.difficulty_level,
            dailyGoal: settingsData.daily_goal,
            weeklyGoal: settingsData.weekly_goal,
            autoSave: settingsData.auto_save,
            showHints: settingsData.show_hints,
            publicProfile: settingsData.public_profile,
            shareProgress: settingsData.share_progress,
            analyticsOptIn: settingsData.analytics_opt_in,
          }))
        }
      } catch (error) {
        console.error('Error loading profile and settings:', error)
        toast({
          title: "Error loading settings",
          description: "Failed to load your settings. Please try again.",
          variant: "destructive",
        })
      } finally {
        setIsLoading(false)
      }
    }
    loadProfileAndSettings()
  }, [])

  const updateSetting = (key: keyof SettingsState, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }))
    setHasChanges(true)
  }

  const addTargetLanguage = (languageCode: string) => {
    if (!settings.targetLanguages.includes(languageCode)) {
      updateSetting("targetLanguages", [...settings.targetLanguages, languageCode])
    }
  }

  const removeTargetLanguage = (languageCode: string) => {
    updateSetting("targetLanguages", settings.targetLanguages.filter(lang => lang !== languageCode))
  }

  const handleSaveSettings = async () => {
    if (!userSettingsData) {
      toast({
        title: "Error",
        description: "Settings not loaded yet. Please try again.",
        variant: "destructive",
      })
      return
    }

    setIsSaving(true)
    try {
      // Map frontend state format to API format
      const updateData: UserSettingsUpdate = {
        native_language: settings.nativeLanguage,
        target_languages: settings.targetLanguages,
        email_notifications: settings.emailNotifications,
        push_notifications: settings.pushNotifications,
        daily_reminders: settings.dailyReminders,
        weekly_progress: settings.weeklyProgress,
        reminder_time: settings.reminderTime,
        theme: settings.theme,
        app_language: settings.appLanguage,
        sound_effects: settings.soundEffects,
        animations: settings.animations,
        difficulty_level: settings.difficultyLevel,
        daily_goal: settings.dailyGoal,
        weekly_goal: settings.weeklyGoal,
        auto_save: settings.autoSave,
        show_hints: settings.showHints,
        public_profile: settings.publicProfile,
        share_progress: settings.shareProgress,
        analytics_opt_in: settings.analyticsOptIn,
      }

      const updatedSettings = await updateUserSettings(updateData)
      setUserSettingsData(updatedSettings)
      
      // If username changed, also update the user profile
      if (settings.username !== userProfile?.username) {
        try {
          const profileUpdateData = {
            full_name: settings.username
            // Note: email is intentionally excluded as it's read-only
          }
          const updatedProfile = await updateUserProfile(profileUpdateData)
          setUserProfile(prev => prev ? { ...prev, username: settings.username } : null)
          
          // Broadcast user profile change to other components
          window.dispatchEvent(new CustomEvent('userProfileUpdated', {
            detail: { username: settings.username }
          }))
        } catch (profileError) {
          console.error('Error updating user profile:', profileError)
          // Don't fail the whole operation if profile update fails
        }
      }
      
      setHasChanges(false)
      
      toast({
        title: "Settings Saved! ✨",
        description: settings.username !== userProfile?.username 
          ? "Your settings and display name have been updated! You may need to refresh to see the name change everywhere."
          : "Your preferences have been updated successfully.",
        variant: "fun",
      })
    } catch (error) {
      console.error('Error saving settings:', error)
      toast({
        title: "Error saving settings",
        description: "Failed to save your settings. Please try again.",
        variant: "destructive",
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleExportData = () => {
    toast({
      title: "Export Started 📦",
      description: "Your data export will be ready shortly. Check your email!",
      variant: "fun",
    })
  }

  const handleDeleteAccount = () => {
    toast({
      title: "Account Deletion",
      description: "Please contact support to delete your account.",
      variant: "destructive",
    })
  }

  if (!userProfile) {
    return (
      <div className="container max-w-4xl mx-auto py-8 px-4">
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-fun-purple mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading settings...</p>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="container max-w-4xl mx-auto py-8 px-4">
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-fun-purple mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading your settings...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container max-w-4xl mx-auto py-8 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-fun-purple to-fun-blue bg-clip-text text-transparent">
                Settings
              </h1>
              <p className="text-xl text-muted-foreground mt-2">
                Customize your LinguaLog experience
              </p>
            </div>
            
            {hasChanges && (
              <Button 
                onClick={handleSaveSettings} 
                disabled={!hasChanges || isSaving}
                className="bg-gradient-to-r from-fun-green to-fun-blue hover:shadow-lg gap-2"
              >
                <Save className="h-4 w-4" />
                {isSaving ? "Saving..." : "Save Changes"}
              </Button>
            )}
          </div>
        </div>

        {/* Settings Tabs */}
        <Tabs defaultValue="account" className="space-y-6">
          <TabsList className="grid grid-cols-2 md:grid-cols-5 w-full">
            <TabsTrigger value="account" className="gap-2">
              <User className="h-4 w-4" />
              <span className="hidden sm:inline">Account</span>
            </TabsTrigger>
            <TabsTrigger value="languages" className="gap-2">
              <Languages className="h-4 w-4" />
              <span className="hidden sm:inline">Languages</span>
            </TabsTrigger>
            <TabsTrigger value="notifications" className="gap-2">
              <Bell className="h-4 w-4" />
              <span className="hidden sm:inline">Notifications</span>
            </TabsTrigger>
            <TabsTrigger value="preferences" className="gap-2">
              <Settings className="h-4 w-4" />
              <span className="hidden sm:inline">Preferences</span>
            </TabsTrigger>
            <TabsTrigger value="privacy" className="gap-2">
              <Shield className="h-4 w-4" />
              <span className="hidden sm:inline">Privacy</span>
            </TabsTrigger>
          </TabsList>

          {/* Account Settings */}
          <TabsContent value="account" className="space-y-6">
            <Card className="border-fun-blue/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5 text-fun-blue" />
                  Account Information
                </CardTitle>
                <CardDescription>Manage your account details and security</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="email">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      value={settings.email}
                      readOnly
                      className="mt-1 bg-muted"
                      title="Contact support to change your email address"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Contact support to change your email address
                    </p>
                  </div>
                  <div>
                    <Label htmlFor="username">Display Name</Label>
                    <Input
                      id="username"
                      value={settings.username}
                      onChange={(e) => updateSetting("username", e.target.value)}
                      className="mt-1"
                    />
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="password">Password</Label>
                  <div className="mt-1">
                    <Input
                      id="password"
                      type="password"
                      value="••••••••••••"
                      readOnly
                      className="bg-muted"
                      title="Use 'Change Password' button to update your password"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="mt-2"
                      onClick={() => {
                        toast({
                          title: "Change Password",
                          description: "Password change feature coming soon - contact support for now",
                          variant: "default",
                        })
                      }}
                    >
                      Change Password
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Language Settings */}
          <TabsContent value="languages" className="space-y-6">
            <Card className="border-fun-purple/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Globe className="h-5 w-5 text-fun-purple" />
                  Language Preferences
                </CardTitle>
                <CardDescription>Set your native language and learning targets</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <Label htmlFor="native-language">Native Language</Label>
                  <Select value={settings.nativeLanguage} onValueChange={(value) => updateSetting("nativeLanguage", value)}>
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {languages.map((lang) => (
                        <SelectItem key={lang.code} value={lang.code}>
                          <div className="flex items-center gap-2">
                            <span>{lang.flag}</span>
                            <span>{lang.name}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>Target Languages</Label>
                  <div className="mt-2 space-y-2">
                    <div className="flex flex-wrap gap-2">
                      {settings.targetLanguages.map((langCode) => {
                        const lang = languages.find(l => l.code === langCode)
                        return lang ? (
                          <Badge key={langCode} variant="outline" className="gap-2">
                            <span>{lang.flag}</span>
                            <span>{lang.name}</span>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-4 w-4 p-0 hover:bg-destructive hover:text-destructive-foreground"
                              onClick={() => removeTargetLanguage(langCode)}
                            >
                              ×
                            </Button>
                          </Badge>
                        ) : null
                      })}
                    </div>
                    
                    <Select onValueChange={addTargetLanguage}>
                      <SelectTrigger>
                        <SelectValue placeholder="Add a language to learn" />
                      </SelectTrigger>
                      <SelectContent>
                        {languages
                          .filter(lang => !settings.targetLanguages.includes(lang.code) && lang.code !== settings.nativeLanguage)
                          .map((lang) => (
                            <SelectItem key={lang.code} value={lang.code}>
                              <div className="flex items-center gap-2">
                                <span>{lang.flag}</span>
                                <span>{lang.name}</span>
                              </div>
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div>
                  <Label>App Interface Language</Label>
                  <Select value={settings.appLanguage} onValueChange={(value) => updateSetting("appLanguage", value)}>
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {languages.slice(0, 5).map((lang) => (
                        <SelectItem key={lang.code} value={lang.code}>
                          <div className="flex items-center gap-2">
                            <span>{lang.flag}</span>
                            <span>{lang.name}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notification Settings */}
          <TabsContent value="notifications" className="space-y-6">
            <Card className="border-fun-pink/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5 text-fun-pink" />
                  Notification Preferences
                </CardTitle>
                <CardDescription>Choose how and when you'd like to be notified</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Mail className="h-5 w-5 text-fun-blue" />
                      <div>
                        <Label>Email Notifications</Label>
                        <p className="text-sm text-muted-foreground">Receive updates via email</p>
                      </div>
                    </div>
                    <Switch 
                      checked={settings.emailNotifications} 
                      onCheckedChange={(checked) => updateSetting("emailNotifications", checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Smartphone className="h-5 w-5 text-fun-purple" />
                      <div>
                        <Label>Push Notifications</Label>
                        <p className="text-sm text-muted-foreground">Receive push notifications on your device</p>
                      </div>
                    </div>
                    <Switch 
                      checked={settings.pushNotifications} 
                      onCheckedChange={(checked) => updateSetting("pushNotifications", checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Bell className="h-5 w-5 text-fun-pink" />
                      <div>
                        <Label>Daily Reminders</Label>
                        <p className="text-sm text-muted-foreground">Get reminded to practice daily</p>
                      </div>
                    </div>
                    <Switch 
                      checked={settings.dailyReminders} 
                      onCheckedChange={(checked) => updateSetting("dailyReminders", checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Target className="h-5 w-5 text-fun-green" />
                      <div>
                        <Label>Weekly Progress</Label>
                        <p className="text-sm text-muted-foreground">Get weekly progress summaries</p>
                      </div>
                    </div>
                    <Switch 
                      checked={settings.weeklyProgress} 
                      onCheckedChange={(checked) => updateSetting("weeklyProgress", checked)}
                    />
                  </div>
                </div>

                {settings.dailyReminders && (
                  <div>
                    <Label htmlFor="reminder-time">Daily Reminder Time</Label>
                    <Input
                      id="reminder-time"
                      type="time"
                      value={settings.reminderTime}
                      onChange={(e) => updateSetting("reminderTime", e.target.value)}
                      className="mt-1 w-40"
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* App Preferences */}
          <TabsContent value="preferences" className="space-y-6">
            <div className="grid gap-6">
              {/* Learning Preferences */}
              <Card className="border-fun-green/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Target className="h-5 w-5 text-fun-green" />
                    Learning Preferences
                  </CardTitle>
                  <CardDescription>Customize your learning experience</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>Difficulty Level</Label>
                    <Select value={settings.difficultyLevel} onValueChange={(value) => updateSetting("difficultyLevel", value)}>
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="beginner">🌱 Beginner</SelectItem>
                        <SelectItem value="intermediate">🌿 Intermediate</SelectItem>
                        <SelectItem value="advanced">🌳 Advanced</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Daily Entry Goal: {settings.dailyGoal} {settings.dailyGoal === 1 ? 'entry' : 'entries'}</Label>
                    <Slider
                      value={[settings.dailyGoal]}
                      onValueChange={(value) => updateSetting("dailyGoal", value[0])}
                      max={5}
                      min={1}
                      step={1}
                      className="mt-2"
                    />
                  </div>

                  <div>
                    <Label>Weekly Vocabulary Goal: {settings.weeklyGoal} words</Label>
                    <Slider
                      value={[settings.weeklyGoal]}
                      onValueChange={(value) => updateSetting("weeklyGoal", value[0])}
                      max={50}
                      min={5}
                      step={5}
                      className="mt-2"
                    />
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label>Auto-save entries</Label>
                      <Switch 
                        checked={settings.autoSave} 
                        onCheckedChange={(checked) => updateSetting("autoSave", checked)}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <Label>Show learning hints</Label>
                      <Switch 
                        checked={settings.showHints} 
                        onCheckedChange={(checked) => updateSetting("showHints", checked)}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* App Preferences */}
              <Card className="border-fun-blue/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Settings className="h-5 w-5 text-fun-blue" />
                    App Preferences
                  </CardTitle>
                  <CardDescription>Customize the app's look and feel</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>Theme</Label>
                    <Select value={settings.theme} onValueChange={(value) => updateSetting("theme", value)}>
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="light">
                          <div className="flex items-center gap-2">
                            <Sun className="h-4 w-4" />
                            Light
                          </div>
                        </SelectItem>
                        <SelectItem value="dark">
                          <div className="flex items-center gap-2">
                            <Moon className="h-4 w-4" />
                            Dark
                          </div>
                        </SelectItem>
                        <SelectItem value="system">
                          <div className="flex items-center gap-2">
                            <Settings className="h-4 w-4" />
                            System
                          </div>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {settings.soundEffects ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                        <Label>Sound effects</Label>
                      </div>
                      <Switch 
                        checked={settings.soundEffects} 
                        onCheckedChange={(checked) => updateSetting("soundEffects", checked)}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <Label>Animations</Label>
                      <Switch 
                        checked={settings.animations} 
                        onCheckedChange={(checked) => updateSetting("animations", checked)}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Privacy & Data */}
          <TabsContent value="privacy" className="space-y-6">
            <div className="grid gap-6">
              {/* Privacy Settings */}
              <Card className="border-fun-purple/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-fun-purple" />
                    Privacy Settings
                  </CardTitle>
                  <CardDescription>Control your privacy and data sharing preferences</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Public Profile</Label>
                      <p className="text-sm text-muted-foreground">Allow others to see your profile</p>
                    </div>
                    <Switch 
                      checked={settings.publicProfile} 
                      onCheckedChange={(checked) => updateSetting("publicProfile", checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Share Progress</Label>
                      <p className="text-sm text-muted-foreground">Share your learning progress publicly</p>
                    </div>
                    <Switch 
                      checked={settings.shareProgress} 
                      onCheckedChange={(checked) => updateSetting("shareProgress", checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Analytics & Insights</Label>
                      <p className="text-sm text-muted-foreground">Help improve the app with usage analytics</p>
                    </div>
                    <Switch 
                      checked={settings.analyticsOptIn} 
                      onCheckedChange={(checked) => updateSetting("analyticsOptIn", checked)}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Data Management */}
              <Card className="border-fun-pink/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Download className="h-5 w-5 text-fun-pink" />
                    Data Management
                  </CardTitle>
                  <CardDescription>Export or delete your data</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-medium">Export Your Data</h4>
                      <p className="text-sm text-muted-foreground mb-3">
                        Download all your journal entries, vocabulary, and progress data
                      </p>
                      <Button onClick={handleExportData} variant="outline" className="gap-2">
                        <Download className="h-4 w-4" />
                        Export Data
                      </Button>
                    </div>

                    <Separator />

                    <div>
                      <h4 className="font-medium text-destructive">Danger Zone</h4>
                      <p className="text-sm text-muted-foreground mb-3">
                        Permanently delete your account and all associated data
                      </p>
                      <Button onClick={handleDeleteAccount} variant="destructive" className="gap-2">
                        <Trash2 className="h-4 w-4" />
                        Delete Account
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </motion.div>
    </div>
  )
}
