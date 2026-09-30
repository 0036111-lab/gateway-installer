# Vendored source snapshot

Status: generated and audit-passed on 2026-09-30.

Contents:
- `gateway` — source snapshot pinned to `d36aa25521e16c8d69ac6adde9ef14fec77a95e0`
- `platform` — source snapshot pinned to `df5588d572e343805261d16889e1db7354cfd33d`
- total files: 465

Verification performed by CI:
- both upstream repositories cloned at the exact pinned commits;
- nested `.git` metadata removed;
- non-legal `coMind` / `comindspace` branding rewritten;
- final audit found no upstream-brand references outside required `NOTICE` attribution;
- both upstream `LICENSE` and `NOTICE` files retained verbatim.

Snapshot hashes:
- GitHub Actions ZIP: `sha256:f5f0825f07377fc0e889a74885903085bb7941bfcf15b7489affad1a040351bc`
- inner `vendor-snapshot.tar.gz`: `sha256:064d7c2e5509b30e3f9b65939e7b044c9d27b623b930f62129d7883ebe172d11`

The expanded `vendor/gateway` and `vendor/platform` trees are the intended canonical in-repository layout. Until those expanded files are committed, this branch is intentionally kept as a draft PR and must not be merged as the final independent distribution.
