"""The conductor — P1 of lex v2.

Ruled: *"autopilot walks plan levels in parallel, clean gate = proceed,
spawns agents, harvests, verifies, records, advances. Human absent between
spec and law-escalation."*

**Where the ratification went, since it did not go away.** The confirm gate
in `lex.confirm` has no bypass and gains none here — this module does not
call it, because the unit of ratification moved rather than dissolved. A
human authorises a *run*, once, against a specific compiled plan hash. That
hash is what they read and approved; if the spec changes underneath the run,
the thing they authorised no longer exists and the run stops. So the
constitution holds in the form it always had: nothing mechanical happens
that a human did not ratify a hashed description of. What is gone is the
per-step tapping, not the consent.

`authorized_plan_hash` is therefore mandatory, checked before the run and
again before every level. There is no flag that skips it.

**Escalation is typed, not vibes.** Every stop names a class and cites the
standing law that produced it, so the ledger the human wakes up to is a
list of decisions with their grounds attached rather than a traceback.

**Stop-routing is inherited, not re-invented.** A node that stops takes its
dependents with it and nothing else, per the ratified rule that a blocking
signal stops the line it gates.

Run: python -m harness.autopilot --authorize <plan_hash> [--dry-run]
"""

import argparse
import concurrent.futures
import dataclasses
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

from harness import join

# Escalation classes. Each carries the ratified rule it descends from, so a
# stop can be audited against law rather than against my judgement.
ESCALATIONS = {
    "PLAN_DRIFT": "the compiled plan hash no longer matches the authorised "
                  "one — the human ratified a description that has changed",
    "GATE_NOT_CLEAN": "packet-sufficiency gate did not come back clean "
                      "(ruled: clean gate = proceed)",
    "NEW_FINDING": "a finding that is not already queued (ratified gate stop "
                   "rule: anything new stops the line)",
    "FENCE_VIOLATION": "the diff gate found a write outside the fence",
    "REQUEST_MEM": "the agent's packet was insufficient and it asked rather "
                   "than guessed (a miss is a query, not a build)",
    "REPLAY_DIVERGED": "the packet cannot be rebuilt from its commit",
    "RULING_REQUIRED": "the work reached a question only the ratifier answers",
    "BUDGET_EXCEEDED": "the run or dispatch cap was reached (P3)",
    "RUNNER_ERROR": "the agent could not be run to completion",
    "GATE_INERT": "the provider's gate did not stop on the seeded-gutted "
                  "packet, so its verdicts are treated as no-gate (ruled: "
                  "per-provider calibration is mandatory)",
    "GATE_BLOCKING": "the gate reported a BLOCKING-classed item (ruled: "
                     "blocking items stop the line they gate)",
    "TIMEOUT": "the worker exceeded the bounded wall-clock for a dispatch "
               "(ruled: an unattended agent that hangs escalates, never "
               "stalls silently)",
    "PROVISIONING_FAILED": "staging could not prove the verify channel the "
                           "packet promises (ruled: the packet may only "
                           "promise what staging has proven)",
}

# Ruled provisioning law: "Stage executes the verify command in the worktree
# pre-spawn; a USING-style preflight (interpreter + worktree-resolved
# imports) records in the journal."
#
# USING-style is a deliberate callback: staging a check against another tree
# and having it silently import THIS one is a trap this project has already
# fallen into once. The preflight prints the interpreter and the resolved
# module file, and staging asserts the module resolved inside the worktree —
# an unproven promise is the thing the law forbids.
VERIFY_COMMAND = (".venv/bin/python", "-m", "pytest", "-q")

# Ruled: bounded wall-clock per dispatch, escalate on expiry. Unattended is
# the whole point of the conductor, and unattended plus unbounded is a stall
# nobody is watching.
DISPATCH_TIMEOUT_SECONDS = 1800

# F34, promoted: a live-dispatch registry written at stage and cleared at
# teardown. Rung three widens the tree to six concurrent worktrees, which is
# exactly when a cross-tree target no-op stops being theoretical.
REGISTRY = Path(".harness") / "dispatch-registry.json"
PREFLIGHT_PROBE = (
    "import sys, analyzer.gitio as m; "
    "print('USING interpreter', sys.executable); "
    "print('USING analyzer', m.__file__)"
)

