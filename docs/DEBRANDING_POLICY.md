# Debranding and provenance policy

Goal: make this repository operationally independent from the upstream repositories while preserving required open-source attribution.

## Product-facing layer

The distributed product must not present itself as a coMind/coMind Space product. Product name, README copy, UI text, commands, examples, plugin manifests, documentation, service labels and generated client configuration may use this project's own naming.

## Legal/provenance layer

Apache-2.0 licensing material that applies to imported code is retained. In particular, upstream LICENSE and NOTICE files are preserved verbatim inside the vendored source trees, and the root NOTICE / THIRD_PARTY_NOTICES document the origin of the imported code.

Copyright or attribution notices found in source files must not be removed automatically. Any such occurrence is reviewed before modification.

## Import policy

Pinned source versions:

- gateway-mcp: d36aa25521e16c8d69ac6adde9ef14fec77a95e0
- ai-native: df5588d572e343805261d16889e1db7354cfd33d

The import process removes .git history from vendored copies. Runtime/builds must use the vendored copies and must not clone or fetch the upstream repositories.

Expected layout:

- vendor/gateway — independent source snapshot derived from gateway-mcp
- vendor/platform — independent source snapshot derived from ai-native
- installer — new deployment/onboarding code owned by this project
- clients — client adapters, initially Hermes

## Verification

Before a vendor snapshot is accepted:

1. LICENSE and NOTICE files exist in each vendored source tree.
2. Upstream git metadata is absent.
3. No runtime/build step requires github.com/comindspace.
4. Non-legal coMind/comindspace references are removed from product-facing material.
5. Remaining references are limited to required attribution/provenance and are reviewed explicitly.
6. The vendored code builds/tests without network access to the upstream repositories, except normal dependency package registries where required.
