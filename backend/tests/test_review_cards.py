"""What a review card shows: the learner's own sentence, deterministic cloze, format per quiz flag."""

import pytest

import review_cards as rc

WORD = {
    "id": "word-1", "lemma": "aprovechar", "term": "aprovechar", "language": "es", "status": "learning",
    "example_sentence": "Aproveché la tarde para estudiar.", "entry_id": "entry-1",
    "card": {
        "lemma": "aprovechar", "surface": "Aproveché", "sense_in_context": "to make good use of",
        "gloss_l1": "make use of", "examples": ["Quiero aprovechar el sol.", "Hay que aprovechar el tiempo."],
    },
}
ENTRY = {
    "id": "entry-1",
    "original_text": "Ayer aproveché de la tarde para estudiar. Luego cené.",
    "corrected": "Ayer aproveché la tarde para estudiar. Luego cené.",
    "sentence_mapping": [
        {"source_sentence": 0, "corrected_sentences": [0]},
        {"source_sentence": 1, "corrected_sentences": [1]},
    ],
    "sentence_mapping_status": "valid",
}
ENCOUNTER = {
    "word_id": "word-1", "surface": "aproveché", "kind": "entry_text", "source_type": "entry",
    "source_id": "entry-1", "sentence": "Ayer aproveché de la tarde para estudiar.",
    "created_at": "2026-10-30T10:00:00Z",
}


def row(card_type="recognition", reps=0):
    return {"id": "card-1", "word_id": "word-1", "language": "es", "card_type": card_type, "reps": reps}


def build(card_type="recognition", quiz="recognition_l1", reps=0, word=WORD, encounters=(ENCOUNTER,),
          entries=None):
    return rc.build_review_card(
        row(card_type, reps), word, list(encounters),
        {"entry-1": ENTRY} if entries is None else entries, quiz, "learning", False,
    )


def test_recognition_front_is_the_learners_own_sentence_with_the_word_marked():
    card = build()
    assert card["format"] == "recognition"
    assert card["front"] == {"before": "", "target": "Aproveché", "after": " la tarde para estudiar."}
    assert card["sentence_source"] == "encounter"
    assert card["is_new"] is True
    assert card["meaning"] == "to make good use of"


def test_recognition_keeps_the_sentence_as_written_even_with_a_mistake():
    card = build(reps=1)
    assert card["front"] == {"before": "Ayer ", "target": "aproveché", "after": " de la tarde para estudiar."}
    assert card["is_new"] is False


def test_cloze_blanks_the_word_in_the_corrected_sentence_not_the_mistaken_one():
    card = build("production", "cloze_l1_hint", reps=1)
    assert card["format"] == "cloze"
    sentence = card["front"]["before"] + card["front"]["target"] + card["front"]["after"]
    assert sentence == "Ayer aproveché la tarde para estudiar."
    assert "de la tarde" not in sentence
    assert card["front"]["target"] == "aproveché"
    assert card["answer"] == "aproveché"


def test_cloze_follows_the_sentence_mapping_to_the_right_corrected_sentence():
    word = {**WORD, "example_sentence": None, "entry_id": None}
    two_words = {**ENTRY,
                 "original_text": "Luego cené aprovechando poco. Ayer aproveché de la tarde.",
                 "corrected": "Luego cené aprovechando poco. Ayer aproveché la tarde.",
                 "sentence_mapping": [{"source_sentence": 0, "corrected_sentences": [0]},
                                      {"source_sentence": 1, "corrected_sentences": [1]}]}
    encounter = {**ENCOUNTER, "sentence": "Ayer aproveché de la tarde."}
    card = build("production", "cloze_l1_hint", word=word, encounters=[encounter],
                 entries={"entry-1": two_words}, reps=0)
    assert card["front"]["before"] + card["front"]["target"] + card["front"]["after"] == (
        "Ayer aproveché la tarde."
    )


def test_cloze_without_a_valid_mapping_picks_the_closest_corrected_sentence():
    entry = {**ENTRY, "sentence_mapping": [], "sentence_mapping_status": "invalid"}
    card = build("production", "cloze_l1_hint", entries={"entry-1": entry})
    assert card["front"]["before"] + card["front"]["target"] + card["front"]["after"] == (
        "Ayer aproveché la tarde para estudiar."
    )


