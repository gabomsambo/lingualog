// src/components/entries/new-entry-form.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "@/components/ui/use-toast"; // Assuming use-toast is setup

// --- Zod Schema Definition ---
const formSchema = z.object({
  title: z.string()
    .min(2, { message: "Title must be at least 2 characters." })
    .max(150, { message: "Title must not exceed 150 characters." }), // Increased max length slightly
  content: z.string()
    .min(10, { message: "Content must be at least 10 characters." }),
  language: z.string()
    .min(1, { message: "Please select the language you are writing in." }), // Changed message slightly
});

// --- Language Options ---
// Consider fetching these from a constants file or API later if needed
const languageOptions = [
  { value: "arabic", label: "Arabic" },
  { value: "chinese", label: "Chinese" },
  { value: "french", label: "French" },
  { value: "german", label: "German" },
  { value: "italian", label: "Italian" },
  { value: "japanese", label: "Japanese" },
  { value: "korean", label: "Korean" },
  { value: "portuguese", label: "Portuguese" },
  { value: "russian", label: "Russian" },
  { value: "spanish", label: "Spanish" },
  // Add more languages as needed
  { value: "english", label: "English" }, // Added English as an option
  { value: "other", label: "Other" },
];

// --- Component Definition ---
export function NewEntryForm() {
  const router = useRouter(); // Hook for navigation
  const [isLoading, setIsLoading] = useState(false); // State for loading indicators
  const [isFeedbackLoading, setIsFeedbackLoading] = useState(false); // Separate loading state for feedback
  // --- Use the correct browser client ---
  const supabase = createSupabaseBrowserClient(); // Initialize Supabase

  // Initialize react-hook-form
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema), // Use Zod for validation
    defaultValues: {
      title: "",
      content: "",
      language: "", // Start with no language selected
    },
  });

  // --- Handler for Submitting the New Entry ---
  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsLoading(true); // Indicate loading state

    try {
      // 1. Get the current user session
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      // Handle error or missing session
      if (sessionError || !session?.user) {
        console.error("Session Error:", sessionError?.message);
        toast({ title: "Authentication Error", description: "You must be logged in to create an entry.", variant: "destructive" });
        setIsLoading(false); // Stop loading
        // Optionally redirect to login
        // router.push('/auth/sign-in');
        return; // Stop submission
      }

      // 2. Insert the new entry into the Supabase table
      const userId = session.user.id;
      const { error: insertError } = await supabase
        .from("entries") // Ensure 'entries' matches your table name
        .insert({
          title: values.title,
          content: values.content,
          language: values.language,
          user_id: userId, // Associate entry with the logged-in user
          // corrected_content: null, // Ensure defaults are set if needed
          // vocab_extracted: false,
        });

      // Handle insertion errors
      if (insertError) {
        console.error("Insert Error:", insertError);
        throw insertError; // Propagate error to the catch block
      }

      // 3. Show success toast
      toast({
        title: "Entry Saved!",
        description: "Your journal entry has been successfully saved.",
      });

      // 4. Redirect to the dashboard after successful save
      router.push("/dashboard"); // Ensure this path is correct
      router.refresh(); // Refresh dashboard data

    } catch (error: any) {
      // Show error toast if any step fails
      toast({
        title: "Failed to Save Entry",
        description: error.message || "An unexpected error occurred. Please try again.",
        variant: "destructive",
      });
      setIsLoading(false); // Stop loading on error
    }
    // Note: No finally block needed to set isLoading false if success causes navigation
  }

  // --- Handler for Requesting Grammar Feedback ---
  async function requestGrammarFeedback() {
    // Get current form values without triggering full validation/submission
    const values = form.getValues();

    // Basic client-side checks before calling API
    if (!values.content || values.content.trim().length < 10) {
      toast({ title: "Cannot Get Feedback", description: "Please write at least 10 characters in the content field.", variant: "destructive" });
      return;
    }
    if (!values.language) {
      toast({ title: "Cannot Get Feedback", description: "Please select the language of your entry first.", variant: "destructive" });
      return;
    }

    setIsFeedbackLoading(true); // Use separate loading state for feedback button

    try {
      // Call your internal API endpoint for grammar checking
      const response = await fetch("/api/grammar", { // Ensure this API route exists
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: values.content,
          language: values.language,
          // Optionally pass entry ID if needed by the API
        }),
      });

      // Check if the API call was successful
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: "Unknown API error" }));
        console.error("API Error:", response.status, errorData);
        throw new Error(errorData.message || `Failed to get grammar feedback (Status: ${response.status})`);
      }

      // Process the successful response
      const data = await response.json(); // Assuming API returns JSON with feedback

      toast({
        title: "Grammar Feedback Received",
        description: "Suggestions processed (check console or UI for details).", // Adjust message
      });

      // TODO: Implement how feedback is displayed or applied
      // Example: Update form state, show a modal, etc.
      console.log("Grammar feedback data:", data);
      // Example: Maybe update a state variable holding corrections
      // setCorrections(data.corrections);

    } catch (error: any) {
      // Show error toast if feedback request fails
      toast({
        title: "Feedback Error",
        description: error.message || "Failed to get grammar feedback. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsFeedbackLoading(false); // Turn off feedback loading indicator
    }
  }

  // --- Render the Form ---
  return (
    <Form {...form}>
      {/* Pass form control to the form component */}
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">

        {/* Title Field */}
        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Entry Title</FormLabel>
              <FormControl>
                <Input placeholder="e.g., Practicing past tense" {...field} />
              </FormControl>
              <FormDescription>A short title for your journal entry.</FormDescription>
              <FormMessage /> {/* Displays validation errors */}
            </FormItem>
          )}
        />

        {/* Language Selection Field */}
        <FormField
          control={form.control}
          name="language"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Language</FormLabel>
              {/* Use shadcn/ui Select component */}
              <Select
                onValueChange={field.onChange} // Update form state on change
                defaultValue={field.value} // Control the selected value
                value={field.value} // Ensure value is explicitly set for controlled component
              >
                <FormControl>
                  <SelectTrigger>
                    {/* Display placeholder if no value is selected */}
                    <SelectValue placeholder="Select the language you wrote in" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {/* Map over language options to create SelectItems */}
                  {languageOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormDescription>
                Choose the language you are practicing in this entry.
              </FormDescription>
              <FormMessage /> {/* Displays validation errors */}
            </FormItem>
          )}
        />

        {/* Content Textarea Field */}
        <FormField
          control={form.control}
          name="content"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Journal Content</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Write your thoughts, practice phrases, or document what you learned today..."
                  className="min-h-[250px] resize-y" // Allow vertical resize
                  {...field} // Spread field props (onChange, onBlur, value, ref)
                />
              </FormControl>
              <FormDescription>Write as much as you like in your target language.</FormDescription>
              <FormMessage /> {/* Displays validation errors */}
            </FormItem>
          )}
        />

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-4 pt-2"> {/* Added padding top */}
          <Button type="submit" disabled={isLoading || isFeedbackLoading}>
            {/* Show loading text if saving */}
            {isLoading ? "Saving Entry..." : "Save Entry"}
          </Button>
          <Button
            type="button" // Important: Prevent form submission
            variant="outline"
            onClick={requestGrammarFeedback}
            disabled={isLoading || isFeedbackLoading} // Disable if saving or getting feedback
          >
            {/* Show loading text if getting feedback */}
            {isFeedbackLoading ? "Getting Feedback..." : "Get Grammar Feedback"}
          </Button>
        </div>
      </form>
    </Form>
  );
}