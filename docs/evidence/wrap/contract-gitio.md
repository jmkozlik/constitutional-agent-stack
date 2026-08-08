---
type: contract
labels: [contract, run]
run-id: r-lex-001
status: immutable
---
# Contract — gitio
## Goal
Git plumbing for the analyzer - file listings, blob contents, and diff ranges at a rev, all read from git objects without checkouts.
## Files owned (exhaustive — touching anything else is a violation)
- analyzer/gitio.py
## Protocol scaffolding (worktree-local, NEVER merged)
The following files are maintained ON DISK in the executor's worktree as a
standing protocol obligation, are NOT part of the owned-files list above, and
MUST NEVER be staged, committed, or merged. They are harvested from the
worktree directly, not through git:
- .stack-state.md   (executor working-state note)
- <any additional chair-named protocol scaffolding for this run>

The owned-files list being "exhaustive" governs MERGE SCOPE only; it does not
override this clause. An executor that commits a file named here has committed
a contract violation and must untrack it (`git rm --cached <path>`) before the
branch is presented for integration. Worked example: after any commit,
`git ls-files | grep -F .stack-state.md` returns nothing.
## Interface spec (what the test-engineer builds fixtures from)
- read_files and list_py_files answer from git objects, never a checkout.
- changed_files surfaces a renamed file as a delete plus an add, never a rename.
- A failing git command raises GitError, never a silent empty result.
- callables:
  - analyzer.gitio.changed_files(repo: str | Path, old: str, new: str) -> dict[str, tuple[list[Range], list[Range]]]  [seeded]
  - analyzer.gitio.list_py_files(repo: str | Path, rev: str) -> list[str]  [seeded]
  - analyzer.gitio.read_files(repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]  [seeded]
  - analyzer.gitio.resolve_commit(repo: str | Path, rev: str) -> str  [seeded]
- types:
  - analyzer.gitio.Range = tuple[int, int]  [authored]
- errors:
  - analyzer.gitio.GitError: raised by every callable when the underlying git command exits non-zero, naming the failed command  [seeded]
## Rate-limited / decorator-wrapped handler test idiom (motion m-w1a, r007)
If a contract names a handler decorated with `@limiter.limit` (slowapi) — or any
decorator that intercepts the call before the function body — as the unit under
test, the contract MUST state BOTH of the following, or it is a returnable defect:

  (i)  The real-Request construction idiom. slowapi rejects any `request`
       argument that is not a genuine `starlette.requests.Request`. A bare
       `MagicMock()` request FAILS. Cite the in-repo scope-dict idiom the test
       must use to build a real Request — name the file:line it is copied from
       (e.g. a `Request({"type":"http", ...})` scope-dict pattern), per
       worked-example fidelity (§1d / motion 0035).
  (ii) The direct-call interception warning. A test that calls the handler
       directly (not through the ASGI/TestClient stack) exercises a DIFFERENT
       codepath than the live route: the decorator wrapper and routing
       normalization are bypassed. State explicitly whether the gate tests the
       handler directly or through the route. A direct-call gate on a decorated
       handler must say so, and must use the real-Request idiom above.
(Worked example of the failing pattern: two pytest cycles burned on `MagicMock()`
requests before the scope-dict idiom was found — r007 w1-t4.)
## Hard-error-class assertions enumerate their violating inputs (motion m-w1b, r007)
Whenever a contract asserts a hard error-class boundary on a handler's behavior —
"do NOT 500", "never raise", "no uncaught exception", "must return 4xx not 5xx",
or equivalent — the clause MUST enumerate, as REQUIRED worked-example rows, the
malformed inputs that would actually trigger that error class if unguarded. The
enumeration is a FLOOR (per the orphan-sweep pattern):
  - Minimum vectors for a string/path input reaching the filesystem or a parser:
    null byte (`\x00` / `%00`), encoding error (invalid percent-encoding,
    malformed UTF-8), overlong input, and any primitive the handler calls that
    can raise (e.g. `Path.resolve()` raises `ValueError` on an embedded null byte).
  - The chair MUST grep the handler body for any call documented to raise on
    malformed input (`Path.resolve()`, `int()`, `json.loads()`, `uuid.UUID()`, a
    custom parser, etc.) and add a malformed-input row for EACH — the floor list
    alone does not generalize to a handler that calls `json.loads()` on the body.
  - Each row states input → expected non-error outcome (e.g.
    `viz_id = "legit%00evil"` → 404, NOTHING written, no uncaught exception).
