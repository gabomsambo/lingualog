// src/app/entries/[id]/page.tsx
"use client"; // Required for useEffect, useState

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation'; // Hook to get dynamic route parameters
import Link from 'next/link';
import { format } from 'date-fns';

// UI Imports (adjust as needed)
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';

// Define the shape of a full entry
interface Entry {
  id: string;
  title: string;
  content: string;
  language: string;
  corrected_content?: string | null; // Optional fields
  vocab_extracted?: boolean;
  created_at: string;
  user_id: string;
}

export default function EntryDetailPage() {
  const params = useParams(); // Get route parameters { id: '...' }
  const entryId = params?.id as string; // Extract the id, assert as string

  const [entry, setEntry] = useState<Entry | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Define using const and arrow function expression
    const fetchEntryDetail = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/entries/${entryId}`);
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || `Entry not found or unauthorized (Status: ${response.status})`);
        }
        const data = await response.json();
        if (!data.entry) {
           throw new Error("Entry data not found in API response.");
        }
        setEntry(data.entry);
      } catch (err: any) {
        console.error("Failed to fetch entry detail:", err);
        setError(err.message);
        setEntry(null);
      } finally {
        setIsLoading(false);
      }
    };

    if (entryId) {
      fetchEntryDetail(); // Call the function expression
    } else {
      setError("Entry ID is missing.");
      setIsLoading(false);
    }
  }, [entryId]);
  // --- Render Loading State ---
  if (isLoading) {
    return (
      <div className="container mx-auto max-w-3xl py-8 px-4">
        <Skeleton className="h-8 w-3/4 mb-2" />
        <Skeleton className="h-4 w-1/2 mb-6" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  // --- Render Error State ---
  if (error) {
    return (
      <div className="container mx-auto max-w-3xl py-8 px-4 text-center text-destructive">
        <p>Error loading entry:</p>
        <p>{error}</p>
        <Button variant="link" asChild className='mt-4'>
           <Link href="/dashboard"><ArrowLeft className="mr-2 h-4 w-4" /> Back to Dashboard</Link>
        </Button>
      </div>
    );
  }

  // --- Render Not Found State (if entry is null after loading without error) ---
   if (!entry) {
     return (
       <div className="container mx-auto max-w-3xl py-8 px-4 text-center text-muted-foreground">
         <p>Entry not found.</p>
          <Button variant="link" asChild className='mt-4'>
             <Link href="/dashboard"><ArrowLeft className="mr-2 h-4 w-4" /> Back to Dashboard</Link>
          </Button>
       </div>
     );
   }

  // --- Render Entry Details ---
  return (
    <div className="container mx-auto max-w-3xl py-8 px-4">
       <Button variant="outline" size="sm" asChild className='mb-6'>
         <Link href="/dashboard">
           <ArrowLeft className="mr-2 h-4 w-4" /> Back to Dashboard
         </Link>
       </Button>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">{entry.title}</CardTitle>
          <CardDescription>
            Language: {entry.language} | Created: {format(new Date(entry.created_at), 'PPP p')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Use whitespace-pre-wrap to preserve line breaks */}
          <div className="prose dark:prose-invert max-w-none">
             <p className="whitespace-pre-wrap">{entry.content}</p>
          </div>

          {/* TODO: Add sections for corrected_content, vocabulary etc. later */}
           {entry.corrected_content && (
              <div className="mt-6 pt-4 border-t">
                 <h3 className="font-semibold mb-2">Corrected Content (AI Suggestion):</h3>
                 <p className="whitespace-pre-wrap text-muted-foreground">{entry.corrected_content}</p>
              </div>
           )}
        </CardContent>
         {/* Optional: Add Edit/Delete buttons here */}
      </Card>
    </div>
  );
}