# Ruled: "evidence-class commits only (harvests, records, reports, inbound
# handoffs), local, run branch, dispatch-id + record hash in the message,
# generator-authored. PUSH remains outside autopilot."
#
# An allowlist, not a denylist: a path autopilot has never been told it may
# commit is a path it does not commit. The prefixes below are the four
# named classes and nothing else.
EVIDENCE_PREFIXES = (
    "docs/evidence/",        # harvests, records, journals
    "harness/reports/",      # reports
)
GENERATOR = ("harness.autopilot", "autopilot@lex.local")


class AutopilotError(Exception):
    pass


@dataclasses.dataclass
class Event:
    """One line of the run journal. The permanent record is these, in order."""

    seq: int
    kind: str
    node: str = ""
    detail: str = ""
    escalation: str = ""
    data: dict = dataclasses.field(default_factory=dict)

    def as_dict(self) -> dict:
        out = dataclasses.asdict(self)
        if self.escalation:
            out["because"] = ESCALATIONS.get(self.escalation, "")
        return out


class Journal:
    """Append-only JSONL. Nothing rewrites a line; the run is what happened."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = 0
        self.events: list = []

    def write(self, kind, *, node="", detail="", escalation="", **data) -> Event:
        self._seq += 1
        event = Event(self._seq, kind, node, detail, escalation, data)
        self.events.append(event)
        with self.path.open("a") as handle:
            handle.write(json.dumps(event.as_dict(), sort_keys=True) + "\n")
        return event

    def escalations(self) -> list:
        return [e for e in self.events if e.escalation]


def compile_plan_hash(repo, specs) -> str:
    """The current plan hash, from the compiler — never from a cache."""
    plan = join.load_plan(specs)
    return join.serialize_plan(plan, []).plan_hash


def dependents(plan, node_id: str) -> set:
    """Every node that would build on this one, transitively.

    Stop-routing needs the descendants of a stopped node and nothing wider:
    a sibling on the same level shares no edge with it and is unaffected.
    """
    out, frontier = set(), {node_id}
    while frontier:
        current = frontier.pop()
        for other in plan.nodes.values():
            oid = other["id"]
            if oid in out or oid == node_id:
                continue
            if current in (other.get("references") or []):
                out.add(oid)
                frontier.add(oid)
    return out


def default_runner(prompt: str, worktree: Path, *,
                   timeout=DISPATCH_TIMEOUT_SECONDS) -> dict:
    """Spawn a real agent against a prepared worktree.

    Claude Code headless, with the worktree as its working directory — so
    the write fence hook and the read fence that already live in
    `.claude/settings.json` apply to it unchanged. The runner deliberately
    adds no permissions of its own: an agent that could widen its own fence
    would make the fence advisory.
    """
    # `--permission-mode acceptEdits` is deliberate and is the one place
    # autopilot touches a permission. In an interactive session the prompt is
    # the containment; in a fenced worktree it is not, and the real
    # containment is three-layered and already there: out-of-scope files are
    # chmod'd read-only, a PreToolUse hook refuses writes outside the allowed
    # set, and the diff gate checks afterwards independently. Without this the
    # headless agent cannot write at all and every leg is a guaranteed dud.
    # Ruled: "the runner grants the tool permissions the protocol requires."
    # The protocol requires reading the packet, writing inside the fence, and
    # running the verify command — so Bash is granted. Leg one proved the
    # cost of not granting it: the worker could not run a single Python
    # invocation and correctly refused to attest anything.
    result = subprocess.run(
        ["claude", "-p", prompt, "--permission-mode", "acceptEdits",
         "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep"],
        cwd=str(worktree), capture_output=True, text=True, timeout=timeout,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


class Conductor:
    """Walks the plan. Human absent until an escalation names them."""

    def __init__(self, *, repo=".", specs="harness/specs",
                 authorized_plan_hash: str, journal: Journal,
                 runner=None, gate_fn=None, dry_run=False,
                 queued_findings=(), max_parallel=3, calibration_fn=None,
                 run_id=""):
        self.repo = Path(repo)
        self.specs = specs
        self.authorized = authorized_plan_hash
        self.journal = journal
        self.runner = runner or default_runner
        self.gate_fn = gate_fn
        self.dry_run = dry_run
        self.queued = set(queued_findings)
        self.max_parallel = max_parallel
        self.stopped: set = set()
        self.completed: set = set()
        self.gate_inert = False
        # The registry is one file mutated by every worker thread. Without
        # this, two nodes read {}, both write, and one live dispatch vanishes
        # from the record — or a reader catches a truncated write and the
        # registry crashes the dispatch it exists to track, which is the
        # failure this registry has already caused once.
        self._registry_lock = threading.Lock()
        self.calibration_fn = calibration_fn
        self.run_id = run_id

    # --- the constitutional check ------------------------------------------

    def check_authorization(self) -> str:
        current = compile_plan_hash(self.repo, self.specs)
        if current != self.authorized:
            self.journal.write(
                "stop", detail=f"authorised {self.authorized}, compiled {current}",
                escalation="PLAN_DRIFT",
            )
            raise AutopilotError(
                f"plan drift: authorised {self.authorized}, compiled {current}. "
                "The run stops — the human ratified a plan that no longer "
                "exists, and re-authorising is theirs, not mine."
            )
        return current

    # --- one node ----------------------------------------------------------

    def run_node(self, node_id: str) -> str:
        """Gate, dispatch, harvest, verify. Returns a terminal state."""
        if self.dry_run:
            self.journal.write("dry_run", node=node_id,
                               detail="planned; no agent spawned")
            return "planned"

        if self.gate_inert:
            # Ruled: a provider whose gate is inert has its verdicts treated
            # as no-gate. No-gate is not permission — it escalates.
            self.journal.write("stop", node=node_id, escalation="GATE_INERT",
                               detail="verdicts treated as no-gate")
            return "stopped"

        verdicts = self.gate(node_id)
        blocking = self.blocking_items(verdicts)
        # Leg one, D2: only stops were journalled, so a dispatch appeared in
        # the record with nothing showing what authorised it. A gate that
        # passed is evidence too.
        self.journal.write(
            "gate", node=node_id,
            detail=", ".join(f"{p.get('probe')}={p.get('verdict')}"
                             for p in verdicts.get("probes") or []) or "(no probes)",
            blocking=len(blocking),
        )
        if not self._gate_clean(verdicts, blocking):
            self.journal.write(
                "stop", node=node_id,
                escalation="GATE_BLOCKING" if blocking else "GATE_NOT_CLEAN",
                detail=(json.dumps(blocking[:3]) if blocking
                        else json.dumps(verdicts)[:400]),
            )
            return "stopped"

        from harness import dispatch

        context = None
        try:
            context = dispatch.prepare(node_id, role="executor", repo=self.repo,
                                       specs=self.specs)
            started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            self.journal.write("dispatch", node=node_id,
                               detail=str(context["worktree"]),
                               packet_hash=context["packet_hash"])
            self.register(node_id, context)
            staged = self.stage(node_id, context)
            if not staged.get("proven"):
                self.journal.write("stop", node=node_id,
                                   escalation="PROVISIONING_FAILED",
                                   detail=staged.get("why", "")[:400])
                return "stopped"

            try:
                outcome = self.runner(context["prompt"], context["worktree"])
            except subprocess.TimeoutExpired as exc:
                self.journal.write(
                    "stop", node=node_id, escalation="TIMEOUT",
                    detail=f"no result after {exc.timeout}s — the worker is "
                           f"abandoned and the line stops")
                return "stopped"
            # Leg one, D1: this used to sit after harvest, so every stop that
            # happened first — a runner error, a REQUEST_MEM — threw away the
            # worker's own account of how it got there. The transcript is
            # archived the moment the worker returns, on every path.
            self.archive_transcript(node_id, context, outcome)
            # Rung two: the fence flagged `.venv` — my own provisioning
            # artifact — as a write outside the allowed set, and it was right
            # to. Staging cleans up after itself rather than the fence
            # growing an exemption: the worker is finished, the verify
            # channel has served its purpose, and the diff the gate sees is
            # then exactly the agent's work.
            self.unstage(context)
            if outcome.get("returncode") != 0:
                self.journal.write("stop", node=node_id, escalation="RUNNER_ERROR",
                                   detail=str(outcome.get("stderr"))[:400])
                return "stopped"
            if "REQUEST_MEM:" in (outcome.get("stdout") or ""):
                ask = _first_request_mem(outcome["stdout"])
                # Ruled: the worker's own classification is TESTIMONY, not a
                # verdict. It is recorded, it governs the worker's own
                # workaround conduct, and it does not route the conductor —
                # which routes on corroboration-vs-new. Divergence between
                # the two is kept because it is a calibration metric.
                testimony = worker_class(ask)
                self.journal.write(
                    "testimony", node=node_id, detail=ask,
                    worker_says=testimony, conductor_routes="stop",
                    diverged=testimony == "non-blocking",
                )
                self.journal.write("stop", node=node_id, escalation="REQUEST_MEM",
                                   detail=ask)
                return "stopped"

            harvest = dispatch.harvest(context, evidence=self.evidence_dir(node_id),
                                       started=started)
            if harvest.get("gate") != "clean":
                self.journal.write(
                    "stop", node=node_id, escalation="FENCE_VIOLATION",
                    detail=", ".join(harvest.get("violations") or []),
                )
                return "stopped"
            self.journal.write("harvest", node=node_id,
                               detail=f"{len(harvest.get('artifacts') or [])} artifacts")
            return "completed"
        finally:
            if context is not None:
                # Teardown gets its own protection. Deregistering used to run
                # first and unguarded, so a registry error skipped teardown
                # entirely — leaving the fence's read-only chmods in place and
                # the worktree behind, which then breaks the NEXT prepare for
                # that node. Bookkeeping must never outrank releasing the wall.
                try:
                    self.deregister(node_id)     # F34: cleared at teardown
                except Exception as exc:
                    self.journal.write("note", node=node_id,
                                       detail=f"deregister failed: {exc}")
                dispatch.teardown(context)

    def evidence_dir(self, node_id: str) -> Path:
        return (self.repo / "docs" / "evidence" / "autopilot"
                / f"run-{self.run_id or 'adhoc'}" / node_id)

    def archive_transcript(self, node_id: str, context: dict, outcome: dict) -> Path:
        """Ruled, observability: the worker's own account, from leg one onward."""
        evidence = self.evidence_dir(node_id)
        evidence.mkdir(parents=True, exist_ok=True)
        path = evidence / "worker-transcript.txt"
        path.write_text(
            f"$ claude -p <prompt>  (cwd {context['worktree']})\n"
            f"--- exit {outcome.get('returncode')}\n"
            f"--- stdout\n{outcome.get('stdout', '')}\n"
            f"--- stderr\n{outcome.get('stderr', '')}\n"
        )
        self.journal.write("transcript", node=node_id, detail=str(path))
        return path

    def stage(self, node_id: str, context: dict) -> dict:
        """Prove the verify channel before the packet promises it.

        Implementation choice is the operator's, gated by the proof: the
        repo's virtualenv is linked into the worktree so the packet's literal
        `.venv/bin/python -m pytest` is true there rather than rewritten into
        something the packet never said. The preflight then proves the
        interpreter resolves `analyzer` from the WORKTREE and not from the
        repo — an editable install makes that failure silent, which is
        exactly how it bit the time-travel check.
        """
        worktree = Path(context["worktree"])
        # Absolute, deliberately: a relative target resolves against the
        # worktree and makes the link point at itself — proved by staging
        # this against a real worktree before spending a leg on it.
        link, source = worktree / ".venv", (self.repo / ".venv").resolve()
        if source.exists() and not link.exists():
            link.symlink_to(source)

        preflight = subprocess.run(
            [str(link / "bin" / "python"), "-c", PREFLIGHT_PROBE],
            cwd=str(worktree), capture_output=True, text=True,
        )
        using = preflight.stdout.strip()
        resolved_here = str(worktree) in using
        self.journal.write("preflight", node=node_id, detail=using[:300],
                           resolved_in_worktree=resolved_here)
        if preflight.returncode != 0 or not resolved_here:
            return {"proven": False,
                    "why": f"preflight did not resolve inside the worktree: "
                           f"{using or preflight.stderr.strip()[:200]}"}

        verify = subprocess.run(list(VERIFY_COMMAND), cwd=str(worktree),
                                capture_output=True, text=True, timeout=900)
        tail = (verify.stdout or verify.stderr).strip().splitlines()[-1:] or [""]
        self.journal.write("stage_verify", node=node_id,
                           detail=f"{' '.join(VERIFY_COMMAND)} -> exit "
                                  f"{verify.returncode}: {tail[0][:120]}")
        if verify.returncode != 0:
            return {"proven": False,
                    "why": f"the verify command the packet promises exits "
                           f"{verify.returncode} in the worktree: {tail[0][:200]}"}
        return {"proven": True, "verify": tail[0]}

    def registry_path(self) -> Path:
        return self.repo / REGISTRY

    def _read_registry(self, path: Path) -> dict:
        """A registry that cannot be read is empty, never fatal — it must not
        be able to preempt teardown."""
        try:
            return json.loads(path.read_text()) if path.exists() else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_registry(self, path: Path, live: dict) -> None:
        # Write-then-rename: a reader sees the old file or the new one, never
        # a half-written one.
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(live, indent=2, sort_keys=True))
        temp.replace(path)

    def register(self, node_id: str, context: dict) -> dict:
        """Record a live dispatch: which tree it owns and what it may write."""
        path = self.registry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._registry_lock:
            live = self._read_registry(path)
            live[node_id] = {
                "worktree": str(context["worktree"]),
            # Defensively read: prepare's context carries `fence` as a PATH
            # string, not a mapping. The first version assumed a dict and
            # took down both level-0 nodes on rung three — a registry that
            # crashes the dispatch it exists to track.
                "allowed": sorted(_allowed_of(context)),
                "packet_hash": context.get("packet_hash", ""),
            }
            self._write_registry(path, live)
        self.journal.write("register", node=node_id, detail=str(context["worktree"]),
                           live=sorted(live))
        return live

    def deregister(self, node_id: str) -> dict:
        path = self.registry_path()
        with self._registry_lock:
            live = self._read_registry(path)
            live.pop(node_id, None)
            try:
                self._write_registry(path, live)
            except OSError:
                pass          # never let bookkeeping outrank releasing the fence
        return live

    def unstage(self, context: dict) -> None:
        link = Path(context["worktree"]) / ".venv"
        if link.is_symlink():
            link.unlink()

    def gate(self, node_id: str) -> dict:
        if self.gate_fn is not None:
            return self.gate_fn(node_id)
        from harness import gate as gate_mod

        return gate_mod.run(repo=self.repo, specs=self.specs)

    def _gate_clean(self, verdicts: dict, blocking=None) -> bool:
        """Ruled: proceed unless `insufficient` or any BLOCKING-classed item.

        `sufficient_with_gaps` proceeds — it is the historical verdict for
        every packet this loop has shipped — but a gap classed BLOCKING
        stops the line regardless of the headline verdict. The gaps that do
        not block still land in the journal; proceeding is not the same as
        not recording.
        """
        probes = verdicts.get("probes") or []
        if not probes:
            return False          # a gate that answered nothing did not say yes
        if any(p.get("verdict") == "insufficient" for p in probes):
            return False
        # Classification is computed once by the caller and passed in. It used
        # to be recomputed here, which logged every miss to the journal twice
        # — found by the ordered router exercise before a live miss ever
        # routed on it, which is what the exercise was for.
        return not (self.blocking_items(verdicts) if blocking is None
                    else blocking)

    def blocking_items(self, verdicts: dict) -> list:
        """Which reported misses stop the line.

        Classification is deliberately NOT asked of the probe: the probe
        prompt is byte-identical to the archived instrument (F37's
        continuity clause) and adding a severity field to what it must
        produce would change the measurement while keeping its name. So the
        class is decided here, from the ratified stop rule — a miss whose
        substance is an already-queued finding is corroboration, anything
        else is new and blocks.
        """
        blocking = []
        for probe in verdicts.get("probes") or []:
            for miss in probe.get("missing") or []:
                matched = next((f for f in self.queued
                                if f.lower() in miss.lower()), None)
                # Ruled: every miss is logged with the finding it matched, or
                # `new`. The classification is then auditable per item rather
                # than only in aggregate — a wrong class is visible.
                self.journal.write(
                    "classify", node=probe.get("probe", ""),
                    detail=miss[:200], matched=matched or "new",
                    blocking=matched is None,
                )
                if matched is None:
                    blocking.append({"probe": probe.get("probe"), "miss": miss})
        return blocking

    # --- the walk ----------------------------------------------------------

    def calibrate(self) -> dict:
        """Ruled: per-provider calibration is mandatory before the run."""
        if self.calibration_fn is None:
            from harness import gate as gate_mod

            result = gate_mod.calibrate(repo=self.repo, specs=self.specs)
        else:
            result = self.calibration_fn()
        self.gate_inert = bool(result.get("inert"))
        self.journal.write(
            "calibration",
            detail=f"seeded-gutted packet -> {result.get('verdict')}",
            escalation="GATE_INERT" if self.gate_inert else "",
            inert=self.gate_inert, model=result.get("model"),
        )
        return result

    def run(self) -> dict:
        self.check_authorization()
        if not self.dry_run:
            self.calibrate()
        plan = join.load_plan(self.specs)
        levels = join.serialize_plan(plan, []).levels
        self.journal.write("run_start", detail=f"plan {self.authorized}",
                           levels=[list(lv) for lv in levels],
                           dry_run=self.dry_run)

        for depth, node_ids in levels:
            self.check_authorization()   # drift is checked per level, not once
            live = [n for n in node_ids if n not in self.stopped]
            skipped = [n for n in node_ids if n in self.stopped]
            for node_id in skipped:
                self.journal.write("skip", node=node_id,
                                   detail="an ancestor stopped this line")
            if not live:
                continue
            self.journal.write("level", detail=f"level {depth}", nodes=live)

            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(self.max_parallel, len(live))) as pool:
                futures = {pool.submit(self.run_node, n): n for n in live}
                for future in concurrent.futures.as_completed(futures):
                    node_id = futures[future]
                    try:
                        state = future.result()
                    except Exception as exc:            # one node, not the run
                        self.journal.write("stop", node=node_id,
                                           escalation="RUNNER_ERROR",
                                           detail=f"{type(exc).__name__}: {exc}")
                        state = "stopped"
                    if state == "stopped":
                        self._stop_line(node_id, plan)
                    elif state == "completed":
                        self.completed.add(node_id)

        self.journal.write("run_end", detail=f"{len(self.completed)} completed, "
                                             f"{len(self.stopped)} stopped")
        summary = self.summary()
        if not self.dry_run and self.run_id:
            target = promote_journal(self.repo, self.journal, self.run_id)
            rel = str(target.relative_to(self.repo) / "journal.jsonl")
            commit_evidence(self.repo, [rel], dispatch_id=f"run-{self.run_id}",
                            record_hash=self.authorized,
                            branch=run_branch(self.repo, self.run_id))
            try:
                vault_entry(self.run_id, summary)
            except OSError as exc:      # a missing vault is not a lost run
                self.journal.write("note", detail=f"vault entry not filed: {exc}")
        return summary

    def run_single(self, spec: str) -> dict:
        """One node, or a named set of them in parallel. The ladder's rungs.

        Downstream is deliberately not walked: a rung proves the machinery
        on nodes the operator chose, and routing past them is the full walk's
        job.
        """
        node_ids = [n.strip() for n in spec.split(",") if n.strip()]
        self.check_authorization()
        if not self.dry_run:
            self.calibrate()
        self.journal.write("run_start", detail=f"rung: {', '.join(node_ids)}",
                           levels=[["rung", node_ids]], dry_run=self.dry_run)
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(self.max_parallel, len(node_ids))) as pool:
            futures = {pool.submit(self.run_node, n): n for n in node_ids}
            for future in concurrent.futures.as_completed(futures):
                node_id = futures[future]
                try:
                    state = future.result()
                except Exception as exc:
                    self.journal.write("stop", node=node_id,
                                       escalation="RUNNER_ERROR",
                                       detail=f"{type(exc).__name__}: {exc}")
                    state = "stopped"
                (self.stopped if state == "stopped" else self.completed).add(node_id) \
                    if state in ("stopped", "completed") else None
        self.journal.write("run_end", detail=f"{len(self.completed)} completed, "
                                             f"{len(self.stopped)} stopped")
        summary = self.summary()
        if not self.dry_run and self.run_id:
            target = promote_journal(self.repo, self.journal, self.run_id)
            paths = [str(target.relative_to(self.repo) / "journal.jsonl")]
            for node_id in node_ids:
                node_dir = target / node_id
                if node_dir.exists():
                    paths += [str(p.relative_to(self.repo))
                              for p in sorted(node_dir.rglob("*")) if p.is_file()]
            commit_evidence(self.repo, paths, dispatch_id=",".join(node_ids),
                            record_hash=self.authorized, journal=self.journal,
                            branch=run_branch(self.repo, self.run_id))
            try:
                vault_entry(self.run_id, summary)
            except OSError as exc:
                self.journal.write("note", detail=f"vault entry not filed: {exc}")
        return summary

    def _stop_line(self, node_id: str, plan) -> None:
        """Stop-routing: this line, not every line."""
        self.stopped.add(node_id)
        downstream = dependents(plan, node_id)
        self.stopped |= downstream
        if downstream:
            self.journal.write("stop_routing", node=node_id,
                               detail=f"line stopped: {', '.join(sorted(downstream))}")

    def summary(self) -> dict:
        return {
            "plan_hash": self.authorized,
            "completed": sorted(self.completed),
            "stopped": sorted(self.stopped),
            "escalations": [e.as_dict() for e in self.journal.escalations()],
            "journal": str(self.journal.path),
        }


