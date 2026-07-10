#!/usr/bin/env node
/**
 * gate_t1-beacon_telemetry-liveness.js
 * Asserts:
 *   TL-1: RECORDER-DEAD emitted when a canary boot exists but NO telemetry rows
 *          follow it (canary boot ts is the most recent event; nothing in .telemetry
 *          after that point).
 *   TL-2: liveness=UNKNOWN emitted when there is NO canary data at all (god/canary
 *          dir absent or boot-log.jsonl empty / not present). Absence of canary ≠
 *          recorder dead.
 *   TL-3: telemetry-liveness=OK when telemetry rows exist with ts AFTER latest
 *          canary boot ts.
 *
 * Contract ref: "telemetry-liveness" metric and the explicit note:
 *   "if NO canary data exists at all → liveness=UNKNOWN (NOT recorder-dead —
 *    absence of canary is not proof of a dead recorder)"
 */
'use strict';
const fs   = require('fs');
const path = require('path');
const {spawnSync} = require('child_process');
const os   = require('os');

// ---------------------------------------------------------------------------
// Vault builders
// ---------------------------------------------------------------------------
function makeBaseVault(base) {
  const ledger = path.join(base, 'ledger');
  fs.mkdirSync(ledger, {recursive: true});
  // Minimal ledger so beacon has something to parse
  fs.writeFileSync(path.join(ledger, '0001-rX-start.md'),
    '---\ntype: log\nlabels: [run]\nrun-id: rX\n---\n2026-01-01T10:00:00Z · rX START\n');
  fs.writeFileSync(path.join(ledger, '0002-rX-complete.md'),
    '---\ntype: log\nlabels: [run]\nrun-id: rX\n---\n2026-01-01T10:08:00Z · rX COMPLETE\n');
}

/** TL-1: canary boot exists, but telemetry directory is empty (no rows after boot) */
function makeVaultRecorderDead(base) {
  makeBaseVault(base);
  const telem  = path.join(base, '.telemetry');
  const canary = path.join(base, 'god', 'canary');
  fs.mkdirSync(telem,  {recursive: true});
  fs.mkdirSync(canary, {recursive: true});

  // Canary boot at T+1
  const bootTs = '2026-01-01T09:05:00.000Z';
  fs.writeFileSync(path.join(canary, 'boot-log.jsonl'),
    JSON.stringify({ts: bootTs, event: 'sessionstart'}) + '\n');

  // Telemetry only has rows BEFORE the canary boot (stale rows)
  const oldTs = '2026-01-01T09:00:00.000Z';
  fs.writeFileSync(path.join(telem, 'raw-2026-01-01.jsonl'),
    JSON.stringify({ts: oldTs, tool: 'Write', file: '/tmp/x', session: 'test'}) + '\n');
  // No rows with ts > bootTs → recorder dead
}

/** TL-2: no canary data at all (god/canary dir is absent) */
function makeVaultNoCanary(base) {
  makeBaseVault(base);
  const telem = path.join(base, '.telemetry');
  fs.mkdirSync(telem, {recursive: true});
  // Telemetry rows exist, but no canary dir
  const ts = '2026-01-01T09:00:00.000Z';
  fs.writeFileSync(path.join(telem, 'raw-2026-01-01.jsonl'),
    JSON.stringify({ts, tool: 'Write', file: '/tmp/x', session: 'test'}) + '\n');
  // god/canary is deliberately NOT created
}

/** TL-3: telemetry rows after latest canary boot → OK */
function makeVaultLivenessOK(base) {
  makeBaseVault(base);
  const telem  = path.join(base, '.telemetry');
  const canary = path.join(base, 'god', 'canary');
  fs.mkdirSync(telem,  {recursive: true});
  fs.mkdirSync(canary, {recursive: true});

  const bootTs  = '2026-01-01T09:00:00.000Z';
  const telemTs = '2026-01-01T09:01:00.000Z'; // strictly after boot

  fs.writeFileSync(path.join(canary, 'boot-log.jsonl'),
    JSON.stringify({ts: bootTs, event: 'sessionstart'}) + '\n');
  fs.writeFileSync(path.join(telem, 'raw-2026-01-01.jsonl'),
    JSON.stringify({ts: telemTs, tool: 'Write', file: '/tmp/x', session: 'test'}) + '\n');
}

// ---------------------------------------------------------------------------
// Runner
// ---------------------------------------------------------------------------
function runBeacon(vaultPath) {
  const beacon = path.join(__dirname, 'beacon.js');
  const out    = path.join(vaultPath, '_out');
  fs.mkdirSync(out, {recursive: true});
  return spawnSync(process.execPath, [beacon, '--vault', vaultPath, '--out', out],
    {encoding: 'utf8', timeout: 10000});
}

