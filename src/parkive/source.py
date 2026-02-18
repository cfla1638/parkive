from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from rich.console import Console
from typing import Annotated
from . import config
from .common import iter_files_to_process

import os
import re
import typer
import tomllib
import tomli_w
import logging

console = Console()

log = logging.getLogger(__name__)

source_app = typer.Typer()

MD_IMAGE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)(?P<tail>\s+\"[^\"]*\")?\)"
)
HTML_IMAGE_RE = re.compile(
    r"(?P<prefix><img\b[^>]*\bsrc\s*=\s*[\"'])(?P<url>[^\"']+)(?P<suffix>[\"'])",
    flags=re.IGNORECASE,
)


def load_sources(parkive_root: Path) -> dict:
    config_path = parkive_root / ".parkive" / "sources.toml"
    if not config_path.is_file():
        return {}
    try:
        with config_path.open("rb") as f:
            loaded = tomllib.load(f)
            sources = loaded.get("sources", {})
            if not isinstance(sources, dict):
                console.print(
                    f"Invalid format in {config_path}: 'sources' should be a table.",
                    style="red bold",
                )
                return {}
            return {k: v for k, v in sources.items() if isinstance(v, str)}
    except Exception as e:
        console.print(
            f"Failed to load sources from {config_path}: {e}",
            style="red bold",
        )
        raise typer.Exit(code=1)

@source_app.callback()
def bootstrap(ctx: typer.Context):
    ctx.obj["sources"] = load_sources(Path(ctx.obj["parkive_root"]))
    log.debug(f"Sources loaded: {ctx.obj['sources']}")
    

def validate_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    parsed = urlparse(normalized)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("base_url must be like http://host:port")
    if parsed.path or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("base_url can only include scheme://host[:port]")
    return normalized


def save_sources(parkive_root: Path, sources: dict) -> None:
    """
    将 sources 字典保存到 parkive_root/.parkive/sources.toml 文件中。
    """
    path = parkive_root / ".parkive" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        tomli_w.dump({"sources": sources}, f)


def prefix_match(url: str, prefix: str) -> bool:
    """检查 url 是否以 prefix 开头，并且后面要么结束，要么是 / ? # 之一。"""
    if not url.startswith(prefix):
        return False
    if len(url) == len(prefix):
        return True
    return url[len(prefix)] in ["/", "?", "#"]


def convert_url_prefix(url: str, source_prefix: str, target_prefix: str) -> str:
    if not prefix_match(url, source_prefix):
        return url
    return target_prefix + url[len(source_prefix) :]


def replace_images_in_text(content: str, source_prefix: str, target_prefix: str) -> tuple[str, int]:
    replaced_count = 0

    def md_repl(match: re.Match) -> str:
        nonlocal replaced_count
        original_url = match.group("url")
        converted_url = convert_url_prefix(original_url, source_prefix, target_prefix)
        if converted_url == original_url:
            return match.group(0)
        replaced_count += 1
        log.debug(f"Replacing URL in markdown: {original_url} => {converted_url}")
        tail = match.group("tail") or ""
        return f"![{match.group('alt')}]({converted_url}{tail})"

    content = MD_IMAGE_RE.sub(md_repl, content)

    def html_repl(match: re.Match) -> str:
        nonlocal replaced_count
        original_url = match.group("url")
        converted_url = convert_url_prefix(original_url, source_prefix, target_prefix)
        if converted_url == original_url:
            return match.group(0)
        replaced_count += 1
        log.debug(f"Replacing URL in HTML: {original_url} => {converted_url}")
        return f"{match.group('prefix')}{converted_url}{match.group('suffix')}"

    content = HTML_IMAGE_RE.sub(html_repl, content)
    return content, replaced_count


def count_source_urls(content: str, base_url: str) -> int:
    count = 0
    for match in MD_IMAGE_RE.finditer(content):
        if prefix_match(match.group("url"), base_url):
            count += 1
    for match in HTML_IMAGE_RE.finditer(content):
        if prefix_match(match.group("url"), base_url):
            count += 1
    return count


def require_source(sources: dict, name: str) -> str:
    if name not in sources:
        console.print(f"source '{name}' not found.", style=config.error_style)
        raise typer.Exit(code=1)
    return sources[name]


