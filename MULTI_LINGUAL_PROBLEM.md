Problem: I want to make sure we implement the functionality of the application correctly. The issue is that I want to make sure the approach we had chosen which was that in the setting we have the user pick three languages which are the:
    - Interface Language- The language used for the application interface
    - Native Language - Your native or most proficient language
    - Default Target Language: The language you are trying to learn

Immersion Level 1 / 3 : 0 - Native First, 1: Guided Bilingual, 2 : Balance, 3 : immersive.

Love this—let’s lock in the mental model so every screen and prompt behaves predictably. Think of LinguaLog as orchestrating three languages with one brain:
	•	UI-lang (Interface language): what the chrome, buttons, dates, and numbers are shown in.
	•	L1 (Native language): what explanations/teaching meta-talk can be in.
	•	L2 (Target language): what the learner practices and gets corrected/re-written in.

North-star goals
	1.	Keep the learner in L2 as much as they can handle (focus time),
	2.	Make help instantly available in L1 (frictionless rescue),
	3.	Never confuse the UI with pedagogy (UI-lang is purely interface),
	4.	Make behavior consistent across all exercise types (journal today, photo game tomorrow).

⸻

The rulebook (one table, covers everything)

Immersion slider → output languages

Level	Explanation language	Translation policy
0 – Native-First	L1	Always show L2→L1
1 – Guided Bilingual	L1	On-demand (generate, hide behind 👁️)
2 – Balanced Immersion	Bilingual (start in L2, then brief L1)	On-demand
3 – Full Immersion	L2	Omit (no translation generated)

Field-by-field language contract (always)
	•	corrected: L2
	•	rewritten: L2 (native-like)
	•	explanation: per slider (above)
	•	translation: per slider (above)
	•	tone (label/descriptor): L2 (short)
	•	UI labels/tooltips: UI-lang

Important: UI-lang never changes the coaching language. It only changes chrome and formatting (dates/numbers, RTL).

⸻

How a session works (the “resolver → model → render” loop)
	1.	Resolve languages
	•	UI-lang = user setting (or browser on first visit)
	•	L1 = user setting “Native language”
	•	L2 = per-entry picker (defaults to “Default Target”)
	•	immersion_level (0–3) → (explanation_language, translation_policy) via the table
	2.	Render composer
	•	Textarea lang={L2}, dir=rtl if L2 is RTL
	•	Chrome (menus/tabs/buttons) in UI-lang
	3.	Call the model
	•	Prompts in English (control language), outputs parameterized with {L1, L2, explanation_language, translation_policy}.
	•	Always produce corrected, rewritten, score, tone.
	•	Produce translation according to policy (generate & show, generate & hide, or do not generate).
	4.	Snapshot for reproducibility (save with the entry)
	•	target_language = L2
	•	ui_language_snapshot = UI-lang
	•	explanation_language_snapshot (derived from immersion)
	•	translation_policy_snapshot (derived from immersion)
	•	optional proficiency_estimate (A/B/C)
	5.	Render feedback
	•	corrected/rewritten (L2) visible by default
	•	explanation per policy (L1/L2/bilingual)
	•	👁️ toggle reveals translation when policy is on-demand
	•	UI chrome stays in UI-lang
	6.	Quick rescues without re-calling the model
	•	“Explain this in L1/L2” button can post-transform the current explanation (cheap translation step)
	•	“More strict / more casual” reuses the same entry + flips variables for a quick re-ask
	7.	Analytics & adapt
	•	Track clicks on 👁️ translation (proxy for difficulty)
	•	If user in Level 3 repeatedly opens rescues, nudge toward Level 2 next time

⸻

What each language actually does
	•	UI-lang: accessibility, comfort, format correctness. It does not teach. It must always be dependable (fallback to English per key if missing).
	•	L1: cognitive safety net. It turns confusion into clarity with the fewest words possible.
	•	L2: practice and modeling. All “do this like a native” outputs are in L2.

⸻

Three crystal-clear scenarios

