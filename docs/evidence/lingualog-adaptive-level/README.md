# Suggested immersion levels: live proof

Captured 2026-10-04 in headless Chrome against a local `make dev`-style stack (own ports, own
Supabase project id via an untracked override). A suggestion counts only entries with
`analysis_status` `ok`, a real score, `policy_snapshot.immersion_level` equal to the current
level, and `created_at` after `user_language_profiles.level_changed_at`. Demo learner, L1 English.
Spanish was set to immersion 1, which stamped the level change, and then five such entries were
written with a meaning reveal on three of them (exactly 60%). Japanese was set to immersion 2,
which stamped that change, and then eight such entries were written, each scored 80, with no
support taps.

| Shot | What it shows |
|---|---|
| `before-dashboard.png` | Dashboard after the level change, before enough new entries: no card |
| `before-entry.png` | One new Japanese entry: side by side, no card |
| `after-dashboard-step-down.png` | Dashboard card: "Try level 0 for a while?" |
| `after-entry-step-up.png` | Japanese entry card: "Ready for level 3?" |
| `after-settings-spanish-0.png` | After one tap on Yes, Settings shows Spanish immersion 0/3 |

## Exercised live

- `GET /user/level-suggestions` returned Spanish step-down (1 → 0) and Japanese step-up (2 → 3).
- The dashboard showed the Spanish card. The Japanese entry page showed the Japanese card.
- Dismiss on the Japanese card hid it and wrote `level_suggestion_snoozes` for `ja` until 2026-10-11
  (7 days). Japanese immersion stayed 2.
- Accept on the Spanish card wrote the profile through `save_user_settings`: Spanish immersion 0,
  and the default-language `user_settings.immersion_level` is 0. The accept also stamped
  `level_changed_at`, so the card left the dashboard.

## Provider calls

- Gemini: 0. The qualifying rows were seeded with `analysis_status` `ok` and stored scores.
- Lara: 0. The opened entry already had a saved meaning, and the translate requests were served
  from that cache.