def is_evidence_path(rel_path: str) -> bool:
    """Allowlist. A path autopilot was never told it may commit, it does not."""
    return any(rel_path.startswith(prefix) for prefix in EVIDENCE_PREFIXES)


def _git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=check)


def run_branch(repo, run_id: str) -> str:
    """Ruled: commits land on a run branch, never on whatever was checked out."""
    branch = f"autopilot/run-{run_id}"
    existing = _git(repo, "rev-parse", "--verify", branch, check=False)
    if existing.returncode != 0:
        _git(repo, "branch", branch)
    return branch


def commit_evidence(repo, paths, *, dispatch_id: str, record_hash: str,
                    branch: str, journal=None) -> dict:
    """Commit evidence-class artifacts only, locally, authored by the generator.

    Ruled: "evidence-class commits only (harvests, records, reports, inbound
    handoffs), local, run branch, dispatch-id + record hash in the message,
    generator-authored. PUSH remains outside autopilot."

    There is no push here and no remote is ever named — the ruling draws
    that line and the absence of the capability is how it is kept, rather
    than a flag someone could set.
    """
    repo = Path(repo)
    allowed = [p for p in paths if is_evidence_path(p)]
    refused = [p for p in paths if not is_evidence_path(p)]
    if refused and journal is not None:
        journal.write("commit_refused", node=dispatch_id,
                      detail="not evidence-class: " + ", ".join(sorted(refused)))
    if not allowed:
        return {"committed": False, "reason": "nothing evidence-class to commit",
                "refused": refused}

    _git(repo, "add", "--", *allowed)
    message = (
        f"autopilot evidence — dispatch {dispatch_id}\n\n"
        f"record {record_hash}\n"
        f"Generated by {GENERATOR[0]} on {branch}. Not pushed."
    )
    name, email = GENERATOR
    result = _git(repo, "-c", f"user.name={name}", "-c", f"user.email={email}",
                  "commit", "-m", message, "--", *allowed, check=False)
    if result.returncode != 0:
        return {"committed": False, "reason": result.stderr.strip()[:200],
                "refused": refused}
    sha = _git(repo, "rev-parse", "HEAD").stdout.strip()[:12]
    if journal is not None:
        journal.write("commit", node=dispatch_id, detail=sha,
                      paths=allowed, branch=branch)
    return {"committed": True, "sha": sha, "paths": allowed, "refused": refused}


