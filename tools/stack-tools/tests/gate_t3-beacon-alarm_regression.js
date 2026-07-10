#!/usr/bin/env node
/**
 * gate_t3-beacon-alarm_regression.js
 *
 * Contract: beacon-alarm.js  (r004-regency / t3-beacon-alarm)
 * Behaviors under test:
 *
 *   REG-1: Synthetic vault where first-pass-rate = 0.4 (4 REFUTED out of 10
 *          across 5 runs, below floor 0.60) → exit EXACTLY 4.
 *   REG-2: Alarm file is written under <out>/ named alarm-<UTCstamp>.md.
 *   REG-3: Alarm file is LOCALIZED: names the metric, the threshold crossed,
 *          and the specific run-id that drove the regression.
 *          Contract worked example: "first-pass-verification-rate=0.40 < 0.60,
 *          driver: rX"
 *   REG-4: Alarm naming — metric name must appear in the alarm file content,
 *          threshold value 0.6 must appear, driver run-id must appear.
 *
 * Invocation tested: node beacon-alarm.js --vault <PATH> --out <PATH>
 *
 * Exit codes asserted:
 *   - exit 4   on regression (REG-1)
 *   - not 4    implied by nominal tests (see gate_t3-beacon-alarm_nominal.js)
 */
'use strict';

const fs   = require('fs');
const path = require('path');
const os   = require('os');
const {spawnSync} = require('child_process');

// ---------------------------------------------------------------------------
// Locate beacon-alarm.js — same directory as this fixture (the implementer's
// worktree will drop it here; the verify harness passes __dirname-relative).
// ---------------------------------------------------------------------------
const BEACON_ALARM = path.join(__dirname, 'beacon-alarm.js');

