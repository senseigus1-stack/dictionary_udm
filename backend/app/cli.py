import asyncio
from pathlib import Path

import typer
from sqlalchemy import func, select

from app.database import SessionFactory
from app.models import DictionaryEntry, User
from app.services.importer import import_dictionary as run_import

cli = typer.Typer(help="Администрирование платформы Ӟечбур", no_args_is_help=True)


@cli.command("import-dictionary")
def import_dictionary_command(
    source: Path = typer.Argument(..., exists=True, readable=True),
    force: bool = typer.Option(False, help="Перезаписать уже импортированные записи"),
) -> None:
    async def execute() -> int:
        async with SessionFactory() as session:
            return await run_import(session, source, force=force)

    imported = asyncio.run(execute())
    typer.echo(f"Словарь готов: {imported} записей")


@cli.command("stats")
def stats() -> None:
    async def execute() -> tuple[int, int]:
        async with SessionFactory() as session:
            words = await session.scalar(select(func.count()).select_from(DictionaryEntry)) or 0
            users = await session.scalar(select(func.count()).select_from(User)) or 0
            return words, users

    words, users = asyncio.run(execute())
    typer.echo(f"Слов: {words}\nПользователей: {users}")


if __name__ == "__main__":
    cli()
