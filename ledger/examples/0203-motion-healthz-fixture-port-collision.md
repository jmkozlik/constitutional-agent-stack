---
type: motion
labels: [motion, governance]
run-id: r101-health-check
status: filed
---
2026-07-02 · MOTION (digest Exec 1, r101-health-check) · gate fixtures that bind a TCP port MUST bind port 0 (ephemeral) and read the assigned port back, OR the contract must reserve a port per task — never a hardcoded port. Evidence: gate_t1-endpoint_liveness failed twice on `EADDRINUSE` against a stale listener from an earlier fixture run; both retries burned a verification rung before the collision was diagnosed; same friction co-signed from the digest. Co-signs: 2 (Execs 2, 3). Artifacts: executors/archive/r101-health-check/digest.md, verify-report-t1-endpoint.md.
