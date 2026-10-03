import { Entry } from "@/types/entry";
import { getAuthHeaders, getUser } from "./auth";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL;

if (!API_BASE) {
  throw new Error("Missing NEXT_PUBLIC_API_URL environment variable.");
}

export interface JournalEntryOverrides {
  target_language?: string;
  ui_language?: string;
  explanation_mode?: string;
  strictness?: string;
  formality?: string;
  immersion_level?: number;
}

export async function postLogEntry(
  text: string, 
  title: string, 
  language: string, 
  overrides?: JournalEntryOverrides
) {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();

  const customHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(authHeaders as Record<string, string>)
  };

  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }
  
  // Build request body with overrides
  const requestBody = {
    text,
    title,
    language,
    ...(overrides || {})
  };
  
  const res = await fetch(`${API_BASE}/log-entry`, {
    method: "POST",
    headers: customHeaders,
    body: JSON.stringify(requestBody),
    credentials: "include",
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as Entry;
}

export async function getEntries(language?: string) {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();

  const customHeaders: Record<string, string> = {
    ...(authHeaders as Record<string, string>)
  };

  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }

  // Build URL with optional language query parameter
  const url = new URL(`${API_BASE}/entries`);
  if (language) {
    url.searchParams.append('language', language);
  }

  const res = await fetch(url.toString(), {
    method: "GET",
    credentials: "include",
    headers: customHeaders as HeadersInit
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as Entry[];
}

// Mock functions for backward compatibility
// export function getEntryById(id: string): Promise<Entry | null> { // Comment out old mock
//   return Promise.resolve(null);
// }

export async function getEntryById(id: string): Promise<Entry | null> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();

  const customHeaders: Record<string, string> = {
    ...(authHeaders as Record<string, string>)
  };

  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id; 
  }

  // Add a cache-busting query parameter
  const cacheBust = `_cb=${new Date().getTime()}`;
  const url = `${API_BASE}/entries/${id}?${cacheBust}`;
  console.log(`Fetching entry by ID from URL: ${url}`); // Changed to console.log

  const res = await fetch(url, { 
    method: "GET",
    headers: customHeaders,
    credentials: "include",
    // Explicitly disable caching for this fetch call if possible (depends on browser/fetch spec)
    cache: "no-store", // Standard way to prevent caching
  });

  if (!res.ok) {
    if (res.status === 404) {
      return null; // Entry not found
    }
    throw new Error(await res.text());
  }
  return (await res.json()) as Entry;
}

export function updateEntry(id: string, updates: Partial<Entry>): Promise<Entry> {
  return Promise.resolve(updates as Entry);
}

export async function deleteEntry(entryId: string): Promise<void> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();

  const customHeaders: Record<string, string> = {
    ...(authHeaders as Record<string, string>),
  };

  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }

  const res = await fetch(`${API_BASE}/entries/${entryId}`, {
    method: "DELETE",
    headers: customHeaders,
    credentials: "include",
  });

  if (!res.ok) {
    // Try to parse error message from backend if available
    let errorDetail = `Failed to delete entry. Status: ${res.status}`;
    try {
      const errorData = await res.json();
      if (errorData && errorData.detail) {
        errorDetail = errorData.detail;
      }
    } catch (e) {
      // Ignore if response is not JSON or other parsing error
    }
    throw new Error(errorDetail);
  }
  // DELETE requests typically return 204 No Content on success, so no JSON body to parse.
}

// --- Vocabulary API Functions ---

// Simplified frontend types based on backend Pydantic models
export interface UserVocabularyItemCreate {
  term: string;
  language: string;
  part_of_speech?: string;
  definition?: string;
  reading?: string;
  example_sentence?: string;
  status?: string;
  entry_id?: string; 
  
