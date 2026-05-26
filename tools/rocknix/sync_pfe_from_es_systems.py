#!/usr/bin/env python3
"""Sync existing PFE systems with a ROCKNIX EmulationStation es_systems.cfg."""

from __future__ import annotations

import argparse
import dataclasses
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


@dataclasses.dataclass
class EsSystem:
    name: str
    fullname: str
    rom_dir: str
    extensions: list[str]
    cores: list[str]
    custom_emulators: list[str]


ALIASES = {
    "fbneo": ["fbn"],
    "pc88": ["pc-8800"],
    "pc98": ["pc-9800"],
    "scummvm": ["scummvm"],
}


def _clean_ext(value: str) -> str:
    return value.strip().lstrip(".")


def _launcher_key(emulator: str) -> str:
    return f"TYPE_{emulator.upper()}"


def parse_es_systems(path: Path) -> tuple[list[EsSystem], dict[str, EsSystem], dict[str, EsSystem]]:
    root = ET.parse(path).getroot()
    systems: list[EsSystem] = []
    by_name: dict[str, EsSystem] = {}
    by_dir: dict[str, EsSystem] = {}

    for node in root.findall("system"):
        name = (node.findtext("name") or "").strip()
        fullname = (node.findtext("fullname") or "").strip()
        rom_path = (node.findtext("path") or "").strip()
        rom_dir = os.path.basename(os.path.normpath(rom_path))
        extensions = [_clean_ext(ext) for ext in (node.findtext("extension") or "").split()]
        extensions = [ext for ext in extensions if ext]

        cores: list[str] = []
        custom_emulators: list[str] = []
        for emulator_node in node.findall("./emulators/emulator"):
            emulator = (emulator_node.get("name") or "").strip()
            if not emulator:
                continue
            for core_node in emulator_node.findall("./cores/core"):
                core = (core_node.text or "").strip()
                if not core:
                    continue
                if emulator == "retroarch":
                    cores.append(core)
                else:
                    cores.append(f"{emulator}:{core}")
                    if emulator not in custom_emulators:
                        custom_emulators.append(emulator)

        system = EsSystem(name, fullname, rom_dir, extensions, cores, custom_emulators)
        systems.append(system)
        by_name[name] = system
        if rom_dir and rom_dir not in by_dir:
            by_dir[rom_dir] = system

    return systems, by_name, by_dir


def parse_pfe_dir(block: list[str]) -> str:
    for line in block:
        stripped = line.strip()
        if stripped.startswith("-DIR="):
            value = stripped.split("=", 1)[1].strip()
            return os.path.basename(os.path.normpath(value))
    return ""


def parse_pfe_system(block: list[str]) -> str:
    for line in block:
        stripped = line.strip()
        if stripped.startswith("-SYSTEM=") or stripped.startswith("-ES_SYSTEM="):
            return stripped.split("=", 1)[1].strip()
    return ""


def match_system(block: list[str], by_name: dict[str, EsSystem], by_dir: dict[str, EsSystem]) -> EsSystem | None:
    explicit = parse_pfe_system(block)
    if explicit and explicit in by_name:
        return by_name[explicit]

    pfe_dir = parse_pfe_dir(block)
    if pfe_dir in by_dir:
        return by_dir[pfe_dir]

    for alias in ALIASES.get(pfe_dir, []):
        if alias in by_name:
            return by_name[alias]
        if alias in by_dir:
            return by_dir[alias]

    return None


def replace_or_insert(block: list[str], key: str, value: str, after_key: str | None = None) -> list[str]:
    target = f"-{key}="
    replacement = f"{target}{value}\n"
    for index, line in enumerate(block):
        if line.strip().startswith(target):
            block[index] = replacement
            return block

    if after_key:
        after_target = f"-{after_key}="
        for index, line in enumerate(block):
            if line.strip().startswith(after_target):
                block.insert(index + 1, replacement)
                return block

    block.append(replacement)
    return block


def update_block(block: list[str], system: EsSystem) -> list[str]:
    block = replace_or_insert(block, "SYSTEM", system.name, after_key="DIR")
    if system.extensions:
        block = replace_or_insert(block, "EXT", ",".join(system.extensions))
    if system.cores:
        block = replace_or_insert(block, "CORE", ",".join(system.cores))
    return block


def split_blocks(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    prefix: list[str] = []
    blocks: list[list[str]] = []
    current: list[str] | None = None

    for line in lines:
        if line.strip().startswith("-TITLE="):
            if current is not None:
                blocks.append(current)
            current = [line]
        elif current is None:
            prefix.append(line)
        else:
            current.append(line)

    if current is not None:
        blocks.append(current)

    return prefix, blocks


def ensure_launcher_types(prefix: list[str], emulators: list[str]) -> list[str]:
    existing = {
        line.split("=", 1)[0].strip().upper()
        for line in prefix
        if "=" in line and not line.lstrip().startswith(("-", ";", "#"))
    }

    needed: list[tuple[str, str]] = []
    for emulator in emulators:
        key = _launcher_key(emulator)
        if key in existing:
            continue
        script = "./bin/pyxel.sh" if emulator == "pyxel" else "./bin/rocknix_runemu.sh"
        needed.append((key, script))
        existing.add(key)

    if not needed:
        return prefix

    insert_at = 0
    for index, line in enumerate(prefix):
        if line.strip().startswith("TYPE_RA="):
            insert_at = index + 1
            break

    additions = [f"{key}={script}\n" for key, script in needed]
    return prefix[:insert_at] + additions + prefix[insert_at:]


def sync(es_path: Path, pfe_path: Path, write: bool) -> int:
    _, by_name, by_dir = parse_es_systems(es_path)
    lines = pfe_path.read_text(encoding="utf-8").splitlines(keepends=True)
    prefix, blocks = split_blocks(lines)

    updated_blocks: list[list[str]] = []
    matched = 0
    missing: list[str] = []
    custom_emulators: list[str] = []

    for block in blocks:
        title = next((line.split("=", 1)[1].strip() for line in block if line.strip().startswith("-TITLE=")), "?")
        system = match_system(block, by_name, by_dir)
        if not system:
            missing.append(title)
            updated_blocks.append(block)
            continue
        matched += 1
        custom_emulators.extend(
            emulator for emulator in system.custom_emulators if emulator not in custom_emulators
        )
        updated_blocks.append(update_block(block, system))

    prefix = ensure_launcher_types(prefix, custom_emulators)
    output = "".join(prefix + [line for block in updated_blocks for line in block])

    print(f"matched: {matched}/{len(blocks)}")
    if missing:
        print("missing:", ", ".join(missing))
    if custom_emulators:
        print("custom emulators:", ", ".join(custom_emulators))

    if write:
        pfe_path.write_text(output, encoding="utf-8")
    return 0 if matched else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("es_systems", type=Path)
    parser.add_argument("pfe_cfg", type=Path, nargs="?", default=Path("data/pfe.cfg"))
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    return sync(args.es_systems, args.pfe_cfg, args.write)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
