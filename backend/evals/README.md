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
