---
description: Run the full dispatch loop for a node (prepare, spawn, harvest, report).
argument-hint: <node> [--role executor|tester]
---
Follow the `lex-operator` skill, orchestration section, for: $ARGUMENTS

Show what the dispatch would be and what the gate says about its packet,
then WAIT for approval. On approval: `dispatch prepare`, spawn with the
compiled prompt verbatim, stream progress, surface any REQUEST_MEM as an
inline question, then harvest, rerun the agent's verification yourself,
tear down, and file the report and LOOP update.
