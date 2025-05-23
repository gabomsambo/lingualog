export interface Entry {
  id?: string;              // from DB
  original_text: string;
  title?: string;           // Added: title of the entry
  language?: string;        // Added: language of the entry
  corrected: string;
  rewrite: string;
  score: number;
  tone: "Reflective" | "Confident" | "Neutral";
  translation: string;
  created_at?: string;
}
