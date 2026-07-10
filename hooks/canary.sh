#!/bin/bash
# Liveness proof: if this ran, the SessionStart chain fired.
# Beacon (Phase 2) alarms on staleness. "No data" must be distinguishable from "recorder dead".
DIR="${VAULT_ROOT:-$HOME/vault}"/god/canary
mkdir -p "$DIR"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf '{"last_boot":"%s","chain":"sessionstart"}\n' "$TS" > "$DIR/last-boot.json"
printf '{"ts":"%s","event":"sessionstart"}\n' "$TS" >> "$DIR/boot-log.jsonl"
exit 0
