"use client"

import { useState, FormEvent } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Eye, EyeOff, LogIn, Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/components/ui/use-toast"
import { LoadingDots } from "@/components/loading-dots"
import { Confetti } from "@/components/confetti"

// Import the auth functions
import { signInWithEmail, signIn } from "@/lib/auth"

export default function SignInPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [showConfetti, setShowConfetti] = useState(false)
  const [magicLinkSent, setMagicLinkSent] = useState(false)
  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const router = useRouter()
  const { toast } = useToast()

  const handleMagicLinkSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError("")

    if (!email) {
      setError("Please enter your email address")
      return
    }

    setIsLoading(true)

    try {
      // Use Supabase to send the magic link
      const { success } = await signInWithEmail(email)
      
      setIsLoading(false)
      
      if (success) {
        setMagicLinkSent(true)
        setShowConfetti(true)

        toast({
          title: "Magic link sent! 🪄",
          description: "Check your email for a login link",
          variant: "default",
        })
      }
    } catch (err: unknown) {
      setIsLoading(false)
      setError("Failed to send login link. Please try again.")
      console.error(err)
    }
  }

  const handlePasswordSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError("")

    if (!email || !password) {
      setError("Email and password are required")
      return
    }

    setIsLoading(true)

    try {
      // Use Supabase to sign in with password
      const { success, user } = await signIn({ email, password })
      
      setIsLoading(false)
      
      if (success && user) {
        setShowConfetti(true)
        
        toast({
          title: "Welcome back! ✨",
          description: "Successfully logged in",
          variant: "default",
        })
        
        // Redirect to dashboard
        router.push("/dashboard")
      }
    } catch (err: unknown) {
      setIsLoading(false)
      
      // Better error handling
      const errorMessage = err instanceof Error ? err.message : String(err)
      if (errorMessage.includes("Invalid login credentials")) {
        setError("Invalid email or password. Please try again.")
      } else {
        setError(errorMessage || "Failed to sign in. Please try again.")
      }
      
      console.error("Login error:", err)
    }
  }

  return (
    <>
      {showConfetti && <Confetti />}
      <Card className="w-full">
        <CardHeader className="space-y-1">
          <div className="flex justify-center mb-2">
            <Sparkles className="h-10 w-10 text-blue-500" />
          </div>
          <CardTitle className="text-2xl font-bold text-center">
            {showPasswordForm ? "Sign In with Password" : "Welcome to LinguaLog"}
          </CardTitle>
          <CardDescription className="text-center">
            {magicLinkSent 
              ? "Check your email for the login link"
              : showPasswordForm
                ? "Enter your credentials to access your account"
                : "Let's continue your language journey!"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="p-3 text-sm bg-red-50 text-red-600 rounded-lg border border-red-200">
              {error}
            </div>
          )}
          
          {magicLinkSent ? (
            <div className="p-3 text-sm bg-blue-50 text-primary rounded-lg border border-blue-200">
              Magic link sent! Check your email to complete login.
            </div>
          ) : showPasswordForm ? (
            <form onSubmit={handlePasswordSubmit}>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email-password">Email</Label>
                  <Input
                    id="email-password"
                    type="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <Eye className="h-4 w-4 text-muted-foreground" />
                      )}
                      <span className="sr-only">{showPassword ? "Hide password" : "Show password"}</span>
                    </Button>
                  </div>
                </div>
                
                <Button type="submit" className="w-full" disabled={isLoading}>
                  {isLoading ? (
                    <div className="flex items-center justify-center">
                      <LoadingDots />
                      <span className="ml-2">Signing in</span>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center">
                      <LogIn className="mr-2 h-4 w-4" />
                      Sign In
                    </div>
                  )}
                </Button>
                
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setShowPasswordForm(false)}
                  className="w-full mt-2"
                >
                  Use Magic Link Instead
                </Button>
              </div>
            </form>
          ) : (
            <>
              <form onSubmit={handleMagicLinkSubmit}>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="name@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                  
                  <Button type="submit" className="w-full" disabled={isLoading}>
                    {isLoading ? (
                      <div className="flex items-center justify-center">
                        <LoadingDots />
                        <span className="ml-2">Sending link</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center">
                        <LogIn className="mr-2 h-4 w-4" />
                        Send Login Link
                      </div>
                    )}
                  </Button>
                </div>
              </form>
              
              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">Or</span>
                </div>
              </div>
              
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => setShowPasswordForm(true)}
                className="w-full"
              >
                Sign in with Password
              </Button>
            </>
          )}
        </CardContent>
        <CardFooter className="flex flex-col">
          <div className="text-center text-sm">
            Don&apos;t have an account?{" "}
            <Link href="/auth/sign-up" className="text-blue-600 hover:underline font-medium">
              Sign up
            </Link>
          </div>
        </CardFooter>
      </Card>
    </>
  )
}