@source_app.command("add")
def source_add(name: Annotated[str, typer.Argument(help="Name of the source to add")],
               base_url: Annotated[str, typer.Argument(help="Base URL of the source, like http://host:port")],
               ctx: typer.Context):
    """
    Add a source with given name and base_url. base_url must be like protocol://host:port.
    """
    sources = ctx.obj["sources"]

    if name in sources:
        console.print(f"source '{name}' already exists.", style=config.error_style)
        raise typer.Exit(code=1)

    try:
        normalized_url = validate_base_url(base_url)
    except ValueError as e:
        console.print(f"Invalid base_url: {e}", style=config.error_style)
        raise typer.Exit(code=1)

    sources[name] = normalized_url
    save_sources(ctx.obj["parkive_root"], sources)
    ctx.obj["sources"] = sources
    console.print(f"added source '{name}' => {normalized_url}", style=config.success_style)

@source_app.command("remove")
def source_remove(name: Annotated[str, typer.Argument(help="Name of the source to remove")], ctx: typer.Context):
    """Remove the source with given name."""
    sources = ctx.obj["sources"]

    if name not in sources:
        console.print(f"source '{name}' not found.", style=config.error_style)
        raise typer.Exit(code=1)

    removed_url = sources.pop(name)
    save_sources(ctx.obj["parkive_root"], sources)
    ctx.obj["sources"] = sources
    console.print(f"removed source '{name}' ({removed_url})", style=config.success_style)


@source_app.command("change")
def source_convert(src: Annotated[str, typer.Argument(help="Source name to change from")],
                   tgt: Annotated[str, typer.Argument(help="Target source name to change to")],
                   ctx: typer.Context,
                   files: Annotated[list[str] | None, typer.Option("--file", "-f", help="Only convert the specified files instead of all managed files. It will override the scan_glob configuration. Can be specified multiple times.")] = None,
                   glob: Annotated[list[str] | None, typer.Option("--glob", "-g", help="Override the scan_glob configuration with the specified glob patterns. Can be specified multiple times.")] = None):
    """Change source prefix from src to tgt in all managed files."""
    parkive_root = Path(ctx.obj["parkive_root"])
    user_config = ctx.obj["user_config"]
    source_prefix = require_source(ctx.obj["sources"], src)
    target_prefix = require_source(ctx.obj["sources"], tgt)

    changed_files = 0
    replaced_urls = 0

    if glob is not None:
        log.debug(f"Overriding scan_glob with: {glob}")

    for file_path in iter_files_to_process(
        parkive_root=parkive_root,
        scan_glob=user_config["scope"]["scan_glob"] if glob is None else glob,
        skip_dirs=user_config["scope"]["skip_dirs"],
        specified_files=files,
    ):
        original = file_path.read_text(encoding="utf-8")
        converted, count = replace_images_in_text(original, source_prefix, target_prefix)
        if count > 0:
            file_path.write_text(converted, encoding="utf-8")
            changed_files += 1
            replaced_urls += count

    console.print(
        f"changed source '{src}' => '{tgt}', replaced {replaced_urls} urls in {changed_files} files.",
        style=config.success_style,
    )


@source_app.command("inspect")
def source_inspect(name: Annotated[str, typer.Argument(help="Name of the source to inspect")], 
                   ctx: typer.Context,
                   files: Annotated[list[str] | None, typer.Option("--file", "-f", help="Only inspect the specified files instead of all managed files. It will override the scan_glob configuration. Can be specified multiple times.")] = None):
    """Inspect how many images are using the source with given name."""
    user_config = ctx.obj["user_config"]
    parkive_root = Path(ctx.obj["parkive_root"])
    base_url = require_source(ctx.obj["sources"], name)

    matched_cnt = 0
    for file_path in iter_files_to_process(
        parkive_root=parkive_root,
        scan_glob=user_config["scope"]["scan_glob"],
        skip_dirs=user_config["scope"]["skip_dirs"],
        specified_files=files
    ):
        content = file_path.read_text(encoding="utf-8")
        matched_cnt_this_file = count_source_urls(content, base_url)
        matched_cnt += matched_cnt_this_file
        log.debug(f"Scanned {file_path}, found {matched_cnt_this_file} urls with base {base_url}")

    console.print(f"name: {name}", style=config.info_style)
    console.print(f"base_url: {base_url}", style=config.info_style)
    console.print(f"images: {matched_cnt}", style=config.info_style)


@source_app.command("list")
def source_list(ctx: typer.Context):
    """List all configured sources."""
    sources = ctx.obj["sources"]

    if not sources:
        console.print("No sources configured.", style=config.warning_style)
        return

    for name in sorted(sources):
        console.print(f"{name}\t{sources[name]}", style=config.info_style)
