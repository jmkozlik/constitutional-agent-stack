LEX LAB — DESIGN & BUILD BRIEF (governing doc: commit as
docs/lab-brief.md; the build cites it the way packets cite spec)

WHAT THIS IS
A local instrument for operating and inspecting the lex harness.
Not a SaaS dashboard, not a marketing page — an instrument.
The character in one line: court record meets mission control.
Dense, typographic, quiet, honest. If Linear and a legal ledger
had a terminal baby.

THE ONE DESIGN LAW (non-negotiable, the soul of the product):
EVERY NUMBER IS A CITATION. No stat, verdict, or chart point may
render without a provenance affordance — hover/tap reveals the
file, record, and hash it came from, and clicking goes there.
A number the UI cannot cite does not render. This is the
constitution as UX.

VISUAL SYSTEM
- Theme: dark default. Paper #0E0F11, ink #E8E6E1, hairline
  borders #26282B. ONE accent: amber #E2B93B, used ONLY for
  attention states (NOT CITABLE, pending confirm, stops).
- Semantic verdict colors, used nowhere else: IDENTICAL #4C9A6A,
  DIVERGED #C0554D, CHECK-ERROR/unknown #8A8F98, empty/
  validation-only = dim ink, never green (empty is a state, not
  a win).
- Type: IBM Plex family throughout — Plex Sans for chrome, Plex
  Mono for anything that is evidence (hashes, verdicts, paths,
  argv, diffs, token counts), Plex Serif for law (rulings,
  findings text, the monarch's vision.md). Three voices: chrome,
  evidence, law. Never mix them.
- Density: information-dense, 13-14px base, generous line-height,
  tables over cards. Hashes truncate to 8 chars with copy-on-
  click, full on hover.
- Motion: none decorative. State changes may fade 120ms. Nothing
  slides, bounces, or shimmers.

FORBIDDEN (refuse even if it looks "nicer"): gradients, glass/
blur, purple/indigo defaults, emoji in chrome, card grids of
stat tiles, rounded-2xl everything, skeleton shimmer, hero
sections, illustrations. Empty states name the file that would
populate them ("no dispatch records yet — runs/ is empty").

LAYOUT MODEL
Three regions. Left rail: nav (Session, Runs, Law, Graph, Evals,
Monarch, Lab) + connection state. Main stage: the active view.
Right inspector (collapsible): detail of whatever is selected —
click a dispatch row, an F-number, a graph node, and its full
record/history renders here without leaving the view.
Global status bar, always visible: provider·model, current plan
hash, F36 state (as a real badge while open), session token
meter ticking live.

VIEWS
1. SESSION (home) — the operator conversation. Transcript with
   tool calls as collapsed evidence cards (argv line visible,
   result expandable, duration + tokens on the card). Mutations
   open a CONFIRM MOTION modal: what will run, exact argv, and a
   typed "y" — Enter does not approve, mirroring the CLI law.
   Every approved mutation drops a ledger chip into the
   transcript. Composer at bottom; Esc never loses a draft.
2. RUNS — dispatch records as a sortable table: id, node, role,
   verdict chips, wall-clock, tokens (or "unavailable", never
   blank), reads_out_of_packet count. Row → inspector: full
   record, artifact list, fence set, transcript link.
3. LAW — the findings ledger F1–F37 as the primary table
   (status, blocking, one-line title); selecting an F renders
   its life as a timeline (filed → ruled → applied → closed)
   assembled from the reports that mention it, each hop linked
   to the report section. Reports readable in-place, Serif.
4. GRAPH — the plan as a leveled DAG, levels as columns, nodes
   carrying their delta badge; edges = references. Click a node:
   inspector shows its surface and what its packet would carry.
   Symbol-level graph (callers/imports from the index) as a
   second tab, loaded on demand.
5. EVALS — /evals as small multiples: miss depth per node, cost
   per dispatch, reads, replay tally. NOT CITABLE renders as an
   amber-asterisked state with the open finding named — styled,
   never hidden.
6. MONARCH — vision.md in a Serif editor, side-by-side diff
   before save, save is a confirm motion that files a ledger
   entry. No autosave. The law does not autosave.
7. LAB — provider/model pickers (backed by the real env knobs),
   lex-version launcher (git ref → worktree → session), and
   side-by-side comparison of any two dispatch records.

TECH CONSTRAINTS
FastAPI backend serving a single-page frontend from the repo;
`lex ui` opens localhost. Chat over SSE/websocket to the
existing lex loop — canonical history and confirm gates
untouched; the browser is a second frontend, the terminal
remains the first. Read layer = file readers over reports/,
runs/, harness/specs/, the ledger, evals output. No external
services, no telemetry leaves the machine, vault stays local.

SEQUENCE (demo-honest)
v0 by the 12th: Session, Runs, Evals, Law, status bar — real
data, this visual system, no placeholders. Graph, Monarch, Lab:
the week after. Screenshot checkpoint after the first view is
styled, BEFORE building the rest — one course-correction beats
seven repaints.
