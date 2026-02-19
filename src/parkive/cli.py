from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from typing import Annotated
from .source import source_app
from .git import git_app
from .tool import tool_app
from . import config

import os
import typer
import logging
import tomllib

# 创建 Rich 控制台实例
console = Console()


# 配置日志
level = os.getenv("PARKIVE_LOG_LEVEL", "WARNING").upper()
if level not in ["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    level = "WARNING"

logging.basicConfig(
    level=getattr(logging, level),
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console)],
)
log = logging.getLogger("__name__")


# 主 CLI 应用
app = typer.Typer(no_args_is_help=True, help="Parkive CLI - A tool for managing your personal archive of notes and images.")
app.add_typer(source_app, name="source", help="Image source management")
app.add_typer(git_app, name="git", help="Git operations related to Parkive")
app.add_typer(tool_app, name="tool", help="Utility tools for Parkive")


def find_parkive_root(start: Path | None = None) -> Path | None:
    """
    寻找包含 .parkive 目录的路径，从 start 开始向上查找，直到找到为止。如果没有找到，则返回 None。
    """
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".parkive").is_dir():
            return candidate
    return None


def load_user_config(parkive_root: Path) -> dict:
    """
    加载用户配置文件，如果存在的话。返回一个包含配置的字典。
    """
    user_config: dict = {
        "scope" : {
            "scan_glob": list(config.DEFAULT_SCAN_GLOB),
            "skip_dirs": list(config.DEFAULT_SKIP_DIRS)
        }
    }

    user_config_path = parkive_root / ".parkive" / "config.toml"
    if not user_config_path.is_file():
        console.print(
            f"No user config found at {user_config_path}. Using default configuration.",
            style=config.warning_style,
        )
        return user_config
    
    try:
        with user_config_path.open("rb") as f:
            loaded = tomllib.load(f)
        scan_glob = loaded.get("scope", {}).get("scan_glob", None)
        skip_dirs = loaded.get("scope", {}).get("skip_dirs", None)
        if isinstance(scan_glob, list) and all(isinstance(i, str) for i in scan_glob):
            user_config["scope"]["scan_glob"] = scan_glob
        if isinstance(skip_dirs, list) and all(isinstance(i, str) for i in skip_dirs):
            user_config["scope"]["skip_dirs"] = skip_dirs
        log.debug(f"User config loaded from {user_config_path}: {user_config}")
        return user_config
    except Exception as e:
        console.print(
            f"Failed to load user config from {user_config_path}: {e}",
            style=config.error_style,
        )
        raise typer.Exit(code=1)


@app.callback()
def bootstrap(ctx: typer.Context):
    """
     - 寻找包含 .parkive 目录
     - 加载用户配置文件
    """
    log.debug("This program is running in directory: " + str(Path.cwd()))
    
    if ctx.invoked_subcommand == "init":
        return

    parkive_root = find_parkive_root()
    log.debug(f"Parkive root found at: {parkive_root}")

    if parkive_root is None:
        console.print(
            "Cannot find .parkive directory from current working directory upward.",
            style=config.error_style,
        )
        raise typer.Exit(code=1)
    ctx.obj = {"parkive_root": parkive_root, "user_config": load_user_config(parkive_root)}


@app.command("init")
def init(path : Annotated[str | None, typer.Argument(help="Path to initialize the Parkive project in. If not provided, initializes in the current working directory.")] = None):
    """
    Initialize a new Parkive project in the specified directory (or current directory if not specified). This will create a .parkive directory with default configuration files.
    """
    cwd = Path.cwd()
    target_dir = cwd if path is None else Path(path)
    if not target_dir.is_absolute():
        target_dir = (cwd / target_dir).resolve()

    parkive_dir = target_dir / ".parkive"
    parkive_dir.mkdir(parents=True, exist_ok=True)

    sources_path = parkive_dir / "sources.toml"
    config_path = parkive_dir / "config.toml"

    if not sources_path.exists():
        sources_path.write_text("[sources]\n", encoding="utf-8")

    if not config_path.exists():
        scan_glob_items = ", ".join(f'"{item}"' for item in config.DEFAULT_SCAN_GLOB)
        skip_dirs_items = ", ".join(f'"{item}"' for item in config.DEFAULT_SKIP_DIRS)
        config_text = (
            "[scope]\n"
            f"scan_glob = [{scan_glob_items}]\n"
            f"skip_dirs = [{skip_dirs_items}]\n"
        )
        config_path.write_text(config_text, encoding="utf-8")

    console.print(f"initialized parkive at {target_dir}", style=config.success_style)
