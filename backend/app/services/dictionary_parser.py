import re
from dataclasses import dataclass

MULTISPACE = re.compile(r"(?:\u00a0|\s){3,}")
NUMBERING = re.compile(
    r"^(?:(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|\d+)\s*[.)]?\s*|[а-я]\)\s*)+",
    re.IGNORECASE,
)

PARTS_OF_SPEECH = {
    "сущ.": "существительное",
    "прил.": "прилагательное",
    "глаг.": "глагол",
    "нареч.": "наречие",
    "мест.": "местоимение",
    "числ.": "числительное",
    "союз": "союз",
    "частица": "частица",
    "межд.": "междометие",
    "послелог": "послелог",
    "предик.": "предикатив",
}

LABELS = {
    "авиа.",
    "анат.",
    "архит.",
    "биол.",
    "бот.",
    "воен.",
    "геогр.",
    "грам.",
    "детск.",
    "диал.",
    "зоол.",
    "ирон.",
    "ист.",
    "книжн.",
    "лингв.",
    "мат.",
    "мед.",
    "миф.",
    "муз.",
    "неодобр.",
    "перен.",
    "поэт.",
    "прост.",
    "разг.",
    "рел.",
    "собир.",
    "спорт.",
    "тех.",
    "устар.",
    "фольк.",
    "шутл.",
}


@dataclass(frozen=True)
class DefinitionMeta:
    gloss: str
    part_of_speech: str | None
    labels: list[str]
    examples: list[str]


def _clean_gloss(value: str) -> str:
    value = NUMBERING.sub("", value.strip())
    for marker in PARTS_OF_SPEECH:
        if value.startswith(marker):
            value = value[len(marker) :].strip()
    for label in LABELS:
        if value.startswith(label):
            value = value[len(label) :].strip()
    value = NUMBERING.sub("", value)
    return value.strip(" ;,—–")


def parse_definition(definition: str) -> DefinitionMeta:
    normalized = definition.replace("\r", " ").strip()
    segments = [segment.strip() for segment in MULTISPACE.split(normalized) if segment.strip()]
    first = segments[0] if segments else normalized

    part_of_speech = next(
        (name for marker, name in PARTS_OF_SPEECH.items() if marker in first[:60]), None
    )
    labels = sorted(label for label in LABELS if label in normalized[:100])
    gloss = _clean_gloss(first)
    if not gloss:
        gloss = normalized[:240].strip()
    if len(gloss) > 320:
        gloss = gloss[:317].rstrip() + "…"

    examples = [re.sub(r"\s+", " ", segment) for segment in segments[1:7]]
    return DefinitionMeta(
        gloss=gloss,
        part_of_speech=part_of_speech,
        labels=labels,
        examples=examples,
    )


def calculate_learning_rank(word: str, definition: str, curated_position: int | None) -> float:
    if curated_position is not None:
        return float(curated_position)
    penalty = min(len(word), 40) * 2
    penalty += 80 if " " in word or "-" in word else 0
    penalty += 120 if "смотри:" in definition else 0
    penalty += 150 if any(label in definition[:40] for label in ("диал.", "устар.")) else 0
    return 1000.0 + penalty
