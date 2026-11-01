# First-run CEFR guidance

These are LinguaLog's self-placement prompts and writing recommendations, not official CEFR cut-offs.
The can-do statements are original paraphrases inspired by the Council of Europe's *Common European
Framework of Reference for Languages: Learning, teaching, assessment — Companion Volume* (2020)
self-assessment grid. They are not copied official descriptors.

The authoritative table lives in `backend/learning_policy.py` as `CEFR_LEVELS`. The welcome screen reads
its immersion suggestion and writing guidance through `GET /learning/levels`.

| Level | Can-do self-placement | First-run immersion suggestion | Result view | Soft entry range | Spanish grammar scope |
|---|---|---:|---|---:|---|
| A1 | I can write a few familiar words and simple sentences about myself. | 0 | Calm | 25–50 words | Present tense with ser, estar, tener, hay, ir and gustar; gender and number agreement; articles |
| A2 | I can join familiar sentences with words like y, pero and porque. | 1 | Calm | 60–100 words | A1 scope plus pretérito perfecto, common indefinido verbs, imperfecto for descriptions and habits, ir a + infinitive, direct object pronouns and comparatives |
| B1 | I can write connected paragraphs about experiences, reasons and feelings. | 2 | Full | 120–170 words | Indefinido and imperfecto contrasts; future and conditional for courtesy or advice; beginning present subjunctive; relative clauses |
| B2 | I can write clear, detailed texts and support an opinion with reasons. | 2 | Full | 180–250 words | Indicative and subjunctive tenses; si clauses; passive and impersonal se; reported speech; concession and contrast connectors |
| C1 | I can write well-structured text on complex topics and adapt the tone to the reader. | 3 | Full | 250–350 words | Nuanced subjunctive and conditional choices; complex clause linking and emphasis; register, cohesion and precise word choice |
| C2 | I can express fine shades of meaning in fluent, precise writing for different readers. | 3 | Full | 350–500 words | Idiomatic nuance and rhetorical emphasis; flexible complex syntax; precise register and style choices |

The ranges are soft hints, never submit limits. The Spanish grammar scopes are an authored planning guide;
they do not restrict what a learner may write. Other languages need their own reviewed scope before getting
language-specific frames. Proficiency is stored per target language. Immersion remains the learner's
independent control after the one-time first-run suggestion.
