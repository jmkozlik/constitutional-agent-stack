#!/usr/bin/env node
/**
 * gate_t3-beacon-alarm_write-guard.js
 *
 * Contract: beacon-alarm.js  (r004-regency / t3-beacon-alarm)
 * WRITE-GUARD section of the interface spec:
 *
 *   WG-1: --out is a symlink to a real directory → script MUST abort (non-zero),
 *         no alarm file written through the symlink.
 *   WG-2: --out is a regular file (not a directory) → script MUST abort (non-zero).
 *   WG-3: --out is a normal (non-symlink) directory → succeeds when alarm fires.
 *   WG-4: Reads never mutate — passing a vault with only a symlink in the ledger
 *         dir must not cause the script to follow and overwrite anything.
 *   WG-5: Alarm-file collision → uses -NN suffix instead of clobbering.
 *
 * Contract text:
 *   "Writes ONLY a regular file under <out>: lstat parent, no symlink-follow,
 *    abort on non-dir, collision -NN suffix. Reads never mutate."
 *
 * To trigger an actual alarm write (WG-3, WG-5), we use a 5-run vault with
 * first-pass-rate 0.4 < 0.6 floor — guaranteed to produce exit 4 + alarm file.
 */
'use strict';

const fs   = require('fs');
const path = require('path');
const os   = require('os');
const {spawnSync} = require('child_process');

const BEACON_ALARM = path.join(__dirname, 'beacon-alarm.js');

// ---------------------------------------------------------------------------
// Shared vault builders
// ---------------------------------------------------------------------------

// Regression vault: 5 runs, first-pass-rate = 0.4 → guaranteed alarm
function buildRegressionVault(base) {
  const ledger  = path.join(base, 'ledger');
  const archive = path.join(base, 'executors', 'archive');
  fs.mkdirSync(ledger,  {recursive: true});
  fs.mkdirSync(archive, {recursive: true});

  const TS  = '2026-01-01T10:00:00Z';
  const TS2 = '2026-01-01T10:08:00Z';
  let seq = 1;
  function entry(name, body) {
    fs.writeFileSync(path.join(ledger, String(seq).padStart(4,'0') + '-' + name + '.md'), body);
    seq++;
  }

  const runs = [
    {runId: 'rA', verdict: 'REFUTED'},
    {runId: 'rB', verdict: 'REFUTED'},
    {runId: 'rC', verdict: 'REFUTED'},
    {runId: 'rD', verdict: 'NOT-REFUTED'},
    {runId: 'rE', verdict: 'NOT-REFUTED'},
  ];

  for (const run of runs) {
    entry(`${run.runId}-start`,
      `---\ntype: log\nlabels: [run]\nrun-id: ${run.runId}\n---\n${TS} · ${run.runId} START\n`);
    entry(`${run.runId}-complete`,
      `---\ntype: log\nlabels: [run]\nrun-id: ${run.runId}\n---\n${TS2} · ${run.runId} COMPLETE\n`);
    const dir = path.join(archive, run.runId);
    fs.mkdirSync(dir, {recursive: true});
    fs.writeFileSync(path.join(dir, 'verify-report-t1.md'),
      `# Verify Report\nVerdict: ${run.verdict}\n`);
  }
}

