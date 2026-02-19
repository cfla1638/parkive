from pathlib import Path
from typing import Annotated
from rich.console import Console
from . import config
from .common import iter_files_to_process

import typer
import logging
import re

console = Console()
log = logging.getLogger(__name__)
tool_app = typer.Typer(no_args_is_help=True)


EN_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['_-][A-Za-z0-9]+)*")
CJK_CHAR_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def count_mixed_words(content: str) -> int:
    """Count words for mixed Chinese/English text.
    - English/alnum chunks count as 1 word each.
    - Each CJK ideograph counts as 1 word.
    """
    en_count = len(EN_WORD_RE.findall(content))
    cjk_count = len(CJK_CHAR_RE.findall(content))
    return en_count + cjk_count


@tool_app.command("wc")
def word_count(
    ctx: typer.Context,
    files: Annotated[list[str] | None, typer.Option("--file", "-f", help="Only count the specified files instead of all managed files. It will override the scan_glob configuration. Can be specified multiple times.")] = None,
    glob: Annotated[list[str] | None, typer.Option("--glob", "-g", help="Override the scan_glob configuration with the specified glob patterns. Can be specified multiple times.")] = None,
):
    """Count words in managed files."""
    parkive_root = Path(ctx.obj["parkive_root"])
    user_config = ctx.obj["user_config"]
    scan_glob = user_config["scope"]["scan_glob"] if glob is None else glob

    total_words = 0
    counted_files = 0

    for file_path in iter_files_to_process(
        parkive_root=parkive_root,
        scan_glob=scan_glob,
        skip_dirs=user_config["scope"]["skip_dirs"],
        specified_files=files,
    ):
        content = file_path.read_text(encoding="utf-8")
        word_count_in_file = count_mixed_words(content)
        total_words += word_count_in_file
        counted_files += 1

        try:
            display_path = file_path.relative_to(parkive_root).as_posix()
        except ValueError:
            display_path = str(file_path)
        console.print(f"{display_path}\t{word_count_in_file}", style=config.info_style)

    console.print(f"total files: {counted_files}", style=config.info_style)
    console.print(f"total words: {total_words}", style=config.success_style)
