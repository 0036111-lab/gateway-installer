#!/usr/bin/env python3
"""Import pinned upstream sources as vendored copies.

The import creates technical independence from the upstream repositories.
Apache-2.0 licensing/attribution material is preserved. Non-legal upstream
branding is rewritten across the vendored source tree and audited afterwards.
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

# Keep upstream license/notice files verbatim.
PROTECTED_BASENAMES = {"LICENSE", "NOTICE"}
LEGAL_LINE = re.compile(r"copyright|licensed under|developed by", re.I)
BRAND_PATTERN = re.compile(r"comind", re.I)

# Specific compatibility names first, then general branding.
REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"GATEWAY_COMIND_MR_REVIEW_CHAT_ID"), "GATEWAY_SKILL_REVIEW_CHAT_ID"),
    (re.compile(r"GATEWAY_COMIND_CHAT_ID"), "GATEWAY_SKILL_UPDATE_CHAT_ID"),
    (re.compile(r"TELEGRAM_COMIND_CHAT_ID"), "TELEGRAM_SKILL_UPDATE_CHAT_ID"),
    (re.compile(r"comind_skill_update", re.I), "skill_update"),
    (re.compile(r"Comind AI Native Auth", re.I), "Gateway Platform Auth"),
    (re.compile(r"Comind AI Native", re.I), "Gateway Platform"),
    (re.compile(r"sales-assistant@comind\.space", re.I), "sales-assistant@example.invalid"),
    (re.compile(r"employee@comind\.space", re.I), "employee@example.invalid"),
    (re.compile(r"hermes-service@comind\.space", re.I), "hermes-service@example.invalid"),
    (re.compile(r"team@comind\.space", re.I), "maintainers@example.invalid"),
    (re.compile(r"https://github\.com/comindspace/gateway-mcp", re.I), "https://github.com/0036111-lab/gateway-installer"),
    (re.compile(r"https://github\.com/comindspace/ai-native", re.I), "https://github.com/0036111-lab/gateway-installer"),
    (re.compile(r"github\.com/comindspace", re.I), "github.com/0036111-lab"),
    (re.compile(r"comind\.space", re.I), "example.invalid"),
    (re.compile(r"comindspace", re.I), "gateway-project"),
    (re.compile(r"coMind Space", re.I), "Gateway Project"),
    (re.compile(r"\bcomind\b", re.I), "gateway"),
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


def rewrite_nonlegal_branding(root: pathlib.Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or path.name in PROTECTED_BASENAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        out: list[str] = []
        changed = False
        for line in text.splitlines(keepends=True):
            # Preserve explicit legal attribution/copyright lines.
            if LEGAL_LINE.search(line):
                out.append(line)
                continue
            new_line = line
            for pattern, replacement in REPLACEMENTS:
                new_line = pattern.sub(replacement, new_line)
            changed = changed or (new_line != line)
            out.append(new_line)

        if changed:
            path.write_text("".join(out), encoding="utf-8")


def audit_branding() -> list[str]:
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
                if LEGAL_LINE.search(line):
                    continue
                hits.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()}")
    return hits


def main() -> None:
    VENDOR.mkdir(exist_ok=True)
    for name, url, commit in SOURCES:
        root = clone_pinned(name, url, commit)
        rewrite_nonlegal_branding(root)

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
