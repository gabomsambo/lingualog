# Spanish error-tag eval

Measured with the live Gemini feedback schema and production journal prompt on 2026-11-01.

- Model: `gemini-3.8-flash`
- Corpus: 40 original Spanish learner sentences, A1-B2, with one intended tag each
- Live requests: 40 of the 80-request cap
- Exact first-suggestion tag accuracy: **34/40 (85.0%)**
- One request timed out; it remained in the denominator as a miss

| Tag | Support | Precision | Recall |
| --- | ---: | ---: | ---: |
| `accent_spelling` | 3 | 100.0% | 100.0% |
| `article` | 4 | 100.0% | 100.0% |
| `gender_agreement` | 3 | 75.0% | 100.0% |
| `gustar` | 3 | 100.0% | 100.0% |
| `number_agreement` | 4 | 100.0% | 75.0% |
| `other` | 2 | 0.0% | 0.0% |
| `por_para` | 3 | 100.0% | 66.7% |
| `preposition` | 3 | 60.0% | 100.0% |
| `ser_estar` | 3 | 100.0% | 100.0% |
| `tense_choice` | 4 | 100.0% | 75.0% |
| `verb_conjugation` | 4 | 100.0% | 100.0% |
| `vocabulary_choice` | 2 | 50.0% | 50.0% |
| `word_order` | 2 | 100.0% | 100.0% |

The scorer compares the first returned suggestion with the sentence's single hand-labelled tag;
no suggestion or a failed request is incorrect. This small authored set measures tag assignment,
not correction quality or performance on unrestricted journal entries. `other` and lexical-choice
labels are weak in this run, so they should not drive lessons without further evidence.
