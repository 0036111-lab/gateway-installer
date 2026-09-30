#!/usr/bin/env python3
"""Import pinned upstream sources as vendored copies.

The import is designed for technical independence from upstream repositories.
It preserves third-party licensing/attribution material and removes upstream
branding from product-facing material only. Unknown occurrences are reported
for manual review instead of being rewritten blindly.
"""

from __future__ import annotations

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

# Files that must remain verbatim for Apache-2.0 compliance.
PROTECTED_BASENAMES = {"LICENSE", "NOTICE"}

# Product-facing files/directories where upstream branding can be changed.
PRODUCT_FACING_NAMES = {
    "README.md",
    "README.ru.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "plugin.yaml",
    "pyproject.toml",
}
PRODUCT_FACING_PARTS = {
    ".agents",
    ".claude-plugin",
    ".cursor-plugin",
    ".zcode-plugin",
    "docs",
    "plugins",
    "skills",
}

BRAND_REPLACEMENTS = [
    (re.compile(r"coMind Space", re.I), "Gateway Project"),
    (re.compile(r"\bcoMind\b", re.I), "Gateway Project"),
    (re.compile(r"comindspace", re.I), "gateway-project"),
    (re.compile(r"comind\.space", re.I), "example.invalid"),
]
BRAND_PATTERN = re.compile(r"comind|coMind", re.I)


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


def is_product_facing(path: pathlib.Path, root: pathlib.Path) -> bool:
    rel = path.relative_to(root)
    if path.name in PROTECTED_BASENAMES:
        return False
    if path.name in PRODUCT_FACING_NAMES:
        return True
    return any(part in PRODUCT_FACING_PARTS for part in rel.parts[:-1])


def rewrite_product_branding(root: pathlib.Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or not is_product_facing(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        # Never rewrite lines that look like legal attribution/copyright notices.
        out: list[str] = []
        changed = False
        for line in text.splitlines(keepends=True):
            if re.search(r"copyright|licensed under|developed by", line, re.I):
                out.append(line)
                continue
            new_line = line
            for pattern, replacement in BRAND_REPLACEMENTS:
                new_line = pattern.sub(replacement, new_line)
            changed = changed or (new_line != line)
            out.append(new_line)

        if changed:
            path.write_text("".join(out), encoding="utf-8")


def audit_branding() -> list[str]:
    """Return remaining non-legal occurrences for explicit review."""
    hits: list[str] = []
    for root in (VENDOR / "gateway", VENDOR / "platform"):
        for path in root.rglob("*"):
            if not path.is_file() or path.name in PROTECTED_BASENAMES:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for n, line in enumerate(lines, 1):
                if not BRAND_PATTERN.search(line):
                    continue
                if re.search(r"copyright|licensed under|developed by", line, re.I):
                    continue
                hits.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()}")
    return hits


def main() -> None:
    VENDOR.mkdir(exist_ok=True)
    for name, url, commit in SOURCES:
        root = clone_pinned(name, url, commit)
        rewrite_product_branding(root)

    hits = audit_branding()
    if hits:
        print("Remaining upstream-brand references require manual review:", file=sys.stderr)
        for hit in hits:
            print(f"  - {hit}", file=sys.stderr)
        raise SystemExit(2)

    print("Imported pinned sources into vendor/gateway and vendor/platform")
    print("Required LICENSE/NOTICE files were preserved verbatim.")


if __name__ == "__main__":
    main()
