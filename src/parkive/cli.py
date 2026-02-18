from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from .source import source_app
from .git import git_app
import os
import typer
import logging
import tomllib
from . import config

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
app = typer.Typer(help="Parkive CLI - A tool for managing your personal archive of notes and images.")
app.add_typer(source_app, name="source", help="Image source management")
app.add_typer(git_app, name="git", help="Git operations related to Parkive")

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
        return config
    
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
    parkive_root = find_parkive_root()
    log.debug(f"Parkive root found at: {parkive_root}")
    if parkive_root is None:
        console.print(
            "Cannot find .parkive directory from current working directory upward.",
            style=config.error_style,
        )
        raise typer.Exit(code=1)
    ctx.obj = {"parkive_root": parkive_root, "user_config": load_user_config(parkive_root)}
