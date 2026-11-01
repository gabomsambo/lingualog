# Manual feedback evals

This folder is the planted-error corpus and scorer from the immersion design probe.
It is **not** part of `make test-backend` or CI. Provider calls stay manual.

```bash
cd backend
python -m evals.score_ref                  # list the corpus
python -m evals.score_ref path/results.json
```

A results file is a JSON list of `{key, cond, rep, out: {corrected, ambiguities?}}`.
`score_corrected` checks that planted fixes appear and that correct "trap" phrases survive.
`words_changed` counts token edits (characters for Japanese). A minimal Spanish correction is about four tokens.

Do not feed a Lara translation into the correction prompt. The probe measured that this over-edits.

## Spanish error-tag accuracy

`error_tags_es.json` is a hand-labelled set of 40 original A1-B2 learner sentences. Run it
against the production Gemini feedback schema and prompt with:

```bash
cd backend
python -m evals.score_error_tags --output /tmp/error-tags-results.json
```

Each sentence has one intended tag. The scorer compares the first returned grammar suggestion
with that tag; no suggestion counts as a miss. It reports per-tag precision/recall and exact
sentence accuracy. The production adapter can retry once, so the 40-item corpus is capped at
80 Gemini requests total. Keep raw model output outside the repository; commit only the
aggregate result report alongside the code.
The measured result for this corpus is in [ERROR_TAGS_RESULTS.md](ERROR_TAGS_RESULTS.md).