def test_a_fix_or_rewrite_encounter_is_already_corrected():
    fix = {**ENCOUNTER, "kind": "entry_fix", "sentence": "Ayer aproveché la tarde para estudiar."}
    word = {**WORD, "example_sentence": None}
    card = build("production", "cloze_l1_hint", word=word, encounters=[fix], entries={})
    assert card["front"]["target"] == "aproveché"
    assert card["sentence_source"] == "corrected"


def test_cloze_never_uses_an_entry_sentence_it_cannot_correct():
    """The learner's own entry text may hold mistakes; with no corrected text, fall to card examples."""
    word = {**WORD, "example_sentence": None}
    card = build("production", "cloze_l1_hint", word=word, entries={})
    assert card["sentence_source"] == "card_example"
    assert card["front"]["target"].lower() in ("aprovechar",)


def test_a_lookup_sentence_from_outside_an_entry_can_be_blanked_as_written():
    lookup = {"word_id": "word-1", "surface": "aprovechar", "kind": "lookup", "source_type": "manual",
              "source_id": None, "sentence": "Hay que aprovechar la oportunidad.", "created_at": "2026-10-30T09:00:00Z"}
    word = {**WORD, "example_sentence": None, "entry_id": None}
    card = build("production", "l2_only", word=word, encounters=[lookup], entries={})
    assert card["front"] == {"before": "Hay que ", "target": "aprovechar", "after": " la oportunidad."}
    assert card["sentence_source"] == "encounter"


def test_a_sentence_from_a_book_mark_is_a_review_front():
    mark = {"word_id": "word-1", "surface": "aprovechaba", "kind": "read", "source_type": "book_session",
            "source_id": "session-1", "book_id": "book-1", "page": 12, "sentence": "Aprovechaba cada rato libre.",
            "created_at": "2026-10-30T09:00:00Z"}
    word = {**WORD, "example_sentence": None, "entry_id": None}
    card = build("production", "l2_only", word=word, encounters=[mark], entries={})
    assert card["front"] == {"before": "", "target": "Aprovechaba", "after": " cada rato libre."}
    assert card["sentence_source"] == "encounter"


def test_the_sentence_rotates_with_each_review():
    other = {**ENCOUNTER, "sentence": "Quiero aprovechar el día.", "surface": "aprovechar",
             "source_type": "manual", "source_id": None, "kind": "lookup", "created_at": "2026-10-31T09:00:00Z"}
    word = {**WORD, "example_sentence": None}
    shown = [
        "".join(build(word=word, encounters=[ENCOUNTER, other], reps=reps)["front"].values())
        for reps in range(4)
    ]
    assert shown[0] != shown[1]
    assert shown[0] == shown[2] and shown[1] == shown[3]


def test_the_same_sentence_is_not_offered_twice():
    encounters = [ENCOUNTER, {**ENCOUNTER, "created_at": "2026-10-31T10:00:00Z"}]
    word = {**WORD, "example_sentence": ENCOUNTER["sentence"], "entry_id": "entry-1"}
    assert len(rc.sentence_candidates(word, encounters)) == 1


def test_a_lookup_of_the_bare_word_is_not_a_sentence():
    bare = {**ENCOUNTER, "sentence": "aprovechar", "surface": "aprovechar"}
    word = {**WORD, "example_sentence": None}
    assert rc.sentence_candidates(word, [bare]) == []
    card = build(word=word, encounters=[bare])
    assert card["format"] == "meaning_to_word"
    assert card["answer"] == "aprovechar"


def test_an_example_sentence_that_is_just_the_word_is_not_a_sentence():
    word = {**WORD, "example_sentence": "aprovechar", "entry_id": None}
    assert rc.sentence_candidates(word, []) == []


def test_recognition_without_a_sentence_falls_back_to_a_meaning_prompt():
    word = {**WORD, "example_sentence": None, "card": {**WORD["card"], "examples": []}}
    card = build(word=word, encounters=[], entries={})
    assert card["format"] == "meaning_to_word"
    assert card["answer"] == "aprovechar"
    assert card["front"] == {"before": "", "target": "", "after": ""}
    assert card["meaning"] == "to make good use of"


