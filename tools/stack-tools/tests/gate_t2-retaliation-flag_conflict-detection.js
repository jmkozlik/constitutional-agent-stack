#!/usr/bin/env node
/**
 * gate_t2-retaliation-flag_conflict-detection.js
 *
 * Gate fixtures for retaliation-flag.js — t2-retaliation-flag, run r004-regency.
 * Derived EXCLUSIVELY from the contract interface spec. No implementation code read.
 *
 * Behavior classes under test:
 *
 *   A. CONFLICT path — target filed against a voter → exit EXACTLY 3 + flag file
 *      written naming the conflict.
 *   B. CLEAR path — target filed against a non-voter → exit 0 + stdout
 *      "RETALIATION-CLEAR".
 *   C. Flag file naming: must be <target>-<UTCstamp>.flag.md, must contain the
 *      conflicting entry filename, filer, against, and which voter was matched.
 *   D. Exit code EXACTLY 3 — not 1 or 2; a crash (exit 1) must NOT read as conflict.
 *
 * Exit codes:
 *   0 — all assertions passed
 *   1 — one or more assertions failed
 */
'use strict';

const { spawnSync } = require('child_process');
const fs   = require('fs');
const os   = require('os');
const path = require('path');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Path to the script under test; allow override via argv[2]
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
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix || 'gate-rf-'));
}

/**
 * Build a minimal synthetic vault containing a governance ledger directory.
 * ledgerEntries is an array of { filename, content } objects.
 */
function makeVault(base, ledgerEntries) {
  const ledger = path.join(base, 'ledger');
  fs.mkdirSync(ledger, { recursive: true });
  for (const entry of ledgerEntries) {
    fs.writeFileSync(path.join(ledger, entry.filename), entry.content, 'utf8');
  }
  return base;
}

function runFlag(args) {
  return spawnSync(process.execPath, [SCRIPT, ...args], {
    encoding: 'utf8',
    timeout: 10000,
  });
}

/** Returns .flag.md files in outDir (or empty array). */
function flagFiles(outDir) {
  if (!fs.existsSync(outDir)) return [];
  return fs.readdirSync(outDir).filter(f => f.endsWith('.flag.md'));
}

function cleanup(dir) {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch (_) {}
}

