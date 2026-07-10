---
type: law
labels: [knowledge, retrieval]
status: live
---
# Retrieval Guide — how every agent finds context

## The four-step descent (always in this order, cheapest first)
1. INDEX — read the relevant section's `_index.md` (~50 tokens).
2. LABEL — match frontmatter `labels:` against the vocabulary below.
3. GREP — keyword-search note bodies, only within the label-matched set.
4. LINKS — follow `[[wikilinks]]` outward exactly 1 hop.
Stop as soon as you have what you need. Embeddings do not exist here.

## Controlled vocabulary (the ONLY legal labels)
governance · constitution · executor · observer · council · monarch ·
contract · run · scorecard · motion · case · mutiny · promotion ·
knowledge · pattern · failure · taste · retrieval · architecture ·
agent-stack · rehydration · telemetry · spec · genesis ·
<one label per governed project — e.g. project-alpha · project-beta>

## Missing a label?
Tag with the CLOSEST existing label and append one JSON line to
`$VAULT_ROOT/.vocab-gaps.jsonl`:
`{"wanted": "<label>", "used": "<label>", "note": "<path>", "by": "<agent-id>"}`
Retrievers log the mirror case ("label returned mud") the same way.
The gardener batches these; do not invent labels inline. Work never blocks
on vocabulary.

## Per-role recipes
- Context-builder rebuilding an executor: executors/contracts/<run> → executors/active/<id>
  → knowledge/projects/<project>/map.md → 1-hop links from the state note.
- Observer building a case: executors/archive/<run-id>/ → observers/scorecards/
  → ledger/ (cite entry filenames as evidence ids).
- Chair rehydrating: council/state.md → council/roster.md → open contracts →
  ledger entries since last state update.
