#!/usr/bin/env python3
"""Build a ROCKNIX-friendly PFE release zip."""

from __future__ import annotations

import argparse
import fnmatch
import os
import zipfile
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PREFIX = "pfe"
PORTS_PREFIX = "ports"

INCLUDE_ROOT_FILES = (
    ".gitignore",
    "INSTALL.md",
    "INSTALL_JP.md",
    "LICENSE",
    "README.md",
    "README_JP.md",
    "launcher.sh",
    "main.py",
    "requirements.txt",
)

INCLUDE_DIRS = (
    "assets",
    "bin",
    "data",
    "docs",
    "pfe_app",
    "scripts",
    "tools",
    "ui",
)

EXCLUDE_DIR_NAMES = {
    ".claude",
    ".git",
    ".idea",
    ".pyxel_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "downloads",
    "eggs",
    "env",
    "venv",
    "wheels",
}

EXCLUDE_RELATIVE_DIRS = {
    "data/image_cache",
}

EXCLUDE_FILE_NAMES = {
    ".DS_Store",
}

EXCLUDE_PATTERNS = (
    "*.bak",
    "*.backup",
    "*.log",
    "*.pyc",
    "*.pyo",
    "*.swp",
    "*.swo",
    "*~",
    "data/cache.json",
    "data/core_history.json",
    "data/favorites.json",
    "data/history.json",
    "data/pfe.cfg_*",
    "data/pfe_generated.pyxpal",
    "data/session.json",
    "data/settings.json",
    "assets/screenshots/*.jpeg",
    "assets/screenshots/*.jpg",
    "assets/screenshots/*.png",
    "bin/tooles.sh",
)


def load_version() -> str:
    namespace: dict[str, str] = {}
    version_file = ROOT / "pfe_app" / "version.py"
    exec(version_file.read_text(encoding="utf-8"), namespace)
    return namespace.get("VERSION", "dev")


def should_exclude(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    parts = relative.split("/")

    if any(part in EXCLUDE_DIR_NAMES for part in parts[:-1]):
        return True
    if path.is_dir() and path.name in EXCLUDE_DIR_NAMES:
        return True
    if path.is_file() and path.name in EXCLUDE_FILE_NAMES:
        return True
    if any(relative == dirname or relative.startswith(f"{dirname}/") for dirname in EXCLUDE_RELATIVE_DIRS):
        return True
    if path.is_file() and relative.startswith("assets/bgm/") and path.suffix.lower() == ".mp3":
        return not path.name.startswith("PFE_BGM_")
    if path.is_file() and any(fnmatch.fnmatch(relative, pattern) for pattern in EXCLUDE_PATTERNS):
        return True
    return False


def iter_files() -> list[Path]:
    files: list[Path] = []

    for relative in INCLUDE_ROOT_FILES:
        path = ROOT / relative
        if path.exists() and not should_exclude(path):
            files.append(path)

    for directory in INCLUDE_DIRS:
        root = ROOT / directory
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and not should_exclude(path):
                files.append(path)

    return sorted(set(files), key=lambda item: item.relative_to(ROOT).as_posix())


def zip_info_for(path: Path, arcname: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(arcname)
    stat = path.stat()
    info.date_time = date.today().timetuple()[:6]
    mode = stat.st_mode & 0o777
    if path.suffix == ".sh" or path.name in {"launcher.sh"}:
        mode |= 0o755
    info.external_attr = mode << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def add_file(zf: zipfile.ZipFile, source: Path, arcname: str) -> None:
    info = zip_info_for(source, arcname)
    zf.writestr(info, source.read_bytes())


def build(output: Path) -> int:
    files = iter_files()
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w") as zf:
        for source in files:
            relative = source.relative_to(ROOT).as_posix()
            add_file(zf, source, f"{APP_PREFIX}/{relative}")

            ports_prefix = "tools/rocknix/ports/"
            if relative.startswith(ports_prefix):
                ports_relative = relative[len(ports_prefix):]
                add_file(zf, source, f"{PORTS_PREFIX}/{ports_relative}")

    print(f"created: {output}")
    print(f"files: {len(files)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output zip path. Defaults to dist/pfe-rocknix-v<VERSION>-YYYYMMDD.zip.",
    )
    args = parser.parse_args()

    version = load_version()
    default_name = f"pfe-rocknix-v{version}-{date.today():%Y%m%d}.zip"
    output = args.output or (ROOT / "dist" / default_name)
    if not output.is_absolute():
        output = ROOT / output

    return build(output)


if __name__ == "__main__":
    raise SystemExit(main())