// ---------------------------------------------------------------------------
// Synthetic vault builder
// Builds the minimal ledger + verify-reports that beacon-alarm.js reads.
//
// Ledger format derived from contract + existing beacon fixture convention:
//   <seq>-<runId>-start.md   frontmatter: type:log labels:[run] run-id:<id>
//   <seq>-<runId>-complete.md
//   verify-report lives at executors/archive/<runId>/verify-report-<task>.md
//   Verdict line contains literal token NOT-REFUTED or REFUTED
//
// opts: {
//   runs: [ { runId, verifyVerdicts: ['NOT-REFUTED'|'REFUTED', ...] } ],
//   // optional extras per run
//   motionCount: number,   // governance-heat entries per run
//   retryCount:  number,   // retry-ladder entries per run
//   promotionReverted: bool
// }
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

    // retry-ladder
    for (let i = 0; i < (run.retryCount || 0); i++) {
      ledgerEntry(`${run.runId}-retry-${i}`,
        `---\ntype: log\nlabels: [run, retry-ladder]\nrun-id: ${run.runId}\n---\n${BASE_TS} · ${run.runId} RETRY ${i+1}\n`);
    }

    // governance motions
    for (let i = 0; i < (run.motionCount || 0); i++) {
      ledgerEntry(`${run.runId}-motion-${i}`,
        `---\ntype: log\nlabels: [governance, motion]\nrun-id: ${run.runId}\n---\n${BASE_TS} · motion ${i+1} during ${run.runId}\n`);
    }

    // promotion-churn
    if (run.promotionReverted) {
      ledgerEntry(`${run.runId}-promoted`,
        `---\ntype: log\nlabels: [governance, promoted]\nrun-id: ${run.runId}\n---\n${BASE_TS} · promoted in ${run.runId}\n`);
      ledgerEntry(`${run.runId}-reverted`,
        `---\ntype: log\nlabels: [governance, reverted]\nrun-id: ${run.runId}\n---\n${BASE_TS} · reverted in ${run.runId}\n`);
    }

    // contract-violations
    if (run.contractViolation) {
      ledgerEntry(`${run.runId}-violation`,
        `---\ntype: log\nlabels: [governance, contract-violation]\nrun-id: ${run.runId}\n---\n${BASE_TS} · contract violation in ${run.runId}\n`);
    }

    ledgerEntry(`${run.runId}-complete`,
      `---\ntype: log\nlabels: [run]\nrun-id: ${run.runId}\n---\n${END_TS} · ${run.runId} COMPLETE\n`);

    // verify reports
    for (let i = 0; i < (run.verifyVerdicts || []).length; i++) {
      const dir = path.join(archive, run.runId);
      fs.mkdirSync(dir, {recursive: true});
      const verdict = run.verifyVerdicts[i];
      fs.writeFileSync(path.join(dir, `verify-report-t${i+1}.md`),
        `# Verify Report\nVerdict: ${verdict}\n`);
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

function latestAlarmFile(outPath) {
  if (!fs.existsSync(outPath)) return null;
  const files = fs.readdirSync(outPath)
    .filter(f => f.startsWith('alarm-') && f.endsWith('.md'))
    .sort();
  if (files.length === 0) return null;
  return {name: files[files.length - 1], content: fs.readFileSync(path.join(outPath, files[files.length-1]), 'utf8')};
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
// REG-1 / REG-2 / REG-3 / REG-4:
// 5 runs where first-pass-rate = 0.4 (2 out of 5 pass, 3 REFUTED)
// Each run has 2 verify verdicts; 3 runs REFUTED on first task → rate 0.4
// driver = the run-id(s) that contributed REFUTED verdicts
//
// Contract worked example: vault whose last 5 runs show first-pass-rate 0.4
// (below floor 0.6), driven by run rX → exit 4, alarm names metric+threshold+driver.
// ---------------------------------------------------------------------------
console.log('\n--- REG-1/2/3/4: first-pass-rate 0.4 < floor 0.6 → exit 4, localized alarm ---');
{
  const tmp  = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-alarm-reg1-'));
  const out  = path.join(tmp, 'out');
  const vault = path.join(tmp, 'vault');
  fs.mkdirSync(out,   {recursive: true});
  fs.mkdirSync(vault, {recursive: true});

  // 5 runs; 2 NOT-REFUTED, 3 REFUTED → first-pass-rate = 2/5 = 0.4
  // contract example names rX as driver; we use rA as the key failing run
  buildSyntheticVault(vault, {
    runs: [
      {runId: 'rA', verifyVerdicts: ['REFUTED',     'NOT-REFUTED']},
      {runId: 'rB', verifyVerdicts: ['REFUTED',     'NOT-REFUTED']},
      {runId: 'rC', verifyVerdicts: ['REFUTED',     'NOT-REFUTED']},
      {runId: 'rD', verifyVerdicts: ['NOT-REFUTED', 'NOT-REFUTED']},
      {runId: 'rE', verifyVerdicts: ['NOT-REFUTED', 'NOT-REFUTED']},
    ]
  });

  const result = runAlarm(vault, out);

  // REG-1: exit exactly 4
  assert(result.status === 4,
    'REG-1: exit code is exactly 4 on first-pass-rate regression',
    `exit=${result.status} stderr=${result.stderr}`);

  // REG-2: alarm file written
  const alarm = latestAlarmFile(out);
  assert(alarm !== null,
    'REG-2: alarm file written under <out>/',
    `files in out: ${fs.existsSync(out) ? fs.readdirSync(out).join(',') : 'dir missing'}`);

  if (alarm) {
    // REG-3: alarm file name matches alarm-<UTCstamp>.md pattern
    assert(/^alarm-\d{4}-\d{2}-\d{2}T[\d:.]+Z\.md$/.test(alarm.name) ||
           /^alarm-[\dT:.Z-]+\.md$/.test(alarm.name),
      'REG-3: alarm file name is alarm-<UTCstamp>.md',
      `got: ${alarm.name}`);

    // REG-4a: metric name appears in alarm content
    assert(/first.pass/i.test(alarm.content),
      'REG-4a: alarm content names metric "first-pass-verification-rate"',
      `content snippet: ${alarm.content.slice(0, 400)}`);

    // REG-4b: threshold value 0.6 (floor) appears
    assert(/0\.6/i.test(alarm.content),
      'REG-4b: alarm content names threshold 0.6',
      `content snippet: ${alarm.content.slice(0, 400)}`);

    // REG-4c: driver run-id appears (at least one of rA/rB/rC which contributed REFUTED)
    const driverPresent = /rA|rB|rC/i.test(alarm.content);
    assert(driverPresent,
      'REG-4c: alarm content names driver run-id',
      `content snippet: ${alarm.content.slice(0, 400)}`);

    // REG-4d: actual observed rate (0.4 or 40%) mentioned
    assert(/0\.4[0-9]*|40%/i.test(alarm.content),
      'REG-4d: alarm content states observed rate (0.4x or 40%)',
      `content snippet: ${alarm.content.slice(0, 400)}`);
  }

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// REG-5: Exactly at floor (rate = 0.6) — boundary, must NOT trigger alarm
// This is a boundary check from the same fixture to avoid separate file bloat.
// Contract says "DROPS below threshold" — 0.6 exact is NOT below, is healthy.
// ---------------------------------------------------------------------------
console.log('\n--- REG-5: boundary rate=0.6 exactly → NOT an alarm (healthy) ---');
{
  const tmp  = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-alarm-reg5-'));
  const out  = path.join(tmp, 'out');
  const vault = path.join(tmp, 'vault');
  fs.mkdirSync(out,   {recursive: true});
  fs.mkdirSync(vault, {recursive: true});

  // 5 runs × 1 verdict each: 3 NOT-REFUTED, 2 REFUTED → rate = 3/5 = 0.6
  buildSyntheticVault(vault, {
    runs: [
      {runId: 'rA', verifyVerdicts: ['NOT-REFUTED']},
      {runId: 'rB', verifyVerdicts: ['NOT-REFUTED']},
      {runId: 'rC', verifyVerdicts: ['NOT-REFUTED']},
      {runId: 'rD', verifyVerdicts: ['REFUTED']},
      {runId: 'rE', verifyVerdicts: ['REFUTED']},
    ]
  });

  const result = runAlarm(vault, out);

  // Exit must NOT be 4 (0.6 is at the floor, not below it)
  assert(result.status !== 4,
    'REG-5: rate=0.6 (exactly at floor) does not trigger exit 4',
    `exit=${result.status} stderr=${result.stderr}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\nRegression fixtures: ${passed} passed, ${failed} failed.`);
process.exit(failed > 0 ? 1 : 0);