// ---------------------------------------------------------------------------
// Suite A: CONFLICT — frontmatter form (filed-by / against in frontmatter)
//
//   target: obs-2   voters: obs-1,council-skeptic
//   Ledger entry (frontmatter form):
//     filed-by: obs-2
//     against: council-skeptic    ← voter match!
//   Expected: exit 3, flag file written
// ---------------------------------------------------------------------------
console.log('\nSuite A: CONFLICT — frontmatter form (filed-by/against in frontmatter)');
{
  const tmp  = makeTmpDir('gate-rf-a-');
  const out  = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  const vault = makeVault(path.join(tmp, 'vault'), [
    {
      filename: '0040-mutiny.md',
      content: [
        '---',
        'type: mutiny',
        'labels: [mutiny]',
        'filed-by: obs-2',
        'against: council-skeptic',
        '---',
        '# Mutiny filing',
        'Evidence of misconduct.',
      ].join('\n') + '\n',
    },
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('A1: exit code is EXACTLY 3 on conflict (frontmatter form)',
    result.status === 3,
    `got exit ${result.status}\nstdout: ${result.stdout}\nstderr: ${result.stderr}`);

  const flags = flagFiles(out);
  assert('A2: exactly one flag file written',
    flags.length === 1,
    `found ${flags.length}: ${flags.join(', ')}`);

  if (flags.length >= 1) {
    const content = fs.readFileSync(path.join(out, flags[0]), 'utf8');

    assert('A3: flag filename starts with target "obs-2"',
      flags[0].startsWith('obs-2-'),
      `got filename: ${flags[0]}`);

    assert('A4: flag filename ends with .flag.md',
      flags[0].endsWith('.flag.md'),
      `got filename: ${flags[0]}`);

    assert('A5: flag file body contains conflicting entry filename',
      content.includes('0040-mutiny.md'),
      `flag content: ${content}`);

    assert('A6: flag file body names the filer (obs-2)',
      /obs-2/.test(content),
      `flag content: ${content}`);

    assert('A7: flag file body names the "against" target (council-skeptic)',
      /council-skeptic/.test(content),
      `flag content: ${content}`);

    assert('A8: flag file body names which voter was matched',
      /council-skeptic/.test(content),
      `flag content: ${content}`);
  }

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite B: CONFLICT — body token form (· filer: / · against: in body)
//
//   Same scenario but using body tokens instead of frontmatter lines.
//   target: obs-2   voters: obs-1,council-skeptic
// ---------------------------------------------------------------------------
console.log('\nSuite B: CONFLICT — body token form (filer:/against: in body)');
{
  const tmp  = makeTmpDir('gate-rf-b-');
  const out  = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  const vault = makeVault(path.join(tmp, 'vault'), [
    {
      filename: '0041-motion.md',
      content: [
        '---',
        'type: motion',
        'labels: [motion]',
        '---',
        '# Motion filing',
        '· filer: obs-2',
        '· against: council-skeptic',
        'Supporting evidence text.',
      ].join('\n') + '\n',
    },
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('B1: exit code is EXACTLY 3 on conflict (body token form)',
    result.status === 3,
    `got exit ${result.status}\nstdout: ${result.stdout}\nstderr: ${result.stderr}`);

  const flags = flagFiles(out);
  assert('B2: flag file written for body-token form conflict',
    flags.length >= 1,
    `found ${flags.length}`);

  if (flags.length >= 1) {
    const content = fs.readFileSync(path.join(out, flags[0]), 'utf8');
    assert('B3: flag file names the matched voter (council-skeptic)',
      /council-skeptic/.test(content),
      `flag content: ${content}`);
  }

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite C: CLEAR — target filed against a NON-voter
//
//   target: obs-2   voters: obs-1,council-skeptic
//   Ledger entry: filed-by: obs-2, against: obs-9   ← obs-9 is NOT a voter
//   Expected: exit 0, stdout contains RETALIATION-CLEAR, no flag file
// ---------------------------------------------------------------------------
console.log('\nSuite C: CLEAR — target filed against a non-voter → exit 0');
{
  const tmp  = makeTmpDir('gate-rf-c-');
  const out  = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  const vault = makeVault(path.join(tmp, 'vault'), [
    {
      filename: '0040-mutiny.md',
      content: [
        '---',
        'type: mutiny',
        'labels: [mutiny]',
        'filed-by: obs-2',
        'against: obs-9',
        '---',
        '# Mutiny filing against obs-9 (not a voter)',
      ].join('\n') + '\n',
    },
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('C1: exit code is 0 when no conflict (against is non-voter)',
    result.status === 0,
    `got exit ${result.status}\nstdout: ${result.stdout}\nstderr: ${result.stderr}`);

  const combined = (result.stdout || '') + (result.stderr || '');
  assert('C2: output contains RETALIATION-CLEAR when no conflict',
    /RETALIATION-CLEAR/.test(combined),
    `stdout: ${result.stdout} | stderr: ${result.stderr}`);

  const flags = flagFiles(out);
  assert('C3: no flag files written when no conflict',
    flags.length === 0,
    `found ${flags.length}: ${flags.join(', ')}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite D: CLEAR — empty ledger (no motion/mutiny entries at all)
//   Expected: exit 0, RETALIATION-CLEAR
// ---------------------------------------------------------------------------
console.log('\nSuite D: CLEAR — empty ledger → exit 0');
{
  const tmp  = makeTmpDir('gate-rf-d-');
  const out  = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  // Ledger has only a regular log entry, no motion/mutiny label
  const vault = makeVault(path.join(tmp, 'vault'), [
    {
      filename: '0001-rX-start.md',
      content: [
        '---',
        'type: log',
        'labels: [run]',
        'run-id: rX',
        '---',
        '2026-01-01T10:00:00Z · rX START',
      ].join('\n') + '\n',
    },
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('D1: exit 0 for empty ledger (no motion/mutiny entries)',
    result.status === 0,
    `got exit ${result.status}`);

  const combined = (result.stdout || '') + (result.stderr || '');
  assert('D2: RETALIATION-CLEAR emitted for empty ledger',
    /RETALIATION-CLEAR/.test(combined),
    `output: ${combined}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite E: Exit code EXACTLY 3 — a crash must NOT exit 3
//
//   Contract: "exit code EXACTLY 3 (distinct from 0=clean and 1=error so a
//   crash can't read as clean-or-conflict)"
//   Invoke with missing required args (no --target) → should crash/error, NOT exit 3.
// ---------------------------------------------------------------------------
console.log('\nSuite E: crash (missing required args) must NOT exit 3');
{
  const tmp = makeTmpDir('gate-rf-e-');
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });

  const result = runFlag(['--out', out]);  // no --target, no --voters

  assert('E1: missing required args produces non-zero exit',
    result.status !== 0,
    `got exit ${result.status} (should be nonzero error, not success)`);

  assert('E2: missing required args does NOT exit 3 (crash != conflict)',
    result.status !== 3,
    `got exit ${result.status} — a crash must not look like a CONFLICT`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite F: CONFLICT — worked example from contract spec
//   --target obs-2  --voters obs-1,council-skeptic
//   0040-mutiny.md  filed-by: obs-2 / against: council-skeptic → exit 3
// ---------------------------------------------------------------------------
console.log('\nSuite F: CONFLICT — contract worked example verbatim');
{
  const tmp  = makeTmpDir('gate-rf-f-');
  const out  = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  const vault = makeVault(path.join(tmp, 'vault'), [
    {
      filename: '0040-mutiny.md',
      content: [
        '---',
        'type: mutiny',
        'labels: [mutiny]',
        'filed-by: obs-2',
        'against: council-skeptic',
        '---',
        '# Worked example from contract',
      ].join('\n') + '\n',
    },
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('F1: contract worked example exits EXACTLY 3',
    result.status === 3,
    `got exit ${result.status}`);

  const flags = flagFiles(out);
  assert('F2: contract worked example produces a flag file',
    flags.length >= 1,
    `found ${flags.length}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\n${'='.repeat(60)}`);
console.log(`Conflict-detection fixtures: ${passed} passed, ${failed} failed.`);
if (failures.length > 0) {
  console.error('\nFailed assertions:');
  for (const f of failures) {
    console.error(`  FAIL  ${f.label}${f.detail ? ': ' + f.detail : ''}`);
  }
}
console.log('='.repeat(60));
process.exit(failed > 0 ? 1 : 0);
