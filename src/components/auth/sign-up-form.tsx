// src/components/auth/sign-up-form.tsx
"use client";

import * as React from "react";
import { useState } from "react";
import { useRouter } from "next/navigation"; // Used to redirect after successful signup initiation
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import * as z from "zod";
// --- Updated Supabase Client Import ---
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

// --- UI Imports ---
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/use-toast"; // Assuming use-toast is correctly set up

// --- Zod Schema Definition ---
// Added custom messages for better feedback
const formSchema = z.object({
    email: z.string().email({ message: "Please enter a valid email address." }),
    password: z.string().min(6, { message: "Password must be at least 6 characters." }),
    confirmPassword: z.string().min(6, { message: "Password must be at least 6 characters." }),
  })
  // Refine checks if passwords match after individual field validation
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match.",
    path: ["confirmPassword"], // Apply the error specifically to the confirmPassword field
  });

// --- Component Definition ---
export function SignUpForm() {
  const router = useRouter(); // Get router instance for navigation
  const [isLoading, setIsLoading] = useState(false); // State to manage loading indicator
  // --- Use the correct browser client ---
  const supabase = createSupabaseBrowserClient(); // Initialize Supabase client

  // Initialize the form using react-hook-form
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema), // Use Zod for validation
    defaultValues: {
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  // --- Handler for Email/Password Sign Up ---
  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsLoading(true); // Set loading state

    try {
      // Attempt to sign up the user with Supabase auth
      const { data, error } = await supabase.auth.signUp({
        email: values.email,
        password: values.password,
        options: {
          // This URL is embedded in the confirmation email sent by Supabase.
          // When the user clicks the link, they are directed here.
          emailRedirectTo: `${window.location.origin}/auth/callback`, // Or just origin
        },
      });

      // Throw an error if Supabase returns one
      if (error) {
        console.error("Sign-up error:", error); // Log the error
        throw error;
      }

      // IMPORTANT: Supabase signUp by default requires email confirmation.
      // The user is NOT logged in yet at this point.

      // Show success message prompting the user to check their email
      toast({
        title: "Account Created Successfully!",
        description: "Please check your email inbox for a confirmation link to activate your account.",
        duration: 7000, // Give user more time to read
      });

      // Optionally redirect to the sign-in page after showing the message
      setTimeout(() => {
         router.push("/auth/sign-in"); // Redirect to login page
      }, 2000); // Short delay after toast

      // Reset form fields after successful submission
      form.reset();

    } catch (error: any) {
      // Show error toast notification
      toast({
        title: "Sign Up Failed",
        description: error.message || "An unexpected error occurred. Please try again.",
        variant: "destructive",
      });
    } finally {
      // Ensure loading state is turned off regardless of success or failure
      setIsLoading(false);
    }
  }

  // --- Handler for Google OAuth Sign Up/Sign In ---
  async function signUpWithGoogle() {
    setIsLoading(true); // Set loading state

    try {
      // Initiate the Google OAuth flow
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback`, // Redirect URL after Google auth
        },
      });

      // Throw an error if initiation fails
      if (error) {
        console.error("Google OAuth initiation error:", error); // Log error
        throw error;
      }

      // On successful initiation, browser redirects to Google.

    } catch (error: any) {
      // Show error toast if initiation fails
      toast({
        title: "Google Sign-Up Failed",
        description: error.message || "Could not initiate Google sign-up. Please try again.",
        variant: "destructive",
      });
      setIsLoading(false); // Set loading back to false only if initiation fails
    }
    // Do not set loading to false on success, user is leaving page
  }

  // --- Render the Form ---
  return (
    <div className="grid gap-6">
      {/* Email/Password Sign Up Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input type="email" placeholder="you@example.com" {...field} />
                </FormControl>
                <FormMessage /> {/* Displays Zod validation errors */}
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                 {/* *** FIXED THIS LINE *** */}
                <FormLabel>Password</FormLabel>
                {/* *** END FIX *** */}
                <FormControl>
                  <Input type="password" placeholder="••••••••" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="confirmPassword"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Confirm Password</FormLabel>
                <FormControl>
                  <Input type="password" placeholder="••••••••" {...field} />
                </FormControl>
                <FormMessage /> {/* Displays Zod refine error if passwords don't match */}
              </FormItem>
            )}
          />
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Creating Account..." : "Create Account"}
          </Button>
        </form>
      </Form>

      {/* Separator */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">
            Or continue with
          </span>
        </div>
      </div>

      {/* Google Sign Up/Sign In Button */}
      <Button
        variant="outline"
        type="button"
        onClick={signUpWithGoogle} // Function to trigger Google OAuth
        disabled={isLoading} // Disable while any signup process is running
        className="w-full"
      >
        {/* Consider adding an icon */}
        Google
      </Button>
    </div>
  );
}