A) Beginner (A0)
	•	UI-lang: English (en-US)
	•	L1: English (en)
	•	L2: Japanese (ja)
	•	Immersion: 0 – Native-First
Behavior:
	•	Corrections/rewrites: Japanese (L2)
	•	Explanation: English (L1)
	•	Translation: always visible (JA→EN)
Why: minimize cognitive load; constant mapping between L2 form and L1 meaning.

B) Intermediate (B1–B2)
	•	UI-lang: Spanish (es-ES)
	•	L1: Spanish (es)
	•	L2: French (fr)
	•	Immersion: 1 – Guided Bilingual
Behavior:
	•	Explanations in Spanish (L1)
	•	Translation generated but hidden; learner reveals only when stuck
Why: practice recall in L2, keep L1 available with one tap.

C) Advanced (C1) polyglot
	•	UI-lang: German (de-DE)
	•	L1: Spanish (es-419)
	•	L2: Japanese (ja) today, Arabic (ar) tomorrow
	•	Immersion: 3 – Full Immersion
Behavior:
	•	Everything pedagogical in L2 (explanations in JA/AR). No translation generated.
	•	UI remains German across both study languages.
Why: maximize immersion; learner can still “Explain in L1” on demand (one-off translate call).

⸻

Edge cases & how we handle them
	•	L1 = L2 (heritage learners/code-switching): explanations still follow slider; if Level 0/1 says “L1”, then explanation will also be in L2—fine, because the user asked for it. Offer a hint to set L1 to a different language if they want native-language support.
	•	User wrote the entry in the wrong language: we still correct; add a one-line note in explanation (“Detected most text in {detected_lang} not {L2}”). No scolding, just clarity.
	•	RTL mixing: UI may be LTR, but if L2 is Arabic/Hebrew, the textarea and L2 panes switch dir="rtl" with an RTL-friendly font.
	•	Partial translations (locales not fully covered): per-key fallback to English for UI; never block content.
	•	Multiple targets: each entry stores its own target_language; dashboards filter by L2.

⸻

Minimal “resolver” logic (the one function that makes it all work)

type Effective = {
  UI: string; L1: string; L2: string;
  explanation_language: 'native'|'target'|'bilingual';
  translation_policy: 'always'|'on_demand'|'omit';
};

const IMMERSION = {
  0: { explanation_language: 'native',   translation_policy: 'always'    },
  1: { explanation_language: 'native',   translation_policy: 'on_demand' },
  2: { explanation_language: 'bilingual',translation_policy: 'on_demand' },
  3: { explanation_language: 'target',   translation_policy: 'omit'      },
};

function resolveEffective(profile, overrides): Effective {
  const UI = overrides.UI ?? profile.interface_lang ?? 'en';
  const L1 = overrides.L1 ?? profile.native_lang ?? 'en';
  const L2 = overrides.L2 ?? profile.default_target_lang ?? 'en';
  const level = Number(overrides.immersion_level ?? profile.immersion_level ?? 1);
  const { explanation_language, translation_policy } = IMMERSION[level] ?? IMMERSION[1];
  return { UI, L1, L2, explanation_language, translation_policy };
}


⸻

What success looks like in the UI
	•	The chrome feels native (UI-lang), even if the lesson is hard.
	•	The practice is always in L2 (corrections/rewrites).
	•	Help is exactly where the slider says it will be (L1/L2/bilingual, with or without immediate translation).
	•	Toggling the immersion slider instantly changes only pedagogy outputs—not the UI chrome.

⸻

Why this design scales
	•	New exercise types (photo describe, dialogue drills) reuse the same resolver + contract.
	•	Adding Lara (or any MT) for the translation pane is plug-and-play: it only touches that field.
	•	Snapshotting ensures old entries render exactly as made, even if the user later changes languages or modes.

If you want, I can turn this into two tiny PRs:
	1.	a resolveEffective() utility + server snapshot write,
	2.	a FeedbackCard that reads the snapshot and applies the display rules (👁️ toggle, bilingual formatting),
so the behavior you just approved becomes impossible to accidentally break.