def promote_journal(repo, journal: "Journal", run_id: str) -> Path:
    """Ruled: .harness/autopilot/ live -> docs/evidence/autopilot/run-NNNN/
    committed at run end.

    The live journal sits under .harness/, which is gitignored by ruling —
    so a run that ended without promotion would leave no permanent record at
    all. This is the step that makes the record permanent.
    """
    target = Path(repo) / "docs" / "evidence" / "autopilot" / f"run-{run_id}"
    target.mkdir(parents=True, exist_ok=True)
    (target / "journal.jsonl").write_text(
        journal.path.read_text() if journal.path.exists() else "")
    return target


VAULT_LEDGER = Path.home() / "vault" / "ledger"


def vault_entry(run_id: str, summary: dict, *, kind="run", ledger=None) -> Path:
    """Ruled: a vault ledger entry per completed run and per resolved escalation.

    Written as a file, never as an edit to an existing one — the ledger is
    append-only for everyone, forever.
    """
    ledger = Path(ledger or VAULT_LEDGER)
    ledger.mkdir(parents=True, exist_ok=True)
    slug = f"autopilot-{kind}-{run_id}"
    path = ledger / f"{slug}.md"
    body = [
        "---", "type: ledger", "labels: [lex, autopilot]", f"run: {run_id}",
        "---", "",
        f"# autopilot {kind} — {run_id}", "",
        f"- plan hash: `{summary.get('plan_hash')}`",
        f"- completed: {', '.join(summary.get('completed') or []) or '(none)'}",
        f"- stopped: {', '.join(summary.get('stopped') or []) or '(none)'}",
        f"- escalations: {len(summary.get('escalations') or [])}", "",
    ]
    for event in summary.get("escalations") or []:
        body.append(f"- **{event['escalation']}** on "
                    f"`{event.get('node') or '(run)'}` — {event.get('because','')}")
    path.write_text("\n".join(body) + "\n")
    return path


