# Gate port parity — F37's instrument-continuity clause

**Ruling being satisfied.** F37: *"port the gate to `python -m harness.gate`…
One instrument-continuity clause, because F26 made protocol identity
load-bearing: the port must demonstrate verdict parity with archived gate.js —
one side-by-side run, same packets, same verdicts, documented — so gate results
stay comparable across the port boundary."*

Commit: `19ca1a7`. Packets built at HEAD by `harness.join`, identical bytes
fed to every arm (hashes below).

## The confound, and why the obvious run does not settle anything

The naive side-by-side is gate.js against `harness.gate`. But gate.js runs its
probes as Claude subagents, and `harness.gate` posts to xAI — so that
comparison varies **two** things at once, the instrument and the model. Run
that way it produced 0/3 verdict agreement, which on its face reads as a failed
port and is in fact uninterpretable.

The clause is about the *instrument*. So the model is held fixed and the
instrument varied: `harness.gate` builds its three prompts, and those exact
prompts are judged by Claude, the same model the archived runner used.

## Three arms

| probe | gate.js / Claude | gate.py / Claude | gate.py / Grok |
|---|---|---|---|
| executor:symbol_table | sufficient_with_gaps | sufficient_with_gaps | sufficient |
| executor:affected_symbols | sufficient_with_gaps | sufficient_with_gaps | sufficient |
| tester:affected_symbols | sufficient_with_gaps | sufficient_with_gaps | sufficient |

**Port effect, model held fixed: 3/3 agree.** The ported instrument reproduces
the archived instrument's verdicts exactly. That is the parity F37 asked for.

**Model effect, instrument held fixed: 0/3 agree.** Every difference in the
naive comparison is attributable to the model, not the port.

## The stronger evidence is the bytes, not the verdicts

Verdict agreement is a sample of a stochastic process; three probes agreeing
once is consistent with continuity but does not prove it. The load-bearing
evidence is
`test_gate.py::test_prompt_is_byte_identical_to_the_archived_construction`,
which reconstructs gate.js's prompt from the archive and asserts the port emits
the same bytes for all three probes, plus tests pinning the preamble, the probe
list, each probe's `extra`, and the verdict enum to the archived file. Those run
every suite, forever; the parity run happened once.

That test earned its place during this build. My first port appended a
"respond in JSON" instruction into the prompt, while gate.js constrains shape
out-of-band with a `schema` parameter. The verdicts would very likely still have
matched, and the gate would have been quietly measuring a different prompt under
the same name — F26 recurring, with a version boundary to hide behind. Shape
enforcement now lives in a system message plus `response_format`, and
`test_shape_enforcement_stays_out_of_band` asserts no JSON instruction reaches
the measured text.

## What the third arm says, which is not a port question

Grok returned `sufficient` on all three probes with **zero** missing items,
against Claude's 4–6 items per probe. No verdict in this loop's history has been
`sufficient`; the packets are the same ones that were judged gappy minutes
earlier by the same prompt.

A gate whose probes never report a gap is not measuring packet sufficiency — the
misses are the telemetry, and this arm produced none. So gate results are
comparable across the **port** boundary and **not** across a model boundary: the
model is part of the instrument. Filed as **F38** rather than acted on here.

## Reproduction

```
python -m harness.gate --json          # requires XAI_API_KEY
```

Artifacts in this directory: `verdicts.json` (all three arms plus per-probe
missing-item counts), `gate_py_grok.json` (the full Grok run).

Input hashes — the same three packets fed to every arm:

```
c3880707ec1997d756225da2b3de3327f0f7fc86026fae113d4959edb2d0b28d  packet_st.md
4e3083018182b089017ae19c0541f5ef1ccb290b1ad5c781bd827fe171844348  packet_af.md
740b363784de2e20f1abe7537a6a9151b33a0b7fa0aa418517e8b0f34355c09c  packet_at.md

aab3ce749415dad67607000d7a8fdac323ab5142680e0af3d7ba0d099f508f5f  prompt_executor_symbol_table.txt
b4dc8a9b5815a07cbe108d12772d7c47491b443fc8f6654443136559dd1c74e5  prompt_executor_affected_symbols.txt
28fe747d0334104babc70741cc79bb34bcc495e165de02e7b41064b561c125cd  prompt_tester_affected_symbols.txt
```

The prompt files are exactly `harness.gate.build_prompt(packet, extra)` output;
they were the literal text sent to the Claude arm, so the middle column is the
port's own construction and not a re-transcription of it.
