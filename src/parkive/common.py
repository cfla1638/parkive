from pathlib import Path, PurePosixPath
import os

def iter_managed_files(parkive_root: Path, scan_glob: list[str], skip_dirs: list[str]):
    skip_set = set(skip_dirs)
    for root, dirs, files in os.walk(parkive_root):
        dirs[:] = [d for d in dirs if d not in skip_set]
        root_path = Path(root)
        for filename in files:
            file_path = root_path / filename
            rel = file_path.relative_to(parkive_root).as_posix()
            rel_path = PurePosixPath(rel)
            if any(rel_path.match(pattern) for pattern in scan_glob):
                yield file_path