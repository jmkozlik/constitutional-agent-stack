#!/usr/bin/env node
/**
 * gate_t3-beacon-alarm_nominal.js
 *
 * Contract: beacon-alarm.js  (r004-regency / t3-beacon-alarm)
 * Behaviors under test:
 *
 *   NOM-1: Healthy vault (3 runs, all metrics within thresholds) →
 *          stdout contains "BEACON-NOMINAL", exit 0.
 *   NOM-2: Insufficient data (1 run, below the rolling-window minimum) →
 *          NO alarm file written, stdout note acknowledges insufficiency,
 *          exit 0.  "Absence of data is not a regression."
 *   NOM-3: Empty vault (no ledger, no runs at all) → exit 0, no alarm.
 *   NOM-4: Crash / unhandled error → exit code must NOT be 4.
 *          (A bug that throws must not masquerade as a regression alarm.)
 *
 * Thresholds from contract (hardcoded in script, god-space):
 *   first-pass-rate floor  0.6
 *   rework-rate ceiling    2.0
 *   contract-violations    0
 *   promotion-churn        0
 *   governance-heat ceiling 6/run
 */
'use strict';

const fs   = require('fs');
const path = require('path');
const os   = require('os');
const {spawnSync} = require('child_process');

const BEACON_ALARM = path.join(__dirname, 'beacon-alarm.js');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function buildSyntheticVault(base, opts) {
  const ledger  = path.join(base, 'ledger');
  const archive = path.join(base, 'executors', 'archive');
  fs.mkdirSync(ledger,  {recursive: true});
  fs.mkdirSync(archive, {recursive: true});

  let seq = 1;
  function ledgerEntry(name, content) {
    const fname = String(seq).padStart(4, '0') + '-' + name + '.md';
    fs.writeFileSync(path.join(ledger, fname), content);
    seq++;
  }

  const BASE_TS = '2026-01-01T10:00:00Z';
  const END_TS  = '2026-01-01T10:08:00Z';

  for (const run of (opts.runs || [])) {
    ledgerEntry(`${run.runId}-start`,
      `---\ntype: log\nlabels: [run]\nrun-id: ${run.runId}\n---\n${BASE_TS} · ${run.runId} START\n`);
    ledgerEntry(`${run.runId}-complete`,
      `---\ntype: log\nlabels: [run]\nrun-id: ${run.runId}\n---\n${END_TS} · ${run.runId} COMPLETE\n`);

    // All-healthy verify reports
    for (let i = 0; i < (run.taskCount || 1); i++) {
      const dir = path.join(archive, run.runId);
      fs.mkdirSync(dir, {recursive: true});
      fs.writeFileSync(path.join(dir, `verify-report-t${i+1}.md`),
        `# Verify Report\nVerdict: NOT-REFUTED\n`);
    }
  }
}

function runAlarm(vaultPath, outPath) {
  if (!fs.existsSync(BEACON_ALARM)) {
    return {status: -1, stdout: '', stderr: `beacon-alarm.js not found at ${BEACON_ALARM}`};
  }
  const result = spawnSync(process.execPath, [BEACON_ALARM, '--vault', vaultPath, '--out', outPath],
    {encoding: 'utf8', timeout: 15000});
  return result;
}

function alarmFiles(outPath) {
  if (!fs.existsSync(outPath)) return [];
  return fs.readdirSync(outPath).filter(f => f.startsWith('alarm-') && f.endsWith('.md'));
}

