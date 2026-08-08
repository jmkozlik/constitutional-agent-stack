---
description: Replay the shipped packets on record and report per-packet verdicts.
---
Follow the `lex-operator` skill.

For each shipped packet under `docs/evidence/`, run
`python -m harness.join replay <node> --role <role> --commit <commit> --shipped <path>`
and report IDENTICAL / DIVERGED / CHECK-ERROR per packet, with the diff head
for any divergence. Replay is commit-anchored and join-version pinned, so a
divergence means the packet, not the compiler.
