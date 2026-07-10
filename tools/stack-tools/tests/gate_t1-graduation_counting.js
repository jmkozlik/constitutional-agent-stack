#!/usr/bin/env node
/**
 * gate_t1-graduation_counting.js
 *
 * Asserts the consecutive-counting and graduation logic of graduation.js.
 *
 * Covered behaviors (from contract interface spec):
 *   C1. Empty ledger  → all four classes: consecutive=0, graduated=false
 *   C2. Single positive decision (pruning) → consecutive=1, graduated=false (1<5)
 *   C3. Worked example from contract: APPROVED→VETOED→APPROVED for pruning
 *       → consecutive=1, graduated=false (reset by veto, then one approval)
 *   C4. pruning reaches threshold (5 consecutive) → graduated=true
 *   C5. mega-auth reaches threshold (10 consecutive) → graduated=true
 *   C6. steward-signoff reaches threshold (10 consecutive) → graduated=true
 *   C7. amendment reaches threshold (20 consecutive) → graduated=true
 *   C8. VETOED mid-stream resets counter; subsequent positives count fresh
 *   C9. REVERSED mid-stream resets counter (same semantics as VETOED)
 *   C10. Multiple classes counted independently in same ledger
 *   C11. Entries sorted by filename ascending (sort order determines sequence)
 *   C12. RATIFIED and SIGNED are also positive tokens (not just APPROVED)
 *   C13. Entry matching two power-class labels simultaneously is EXCLUDED
 *        (contract: "exactly one of" — ambiguous entries are not ledger entries)
 *   C14. Entry with no decision token (body has neither positive nor veto word)
 *        is ignored (not counted, not a reset)
 *   C15. Each class has hardcoded threshold in output: pruning=5, mega-auth=10,
 *        steward-signoff=10, amendment=20
 *
 * Run: node gate_t1-graduation_counting.js <path-to-graduation.js>
 */
'use strict';