  // AI Enrichment fields
  ai_example_sentences?: string[];
  ai_definitions?: any[];
  ai_synonyms?: string[];
  ai_antonyms?: string[];
  ai_related_phrases?: string[];
  ai_conjugation_info?: any;
  ai_cultural_note?: string;
  ai_pronunciation_guide?: string;
  ai_alternative_forms?: string[];
  ai_common_mistakes?: Array<{ mistake: string; correction: string; explanation?: string }>;
  ai_eli5_explanation?: string;
  emotion_tone?: string;
  mnemonic?: string;
  emoji?: string;
  source_model?: string;
  notes_user?: string;
  tags?: string[];
}

export interface UserVocabularyItemResponse extends UserVocabularyItemCreate {
  id: string; // UUID from DB
  user_id: string; // UUID from DB
  created_at: string; // ISO date string
  updated_at: string; // ISO date string
}

export async function addVocabularyItem(item: UserVocabularyItemCreate): Promise<UserVocabularyItemResponse> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  const customHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(authHeaders as Record<string, string>),
  };
  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }

  const res = await fetch(`${API_BASE}/vocabulary`, {
    method: "POST",
    headers: customHeaders,
    body: JSON.stringify(item),
    credentials: "include",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: `Failed to add vocabulary item. Status: ${res.status}` }));
    throw new Error(errorData.detail || `Failed to add vocabulary item. Status: ${res.status}`);
  }
  return (await res.json()) as UserVocabularyItemResponse;
}

export async function getVocabularyItems(language?: string): Promise<UserVocabularyItemResponse[]> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  const customHeaders: Record<string, string> = {
    ...(authHeaders as Record<string, string>),
  };
  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }

  let url = `${API_BASE}/vocabulary`;
  if (language) {
    url += `?language=${encodeURIComponent(language)}`;
  }

  const res = await fetch(url, {
    method: "GET",
    headers: customHeaders,
    credentials: "include",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: `Failed to fetch vocabulary items. Status: ${res.status}` }));
    throw new Error(errorData.detail || `Failed to fetch vocabulary items. Status: ${res.status}`);
  }
  return (await res.json()) as UserVocabularyItemResponse[];
}

export async function deleteVocabularyItem(itemId: string): Promise<void> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  const customHeaders: Record<string, string> = {
    ...(authHeaders as Record<string, string>),
  };
  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }

  const res = await fetch(`${API_BASE}/vocabulary/${itemId}`, {
    method: "DELETE",
    headers: customHeaders,
    credentials: "include",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: `Failed to delete vocabulary item. Status: ${res.status}` }));
    throw new Error(errorData.detail || `Failed to delete vocabulary item. Status: ${res.status}`);
  }
  // No content expected on successful delete (204)
}

// --- Vocabulary AI On-Demand Generation --- 

// Request and Response types mirroring backend Pydantic models

export interface MoreExamplesRequest {
  word: string;
  language: string;
  existing_examples?: string[];
  target_audience_level?: string;
}

export interface MoreExamplesResponse {
  new_example_sentences: string[];
}

export interface ELI5Request {
  term: string;
  language: string;
  context?: string;
}

export interface ELI5Response {
  explanation: string;
}

export interface MiniQuizQuestion {
  question_text: string;
  options: string[];
  correct_answer_index: number;
  explanation?: string;
}

export interface MiniQuizRequest {
  word: string;
  language: string;
  num_questions?: number;
  difficulty?: string;
}

export interface MiniQuizResponse {
  quiz_title: string;
  questions: MiniQuizQuestion[];
}

