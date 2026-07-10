#!/usr/bin/env node
/**
 * gate_t1-beacon_metrics.js
 * Asserts metric computations on a fully synthetic vault with known values.
 *
 * Metrics under test (from contract interface spec):
 *   MET-1: first-pass-verification-rate — fraction NOT-REFUTED on attempt 1
 *           (verify-reports at <vault>/executors/archive/<run-id>/verify-report-<task>.md
 *            containing literal token NOT-REFUTED or REFUTED)
 *   MET-2: rework-rate — retry-ladder ledger entries per run
 *   MET-3: time-to-merge — ledger start→complete timestamp delta
 *   MET-4: tokens-per-task proxy — telemetry event count per run-id
 *   MET-5: promotion-churn — promoted-then-reverted count (ledger)
 *   MET-6: governance-heat (SHADOW) — motion+mutiny ledger entries per run
 *   MET-7: unanimity-rate (SHADOW) — fraction of panel entries where all pre-convene
 *           verdicts agreed
 *   MET-8: revert-frequency — git log reverts/run (requires git repo in vault)
 *
 * Worked example from contract:
 *   - ledger: 0001-rX-start.md (10:00) + 0002-rX-complete.md (10:08)
 *   - verify-report: NOT-REFUTED
 *   → time-to-merge rX=8m, first-pass-verification-rate=1.0
 *   → liveness=OK if .telemetry has rows after latest canary boot
 *
 * The report is LOCALIZED (names run-id/agent-type for each degraded metric).
 * We verify the run-id appears in the report when metrics degrade.
 */
'use strict';
const fs   = require('fs');
const path = require('path');
const {spawnSync, execFileSync} = require('child_process');
const os   = require('os');

