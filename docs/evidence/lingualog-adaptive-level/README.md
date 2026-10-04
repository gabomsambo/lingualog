# Suggested immersion levels: live proof

Captured 2026-10-04 in headless Chrome against a local `make dev`-style stack (own ports, own
Supabase project id via an untracked override), on the code that counts only entries with
`analysis_status` `ok`, a real score, and `policy_snapshot.immersion_level` equal to the current
level. Demo learner, L1 English. Spanish was at immersion 1 with five such entries and a meaning
reveal on the three newest (exactly 60%). Japanese was at immersion 2 with eight such entries
scored 80 and no support taps.

> **Note:** This run predates `user_language_profiles.level_changed_at`. Windows now also skip
> entries written before the language's last level change; with no change recorded (the stamp
> is null) the seed above behaves the same.

| Shot | What it shows |
|---|---|
| `before-dashboard.png` | Dashboard before enough qualifying entries: no card |
| `before-entry.png` | One scored Japanese entry: side by side, no card |
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

## Provider calls

- Gemini: 0. The qualifying rows were seeded with `analysis_status` `ok` and stored scores.
- Lara: 0. The opened entry already had a saved meaning, and the translate request was served
  from that cache.
