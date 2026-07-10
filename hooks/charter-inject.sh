#!/bin/bash
# Delivery mechanism for the law: reads LIVE from the vault (source of truth).
# Main session = council chair role. Subagent charters ride agent-defs (Phase 1).
CORE="${VAULT_ROOT:-$HOME/vault}"/_system/core.md
CHARTER="${VAULT_ROOT:-$HOME/vault}"/_system/charters/council.md
if [[ -f "$CORE" && -f "$CHARTER" ]]; then
  echo "<agent-stack-law>"
  cat "$CORE"
  echo ""
  cat "$CHARTER"
  echo "</agent-stack-law>"
else
  echo "<agent-stack-law-ERROR>law files missing from vault/_system — constitution NOT delivered</agent-stack-law-ERROR>"
fi
exit 0
