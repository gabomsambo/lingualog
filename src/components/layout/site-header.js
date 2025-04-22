// src/components/layout/site-header.js
"use client"; // Required for hooks like usePathname, useRouter, useState and event handlers

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import * as React from "react"; // Import React if using state like [isLoading]
import { Book, LayoutDashboard, LogOut, PenLine, BookOpen, BarChart2 } from "lucide-react"; // Added BarChart2 for Stats

// --- Updated Supabase Client Import ---
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

// --- UI Imports ---
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/use-toast"; // Assuming use-toast is setup

export function SiteHeader() {
  const pathname = usePathname(); // Hook to get the current URL path
  const router = useRouter(); // Hook for programmatic navigation
  // --- Use the correct browser client ---
  const supabase = createSupabaseBrowserClient(); // Initialize Supabase client
  const [isSigningOut, setIsSigningOut] = React.useState(false); // Optional: Loading state for sign out

  // --- Sign Out Handler ---
  async function handleSignOut() {
    setIsSigningOut(true); // Set loading state true

    try {
      // Attempt to sign out the user
      const { error } = await supabase.auth.signOut();

      // Handle potential errors during sign out
      if (error) {
        console.error("Error signing out:", error);
        toast({
          title: "Error Signing Out",
          description: error.message || "An unexpected error occurred.",
          variant: "destructive",
        });
        setIsSigningOut(false); // Reset loading state on error
        return; // Stop execution if sign out failed
      }

      // Sign out successful
      toast({
          title: "Signed Out",
          description: "You have been successfully signed out.",
      });

      // Redirect to the sign-in page after successful sign out
      // Ensure this path matches your actual sign-in page route
      router.push('/auth/sign-in'); // Corrected path

      // Force a refresh of the current route. Good practice after auth changes
      // to ensure layout/data reflects the new auth state.
      router.refresh();

    } catch (err) {
      // Catch any unexpected errors during the process
      console.error("Unexpected error during sign out:", err);
      toast({
        title: "Error Signing Out",
        description: "An unexpected error occurred.",
        variant: "destructive",
      });
      setIsSigningOut(false); // Reset loading state on unexpected error
    }
    // Note: No need for finally block to set loading false if success causes navigation
  }

  // --- Navigation Links Definition ---
  // Define links for cleaner mapping in the JSX
  const navLinks = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/entries/new", label: "New Entry", icon: PenLine }, // Adjust path if needed
    { href: "/vocabulary", label: "Vocabulary", icon: BookOpen }, // Adjust path if needed
    { href: "/stats", label: "Stats", icon: BarChart2 }, // Adjust path and icon if needed
  ];


  // --- Render Component ---
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between"> {/* Adjusted height/padding if needed */}

        {/* Left Section: Logo and Main Navigation (Desktop) */}
        <div className="flex items-center gap-6"> {/* Added gap */}
          {/* Logo/Brand Link */}
          <Link href="/dashboard" className="flex items-center gap-2 mr-4"> {/* Added gap and margin */}
            <Book className="h-6 w-6" /> {/* LinguaLog icon */}
            <span className="text-lg font-semibold hidden sm:inline-block"> {/* Hide text on small screens */}
              LinguaLog
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden items-center gap-4 md:flex lg:gap-6"> {/* Adjusted gaps */}
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                // Apply dynamic classes for active link styling
                className={`text-sm font-medium transition-colors hover:text-primary ${
                  pathname === link.href
                    ? 'text-primary font-semibold' // Active link style
                    : 'text-muted-foreground hover:text-foreground/80' // Inactive link style
                }`}
              >
                {/* Optional: Include icons in desktop nav if desired */}
                {/* <link.icon className="h-4 w-4 mr-1" /> */}
                {link.label}
              </Link>
            ))}
          </nav>
        </div>

         {/* Optional: Mobile Navigation (Hamburger Menu) would go here */}
         {/* <div className="md:hidden"> Mobile Menu Button </div> */}

        {/* Right Section: Sign Out Button */}
        <div className="flex items-center">
          <Button
            variant="ghost" // Subtle button style
            size="sm"
            onClick={handleSignOut}
            disabled={isSigningOut} // Disable button while signing out
          >
            <LogOut className="mr-2 h-4 w-4" /> {/* Sign out icon */}
            {isSigningOut ? "Signing Out..." : "Sign Out"}
          </Button>
          {/* Optional: Theme Toggle or User Profile Dropdown could go here */}
        </div>
      </div>
    </header>
  );
}