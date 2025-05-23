import { Entry } from "@/types/entry";
import { getAuthHeaders, getUser } from "./auth";

// Always use localhost for consistent access across browser and container
export const API_BASE = "http://localhost:8000";

export async function postLogEntry(text: string, title: string, language: string) {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();

  const customHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(authHeaders as Record<string, string>)
  };

  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }
  
  const res = await fetch(`${API_BASE}/log-entry`, {
    method: "POST",
    headers: customHeaders,
    body: JSON.stringify({ text, title, language }),
    credentials: "include",
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as Entry;
}

export async function getEntries() {
  const authHeaders = await getAuthHeaders();
  const user = await getUser();

  const customHeaders: Record<string, string> = {
    ...(authHeaders as Record<string, string>)
  };

  if (user && user.id) {
    customHeaders["X-User-ID"] = user.id;
  }
  
  const res = await fetch(`${API_BASE}/entries`, { 
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
    customHeaders["X-User-ID"] = user.id; // Good for security/logging if needed on backend
  }

  const res = await fetch(`${API_BASE}/entries/${id}`, { // New endpoint `/entries/{id}`
    method: "GET",
    headers: customHeaders,
    credentials: "include",
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