#!/usr/bin/env node
/**
 * gate_t3-beacon-alarm_thresholds.js
 *
 * Contract: beacon-alarm.js  (r004-regency / t3-beacon-alarm)
 * One test per hardcoded threshold:
 *
 *   THR-1: rework-rate rises above ceiling 2.0
 *          → exit 4, alarm names "rework-rate" + ceiling + driver run
 *   THR-2: contract-violations > 0
 *          → exit 4, alarm names "contract-violation" + driver run
 *   THR-3: promotion-churn > 0 (a promotion that was then reverted)
 *          → exit 4, alarm names "promotion-churn" + driver run
 *   THR-4: governance-heat spikes past ceiling 6/run
 *          → exit 4, alarm names "governance-heat" + ceiling + driver run
 *
 * Each sub-test builds a 5-run synthetic vault where exactly ONE metric
 * breaches its threshold in the rolling window.  All other metrics remain
 * healthy so that only the targeted alarm fires.
 *
 * Thresholds (contract-hardcoded, god-space):
 *   first-pass-rate floor   0.6   (tested in gate_t3-beacon-alarm_regression.js)
 *   rework-rate ceiling     2.0
 *   contract-violations     0
 *   promotion-churn         0
 *   governance-heat ceiling 6/run
 */
'use strict';

const fs   = require('fs');
const path = require('path');
const os   = require('os');
const {spawnSync} = require('child_process');

const BEACON_ALARM = path.join(__dirname, 'beacon-alarm.js');

// ---------------------------------------------------------------------------
// Vault builder (shared)
// ---------------------------------------------------------------------------
function buildVault(base, opts) {
  // opts.runs: array of run descriptors
  //   { runId, verdicts, retryCount, contractViolation, promotionReverted, motionCount }
  const ledger  = path.join(base, 'ledger');
  const archive = path.join(base, 'executors', 'archive');
  fs.mkdirSync(ledger,  {recursive: true});
  fs.mkdirSync(archive, {recursive: true});

  let seq = 1;
  function entry(name, body) {
    fs.writeFileSync(path.join(ledger, String(seq).padStart(4,'0') + '-' + name + '.md'), body);
    seq++;
  }
  const TS  = '2026-01-01T10:00:00Z';
  const TS2 = '2026-01-01T10:08:00Z';

  for (const run of opts.runs) {
    entry(`${run.runId}-start`,
      `---\ntype: log\nlabels: [run]\nrun-id: ${run.runId}\n---\n${TS} · ${run.runId} START\n`);

    for (let i = 0; i < (run.retryCount || 0); i++) {
      entry(`${run.runId}-retry-${i}`,
        `---\ntype: log\nlabels: [run, retry-ladder]\nrun-id: ${run.runId}\n---\n${TS} · ${run.runId} RETRY\n`);
    }

    if (run.contractViolation) {
      entry(`${run.runId}-violation`,
        `---\ntype: log\nlabels: [governance, contract-violation]\nrun-id: ${run.runId}\n---\n${TS} · contract violation in ${run.runId}\n`);
    }

    if (run.promotionReverted) {
      entry(`${run.runId}-promoted`,
        `---\ntype: log\nlabels: [governance, promoted]\nrun-id: ${run.runId}\n---\n${TS} · promoted\n`);
      entry(`${run.runId}-reverted`,
        `---\ntype: log\nlabels: [governance, reverted]\nrun-id: ${run.runId}\n---\n${TS} · reverted\n`);
    }

    for (let i = 0; i < (run.motionCount || 0); i++) {
      entry(`${run.runId}-motion-${i}`,
        `---\ntype: log\nlabels: [governance, motion]\nrun-id: ${run.runId}\n---\n${TS} · motion ${i+1}\n`);
    }

    entry(`${run.runId}-complete`,
      `---\ntype: log\nlabels: [run]\nrun-id: ${run.runId}\n---\n${TS2} · ${run.runId} COMPLETE\n`);

    // Verify reports (default all NOT-REFUTED unless specified)
    const verdicts = run.verdicts || ['NOT-REFUTED'];
    for (let i = 0; i < verdicts.length; i++) {
      const dir = path.join(archive, run.runId);
      fs.mkdirSync(dir, {recursive: true});
      fs.writeFileSync(path.join(dir, `verify-report-t${i+1}.md`),
        `# Verify Report\nVerdict: ${verdicts[i]}\n`);
    }
  }
}