def _allowed_of(context: dict) -> list:
    """The write scope, read from the key `dispatch.prepare` actually writes.

    Twice now this has been wrong in the same place. First it assumed
    `fence` was a mapping and crashed rung three; the fix stopped the crash
    but read a key the manifest does not have, so the registry recorded an
    empty allowed set for every live dispatch — a tracker that no longer
    crashes and no longer knows anything. `prepare` puts the scope in
    `fence_allowed` and `fence` is only a path (harness/dispatch.py:175-177).
    """
    allowed = context.get("fence_allowed")
    if isinstance(allowed, dict):
        return list(allowed)
    fence = context.get("fence")
    if isinstance(fence, dict):
        return list(fence.get("allowed") or {})
    return []


def worker_class(ask: str) -> str:
    """What the worker said about its own ask. Testimony, never a verdict."""
    lowered = ask.lower()
    if "(non-blocking)" in lowered or "non-blocking" in lowered:
        return "non-blocking"
    if "(blocking)" in lowered:
        return "blocking"
    return "unclassified"


def _first_request_mem(text: str) -> str:
    for line in text.splitlines():
        if "REQUEST_MEM:" in line:
            return line.strip()[:400]
    return "REQUEST_MEM raised"


def render(summary: dict) -> str:
    lines = [f"autopilot — plan {summary['plan_hash']}", ""]
    lines.append(f"  completed   {', '.join(summary['completed']) or '(none)'}")
    lines.append(f"  stopped     {', '.join(summary['stopped']) or '(none)'}")
    if summary["escalations"]:
        lines.append("")
        lines.append("  escalations — the human's queue:")
        for event in summary["escalations"]:
            node = event.get("node") or "(run)"
            lines.append(f"    [{event['escalation']}] {node}")
            lines.append(f"        {event.get('because', '')}")
            if event.get("detail"):
                lines.append(f"        {event['detail'][:150]}")
    lines.append("")
    lines.append(f"  journal     {summary['journal']}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness.autopilot",
        description="Walk the plan without a human between spec and escalation.",
    )
    parser.add_argument("--authorize", required=True,
                        help="the plan hash the human ratified; drift stops the run")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--specs", default="harness/specs")
    parser.add_argument("--dry-run", action="store_true",
                        help="walk the levels and record intent; spawn nothing")
    parser.add_argument("--max-parallel", type=int, default=3)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--node", default=None,
                        help="run one node only — the live ladder's first rungs")
    args = parser.parse_args(argv)

    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    journal = Journal(Path(args.repo) / ".harness" / "autopilot" / f"{run_id}.jsonl")
    conductor = Conductor(
        repo=args.repo, specs=args.specs, authorized_plan_hash=args.authorize,
        journal=journal, dry_run=args.dry_run, max_parallel=args.max_parallel,
        run_id=run_id,
    )
    try:
        summary = (conductor.run_single(args.node) if args.node
                   else conductor.run())
    except AutopilotError as exc:
        print(f"autopilot: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(render(summary))
    return 1 if summary["escalations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
