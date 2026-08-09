> Imported verbatim from the harness-v0 kit as CLAUDE.md; renamed so these
> per-part session rules (written for the five-session analyzer build, now
> complete) are a historical record, not auto-loaded standing instructions.

# harness build — standing rules

You are building the analyzer described in `BRIEF-analyzer.md`.
Read it end to end before writing anything, every session.

- One part per session. The session prompt names the part. Everything
  else, and everything under Non-goals in the brief, is out of scope.
  Do not create files for parts you were not given.
- Tests first. Write pytest tests from the Acceptance criteria that
  apply to the named part, then implement until green.
- Stdlib only. No new dependencies without asking.
- Ambiguity: add a `TODO`, take the conservative reading, and list
  every TODO you added at the end of the session. Never expand scope
  to resolve ambiguity. Never guess where the brief says flag.
- Evidence over claims. End every session by running the tests and
  showing real output against this repo — not by describing what
  should happen.
- Determinism is load-bearing. Anything that makes output depend on
  dict order, file-walk order, or timestamps is a bug, not a style
  issue. Sort before you emit.
- If `ARCHITECTURE.md` or `WRAP.md` seem to conflict with the brief,
  the brief wins. They are background, not instructions.

Build order comes from the compiled plan (`python3 speccc.py specs/`):
symbol_table → reference_map ∥ unresolved_sites → affected_symbols →
analyzer_cli. The session prompts in `PROMPTS.md` follow that order.
