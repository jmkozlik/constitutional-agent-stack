#!/usr/bin/env node
/**
 * gate_t2-retaliation-flag_write-guard.js
 *
 * Gate fixtures for retaliation-flag.js — t2-retaliation-flag, run r004-regency.
 * Derived EXCLUSIVELY from the contract interface spec. No implementation code read.
 *
 * Behavior classes under test:
 *
 *   WG-1: --out is a symlink pointing to a real directory → abort (non-zero,
 *         NOT exit 3), no flag file written through the symlink.
 *   WG-2: --out path exists as a regular file (non-dir) → abort (non-zero,
 *         NOT exit 3).
 *   WG-3: --out is a normal (non-symlink) directory → on conflict: exit 3
 *         and flag written; on clear: exit 0.  (Baseline — guards don't fire
 *         on a normal dir.)
 *   WG-4: flag file collision suffix — if <target>-<UTCstamp>.flag.md already
 *         exists in <out>, the script appends a -NN suffix rather than
 *         overwriting.
 *
 * Contract text:
 *   "Writes ONLY a regular file under <out>: lstat parent, no symlink-follow,
 *   abort on non-dir, collision -NN suffix."
 *
 * Exit codes for this fixture:
 *   0 — all assertions passed
 *   1 — one or more assertions failed
 */
'use strict';

const { spawnSync } = require('child_process');
const fs   = require('fs');
const os   = require('os');
const path = require('path');

const SCRIPT = path.resolve(process.argv[2] || path.join(__dirname, 'retaliation-flag.js'));

let passed = 0;
let failed = 0;
const failures = [];

function assert(label, condition, detail) {
  if (condition) {
    console.log(`  PASS  ${label}`);
    passed++;
  } else {
    console.error(`  FAIL  ${label}${detail ? ' — ' + detail : ''}`);
    failed++;
    failures.push({ label, detail });
  }
}

function makeTmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix || 'gate-rf-wg-'));
}

/**
 * A vault containing a single mutiny entry that WILL cause a CONFLICT for
 * --target obs-2 --voters obs-1,council-skeptic.
 * This ensures any write-guard test that uses it is exercising the write path.
 */
function makeConflictVault(base) {
  const ledger = path.join(base, 'ledger');
  fs.mkdirSync(ledger, { recursive: true });
  fs.writeFileSync(path.join(ledger, '0040-mutiny.md'), [
    '---',
    'type: mutiny',
    'labels: [mutiny]',
    'filed-by: obs-2',
    'against: council-skeptic',
    '---',
    '# Mutiny filing for write-guard tests',
  ].join('\n') + '\n', 'utf8');
  return base;
}

function runFlag(args) {
  return spawnSync(process.execPath, [SCRIPT, ...args], {
    encoding: 'utf8',
    timeout: 10000,
  });
}

function flagFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter(f => f.endsWith('.flag.md'));
}

function cleanup(dir) {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch (_) {}
}