A "do NOT 500" assertion that lists zero 500-producing inputs is a contract
defect (the violating input escapes the authored gate — r007 w1-t1 null-byte 500,
caught only by the refuter).
## Enumerated branches are a fixture-coverage floor (motion 0070, r008)
Whenever the interface spec enumerates an outcome as a DISTINCT branch — not just
the happy path and not just the malformed-input error rows — the gate MUST contain
at least one discriminating fixture that asserts THAT exact branch's output. The
enumeration of distinct branches is a FLOOR for fixture coverage, parallel to the
malformed-input enumeration (motion m-w1b above). Branch classes that MUST each
get a fixture when the spec names them:
  - empty-result branch (zero rows / `fields=[]` / `[]` output),
  - None-pointer / null-base branch (a nullable id resolves to None →
    a specified non-error output, NOT a fallthrough dump),
  - no-predecessor / oldest / boundary branch (the first/last element has no
    neighbor → a specified empty/identity output, not an all-added/all-removed dump),
  - identity branch (base == target → empty diff / no-op output),
  - not-found branch (a referenced id absent from the owned scope → the specified
    4xx, distinct from the malformed-input 422 rows of m-w1b).
The chair MUST, when writing the contract, list each enumerated outcome branch and
confirm the gate spec names a fixture for it. A spec branch with ZERO discriminating
fixtures is a RETURNABLE gate defect — the gate passes while that branch is wrong,
and only the adversarial refuter catches it.
(Worked example: r008 w1-t1 enumerated `against=canonical` with
`canonical_version_id is None` → `fields=[]` (contract lines 115-116); the blind
20-fixture gate omitted it, passed 20/20, and the canonical-None all-added-dump
defect was caught only by the refuter — verify-report-w1-t1.md Gate 2 Round 1.)
## Decorator/annotation interaction guard (motion m-w1c, r007)
If a handler is BOTH `@limiter.limit`-decorated AND its module declares
`from __future__ import annotations`, the contract MUST flag the interaction:
slowapi's wrapper drops the module globals FastAPI needs to resolve stringized
(ForwardRef) body-model annotations, raising `PydanticUndefinedAnnotation` at
import. On Python 3.12 the safe remedy is to REMOVE `from __future__ import
annotations` from that module (`list[X]`, `AsyncGenerator[...]` resolve natively
on 3.12); state this as the expected fix so the implementer does not burn an
import cycle diagnosing it.
## Env-keyed dev bypass: hosted-marker fence is MANDATORY (motion m-w1d, r007)
Any contract touching a dev-mode bypass keyed on `environment == "local"` —
email-verification skip, synthetic-email mint, super_admin / org-autojoin,
HSTS-drop, or any privilege-relaxing branch — MUST mandate (not suggest) a
hosted-marker defense-in-depth check: the bypass fires ONLY when
`environment == "local"` AND no hosted-platform marker is present in `os.environ`
(e.g. `_detect_hosted_marker() is None`). REQUIRED, not optional. Conditional
wording ("if you add a defense-in-depth assertion") on a privilege-escalation
fence is a contract defect: it makes fail-closed depend on which executor reads
the clause.
## New middleware on an SSE/streaming app: regression assertion required (motion m-w1e, r007)
If a contract adds a `BaseHTTPMiddleware` (or any response-path middleware), the
chair MUST grep the target file(s) for `StreamingResponse` / SSE / a documented
streaming hazard BEFORE writing the contract. If such a hazard is documented (e.g.
a load-bearing comment that a prior middleware was NOT added because it buffered
an SSE `StreamingResponse`), the interface spec MUST require an EXECUTOR-AUTHORED
streaming-route regression assertion (drive the SSE route WITH the new middleware
registered; assert it still streams incrementally / is not buffered). A
pre-existing full-suite SSE test passing with the middleware merely present is
INCIDENTAL evidence, not proof. A "Set-Cookie is additive" note does NOT discharge
this requirement.
## Long-lived background loop: connection lifetime vs sleep (motion m-w3c, r007)
Any interface spec describing a long-lived background loop — scheduler, periodic
purge, or any `while`/sleep loop touching a pooled resource (DB session, HTTP
client, file handle) — MUST state the resource's lifetime relative to the sleep:
acquire it INSIDE the loop body per iteration and RELEASE it before the `sleep`;
it MUST NOT be held across the sleep (a pooled connection held across an 86400s
interval exhausts the pool). Worked structure:
    while True:
        async with session_factory() as s:   # acquire per iteration
            await do_work(s)
        await asyncio.sleep(interval)         # connection already released
