#!/usr/bin/env bash
# lex — the interactive interface to the harness.
#
# v0 rides the existing chassis: this opens a dedicated operator agent in
# the lex repo with the lex-operator skill in hand. The custom REPL is the
# product version, once the operator skill has real sessions behind it.
#
#   lex                 open the operator
#   lex plan            open it and go straight to /plan
#   lex run <node>      open it and go straight to /run <node>
#
# Anything after `lex` is passed through as the opening verb.

set -euo pipefail

LEX_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$LEX_HOME"

case "${1:-}" in
  -h|--help|help)
    sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    echo
    echo "verbs: plan | run <node> | status | replay | evals | ledger"
    exit 0
    ;;
esac

if ! command -v claude >/dev/null 2>&1; then
  echo "lex: the 'claude' CLI is not on PATH — lex v0 runs on that chassis." >&2
  exit 1
fi

if [ "$#" -eq 0 ]; then
  OPENING="/lex"
else
  OPENING="/$*"
fi

exec claude "$OPENING"
