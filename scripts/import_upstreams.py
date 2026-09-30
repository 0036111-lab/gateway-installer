#!/usr/bin/env python3
"""Import pinned upstream sources into this repository as vendored copies.

This script intentionally keeps required Apache-2.0 licensing/NOTICE material,
while removing upstream branding from product-facing docs/config where safe.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"

SOURCES = [
    (
        "gateway",
        "https://github.com/comindspace/gateway-mcp.git",
        "d36aa25521e16c8d69ac6adde9ef14fec77a95e0",
    ),
    (
        "platform",
        "https://github.com/comindspace/ai-native.git",
        "df5588d572e343805261d16889e1db7354cfd33d",
    ),
]

# Files where third-party attribution must remain intact.
PROTECTED_BASENAMES = {"LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"}
TEXT_EXTENSIONS = {
    ".md", ".txt", ".py", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".sh", ".env", ".example", ".html", ".css", ".js", ".ts", ".tsx", ".jsx",
}

REPLACEMENTS = [
    (re.compile(r"coMind Space", re.I), "Gateway Project"),
    (re.compile(r"coMind", re.I), "Gateway Project"),
    (re.compile(r"comindspace", re.I), "gateway-project"),
    (re.compile(r"comind\.space", re.I), "example.invalid"),
]


def run(*args: str, cwd: pathlib.Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def clone_pinned(name: str, url: str, commit: str) -> pathlib.Path:
    dst = VENDOR / name
    if dst.exists():
        shutil.rmtree(dst)
    tmp = VENDOR / f".{name}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    run("git", "clone", "--no-checkout", url, str(tmp))
    run("git", "checkout", commit, cwd=tmp)
    shutil.rmtree(tmp / ".git")
    tmp.rename(dst)
    return dst


def is_text_candidate(path: pathlib.Path) -> bool:
    if path.name in PROTECTED_BASENAMES:
        return False
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    return path.name in {"Dockerfile", "Makefile", "MANIFEST.in"}


def debrand_tree(root: pathlib.Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or not is_text_candidate(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text
        for pattern, replacement in REPLACEMENTS:
            new = pattern.sub(replacement, new)
        if new != text:
            path.write_text(new, encoding="utf-8")


def assert_no_product_branding() -> None:
    hits: list[str] = []
    for root in (VENDOR / "gateway", VENDOR / "platform"):
        for path in root.rglob("*"):
            if not path.is_file() or path.name in PROTECTED_BASENAMES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if re.search(r"comind|coMind", text, re.I):
                hits.append(str(path.relative_to(ROOT)))
    if hits:
        print("Branding still present outside protected attribution files:", file=sys.stderr)
        for hit in hits:
            print(f"  - {hit}", file=sys.stderr)
        raise SystemExit(2)


def main() -> None:
    VENDOR.mkdir(exist_ok=True)
    for name, url, commit in SOURCES:
        root = clone_pinned(name, url, commit)
        debrand_tree(root)
    assert_no_product_branding()
    print("Imported pinned upstreams into vendor/gateway and vendor/platform")


if __name__ == "__main__":
    main()
