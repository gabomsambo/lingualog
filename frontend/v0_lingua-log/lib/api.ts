import { Entry } from "@/types/entry";
import { getAuthHeaders, getUser } from "./auth";
import type { LearningPolicySnapshot } from "./side-by-side";
import type { WordBank } from "./word-bank";

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
  /** Notebook words chosen from the word bank to write this entry with. */
  target_word_ids?: string[];
  /** Target words whose text stayed hidden while writing. */
  challenge_word_ids?: string[];
  /** The class note whose grammar focus this entry practises. */
  class_note_id?: string;
  prompt_id?: string;
  entry_mode?: PromptEntryMode;
}

export type PromptEntryMode = "idea" | "frame" | "one_sentence";

export interface WritingPrompt {
  id: string;
  level: string;
  topics: string[];
  title: string;
  prompt: string;
  sentence_frame: string;
  one_sentence_frame: string;
  structure_hint: string;
  suggested_words: string[];
  gloss: {
    prompt: string;
    sentence_frame: string;
    one_sentence_frame: string;
    structure_hint: string;
  } | null;
}

export interface WritingPromptResponse {
  l2: string;
  level: string;
  meaning: "open" | "tap" | "tap_hidden" | "rescue_only" | string;
  gloss_available: boolean;
  topics: string[];
  prompts: WritingPrompt[];
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

export async function getPrompts(options: {
  l2: string;
  level?: string;
  topic?: string;
  exclude?: string[];
}): Promise<WritingPromptResponse> {
  const url = new URL(`${API_BASE}/prompts`);
  url.searchParams.set("l2", options.l2);
  if (options.level) url.searchParams.set("level", options.level);
  if (options.topic) url.searchParams.set("topic", options.topic);
  options.exclude?.forEach((promptId) => url.searchParams.append("exclude", promptId));

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as WritingPromptResponse;
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
  | "reveal_gloss"
  | "prompt_selected";

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
  prompt_id?: string;
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
  source: "entry" | "manual" | "book_session";
  source_id?: string;
  kind?: "lookup" | "entry_text" | "entry_fix" | "entry_rewrite";
  /** Book page, for a lookup made in a reading session. */
  page?: number;
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

export type VocabularyListId = "due" | "never_used";
export type VocabularySource = "entry" | "book" | "lookup" | "class_note";

/** List and filter selectors for the notebook (GET /vocabulary). */
export interface VocabularyQuery {
  list?: VocabularyListId;
  tag?: string;
  entry_id?: string;
  book_id?: string;
  status?: VocabularyStatus;
  source?: VocabularySource;
}

export async function getVocabularyItems(
  language?: string,
  query?: VocabularyQuery,
): Promise<UserVocabularyItemResponse[]> {
  const url = new URL(`${API_BASE}/vocabulary`);
  if (language) url.searchParams.append("language", language);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== "") url.searchParams.append(key, String(value));
  }
  const res = await fetch(url.toString(), {
    method: "GET",
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
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

// --- Progress, lists, export and placement ---

export interface PlacementResult {
  v: number;
  estimate: number;
  sample_size: number;
  known: string[];
  checked_at: string;
}

export interface VocabularyProgress {
  language: string | null;
  notebook: { new: number; learning: number; known: number; mastered: number; ignored: number; total: number };
  trend: Array<{ date: string; count: number }>;
  active_words: number;
  encounters: {
    by_kind: Record<string, number>;
    reviews: number;
    per_word: number;
    guide_min: number;
    guide_max: number;
  };
  review: {
    due_today: number;
    new_today: number;
    forecast: Array<{ date: string; count: number }>;
    at_risk: number;
    true_retention: number | null;
    reviews_last_7_days: number;
    minutes_last_7_days: number;
  };
  week: {
    reading: number;
    journal: number;
    reviews: number;
    review_minutes: number;
    review_share: number;
    over_budget: boolean;
  };
  placement: PlacementResult | null;
  placement_available: boolean;
}

export interface VocabularyLists {
  total: number;
  smart: Array<{ id: VocabularyListId; count: number }>;
  tags: Array<{ id: string; name: string; count: number }>;
  entries: Array<{ id: string; entry_id: string; title: string | null; date: string | null; count: number }>;
  books: Array<{ id: string; book_id: string; title: string | null; count: number }> | null;
}

export interface PlacementCheck {
  language: string;
  words: string[];
  bands: string[][];
  result: PlacementResult | null;
}

export async function getVocabularyProgress(language?: string): Promise<VocabularyProgress> {
  const url = new URL(`${API_BASE}/vocabulary/progress`);
  if (language) url.searchParams.append("language", language);
  const res = await fetch(url.toString(), {
    method: "GET",
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as VocabularyProgress;
}

export async function getVocabularyLists(language?: string): Promise<VocabularyLists> {
  const url = new URL(`${API_BASE}/vocabulary/lists`);
  if (language) url.searchParams.append("language", language);
  const res = await fetch(url.toString(), {
    method: "GET",
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as VocabularyLists;
}

/** Download the notebook (or one list) as CSV or as an Anki deck. */
export async function exportVocabulary(
  format: "csv" | "apkg",
  language?: string,
  query?: VocabularyQuery,
): Promise<Blob> {
  const url = new URL(`${API_BASE}/vocabulary/export`);
  url.searchParams.append("format", format);
  if (language) url.searchParams.append("language", language);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== "") url.searchParams.append(key, String(value));
  }
  const res = await fetch(url.toString(), {
    method: "GET",
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return res.blob();
}

export async function getPlacementCheck(language: string): Promise<PlacementCheck> {
  const res = await fetch(`${API_BASE}/placement/${encodeURIComponent(language)}`, {
    method: "GET",
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as PlacementCheck;
}

export async function submitPlacementCheck(language: string, known: string[]): Promise<PlacementResult> {
  const res = await fetch(`${API_BASE}/placement/${encodeURIComponent(language)}`, {
    method: "POST",
    headers: await userHeaders(true),
    credentials: "include",
    body: JSON.stringify({ known }),
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as PlacementResult;
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
  /** New words allowed in a session today, counted apart like Anki's new count. */
  new: number;
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
  new: number;
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

// --- Word bank API ---

export async function getWordBank(
  language: string,
  options: { count?: number; exclude?: string[]; include?: string[]; book?: string } = {},
): Promise<WordBank> {
  const params = new URLSearchParams({ language });
  if (options.count) params.set("count", String(options.count));
  for (const id of options.exclude ?? []) params.append("exclude", id);
  for (const id of options.include ?? []) params.append("include", id);
  if (options.book) params.set("book", options.book);
  const res = await fetch(`${API_BASE}/word-bank?${params}`, {
    headers: await userHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as WordBank;
}

export interface ClassNoteWord {
  term: string;
  lemma: string;
  gloss: string;
  part_of_speech: string;
  example: string;
  reading: string;
  word_id?: string | null;
  encounter_id?: string | null;
}

export interface ClassPracticeTask {
  title: string;
  prompt: string;
  length_hint: string;
  grammar_scope: string;
}

export interface ClassNoteExtraction {
  words: ClassNoteWord[];
  grammar_focus: string | null;
  phrases: string[];
  tasks: ClassPracticeTask[];
  level: string;
  length_hint: string;
  grammar_scope: string;
}

export interface ClassNoteRecord {
  id: string;
  user_id: string;
  l2: string;
  raw_text: string;
  source: "paste" | "photo";
  extracted: ClassNoteExtraction;
  created_at: string;
}

async function classNoteRequest<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: await userHeaders(method !== "GET"),
    credentials: "include",
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as T;
}

export function createClassNote(text: string, language: string): Promise<ClassNoteRecord> {
  return classNoteRequest("/class-notes", "POST", { text, language });
}

export function getClassNote(noteId: string): Promise<ClassNoteRecord> {
  return classNoteRequest(`/class-notes/${encodeURIComponent(noteId)}`);
}

export function getWaitingClassNote(language: string): Promise<ClassNoteRecord | null> {
  const params = new URLSearchParams({ language });
  return classNoteRequest(`/class-notes/waiting?${params.toString()}`);
}

export function confirmClassNote(
  noteId: string,
  extraction: ClassNoteExtraction,
): Promise<ClassNoteRecord> {
  return classNoteRequest(`/class-notes/${encodeURIComponent(noteId)}/confirm`, "POST", extraction);
}

// --- Book mode API ---

export type BookStatus = "reading" | "finished" | "paused";
/** Soft estimate of how many unknown words a page holds; never a percentage. */
export type CoverageBand = "comfortable" | "study" | "demanding" | "hard";

export interface Book {
  id: string;
  title: string;
  author?: string | null;
  language: string;
  status: BookStatus;
  created_at: string;
  updated_at: string;
}

export interface BookSummary extends Book {
  sessions: number;
  words_marked: number;
  open_session_id: string | null;
  /** Words marked per page, one number per finished session that had pages. */
  rate_series: number[];
  last_band: CoverageBand | null;
}

export interface ReadingSessionSummary {
  id: string;
  started_at: string;
  ended_at: string | null;
  page_from: number | null;
  page_to: number | null;
  pages_read: number | null;
  words_marked: number;
  words_per_page: number | null;
  band: CoverageBand | null;
}

export interface BookMark {
  id: string;
  surface: string;
  sentence: string | null;
  page: number | null;
  created_at: string;
  /** How often this word is marked in the whole book. */
  times_marked: number;
  in_notebook: boolean;
}

export interface BookDetail {
  book: Book;
  session: (ReadingSessionSummary & { marks: BookMark[] }) | null;
}

export interface TriageItem {
  key: string;
  lemma: string;
  surface: string;
  sentence: string | null;
  page: number | null;
  times_marked: number;
  recurring: boolean;
  card: VocabularyCardData | null;
  card_status: "ok" | "failed" | "pending";
  encounter_id: string | null;
  encounter_ids: string[];
}

export interface SessionTriage {
  items: TriageItem[];
  recurring: number;
  /** Cards the model could not build this time; the marks stay and can be retried. */
  failed?: number;
}

export interface PageCandidate {
  surface: string;
  lemma: string;
  status: VocabularyStatus | null;
}

export interface PagePhotoResult {
  readable: boolean;
  transcription: string;
  candidates: PageCandidate[];
  estimate: { unknown_estimate: number; page_words: number; band: CoverageBand | null } | null;
}

export interface GlossaryWord {
  key: string;
  lemma: string;
  surfaces: string[];
  times_marked: number;
  pages: number[];
  sentences: Array<{ sentence: string; page: number | null }>;
  meaning: string;
  gloss: string;
  has_card: boolean;
  status: VocabularyStatus | null;
  skipped: boolean;
}

export interface BookGlossary {
  book: Book;
  words: GlossaryWord[];
}

export interface BookProgress {
  book: Book;
  sessions: ReadingSessionSummary[];
  pages: Array<{ page: number; words: number; band: CoverageBand | null }>;
  trend: "falling" | "flat" | "rising" | null;
  latest_band: CoverageBand | null;
  stays_hard: boolean;
  estimate: true;
}

async function bookRequest<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: init.method ?? "GET",
    headers: await userHeaders(init.body !== undefined),
    credentials: "include",
    ...(init.body !== undefined ? { body: JSON.stringify(init.body) } : {}),
  });
  if (!res.ok) throw await apiError(res);
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const listBooks = (language?: string) =>
  bookRequest<BookSummary[]>(`/books${language ? `?${new URLSearchParams({ language })}` : ""}`);
export const createBook = (book: { title: string; author?: string; language: string }) =>
  bookRequest<Book>("/books", { method: "POST", body: book });
export const getBook = (bookId: string) => bookRequest<BookDetail>(`/books/${bookId}`);
export const updateBook = (bookId: string, changes: { title?: string; author?: string; status?: BookStatus }) =>
  bookRequest<Book>(`/books/${bookId}`, { method: "PATCH", body: changes });
export const deleteBook = (bookId: string) => bookRequest<void>(`/books/${bookId}`, { method: "DELETE" });
export const startReadingSession = (bookId: string, pageFrom?: number) =>
  bookRequest<ReadingSessionSummary>(`/books/${bookId}/sessions`, { method: "POST", body: { page_from: pageFrom ?? null } });
export const markWord = (bookId: string, sessionId: string, mark: { word: string; sentence?: string; page?: number }) =>
  bookRequest<BookMark & { created: boolean }>(`/books/${bookId}/sessions/${sessionId}/marks`, {
    method: "POST",
    body: { word: mark.word, sentence: mark.sentence || null, page: mark.page ?? null },
  });
export const unmarkWord = (bookId: string, sessionId: string, markId: string) =>
  bookRequest<void>(`/books/${bookId}/sessions/${sessionId}/marks/${markId}`, { method: "DELETE" });
export const endReadingSession = (bookId: string, sessionId: string, pageTo?: number) =>
  bookRequest<ReadingSessionSummary>(`/books/${bookId}/sessions/${sessionId}/end`, {
    method: "POST",
    body: { page_to: pageTo ?? null },
  });
export const buildSessionCards = (bookId: string, sessionId: string) =>
  bookRequest<SessionTriage>(`/books/${bookId}/sessions/${sessionId}/cards`, { method: "POST" });
export const getSessionTriage = (bookId: string, sessionId: string) =>
  bookRequest<SessionTriage>(`/books/${bookId}/sessions/${sessionId}/triage`);
export const skipMarks = (bookId: string, encounterIds: string[]) =>
  bookRequest<{ skipped: number }>(`/books/${bookId}/marks/skip`, { method: "POST", body: { encounter_ids: encounterIds } });
export const getBookGlossary = (bookId: string) => bookRequest<BookGlossary>(`/books/${bookId}/glossary`);
export const getBookProgress = (bookId: string) => bookRequest<BookProgress>(`/books/${bookId}/progress`);

/** Send one page photo for transcription. The image is read once by the server and never stored. */
export async function readPagePhoto(bookId: string, image: Blob): Promise<PagePhotoResult> {
  const res = await fetch(`${API_BASE}/books/${bookId}/page-photo`, {
    method: "POST",
    headers: { ...(await userHeaders()), "Content-Type": "application/octet-stream" },
    credentials: "include",
    body: image,
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as PagePhotoResult;
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
    percentage: number;
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
  goal?: string | null;
  onboarded_at?: string | null;
}

export interface FirstRunLevelCriteria {
  can_do: string;
  can_do_key: string;
  default_immersion: number;
  soft_entry_words: [number, number];
  spanish_grammar_scope: string[];
  first_entry: {
    kind: "frames" | "hint" | "open";
    prompt: string;
    hint?: string;
    frames?: Array<{ prefix: string; label: string }>;
  };
}

export async function getLearningLevels(): Promise<Record<string, FirstRunLevelCriteria>> {
  const res = await fetch(`${API_BASE}/learning/levels`);
  if (!res.ok) throw new Error(`Failed to fetch learning levels: ${res.status}`);
  const data = (await res.json()) as { levels: Record<string, FirstRunLevelCriteria> };
  return data.levels;
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