function readBeaconReport(vaultPath) {
  const out   = path.join(vaultPath, '_out');
  const files = fs.readdirSync(out).filter(f => f.startsWith('beacon-'));
  if (files.length === 0) return null;
  files.sort();
  return fs.readFileSync(path.join(out, files[files.length - 1]), 'utf8');
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
// TL-1: RECORDER-DEAD
// ---------------------------------------------------------------------------
console.log('\n--- TL-1: RECORDER-DEAD (canary boot, no subsequent telemetry) ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-tl1-'));
  makeVaultRecorderDead(tmp);
  const result = runBeacon(tmp);
  const report = readBeaconReport(tmp);

  assert(result.status === 0,
    'TL-1a: exit 0',
    `status=${result.status} stderr=${result.stderr}`);

  const combined = (result.stdout || '') + (report || '');
  assert(/RECORDER-DEAD/i.test(combined),
    'TL-1b: RECORDER-DEAD appears in stdout or report',
    `stdout: ${result.stdout}\nreport snippet: ${(report || '').slice(0, 400)}`);

  // Must NOT say liveness=UNKNOWN in this case
  assert(!/liveness\s*=\s*UNKNOWN/i.test(combined),
    'TL-1c: does NOT emit liveness=UNKNOWN when recorder is dead (distinct states)',
    `combined snippet: ${combined.slice(0, 400)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// TL-2: liveness=UNKNOWN (no canary at all)
// ---------------------------------------------------------------------------
console.log('\n--- TL-2: liveness=UNKNOWN (no canary data) ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-tl2-'));
  makeVaultNoCanary(tmp);
  const result = runBeacon(tmp);
  const report = readBeaconReport(tmp);

  assert(result.status === 0,
    'TL-2a: exit 0',
    `status=${result.status} stderr=${result.stderr}`);

  const combined = (result.stdout || '') + (report || '');
  assert(/liveness\s*=\s*UNKNOWN/i.test(combined) || /UNKNOWN/i.test(combined),
    'TL-2b: liveness=UNKNOWN appears in stdout or report',
    `stdout: ${result.stdout}\nreport snippet: ${(report || '').slice(0, 400)}`);

  // Must NOT say RECORDER-DEAD when canary is simply absent
  assert(!/RECORDER-DEAD/i.test(combined),
    'TL-2c: does NOT emit RECORDER-DEAD when canary is absent (no canary ≠ dead recorder)',
    `combined snippet: ${combined.slice(0, 400)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// TL-3: telemetry-liveness=OK
// ---------------------------------------------------------------------------
console.log('\n--- TL-3: telemetry-liveness=OK (telemetry follows canary boot) ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-tl3-'));
  makeVaultLivenessOK(tmp);
  const result = runBeacon(tmp);
  const report = readBeaconReport(tmp);

  assert(result.status === 0,
    'TL-3a: exit 0',
    `status=${result.status} stderr=${result.stderr}`);

  const combined = (result.stdout || '') + (report || '');
  assert(/liveness\s*=\s*OK/i.test(combined) || /telemetry-liveness.*OK/i.test(combined),
    'TL-3b: liveness=OK appears in stdout or report',
    `stdout: ${result.stdout}\nreport snippet: ${(report || '').slice(0, 400)}`);

  assert(!/RECORDER-DEAD/i.test(combined),
    'TL-3c: does NOT emit RECORDER-DEAD when liveness is OK',
    combined.slice(0, 400));

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// TL-4: canary boot-log.jsonl present but empty → treated as no canary data
//        (edge case: empty file should not be treated as a valid boot event)
// ---------------------------------------------------------------------------
console.log('\n--- TL-4: empty boot-log.jsonl treated as no canary (UNKNOWN, not RECORDER-DEAD) ---');
{
  const tmp    = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-tl4-'));
  makeBaseVault(tmp);
  const telem  = path.join(tmp, '.telemetry');
  const canary = path.join(tmp, 'god', 'canary');
  fs.mkdirSync(telem,  {recursive: true});
  fs.mkdirSync(canary, {recursive: true});
  // Empty boot log
  fs.writeFileSync(path.join(canary, 'boot-log.jsonl'), '');
  // Some telemetry rows exist
  fs.writeFileSync(path.join(telem, 'raw-2026-01-01.jsonl'),
    JSON.stringify({ts: '2026-01-01T09:00:00.000Z', tool: 'Write', file: '/tmp/x', session: 's'}) + '\n');

  const result = runBeacon(tmp);
  const report = readBeaconReport(tmp);

  assert(result.status === 0,
    'TL-4a: exit 0 on empty boot-log',
    `status=${result.status} stderr=${result.stderr}`);

  const combined = (result.stdout || '') + (report || '');
  assert(!/RECORDER-DEAD/i.test(combined),
    'TL-4b: empty boot-log does NOT trigger RECORDER-DEAD',
    combined.slice(0, 400));

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\nTelemetry-liveness fixtures: ${passed} passed, ${failed} failed.`);
process.exit(failed > 0 ? 1 : 0);
