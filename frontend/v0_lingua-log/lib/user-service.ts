import { supabase } from './supabase';
import { getUser } from './auth';

export interface UserStats {
  wordCount: number;
  weeklyIncrease: number;
  languages: string[];
  languageEmojis: string[];
  streak: number;
}

export interface UserProfile {
  id: string;
  email: string;
  username: string | null;
  created_at: string;
}

export interface UserEntry {
  id: string;
  title: string;
  language: string;
  languageEmoji: string;
  date: string;
  excerpt: string;
}

// Language emoji mapping
const languageEmojis: Record<string, string> = {
  'Spanish': '🇪🇸',
  'French': '🇫🇷',
  'German': '🇩🇪',
  'Japanese': '🇯🇵',
  'English': '🇬🇧',
  'Italian': '🇮🇹',
  'Portuguese': '🇵🇹',
  'Russian': '🇷🇺',
  'Chinese': '🇨🇳',
  'Korean': '🇰🇷',
};

/**
 * Get the current user's profile
 */
export async function getUserProfile(): Promise<UserProfile | null> {
  try {
    const user = await getUser();
    if (!user) return null;

    // Get user profile from the users table
    const { data, error } = await supabase
      .from('users')
      .select('*')
      .eq('id', user.id)
      .single();

    if (error) throw error;
    
    return {
      id: user.id,
      email: user.email || '',
      username: data?.username || user.user_metadata?.username || null,
      created_at: data?.created_at || user.created_at,
    };
  } catch (error) {
    console.error('Error fetching user profile:', error);
    return null;
  }
}

/**
 * Get the user's entries
 */
export async function getUserEntries(limit = 3): Promise<UserEntry[]> {
  try {
    const user = await getUser();
    if (!user) return [];

    // Fetch entries from the journal_entries table
    const { data, error } = await supabase
      .from('journal_entries')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })
      .limit(limit);

    if (error) {
      console.error('Error fetching entries:', error);
      return [];
    }

    if (!data || data.length === 0) {
      return [];
    }

    // Transform the data to match UserEntry interface
    return data.map(entry => ({
      id: entry.id,
      title: entry.original_text.substring(0, 30) + (entry.original_text.length > 30 ? '...' : ''),
      language: entry.tone || 'Other', // Using tone as language for now
      languageEmoji: languageEmojis[entry.tone] || '📝',
      date: entry.created_at,
      excerpt: entry.original_text.substring(0, 100) + (entry.original_text.length > 100 ? '...' : ''),
    }));
  } catch (error) {
    console.error('Error fetching user entries:', error);
    return [];
  }
}

/**
 * Get the user's stats
 */
export async function getUserStats(): Promise<UserStats | null> {
  try {
    const user = await getUser();
    if (!user) return null;

    // Fetch all entries to calculate stats
    const { data, error } = await supabase
      .from('journal_entries')
      .select('*')
      .eq('user_id', user.id);

    if (error) {
      console.error('Error fetching entries for stats:', error);
      return null;
    }

    if (!data || data.length === 0) {
      // Return default stats for new users
      return {
        wordCount: 0,
        weeklyIncrease: 0,
        languages: [],
        languageEmojis: [],
        streak: 0,
      };
    }

    // Calculate total word count from all entries
    const wordCount = data.reduce((total, entry) => {
      return total + (entry.original_text ? entry.original_text.split(/\s+/).length : 0);
    }, 0);

    // Get entries from the last 7 days
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
    
    const recentEntries = data.filter(entry => {
      const entryDate = new Date(entry.created_at);
      return entryDate >= oneWeekAgo;
    });

    // Calculate word count from the last 7 days
    const weeklyIncrease = recentEntries.reduce((total, entry) => {
      return total + (entry.original_text ? entry.original_text.split(/\s+/).length : 0);
    }, 0);

    // Extract unique tones (using as languages for now)
    const uniqueTones = Array.from(new Set(data.map(entry => entry.tone || 'Other')));
    const languages = uniqueTones.filter(tone => tone !== null && tone !== undefined);

    // Map tones to emojis
    const languageEmojisList = languages.map(lang => languageEmojis[lang as keyof typeof languageEmojis] || '📝');

    // Calculate streak (consecutive days with entries)
    const streak = calculateStreak(data);

    return {
      wordCount,
      weeklyIncrease,
      languages,
      languageEmojis: languageEmojisList,
      streak,
    };
  } catch (error) {
    console.error('Error fetching user stats:', error);
    return null;
  }
}

/**
 * Calculate the user's streak (consecutive days with entries)
 */
function calculateStreak(entries: any[]): number {
  if (!entries || entries.length === 0) return 0;

  // Sort entries by date (newest first)
  const sortedEntries = [...entries].sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  // Get today's date (without time)
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Check if there's an entry for today
  const latestEntryDate = new Date(sortedEntries[0].created_at);
  latestEntryDate.setHours(0, 0, 0, 0);
  
  // If the latest entry is not from today, check if it's from yesterday
  if (latestEntryDate.getTime() !== today.getTime()) {
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    // If the latest entry is not from yesterday either, streak is 0
    if (latestEntryDate.getTime() !== yesterday.getTime()) {
      return 0;
    }
  }

  // Count consecutive days with entries
  let streak = 1; // Start with 1 for the most recent day
  let currentDate = new Date(latestEntryDate);
  
  // Group entries by date (using date string as key)
  const entriesByDate: Record<string, boolean> = {};
  for (const entry of entries) {
    const date = new Date(entry.created_at);
    date.setHours(0, 0, 0, 0);
    entriesByDate[date.toISOString().split('T')[0]] = true;
  }
  
  // Count back from the latest entry date
  while (true) {
    // Move to the previous day
    currentDate.setDate(currentDate.getDate() - 1);
    const dateStr = currentDate.toISOString().split('T')[0];
    
    // If there's an entry for this date, increment streak
    if (entriesByDate[dateStr]) {
      streak++;
    } else {
      // Break the streak when a day is missed
      break;
    }
  }
  
  return streak;
} 