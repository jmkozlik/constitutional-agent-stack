---
description: Run the standing gate (three-probe protocol) plus replay, and report the numbers.
---
Follow the `lex-operator` skill.

Regenerate the three gate packets at HEAD, run the archived gate protocol
(`docs/evidence/step3t/gate.js`, reused verbatim — only the packet payload
changes), and run replay. Report: the three probe verdicts in full, replay
verdicts, index scope, and the test suite count. Apply the ratified
stop-routing — a blocking signal stops the line it gates; a verdict whose
substance is an already-ruled queued finding is corroboration, not a new
stop. Do not hand-patch anything to make a probe pass.
