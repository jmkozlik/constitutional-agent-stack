#!/usr/bin/env node
/**
 * gate_t2-retaliation-flag_token-window-parse.js
 *
 * Gate fixtures for retaliation-flag.js — t2-retaliation-flag, run r004-regency.
 * Derived EXCLUSIVELY from the contract interface spec. No implementation code read.
 *
 * Behavior classes under test:
 *
 *   T. Whole-token matching — voter obs-1 must NOT match obs-10.
 *      (Substring evasion must be rejected.)
 *   W. Window bound — a filing older than --window is IGNORED.
 *      Seed 25 ledger entries; only entries 1-5 (outside newest-20 window)
 *      contain the voter match → result must be CLEAR (exit 0).
 *   P. Both parse forms in the same run:
 *        - one entry uses frontmatter filed-by/against
 *        - one entry uses body · filer: / · against: tokens
 *        Both must be detected as conflict individually.
 *   L. Labels filter — only entries labelled [motion] or [mutiny] are scanned.
 *      An entry labelled [log] with filed-by/against lines must be ignored.
 *   X. Default --window is 20: seed exactly 21 entries; the conflict is in
 *      entry 1 (oldest) → must be ignored without explicit --window flag.
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
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix || 'gate-rf-twp-'));
}

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

function flagFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter(f => f.endsWith('.flag.md'));
}

function cleanup(dir) {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch (_) {}
}

/** Pad n with leading zeros to width w */
function pad(n, w) { return String(n).padStart(w, '0'); }

/** Create a filler ledger entry (labeled [log], no filed-by/against). */
function fillerEntry(n) {
  return {
    filename: `${pad(n, 4)}-log.md`,
    content: [
      '---',
      'type: log',
      'labels: [run]',
      '---',
      `Run log entry ${n}.`,
    ].join('\n') + '\n',
  };
}

/** Create a motion entry with frontmatter filed-by/against. */
function motionEntry(n, filer, against) {
  return {
    filename: `${pad(n, 4)}-motion.md`,
    content: [
      '---',
      'type: motion',
      'labels: [motion]',
      `filed-by: ${filer}`,
      `against: ${against}`,
      '---',
      `# Motion by ${filer} against ${against}`,
    ].join('\n') + '\n',
  };
}

