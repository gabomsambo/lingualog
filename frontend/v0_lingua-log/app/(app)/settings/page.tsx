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
import { useLocale } from "@/i18n/LocaleProvider"
import { LANGUAGES, getUILanguages, getTargetLanguages } from "@/i18n/languages"

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
  
  // New multilingual fields
  interfaceLanguage: string
  nativeLang: string
  defaultTargetLanguage: string
  explanationMode: string
  immersionLevel: number
  strictness: string
  formality: string
  languageProfiles: Record<string, { immersion_level: number; proficiency: string }>
}

export default function SettingsPage() {
  const { toast } = useToast()
  const { t, setUiLang } = useLocale()
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
    // New multilingual fields
    interfaceLanguage: "en",
    nativeLang: "en",
    defaultTargetLanguage: "es",
    explanationMode: "bilingual",
    immersionLevel: 1,
    strictness: "medium",
    formality: "neutral",
    languageProfiles: {},
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
            // New multilingual fields
            interfaceLanguage: settingsData.interface_lang,
            nativeLang: settingsData.native_lang,
            defaultTargetLanguage: settingsData.default_target_lang || "es",
            explanationMode: settingsData.explanation_mode,
            immersionLevel: settingsData.immersion_level,
            strictness: settingsData.strictness,
            formality: settingsData.formality,
            languageProfiles: Object.fromEntries(
              (settingsData.language_profiles ?? []).map((row) => [
                row.l2,
                { immersion_level: row.immersion_level, proficiency: row.proficiency },
              ])
            ),
          }))
        }
      } catch (error) {
        console.error('Error loading profile and settings:', error)
        toast({
          title: t('common.errorLoading'),
          description: t('common.tryAgain'),
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

  const studiedLanguages = Array.from(
    new Set([
      ...(settings.targetLanguages || []),
      settings.defaultTargetLanguage,
      ...Object.keys(settings.languageProfiles),
    ].filter(Boolean))
  )

  const profileFor = (code: string) =>
    settings.languageProfiles[code] ?? {
      immersion_level: settings.immersionLevel,
      proficiency: "A2",
    }

  const updateLanguageProfile = (
    code: string,
    patch: Partial<{ immersion_level: number; proficiency: string }>
  ) => {
    setSettings(prev => {
      const current = prev.languageProfiles[code] ?? {
        immersion_level: prev.immersionLevel,
        proficiency: "A2",
      }
      const nextProfile = { ...current, ...patch }
      return {
        ...prev,
        immersionLevel:
          code === prev.defaultTargetLanguage && patch.immersion_level !== undefined
            ? patch.immersion_level
            : prev.immersionLevel,
        languageProfiles: { ...prev.languageProfiles, [code]: nextProfile },
      }
    })
    setHasChanges(true)
  }

  const updateDefaultImmersion = (level: number) => {
    updateLanguageProfile(settings.defaultTargetLanguage, { immersion_level: level })
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
        title: t('common.error'),
        description: t('common.notLoadedYet'),
        variant: "destructive",
      })
      return
    }

    setIsSaving(true)
    try {
      // If interface language changed, apply it immediately
      if (settings.interfaceLanguage !== userSettingsData.interface_lang) {
        try {
          await setUiLang(settings.interfaceLanguage)
        } catch (error) {
          console.error('Error changing interface language:', error)
        }
      }

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
        // New multilingual fields
        interface_lang: settings.interfaceLanguage,
        native_lang: settings.nativeLang,
        default_target_lang: settings.defaultTargetLanguage,
        explanation_mode: settings.explanationMode,
        immersion_level: settings.immersionLevel,
        strictness: settings.strictness,
        formality: settings.formality,
        language_profiles: studiedLanguages.map((code) => ({
          l2: code,
          immersion_level: profileFor(code).immersion_level,
          proficiency: profileFor(code).proficiency,
        })),
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
        title: t('settings.settingsSaved'),
        description: settings.username !== userProfile?.username 
          ? t('settings.settingsAndNameUpdated')
          : t('settings.settingsUpdated'),
        variant: "fun",
      })
    } catch (error) {
      console.error('Error saving settings:', error)
      toast({
        title: t('common.errorSaving'),
        description: t('common.tryAgain'),
        variant: "destructive",
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleExportData = () => {
    toast({
      title: t('settings.exportStarted'),
      description: t('settings.dataExportReady'),
      variant: "fun",
    })
  }

  const handleDeleteAccount = () => {
    toast({
      title: t('settings.accountDeletion'),
      description: t('settings.contactSupportToDelete'),
      variant: "destructive",
    })
  }

  if (!userProfile) {
    return (
      <div className="container max-w-4xl mx-auto py-8 px-4">
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-fun-purple mx-auto mb-4"></div>
            <p className="text-muted-foreground">{t('settings.loadingSettings')}</p>
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
            <p className="text-muted-foreground">{t('settings.loadingYourSettings')}</p>
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
                {t('settings.settings')}
              </h1>
              <p className="text-xl text-muted-foreground mt-2">
                {t('settings.customizeExperience')}
              </p>
            </div>
            
            {hasChanges && (
              <Button 
                onClick={handleSaveSettings} 
                disabled={!hasChanges || isSaving}
                className="bg-gradient-to-r from-fun-green to-fun-blue hover:shadow-lg gap-2"
              >
                <Save className="h-4 w-4" />
                {isSaving ? t('settings.saving') : t('settings.saveChanges')}
              </Button>
            )}
          </div>
        </div>

        {/* Settings Tabs */}
        <Tabs defaultValue="account" className="space-y-6">
          <TabsList className="grid grid-cols-2 md:grid-cols-5 w-full">
            <TabsTrigger value="account" className="gap-2">
              <User className="h-4 w-4" />
              <span className="hidden sm:inline">{t('settings.account')}</span>
            </TabsTrigger>
            <TabsTrigger value="languages" className="gap-2">
              <Languages className="h-4 w-4" />
              <span className="hidden sm:inline">{t('settings.languages')}</span>
            </TabsTrigger>
            <TabsTrigger value="notifications" className="gap-2">
              <Bell className="h-4 w-4" />
              <span className="hidden sm:inline">{t('settings.notifications')}</span>
            </TabsTrigger>
            <TabsTrigger value="preferences" className="gap-2">
              <Settings className="h-4 w-4" />
              <span className="hidden sm:inline">{t('settings.preferences')}</span>
            </TabsTrigger>
            <TabsTrigger value="privacy" className="gap-2">
              <Shield className="h-4 w-4" />
              <span className="hidden sm:inline">{t('settings.privacy')}</span>
            </TabsTrigger>
          </TabsList>

          {/* Account Settings */}
          <TabsContent value="account" className="space-y-6">
            <Card className="border-fun-blue/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5 text-fun-blue" />
                  {t('settings.accountInformation')}
                </CardTitle>
                <CardDescription>{t('settings.manageAccountDetails')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="email">{t('settings.emailAddress')}</Label>
                    <Input
                      id="email"
                      type="email"
                      value={settings.email}
                      readOnly
                      className="mt-1 bg-muted"
                      title={t('settings.contactSupportToChangeEmail')}
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      {t('settings.contactSupportToChangeEmail')}
                    </p>
                  </div>
                  <div>
                    <Label htmlFor="username">{t('settings.displayName')}</Label>
                    <Input
                      id="username"
                      value={settings.username}
                      onChange={(e) => updateSetting("username", e.target.value)}
                      className="mt-1"
                    />
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="password">{t('settings.password')}</Label>
                  <div className="mt-1">
                    <Input
                      id="password"
                      type="password"
                      value="••••••••••••"
                      readOnly
                      className="bg-muted"
                      title={t('settings.changePassword')}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="mt-2"
                      onClick={() => {
                        toast({
                          title: t('settings.changePasswordFeature'),
                          description: t('settings.passwordChangeComingSoon'),
                          variant: "default",
                        })
                      }}
                    >
                      {t('settings.changePassword')}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Language Settings */}
          <TabsContent value="languages" className="space-y-6">
            <div className="grid gap-6">
              {/* Core Language Settings */}
              <Card className="border-fun-purple/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Globe className="h-5 w-5 text-fun-purple" />
                    {t('settings.language')} {t('settings.preferences')}
                  </CardTitle>
                  <CardDescription>{t('settings.nativeLanguageDesc')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="interface-language">{t('settings.interfaceLanguage')}</Label>
                      <p className="text-sm text-muted-foreground mb-2">{t('settings.interfaceLanguageDesc')}</p>
                      <Select value={settings.interfaceLanguage} onValueChange={(value) => updateSetting("interfaceLanguage", value)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {getUILanguages().map((lang) => (
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
                      <Label htmlFor="native-language">{t('settings.nativeLanguage')}</Label>
                      <p className="text-sm text-muted-foreground mb-2">{t('settings.nativeLanguageDesc')}</p>
                      <Select value={settings.nativeLang} onValueChange={(value) => updateSetting("nativeLang", value)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {LANGUAGES.map((lang) => (
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
                    <Label htmlFor="default-target-language">{t('settings.defaultTargetLanguage')}</Label>
                    <p className="text-sm text-muted-foreground mb-2">{t('settings.defaultTargetLanguageDesc')}</p>
                    <Select value={settings.defaultTargetLanguage} onValueChange={(value) => {
                      const profile = settings.languageProfiles[value]
                      setSettings(prev => ({
                        ...prev,
                        defaultTargetLanguage: value,
                        immersionLevel: profile?.immersion_level ?? prev.immersionLevel,
                      }))
                      setHasChanges(true)
                    }}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {getTargetLanguages()
                          .filter(lang => lang.code !== settings.nativeLang)
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

                  <div className="space-y-4">
                    <div>
                      <Label>{t('settings.languagesYouStudy')}</Label>
                      <p className="text-sm text-muted-foreground">{t('settings.languagesYouStudyDesc')}</p>
                    </div>
                    {studiedLanguages.map((code) => {
                      const lang = LANGUAGES.find((item) => item.code === code)
                      const profile = profileFor(code)
                      const descriptions = [
                        t('settings.immersion0Desc'),
                        t('settings.immersion1Desc'),
                        t('settings.immersion2Desc'),
                        t('settings.immersion3Desc'),
                      ]
                      return (
                        <div key={code} className="rounded-2xl border border-fun-purple/15 p-4 space-y-3">
                          <div className="flex items-center gap-2 font-medium">
                            <span>{lang?.flag}</span>
                            <span>{lang?.name || code}</span>
                          </div>
                          <div>
                            <Label>
                              {t('settings.immersionLevel')}: {profile.immersion_level}/3
                            </Label>
                            <p className="text-sm text-muted-foreground mb-2">{descriptions[profile.immersion_level]}</p>
                            <Slider
                              value={[profile.immersion_level]}
                              onValueChange={(value) => updateLanguageProfile(code, { immersion_level: value[0] })}
                              max={3}
                              min={0}
                              step={1}
                            />
                            <div className="flex justify-between text-xs text-muted-foreground mt-1">
                              <span>0: {t('settings.immersionNativeFirst')}</span>
                              <span>1: {t('settings.immersionGuidedBilingual')}</span>
                              <span>2: {t('settings.immersionBalanced')}</span>
                              <span>3: {t('settings.immersionImmersive')}</span>
                            </div>
                          </div>
                          <div>
                            <Label>{t('settings.proficiency')}</Label>
                            <p className="text-sm text-muted-foreground mb-2">{t('settings.proficiencyDesc')}</p>
                            <Select
                              value={profile.proficiency}
                              onValueChange={(value) => updateLanguageProfile(code, { proficiency: value })}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {(["A1", "A2", "B1", "B2", "C1", "C2"] as const).map((band) => (
                                  <SelectItem key={band} value={band}>
                                    {t(`settings.proficiency${band}`)}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  <div>
                    <Label>{t('settings.immersionLevel')}: {settings.immersionLevel}/3</Label>
                    <p className="text-sm text-muted-foreground mb-2">{t('settings.immersionLevelDesc')}</p>
                    <div className="space-y-3">
                      <Slider
                        value={[settings.immersionLevel]}
                        onValueChange={(value) => updateDefaultImmersion(value[0])}
                        max={3}
                        min={0}
                        step={1}
                        className="mt-2"
                      />
                      <div className="flex justify-between text-sm text-muted-foreground">
                        <span>0: {t('settings.immersionNativeFirst')}</span>
                        <span>1: {t('settings.immersionGuidedBilingual')}</span>
                        <span>2: {t('settings.immersionBalanced')}</span>
                        <span>3: {t('settings.immersionImmersive')}</span>
                      </div>
                    </div>
                  </div>

                  {/* Deprecated: Target Languages array UI - Hidden but kept for backward compatibility */}
                  {/* Language switching is now done via "Default Target Language" above */}
                  {false && (
                    <div>
                      <Label>{t('settings.targetLanguagesLegacy')}</Label>
                      <div className="mt-2 space-y-2">
                        <div className="flex flex-wrap gap-2">
                          {settings.targetLanguages.map((langCode) => {
                            const lang = LANGUAGES.find(l => l.code === langCode)
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
                            <SelectValue placeholder={t('settings.addLanguageToLearn')} />
                          </SelectTrigger>
                          <SelectContent>
                            {LANGUAGES
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
                  )}
                </CardContent>
              </Card>

              {/* Advanced Language Settings */}
              <Card className="border-fun-blue/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Settings className="h-5 w-5 text-fun-blue" />
                    {t('settings.advancedSettings')}
                  </CardTitle>
                  <CardDescription>{t('settings.fineTuneExperience')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label>{t('settings.explanationMode')}</Label>
                      <p className="text-sm text-muted-foreground mb-2">{t('settings.explanationModeDesc')}</p>
                      <Select value={settings.explanationMode} onValueChange={(value) => updateSetting("explanationMode", value)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="level">{t('settings.explanationFollowLevel')}</SelectItem>
                          <SelectItem value="native_only">{t('settings.explanationNativeOnly')}</SelectItem>
                          <SelectItem value="target_only">{t('settings.explanationTargetOnly')}</SelectItem>
                          <SelectItem value="bilingual">{t('settings.explanationBilingual')}</SelectItem>
                          <SelectItem value="smart">{t('settings.explanationSmart')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label>{t('settings.strictness')}</Label>
                      <p className="text-sm text-muted-foreground mb-2">{t('settings.strictnessDesc')}</p>
                      <Select value={settings.strictness} onValueChange={(value) => updateSetting("strictness", value)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="gentle">{t('settings.strictnessGentle')}</SelectItem>
                          <SelectItem value="medium">{t('settings.strictnessMedium')}</SelectItem>
                          <SelectItem value="strict">{t('settings.strictnessStrict')}</SelectItem>
                          <SelectItem value="pedantic">{t('settings.strictnessPedantic')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label>{t('settings.formality')}</Label>
                      <p className="text-sm text-muted-foreground mb-2">{t('settings.formalityDesc')}</p>
                      <Select value={settings.formality} onValueChange={(value) => updateSetting("formality", value)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="casual">{t('settings.formalityCasual')}</SelectItem>
                          <SelectItem value="neutral">{t('settings.formalityNeutral')}</SelectItem>
                          <SelectItem value="formal">{t('settings.formalityFormal')}</SelectItem>
                          <SelectItem value="academic">{t('settings.formalityAcademic')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Notification Settings */}
          <TabsContent value="notifications" className="space-y-6">
            <Card className="border-fun-pink/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5 text-fun-pink" />
                  {t('settings.notificationPreferences')}
                </CardTitle>
                <CardDescription>{t('settings.chooseHowNotified')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Mail className="h-5 w-5 text-fun-blue" />
                      <div>
                        <Label>{t('settings.emailNotifications')}</Label>
                        <p className="text-sm text-muted-foreground">{t('settings.receiveUpdatesViaEmail')}</p>
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
                        <Label>{t('settings.pushNotifications')}</Label>
                        <p className="text-sm text-muted-foreground">{t('settings.receivePushNotifications')}</p>
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
                        <Label>{t('settings.dailyReminders')}</Label>
                        <p className="text-sm text-muted-foreground">{t('settings.getRemindedToPractice')}</p>
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
                        <Label>{t('settings.weeklyProgress')}</Label>
                        <p className="text-sm text-muted-foreground">{t('settings.getWeeklyProgressSummaries')}</p>
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
                    <Label htmlFor="reminder-time">{t('settings.dailyReminderTime')}</Label>
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
                    {t('settings.learningPreferences')}
                  </CardTitle>
                  <CardDescription>{t('settings.customizeLearningExperience')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>{t('settings.difficultyLevel')}</Label>
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
                    <Label>{t('settings.dailyEntryGoal')}: {settings.dailyGoal} {settings.dailyGoal === 1 ? t('settings.entry') : t('settings.entries')}</Label>
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
                    <Label>{t('settings.weeklyVocabularyGoal')}: {settings.weeklyGoal} {t('settings.words')}</Label>
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
                      <Label>{t('settings.autoSaveEntries')}</Label>
                      <Switch 
                        checked={settings.autoSave} 
                        onCheckedChange={(checked) => updateSetting("autoSave", checked)}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <Label>{t('settings.showLearningHints')}</Label>
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
                    {t('settings.appPreferences')}
                  </CardTitle>
                  <CardDescription>{t('settings.customizeAppLookAndFeel')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>{t('settings.theme')}</Label>
                    <Select value={settings.theme} onValueChange={(value) => updateSetting("theme", value)}>
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="light">
                          <div className="flex items-center gap-2">
                            <Sun className="h-4 w-4" />
                            {t('settings.light')}
                          </div>
                        </SelectItem>
                        <SelectItem value="dark">
                          <div className="flex items-center gap-2">
                            <Moon className="h-4 w-4" />
                            {t('settings.dark')}
                          </div>
                        </SelectItem>
                        <SelectItem value="system">
                          <div className="flex items-center gap-2">
                            <Settings className="h-4 w-4" />
                            {t('settings.system')}
                          </div>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {settings.soundEffects ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                        <Label>{t('settings.soundEffects')}</Label>
                      </div>
                      <Switch 
                        checked={settings.soundEffects} 
                        onCheckedChange={(checked) => updateSetting("soundEffects", checked)}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <Label>{t('settings.animations')}</Label>
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
                    {t('settings.privacySettings')}
                  </CardTitle>
                  <CardDescription>{t('settings.controlPrivacyDataSharing')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>{t('settings.publicProfile')}</Label>
                      <p className="text-sm text-muted-foreground">{t('settings.allowOthersToSeeProfile')}</p>
                    </div>
                    <Switch 
                      checked={settings.publicProfile} 
                      onCheckedChange={(checked) => updateSetting("publicProfile", checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label>{t('settings.shareProgress')}</Label>
                      <p className="text-sm text-muted-foreground">{t('settings.shareLearningProgressPublicly')}</p>
                    </div>
                    <Switch 
                      checked={settings.shareProgress} 
                      onCheckedChange={(checked) => updateSetting("shareProgress", checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label>{t('settings.analyticsInsights')}</Label>
                      <p className="text-sm text-muted-foreground">{t('settings.helpImproveAppWithAnalytics')}</p>
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
                    {t('settings.dataManagement')}
                  </CardTitle>
                  <CardDescription>{t('settings.exportOrDeleteData')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-medium">{t('settings.exportYourData')}</h4>
                      <p className="text-sm text-muted-foreground mb-3">
                        {t('settings.downloadAllData')}
                      </p>
                      <Button onClick={handleExportData} variant="outline" className="gap-2">
                        <Download className="h-4 w-4" />
                        {t('settings.exportData')}
                      </Button>
                    </div>

                    <Separator />

                    <div>
                      <h4 className="font-medium text-destructive">{t('settings.dangerZone')}</h4>
                      <p className="text-sm text-muted-foreground mb-3">
                        {t('settings.permanentlyDeleteAccount')}
                      </p>
                      <Button onClick={handleDeleteAccount} variant="destructive" className="gap-2">
                        <Trash2 className="h-4 w-4" />
                        {t('settings.deleteAccount')}
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
