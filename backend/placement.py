"""Vocabulary-size placement check: fixed word samples per frequency band.

Sample words are drawn from wordfreq (CC BY-SA 4.0) lemma rankings, frozen at the
installed package's data (about 2021), eight words per rank range. The check estimates
vocabulary size as an estimate, never a score.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

MAX_RANK = 32000
BANDS: tuple[tuple[int, int], ...] = (
    (1, 2000),
    (2001, 4000),
    (4001, 8000),
    (8001, 16000),
    (16001, 32000),
)
WORDS_PER_BAND = 8

# l2 -> one word list per band in BANDS order.
SAMPLES: dict[str, tuple[tuple[str, ...], ...]] = {
    "en": (
        ("security", "trip", "light", "camp", "fat", "army", "plant", "society"),
        ("pure", "leads", "recognition", "fitness", "hat", "email", "obtained", "calm"),
        ("slap", "workplace", "theories", "namely", "animation", "competitors", "cathedral", "specifications"),
        ("lest", "shortest", "questionable", "clergy", "piracy", "preserving", "affection", "costing"),
        ("depiction", "strangest", "follicles", "discord", "exceedingly", "gadget", "keywords", "endeavour"),
    ),
    "es": (
        ("bajo", "leer", "venga", "queremos", "ciudad", "moda", "encuentran", "maestro"),
        ("decirle", "tradicionales", "acaban", "década", "investigaciones", "embajada", "definitivamente", "estuvieron"),
        ("preocupes", "tribu", "comisario", "seguiremos", "preocupado", "ganancia", "criticar", "llevarse"),
        ("harías", "recordé", "seudónimo", "crecieron", "entornos", "elevación", "aprecia", "codo"),
        ("amorosas", "consisten", "aprendices", "cerramos", "respondes", "epidemias", "mercadeo", "trecho"),
    ),
    "fr": (
        ("estime", "attendre", "remettre", "contre", "avantage", "mariage", "cette", "télévision"),
        ("larmes", "connus", "investissements", "touché", "bibliothèque", "considéré", "séjour", "inutile"),
        ("scrutin", "élaboration", "immeubles", "urss", "néo", "travailleur", "artillerie", "athlètes"),
        ("blindé", "laissons", "démonstrations", "formelle", "découverts", "agriculteur", "désespoir", "requises"),
        ("lingots", "comprendrai", "inachevé", "medias", "existentielle", "cogne", "constatation", "skieurs"),
    ),
    "de": (
        ("sinn", "hatten", "geschlossen", "ebene", "bildet", "interessant", "statt", "guter"),
        ("schäden", "kommunikation", "nutzer", "erlauben", "ganzes", "schwimmen", "gewicht", "teilt"),
        ("erwähnung", "mengen", "tagebuch", "meins", "heizung", "suchte", "aktueller", "leiche"),
        ("breites", "rührt", "friseur", "anbetracht", "schweizerischen", "kreativen", "schwersten", "schema"),
        ("ladungen", "redakteurin", "mitzubringen", "klientel", "verächtlich", "preisgeben", "wett", "klägerin"),
    ),
    "it": (
        ("carta", "loro", "momento", "metri", "vittima", "sindaco", "mercato", "vedere"),
        ("denuncia", "attivo", "pianta", "stavano", "inserito", "ospiti", "omaggio", "tracce"),
        ("ostacolo", "svolgimento", "acceso", "penali", "mondi", "vaccino", "prostituzione", "servito"),
        ("manoscritto", "correzione", "economicamente", "perdonare", "esistevano", "guidando", "zitta", "surreale"),
        ("abbracciando", "timidezza", "focalizzare", "angolare", "longitudinale", "insensata", "rinchiusa", "ricavarne"),
    ),
    "pt": (
        ("erros", "ministério", "teria", "corte", "deputados", "resto", "marca", "escrita"),
        ("registros", "ferramenta", "acaso", "tirou", "perde", "pego", "científica", "parlamentar"),
        ("diminuição", "detalhe", "resenha", "gêneros", "reflete", "consumidores", "promessas", "cúpula"),
        ("evangélicos", "estarmos", "domiciliar", "alturas", "violentos", "isenção", "firmemente", "prático"),
        ("referencia", "extintas", "rastreando", "reforçou", "simplificar", "descartou", "acumulação", "lisos"),
    ),
    "nl": (
        ("grootste", "gedacht", "bos", "vinden", "verslag", "gisteren", "rijden", "wees"),
        ("ernaar", "sloot", "streven", "hel", "lezers", "speel", "populaire", "plaatsvinden"),
        ("behaalde", "distributie", "dekking", "vrouwe", "hek", "juridisch", "latere", "financieren"),
        ("vooravond", "schoonzoon", "karton", "verontschuldigingen", "altaar", "afstaan", "ambassadeurs", "sprekend"),
        ("deeltijd", "afwerken", "ouderavond", "magistraat", "voetbalvereniging", "oververhitting", "thuishoren", "theologie"),
    ),
    "ru": (
        ("церковь", "работников", "западной", "многие", "сеть", "только", "боже", "помощи"),
        ("членами", "известного", "начинают", "апреле", "рубль", "сад", "молодец", "зря"),
        ("колонны", "любим", "участником", "изданий", "интереса", "олимпийский", "стекло", "посмотри"),
        ("восторг", "ребёнком", "нападающего", "школьной", "продуктами", "лучи", "тихий", "намерения"),
        ("ловушка", "покрыт", "аналогичную", "файлов", "тактике", "трудовое", "добавлять", "морального"),
    ),
}


def has_samples(language: str) -> bool:
    """Whether the placement check exists for this language."""
    return _key(language) in SAMPLES


def sample_words(language: str) -> list[str]:
    """The words shown in the check, one flat list in band order."""
    bands = SAMPLES.get(_key(language))
    return [word for band in bands for word in band] if bands else []


def band_samples(language: str) -> Sequence[Sequence[str]]:
    """The sample words grouped by frequency band."""
    return SAMPLES.get(_key(language)) or ()


def estimate_size(language: str, known: Iterable[str]) -> Optional[int]:
    """Estimated vocabulary size from the tapped words. An estimate, never a score.

    Each band's known share scales that band's rank range; the sum is the estimate.
    Returns None when the language has no sample.
    """
    bands = SAMPLES.get(_key(language))
    if not bands:
        return None
    wanted = {_norm(word) for word in known}
    estimate = 0.0
    for (rank_lo, rank_hi), words in zip(BANDS, bands):
        share = len([w for w in words if _norm(w) in wanted]) / len(words)
        estimate += share * (rank_hi - rank_lo + 1)
    return int(round(estimate))


def matching_words(language: str, known: Iterable[str]) -> list[str]:
    """The sample words among ``known``, in sample order."""
    bands = SAMPLES.get(_key(language))
    if not bands:
        return []
    wanted = {_norm(word) for word in known}
    return [w for band in bands for w in band if _norm(w) in wanted]


def _key(language: str) -> str:
    return (language or "").split("-")[0].lower()


def _norm(word: str) -> str:
    return (word or "").strip().lower()
