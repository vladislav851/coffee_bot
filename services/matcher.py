from rapidfuzz import fuzz, process

MATCH_THRESHOLD = 80


def find_best_match(
    query: str,
    choices: dict[str, int],
) -> int | None:
    """
    Ищет наилучшее совпадение query среди ключей choices.
    choices — словарь {нормализованное_имя: product_id}.
    Возвращает product_id или None если ничего не нашлось выше порога.
    """
    if not choices:
        return None

    result = process.extractOne(
        query.lower(),
        choices.keys(),
        scorer=fuzz.WRatio,
        score_cutoff=MATCH_THRESHOLD,
    )
    if result is None:
        return None

    best_name = result[0]
    return choices[best_name]


def find_candidates(
    query: str,
    choices: dict[str, int],
    limit: int = 5,
) -> list[tuple[str, int]]:
    """
    Возвращает до `limit` кандидатов выше порога.
    Используется когда совпадений несколько (например, 'молоко' → 6 видов).
    Возвращает список (нормализованное_имя, product_id).
    """
    results = process.extract(
        query.lower(),
        choices.keys(),
        scorer=fuzz.WRatio,
        score_cutoff=MATCH_THRESHOLD,
        limit=limit,
    )
    return [(name, choices[name]) for name, _score, _idx in results]