// ---------------------------------------------------------------------------
// Suite T: Whole-token matching — obs-1 must NOT match obs-10
//
//   voters: obs-1,council-skeptic
//   Ledger entry: filed-by: obs-2, against: obs-10  (NOT a voter; obs-1 is
//   a voter, but obs-10 is a different id; substring match would falsely flag)
//   Expected: exit 0, RETALIATION-CLEAR
// ---------------------------------------------------------------------------
console.log('\nSuite T: Whole-token matching — obs-1 voter must NOT match against obs-10');
{
  const tmp = makeTmpDir('gate-rf-t-');
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  const vault = makeVault(path.join(tmp, 'vault'), [
    motionEntry(40, 'obs-2', 'obs-10'),  // against obs-10, NOT obs-1
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',   // obs-1 is a voter; obs-10 is not
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('T1: exit 0 — obs-1 voter does NOT match against obs-10 (no substring)',
    result.status === 0,
    `got exit ${result.status} — a substring match would wrongly exit 3`);

  const combined = (result.stdout || '') + (result.stderr || '');
  assert('T2: RETALIATION-CLEAR when against=obs-10 and voter=obs-1',
    /RETALIATION-CLEAR/.test(combined),
    `output: ${combined}`);

  const flags = flagFiles(out);
  assert('T3: no flag file written (obs-10 is not obs-1)',
    flags.length === 0,
    `found ${flags.length}: ${flags.join(', ')}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite T2: Whole-token matching — obs-10 in voters, against=obs-1 → CLEAR
//
//   Complementary to T: obs-10 is a voter, filed against obs-1 (not a voter).
//   A substring match would wrongly treat obs-1 as matching obs-10.
// ---------------------------------------------------------------------------
console.log('\nSuite T2: Whole-token — obs-10 voter must NOT match against obs-1');
{
  const tmp = makeTmpDir('gate-rf-t2-');
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  const vault = makeVault(path.join(tmp, 'vault'), [
    motionEntry(40, 'obs-2', 'obs-1'),   // against obs-1
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-10,council-skeptic',  // obs-10 is a voter; obs-1 is not
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('T2-1: exit 0 — obs-10 voter does NOT match against obs-1 (no substring)',
    result.status === 0,
    `got exit ${result.status} — substring match would wrongly exit 3`);

  const flags = flagFiles(out);
  assert('T2-2: no flag file when against=obs-1 and voter is obs-10',
    flags.length === 0,
    `found ${flags.length}: ${flags.join(', ')}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite T3: Whole-token — exact match of obs-1 when obs-1 IS a voter → CONFLICT
//   Confirming that the token guard does NOT accidentally prevent a true positive.
// ---------------------------------------------------------------------------
console.log('\nSuite T3: Whole-token — exact match of obs-1 as voter → CONFLICT');
{
  const tmp = makeTmpDir('gate-rf-t3-');
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  const vault = makeVault(path.join(tmp, 'vault'), [
    motionEntry(40, 'obs-2', 'obs-1'),  // exact voter match
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',  // obs-1 IS a voter
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('T3-1: exit 3 — exact match of obs-1 as voter correctly triggers CONFLICT',
    result.status === 3,
    `got exit ${result.status}`);

  const flags = flagFiles(out);
  assert('T3-2: flag file written for exact voter match',
    flags.length >= 1,
    `found ${flags.length}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite W: Window bound — conflict is outside the window → CLEAR
//
//   Seed 25 ledger entries (numbered 0001-0025, sorted by filename).
//   The conflict entry is 0001-motion.md (oldest, outside newest-20 window).
//   Entries 0006-0025 are filler [log] entries.
//   With --window 20 (default), only entries 0006-0025 are scanned.
//   Expected: exit 0, RETALIATION-CLEAR.
// ---------------------------------------------------------------------------
console.log('\nSuite W: Window bound — conflict in oldest entry, outside newest-20 window → CLEAR');
{
  const tmp = makeTmpDir('gate-rf-w-');
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });

  // Build 25 entries: entry 1 is conflict, entries 2-25 are filler
  const entries = [];
  // Entry 1 (oldest): conflict motion — filed-by: obs-2, against: obs-1 (voter)
  entries.push(motionEntry(1, 'obs-2', 'obs-1'));
  // Entries 2-5: more filler motion/log entries (not conflict)
  for (let i = 2; i <= 5; i++) {
    entries.push(fillerEntry(i));
  }
  // Entries 6-25: filler log entries (newest 20 window)
  for (let i = 6; i <= 25; i++) {
    entries.push(fillerEntry(i));
  }

  const vault = makeVault(path.join(tmp, 'vault'), entries);

  // With default window of 20, only entries 6-25 are scanned; entry 1 is outside
  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
    // no --window; default is 20
  ]);

  assert('W1: exit 0 when conflict is outside default window of 20',
    result.status === 0,
    `got exit ${result.status} — entry 0001-motion.md should be excluded by window`);

  const combined = (result.stdout || '') + (result.stderr || '');
  assert('W2: RETALIATION-CLEAR when conflict is outside window',
    /RETALIATION-CLEAR/.test(combined),
    `output: ${combined}`);

  const flags = flagFiles(out);
  assert('W3: no flag file when conflict entry is outside window',
    flags.length === 0,
    `found ${flags.length}: ${flags.join(', ')}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite W2: Window bound — conflict is inside explicit --window N → CONFLICT
//
//   Same 25-entry vault. Now pass --window 25 to include all entries.
//   Entry 1 (conflict) is now within window → exit 3.
// ---------------------------------------------------------------------------
console.log('\nSuite W2: Window bound — conflict inside explicit --window 25 → CONFLICT');
{
  const tmp = makeTmpDir('gate-rf-w2-');
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });

  const entries = [];
  entries.push(motionEntry(1, 'obs-2', 'obs-1'));  // oldest, conflict
  for (let i = 2; i <= 25; i++) {
    entries.push(fillerEntry(i));
  }

  const vault = makeVault(path.join(tmp, 'vault'), entries);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
    '--window', '25',   // explicit window includes entry 1
  ]);

  assert('W2-1: exit 3 when conflict is within explicit --window 25',
    result.status === 3,
    `got exit ${result.status}`);

  const flags = flagFiles(out);
  assert('W2-2: flag file written when conflict is within explicit window',
    flags.length >= 1,
    `found ${flags.length}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite X: Default window is 20 — seed 21 entries; conflict is entry 1 (oldest)
//   Without --window flag, default 20 means entry 1 is excluded → CLEAR.
// ---------------------------------------------------------------------------
console.log('\nSuite X: Default --window 20 — conflict at entry 1 of 21 → outside default → CLEAR');
{
  const tmp = makeTmpDir('gate-rf-x-');
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });

  const entries = [];
  entries.push(motionEntry(1, 'obs-2', 'obs-1'));  // oldest; outside window of 20
  for (let i = 2; i <= 21; i++) {
    entries.push(fillerEntry(i));  // entries 2-21 are the newest 20
  }

  const vault = makeVault(path.join(tmp, 'vault'), entries);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
    // no --window; default must be 20
  ]);

  assert('X1: exit 0 — entry 1 of 21 excluded by default window of 20',
    result.status === 0,
    `got exit ${result.status}`);

  const flags = flagFiles(out);
  assert('X2: no flag file when conflict is entry 1 of 21 with default window',
    flags.length === 0,
    `found ${flags.length}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite P: Both parse forms in a single run — each form is a conflict alone
//
//   P1: frontmatter form (filed-by / against in frontmatter) → exit 3
//   P2: body token form (· filer: / · against: in body) → exit 3
//   P3: run with BOTH in ledger → still exit 3 (multiple conflicts)
// ---------------------------------------------------------------------------
console.log('\nSuite P: Both parse forms — frontmatter and body tokens each cause CONFLICT');

// P1: frontmatter only
{
  const tmp = makeTmpDir('gate-rf-p1-');
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  const vault = makeVault(path.join(tmp, 'vault'), [
    {
      filename: '0040-mutiny.md',
      content: [
        '---',
        'type: mutiny',
        'labels: [mutiny]',
        'filed-by: obs-2',
        'against: obs-1',
        '---',
        '# Frontmatter parse form',
      ].join('\n') + '\n',
    },
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('P1-1: exit 3 using frontmatter filed-by/against form',
    result.status === 3,
    `got exit ${result.status}`);

  const flags = flagFiles(out);
  assert('P1-2: flag file written (frontmatter form)',
    flags.length >= 1,
    `found ${flags.length}`);

  cleanup(tmp);
}

// P2: body token form only
{
  const tmp = makeTmpDir('gate-rf-p2-');
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  const vault = makeVault(path.join(tmp, 'vault'), [
    {
      filename: '0041-motion.md',
      content: [
        '---',
        'type: motion',
        'labels: [motion]',
        '---',
        '# Body token parse form',
        '· filer: obs-2',
        '· against: obs-1',
        'Evidential content.',
      ].join('\n') + '\n',
    },
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('P2-1: exit 3 using body · filer: / · against: token form',
    result.status === 3,
    `got exit ${result.status}`);

  const flags = flagFiles(out);
  assert('P2-2: flag file written (body token form)',
    flags.length >= 1,
    `found ${flags.length}`);

  cleanup(tmp);
}

// P3: both forms present in same ledger
{
  const tmp = makeTmpDir('gate-rf-p3-');
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  const vault = makeVault(path.join(tmp, 'vault'), [
    {
      filename: '0040-mutiny.md',
      content: [
        '---',
        'type: mutiny',
        'labels: [mutiny]',
        'filed-by: obs-2',
        'against: obs-1',
        '---',
        '# Frontmatter form entry',
      ].join('\n') + '\n',
    },
    {
      filename: '0041-motion.md',
      content: [
        '---',
        'type: motion',
        'labels: [motion]',
        '---',
        '# Body token form entry',
        '· filer: obs-2',
        '· against: council-skeptic',
        'More evidence.',
      ].join('\n') + '\n',
    },
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('P3-1: exit 3 when both frontmatter and body-token conflicts present',
    result.status === 3,
    `got exit ${result.status}`);

  const flags = flagFiles(out);
  assert('P3-2: flag file written listing both conflicting entries',
    flags.length >= 1,
    `found ${flags.length}`);

  if (flags.length >= 1) {
    const content = fs.readFileSync(path.join(out, flags[0]), 'utf8');
    assert('P3-3: flag file mentions both conflicting entry filenames',
      content.includes('0040-mutiny.md') && content.includes('0041-motion.md'),
      `flag content: ${content}`);
  }

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite L: Labels filter — only [motion] or [mutiny] entries are scanned
//
//   A [log] entry with filed-by/against lines must NOT be picked up.
// ---------------------------------------------------------------------------
console.log('\nSuite L: Labels filter — [log] entry with filed-by/against must be ignored');
{
  const tmp = makeTmpDir('gate-rf-l-');
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  const vault = makeVault(path.join(tmp, 'vault'), [
    {
      filename: '0040-log.md',
      content: [
        '---',
        'type: log',
        'labels: [log]',          // NOT motion or mutiny
        'filed-by: obs-2',
        'against: obs-1',
        '---',
        '# This is a log entry, not a motion or mutiny',
        '· filer: obs-2',         // body tokens too — still should be ignored
        '· against: obs-1',
      ].join('\n') + '\n',
    },
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,council-skeptic',
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('L1: exit 0 — [log] entry with filed-by/against must be ignored (wrong label)',
    result.status === 0,
    `got exit ${result.status} — log entries must not be scanned`);

  const combined = (result.stdout || '') + (result.stderr || '');
  assert('L2: RETALIATION-CLEAR when only [log] entries present',
    /RETALIATION-CLEAR/.test(combined),
    `output: ${combined}`);

  const flags = flagFiles(out);
  assert('L3: no flag file for [log] entry',
    flags.length === 0,
    `found ${flags.length}: ${flags.join(', ')}`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite I: Case-insensitive matching on voter ids
//
//   Contract: "case-insensitive, whole-token" matching for against vs voters.
//   Voter: Council-Skeptic (mixed case in --voters)
//   Entry: against: council-skeptic (lower case)
//   Expected: exit 3 (case-insensitive match)
// ---------------------------------------------------------------------------
console.log('\nSuite I: Case-insensitive voter id matching');
{
  const tmp = makeTmpDir('gate-rf-i-');
  const out = path.join(tmp, 'out');
  fs.mkdirSync(out, { recursive: true });
  const vault = makeVault(path.join(tmp, 'vault'), [
    motionEntry(40, 'obs-2', 'council-skeptic'),  // lower case "against"
  ]);

  const result = runFlag([
    '--target', 'obs-2',
    '--voters', 'obs-1,Council-Skeptic',   // mixed case voter
    '--vault',  vault,
    '--out',    out,
  ]);

  assert('I1: exit 3 — case-insensitive match for voter id',
    result.status === 3,
    `got exit ${result.status} — case-insensitive match should trigger`);

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\n${'='.repeat(60)}`);
console.log(`Token/window/parse fixtures: ${passed} passed, ${failed} failed.`);
if (failures.length > 0) {
  console.error('\nFailed assertions:');
  for (const f of failures) {
    console.error(`  FAIL  ${f.label}${f.detail ? ': ' + f.detail : ''}`);
  }
}
console.log('='.repeat(60));
process.exit(failed > 0 ? 1 : 0);