@pytest.mark.parametrize("quiz,card_type,expected", [
    ("recognition_l1", "recognition", "recognition"),
    ("recognition_l1", "production", "meaning_to_word"),
    ("recognition_and_recall", "production", "typed_recall"),
    ("cloze_l1_hint", "production", "cloze"),
    ("l2_only", "production", "cloze"),
    ("l2_only", "recognition", "recognition"),
])
def test_format_follows_the_quiz_flag(quiz, card_type, expected):
    assert build(card_type, quiz, reps=1)["format"] == expected


def test_a_production_card_without_a_usable_sentence_falls_back_to_meaning_to_word():
    word = {**WORD, "example_sentence": None, "card": {**WORD["card"], "examples": []}}
    card = build("production", "cloze_l1_hint", word=word, encounters=[], entries={})
    assert card["format"] == "meaning_to_word"
    assert card["answer"] == "aprovechar"
    assert card["front"]["target"] == ""


@pytest.mark.parametrize("quiz,gloss,tap_gloss,hint", [
    ("recognition_l1", "make use of", "", "make use of"),
    ("recognition_and_recall", "make use of", "", "make use of"),
    ("cloze_l1_hint", "", "make use of", ""),
    ("l2_only", "", "", "to make good use of"),
])
def test_native_language_is_shown_hidden_or_absent_by_level(quiz, gloss, tap_gloss, hint):
    card = build("production", quiz, reps=1)
    assert card["gloss"] == gloss
    assert card["tap_gloss"] == tap_gloss
    assert card["hint"] == hint


def test_level_three_recognition_back_is_target_language_only():
    card = build("recognition", "l2_only")
    assert card["gloss"] == "" and card["tap_gloss"] == ""
    assert card["hint"] == ""


def test_typed_recall_accepts_accent_and_case_insensitive_answers():
    card = build("production", "recognition_and_recall", reps=1)
    assert card["typed"] is True
    assert rc.normalize_answer("  APROVECHÉ ") in card["accepted"]
    assert rc.normalize_answer("aprovechar") in card["accepted"]
    assert "aproveche" in card["accepted"]


def test_the_cloze_front_never_contains_the_answer_at_the_blank():
    card = build("production", "cloze_l1_hint", reps=1)
    assert card["front"]["target"] == card["answer"]
    assert card["front"]["before"].lower().count("aproveché") == 0
    assert card["front"]["after"].lower().count("aproveché") == 0


def test_phrases_are_blanked_as_a_whole():
    word = {"id": "w", "lemma": "echar de menos", "term": "echar de menos",
            "card": {"surface": "echo de menos", "examples": []}, "example_sentence": "Te echo de menos cada día."}
    cut = rc.split_around(word["example_sentence"], rc.word_forms(word), "es")
    assert cut == rc.Cloze("Te ", "echo de menos", " cada día.")


def test_a_word_inside_another_word_is_not_matched():
    assert rc.find_form("Los caballos corren.", ["lo"], "es") is None
    assert rc.find_form("Lo vi ayer.", ["lo"], "es") == (0, 2)


def test_unspaced_languages_match_inside_a_run_of_text():
    cut = rc.split_around("私は毎日学校に行きます。", ["学校"], "ja")
    assert cut == rc.Cloze("私は毎日", "学校", "に行きます。")


def test_the_longest_form_wins_so_a_phrase_is_not_cut_short():
    assert rc.find_form("Te echo de menos.", ["echo", "echo de menos"], "es") == (3, 16)


def test_forms_from_every_copy_of_a_sentence_are_kept():
    """The saved example names the lemma form; the lookup of the same sentence names the inflected one."""
    word = {**WORD, "card": {**WORD["card"], "surface": "aprovechar"}}
    (candidate,) = rc.sentence_candidates(word, [{**ENCOUNTER, "sentence": WORD["example_sentence"]}])
    assert set(candidate.surfaces) == {"aprovechar", "aproveché"}
    card = build(word=word, encounters=[{**ENCOUNTER, "sentence": WORD["example_sentence"]}])
    assert card["front"] == {"before": "", "target": "Aproveché", "after": " la tarde para estudiar."}
