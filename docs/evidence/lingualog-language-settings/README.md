# One language model in Settings: live proof

Captured 2026-10-04 in headless Chrome against a local `make dev`-style stack (own ports, own
Supabase project id via an untracked override), with the real Gemini and Lara keys. Demo learner,
explanations in English, studying Spanish (default) and French. "Before" is `main` at `06253d5`.

| Shot | What it shows |
|---|---|
| `before-settings.png` | No add/remove; French appears only through the legacy `target_languages` list |
| `before-default-picker.png` | The default-language picker has no English |
| `before-entry-picker.png` | The new-entry picker lists every language, English included, bypassing Settings |
| `before-mismatch.png` | French text written with Spanish selected: graded silently, no warning |
| `after-settings.png` | "Explain things to me in", "Languages I'm learning" with add/remove, English added (full immersion), French removed |
| `after-entry-picker.png` | The new-entry picker offers only Spanish and English, plus "Learn another language" |
| `after-mismatch-not-studied.png` | The same French text: "This looks like French, but you're set to Spanish." French is not studied, so: Learn French / Keep Spanish |
| `after-mismatch-studied.png` | After "Learn French" re-added French in Settings: Switch to French / Keep Spanish |
| `after-switched.png` | After "Switch to French": the entry is re-analysed as French |
| `after-english-immersion.png` | English studied with explanations in English: English notes, no translation, no rescue |
| `after-settings-native-es.png` | Explanations in Spanish: Spanish (default) becomes full immersion; English keeps its level |
| `after-spanish-immersion.png` | A Spanish speaker improving Spanish: notes and "Lo que quisiste decir" in Spanish |
| `after-removed-language-entry.png` | After removing French again, an older French entry still opens and renders |

## Exercised live

- The migration on the existing local database copied the legacy `target_languages` French into
  `user_language_profiles` at the level and proficiency the old page showed (2, A2). A fresh
  `db reset` applies all migrations and the seed cleanly.
- Removing French saved `active = false`; the row stayed. "Learn French" (`/settings?add=fr`) and
  saving restored it at level 2 / A2.
- Gemini reported `detected_language` in the same structured call: `fr` for the French entry,
  `it` for an Italian one, and `en`/`es` for matching entries (no prompt).
- "Switch to French" moved the entry to `language`/`target_language` `fr`, stored the French policy
  snapshot, and rebuilt the meaning cache from French.
- "Keep Spanish" on the Italian entry stored `detected_language_kept = true`; the prompt stayed gone
  after a reload.
- English with explanations in English and Spanish with explanations in Spanish stored
  `immersion_level` 3, `explanation_source` `same_language`, `note_l1` empty, and no Lara call.
- With explanations in Spanish, an English entry at level 1 got Spanish notes naming the English
  grammar terms (`Past Simple`), with the Spanish meaning blurred behind a tap.

## Provider calls

- Gemini: 6 journal analyses (one before, five after) plus one re-analysis on switch.
- Lara: meaning translations for the opened entries at levels 1-2 only.