// ---------------------------------------------------------------------------
// WG-1: --out is a symlink → must abort, NOT write any flag through the link
// ---------------------------------------------------------------------------
console.log('\nWG-1: --out is a symlink — must abort (non-zero, NOT exit 3)');
{
  const tmp      = makeTmpDir('gate-rf-wg1-');
  const vault    = makeConflictVault(path.join(tmp, 'vault'));
  const realDir  = path.join(tmp, 'real-out');
  const symlinkPath = path.join(tmp, 'sym-out');
  fs.mkdirSync(realDir, { recursive: true });
  fs.symlinkSync(realDir, symlinkPath);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    symlinkPath,
  ]);

  assert('WG-1a: non-zero exit when --out is a symlink',
    result.status !== 0,
    `got exit ${result.status}`);

  assert('WG-1b: exit is NOT 3 when refusing symlink (abort != conflict)',
    result.status !== 3,
    `got exit ${result.status} — a write-guard abort must not look like CONFLICT`);

  const filesInReal = flagFiles(realDir);
  assert('WG-1c: no flag file written through the symlink to real dir',
    filesInReal.length === 0,
    `found ${filesInReal.length} flag file(s) in real dir: ${filesInReal.join(', ')}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// WG-2: --out is a regular file (not a directory) → must abort
// ---------------------------------------------------------------------------
console.log('\nWG-2: --out is a regular file — must abort (non-zero, NOT exit 3)');
{
  const tmp     = makeTmpDir('gate-rf-wg2-');
  const vault   = makeConflictVault(path.join(tmp, 'vault'));
  const notADir = path.join(tmp, 'not-a-dir.txt');
  fs.writeFileSync(notADir, 'I am a file, not a directory.\n', 'utf8');

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    notADir,
  ]);

  assert('WG-2a: non-zero exit when --out is a regular file',
    result.status !== 0,
    `got exit ${result.status}\nstderr: ${result.stderr}`);

  assert('WG-2b: exit is NOT 3 when refusing non-dir (abort != conflict)',
    result.status !== 3,
    `got exit ${result.status} — a write-guard abort must not look like CONFLICT`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// WG-3a: --out is a normal directory + conflict present → exit 3, flag written
//         (baseline: write-guard passes for a valid directory)
// ---------------------------------------------------------------------------
console.log('\nWG-3a: --out is a normal directory + conflict → exit 3 + flag (baseline)');
{
  const tmp   = makeTmpDir('gate-rf-wg3-');
  const vault = makeConflictVault(path.join(tmp, 'vault'));
  const out   = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('WG-3a-1: normal dir + conflict → exit 3',
    result.status === 3,
    `got exit ${result.status}`);

  const flags = flagFiles(out);
  assert('WG-3a-2: flag file written into normal dir',
    flags.length >= 1,
    `found ${flags.length}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// WG-3b: --out is a normal directory + clear (no conflict) → exit 0, no flag
// ---------------------------------------------------------------------------
console.log('\nWG-3b: --out is a normal directory + no conflict → exit 0, no flag');
{
  const tmp   = makeTmpDir('gate-rf-wg3b-');
  const vault = path.join(tmp, 'vault');
  const ledger = path.join(vault, 'ledger');
  fs.mkdirSync(ledger, { recursive: true });
  fs.writeFileSync(path.join(ledger, '0040-mutiny.md'), [
    '---',
    'type: mutiny',
    'labels: [mutiny]',
    'filed-by: obs-2',
    'against: obs-9',  // obs-9 is NOT a voter
    '---',
    '# Filing against non-voter',
  ].join('\n') + '\n', 'utf8');

  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('WG-3b-1: normal dir + no conflict → exit 0',
    result.status === 0,
    `got exit ${result.status}`);

  const flags = flagFiles(out);
  assert('WG-3b-2: no flag file written when no conflict',
    flags.length === 0,
    `found ${flags.length}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// WG-4: collision suffix — if <target>-<UTCstamp>.flag.md already exists,
//        next write uses -NN suffix and does NOT clobber the prior file.
//        We run the script twice against the same --out to force the collision.
// ---------------------------------------------------------------------------
console.log('\nWG-4: collision suffix — second conflict write gets -NN suffix, no clobber');
{
  const tmp   = makeTmpDir('gate-rf-wg4-');
  const vault = makeConflictVault(path.join(tmp, 'vault'));
  const out   = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });

  // First run — produces the base flag file
  const r1 = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
  ]);
  assert('WG-4a: first run exits 3 (conflict)',
    r1.status === 3,
    `got exit ${r1.status}\nstderr: ${r1.stderr}`);

  const after1 = flagFiles(out);
  assert('WG-4b: exactly one flag file after first run',
    after1.length === 1,
    `found ${after1.length}: ${after1.join(', ')}`);

  if (after1.length === 1) {
    const firstContent = fs.readFileSync(path.join(out, after1[0]), 'utf8');

    // Second run — same vault, same conflict, same timestamp resolution window
    const r2 = runFlag([
      '--target', 'obs-2',
      '--voters', 'obs-1,council-skeptic',
      '--vault',  vault,
      '--out',    out,
    ]);
    assert('WG-4c: second run exits 3 (conflict, again)',
      r2.status === 3,
      `got exit ${r2.status}\nstderr: ${r2.stderr}`);

    const after2 = flagFiles(out);
    assert('WG-4d: two distinct flag files after second run (no clobber)',
      after2.length === 2,
      `found ${after2.length}: ${after2.join(', ')}`);

    // Verify the first file was not overwritten
    if (after2.length === 2) {
      const contentNow = fs.readFileSync(path.join(out, after1[0]), 'utf8');
      assert('WG-4e: original flag file content preserved (not clobbered)',
        contentNow === firstContent,
        `original length=${firstContent.length} now length=${contentNow.length}`);

      // The two files must have distinct names
      assert('WG-4f: two flag files have distinct names',
        after2[0] !== after2[1],
        `both named: ${after2[0]}`);
    }
  }

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\n${'='.repeat(60)}`);
console.log(`Write-guard fixtures: ${passed} passed, ${failed} failed.`);
if (failures.length > 0) {
  console.error('\nFailed assertions:');
  for (const f of failures) {
    console.error(`  FAIL  ${f.label}${f.detail ? ': ' + f.detail : ''}`);
  }
}
console.log('='.repeat(60));
process.exit(failed > 0 ? 1 : 0);
