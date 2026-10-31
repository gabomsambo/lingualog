"""The word bank through the API: the offer, an entry written with chosen words, and what it does to the notebook.

An in-memory notebook stands in for the tables; Gemini is mocked, so no test reaches a provider.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import review_scheduler as rs
import server
from ai.gemini import GeminiError
from ai.schemas import JournalFeedback, TargetWordUse
from app.services import review_service, word_bank_service

USER = "00000000-0000-0000-0000-00000000000a"
OTHER = "00000000-0000-0000-0000-00000000000b"
HEADERS = {"X-User-ID": USER}
NOW = datetime.now(timezone.utc)
TEXT = "Ayer madrugué para correr. Aproveché de la tarde. Fue un rato bonito."
ENTRY_ID = "entry-1"


def uid(label):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, label))


W1, W2 = uid("w1"), uid("w2")


class Notebook:
    """Words, cards and encounters, behind the same functions the services call."""

    def __init__(self):
        self.words, self.cards, self.encounters, self.logs = {}, {}, [], []
        self.entries, self.entry_updates = {}, []
        self.quiz = "recognition_l1"

    def word(self, word_id, lemma, status="learning", user=USER, language="es", saved_days_ago=1, **extra):
        self.words[word_id] = {
            "id": word_id, "user_id": user, "language": language, "lemma": lemma, "term": lemma, "status": status,
            "sense": f"sense of {lemma}", "card_status": "ok",
            "created_at": (NOW - timedelta(days=saved_days_ago)).isoformat(),
            "card": {"sense_in_context": f"sense of {lemma}", "gloss_l1": f"gloss of {lemma}"}, **extra,
        }
        return self.words[word_id]

    def card(self, word_id, card_type="recognition", stability=None, reps=0, user=USER, suspended=False, due_in=0,
             last_review_days=5):
        card_id = f"card-{word_id}-{card_type}"
        self.cards[card_id] = {
            "id": card_id, "user_id": user, "word_id": word_id, "language": "es", "card_type": card_type,
            "state": 2 if reps else 1, "step": None, "stability": stability, "difficulty": 5.0 if reps else None,
            "due": (NOW + timedelta(days=due_in)).isoformat(), "reps": reps, "lapses": 0,
            "last_review": (NOW - timedelta(days=last_review_days)).isoformat() if reps else None,
            "suspended_at": NOW.isoformat() if suspended else None, "fsrs_version": "fsrs-6",
        }
        return self.cards[card_id]

    def used(self, word_id, days_ago, kind="used_ok", entry="old-entry"):
        self.encounters.append({
            "id": str(uuid.uuid4()), "user_id": USER, "word_id": word_id, "kind": kind, "surface": "x",
            "source_type": "entry", "source_id": entry, "created_at": (NOW - timedelta(days=days_ago)).isoformat(),
        })

    # --- service seams -----------------------------------------------------------

    def load_notebook_words(self, user_id, language):
        return [dict(w) for w in self.words.values() if w["user_id"] == user_id and w["language"] == language
                and w["status"] in ("new", "learning", "known")]

    def load_recognition_cards_any(self, user_id, word_ids):
        return [dict(c) for c in self.cards.values() if c["user_id"] == user_id and c["card_type"] == "recognition"
                and c["word_id"] in word_ids]

    def load_word_signals(self, user_id, word_ids):
        return [dict(e) for e in self.encounters if e["user_id"] == user_id and e["word_id"] in word_ids]

    def load_words(self, user_id, word_ids):
        return {i: dict(self.words[i]) for i in word_ids if i in self.words and self.words[i]["user_id"] == user_id}

    def load_use_days(self, user_id, word_id):
        from word_bank import use_days
        return use_days(e["created_at"] for e in self.encounters
                        if e["user_id"] == user_id and e["word_id"] == word_id and e["kind"] == "used_ok")

    def load_recognition_card(self, user_id, word_id):
        return next((dict(c) for c in self.cards.values() if c["user_id"] == user_id and c["word_id"] == word_id
                     and c["card_type"] == "recognition"), None)

    def load_production_card(self, user_id, word_id):
        return next((dict(c) for c in self.cards.values() if c["user_id"] == user_id and c["word_id"] == word_id
                     and c["card_type"] == "production"), None)

    def load_card(self, user_id, card_id):
        card = self.cards.get(card_id)
        return dict(card) if card and card["user_id"] == user_id else None

    def insert_cards(self, rows):
        added = []
        for row in rows:
            if any(c["word_id"] == row["word_id"] and c["card_type"] == row["card_type"] for c in self.cards.values()):
                continue
            added.append(self.card(row["word_id"], row["card_type"], user=row["user_id"]))
        return added

    def apply_card_review(self, user_id, card_id, expected_reps, card, log):
        stored = self.cards.get(card_id)
        if not stored or stored["user_id"] != user_id or stored["suspended_at"] or stored["reps"] != expected_reps:
            return None
        stored.update({k: v for k, v in card.items() if k != "lapsed"})
        stored["reps"] += 1
        self.logs.append({**log, "card_id": card_id})
        return dict(stored)

    def update_vocabulary_item(self, item_id, user_id, changes):
        word = self.words.get(item_id)
        if not word or word["user_id"] != user_id:
            return None
        word.update(changes)
        return dict(word)

    def fetch_entry_encounters(self, user_id, entry_id, kinds, word_ids=None):
        return [dict(e) for e in self.encounters if e["user_id"] == user_id and e["source_id"] == entry_id
                and e["kind"] in kinds and (word_ids is None or e["word_id"] in word_ids)]

    def delete_entry_encounters(self, user_id, entry_id, kinds, word_ids=None):
        self.encounters = [e for e in self.encounters if not (
            e["user_id"] == user_id and e["source_id"] == entry_id and e["kind"] in kinds
            and (word_ids is None or e["word_id"] in word_ids))]

    def save_word_encounters(self, rows, user_id):
        saved = [{"id": str(uuid.uuid4()), "user_id": user_id, "created_at": NOW.isoformat(), **row} for row in rows]
        self.encounters += saved
        return saved

    def save_entry(self, entry):
        self.entries[ENTRY_ID] = {**entry, "id": ENTRY_ID, "created_at": NOW.isoformat()}
        return dict(self.entries[ENTRY_ID])

    def update_entry_analysis(self, entry_id, user_id, changes):
        self.entries[entry_id].update(changes)
        self.entry_updates.append(changes)
        return dict(self.entries[entry_id])

    def fetch_single_entry(self, entry_id, user_id):
        entry = self.entries.get(entry_id)
        return {**entry, "content": entry["original_text"]} if entry else None

    def install(self, monkeypatch):
        scheduler = rs.make_scheduler(0.9, fuzz=False)
        patches = {
            word_bank_service: [
                "load_notebook_words", "load_recognition_cards_any", "load_word_signals", "fetch_entry_encounters",
                "delete_entry_encounters", "save_word_encounters", "update_vocabulary_item",
            ],
            review_service: [
                "load_words", "load_use_days", "load_recognition_card", "load_production_card", "apply_card_review",
                "load_card", "insert_cards",
            ],
            server: ["save_entry", "update_entry_analysis", "fetch_single_entry"],
        }
        for module, names in patches.items():
            for name in names:
                monkeypatch.setattr(module, name, getattr(self, name))
        monkeypatch.setattr(review_service, "scheduler_for", lambda user_id, language: scheduler)
        monkeypatch.setattr(
            word_bank_service, "resolve_policy", lambda user_id, language: SimpleNamespace(quiz=self.quiz)
        )
        monkeypatch.setattr(review_service, "update_vocabulary_item", self.update_vocabulary_item)


@pytest.fixture
def book(monkeypatch):
    notebook = Notebook()
    notebook.install(monkeypatch)
    # A local .env may select the offline provider; these tests mock the real one.
    monkeypatch.setattr(server, "AI_PROVIDER", "gemini")
    return notebook


@pytest.fixture
def client():
    return TestClient(server.app, raise_server_exceptions=False)


def feedback(*uses, text=TEXT):
    return JournalFeedback(
        corrected=f"Corrected {text}", rewrite="Rewrite", score=80, tone="Neutral", explanation="Fine.",
        rubric={"grammar": 80, "vocabulary": 80, "complexity": 80}, grammar_suggestions=[], new_words=[],
        sentence_mapping=[{"source_sentence": 0, "corrected_sentences": [0]}], sentence_actions=[],
        target_word_uses=list(uses),
    )


def correct(term, form):
    return TargetWordUse(term=term, status="used_correctly", form_in_text=form)


def submit(client, word_ids, challenge=(), uses=(), text=TEXT, user=USER, gemini=None):
    gemini = gemini or AsyncMock(return_value=feedback(*uses, text=text))
    with patch("server.fetch_user_profile_settings", new=AsyncMock(return_value=None)), \
            patch("server.generate_structured", new=gemini):
        response = client.post(
            "/log-entry",
            json={"text": text, "title": "t", "target_word_ids": word_ids, "challenge_word_ids": list(challenge)},
            headers={"X-User-ID": user},
        )
    return response, gemini


# --- GET /word-bank ----------------------------------------------------------------------


def test_the_bank_offers_the_learners_words_for_one_language_with_why(book, client):
    book.word(uid("due"), "aprovechar")
    book.card(uid("due"), stability=3.0, reps=3, due_in=-2, last_review_days=20)
    book.word(uid("fresh"), "rato", "new", saved_days_ago=0)
    book.word(uid("french"), "bouger", language="fr")
    book.word(uid("theirs"), "madrugar", user=OTHER)
    book.word(uid("done"), "banco", "mastered")

    body = client.get("/word-bank", params={"language": "es"}, headers=HEADERS).json()
    assert [(w["word_id"], w["reason"]) for w in body["words"]] == [
        (uid("due"), "at_risk"), (uid("fresh"), "never_used")]
    first = body["words"][0]
    assert first["lemma"] == "aprovechar" and first["forms"] == ["aprovechar"]
    assert first["hint"] == "gloss of aprovechar" and first["hint_mode"] == "shown"


def test_the_chip_hint_follows_the_policy_and_exclude_reshuffles(book, client):
    for index in range(4):
        book.word(uid(f"w{index}"), f"palabra{index}", "new", saved_days_ago=index)
    book.quiz = "cloze_l1_hint"
    shown = client.get("/word-bank", params={"language": "es", "count": 2}, headers=HEADERS).json()["words"]
    assert [w["word_id"] for w in shown] == [uid("w0"), uid("w1")]
    assert {w["hint_mode"] for w in shown} == {"tap"}
    more = client.get(
        "/word-bank", params={"language": "es", "count": 2, "exclude": [w["word_id"] for w in shown]}, headers=HEADERS
    ).json()["words"]
    assert [w["word_id"] for w in more] == [uid("w2"), uid("w3")]


def test_forms_the_learner_met_or_wrote_become_the_forms_the_ticks_match(book, client):
    book.word(W1, "madrugar", "new")
    book.encounters.append({"user_id": USER, "word_id": W1, "kind": "lookup", "surface": "madrugué",
                            "created_at": NOW.isoformat()})
    book.encounters.append({"user_id": USER, "word_id": W1, "kind": "lookup",
                            "surface": "una frase pegada muy larga de verdad", "created_at": NOW.isoformat()})
    words = client.get("/word-bank", params={"language": "es"}, headers=HEADERS).json()["words"]
    assert words[0]["forms"] == ["madrugar", "madrugué"]


def test_the_bank_needs_a_user_and_a_valid_language(book, client):
    assert client.get("/word-bank", params={"language": "es"}).status_code == 401
    assert client.get("/word-bank", params={"language": "Spanish"}, headers=HEADERS).status_code == 400
    assert client.get("/word-bank", params={"language": "es", "count": 20}, headers=HEADERS).status_code == 422


# --- An entry written with chosen words ---------------------------------------------------


def test_a_correct_use_is_kept_as_a_production_encounter_with_its_sentence(book, client):
    book.word(W1, "madrugar", "new")
    response, gemini = submit(client, [W1], uses=[correct("madrugar", "madrugué")])

    assert response.status_code == 201
    sent = gemini.call_args.args
    assert "- madrugar" in sent[1] and "**TARGET WORDS:**" in sent[0]
    [encounter] = book.encounters
    assert (encounter["kind"], encounter["source_type"], encounter["source_id"]) == ("used_ok", "entry", ENTRY_ID)
    assert encounter["surface"] == "madrugué" and encounter["sentence"] == "Ayer madrugué para correr."
    assert encounter["word_id"] == W1 and encounter["language"] == "es" and encounter["created_at"] == NOW.isoformat()
    [use] = response.json()["target_word_uses"]
    assert (use["status"], use["word_status"], use["credited"], use["became_mastered"]) == (
        "used_correctly", "new", False, False)
    assert book.entries[ENTRY_ID]["target_words"] == [
        {"word_id": W1, "lemma": "madrugar", "term": "madrugar", "challenge": False}]
    assert book.entries[ENTRY_ID]["target_word_uses"][0]["word_status"] == "new"


def test_an_error_is_shown_with_its_fix_and_is_not_credit(book, client):
    book.word(W1, "aprovechar")
    use = TargetWordUse(term="aprovechar", status="used_with_error", form_in_text="Aproveché de la tarde",
                        fix="Aproveché la tarde", note="Sin «de».")
    body = submit(client, [W1], uses=[use])[0].json()

    [row] = body["target_word_uses"]
    assert (row["status"], row["fix"], row["note"]) == ("used_with_error", "Aproveché la tarde", "Sin «de».")
    assert [e["kind"] for e in book.encounters] == ["used_error"]
    assert book.load_use_days(USER, W1) == 0


def test_an_unclear_use_is_asked_about_and_leaves_no_evidence_either_way(book, client):
    book.word(W1, "rato")
    use = TargetWordUse(
        term="rato", status="unclear", form_in_text="un rato bonito", note="¿Querías decir «momento»?"
    )
    body = submit(client, [W1], uses=[use])[0].json()

    [row] = body["target_word_uses"]
    assert row["status"] == "unclear" and row["note"].startswith("¿Querías")
    assert book.encounters == [] and book.logs == []
    assert book.words[W1]["status"] == "learning"


def test_a_word_not_used_is_reported_and_costs_nothing(book, client):
    book.word(W1, "banco")
    body = submit(client, [W1], uses=[TargetWordUse(term="banco", status="not_used")])[0].json()
    assert [u["status"] for u in body["target_word_uses"]] == ["not_used"]
    assert book.encounters == []


def test_a_use_the_text_does_not_contain_is_not_recorded(book, client):
    book.word(W1, "banco")
    body = submit(client, [W1], uses=[correct("banco", "bancos")])[0].json()
    assert body["target_word_uses"] == []
    assert book.encounters == [] and "target_word_uses" in book.entries[ENTRY_ID]
    assert book.entries[ENTRY_ID]["target_word_uses"] == []


def test_someone_elses_word_a_wrong_language_or_an_ignored_word_is_dropped_from_the_request(book, client):
    book.word(uid("mine"), "madrugar")
    book.word(uid("theirs"), "rato", user=OTHER)
    book.word(uid("french"), "bouger", language="fr")
    book.word(uid("ignored"), "banco", "ignored")
    response, gemini = submit(
        client, [uid("mine"), uid("theirs"), uid("french"), uid("ignored"), str(uuid.uuid4())])
    assert response.status_code == 201
    assert "- madrugar" in gemini.call_args.args[1]
    for other in ("rato", "bouger", "banco"):
        assert f"- {other}" not in gemini.call_args.args[1]
    assert [t["word_id"] for t in book.entries[ENTRY_ID]["target_words"]] == [uid("mine")]


def test_an_entry_without_chosen_words_touches_none_of_it(book, client):
    response, gemini = submit(client, [], uses=[correct("madrugar", "madrugué")])
    assert response.status_code == 201
    assert "**TARGET WORDS:**" not in gemini.call_args.args[0]
    assert response.json()["target_word_uses"] is None
    assert "target_words" not in book.entries[ENTRY_ID] and "target_word_uses" not in book.entries[ENTRY_ID]
    assert book.encounters == []


def test_a_failed_analysis_keeps_the_chosen_words_but_records_no_uses(book, client):
    book.word(W1, "madrugar")
    response, _ = submit(client, [W1], gemini=AsyncMock(side_effect=GeminiError("ai_timeout", "slow")))
    assert response.status_code == 503
    saved = book.entries[ENTRY_ID]
    assert saved["analysis_status"] == "failed" and saved["target_words"][0]["word_id"] == W1
    assert "target_word_uses" not in saved
    assert book.encounters == [] and book.logs == []


def test_a_failure_while_recording_never_fails_the_submission(book, client, monkeypatch):
    book.word(W1, "madrugar")
    monkeypatch.setattr(word_bank_service, "save_word_encounters", lambda *_: (_ for _ in ()).throw(RuntimeError("db")))
    response, _ = submit(client, [W1], uses=[correct("madrugar", "madrugué")])
    assert response.status_code == 201
    assert response.json()["target_word_uses"][0]["status"] == "used_correctly"


# --- Mastered --------------------------------------------------------------------------------


def test_known_and_used_correctly_on_a_second_day_becomes_mastered(book, client):
    book.word(W1, "madrugar", "known")
    book.card(W1, stability=30.0, reps=6, suspended=True)
    book.used(W1, days_ago=3)
    body = submit(client, [W1], uses=[correct("madrugar", "madrugué")])[0].json()

    [row] = body["target_word_uses"]
    assert (row["word_status"], row["became_mastered"], row["use_days"]) == ("mastered", True, 2)
    assert book.words[W1]["status"] == "mastered"


def test_two_uses_on_the_same_day_are_one_day(book, client):
    book.word(W1, "madrugar", "known")
    book.card(W1, stability=30.0, reps=6)
    book.used(W1, days_ago=0)
    row = submit(client, [W1], uses=[correct("madrugar", "madrugué")])[0].json()["target_word_uses"][0]
    assert (row["word_status"], row["use_days"]) == ("known", 1)
    assert book.words[W1]["status"] == "known"


@pytest.mark.parametrize("stability", [None, 20.0])
def test_used_twice_but_not_yet_stable_stays_unmastered(book, client, stability):
    book.word(W1, "madrugar")
    book.card(W1, stability=stability, reps=2)
    book.used(W1, days_ago=4)
    row = submit(client, [W1], uses=[correct("madrugar", "madrugué")])[0].json()["target_word_uses"][0]
    assert (row["word_status"], row["became_mastered"], row["use_days"]) == ("learning", False, 2)


def test_a_word_known_only_by_a_tap_is_not_mastered_by_writing(book, client):
    book.word(W1, "madrugar", "known")
    book.used(W1, days_ago=4)
    row = submit(client, [W1], uses=[correct("madrugar", "madrugué")])[0].json()["target_word_uses"][0]
    assert row["word_status"] == "known" and book.words[W1]["status"] == "known"


def almost_known(book):
    book.word(W1, "madrugar")
    card = book.card(W1, stability=25.0, reps=4, due_in=-1)
    card["last_review"] = (NOW - timedelta(days=25)).isoformat()
    return card


def test_a_review_that_makes_the_word_known_masters_it_when_the_writing_evidence_is_there(book):
    card = almost_known(book)
    book.used(W1, days_ago=9)
    book.used(W1, days_ago=2)
    body = review_service.submit_review(USER, card["id"], "got_it", now=NOW)
    assert body["status"] == "mastered" and book.words[W1]["status"] == "mastered"


def test_a_review_that_makes_the_word_known_without_writing_evidence_is_only_known(book):
    card = almost_known(book)
    book.used(W1, days_ago=2)
    assert review_service.submit_review(USER, card["id"], "got_it", now=NOW)["status"] == "known"
    assert book.words[W1]["status"] == "known"


# --- FSRS credit -------------------------------------------------------------------------------


def stable_word(book, production_reps=0):
    book.word(W1, "madrugar")
    book.card(W1, stability=10.0, reps=4)
    book.card(W1, "production", stability=3.0 if production_reps else None, reps=production_reps, due_in=1)


def test_a_correct_use_with_the_word_hidden_is_a_got_it_on_the_production_card(book, client):
    stable_word(book)
    row = submit(client, [W1], challenge=[W1], uses=[correct("madrugar", "madrugué")])[0].json()["target_word_uses"][0]
    assert row["credited"] is True
    [log] = book.logs
    assert (log["rating"], log["source"], log["card_id"]) == (3, "challenge_use", f"card-{W1}-production")
    assert book.cards[f"card-{W1}-production"]["reps"] == 1
    assert book.entries[ENTRY_ID]["target_words"][0]["challenge"] is True


def test_a_use_with_the_word_on_screen_is_not_a_review(book, client):
    stable_word(book)
    row = submit(client, [W1], uses=[correct("madrugar", "madrugué")])[0].json()["target_word_uses"][0]
    assert row["credited"] is False and book.logs == []


def test_an_error_or_a_question_earns_no_credit_even_in_challenge_mode(book, client):
    stable_word(book)
    error = TargetWordUse(term="madrugar", status="used_with_error", form_in_text="madrugué", fix="x", note="y")
    submit(client, [W1], challenge=[W1], uses=[error])
    unclear = TargetWordUse(term="madrugar", status="unclear", form_in_text="madrugué", note="?")
    submit(client, [W1], challenge=[W1], uses=[unclear])
    assert book.logs == []


def test_no_production_card_yet_means_no_credit_and_no_invented_card(book, client):
    book.word(W1, "madrugar")
    book.card(W1, stability=3.0, reps=2)
    row = submit(client, [W1], challenge=[W1], uses=[correct("madrugar", "madrugué")])[0].json()["target_word_uses"][0]
    assert row["credited"] is False and book.logs == []
    assert len(book.cards) == 1


def test_a_challenge_id_for_a_word_that_was_not_chosen_is_ignored(book, client):
    stable_word(book)
    book.word(W2, "rato")
    submit(client, [W2], challenge=[W1], uses=[correct("rato", "rato")])
    assert book.logs == []


# --- Retrying an analysis -------------------------------------------------------------------------


def retry(client, uses, text=TEXT):
    with patch("server.fetch_user_profile_settings", new=AsyncMock(return_value=None)), \
            patch("server.generate_structured", new=AsyncMock(return_value=feedback(*uses, text=text))):
        return client.post(f"/entries/{ENTRY_ID}/analyze", headers=HEADERS)


def test_retrying_checks_the_same_words_and_replaces_rather_than_doubles_the_evidence(book, client):
    stable_word(book)
    submit(client, [W1], challenge=[W1], uses=[correct("madrugar", "madrugué")])
    assert len(book.encounters) == 1 and len(book.logs) == 1

    assert retry(client, [correct("madrugar", "madrugué")]).status_code == 200
    assert len(book.encounters) == 1
    assert len(book.logs) == 1, "an entry credits a word once"
    assert book.entries[ENTRY_ID]["target_word_uses"][0]["status"] == "used_correctly"


def test_a_retry_that_finds_an_error_replaces_the_earlier_correct_use(book, client):
    book.word(W1, "aprovechar")
    submit(client, [W1], uses=[correct("aprovechar", "Aproveché")])
    error = TargetWordUse(term="aprovechar", status="used_with_error", form_in_text="Aproveché de la tarde",
                          fix="Aproveché la tarde", note="x")
    retry(client, [error])
    assert [e["kind"] for e in book.encounters] == ["used_error"]


def test_retrying_a_failed_entry_uses_the_words_it_was_written_with(book, client):
    book.word(W1, "madrugar", "new")
    submit(client, [W1], gemini=AsyncMock(side_effect=GeminiError("ai_timeout", "slow")))
    response = retry(client, [correct("madrugar", "madrugué")])
    assert response.status_code == 200
    assert response.json()["target_word_uses"][0]["status"] == "used_correctly"
    assert [e["kind"] for e in book.encounters] == ["used_ok"]


def test_moving_an_entry_to_another_language_forgets_its_words_and_their_evidence(book, client):
    book.word(W1, "madrugar", "new")
    submit(client, [W1], uses=[correct("madrugar", "madrugué")])
    assert len(book.encounters) == 1
    with patch("server._studied_languages", return_value={"fr": True}), \
            patch("server.fetch_user_profile_settings", new=AsyncMock(return_value=None)), \
            patch("server.generate_structured", new=AsyncMock(return_value=feedback())):
        response = client.post(f"/entries/{ENTRY_ID}/analyze", json={"target_language": "fr"}, headers=HEADERS)
    assert response.status_code == 200
    assert book.encounters == []
    assert book.entries[ENTRY_ID]["target_words"] == [] and book.entries[ENTRY_ID]["target_word_uses"] == []


def test_deleting_an_entry_removes_the_uses_it_recorded(book, client):
    book.word(W1, "madrugar", "new")
    submit(client, [W1], uses=[correct("madrugar", "madrugué")])
    book.used(W1, days_ago=1, entry="other-entry")
    with patch("server.delete_entry", return_value=True):
        assert client.delete(f"/entries/{ENTRY_ID}", headers=HEADERS).status_code == 204
    assert [e["source_id"] for e in book.encounters] == ["other-entry"]


# --- Reviews and lookups keep working with these encounters ---------------------------------------


def test_a_use_with_a_mistake_is_never_a_review_front():
    from review_cards import sentence_candidates

    word = {"card": {}, "example_sentence": None, "entry_id": None}
    encounters = [
        {"sentence": "Aproveché de la tarde.", "surface": "Aproveché", "kind": "used_error",
         "source_type": "entry", "source_id": "e1", "created_at": "1"},
        {"sentence": "Ayer madrugué para correr.", "surface": "madrugué", "kind": "used_ok",
         "source_type": "entry", "source_id": "e1", "created_at": "2"},
    ]
    assert [c.sentence for c in sentence_candidates(word, encounters)] == ["Ayer madrugué para correr."]


def test_the_offline_provider_shows_a_sample_check_but_never_counts_it(book, client, monkeypatch):
    monkeypatch.setattr(server, "AI_PROVIDER", "mock")
    book.word(W1, "rato", "known")
    book.card(W1, stability=30.0, reps=6)
    book.used(W1, days_ago=3)
    book.word(W2, "banco", "new")
    with patch("server.fetch_user_profile_settings", new=AsyncMock(return_value=None)):
        body = client.post(
            "/log-entry",
            json={"text": TEXT, "title": "t", "target_word_ids": [W1, W2], "challenge_word_ids": [W1]},
            headers=HEADERS,
        ).json()
    assert body["is_mock"] is True
    assert [(u["term"], u["status"]) for u in body["target_word_uses"]] == [
        ("rato", "used_correctly"), ("banco", "not_used")]
    assert len(book.encounters) == 1, "only the evidence that was there before"
    assert book.words[W1]["status"] == "known" and book.logs == []


def test_a_retry_that_no_longer_backs_up_a_use_removes_the_evidence_it_recorded(book, client):
    book.word(W1, "madrugar", "new")
    submit(client, [W1], uses=[correct("madrugar", "madrugué")])
    assert len(book.encounters) == 1
    # The tutor now claims a use the text does not hold, which is dropped.
    retry(client, [correct("madrugar", "madrugaba")])
    assert book.encounters == []
    assert book.entries[ENTRY_ID]["target_word_uses"] == []


def test_the_entry_page_payload_carries_the_target_words_and_their_uses():
    from app.models import JournalEntry
    from database import shape_entry_for_api

    flat = {
        "id": str(uuid.uuid4()), "user_id": USER, "language": "es", "original_text": "Hola", "analysis_status": "ok",
        "created_at": NOW.isoformat(), "updated_at": NOW.isoformat(), "corrected": "Hola",
        "target_words": [{"word_id": W1, "lemma": "rato", "term": "rato", "challenge": False}],
        "target_word_uses": [{"word_id": W1, "term": "rato", "status": "not_used"}],
    }
    entry = JournalEntry(**shape_entry_for_api(flat)).model_dump(mode="json")
    assert entry["target_word_uses"] == [{"word_id": W1, "term": "rato", "status": "not_used"}]
    assert entry["target_words"][0]["lemma"] == "rato"
    bare = JournalEntry(**shape_entry_for_api({**flat, "target_words": None, "target_word_uses": None}))
    assert bare.target_word_uses is None