Stating only "open a session, do work, sleep" is a contract defect (it permits
hoisting the `async with` outside the loop).
## Render-tree / JSX-branch promises (testability gate)
A contract MAY gate a render-tree or JSX-branch structural property (e.g. "X
renders in BOTH the collapsed and expanded branch") ONLY IF it also authorizes,
inside the test-engineer's owned scope, a minimal DOM-render fixture capable of
discriminating that property — e.g. a jsdom/@testing-library render of the
component in each branch state, asserting on the rendered tree. Name the fixture
path and the render harness the test-engineer is permitted to add.

If the contract does NOT authorize such a fixture, it MUST NOT state branch-level
or render-tree structure as a gated promise. A grep/string-presence check MAY
NOT be cited as verifying render-branch placement; at most it gates token
PRESENCE, and the contract must label it as such (and note it is non-
discriminating when the token already exists pre-implementation).
**ARIA-role pinning (motion m-w2-aria-role, r008).** If the authorized render
fixture queries elements by ARIA role (`getByRole(...)`, `role=`-based selectors,
or any semantic-role query), the contract MUST state the ARIA role each tested
element exposes (e.g. `role="tab"` vs `role="button"` vs `role="option"`; or, for
a custom element, the explicit `role` attribute it renders). The pinned role is a
seam the implementer and the BLIND test-engineer both build to — without it they
diverge (the implementer renders `role="tab"`, the test-engineer queries
`role="button"`) and every role-based assertion false-fails at integration, burning
a retry rung. State the role next to the fixture authorization, not in prose
elsewhere. A render-tree gate that authorizes a `getByRole` fixture WITHOUT naming
the role is a returnable contract defect.
(Worked example: r008 w2-t2 authorized a `WorkspaceTabBar` render fixture but left
the tab role unpinned; impl chose `role="tab"`, the blind test-engineer queried
`role="button"` → 5 fixtures failed at integration gate 1, consuming rung 1 —
council/state.md run/r008-w2 lines 111-115.)
## Orphan-removal sweep (closes every enumerated removal list)
Whenever a contract enumerates imports, locals, or symbols to remove as
"orphaned after excision," the enumeration is a FLOOR, not a ceiling, and MUST
close with this standing clause:

  "…and any other import or local binding that, after this excision,
  grep-confirms ZERO remaining uses in the owned files. Remove it. Worked
  example, per owned file: `grep -nw <symbol> <file>` returns only the
  declaration line (or nothing) → the symbol is orphaned → remove the
  declaration."

The named symbols are the ones the chair could foresee; the sweep clause makes
the executor responsible for the cascade the chair could not (e.g. a dropped
column that orphans a `date`/`Date` import two files away). Naming a subset
without this clause implicitly reads as exhaustive and is a contract defect.
## Model tier
UNFILLED — the spec format carries no `model:` field. WRAP proposes adding one; until that is ratified the chair supplies the tier by hand. A compiler that guessed here would be ratifying its own proposal.
## Dependencies
- none
