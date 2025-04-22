// src/components/auth/sign-in-form.tsx
"use client";

import * as React from "react";
import { useState } from "react";
// Keep useRouter if needed for other potential future navigation, but not for the post-login redirect
// import { useRouter } from "next/navigation";
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
const formSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email address." }), // Added custom message
  password: z.string().min(6, { message: "Password must be at least 6 characters." }), // Added custom message
});

// --- Component Definition ---
export function SignInForm() {
  // const router = useRouter(); // Keep if needed later
  const [isLoading, setIsLoading] = useState(false);
  // --- Use the correct browser client ---
  const supabase = createSupabaseBrowserClient();

  // Initialize the form using react-hook-form
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  // --- Handler for Email/Password Sign In ---
  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsLoading(true); // Set loading state

    try {
      // Attempt to sign in with Supabase auth
      const { data, error } = await supabase.auth.signInWithPassword({
        email: values.email,
        password: values.password,
      });

      // Throw an error if Supabase returns one
      if (error) {
        console.error("Sign-in error:", error); // Log the error for debugging
        throw error;
      }

      // Show success toast notification
      toast({
        title: "Sign In Successful",
        description: "Redirecting to your dashboard...",
      });

      // Use a timeout and hard redirect. This is often more reliable for ensuring
      // the cookie/session state is fully updated and recognized by middleware
      // compared to Next.js router pushes immediately after auth changes.
      setTimeout(() => {
        window.location.href = "/dashboard"; // Adjust if your dashboard path is different
      }, 800); // Delay in milliseconds (adjust if needed)

      // Note: We don't set isLoading back to false here on success because the page will navigate away.

    } catch (error: any) {
      // Show error toast notification
      toast({
        title: "Sign In Failed",
        description: error.message || "An unexpected error occurred. Please try again.",
        variant: "destructive",
      });
      setIsLoading(false); // Set loading back to false only on error
    }
    // Do not use 'finally' to set isLoading to false if success leads to navigation.
  }

  // --- Handler for Google OAuth Sign In ---
  async function signInWithGoogle() {
    setIsLoading(true); // Set loading state

    try {
      // Initiate the Google OAuth flow
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          // The URL Supabase redirects back to after Google authentication.
          // Ensure you have a handler at this route (e.g., /auth/callback) if needed
          // to exchange the code for a session, although Supabase often handles this.
          redirectTo: `${window.location.origin}/auth/callback`, // Adjust if necessary
        },
      });

      // Throw an error if initiation fails
      if (error) {
        console.error("Google OAuth initiation error:", error); // Log error
        throw error;
      }

      // On successful initiation, the browser redirects to Google.
      // No further client-side action is needed here immediately.
      // Do not set isLoading back to false here, as the user is leaving the page.

    } catch (error: any) {
      // Show error toast notification if initiation fails
      toast({
        title: "Google Sign-In Failed",
        description: error.message || "Could not initiate Google sign-in. Please try again.",
        variant: "destructive",
      });
      setIsLoading(false); // Set loading back to false only if initiation fails
    }
  }

  // --- Render the Form ---
  return (
    <div className="grid gap-6">
      {/* Email/Password Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input type="email" placeholder="your@email.com" {...field} />
                </FormControl>
                <FormMessage /> {/* Shows validation errors */}
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Password</FormLabel>
                <FormControl>
                  <Input type="password" placeholder="••••••••" {...field} />
                </FormControl>
                <FormMessage /> {/* Shows validation errors */}
              </FormItem>
            )}
          />
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Signing In..." : "Sign In"}
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

      {/* Google Sign-In Button */}
      <Button
        variant="outline"
        type="button"
        onClick={signInWithGoogle}
        disabled={isLoading} // Disable while any sign-in process is running
        className="w-full"
      >
        {/* Consider adding an icon */}
        Google
      </Button>
    </div>
  );
}