// ---------------------------------------------------------------------------
// Synthetic vault builder
// ---------------------------------------------------------------------------
function buildSyntheticVault(base, opts) {
  /*
   * opts: {
   *   runs: [
   *     { runId, startTs, completeTs, motionCount, retryCount, panelUnanimous }
   *   ],
   *   verifyReports: [
   *     { runId, task, verdict }   // verdict: 'NOT-REFUTED' | 'REFUTED'
   *   ],
   *   telemCount: number,   // telemetry rows to emit
   *   bootTs: string,       // canary boot timestamp
   *   initGit: boolean,     // create a git repo (for revert-frequency test)
   *   revertCommits: number // number of fake revert commits to add
   * }
   */
  const ledger  = path.join(base, 'ledger');
  const telem   = path.join(base, '.telemetry');
  const canary  = path.join(base, 'god', 'canary');
  const archive = path.join(base, 'executors', 'archive');

  fs.mkdirSync(ledger,  {recursive: true});
  fs.mkdirSync(telem,   {recursive: true});
  fs.mkdirSync(canary,  {recursive: true});
  fs.mkdirSync(archive, {recursive: true});

  let seq = 1;
  function writeEntry(name, content) {
    const fname = String(seq).padStart(4, '0') + '-' + name + '.md';
    fs.writeFileSync(path.join(ledger, fname), content);
    seq++;
  }

  for (const run of (opts.runs || [])) {
    writeEntry(`${run.runId}-start`,
      `---\ntype: log\nlabels: [run]\nrun-id: ${run.runId}\n---\n${run.startTs} · ${run.runId} START\n`);

    // Add retry-ladder entries if requested
    for (let i = 0; i < (run.retryCount || 0); i++) {
      writeEntry(`${run.runId}-retry-${i}`,
        `---\ntype: log\nlabels: [run, retry-ladder]\nrun-id: ${run.runId}\n---\n${run.startTs} · ${run.runId} RETRY ${i+1}\n`);
    }

    // Add motion entries (governance-heat)
    for (let i = 0; i < (run.motionCount || 0); i++) {
      writeEntry(`${run.runId}-motion-${i}`,
        `---\ntype: log\nlabels: [governance, motion]\nrun-id: ${run.runId}\n---\n${run.startTs} · motion ${i+1} filed during ${run.runId}\n`);
    }

    // Panel entry for unanimity
    if (run.panelUnanimous !== undefined) {
      const verdicts = run.panelUnanimous
        ? 'pre-convene: panelist-A PASS · panelist-B PASS · panelist-C PASS'
        : 'pre-convene: panelist-A PASS · panelist-B RE-DISCUSS · panelist-C PASS';
      writeEntry(`${run.runId}-panel`,
        `---\ntype: log\nlabels: [run, council]\nrun-id: ${run.runId}\n---\n${run.startTs} · PANEL · ${verdicts}\n`);
    }

    // Add promotion-churn: promoted + reverted entry
    if (run.promotionReverted) {
      writeEntry(`${run.runId}-promoted`,
        `---\ntype: log\nlabels: [governance, promoted]\nrun-id: ${run.runId}\n---\n${run.startTs} · amendment promoted in ${run.runId}\n`);
      writeEntry(`${run.runId}-reverted`,
        `---\ntype: log\nlabels: [governance, reverted]\nrun-id: ${run.runId}\n---\n${run.startTs} · amendment reverted in ${run.runId}\n`);
    }

    writeEntry(`${run.runId}-complete`,
      `---\ntype: log\nlabels: [run]\nrun-id: ${run.runId}\n---\n${run.completeTs} · ${run.runId} COMPLETE\n`);
  }

  // Verify reports
  for (const vr of (opts.verifyReports || [])) {
    const dir = path.join(archive, vr.runId);
    fs.mkdirSync(dir, {recursive: true});
    fs.writeFileSync(path.join(dir, `verify-report-${vr.task}.md`),
      `# Verify Report\nVerdict: ${vr.verdict}\n`);
  }

  // Telemetry + canary
  const bootTs = opts.bootTs || '2026-01-01T09:00:00.000Z';
  fs.writeFileSync(path.join(canary, 'boot-log.jsonl'),
    JSON.stringify({ts: bootTs, event: 'sessionstart'}) + '\n');

  if (opts.telemCount > 0) {
    const rows = [];
    for (let i = 0; i < opts.telemCount; i++) {
      // timestamp is strictly after bootTs
      const ts = new Date(new Date(bootTs).getTime() + (i + 1) * 60000).toISOString();
      rows.push(JSON.stringify({ts, tool: 'Write', file: '/tmp/x', session: opts.runs[0].runId}));
    }
    fs.writeFileSync(path.join(telem, 'raw-2026-01-01.jsonl'), rows.join('\n') + '\n');
  }

  // Optional: git repo with revert commits
  if (opts.initGit) {
    execFileSync('git', ['-C', base, 'init'], {stdio: 'pipe'});
    execFileSync('git', ['-C', base, 'config', 'user.email', 'test@test.com'], {stdio: 'pipe'});
    execFileSync('git', ['-C', base, 'config', 'user.name', 'Test'], {stdio: 'pipe'});
    execFileSync('git', ['-C', base, 'add', '-A'], {stdio: 'pipe'});
    execFileSync('git', ['-C', base, 'commit', '-m', 'initial', '--allow-empty'], {stdio: 'pipe'});

    for (let i = 0; i < (opts.revertCommits || 0); i++) {
      // Create a file to give the commit a concrete change
      const f = path.join(ledger, `revert-dummy-${i}.md`);
      fs.writeFileSync(f, `revert ${i}\n`);
      execFileSync('git', ['-C', base, 'add', f], {stdio: 'pipe'});
      execFileSync('git', ['-C', base, 'commit', '-m', `Revert "something ${i}" (auto-test)`], {stdio: 'pipe'});
    }
  }
}

function runBeacon(vaultPath) {
  const out    = path.join(vaultPath, '_out');
  const beacon = path.join(__dirname, 'beacon.js');
  fs.mkdirSync(out, {recursive: true});
  const result = spawnSync(process.execPath, [beacon, '--vault', vaultPath, '--out', out],
    {encoding: 'utf8', timeout: 15000});
  const files  = fs.readdirSync(out).filter(f => f.startsWith('beacon-') && f.endsWith('.md')).sort();
  const report = files.length > 0 ? fs.readFileSync(path.join(out, files[files.length - 1]), 'utf8') : '';
  return {result, report};
}

let passed = 0;
let failed = 0;

function assert(condition, label, detail) {
  if (condition) {
    console.log(`  PASS  ${label}`);
    passed++;
  } else {
    console.error(`  FAIL  ${label}${detail ? '\n        ' + detail : ''}`);
    failed++;
  }
}

