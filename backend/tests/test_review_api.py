"""Review sessions and answers through the API, against an in-memory copy of the review tables."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import review_scheduler as rs
import server
from app.models import UserSettings
from app.services import review_service

USER = "00000000-0000-0000-0000-00000000000a"
OTHER = "00000000-0000-0000-0000-00000000000b"
NOW = datetime.now(timezone.utc)
HEADERS = {"X-User-ID": USER}


def iso(delta=timedelta()):
    return (NOW + delta).isoformat()


class FakeDb:
    """Just enough of the tables behind review_service, with the same rules as the SQL."""

    def __init__(self):
        self.cards, self.logs, self.words, self.encounters, self.entries = {}, [], {}, [], {}
        self.profiles = {}
        self.word_updates = []
        self.quiz = "recognition_l1"

    def add_word(self, word_id="w1", user=USER, language="es", status="learning", card_status="ok", **extra):
        word = {
            "id": word_id, "user_id": user, "language": language, "lemma": "aprovechar", "term": "aprovechar",
            "status": status, "card_status": card_status, "entry_id": None,
            "example_sentence": "Voy a aprovechar el día.",
            "card": {"lemma": "aprovechar", "surface": "aprovechar", "sense_in_context": "to make use of",
                     "gloss_l1": "make use of", "examples": ["Hay que aprovechar el sol."]},
            **extra,
        }
        self.words[word_id] = word
        return word

    def add_card(self, card_id="c1", word_id="w1", user=USER, language="es", card_type="recognition", **extra):
        card = {
            "id": card_id, "user_id": user, "word_id": word_id, "language": language, "card_type": card_type,
            "state": 1, "step": None, "stability": None, "difficulty": None, "stability_fast": None,
            "due": iso(), "last_review": None, "first_reviewed_at": None, "reps": 0, "lapses": 0,
            "fsrs_version": "fsrs-6", "suspended_at": None, "created_at": iso(timedelta(minutes=-5)),
            **extra,
        }
        self.cards[card_id] = card
        return card

    def add_reviewed(self, card_id, word_id, days_ago, stability=5.0, **extra):
        due = NOW - timedelta(days=days_ago)
        if word_id not in self.words:
            self.add_word(word_id)
        return self.add_card(
            card_id, word_id, state=2, stability=stability, difficulty=5.0, reps=3,
            last_review=(due - timedelta(days=5)).isoformat(), due=due.isoformat(),
            first_reviewed_at=(due - timedelta(days=9)).isoformat(), **extra,
        )

    # --- the functions review_service loads and stores through -----------------

    def load_review_settings(self, user_id, language):
        row = self.profiles.get((user_id, language), {})
        return row.get("daily_new_words", 10), row.get("desired_retention", 0.9)

    def load_fsrs_parameters(self, user_id, language):
        return None

    def load_active_cards(self, user_id, language, now):
        return [
            dict(c) for c in sorted(self.cards.values(), key=lambda card: card["due"])
            if c["user_id"] == user_id and c["suspended_at"] is None
            and (language is None or c["language"] == language)
            and self.words[c["word_id"]]["card_status"] == "ok"
            and (c["reps"] == 0 or rs.aware(c["due"]) <= now)
        ]

    def load_recognition_cards(self, user_id, word_ids):
        return [
            dict(c) for c in self.cards.values()
            if c["user_id"] == user_id and c["suspended_at"] is None
            and c["card_type"] == "recognition" and c["word_id"] in word_ids
        ]

    def load_card(self, user_id, card_id):
        card = self.cards.get(card_id)
        return dict(card) if card and card["user_id"] == user_id else None

    def load_recognition_card(self, user_id, word_id):
        return next((dict(c) for c in self.cards.values()
                     if c["user_id"] == user_id and c["word_id"] == word_id and c["card_type"] == "recognition"), None)

    def load_words(self, user_id, word_ids):
        return {i: dict(self.words[i]) for i in word_ids if i in self.words and self.words[i]["user_id"] == user_id}

    def load_encounters(self, user_id, word_ids):
        return [e for e in self.encounters if e["word_id"] in word_ids and e.get("user_id", user_id) == user_id]

    def load_entries(self, user_id, entry_ids):
        return {i: self.entries[i] for i in entry_ids if i in self.entries}

    def count_new_words_today(self, user_id, language, now):
        start = rs.day_start(now)
        return len([
            c for c in self.cards.values()
            if c["user_id"] == user_id and c["language"] == language and c["card_type"] == "recognition"
            and c["first_reviewed_at"] and rs.aware(c["first_reviewed_at"]) >= start
        ])

    def count_reviews_today(self, user_id, language, now):
        start = rs.day_start(now)
        return len([
            log for log in self.logs
            if log["user_id"] == user_id and log["language"] == language and rs.aware(log["reviewed_at"]) >= start
        ])

    def load_learning_words(self, user_id, language=None):
        return [
            {"id": w["id"], "language": w["language"]} for w in self.words.values()
            if w["user_id"] == user_id and w["status"] == "learning" and (language is None or w["language"] == language)
        ]

    def load_card_word_ids(self, user_id, word_ids):
        return {c["word_id"] for c in self.cards.values()
                if c["user_id"] == user_id and c["card_type"] == "recognition" and c["word_id"] in word_ids}

    def insert_cards(self, rows):
        added = []
        for row in rows:
            if any(c["word_id"] == row["word_id"] and c["card_type"] == row["card_type"] for c in self.cards.values()):
                continue
            added.append(self.add_card(str(uuid.uuid4()), row["word_id"], row["user_id"], row["language"],
                                       row["card_type"], **({"due": row["due"]} if "due" in row else {})))
        return added

    def set_cards_suspended(self, user_id, word_id, suspended):
        for card in self.cards.values():
            if card["user_id"] == user_id and card["word_id"] == word_id:
                if suspended:
                    card["suspended_at"] = card["suspended_at"] or iso()
                else:
                    card["suspended_at"] = None

    def suspend_inactive_cards(self, user_id, language=None):
        for card in self.cards.values():
            word = self.words[card["word_id"]]
            if (card["user_id"] == user_id and card["suspended_at"] is None
                    and word["status"] in ("new", "known", "ignored")
                    and (language is None or card["language"] == language)):
                card["suspended_at"] = iso()

    def apply_card_review(self, user_id, card_id, expected_reps, card, log):
        stored = self.cards.get(card_id)
        if not stored or stored["user_id"] != user_id or stored["suspended_at"] or stored["reps"] != expected_reps:
            return None
        stored.update({k: v for k, v in card.items() if k != "lapsed"})
        stored["first_reviewed_at"] = stored["first_reviewed_at"] or card["last_review"]
        stored["reps"] += 1
        stored["lapses"] += int(card["lapsed"])
        self.logs.append({**log, "user_id": user_id, "card_id": card_id, "language": stored["language"]})
        return dict(stored)

    def update_vocabulary_item(self, item_id, user_id, changes):
        word = self.words.get(item_id)
        if not word or word["user_id"] != user_id:
            return None
        word.update(changes)
        self.word_updates.append((item_id, changes))
        return dict(word)

    def install(self, monkeypatch):
        for name in (
            "load_review_settings", "load_fsrs_parameters", "load_active_cards", "load_recognition_cards", "load_card",
            "load_recognition_card", "load_words", "load_encounters", "load_entries", "count_new_words_today",
            "count_reviews_today", "load_learning_words", "load_card_word_ids", "insert_cards",
            "set_cards_suspended", "suspend_inactive_cards", "apply_card_review", "update_vocabulary_item",
        ):
            monkeypatch.setattr(review_service, name, getattr(self, name))
        real = rs.make_scheduler
        monkeypatch.setattr(review_service, "make_scheduler", lambda r=0.9, p=None, fuzz=True: real(r, p, fuzz=False))
        monkeypatch.setattr(review_service, "resolve_policy", lambda user_id, language: SimpleNamespace(quiz=self.quiz))
        monkeypatch.setattr(
            review_service, "list_language_profiles",
            lambda user_id: [{"l2": l, "active": True} for l in sorted({c["language"] for c in self.cards.values()
                                                                        if c["user_id"] == user_id})],
        )


@pytest.fixture
def db(monkeypatch):
    fake = FakeDb()
    fake.install(monkeypatch)
    return fake


@pytest.fixture
def client():
    return TestClient(server.app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def no_model_calls(monkeypatch):
    """Review costs no model calls: any attempt to reach Gemini fails the test."""
    def forbidden(*_args, **_kwargs):
        raise AssertionError("review must not call a model")

    monkeypatch.setattr("ai.gemini.generate_structured", forbidden)
    monkeypatch.setattr("ai.word_card.generate_structured", forbidden)
    monkeypatch.setattr(server, "generate_word_card", forbidden)


def session(client, language="es", **params):
    return client.get("/review/session", params={"language": language, **params}, headers=HEADERS)


# --- Sessions ----------------------------------------------------------------------


def test_session_shows_the_learners_own_sentence_with_the_word_marked(db, client):
    db.add_word("w1")
    db.add_card("c1", "w1")
    body = session(client).json()
    card = body["cards"][0]
    assert card["card_id"] == "c1"
    assert card["format"] == "recognition"
    assert card["front"] == {"before": "Voy a ", "target": "aprovechar", "after": " el día."}
    assert card["meaning"] == "to make use of"
    assert card["is_new"] is True
    assert body["counts"]["total"] == 1


def test_a_word_in_study_without_a_card_gets_one(db, client):
    db.add_word("w1", status="learning")
    assert session(client).json()["counts"]["new_available"] == 1
    assert [c["card_type"] for c in db.cards.values()] == ["recognition"]


def test_words_not_in_study_get_no_card(db, client):
    for index, status in enumerate(["new", "known", "ignored"]):
        db.add_word(f"w{index}", status=status)
    assert session(client).json()["cards"] == []
    assert db.cards == {}


def test_words_whose_card_failed_are_not_offered(db, client):
    db.add_word("w1", card_status="failed")
    db.add_card("c1", "w1")
    assert session(client).json()["cards"] == []


def test_session_respects_the_daily_new_word_limit(db, client):
    for index in range(14):
        db.add_word(f"w{index}")
        db.add_card(f"c{index}", f"w{index}")
    db.profiles[(USER, "es")] = {"daily_new_words": 5}
    body = session(client).json()
    assert len(body["cards"]) == 5
    assert body["counts"]["new_remaining"] == 5
    assert body["settings"] == {
        "daily_new_words": 5, "desired_retention": 0.9, "catchup_daily_budget": rs.CATCHUP_DAILY_REVIEWS,
    }


def test_words_started_today_use_up_the_limit(db, client):
    for index in range(4):
        db.add_word(f"w{index}")
        db.add_card(f"c{index}", f"w{index}")
    db.add_word("seen")
    just_now = max(NOW - timedelta(minutes=2), rs.day_start(NOW)).isoformat()
    db.add_card("seen", "seen", reps=1, first_reviewed_at=just_now, last_review=just_now,
                state=1, step=1, due=iso(timedelta(minutes=8)), stability=2.3)
    db.profiles[(USER, "es")] = {"daily_new_words": 2}
    body = session(client).json()
    assert [c["card_id"] for c in body["cards"]] == ["c0"]
    assert body["counts"]["new_remaining"] == 1


def test_due_reviews_come_before_new_words(db, client):
    db.add_reviewed("old", "wo", days_ago=3)
    db.add_word("wn")
    db.add_card("new", "wn")
    cards = session(client).json()["cards"]
    assert [c["card_id"] for c in cards] == ["old", "new"]
    assert cards[0]["is_new"] is False


def test_the_session_only_holds_the_callers_cards(db, client):
    db.add_word("mine")
    db.add_card("c-mine", "mine")
    db.add_word("theirs", user=OTHER)
    db.add_card("c-theirs", "theirs", user=OTHER)
    assert [c["card_id"] for c in session(client).json()["cards"]] == ["c-mine"]


def test_session_only_holds_the_requested_language(db, client):
    db.add_word("es1", language="es")
    db.add_card("c-es", "es1")
    db.add_word("fr1", language="fr")
    db.add_card("c-fr", "fr1", language="fr")
    assert [c["card_id"] for c in session(client, "fr").json()["cards"]] == ["c-fr"]


def test_catch_up_serves_a_slice_of_the_backlog_and_no_new_words(db, client):
    for index in range(60):
        db.add_reviewed(f"r{index}", f"w{index}", days_ago=10 + index / 10)
    db.add_word("fresh")
    db.add_card("fresh", "fresh")
    normal = session(client).json()
    assert normal["counts"]["suggest_catchup"] is True
    assert normal["counts"]["backlog"] == 60

    body = session(client, mode="catchup").json()
    assert len(body["cards"]) == 20
    assert all(not card["is_new"] for card in body["cards"])
    assert body["catchup"] == {"daily_budget": rs.CATCHUP_DAILY_REVIEWS, "done_today": 0}


def test_catch_up_stops_once_todays_budget_is_spent(db, client):
    for index in range(60):
        db.add_reviewed(f"r{index}", f"w{index}", days_ago=10)
    for _ in range(rs.CATCHUP_DAILY_REVIEWS):
        db.logs.append({"user_id": USER, "language": "es", "reviewed_at": iso(timedelta(minutes=-1)), "rating": 3})
    body = session(client, mode="catchup").json()
    assert body["cards"] == []
    assert body["catchup"]["done_today"] == rs.CATCHUP_DAILY_REVIEWS


def test_each_language_reads_its_own_quiz_flag(db, client):
    db.add_reviewed("p1", "w1", days_ago=2, card_type="production")
    db.quiz = "recognition_and_recall"
    card = session(client).json()["cards"][0]
    assert card["format"] == "typed_recall"
    assert card["typed"] is True


def test_session_input_is_validated(db, client):
    assert session(client, "not a language").status_code == 400
    assert session(client, mode="forever").status_code == 422
    assert session(client, limit=0).status_code == 422
    assert client.get("/review/session", params={"language": "es"}).status_code == 401
    assert client.get("/review/session", headers=HEADERS).status_code == 422


# --- Answers -----------------------------------------------------------------------


def answer(client, card_id, rating="got_it", **body):
    return client.post(f"/review/{card_id}", json={"rating": rating, **body}, headers=HEADERS)


def test_answering_a_new_card_starts_its_schedule(db, client):
    card_id = str(uuid.uuid4())
    db.add_word("w1")
    db.add_card(card_id, "w1")
    response = answer(client, card_id, "got_it", duration_ms=4200)
    body = response.json()
    assert response.status_code == 200
    assert body["reps"] == 1
    assert body["requeue"] is True
    assert body["status"] == "learning"
    stored = db.cards[card_id]
    assert stored["reps"] == 1 and stored["state"] == 1 and stored["step"] == 1
    assert stored["first_reviewed_at"] is not None
    assert db.logs == [{
        "rating": 3, "reviewed_at": db.logs[0]["reviewed_at"], "duration_ms": 4200, "source": "review",
        "user_id": USER, "card_id": card_id, "language": "es",
    }]


def test_again_logs_rating_one(db, client):
    card_id = str(uuid.uuid4())
    db.add_word("w1")
    db.add_card(card_id, "w1")
    assert answer(client, card_id, "again").status_code == 200
    assert db.logs[0]["rating"] == 1
    assert db.cards[card_id]["step"] == 0


def test_only_the_two_buttons_are_accepted(db, client):
    card_id = str(uuid.uuid4())
    db.add_word("w1")
    db.add_card(card_id, "w1")
    for rating in ("hard", "easy", "good", 3, ""):
        assert answer(client, card_id, rating).status_code == 422
    assert db.logs == []


def test_a_lapse_is_counted_and_the_word_goes_back_to_learning(db, client):
    card_id = str(uuid.uuid4())
    db.add_reviewed(card_id, "w1", days_ago=1, stability=40.0)
    db.words["w1"]["status"] = "known"
    body = answer(client, card_id, "again").json()
    assert db.cards[card_id]["lapses"] == 1
    assert db.cards[card_id]["state"] == 3
    assert body["status"] == "learning"
    assert db.words["w1"]["status"] == "learning"


def test_a_word_becomes_known_when_its_recognition_card_is_stable(db, client):
    card_id = str(uuid.uuid4())
    db.add_reviewed(card_id, "w1", days_ago=0, stability=30.0)
    body = answer(client, card_id).json()
    assert body["status"] == "known"
    assert db.words["w1"]["status"] == "known"
    assert db.cards[card_id]["suspended_at"] is None


def test_a_word_stays_learning_after_one_correct_answer(db, client):
    card_id = str(uuid.uuid4())
    db.add_word("w1")
    db.add_card(card_id, "w1")
    answer(client, card_id)
    assert db.words["w1"]["status"] == "learning"
    assert db.word_updates == []


def test_mastered_words_keep_their_state(db, client):
    card_id = str(uuid.uuid4())
    db.add_reviewed(card_id, "w1", days_ago=0, stability=2.0)
    db.words["w1"]["status"] = "mastered"
    assert answer(client, card_id, "again").json()["status"] == "mastered"


def test_a_production_card_is_added_once_recognition_is_stable(db, client):
    card_id = str(uuid.uuid4())
    db.add_reviewed(card_id, "w1", days_ago=0, stability=9.0)
    body = answer(client, card_id).json()
    assert body["production_card_added"] is True
    production = [c for c in db.cards.values() if c["card_type"] == "production"]
    assert len(production) == 1
    assert rs.aware(production[0]["due"]) > NOW + timedelta(hours=20)

    db.cards[card_id]["due"] = iso()
    assert answer(client, card_id).json()["production_card_added"] is False
    assert len([c for c in db.cards.values() if c["card_type"] == "production"]) == 1


def test_no_production_card_while_recognition_is_still_short(db, client):
    card_id = str(uuid.uuid4())
    db.add_word("w1")
    db.add_card(card_id, "w1")
    assert answer(client, card_id).json()["production_card_added"] is False
    assert len(db.cards) == 1


def test_reviewing_a_production_card_does_not_add_another_or_downgrade_known(db, client):
    recognition, production = str(uuid.uuid4()), str(uuid.uuid4())
    db.add_reviewed(recognition, "w1", days_ago=-1, stability=30.0)
    db.words["w1"]["status"] = "known"
    db.add_card(production, "w1", card_type="production", state=1)
    body = answer(client, production, "again").json()
    assert body["production_card_added"] is False
    assert body["status"] == "known"
    assert db.logs[0]["rating"] == 1


def test_another_learners_card_is_not_found(db, client):
    card_id = str(uuid.uuid4())
    db.add_word("theirs", user=OTHER)
    db.add_card(card_id, "theirs", user=OTHER)
    assert answer(client, card_id).status_code == 404
    assert db.cards[card_id]["reps"] == 0
    assert db.logs == []


def test_an_unknown_or_malformed_card_id_is_rejected(db, client):
    assert answer(client, str(uuid.uuid4())).status_code == 404
    assert answer(client, "not-a-uuid").status_code == 422


def test_a_second_submit_for_the_same_serving_is_refused(db, client):
    card_id = str(uuid.uuid4())
    db.add_word("w1")
    db.add_card(card_id, "w1")
    assert answer(client, card_id, reps=0).status_code == 200
    again = answer(client, card_id, reps=0)
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "stale_review"
    assert db.cards[card_id]["reps"] == 1
    assert len(db.logs) == 1


def test_a_race_lost_inside_the_transaction_is_refused(db, client, monkeypatch):
    card_id = str(uuid.uuid4())
    db.add_word("w1")
    db.add_card(card_id, "w1")
    monkeypatch.setattr(review_service, "apply_card_review", lambda *_: None)
    assert answer(client, card_id).json()["detail"]["code"] == "stale_review"
    assert db.logs == []


def test_a_suspended_card_cannot_be_reviewed(db, client):
    card_id = str(uuid.uuid4())
    db.add_word("w1", status="known")
    db.add_card(card_id, "w1", suspended_at=iso())
    response = answer(client, card_id)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "card_suspended"
    assert db.logs == []


def test_a_review_needs_the_owner_header(db, client):
    card_id = str(uuid.uuid4())
    assert client.post(f"/review/{card_id}", json={"rating": "got_it"}).status_code == 401


# --- Card sync ---------------------------------------------------------------------


def test_studying_a_word_creates_its_recognition_card(db):
    word = db.add_word("w1", status="learning")
    review_service.sync_word_cards(USER, word)
    review_service.sync_word_cards(USER, word)
    assert [(c["word_id"], c["card_type"]) for c in db.cards.values()] == [("w1", "recognition")]


def test_marking_a_word_known_ignored_or_new_suspends_its_cards_and_keeps_history(db):
    word = db.add_word("w1")
    db.add_reviewed("c1", "w1", days_ago=1)
    for status in ("known", "ignored", "new"):
        db.cards["c1"]["suspended_at"] = None
        review_service.sync_word_cards(USER, {**word, "status": status})
        assert db.cards["c1"]["suspended_at"] is not None
        assert db.cards["c1"]["reps"] == 3


def test_returning_a_word_to_study_resumes_its_card_with_its_history(db):
    word = db.add_word("w1")
    db.add_reviewed("c1", "w1", days_ago=1, suspended_at=iso())
    review_service.sync_word_cards(USER, {**word, "status": "learning"})
    assert db.cards["c1"]["suspended_at"] is None
    assert db.cards["c1"]["reps"] == 3
    assert len(db.cards) == 1


def test_mastered_words_are_left_alone(db):
    word = db.add_word("w1", status="mastered")
    db.add_reviewed("c1", "w1", days_ago=1)
    review_service.sync_word_cards(USER, word)
    assert db.cards["c1"]["suspended_at"] is None


def test_a_sync_only_touches_the_callers_words(db):
    review_service.sync_word_cards(USER, db.add_word("w1", status="learning"))
    db.add_word("w2", user=OTHER, status="learning")
    assert review_service.sync_learning_cards(USER) == 0
    assert all(c["user_id"] == USER for c in db.cards.values())


def test_a_session_suspends_cards_of_words_marked_known_or_ignored(db, client):
    for word_id, status in (("w1", "known"), ("w2", "ignored")):
        db.add_word(word_id, status=status)
        db.add_card(f"c-{word_id}", word_id)
    assert session(client).json()["cards"] == []
    assert all(c["suspended_at"] for c in db.cards.values())


def test_a_failed_card_sync_does_not_fail_the_status_change(db, client, monkeypatch):
    db.add_word("w1", status="learning", created_at=iso(), updated_at=iso())
    db.add_card("c1", "w1")

    def broken(*_args, **_kwargs):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(review_service, "sync_word_cards", broken)
    monkeypatch.setattr(server, "update_vocabulary_item", db.update_vocabulary_item)
    response = client.patch("/vocabulary/w1", json={"status": "ignored"}, headers=HEADERS)
    assert response.status_code == 200
    assert db.words["w1"]["status"] == "ignored"


# --- Dashboard summary and notebook state ------------------------------------------


def test_summary_counts_what_is_waiting_per_language(db, client):
    db.add_reviewed("r1", "w1", days_ago=2)
    db.add_reviewed("r2", "w2", days_ago=30)
    db.add_reviewed("fr1", "w3", days_ago=1, language="fr")
    db.add_word("wn")
    db.add_card("n1", "wn")
    body = client.get("/review/summary", headers=HEADERS).json()
    by_language = {row["language"]: row for row in body["languages"]}
    assert by_language["es"]["due"] == 2
    assert by_language["es"]["new_available"] == 1
    assert by_language["es"]["total"] == 3
    assert by_language["es"]["at_risk"] == 1
    assert by_language["fr"]["total"] == 1
    assert body["total"] == 4
    assert body["at_risk"] == 1


def test_summary_total_does_not_count_new_words_over_the_daily_limit(db, client):
    for index in range(8):
        db.add_word(f"w{index}")
        db.add_card(f"c{index}", f"w{index}")
    db.profiles[(USER, "es")] = {"daily_new_words": 3}
    assert client.get("/review/summary", headers=HEADERS).json()["total"] == 3


def test_summary_ignores_other_learners(db, client):
    db.add_word("theirs", user=OTHER)
    db.add_card("c1", "theirs", user=OTHER)
    assert client.get("/review/summary", headers=HEADERS).json() == {"languages": [], "total": 0, "at_risk": 0}


def test_notebook_items_carry_their_review_progress_and_the_at_risk_flag(db):
    db.add_reviewed("c1", "late", days_ago=30)
    db.add_reviewed("c2", "fine", days_ago=-3)
    items = [{"id": "late", "language": "es"}, {"id": "fine", "language": "es"}, {"id": "none", "language": "es"}]
    late, fine, none = review_service.attach_review_state(USER, items, NOW)
    assert late["review"]["at_risk"] is True
    assert fine["review"]["at_risk"] is False
    assert fine["review"]["reps"] == 3
    assert none["review"] is None


# --- Review settings ---------------------------------------------------------------


def put_settings(monkeypatch, body):
    saves = []
    monkeypatch.setattr(
        "database.create_supabase_client",
        lambda: SimpleNamespace(
            table=lambda _n: SimpleNamespace(
                select=lambda *_: SimpleNamespace(
                    eq=lambda *_: SimpleNamespace(
                        limit=lambda *_: SimpleNamespace(
                            execute=lambda: SimpleNamespace(data=[{"default_target_lang": "es", "immersion_level": 2}])
                        )
                    )
                )
            )
        ),
    )
    monkeypatch.setattr(
        server, "list_language_profiles",
        lambda _u: [{"l2": "es", "immersion_level": 2, "proficiency": "B1", "active": True}],
    )
    monkeypatch.setattr(server, "save_user_settings", lambda user_id, s, p: saves.append((s, p)))

    async def fake_get(request):
        now = datetime.now(timezone.utc)
        return UserSettings(id=uuid.uuid4(), user_id=uuid.uuid4(), created_at=now, updated_at=now)

    monkeypatch.setattr(server, "get_user_settings", fake_get)
    response = TestClient(server.app).put("/user/settings", json=body, headers=HEADERS)
    return response, saves


def profile(**changes):
    return {"l2": "es", "immersion_level": 2, "proficiency": "B1", "active": True, **changes}


def test_per_language_review_settings_are_saved_with_the_profile(monkeypatch):
    response, saves = put_settings(
        monkeypatch, {"language_profiles": [profile(daily_new_words=15, desired_retention=0.85)]}
    )
    assert response.status_code == 200
    assert saves[0][1][0]["daily_new_words"] == 15
    assert saves[0][1][0]["desired_retention"] == 0.85


def test_a_profile_save_without_review_settings_leaves_them_alone(monkeypatch):
    _, saves = put_settings(monkeypatch, {"language_profiles": [profile()]})
    assert "daily_new_words" not in saves[0][1][0]
    assert "desired_retention" not in saves[0][1][0]


@pytest.mark.parametrize("changes", [
    {"desired_retention": 0.99}, {"desired_retention": 0.97}, {"desired_retention": 0.79},
    {"daily_new_words": 0}, {"daily_new_words": 101},
])
def test_review_settings_outside_their_range_are_refused(monkeypatch, changes):
    response, saves = put_settings(monkeypatch, {"language_profiles": [profile(**changes)]})
    assert response.status_code == 422
    assert saves == []


def test_the_range_edges_are_allowed(monkeypatch):
    for changes in ({"desired_retention": 0.80}, {"desired_retention": 0.95}, {"daily_new_words": 1},
                    {"daily_new_words": 100}):
        response, _ = put_settings(monkeypatch, {"language_profiles": [profile(**changes)]})
        assert response.status_code == 200


def test_settings_report_the_stored_review_settings(monkeypatch):
    monkeypatch.setattr(
        server, "list_language_profiles",
        lambda _u: [profile(daily_new_words=7, desired_retention=0.92), profile(l2="fr")],
    )
    profiles = server._language_profiles_for_user(USER)
    assert (profiles[0].daily_new_words, profiles[0].desired_retention) == (7, 0.92)
    assert (profiles[1].daily_new_words, profiles[1].desired_retention) == (None, None)


# --- Query shape -------------------------------------------------------------------


class QueryRecorder:
    """Records every builder call so a test can read the request a query would make."""

    def __init__(self):
        self.queries, self._current = [], []

    def table(self, name):
        self._current = [("table", (name,))]
        return self

    def __getattr__(self, name):
        def call(*args):
            self._current.append((name, args))
            return self
        return call

    def execute(self):
        self.queries.append(self._current)
        return SimpleNamespace(data=[])


def test_a_session_only_loads_cards_that_are_due_or_never_reviewed(monkeypatch):
    recorder = QueryRecorder()
    monkeypatch.setattr(review_service, "create_supabase_client", lambda: recorder)
    review_service.load_active_cards(USER, "es", NOW)
    calls = recorder.queries[0]
    assert ("or_", (f"reps.eq.0,due.lte.{NOW.isoformat()}",)) in calls
    assert ("is_", ("suspended_at", "null")) in calls
    assert ("eq", ("word.card_status", "ok")) in calls
    assert ("eq", ("language", "es")) in calls
    assert ("eq", ("user_id", USER)) in calls
    assert ("order", ("due",)) in calls


def test_notebook_review_state_is_loaded_a_hundred_words_at_a_time(monkeypatch):
    recorder = QueryRecorder()
    monkeypatch.setattr(review_service, "create_supabase_client", lambda: recorder)
    ids = [str(uuid.uuid4()) for _ in range(250)]
    review_service.load_recognition_cards(USER, ids)
    sizes = [len(dict(query)["in_"][1]) for query in recorder.queries]
    assert sizes == [100, 100, 50]
    assert all(("eq", ("user_id", USER)) in query for query in recorder.queries)


def test_no_request_is_made_for_an_empty_notebook(monkeypatch):
    recorder = QueryRecorder()
    monkeypatch.setattr(review_service, "create_supabase_client", lambda: recorder)
    assert review_service.load_recognition_cards(USER, []) == []
    assert recorder.queries == []
