# Side-by-side entry result: live proof

Captured 2026-10-04 in headless Chrome against a local `make dev`-style stack (own ports, own
Supabase project id via an untracked override), with real Gemini 3.8 Flash and Lara keys.
Demo learner, L1 English, Spanish at proficiency B1.

Entry used at every level (planted mistakes, two of them meaning-changing):

> Mi hermana es muy aburrida hoy porque está lloviendo. Quiero que ella viene conmigo al cine para
> ver una película nueva. Despues comimos mucho palomitas y la película era muy divertido. Estoy muy
> embarazada porque olvidé su cumpleaños.

| Shot | What it shows |
|---|---|
| `before-1` | `main`: after submit, the "Entry Saved! translate?" pop-up covers the result |
| `before-2` | `main`: closing the pop-up navigates to `/entries` |
| `before-3` | `main`: entry page has no corrected text or rewrite, and Gemini returned no grammar notes |
| `before-4` | `main`: dashboard "Languages Practiced" counts tones (7) |
| `after-1` | Immersion 1 post-submit result: three columns, meaning blurred |
| `after-2` | The pop-up opened from "Translate whole entry"; closing it stays on the result |
| `after-3` | Immersion 0 entry page: side-by-side card above the existing sections |
| `after-4` | Dashboard counts languages (Spanish, French: 2) |
| `after-5` | Immersion 0 Native view: rewrite block, idiom chips, English translation shown |
| `after-6` | Immersion 1 after one tap to reveal and "Show in English" on the rewrite |
| `after-7` | Immersion 2: "Show meaning" links, Spanish notes with an English gloss |
| `after-8` | Immersion 3: "Lo que quisiste decir" paraphrase, Spanish warnings, meaning and note rescues |
| `after-9` | Immersion 1 at 390 px: rows stack per sentence, no horizontal scroll |
| `after-10` | Analysis failed (Gemini model unavailable): clear message and Retry |
| `after-11` | The same entry after Retry |
| `after-12` | Seeded mock entry: "Sample feedback" banner; no stored policy, so the current one is used |

## Exercised live

- Submit at immersion 0, 1, 2 and 3; each entry stored its `policy_snapshot` and rendered from it.
- Reveal and rescue events in `support_events`: `reveal_meaning` (1, 2, 3), `reveal_rewrite_gloss`
  (1, 3), `rescue_note` (3). Nothing is logged for content shown open at immersion 0.
- `POST /entries/{id}/translate` for `original`, `rewrite` and `note:<id>`, sentence-aligned rows.
- Failure: the API was restarted with a nonexistent Gemini model, the entry was saved as `failed`,
  and Retry (`POST /entries/{id}/analyze`) succeeded once the model was restored.
- Mobile width (390 px), the kept translate pop-up, the dashboard language count.

## Found and fixed during the walk

- Gemini returned empty `grammar_suggestions` and `new_words` on every live call while they were
  optional in the response schema (PR 4's live proof shows `notes: []` too). They are now required.
- Note rescues sent Lara `content_type="html"`; Lara accepts only `text/html`, so every rescue fell
  back to Gemini Flash-Lite. Rescued notes come back as HTML and are shown as text.

## Reasoned about, not exercised live

- "Translation unavailable" Retry and the misaligned-sentence fallback: covered by component tests.
- Ambiguity questions: Gemini asked none for this entry; the card is covered by component tests.
  The schema has no answer options, so questions are shown without one-tap answers.

## Provider calls

- Gemini 3.8 Flash: 7 successful (1 before, 1 schema probe, 4 levels, 1 retry) plus the failed
  request(s) to the nonexistent model.
- Gemini Flash-Lite (translation fallback): 2, both note rescues before the `text/html` fix.
- Lara: 10 successful translations, 2 rejected by Lara (the `html` content type).
