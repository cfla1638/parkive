from pathlib import Path, PurePosixPath
import os


def iter_files_to_process(parkive_root: Path, scan_glob: list[str], skip_dirs: list[str], specified_files: list[str] | None = None):
    """根据参数将调用分流到不同的生成器函数"""
    if specified_files is not None:
        yield from iter_specified_files(specified_files)
    else:
        yield from iter_managed_files(parkive_root, scan_glob, skip_dirs)


def iter_managed_files(parkive_root: Path, scan_glob: list[str], skip_dirs: list[str]):
    skip_set = set(skip_dirs)
    normalized_globs = [pattern.strip().strip("'\"`") for pattern in scan_glob]     #去除空白和引号，避免用户配置中的格式问题导致匹配失败
    """
    迭代 parkive_root 下所有匹配 scan_glob 模式的文件，跳过 skip_dirs 中的目录。返回一个生成器，生成 Path 对象。
    """
    for root, dirs, files in os.walk(parkive_root):
        dirs[:] = [d for d in dirs if d not in skip_set]
        root_path = Path(root)
        for filename in files:
            file_path = root_path / filename
            rel = file_path.relative_to(parkive_root).as_posix()
            rel_path = PurePosixPath(rel)
            if any(rel_path.match(pattern) for pattern in normalized_globs):
                yield file_path


def iter_specified_files(specified_files: list[str]):
    """
    迭代指定的文件路径，根据工作目录和输入路径解析出绝对路径，过滤掉不存在的文件，并返回 Path 对象。
    """
    cwd = Path.cwd()
    for rel_path in specified_files:
        file_path = (cwd / rel_path).resolve()
        if file_path.is_file():
            yield file_path