// Interface for the /ai/vocabulary/{itemId}/enrich endpoint response
export interface EnrichedVocabDetails {
  id: string; // UUID for the AI cache entry
  word_vocabulary_id: string; // UUID for the vocabulary item this relates to
  language: string;
  ai_example_sentences?: string[];
  ai_definitions?: Array<{ part_of_speech: string; definition: string }>;
  ai_synonyms?: string[];
  ai_antonyms?: string[];
  ai_related_phrases?: string[];
  ai_conjugation_info?: Record<string, any>; // Conjugation information for verbs/adjectives
  ai_cultural_note?: string;
  ai_pronunciation_guide?: string;
  ai_alternative_forms?: string[];
  ai_common_mistakes?: Array<{ mistake: string; correction: string; explanation?: string }>;
  // New fields for comprehensive vocabulary enrichment
  emotion_tone?: string; // Emotional tone or feeling associated with the word
  mnemonic?: string; // Memory aid, metaphor, or mnemonic device
  emoji?: string; // Emoji representing the word's meaning or emotion
  source_model?: string;
  // Match this structure with VocabWordData where possible, or map it in the component
  // For example, VocabWordData uses 'eli5Explanation', this might come from one of these fields or be separate.
}

export async function getEnrichedVocabularyDetails(itemId: string, language: string): Promise<EnrichedVocabDetails> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  const customHeaders: Record<string, string> = {
    ...(authHeaders as Record<string, string>),
  };
  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }

  const res = await fetch(`${API_BASE}/ai/vocabulary/${itemId}/enrich?language=${language}`, {
    method: "GET",
    headers: customHeaders,
    credentials: "include",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: `Failed to fetch enriched details. Status: ${res.status}` }));
    throw new Error(errorData.detail || `Failed to fetch enriched details. Status: ${res.status}`);
  }
  return (await res.json()) as EnrichedVocabDetails;
}

export async function generateMoreExamples(request: MoreExamplesRequest): Promise<MoreExamplesResponse> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  const customHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(authHeaders as Record<string, string>),
  };
  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }

  const res = await fetch(`${API_BASE}/ai/vocabulary/on-demand/more-examples`, {
    method: "POST",
    headers: customHeaders,
    body: JSON.stringify(request),
    credentials: "include",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: `Failed to generate more examples. Status: ${res.status}` }));
    throw new Error(errorData.detail || `Failed to generate more examples. Status: ${res.status}`);
  }
  return (await res.json()) as MoreExamplesResponse;
}

export async function generateEli5(request: ELI5Request): Promise<ELI5Response> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  const customHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(authHeaders as Record<string, string>),
  };
  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }

  const res = await fetch(`${API_BASE}/ai/vocabulary/on-demand/eli5`, {
    method: "POST",
    headers: customHeaders,
    body: JSON.stringify(request),
    credentials: "include",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: `Failed to generate ELI5. Status: ${res.status}` }));
    throw new Error(errorData.detail || `Failed to generate ELI5. Status: ${res.status}`);
  }
  return (await res.json()) as ELI5Response;
}

export async function generateMiniQuiz(request: MiniQuizRequest): Promise<MiniQuizResponse> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  const customHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(authHeaders as Record<string, string>),
  };
  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }

  const res = await fetch(`${API_BASE}/ai/vocabulary/on-demand/mini-quiz`, {
    method: "POST",
    headers: customHeaders,
    body: JSON.stringify(request),
    credentials: "include",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: `Failed to generate mini quiz. Status: ${res.status}` }));
    throw new Error(errorData.detail || `Failed to generate mini quiz. Status: ${res.status}`);
  }
  return (await res.json()) as MiniQuizResponse;
}

// User Profile and Stats API

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserProfileUpdate {
  email?: string;
  full_name?: string;
}

export interface UserStats {
  wordCounts: Array<{
    date: string;
    count: number;
  }>;
  languageBreakdown: Array<{
    language: string;
    count: number;
  }>;
  streak: {
    current: number;
    longest: number;
    totalWords: number;
  };
}

export async function getUserProfile(): Promise<UserProfile> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  
  const customHeaders: Record<string, string> = {
    ...(authHeaders as Record<string, string>)
  };

  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }
  
  const res = await fetch(`${API_BASE}/user/profile`, {
    method: "GET",
    headers: customHeaders,
    credentials: "include",
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: `Failed to fetch profile. Status: ${res.status}` }));
    throw new Error(errorData.detail || `Failed to fetch profile. Status: ${res.status}`);
  }
  
  return (await res.json()) as UserProfile;
}

