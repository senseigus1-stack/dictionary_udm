from app.services.dictionary_parser import calculate_learning_rank, parse_definition


def test_extracts_rich_definition_parts() -> None:
    value = (
        "\u00a0\u00a0\u00a0Ⅰсущ.1) дом; изба"
        "\u00a0\u00a0\u00a0корка ӝутыны построить дом"
        "\u00a0\u00a0\u00a02) семья"
    )
    parsed = parse_definition(value)
    assert parsed.part_of_speech == "существительное"
    assert parsed.gloss == "дом; изба"
    assert parsed.examples == ["корка ӝутыны построить дом", "2) семья"]


def test_extracts_domain_label_without_losing_gloss() -> None:
    parsed = parse_definition("бот.1) таволга; лабазник2) папоротник")
    assert parsed.labels == ["бот."]
    assert parsed.gloss == "таволга; лабазник2) папоротник"


def test_curated_words_are_ranked_before_other_entries() -> None:
    assert calculate_learning_rank("мон", "я", 2) == 2
    assert calculate_learning_rank("редкое-слово", "диал. значение", None) > 1200
