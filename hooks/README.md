# hooks/ — the mechanical enforcement layer

These are Claude Code hooks. They are the part of the constitution that does
not depend on any agent choosing to obey it: exit code 2 from a PreToolUse
hook blocks the tool call outright. Judgment proposes, arithmetic disposes.

All hooks resolve the vault via the `VAULT_ROOT` environment variable
(default `~/vault`). All blocking hooks fail-open on their own errors —
machinery must never wedge a session — except spawn-guard, which fails-closed
when run state is unreadable (no run state, no executor spawns).

## Files here (hook-only machinery)

| file | event | function |
|---|---|---|
| `canary.sh` | SessionStart | liveness proof: records boot timestamp so "no data" is distinguishable from "recorder dead" |
| `charter-inject.sh` | SessionStart | delivers the law: injects core.md + council charter (the main session is the chair) live from the vault |
| `ledger-guard.js` | PreToolUse (Write/Edit/NotebookEdit) | the ledger is append-only for everyone: blocks edits to existing entries; canonicalizes paths to close symlink/case tricks |
| `spawn-guard.js` | PreToolUse (Agent/Task) | no executor spawns without an active run and an existing contract file (`EXECUTOR-SPAWN` + `CONTRACT:` marker lines) |
| `quick-bounds.js` | PreToolUse (Bash) | quick-lane commits are mechanically bounded (≤2 files, ≤150 lines, no dependency manifests); blocks stage-and-commit one-shots that would evade the staged-diff bound |
| `telemetry.js` | PostToolUse (all) | silent raw event capture to `$VAULT_ROOT/.telemetry/` — the observers' feed; agents do not read it |
| `clerk.js` | manual (`node clerk.js <run-id>`) | god-space machinery: compiles the anonymized end-of-run grievance digest from executor debriefs; strips identity, censors nothing |

## Deployed copies not duplicated here

The production `~/.claude/hooks/` directory also carries deployed copies of
`beacon.js`, `beacon-alarm.js`, `graduation.js`, `leak-linter.js`,
`retaliation-flag.js`, `compile.js`, and the compiler's templates + manifest.
Their canonical sources live in [`../tools/stack-tools/`](../tools/stack-tools/)
in this repo; they are byte-identical at deploy time (installed by the
promotion procedure after canary).

## Wiring (settings.json)

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [
        { "type": "command", "command": "bash \"$HOME/.claude/hooks/canary.sh\"", "timeout": 5 },
        { "type": "command", "command": "bash \"$HOME/.claude/hooks/charter-inject.sh\"", "timeout": 5 }
      ]}
    ],
    "PreToolUse": [
      { "matcher": "Write|Edit|NotebookEdit", "hooks": [
        { "type": "command", "command": "node \"$HOME/.claude/hooks/ledger-guard.js\"", "timeout": 5 } ]},
      { "matcher": "Agent|Task", "hooks": [
        { "type": "command", "command": "node \"$HOME/.claude/hooks/spawn-guard.js\"", "timeout": 5 } ]},
      { "matcher": "Bash", "hooks": [
        { "type": "command", "command": "node \"$HOME/.claude/hooks/quick-bounds.js\"", "timeout": 5 } ]}
    ],
    "PostToolUse": [
      { "matcher": ".*", "hooks": [
        { "type": "command", "command": "node \"$HOME/.claude/hooks/telemetry.js\"", "timeout": 5 } ]}
    ]
  }
}
```

Set `VAULT_ROOT` in the environment Claude Code runs under (or rely on the
`~/vault` default).