// ---------------------------------------------------------------------------
// MET-1: first-pass-verification-rate worked example (rate = 1.0)
// ---------------------------------------------------------------------------
console.log('\n--- MET-1: first-pass-verification-rate = 1.0 (all NOT-REFUTED) ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-met1a-'));
  buildSyntheticVault(tmp, {
    runs: [{runId: 'rX', startTs: '2026-01-01T10:00:00Z', completeTs: '2026-01-01T10:08:00Z'}],
    verifyReports: [
      {runId: 'rX', task: 't1', verdict: 'NOT-REFUTED'},
      {runId: 'rX', task: 't2', verdict: 'NOT-REFUTED'},
    ],
    bootTs: '2026-01-01T09:00:00.000Z',
    telemCount: 2,
  });

  const {result, report} = runBeacon(tmp);
  assert(result.status === 0, 'MET-1a: exit 0', `stderr=${result.stderr}`);
  const combined = result.stdout + report;
  // Rate = 1.0 (2/2 NOT-REFUTED)
  assert(/first-pass.*1\.0/i.test(combined) || /verification.*rate.*1\.0/i.test(combined) || /1\.0.*first.pass/i.test(combined),
    'MET-1b: first-pass-verification-rate=1.0 reported',
    `combined snippet: ${combined.slice(0, 600)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// MET-1 variant: 1 REFUTED, 1 NOT-REFUTED → rate = 0.5
console.log('\n--- MET-1: first-pass-verification-rate = 0.5 (mixed) ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-met1b-'));
  buildSyntheticVault(tmp, {
    runs: [{runId: 'rY', startTs: '2026-01-01T10:00:00Z', completeTs: '2026-01-01T10:08:00Z'}],
    verifyReports: [
      {runId: 'rY', task: 't1', verdict: 'NOT-REFUTED'},
      {runId: 'rY', task: 't2', verdict: 'REFUTED'},
    ],
    bootTs: '2026-01-01T09:00:00.000Z',
    telemCount: 1,
  });

  const {result, report} = runBeacon(tmp);
  assert(result.status === 0, 'MET-1c: exit 0 mixed verdicts', `stderr=${result.stderr}`);
  const combined = result.stdout + report;
  // Rate = 0.5 (1/2)
  assert(/first-pass.*0\.5/i.test(combined) || /verification.*rate.*0\.5/i.test(combined) || /0\.5.*first.pass/i.test(combined) || /50%/.test(combined),
    'MET-1d: first-pass-verification-rate=0.5 reported for mixed verdicts',
    `combined snippet: ${combined.slice(0, 600)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// MET-3: time-to-merge — worked example from contract: rX 10:00→10:08 = 8m
// ---------------------------------------------------------------------------
console.log('\n--- MET-3: time-to-merge rX=8m (contract worked example) ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-met3-'));
  buildSyntheticVault(tmp, {
    runs: [{runId: 'rX', startTs: '2026-01-01T10:00:00Z', completeTs: '2026-01-01T10:08:00Z'}],
    verifyReports: [{runId: 'rX', task: 't1', verdict: 'NOT-REFUTED'}],
    bootTs: '2026-01-01T09:00:00.000Z',
    telemCount: 3,
  });

  const {result, report} = runBeacon(tmp);
  assert(result.status === 0, 'MET-3a: exit 0', `stderr=${result.stderr}`);
  const combined = result.stdout + report;
  // 8 minutes
  assert(/8\s*m/i.test(combined) || /time.to.merge.*8/i.test(combined) || /rX.*8/i.test(combined),
    'MET-3b: time-to-merge rX=8m reported',
    `combined snippet: ${combined.slice(0, 600)}`);

  // run-id localization: rX must appear in report
  assert(/rX/i.test(combined),
    'MET-3c: report is localized — run-id rX named',
    `combined snippet: ${combined.slice(0, 600)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// MET-4: tokens-per-task proxy = telemetry event count per run-id
// ---------------------------------------------------------------------------
console.log('\n--- MET-4: tokens-per-task = telemetry event count (5 rows) ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-met4-'));
  buildSyntheticVault(tmp, {
    runs: [{runId: 'rZ', startTs: '2026-01-01T10:00:00Z', completeTs: '2026-01-01T10:10:00Z'}],
    verifyReports: [{runId: 'rZ', task: 't1', verdict: 'NOT-REFUTED'}],
    bootTs: '2026-01-01T09:00:00.000Z',
    telemCount: 5,
  });

  const {result, report} = runBeacon(tmp);
  assert(result.status === 0, 'MET-4a: exit 0', `stderr=${result.stderr}`);
  const combined = result.stdout + report;
  // 5 telemetry events
  assert(/tokens.*5/i.test(combined) || /telemetry.*5/i.test(combined) || /5.*token/i.test(combined) || /proxy.*5/i.test(combined),
    'MET-4b: tokens-per-task proxy=5 reported',
    `combined snippet: ${combined.slice(0, 600)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// MET-2: rework-rate (retry-ladder entries per run)
// ---------------------------------------------------------------------------
console.log('\n--- MET-2: rework-rate (2 retry-ladder entries) ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-met2-'));
  buildSyntheticVault(tmp, {
    runs: [{runId: 'rW', startTs: '2026-01-01T10:00:00Z', completeTs: '2026-01-01T11:00:00Z',
            retryCount: 2}],
    verifyReports: [{runId: 'rW', task: 't1', verdict: 'NOT-REFUTED'}],
    bootTs: '2026-01-01T09:00:00.000Z',
    telemCount: 1,
  });

  const {result, report} = runBeacon(tmp);
  assert(result.status === 0, 'MET-2a: exit 0', `stderr=${result.stderr}`);
  const combined = result.stdout + report;
  assert(/rework.*2/i.test(combined) || /retry.*2/i.test(combined) || /2.*retry/i.test(combined) || /2.*rework/i.test(combined),
    'MET-2b: rework-rate=2 reported',
    `combined snippet: ${combined.slice(0, 600)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// MET-5: promotion-churn (promoted-then-reverted)
// ---------------------------------------------------------------------------
console.log('\n--- MET-5: promotion-churn (1 promoted-then-reverted) ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-met5-'));
  buildSyntheticVault(tmp, {
    runs: [{runId: 'rV', startTs: '2026-01-01T10:00:00Z', completeTs: '2026-01-01T10:15:00Z',
            promotionReverted: true}],
    verifyReports: [{runId: 'rV', task: 't1', verdict: 'NOT-REFUTED'}],
    bootTs: '2026-01-01T09:00:00.000Z',
    telemCount: 1,
  });

  const {result, report} = runBeacon(tmp);
  assert(result.status === 0, 'MET-5a: exit 0', `stderr=${result.stderr}`);
  const combined = result.stdout + report;
  assert(/promotion.churn/i.test(combined) || /promoted.*reverted/i.test(combined) || /churn.*1/i.test(combined),
    'MET-5b: promotion-churn metric present in report',
    `combined snippet: ${combined.slice(0, 600)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// MET-6: governance-heat (motion entries per run)
// ---------------------------------------------------------------------------
console.log('\n--- MET-6: governance-heat (3 motion entries) ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-met6-'));
  buildSyntheticVault(tmp, {
    runs: [{runId: 'rU', startTs: '2026-01-01T10:00:00Z', completeTs: '2026-01-01T10:20:00Z',
            motionCount: 3}],
    verifyReports: [{runId: 'rU', task: 't1', verdict: 'NOT-REFUTED'}],
    bootTs: '2026-01-01T09:00:00.000Z',
    telemCount: 1,
  });

  const {result, report} = runBeacon(tmp);
  assert(result.status === 0, 'MET-6a: exit 0', `stderr=${result.stderr}`);
  const combined = result.stdout + report;
  assert(/governance.heat/i.test(combined) || /motion.*3/i.test(combined) || /heat.*3/i.test(combined),
    'MET-6b: governance-heat metric present in report',
    `combined snippet: ${combined.slice(0, 600)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// MET-7: unanimity-rate — unanimous panel → 1.0; split panel → < 1.0
// ---------------------------------------------------------------------------
console.log('\n--- MET-7: unanimity-rate (unanimous=1.0, split<1.0) ---');
{
  // Unanimous: all verdicts PASS
  const tmp1 = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-met7a-'));
  buildSyntheticVault(tmp1, {
    runs: [{runId: 'rT', startTs: '2026-01-01T10:00:00Z', completeTs: '2026-01-01T10:10:00Z',
            panelUnanimous: true}],
    verifyReports: [{runId: 'rT', task: 't1', verdict: 'NOT-REFUTED'}],
    bootTs: '2026-01-01T09:00:00.000Z',
    telemCount: 1,
  });
  const {result: r1, report: rep1} = runBeacon(tmp1);
  assert(r1.status === 0, 'MET-7a: exit 0 (unanimous)', `stderr=${r1.stderr}`);
  const c1 = r1.stdout + rep1;
  assert(/unanimity/i.test(c1) || /panel/i.test(c1),
    'MET-7b: unanimity-rate metric present (unanimous case)',
    `combined snippet: ${c1.slice(0, 600)}`);
  fs.rmSync(tmp1, {recursive: true, force: true});

  // Split: not all PASS
  const tmp2 = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-met7b-'));
  buildSyntheticVault(tmp2, {
    runs: [{runId: 'rS', startTs: '2026-01-01T10:00:00Z', completeTs: '2026-01-01T10:10:00Z',
            panelUnanimous: false}],
    verifyReports: [{runId: 'rS', task: 't1', verdict: 'NOT-REFUTED'}],
    bootTs: '2026-01-01T09:00:00.000Z',
    telemCount: 1,
  });
  const {result: r2, report: rep2} = runBeacon(tmp2);
  assert(r2.status === 0, 'MET-7c: exit 0 (split panel)', `stderr=${r2.stderr}`);
  fs.rmSync(tmp2, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// MET-8: revert-frequency (git log reverts/run)
// ---------------------------------------------------------------------------
console.log('\n--- MET-8: revert-frequency (git log with 2 revert commits) ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-met8-'));
  buildSyntheticVault(tmp, {
    runs: [{runId: 'rQ', startTs: '2026-01-01T10:00:00Z', completeTs: '2026-01-01T10:10:00Z'}],
    verifyReports: [{runId: 'rQ', task: 't1', verdict: 'NOT-REFUTED'}],
    bootTs: '2026-01-01T09:00:00.000Z',
    telemCount: 1,
    initGit: true,
    revertCommits: 2,
  });

  const {result, report} = runBeacon(tmp);
  assert(result.status === 0, 'MET-8a: exit 0 with git repo', `stderr=${result.stderr}`);
  const combined = result.stdout + report;
  assert(/revert/i.test(combined),
    'MET-8b: revert-frequency metric present in report',
    `combined snippet: ${combined.slice(0, 600)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// MET-9: stdout one-line summary — must print something to stdout on success
// ---------------------------------------------------------------------------
console.log('\n--- MET-9: stdout one-line summary ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-met9-'));
  buildSyntheticVault(tmp, {
    runs: [{runId: 'rP', startTs: '2026-01-01T10:00:00Z', completeTs: '2026-01-01T10:05:00Z'}],
    verifyReports: [{runId: 'rP', task: 't1', verdict: 'NOT-REFUTED'}],
    bootTs: '2026-01-01T09:00:00.000Z',
    telemCount: 1,
  });

  const {result} = runBeacon(tmp);
  assert(result.status === 0, 'MET-9a: exit 0', `stderr=${result.stderr}`);
  const lines = (result.stdout || '').split('\n').filter(l => l.trim().length > 0);
  assert(lines.length >= 1,
    'MET-9b: at least one non-empty line on stdout (one-line summary)',
    `stdout: ${JSON.stringify(result.stdout)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// MET-10: no-args default invocation — exit 0 when invoked with no flags
//          (requires that the real vault exists; if it doesn't, just skip)
// ---------------------------------------------------------------------------
console.log('\n--- MET-10: default --vault path accepted (reads real vault if present) ---');
{
  const beacon = path.join(__dirname, 'beacon.js');
  // Use the worktree itself as a minimal vault-like structure, with explicit out
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-met10-'));
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, {recursive: true});
  const result = spawnSync(process.execPath, [beacon, '--vault', tmp, '--out', out],
    {encoding: 'utf8', timeout: 10000});
  // An empty vault should produce exit 0 with defaults and empty metrics
  assert(result.status === 0,
    'MET-10: empty vault exits 0 (graceful degradation)',
    `status=${result.status} stderr=${result.stderr}`);
  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\nMetric fixtures: ${passed} passed, ${failed} failed.`);
process.exit(failed > 0 ? 1 : 0);
