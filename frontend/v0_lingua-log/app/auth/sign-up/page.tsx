"use client"

import type React from "react"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Eye, EyeOff, UserPlus, Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { useToast } from "@/components/ui/use-toast"
import { LoadingDots } from "@/components/loading-dots"

// Import the auth function
import { signUp } from "@/lib/auth"

export default function SignUpPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const router = useRouter()
  const { toast } = useToast()

  // Password strength calculation
  const calculatePasswordStrength = (password: string): number => {
    if (!password) return 0

    let strength = 0

    // Length check
    if (password.length >= 8) strength += 25

    // Character variety checks
    if (/[A-Z]/.test(password)) strength += 25
    if (/[0-9]/.test(password)) strength += 25
    if (/[^A-Za-z0-9]/.test(password)) strength += 25

    return strength
  }

  const passwordStrength = calculatePasswordStrength(password)

  const getPasswordStrengthText = () => {
    if (passwordStrength === 0) return ""
    if (passwordStrength <= 25) return "Weak"
    if (passwordStrength <= 50) return "Fair"
    if (passwordStrength <= 75) return "Good"
    return "Strong"
  }

  const getPasswordStrengthColor = () => {
    if (passwordStrength <= 25) return "bg-pastel-pink"
    if (passwordStrength <= 50) return "bg-pastel-yellow"
    if (passwordStrength <= 75) return "bg-pastel-blue"
    return "bg-pastel-mint"
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!email || !password) {
      setError("Email and password are required")
      return
    }

    if (passwordStrength < 50) {
      setError("Please use a stronger password")
      return
    }

    setIsLoading(true)

    try {
      // Call the signup function
      const { success, user } = await signUp({
        email,
        password,
        username: name || undefined
      })

      setIsLoading(false)
      
      if (success && user) {
        toast({
          title: "Account created! ✨",
          description: "Welcome to LinguaLog! Your language journey begins now.",
          variant: "default",
        })
        
        // Redirect to dashboard
        router.push("/dashboard")
      }
    } catch (err: any) {
      setIsLoading(false)
      
      // Handle different error types
      if (err.message.includes("already registered")) {
        setError("This email is already registered. Please use another email or sign in.")
      } else {
        setError(err.message || "Failed to create account. Please try again.")
      }
      
      console.error("Signup error:", err)
    }
  }

  return (
    <Card className="w-full shadow-soft-lg border-pastel-purple/20">
      <CardHeader className="space-y-1">
        <div className="flex justify-center mb-2">
          <Sparkles className="h-10 w-10 text-pastel-purple animate-pulse-gentle" />
        </div>
        <CardTitle className="text-2xl font-bold text-center">
          <span className="heading-underline">Join LinguaLog</span>
        </CardTitle>
        <CardDescription className="text-center">Create your account and start your language journey</CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {error && (
            <div className="p-3 text-sm bg-pastel-pink/20 text-primary rounded-xl border border-pastel-pink/30">
              {error}
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="name">Name (optional)</Label>
            <Input
              id="name"
              type="text"
              placeholder="Your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
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
            {password && (
              <div className="space-y-1 mt-2">
                <div className="flex justify-between text-xs">
                  <span>Password strength:</span>
                  <span
                    className={
                      passwordStrength <= 25
                        ? "text-pastel-pink font-medium"
                        : passwordStrength <= 50
                          ? "text-pastel-yellow font-medium"
                          : passwordStrength <= 75
                            ? "text-pastel-blue font-medium"
                            : "text-pastel-mint font-medium"
                    }
                  >
                    {getPasswordStrengthText()}
                  </span>
                </div>
                <Progress value={passwordStrength} className="h-1.5" indicatorClassName={getPasswordStrengthColor()} />
                <p className="text-xs text-muted-foreground mt-1">
                  Use 8+ characters with a mix of letters, numbers & symbols
                </p>
              </div>
            )}
          </div>
        </CardContent>
        <CardFooter className="flex flex-col space-y-4">
          <Button type="submit" className="w-full" variant="default" disabled={isLoading}>
            {isLoading ? (
              <div className="flex items-center justify-center">
                <LoadingDots />
                <span className="ml-2">Creating account</span>
              </div>
            ) : (
              <div className="flex items-center justify-center">
                <UserPlus className="mr-2 h-4 w-4" />
                Create Account
              </div>
            )}
          </Button>
          <div className="text-center text-sm">
            Already have an account?{" "}
            <Link href="/auth/sign-in" className="text-primary hover:underline font-medium">
              Sign in
            </Link>
          </div>
        </CardFooter>
      </form>
    </Card>
  )
}