// ---------------------------------------------------------------------------
// Test harness
// ---------------------------------------------------------------------------
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
// NOM-1: Healthy vault — 3 runs, all NOT-REFUTED, no motions, no churn
//        → BEACON-NOMINAL on stdout, exit 0
//   Contract: "A vault of 3 healthy runs → BEACON-NOMINAL, exit 0."
// ---------------------------------------------------------------------------
console.log('\n--- NOM-1: healthy vault (3 runs, all green) → BEACON-NOMINAL exit 0 ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-alarm-nom1-'));
  const out   = path.join(tmp, 'out');
  const vault = path.join(tmp, 'vault');
  fs.mkdirSync(out,   {recursive: true});
  fs.mkdirSync(vault, {recursive: true});

  buildSyntheticVault(vault, {
    runs: [
      {runId: 'r001', taskCount: 2},
      {runId: 'r002', taskCount: 2},
      {runId: 'r003', taskCount: 2},
    ]
  });

  const result = runAlarm(vault, out);

  assert(result.status === 0,
    'NOM-1a: exit 0 on all-healthy vault',
    `exit=${result.status} stderr=${result.stderr}`);

  assert(/BEACON-NOMINAL/i.test(result.stdout),
    'NOM-1b: stdout contains "BEACON-NOMINAL"',
    `stdout: ${JSON.stringify(result.stdout)}`);

  assert(alarmFiles(out).length === 0,
    'NOM-1c: no alarm file written on healthy vault',
    `alarm files: ${alarmFiles(out).join(',')}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// NOM-2: Insufficient data — 1 run only (below rolling window minimum of 5)
//        → exit 0, no alarm, stdout note about insufficient data
//   Contract: "A vault with 1 run (insufficient window) →
//              BEACON-NOMINAL (note: insufficient data), exit 0."
// ---------------------------------------------------------------------------
console.log('\n--- NOM-2: insufficient data (1 run) → no alarm, exit 0, note on stdout ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-alarm-nom2-'));
  const out   = path.join(tmp, 'out');
  const vault = path.join(tmp, 'vault');
  fs.mkdirSync(out,   {recursive: true});
  fs.mkdirSync(vault, {recursive: true});

  buildSyntheticVault(vault, {
    runs: [
      {runId: 'rSolo', taskCount: 1},
    ]
  });

  const result = runAlarm(vault, out);

  // Must exit 0 — absence of data is NOT a regression
  assert(result.status === 0,
    'NOM-2a: exit 0 with only 1 run (insufficient window)',
    `exit=${result.status} stderr=${result.stderr}`);

  // Must NOT write an alarm file
  assert(alarmFiles(out).length === 0,
    'NOM-2b: no alarm file written for insufficient-data vault',
    `alarm files: ${alarmFiles(out).join(',')}`);

  // Stdout should mention nominal or insufficient (contract says "BEACON-NOMINAL (note: ...)")
  const stdoutOk = /BEACON-NOMINAL/i.test(result.stdout) ||
                   /insufficient/i.test(result.stdout);
  assert(stdoutOk,
    'NOM-2c: stdout mentions BEACON-NOMINAL or insufficient',
    `stdout: ${JSON.stringify(result.stdout)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// NOM-3: Empty vault — ledger directory missing entirely
//        → exit 0, no alarm
//   Contract: "No data must NOT fire an alarm."
// ---------------------------------------------------------------------------
console.log('\n--- NOM-3: empty vault (no ledger at all) → exit 0, no alarm ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-alarm-nom3-'));
  const out   = path.join(tmp, 'out');
  const vault = path.join(tmp, 'vault');
  // vault directory exists but has nothing inside it
  fs.mkdirSync(out,   {recursive: true});
  fs.mkdirSync(vault, {recursive: true});

  const result = runAlarm(vault, out);

  assert(result.status === 0,
    'NOM-3a: exit 0 on completely empty vault',
    `exit=${result.status} stderr=${result.stderr}`);

  assert(alarmFiles(out).length === 0,
    'NOM-3b: no alarm file written on empty vault',
    `alarm files: ${alarmFiles(out).join(',')}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// NOM-4: Crash / thrown error → exit code must NOT be 4
//        We trigger this by passing a vault path that doesn't exist at all
//        (so the script must handle it gracefully or crash non-4).
//   Contract: "crash → NOT exit 4" — exit 4 is reserved for regression alarms;
//   a crash/unhandled exception must produce a different code (e.g. 1, 2).
// ---------------------------------------------------------------------------
console.log('\n--- NOM-4: crash/error scenario → exit must NOT be 4 ---');
{
  const tmp  = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-alarm-nom4-'));
  const out  = path.join(tmp, 'out');
  fs.mkdirSync(out, {recursive: true});

  // Pass a vault path that definitely doesn't exist
  const nonexistentVault = path.join(tmp, 'no-such-vault-' + Date.now());

  if (!fs.existsSync(BEACON_ALARM)) {
    console.log('  SKIP  NOM-4: beacon-alarm.js not yet present (expected before gate runs)');
  } else {
    const result = spawnSync(process.execPath,
      [BEACON_ALARM, '--vault', nonexistentVault, '--out', out],
      {encoding: 'utf8', timeout: 15000});

    // If it exits with 0, that is fine (graceful empty-vault handling).
    // The ONLY forbidden exit code here is 4 — that would mean a crash
    // was misreported as a regression.
    assert(result.status !== 4,
      'NOM-4: missing/unreadable vault does not produce exit code 4',
      `exit=${result.status} stderr=${result.stderr}`);
  }

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\nNominal fixtures: ${passed} passed, ${failed} failed.`);
process.exit(failed > 0 ? 1 : 0);
