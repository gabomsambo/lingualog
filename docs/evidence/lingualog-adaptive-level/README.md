# Suggested immersion levels: live proof

Captured 2026-10-04 in headless Chrome against a local `make dev`-style stack (own ports, own
Supabase project id via an untracked override). Demo learner, L1 English. Spanish was seeded at
immersion 1 with a meaning reveal on 3 of the last 5 entries (exactly 60%). Japanese was seeded
at immersion 2 with 8 entries scored 80 and no support taps.

| Shot | What it shows |
|---|---|
| `before-dashboard.png` | Dashboard before the suggestion: no card |
| `before-entry.png` | Side-by-side entry before the suggestion: no card |
| `after-dashboard-step-down.png` | Dashboard card: "Try level 0 for a while?" |
| `after-entry-step-up.png` | Japanese entry card: "Ready for level 3?" |
| `after-settings-spanish-0.png` | After one tap on Yes, Settings shows Spanish immersion 0/3 |

## Exercised live

- `GET /user/level-suggestions` returned Spanish step-down (1 → 0) and Japanese step-up (2 → 3).
- The dashboard showed the Spanish card. The Japanese entry page showed the Japanese card.
- Dismiss on the Japanese card hid it and wrote `level_suggestion_snoozes` for `ja` until 2026-10-11
  (7 days). Japanese immersion stayed 2.
- Accept on the Spanish card wrote the profile through `save_user_settings`: Spanish immersion 0,
  and the default-language `user_settings.immersion_level` is 0. The card left the dashboard.
- A later `GET /user/level-suggestions` returned no suggestions.

## Provider calls

- Gemini: 0. Feedback on the seeded rows is the offline mock.
- Lara: 2 successful meaning translations (`POST /entries/{id}/translate` 200, provider `lara`).
  Both entries had no stored policy snapshot, so the result page asked for a meaning translation
  while the proof was open. No Gemini fallback.
