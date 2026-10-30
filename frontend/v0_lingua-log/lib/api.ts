import { Entry } from "@/types/entry";
import { getAuthHeaders, getUser } from "./auth";
import type { LearningPolicySnapshot } from "./side-by-side";

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
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as Entry;
}

/** An API failure with its status and parsed `detail` (e.g. 503 `{code, entry_id, message}`). */
export class ApiError extends Error {
  status: number;
  detail: any;

  constructor(status: number, body: string, detail: any) {
    super(body);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function apiError(res: Response): Promise<ApiError> {
  const body = await res.text();
  let detail: any = null;
  try {
    detail = JSON.parse(body)?.detail ?? null;
  } catch {
    detail = null;
  }
  return new ApiError(res.status, body, detail);
}

async function userHeaders(json = false): Promise<Record<string, string>> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();
  const headers: Record<string, string> = {
    ...(json ? { "Content-Type": "application/json" } : {}),
    ...(authHeaders as Record<string, string>),
  };
  if (user?.id) {
    headers["X-User-ID"] = user.id;
  }
  return headers;
}

/** Re-run AI analysis for a saved entry (POST /entries/{id}/analyze). */
/** Retry analysis. With `targetLanguage`, re-analyse the entry as that studied language instead. */
export async function analyzeEntry(entryId: string, targetLanguage?: string): Promise<void> {
  const res = await fetch(`${API_BASE}/entries/${entryId}/analyze`, {
    method: "POST",
    headers: await userHeaders(true),
    credentials: "include",
    ...(targetLanguage ? { body: JSON.stringify({ target_language: targetLanguage }) } : {}),
  });
  if (!res.ok) throw await apiError(res);
}

/** The learner keeps the entry's language after a detected mismatch; stop asking. */
export async function keepEntryLanguage(entryId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/entries/${entryId}/keep-language`, {
    method: "POST",
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
}

/** The learner's current LearningPolicy for one language, for entries stored without a snapshot. */
export async function getCurrentPolicy(l2?: string): Promise<LearningPolicySnapshot> {
  const url = new URL(`${API_BASE}/user/policy`);
  if (l2) url.searchParams.append("l2", l2);
  const res = await fetch(url.toString(), {
    method: "GET",
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as LearningPolicySnapshot;
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

export interface EntryTranslationResult {
  part: string;
  target_lang: string;
  source_lang: string;
  sentences: string[];
  text: string;
  provider: string;
  status: "ok" | "unavailable" | string;
  provider_label?: string | null;
  cached?: boolean;
}

export async function translateEntryPart(
  entryId: string,
  part: string,
  targetLang: string,
): Promise<EntryTranslationResult> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();

  const customHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(authHeaders as Record<string, string>),
  };

  if (user?.id) {
    customHeaders["X-User-ID"] = user.id;
  }

  const res = await fetch(`${API_BASE}/entries/${entryId}/translate`, {
    method: "POST",
    headers: customHeaders,
    credentials: "include",
    body: JSON.stringify({ part, target_lang: targetLang }),
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }
  return (await res.json()) as EntryTranslationResult;
}

export type SupportEventKind =
  | "reveal_meaning"
  | "rescue_note"
  | "reveal_rewrite_gloss"
  | "reveal_example"
  | "reveal_gloss";

export interface LevelSuggestion {
  l2: string;
  direction: "down" | "up";
  from_level: number;
  to_level: number;
  snoozed_until?: string;
}

export async function getLevelSuggestions(): Promise<{ suggestions: LevelSuggestion[] }> {
  const res = await fetch(`${API_BASE}/user/level-suggestions`, {
    method: "GET",
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as { suggestions: LevelSuggestion[] };
}

export async function acceptLevelSuggestion(l2: string): Promise<LevelSuggestion> {
  const res = await fetch(`${API_BASE}/user/level-suggestions/${encodeURIComponent(l2)}/accept`, {
    method: "POST",
    headers: await userHeaders(true),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as LevelSuggestion;
}

export async function dismissLevelSuggestion(l2: string): Promise<LevelSuggestion> {
  const res = await fetch(`${API_BASE}/user/level-suggestions/${encodeURIComponent(l2)}/dismiss`, {
    method: "POST",
    headers: await userHeaders(true),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as LevelSuggestion;
}

export async function postSupportEvent(payload: {
  kind: SupportEventKind;
  entry_id?: string;
  immersion_level?: number;
  l2?: string;
}): Promise<void> {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();

  const customHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(authHeaders as Record<string, string>),
  };

  if (user?.id) {
    customHeaders["X-User-ID"] = user.id;
  }

  const res = await fetch(`${API_BASE}/events`, {
    method: "POST",
    headers: customHeaders,
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }
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
  status?: VocabularyStatus;
  entry_id?: string;
  encounter_id?: string;
}

export type VocabularyStatus = "new" | "learning" | "known" | "mastered" | "ignored";

export interface VocabularyOtherSense {
  meaning: string;
  example: string;
}

export interface VocabularyCardData {
  lemma: string;
  surface: string;
  is_phrase: boolean;
  part_of_speech: string;
  gender: string;
  sense_in_context: string;
  gloss_l1: string;
  other_senses: VocabularyOtherSense[];
  register: string;
  cefr: string;
  frequency_band: string;
  examples: string[];
  example_translations: string[];
  collocations: string[];
  word_family: string[];
  common_mistake: string;
  memory_hook: string;
}

export interface LookupResult {
  encounter_id: string;
  text: string;
  language: string;
  lemma: string;
  sense: string;
  card?: VocabularyCardData | null;
  card_status: "ok" | "failed";
  card_policy: VocabularyCardPolicy;
  seen_count: number;
  saved_item?: UserVocabularyItemResponse | null;
}

export async function lookupWord(payload: {
  text: string;
  sentence?: string;
  language: string;
  source: "entry" | "manual";
  source_id?: string;
  kind?: "lookup" | "entry_text" | "entry_fix" | "entry_rewrite";
}): Promise<LookupResult> {
  const res = await fetch(`${API_BASE}/lookup`, {
    method: "POST",
    headers: await userHeaders(true),
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as LookupResult;
}

export interface VocabularyCardPolicy {
  v: number;
  level: number;
  l1: string;
  l2?: string;
  proficiency?: string;
  vocab_def: "l1" | "l1_plus_l2" | "l2_plus_l1" | "l2";
  model: string;
}

/** Review progress of a word in study, attached to GET /vocabulary. */
export interface VocabularyReviewState {
  due: string;
  stability?: number | null;
  reps: number;
  lapses: number;
  /** Due and likely forgotten (recall probability below 80%). */
  at_risk: boolean;
}

export interface UserVocabularyItemResponse extends UserVocabularyItemCreate {
  id: string;
  user_id: string;
  lemma?: string;
  sense?: string;
  card?: VocabularyCardData | null;
  card_status: "pending" | "ok" | "failed";
  card_policy?: VocabularyCardPolicy | null;
  note?: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
  review?: VocabularyReviewState | null;
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

export async function updateVocabularyItem(
  itemId: string,
  changes: { note?: string; tags?: string[]; status?: VocabularyStatus },
): Promise<UserVocabularyItemResponse> {
  const res = await fetch(`${API_BASE}/vocabulary/${itemId}`, {
    method: "PATCH",
    headers: await userHeaders(true),
    credentials: "include",
    body: JSON.stringify(changes),
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as UserVocabularyItemResponse;
}

export async function retryVocabularyCard(itemId: string): Promise<UserVocabularyItemResponse> {
  const res = await fetch(`${API_BASE}/vocabulary/${itemId}/card`, {
    method: "POST",
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as UserVocabularyItemResponse;
}

// --- Review API ---

export type ReviewRating = "again" | "got_it";
export type ReviewMode = "normal" | "catchup";
export type ReviewFormat = "recognition" | "meaning_to_word" | "typed_recall" | "cloze";

export interface ReviewCard {
  card_id: string;
  word_id: string;
  card_type: "recognition" | "production";
  format: ReviewFormat;
  language: string;
  lemma: string;
  /** Times this card has been reviewed; echoed back so a repeated answer is refused. */
  reps: number;
  is_new: boolean;
  /** The learner's sentence around the word. For cloze formats `target` is the blanked answer. */
  front: { before: string; target: string; after: string };
  meaning: string;
  /** Native-language gloss shown with the answer. */
  gloss: string;
  /** Native-language gloss kept behind a tap (balanced immersion). */
  tap_gloss: string;
  /** Hint shown beside the question. */
  hint: string;
  answer: string;
  typed: boolean;
  /** Normalised answers a typed recall may match. */
  accepted: string[];
  status: VocabularyStatus;
  at_risk: boolean;
}

export interface ReviewCounts {
  due: number;
  new_available: number;
  new_remaining: number;
  /** Reviews waiting plus the new words still allowed today. */
  total: number;
  backlog: number;
  at_risk: number;
  suggest_catchup: boolean;
}

export interface ReviewSession {
  language: string;
  mode: ReviewMode;
  cards: ReviewCard[];
  counts: ReviewCounts;
  settings: { daily_new_words: number; desired_retention: number; catchup_daily_budget: number };
  catchup: { daily_budget: number; done_today: number } | null;
}

export interface ReviewSummary {
  languages: Array<{ language: string } & ReviewCounts>;
  total: number;
  at_risk: number;
}

export interface ReviewResult {
  card_id: string;
  rating: ReviewRating;
  due: string;
  reps: number;
  /** The card comes due again within the session, so show it once more. */
  requeue: boolean;
  status: VocabularyStatus;
  production_card_added: boolean;
}

export async function getReviewSession(language: string, mode: ReviewMode = "normal"): Promise<ReviewSession> {
  const params = new URLSearchParams({ language, mode });
  const res = await fetch(`${API_BASE}/review/session?${params}`, {
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as ReviewSession;
}

export async function getReviewSummary(): Promise<ReviewSummary> {
  const res = await fetch(`${API_BASE}/review/summary`, {
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as ReviewSummary;
}

export async function submitReview(
  cardId: string,
  answer: { rating: ReviewRating; reps?: number; duration_ms?: number },
): Promise<ReviewResult> {
  const res = await fetch(`${API_BASE}/review/${cardId}`, {
    method: "POST",
    headers: await userHeaders(true),
    credentials: "include",
    body: JSON.stringify(answer),
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as ReviewResult;
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
  explanation_mode_explicit?: boolean;
  immersion_level: number;
  strictness: string;
  formality: string;
  language_profiles?: LanguageProfileData[];
}

export interface LanguageProfileData {
  l2: string;
  immersion_level: number;
  proficiency: string;
  /** False once removed in Settings; the profile and entries are kept for re-adding. */
  active?: boolean;
  /** How many new words a day enter review for this language (1-100). */
  daily_new_words?: number | null;
  /** The recall probability review aims for (0.80-0.95). */
  desired_retention?: number | null;
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
  language_profiles?: LanguageProfileData[];
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