export async function updateUserProfile(updateData: UserProfileUpdate): Promise<UserProfile> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  
  const customHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(authHeaders as Record<string, string>)
  };

  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }
  
  const res = await fetch(`${API_BASE}/user/profile`, {
    method: "PUT",
    headers: customHeaders,
    body: JSON.stringify(updateData),
    credentials: "include",
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: `Failed to update profile. Status: ${res.status}` }));
    throw new Error(errorData.detail || `Failed to update profile. Status: ${res.status}`);
  }
  
  return (await res.json()) as UserProfile;
}

export async function getUserStats(): Promise<UserStats> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  
  const customHeaders: Record<string, string> = {
    ...(authHeaders as Record<string, string>)
  };

  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }
  
  const res = await fetch(`${API_BASE}/user/stats`, {
    method: "GET",
    headers: customHeaders,
    credentials: "include",
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: `Failed to fetch stats. Status: ${res.status}` }));
    throw new Error(errorData.detail || `Failed to fetch stats. Status: ${res.status}`);
  }
  
  return (await res.json()) as UserStats;
}

// User Settings API

export interface UserSettingsData {
  id: string;
  user_id: string;
  native_language: string;
  target_languages: string[];
  email_notifications: boolean;
  push_notifications: boolean;
  daily_reminders: boolean;
  weekly_progress: boolean;
  reminder_time: string;
  theme: string;
  app_language: string;
  sound_effects: boolean;
  animations: boolean;
  difficulty_level: string;
  daily_goal: number;
  weekly_goal: number;
  auto_save: boolean;
  show_hints: boolean;
  public_profile: boolean;
  share_progress: boolean;
  analytics_opt_in: boolean;
  created_at: string;
  updated_at: string;
  // New multilingual fields from migration
  interface_lang: string;
  native_lang: string;
  default_target_lang?: string;
  explanation_mode: string;
  immersion_level: number;
  strictness: string;
  formality: string;
}

export interface UserSettingsUpdate {
  native_language?: string;
  target_languages?: string[];
  email_notifications?: boolean;
  push_notifications?: boolean;
  daily_reminders?: boolean;
  weekly_progress?: boolean;
  reminder_time?: string;
  theme?: string;
  app_language?: string;
  sound_effects?: boolean;
  animations?: boolean;
  difficulty_level?: string;
  daily_goal?: number;
  weekly_goal?: number;
  auto_save?: boolean;
  show_hints?: boolean;
  public_profile?: boolean;
  share_progress?: boolean;
  analytics_opt_in?: boolean;
  // New multilingual fields from migration
  interface_lang?: string;
  native_lang?: string;
  default_target_lang?: string;
  explanation_mode?: string;
  immersion_level?: number;
  strictness?: string;
  formality?: string;
}

export async function getUserSettings(): Promise<UserSettingsData> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  
  const customHeaders: Record<string, string> = {
    ...(authHeaders as Record<string, string>)
  };

  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }
  
  const res = await fetch(`${API_BASE}/user/settings`, {
    method: "GET",
    headers: customHeaders,
    credentials: "include",
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: `Failed to fetch settings. Status: ${res.status}` }));
    throw new Error(errorData.detail || `Failed to fetch settings. Status: ${res.status}`);
  }
  
  return (await res.json()) as UserSettingsData;
}

export async function updateUserSettings(updateData: UserSettingsUpdate): Promise<UserSettingsData> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  
  const customHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(authHeaders as Record<string, string>)
  };

  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }
  
  const res = await fetch(`${API_BASE}/user/settings`, {
    method: "PUT",
    headers: customHeaders,
    body: JSON.stringify(updateData),
    credentials: "include",
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: `Failed to update settings. Status: ${res.status}` }));
    throw new Error(errorData.detail || `Failed to update settings. Status: ${res.status}`);
  }
  
  return (await res.json()) as UserSettingsData;
} 