import asyncio
import hashlib
import json
from pathlib import Path

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.content import curated_words
from app.models import AppState, DictionaryEntry
from app.services.dictionary_parser import calculate_learning_rank, parse_definition

logger = structlog.get_logger()


async def import_dictionary(
    session: AsyncSession,
    source: Path,
    *,
    force: bool = False,
    batch_size: int = 1000,
) -> int:
    source_text = await asyncio.to_thread(source.read_text, encoding="utf-8")
    raw_entries = json.loads(source_text)
    source_hash = hashlib.sha256(source_text.encode()).hexdigest()
    existing = await session.scalar(select(func.count()).select_from(DictionaryEntry)) or 0
    import_state = await session.get(AppState, "dictionary_sha256")
    if (
        not force
        and existing == len(raw_entries)
        and import_state is not None
        and import_state.value == source_hash
    ):
        logger.info("dictionary_import_skipped", existing=existing, reason="checksum_match")
        return existing

    curated = curated_words()
    imported = 0

    for start in range(0, len(raw_entries), batch_size):
        rows = []
        for item in raw_entries[start : start + batch_size]:
            definition = item.get("definition", "").strip()
            meta = parse_definition(definition)
            word = item["word"].strip()
            rows.append(
                {
                    "id": int(item["number"]),
                    "word": word,
                    "definition": definition,
                    "detail_url": item.get("detail_url", ""),
                    "part_of_speech": meta.part_of_speech,
                    "labels": meta.labels,
                    "gloss": meta.gloss,
                    "examples": meta.examples,
                    "learning_rank": calculate_learning_rank(word, definition, curated.get(word)),
                }
            )
        statement = insert(DictionaryEntry).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=[DictionaryEntry.id],
            set_={
                "word": statement.excluded.word,
                "definition": statement.excluded.definition,
                "detail_url": statement.excluded.detail_url,
                "part_of_speech": statement.excluded.part_of_speech,
                "labels": statement.excluded.labels,
                "gloss": statement.excluded.gloss,
                "examples": statement.excluded.examples,
                "learning_rank": statement.excluded.learning_rank,
            },
        )
        await session.execute(statement)
        await session.commit()
        imported += len(rows)
        logger.info("dictionary_import_progress", imported=imported, total=len(raw_entries))

    if import_state is None:
        session.add(AppState(key="dictionary_sha256", value=source_hash))
    else:
        import_state.value = source_hash
    await session.commit()
    return imported