const fs   = require('fs');
const path = require('path');
const os   = require('os');
const { spawnSync } = require('child_process');

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------
const GRADUATION_JS = process.argv[2];
if (!GRADUATION_JS) {
  console.error('Usage: node gate_t1-graduation_counting.js <path-to-graduation.js>');
  process.exit(2);
}
if (!fs.existsSync(GRADUATION_JS)) {
  console.error(`graduation.js not found at: ${GRADUATION_JS}`);
  process.exit(2);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a minimal synthetic vault with a ledger directory.
 * entries: array of { filename, labels, bodyToken }
 *   - filename: string (determines sort order)
 *   - labels: string[] — power-class labels to include in frontmatter
 *   - bodyToken: string|null — the decision token to put in the body line
 *                              (or null for no token)
 */
function buildVault(tmpBase, entries) {
  const vaultDir  = path.join(tmpBase, 'vault');
  const ledgerDir = path.join(vaultDir, 'ledger');
  fs.mkdirSync(ledgerDir, { recursive: true });

  for (const entry of entries) {
    const labelYaml = JSON.stringify(entry.labels); // e.g. ["pruning"]
    const body = entry.bodyToken
      ? `This is a MONARCH DECISION. ${entry.bodyToken} by god.\n`
      : `This is a note with no decision token.\n`;
    const content =
      `---\ntype: log\nlabels: ${labelYaml}\nstatus: final\n---\n${body}`;
    fs.writeFileSync(path.join(ledgerDir, entry.filename), content);
  }

  return vaultDir;
}

function runGraduation(vaultPath, outPath) {
  return spawnSync(process.execPath, [
    GRADUATION_JS,
    '--vault', vaultPath,
    '--out',   outPath,
  ], { encoding: 'utf8', timeout: 10000 });
}

function readOut(outPath) {
  try {
    return JSON.parse(fs.readFileSync(outPath, 'utf8'));
  } catch (e) {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Test runner
// ---------------------------------------------------------------------------
let passed = 0;
let failed = 0;

function assert(condition, label, detail) {
  if (condition) {
    console.log(`  PASS  ${label}`);
    passed++;
  } else {
    console.error(`  FAIL  ${label}${detail ? ' — ' + detail : ''}`);
    failed++;
  }
}

function assertClassState(out, cls, expectedConsecutive, expectedGraduated, label) {
  if (!out || !out[cls]) {
    assert(false, `${label} [${cls} present in output]`, `output: ${JSON.stringify(out)}`);
    return;
  }
  assert(
    out[cls].consecutive === expectedConsecutive,
    `${label} [${cls}.consecutive === ${expectedConsecutive}]`,
    `got ${out[cls].consecutive}`
  );
  assert(
    out[cls].graduated === expectedGraduated,
    `${label} [${cls}.graduated === ${expectedGraduated}]`,
    `got ${out[cls].graduated}`
  );
}

const ALL_CLASSES = ['pruning', 'mega-auth', 'steward-signoff', 'amendment'];
const THRESHOLDS  = { 'pruning': 5, 'mega-auth': 10, 'steward-signoff': 10, 'amendment': 20 };

// ---------------------------------------------------------------------------
// C1: Empty ledger → all four classes consecutive=0, graduated=false
// ---------------------------------------------------------------------------
console.log('\n--- C1: empty ledger ---');
{
  const tmp  = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c1-'));
  const vault = buildVault(tmp, []);
  const out   = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C1: exit 0 on empty ledger', `stderr: ${result.stderr}`);

  const data = readOut(out);
  assert(data !== null, 'C1: output file is valid JSON', `content: ${fs.existsSync(out) ? fs.readFileSync(out,'utf8') : 'file missing'}`);

  for (const cls of ALL_CLASSES) {
    assertClassState(data, cls, 0, false, 'C1');
  }

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C2: Single positive decision (pruning APPROVED) → consecutive=1, graduated=false
// ---------------------------------------------------------------------------
console.log('\n--- C2: single positive pruning decision ---');
{
  const tmp  = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c2-'));
  const vault = buildVault(tmp, [
    { filename: '0001-pruning-approved.md', labels: ['pruning'], bodyToken: 'APPROVED' },
  ]);
  const out = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C2: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  assertClassState(data, 'pruning', 1, false, 'C2');
  // Other classes untouched
  for (const cls of ['mega-auth', 'steward-signoff', 'amendment']) {
    assertClassState(data, cls, 0, false, 'C2-others');
  }

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C3: Contract worked example — APPROVED → VETOED → APPROVED for pruning
//     → consecutive=1, graduated=false
// ---------------------------------------------------------------------------
console.log('\n--- C3: contract worked example (APPROVED→VETOED→APPROVED) ---');
{
  const tmp  = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c3-'));
  const vault = buildVault(tmp, [
    { filename: '0030-x-pruning.md', labels: ['pruning'], bodyToken: 'APPROVED' },
    { filename: '0031-y-pruning.md', labels: ['pruning'], bodyToken: 'VETOED'   },
    { filename: '0032-z-pruning.md', labels: ['pruning'], bodyToken: 'APPROVED' },
  ]);
  const out = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C3: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  assertClassState(data, 'pruning', 1, false, 'C3');

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C4: pruning graduation (5 consecutive APPROVED)
// ---------------------------------------------------------------------------
console.log('\n--- C4: pruning graduation at threshold 5 ---');
{
  const tmp    = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c4-'));
  const entries = Array.from({ length: 5 }, (_, i) => ({
    filename:   `${String(i + 1).padStart(4, '0')}-pruning.md`,
    labels:     ['pruning'],
    bodyToken:  'APPROVED',
  }));
  const vault = buildVault(tmp, entries);
  const out   = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C4: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  assertClassState(data, 'pruning', 5, true, 'C4');

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C5: mega-auth graduation (10 consecutive RATIFIED)
// ---------------------------------------------------------------------------
console.log('\n--- C5: mega-auth graduation at threshold 10 ---');
{
  const tmp    = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c5-'));
  const entries = Array.from({ length: 10 }, (_, i) => ({
    filename:   `${String(i + 1).padStart(4, '0')}-mega-auth.md`,
    labels:     ['mega-auth'],
    bodyToken:  'RATIFIED',
  }));
  const vault = buildVault(tmp, entries);
  const out   = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C5: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  assertClassState(data, 'mega-auth', 10, true, 'C5');

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C6: steward-signoff graduation (10 consecutive SIGNED)
// ---------------------------------------------------------------------------
console.log('\n--- C6: steward-signoff graduation at threshold 10 ---');
{
  const tmp    = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c6-'));
  const entries = Array.from({ length: 10 }, (_, i) => ({
    filename:   `${String(i + 1).padStart(4, '0')}-ss.md`,
    labels:     ['steward-signoff'],
    bodyToken:  'SIGNED',
  }));
  const vault = buildVault(tmp, entries);
  const out   = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C6: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  assertClassState(data, 'steward-signoff', 10, true, 'C6');

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C7: amendment graduation (20 consecutive RATIFIED)
// ---------------------------------------------------------------------------
console.log('\n--- C7: amendment graduation at threshold 20 ---');
{
  const tmp    = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c7-'));
  const entries = Array.from({ length: 20 }, (_, i) => ({
    filename:   `${String(i + 1).padStart(4, '0')}-amendment.md`,
    labels:     ['amendment'],
    bodyToken:  'RATIFIED',
  }));
  const vault = buildVault(tmp, entries);
  const out   = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C7: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  assertClassState(data, 'amendment', 20, true, 'C7');

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C8: VETOED resets to 0 mid-stream (pruning: 4 approved → VETOED → 3 approved
//     → consecutive=3, graduated=false)
// ---------------------------------------------------------------------------
console.log('\n--- C8: VETOED resets counter mid-stream ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c8-'));
  const entries = [
    ...Array.from({ length: 4 }, (_, i) => ({
      filename:  `${String(i + 1).padStart(4, '0')}-pruning.md`,
      labels:    ['pruning'],
      bodyToken: 'APPROVED',
    })),
    { filename: '0005-pruning-veto.md', labels: ['pruning'], bodyToken: 'VETOED' },
    ...Array.from({ length: 3 }, (_, i) => ({
      filename:  `${String(i + 6).padStart(4, '0')}-pruning.md`,
      labels:    ['pruning'],
      bodyToken: 'APPROVED',
    })),
  ];
  const vault = buildVault(tmp, entries);
  const out   = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C8: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  assertClassState(data, 'pruning', 3, false, 'C8');

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C9: REVERSED resets counter (same semantics as VETOED)
//     pruning: 3 approved → REVERSED → 2 approved → consecutive=2, graduated=false
// ---------------------------------------------------------------------------
console.log('\n--- C9: REVERSED resets counter ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c9-'));
  const entries = [
    ...Array.from({ length: 3 }, (_, i) => ({
      filename:  `${String(i + 1).padStart(4, '0')}-pruning.md`,
      labels:    ['pruning'],
      bodyToken: 'APPROVED',
    })),
    { filename: '0004-pruning-reversed.md', labels: ['pruning'], bodyToken: 'REVERSED' },
    ...Array.from({ length: 2 }, (_, i) => ({
      filename:  `${String(i + 5).padStart(4, '0')}-pruning.md`,
      labels:    ['pruning'],
      bodyToken: 'APPROVED',
    })),
  ];
  const vault = buildVault(tmp, entries);
  const out   = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C9: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  assertClassState(data, 'pruning', 2, false, 'C9');

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C10: Multiple classes counted independently
//      - pruning: 3 × APPROVED → consecutive=3, graduated=false
//      - mega-auth: 10 × RATIFIED → consecutive=10, graduated=true
//      - steward-signoff: 0 decisions → consecutive=0, graduated=false
//      - amendment: 1 × SIGNED → consecutive=1, graduated=false
// ---------------------------------------------------------------------------
console.log('\n--- C10: multiple classes independent ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c10-'));
  const entries = [
    ...Array.from({ length: 3 }, (_, i) => ({
      filename:  `${String(i + 1).padStart(4, '0')}-pruning.md`,
      labels:    ['pruning'],
      bodyToken: 'APPROVED',
    })),
    ...Array.from({ length: 10 }, (_, i) => ({
      filename:  `${String(i + 10).padStart(4, '0')}-mega-auth.md`,
      labels:    ['mega-auth'],
      bodyToken: 'RATIFIED',
    })),
    { filename: '0025-amendment.md', labels: ['amendment'], bodyToken: 'SIGNED' },
  ];
  const vault = buildVault(tmp, entries);
  const out   = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C10: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  assertClassState(data, 'pruning',         3,  false, 'C10');
  assertClassState(data, 'mega-auth',        10, true,  'C10');
  assertClassState(data, 'steward-signoff',  0,  false, 'C10');
  assertClassState(data, 'amendment',        1,  false, 'C10');

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C11: Filename sort order determines sequence
//      Entry 0002 comes before 0001 alphabetically? No — ascending sort means
//      0001 < 0002. Test that an out-of-order insert doesn't fool the count:
//      file 0010-pruning (APPROVED) then 0009-pruning (VETOED) but sorted
//      lexicographically 0009 < 0010 → veto comes first → only 1 approval
// ---------------------------------------------------------------------------
console.log('\n--- C11: filename ascending sort order ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c11-'));
  // Write files out of insertion order; sort must produce: 0009-veto, 0010-approved
  const vault = buildVault(tmp, [
    { filename: '0010-pruning-approved.md', labels: ['pruning'], bodyToken: 'APPROVED' },
    { filename: '0009-pruning-vetoed.md',   labels: ['pruning'], bodyToken: 'VETOED'   },
  ]);
  const out = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C11: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  // 0009 (veto) → reset to 0; 0010 (approved) → 1. consecutive=1
  assertClassState(data, 'pruning', 1, false, 'C11');

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C12: RATIFIED and SIGNED are positive tokens (not just APPROVED)
// ---------------------------------------------------------------------------
console.log('\n--- C12: RATIFIED and SIGNED are positive tokens ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c12-'));
  const vault = buildVault(tmp, [
    { filename: '0001-pruning-ratified.md',   labels: ['pruning'],  bodyToken: 'RATIFIED' },
    { filename: '0002-mega-auth-signed.md',   labels: ['mega-auth'], bodyToken: 'SIGNED'  },
  ]);
  const out = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C12: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  assertClassState(data, 'pruning',   1, false, 'C12-RATIFIED');
  assertClassState(data, 'mega-auth', 1, false, 'C12-SIGNED');

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C13: Entry with TWO power-class labels is excluded (not exactly one)
//      Spec: "labels: contains exactly one of" — ambiguous entries are skipped
// ---------------------------------------------------------------------------
console.log('\n--- C13: entry with two power-class labels is excluded ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c13-'));
  const vault = buildVault(tmp, [
    // This entry has two power-class labels — must be excluded from counting
    { filename: '0001-dual-class.md', labels: ['pruning', 'mega-auth'], bodyToken: 'APPROVED' },
    // This entry has exactly one power-class label — must be counted
    { filename: '0002-pruning-only.md', labels: ['pruning'], bodyToken: 'APPROVED' },
  ]);
  const out = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C13: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  // Only 0002 counts: pruning=1, mega-auth=0
  assertClassState(data, 'pruning',   1, false, 'C13-pruning-exactly-one');
  assertClassState(data, 'mega-auth', 0, false, 'C13-mega-auth-excluded');

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C14: Entry with no decision token is ignored (not counted, not a reset)
//      pruning: APPROVED, [no-token], APPROVED → consecutive=2 (no reset)
// ---------------------------------------------------------------------------
console.log('\n--- C14: entry with no decision token is ignored ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c14-'));
  const vault = buildVault(tmp, [
    { filename: '0001-pruning-approved.md',  labels: ['pruning'], bodyToken: 'APPROVED' },
    { filename: '0002-pruning-no-token.md',  labels: ['pruning'], bodyToken: null       },
    { filename: '0003-pruning-approved2.md', labels: ['pruning'], bodyToken: 'APPROVED' },
  ]);
  const out = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C14: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  // 0002 has no token — ignored; counts: 0001 (+1), 0002 (ignored), 0003 (+1)
  assertClassState(data, 'pruning', 2, false, 'C14');

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C15: Hardcoded thresholds appear correctly in output JSON
// ---------------------------------------------------------------------------
console.log('\n--- C15: hardcoded thresholds in output ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c15-'));
  const vault = buildVault(tmp, []);
  const out   = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C15: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  for (const [cls, expected] of Object.entries(THRESHOLDS)) {
    assert(
      data && data[cls] && data[cls].threshold === expected,
      `C15: ${cls}.threshold === ${expected}`,
      `got ${data && data[cls] ? data[cls].threshold : 'missing'}`
    );
  }

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// C16: Stdout receives a one-line summary (non-empty), exit 0
// ---------------------------------------------------------------------------
console.log('\n--- C16: stdout summary line ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-c16-'));
  const vault = buildVault(tmp, [
    { filename: '0001-pruning.md', labels: ['pruning'], bodyToken: 'APPROVED' },
  ]);
  const out = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'C16: exit 0', `stderr: ${result.stderr}`);
  const lines = result.stdout.trim().split('\n').filter(l => l.trim().length > 0);
  assert(lines.length >= 1, 'C16: stdout has at least one non-empty line', `stdout: "${result.stdout}"`);

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\nCounting fixtures: ${passed} passed, ${failed} failed.`);
process.exit(failed > 0 ? 1 : 0);