function runAlarm(vaultPath, outPath) {
  if (!fs.existsSync(BEACON_ALARM)) {
    return {status: -1, stdout: '', stderr: `beacon-alarm.js not found at ${BEACON_ALARM}`};
  }
  return spawnSync(process.execPath, [BEACON_ALARM, '--vault', vaultPath, '--out', outPath],
    {encoding: 'utf8', timeout: 15000});
}

function latestAlarm(outPath) {
  if (!fs.existsSync(outPath)) return null;
  const files = fs.readdirSync(outPath)
    .filter(f => f.startsWith('alarm-') && f.endsWith('.md')).sort();
  if (!files.length) return null;
  return fs.readFileSync(path.join(outPath, files[files.length-1]), 'utf8');
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
function setup() {
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-alarm-thr-'));
  const out   = path.join(tmp, 'out');
  const vault = path.join(tmp, 'vault');
  fs.mkdirSync(out,   {recursive: true});
  fs.mkdirSync(vault, {recursive: true});
  return {tmp, out, vault};
}

// ---------------------------------------------------------------------------
// THR-1: rework-rate > 2.0 ceiling
//   5 runs; one run has 3 retry-ladder entries → rework-rate for that run = 3
//   The per-run rate of 3 > ceiling 2.0 → alarm.
//   (Alternatively, the window average exceeds 2.0 — either interpretation is
//   valid per spec "alarm if it RISES above threshold".)
// ---------------------------------------------------------------------------
console.log('\n--- THR-1: rework-rate above ceiling 2.0 → exit 4, alarm names metric + driver ---');
{
  const {tmp, out, vault} = setup();

  buildVault(vault, {
    runs: [
      {runId: 'rA', verdicts: ['NOT-REFUTED']},
      {runId: 'rB', verdicts: ['NOT-REFUTED']},
      {runId: 'rC', verdicts: ['NOT-REFUTED']},
      {runId: 'rD', verdicts: ['NOT-REFUTED']},
      // rE has 3 retries — rework-rate = 3 > ceiling 2.0
      {runId: 'rE', verdicts: ['NOT-REFUTED'], retryCount: 3},
    ]
  });

  const result = runAlarm(vault, out);

  assert(result.status === 4,
    'THR-1a: exit 4 when rework-rate exceeds ceiling',
    `exit=${result.status} stderr=${result.stderr}`);

  const alarm = latestAlarm(out);
  assert(alarm !== null,
    'THR-1b: alarm file written',
    `out dir: ${fs.readdirSync(out).join(',')}`);

  if (alarm) {
    assert(/rework/i.test(alarm),
      'THR-1c: alarm names metric "rework-rate"',
      `alarm: ${alarm.slice(0,300)}`);

    assert(/2\.0|ceiling/i.test(alarm),
      'THR-1d: alarm names threshold 2.0 (ceiling)',
      `alarm: ${alarm.slice(0,300)}`);

    assert(/rE/i.test(alarm),
      'THR-1e: alarm names driver run-id rE',
      `alarm: ${alarm.slice(0,300)}`);
  }

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// THR-2: contract-violations > 0
//   5 runs; one run has a contract-violation ledger entry → count > 0 → alarm.
// ---------------------------------------------------------------------------
console.log('\n--- THR-2: contract-violation count > 0 → exit 4, alarm names metric + driver ---');
{
  const {tmp, out, vault} = setup();

  buildVault(vault, {
    runs: [
      {runId: 'rA', verdicts: ['NOT-REFUTED']},
      {runId: 'rB', verdicts: ['NOT-REFUTED']},
      {runId: 'rC', verdicts: ['NOT-REFUTED']},
      {runId: 'rD', verdicts: ['NOT-REFUTED']},
      // rE violated contract
      {runId: 'rE', verdicts: ['NOT-REFUTED'], contractViolation: true},
    ]
  });

  const result = runAlarm(vault, out);

  assert(result.status === 4,
    'THR-2a: exit 4 when contract-violation count > 0',
    `exit=${result.status} stderr=${result.stderr}`);

  const alarm = latestAlarm(out);
  assert(alarm !== null,
    'THR-2b: alarm file written',
    `out dir: ${fs.existsSync(out) ? fs.readdirSync(out).join(',') : 'missing'}`);

  if (alarm) {
    assert(/contract.violation|contract_violation/i.test(alarm),
      'THR-2c: alarm names metric "contract-violation"',
      `alarm: ${alarm.slice(0,300)}`);

    assert(/rE/i.test(alarm),
      'THR-2d: alarm names driver run-id rE',
      `alarm: ${alarm.slice(0,300)}`);
  }

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// THR-3: promotion-churn > 0
//   5 runs; one run has a promoted-then-reverted ledger pair → churn = 1 → alarm.
// ---------------------------------------------------------------------------
console.log('\n--- THR-3: promotion-churn > 0 → exit 4, alarm names metric + driver ---');
{
  const {tmp, out, vault} = setup();

  buildVault(vault, {
    runs: [
      {runId: 'rA', verdicts: ['NOT-REFUTED']},
      {runId: 'rB', verdicts: ['NOT-REFUTED']},
      {runId: 'rC', verdicts: ['NOT-REFUTED']},
      {runId: 'rD', verdicts: ['NOT-REFUTED']},
      // rE has a promotion that was reverted
      {runId: 'rE', verdicts: ['NOT-REFUTED'], promotionReverted: true},
    ]
  });

  const result = runAlarm(vault, out);

  assert(result.status === 4,
    'THR-3a: exit 4 when promotion-churn > 0',
    `exit=${result.status} stderr=${result.stderr}`);

  const alarm = latestAlarm(out);
  assert(alarm !== null,
    'THR-3b: alarm file written',
    `out dir: ${fs.existsSync(out) ? fs.readdirSync(out).join(',') : 'missing'}`);

  if (alarm) {
    assert(/promotion.churn|churn/i.test(alarm),
      'THR-3c: alarm names metric "promotion-churn"',
      `alarm: ${alarm.slice(0,300)}`);

    assert(/rE/i.test(alarm),
      'THR-3d: alarm names driver run-id rE',
      `alarm: ${alarm.slice(0,300)}`);
  }

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// THR-4: governance-heat spikes past ceiling 6/run
//   5 runs; one run has 7 motion entries → heat = 7 > ceiling 6 → alarm.
// ---------------------------------------------------------------------------
console.log('\n--- THR-4: governance-heat > 6/run ceiling → exit 4, alarm names metric + driver ---');
{
  const {tmp, out, vault} = setup();

  buildVault(vault, {
    runs: [
      {runId: 'rA', verdicts: ['NOT-REFUTED']},
      {runId: 'rB', verdicts: ['NOT-REFUTED']},
      {runId: 'rC', verdicts: ['NOT-REFUTED']},
      {runId: 'rD', verdicts: ['NOT-REFUTED']},
      // rE has 7 governance motions — heat = 7 > ceiling 6
      {runId: 'rE', verdicts: ['NOT-REFUTED'], motionCount: 7},
    ]
  });

  const result = runAlarm(vault, out);

  assert(result.status === 4,
    'THR-4a: exit 4 when governance-heat exceeds ceiling 6/run',
    `exit=${result.status} stderr=${result.stderr}`);

  const alarm = latestAlarm(out);
  assert(alarm !== null,
    'THR-4b: alarm file written',
    `out dir: ${fs.existsSync(out) ? fs.readdirSync(out).join(',') : 'missing'}`);

  if (alarm) {
    assert(/governance.heat|gov.*heat|heat/i.test(alarm),
      'THR-4c: alarm names metric "governance-heat"',
      `alarm: ${alarm.slice(0,300)}`);

    assert(/6/i.test(alarm),
      'THR-4d: alarm names threshold 6 (ceiling)',
      `alarm: ${alarm.slice(0,300)}`);

    assert(/rE/i.test(alarm),
      'THR-4e: alarm names driver run-id rE',
      `alarm: ${alarm.slice(0,300)}`);
  }

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// THR-5: governance-heat exactly AT ceiling (6/run) — boundary, must not alarm
//   Contract says "spikes PAST threshold" — exactly 6 should not fire.
// ---------------------------------------------------------------------------
console.log('\n--- THR-5: governance-heat=6 exactly (at ceiling, not over) → no alarm ---');
{
  const {tmp, out, vault} = setup();

  buildVault(vault, {
    runs: [
      {runId: 'rA', verdicts: ['NOT-REFUTED']},
      {runId: 'rB', verdicts: ['NOT-REFUTED']},
      {runId: 'rC', verdicts: ['NOT-REFUTED']},
      {runId: 'rD', verdicts: ['NOT-REFUTED']},
      // Exactly 6 motions — at ceiling, not over
      {runId: 'rE', verdicts: ['NOT-REFUTED'], motionCount: 6},
    ]
  });

  const result = runAlarm(vault, out);

  // Should NOT exit 4 (at ceiling is not over ceiling)
  assert(result.status !== 4,
    'THR-5: governance-heat exactly at ceiling (6) does not trigger exit 4',
    `exit=${result.status}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\nThreshold fixtures: ${passed} passed, ${failed} failed.`);
process.exit(failed > 0 ? 1 : 0);
