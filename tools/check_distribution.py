#!/usr/bin/env python3
"""Validate PFE distribution files before packaging or copying to a device."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PYXEL_VERSION = "2.9.5"

CONFIG_FILES = (
    "data/pfe.cfg",
    "data/pfe.cfg.example",
)

MARKDOWN_FILES = (
    "README.md",
    "README_JP.md",
    "INSTALL.md",
    "INSTALL_JP.md",
    "docs/ARCHITECTURE.md",
    "docs/ARCHITECTURE_JP.md",
    "docs/RELEASE_JP.md",
    "docs/ROCKNIX_JP.md",
    "docs/releases/v1.0.0.md",
    "docs/releases/v1.0.1.md",
    "docs/releases/v1.0.2.md",
    "tools/rocknix/README_JP.md",
)

PYXEL_VERSION_FILES = (
    "requirements.txt",
    "tools/rocknix/requirements.txt.example",
    "tools/rocknix/ports/01_install_pyxel.sh",
    "tools/rocknix/rocknix_pyxel_setup.sh",
    "INSTALL.md",
    "INSTALL_JP.md",
    "docs/ARCHITECTURE.md",
    "docs/ARCHITECTURE_JP.md",
    "tools/rocknix/README_JP.md",
)

OLD_ROOT_MODULES = (
    "bgm_manager.py",
    "brightness_manager.py",
    "config.py",
    "debug.py",
    "input_handler.py",
    "japanese_text.py",
    "launcher.py",
    "music_mode.py",
    "persistence.py",
    "rom_manager.py",
    "screenshot_loader.py",
    "state_manager.py",
    "system_monitor.py",
    "theme_manager.py",
    "version.py",
)


class Checker:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)

    def local_path_exists(self, value: str) -> bool:
        path = Path(value)
        if path.is_absolute():
            return True
        if value.startswith("./"):
            path = Path(value[2:])
        return (ROOT / path).exists()

    def check_required_tree(self) -> None:
        required = (
            "main.py",
            "launcher.sh",
            "pfe_app/__init__.py",
            "pfe_app/config.py",
            "ui/__init__.py",
            "data/pfe.cfg",
            "data/pfe.cfg.example",
            "tools/build_release.py",
            "tools/check_distribution.py",
            "tools/rocknix/ports/01_install_pyxel.sh",
            "tools/rocknix/ports/02_install_pfe.sh",
            "tools/rocknix/ports/Switch_to_PFE.sh",
        )
        for relative in required:
            if not (ROOT / relative).exists():
                self.fail(f"required file is missing: {relative}")

        for relative in OLD_ROOT_MODULES:
            if (ROOT / relative).exists():
                self.fail(f"old root module should live under pfe_app/: {relative}")

    def check_config(self, relative: str) -> None:
        sys.path.insert(0, str(ROOT))
        from pfe_app.config import Config

        config = Config(str(ROOT / relative))
        if not config.categories:
            self.fail(f"{relative}: no categories parsed")
            return

        self.note(f"{relative}: {len(config.categories)} categories")

        for category in config.categories:
            if not category.name:
                self.fail(f"{relative}: category without title")
            if not category.directory:
                self.fail(f"{relative}: {category.name}: missing -DIR")
            if not category.extensions:
                self.fail(f"{relative}: {category.name}: missing -EXT")
            if not category.cores:
                self.fail(f"{relative}: {category.name}: missing -CORE")
            if category.title_img and not self.local_path_exists(category.title_img):
                self.fail(f"{relative}: {category.name}: title image missing: {category.title_img}")

            for core in category.cores:
                if ":" not in core:
                    continue
                prefix, name = core.split(":", 1)
                if prefix.upper() == "SA":
                    type_key = f"TYPE_SA_{name.upper()}"
                else:
                    type_key = f"TYPE_{prefix.upper()}"
                if not config.global_vars.get(type_key):
                    self.fail(f"{relative}: {category.name}: {core} requires {type_key}")

        for key, value in sorted(config.global_vars.items()):
            if key.startswith("TYPE_") or key.endswith("_SCRIPT"):
                if not self.local_path_exists(value):
                    self.fail(f"{relative}: {key} points to missing file: {value}")

        self.check_duplicate_globals(relative)

    def check_duplicate_globals(self, relative: str) -> None:
        seen: dict[str, int] = {}
        for line_number, line in enumerate((ROOT / relative).read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith((";", "#", "-")) or "=" not in stripped:
                continue
            key = stripped.split("=", 1)[0].strip().upper()
            if key in seen:
                self.fail(f"{relative}: duplicate global {key} at lines {seen[key]} and {line_number}")
            else:
                seen[key] = line_number

    def check_pyxel_versions(self) -> None:
        expected = f"pyxel>={EXPECTED_PYXEL_VERSION}"
        stale_pattern = re.compile(r"\b(?:2\.2\.7|2\.6\.6)\b")
        for relative in PYXEL_VERSION_FILES:
            path = ROOT / relative
            if not path.exists():
                self.fail(f"version check file missing: {relative}")
                continue
            text = path.read_text(encoding="utf-8")
            if stale_pattern.search(text):
                self.fail(f"{relative}: stale Pyxel version remains")
            if "ARCHITECTURE" in relative:
                if f"Pyxel {EXPECTED_PYXEL_VERSION}" not in text:
                    self.fail(f"{relative}: missing Pyxel {EXPECTED_PYXEL_VERSION} tech stack entry")
            elif expected not in text:
                self.fail(f"{relative}: missing {expected}")

    def check_markdown_fences(self) -> None:
        for relative in MARKDOWN_FILES:
            path = ROOT / relative
            if not path.exists():
                self.fail(f"markdown file missing: {relative}")
                continue
            count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("```"))
            if count % 2 != 0:
                self.fail(f"{relative}: unbalanced markdown code fences ({count})")

    def check_rocknix_install_safety(self) -> None:
        pfe_installers = (
            "tools/rocknix/ports/02_install_pfe.sh",
            "tools/rocknix/rocknix_pfe_service_install.sh",
        )
        for relative in pfe_installers:
            text = (ROOT / relative).read_text(encoding="utf-8")
            for marker in ("install_pfe_requirements", "validate_pfe_python", "--no-deps"):
                if marker not in text:
                    self.fail(f"{relative}: missing PFE dependency safety marker: {marker}")
            for marker in ("configure_retroarch_menu", "menu_driver", '"rgui"'):
                if marker not in text:
                    self.fail(f"{relative}: missing RetroArch menu readability marker: {marker}")
            if "install_frontend_apply_service" in text:
                self.fail(f"{relative}: stale boot frontend apply service installer remains")
            for marker in ("cleanup_stale_frontend_apply_service", "pfe-frontend-apply.service", "apply_frontend.sh"):
                if marker not in text:
                    self.fail(f"{relative}: missing stale boot apply cleanup marker: {marker}")
            for marker in ("RequiresMountsFor", "PFE_STORAGE_TIMEOUT", "PFE_WAYLAND_TIMEOUT", "WorkingDirectory=/storage"):
                if marker not in text:
                    self.fail(f"{relative}: missing boot PFE storage/readiness marker: {marker}")

        switchers = (
            "tools/rocknix/ports/Switch_to_PFE.sh",
            "tools/rocknix/rocknix_switch_to_pfe.sh",
        )
        for relative in switchers:
            text = (ROOT / relative).read_text(encoding="utf-8")
            for marker in ("install_switch_worker", "switch_to_pfe_worker.sh", "systemd-run"):
                if marker not in text:
                    self.fail(f"{relative}: missing PFE switch safety marker: {marker}")
            for marker in ("pfe_runtime_ready", "PFE_READY_SECONDS", "PFE_NO_RESTART_FILE", "fallback_to_es"):
                if marker not in text:
                    self.fail(f"{relative}: missing PFE switch readiness marker: {marker}")

    def check_release_file_list(self) -> None:
        sys.path.insert(0, str(ROOT / "tools"))
        from build_release import iter_files

        release_files = {path.relative_to(ROOT).as_posix() for path in iter_files()}
        forbidden = (
            "bin/tooles.sh",
            "data/pfe.cfg_dArkOS",
            "assets/bgm/書かれていない一行.mp3",
        )
        for relative in forbidden:
            if relative in release_files:
                self.fail(f"release zip would include local-only file: {relative}")

        for relative in release_files:
            if relative.startswith("data/pfe.cfg_"):
                self.fail(f"release zip would include local config variant: {relative}")
            if relative.startswith("assets/bgm/") and relative.endswith(".mp3"):
                if not Path(relative).name.startswith("PFE_BGM_"):
                    self.fail(f"release zip would include non-PFE BGM file: {relative}")

    def run(self) -> int:
        os.chdir(ROOT)
        self.check_required_tree()
        for relative in CONFIG_FILES:
            self.check_config(relative)
        self.check_pyxel_versions()
        self.check_markdown_fences()
        self.check_rocknix_install_safety()
        self.check_release_file_list()

        for note in self.notes:
            print(f"OK: {note}")

        if self.failures:
            print("\nDistribution check failed:")
            for failure in self.failures:
                print(f"- {failure}")
            return 1

        print("OK: distribution files are consistent")
        return 0


if __name__ == "__main__":
    raise SystemExit(Checker().run())
