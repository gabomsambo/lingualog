import { createClient } from '@supabase/supabase-js'
import type { Entry } from "@/types/entry"

// Supabase client setup
const supabaseUrl = 'https://plspwcusgvfaghiskuyc.supabase.co'
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBsc3B3Y3VzZ3ZmYWdoaXNrdXljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY1MjQ0OTYsImV4cCI6MjA2MjEwMDQ5Nn0.iJcMz6Gw6N9Iob4_6LQ9Da7O7MsqbUaEp-sLIQnxGSM'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Log to confirm client is initialized
console.log('Supabase client initialized with URL:', supabaseUrl)

// Test Supabase connection
async function testSupabaseConnection() {
  try {
    const { data, error } = await supabase.from('users').select('count').limit(1)
    if (error) {
      console.error('Error connecting to Supabase:', error)
    } else {
      console.log('Successfully connected to Supabase')
    }
  } catch (e) {
    console.error('Exception connecting to Supabase:', e)
  }
}

// Run the test when in browser environment
if (typeof window !== 'undefined') {
  testSupabaseConnection()
}

// Mock entries data for development - properly formatted for the new Entry type
const mockEntries: Entry[] = [
  {
    id: "1",
    original_text: "今日は友達と日本のレストランに行きました。私たちは寿司とラーメンを食べました。とても美味しかったです！",
    corrected: "今日は友達と日本のレストランに行きました。私たちは寿司とラーメンを食べました。とても美味しかったです！",
    rewrite: "今日は友達と日本のレストランに行きました。私たちは寿司とラーメンを食べました。とても美味しかったです！ (more natural)",
    score: 85,
    tone: "Reflective",
    translation: "Today I went to a Japanese restaurant with my friends. We ate sushi and ramen. It was very delicious!",
    created_at: "2025-04-21T14:30:00Z"
  },
  {
    id: "2",
    original_text: "Ayer fui al parque con mis amigos. Jugamos al fútbol y comimos helado. Fue un día muy divertido.",
    corrected: "Ayer fui al parque con mis amigos. Jugamos al fútbol y comimos helado. Fue un día muy divertido.",
    rewrite: "Ayer fui al parque con mis amigos. Jugamos al fútbol y comimos helado. Fue un día muy divertido. (more natural)",
    score: 90,
    tone: "Confident",
    translation: "Yesterday I went to the park with my friends. We played soccer and ate ice cream. It was a very fun day.",
    created_at: "2025-04-18T09:15:00Z"
  }
]

/**
 * Get a single entry by ID
 * In a real app, this would fetch from Supabase
 */
export async function getEntryById(id: string): Promise<Entry | null> {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 1000))

  // In a real app, this would be:
  // const { data, error } = await supabase.from('entries').select('*').eq('id', id).single()
  // if (error) throw error
  // return data

  const entry = mockEntries.find((entry) => entry.id === id)
  return entry || null
}

/**
 * Update an entry
 * In a real app, this would update in Supabase
 */
export async function updateEntry(id: string, updates: Partial<Entry>): Promise<Entry> {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 1000))

  // In a real app, this would be:
  // const { data, error } = await supabase.from('entries').update(updates).eq('id', id).single()
  // if (error) throw error
  // return data

  const entryIndex = mockEntries.findIndex((entry) => entry.id === id)
  if (entryIndex === -1) throw new Error("Entry not found")

  const updatedEntry = { ...mockEntries[entryIndex], ...updates }
  mockEntries[entryIndex] = updatedEntry

  return updatedEntry
} 