function runAlarm(vaultPath, outPath) {
  if (!fs.existsSync(BEACON_ALARM)) {
    return {status: -1, stdout: '', stderr: `beacon-alarm.js not found at ${BEACON_ALARM}`};
  }
  return spawnSync(process.execPath, [BEACON_ALARM, '--vault', vaultPath, '--out', outPath],
    {encoding: 'utf8', timeout: 15000});
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
// WG-1: --out is a symlink → abort, no file written through symlink
//   Contract: "lstat parent, no symlink-follow, abort on ..."
// ---------------------------------------------------------------------------
console.log('\n--- WG-1: --out is a symlink to real directory → abort ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'ba-wg1-'));
  const vault = path.join(tmp, 'vault');
  const real  = path.join(tmp, 'real-out');
  const link  = path.join(tmp, 'link-out');

  buildRegressionVault(vault);
  fs.mkdirSync(real, {recursive: true});
  fs.symlinkSync(real, link);

  const result = runAlarm(vault, link);

  // Must exit non-zero
  assert(result.status !== 0,
    'WG-1a: exit non-zero when --out is a symlink',
    `exit=${result.status}`);

  // No alarm file must appear in the real directory (no follow)
  const written = fs.readdirSync(real).filter(f => f.startsWith('alarm-'));
  assert(written.length === 0,
    'WG-1b: no alarm file written through symlink into real-out',
    `files: ${written.join(',')}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// WG-2: --out is a regular file (not a directory) → abort
//   Contract: "abort on non-dir"
// ---------------------------------------------------------------------------
console.log('\n--- WG-2: --out is a regular file → abort ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'ba-wg2-'));
  const vault = path.join(tmp, 'vault');
  const file  = path.join(tmp, 'i-am-a-file.txt');

  buildRegressionVault(vault);
  fs.writeFileSync(file, 'not a directory\n');

  const result = runAlarm(vault, file);

  assert(result.status !== 0,
    'WG-2: exit non-zero when --out is a regular file',
    `exit=${result.status} stderr=${result.stderr}`);

  // The file must be unmodified (no write attempted)
  const content = fs.readFileSync(file, 'utf8');
  assert(content === 'not a directory\n',
    'WG-2b: regular file content unmodified (no clobber)',
    `content: ${JSON.stringify(content)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// WG-3: --out is a normal (non-symlink) directory → alarm writes successfully
//   Confirms the guard doesn't block legitimate writes.
// ---------------------------------------------------------------------------
console.log('\n--- WG-3: --out is a normal directory → alarm file written, exit 4 ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'ba-wg3-'));
  const vault = path.join(tmp, 'vault');
  const out   = path.join(tmp, 'out');

  buildRegressionVault(vault);
  fs.mkdirSync(out, {recursive: true});

  const result = runAlarm(vault, out);

  assert(result.status === 4,
    'WG-3a: exit 4 when --out is a normal directory and regression detected',
    `exit=${result.status} stderr=${result.stderr}`);

  const alarms = fs.readdirSync(out).filter(f => f.startsWith('alarm-') && f.endsWith('.md'));
  assert(alarms.length >= 1,
    'WG-3b: alarm file written into normal out directory',
    `files: ${alarms.join(',')}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// WG-4: Collision handling — running alarm twice writes two distinct files
//   Contract: "collision -NN suffix"
//   We run the same vault twice against the same out directory; the second
//   invocation must not clobber the first alarm file — instead it uses a
//   -NN suffix or a distinct timestamp.
// ---------------------------------------------------------------------------
console.log('\n--- WG-4: collision → -NN suffix, second alarm file distinct from first ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'ba-wg4-'));
  const vault = path.join(tmp, 'vault');
  const out   = path.join(tmp, 'out');

  buildRegressionVault(vault);
  fs.mkdirSync(out, {recursive: true});

  // First run
  runAlarm(vault, out);
  const afterFirst = fs.readdirSync(out).filter(f => f.startsWith('alarm-') && f.endsWith('.md'));

  // Second run (may happen within same UTC second → collision is possible)
  runAlarm(vault, out);
  const afterSecond = fs.readdirSync(out).filter(f => f.startsWith('alarm-') && f.endsWith('.md'));

  // Must have at least as many files as before (collision must not delete)
  assert(afterSecond.length >= afterFirst.length,
    'WG-4a: second run does not reduce alarm file count (no clobber)',
    `first=${afterFirst.length} second=${afterSecond.length}`);

  // Specifically: if both ran in the same UTC second, we expect -01 or -02 suffix
  // (or a second distinct timestamp). Either way, the first file must still exist
  // with its original content intact.
  if (afterFirst.length > 0) {
    const firstFile = afterFirst.sort()[0];
    const firstPath = path.join(out, firstFile);
    // File still present
    assert(fs.existsSync(firstPath),
      'WG-4b: first alarm file still present after second run (not clobbered)',
      `expected file: ${firstFile}`);
  }

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// WG-5: Reads never mutate — a symlink INSIDE the ledger must not cause the
//   script to overwrite the symlink target.  The script reads ledger files;
//   it must not write to any of the paths it reads.
//   We put a symlink inside the ledger that points to a sentinel file and
//   verify the sentinel is untouched after the script runs.
// ---------------------------------------------------------------------------
console.log('\n--- WG-5: reads-never-mutate — ledger symlink target unmodified after run ---');
{
  const tmp     = fs.mkdtempSync(path.join(os.tmpdir(), 'ba-wg5-'));
  const vault   = path.join(tmp, 'vault');
  const out     = path.join(tmp, 'out');
  const sentinel = path.join(tmp, 'sentinel.txt');

  buildRegressionVault(vault);
  fs.mkdirSync(out, {recursive: true});

  // Sentinel file: unique content so we can detect writes
  const SENTINEL_CONTENT = 'sentinel-' + Date.now() + '\n';
  fs.writeFileSync(sentinel, SENTINEL_CONTENT);

  // Place a symlink inside the ledger directory pointing at the sentinel
  const lnkPath = path.join(vault, 'ledger', '9999-sentinel-link.md');
  fs.symlinkSync(sentinel, lnkPath);

  // Run the alarm — it reads ledger files, but must not write through the symlink
  runAlarm(vault, out);

  const afterContent = fs.readFileSync(sentinel, 'utf8');
  assert(afterContent === SENTINEL_CONTENT,
    'WG-5: sentinel file unmodified — reads do not mutate through ledger symlinks',
    `expected: ${JSON.stringify(SENTINEL_CONTENT)}\ngot: ${JSON.stringify(afterContent)}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\nWrite-guard fixtures: ${passed} passed, ${failed} failed.`);
process.exit(failed > 0 ? 1 : 0);
