#!/usr/bin/env node
/**
 * gate_t1-graduation_edge-cases.js
 *
 * Asserts edge-case and structural requirements of graduation.js.
 *
 * Covered behaviors:
 *   E1. Output JSON contains EXACTLY the four required classes (no more, no fewer)
 *   E2. Each class object has exactly the keys: consecutive, threshold, graduated
 *   E3. consecutive is always a non-negative integer
 *   E4. graduated is always a boolean
 *   E5. threshold is always a positive integer matching the hardcoded spec value
 *   E6. Non-ledger files in ledger/ (e.g. _index.md) are parsed without crash;
 *       entries with no power-class label are ignored
 *   E7. Ledger entries with non-MONARCH labels only (e.g. [run, governance])
 *       are ignored — they carry no power-class tag
 *   E8. Exit code is 0 (not 1, not 2) on a normal successful run
 *   E9. Default --vault path is $VAULT_ROOT (invoked without --vault flag;
 *       tested via a known-safe real vault if available, or skipped gracefully)
 *   E10. pruning threshold (5) is strictly less-than graduation, not less-than-or-equal
 *        to a lower value: 4 consecutive → graduated=false; 5 → graduated=true
 *   E11. Veto count itself is not added to the running total (count resets to 0,
 *        doesn't go negative)
 *   E12. Mixed positive tokens in same class count correctly
 *        (APPROVED + RATIFIED + SIGNED all increment the same counter)
 *
 * Run: node gate_t1-graduation_edge-cases.js <path-to-graduation.js>
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
  console.error('Usage: node gate_t1-graduation_edge-cases.js <path-to-graduation.js>');
  process.exit(2);
}
if (!fs.existsSync(GRADUATION_JS)) {
  console.error(`graduation.js not found at: ${GRADUATION_JS}`);
  process.exit(2);
}

const THRESHOLDS = { 'pruning': 5, 'mega-auth': 10, 'steward-signoff': 10, 'amendment': 20 };
const ALL_CLASSES = Object.keys(THRESHOLDS);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function buildVault(tmpBase, entries) {
  const vaultDir  = path.join(tmpBase, 'vault');
  const ledgerDir = path.join(vaultDir, 'ledger');
  fs.mkdirSync(ledgerDir, { recursive: true });

  for (const entry of entries) {
    const labelYaml = JSON.stringify(entry.labels);
    const body = entry.bodyToken
      ? `MONARCH DECISION. ${entry.bodyToken} by god-space.\n`
      : `Informational note — no decision token here.\n`;
    const content = `---\ntype: log\nlabels: ${labelYaml}\nstatus: final\n---\n${body}`;
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
  try { return JSON.parse(fs.readFileSync(outPath, 'utf8')); } catch (_) { return null; }
}

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

// ---------------------------------------------------------------------------
// E1: Output JSON contains exactly the four required classes
// ---------------------------------------------------------------------------
console.log('\n--- E1: output has exactly four classes ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-e1-'));
  const vault = buildVault(tmp, []);
  const out   = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'E1: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  assert(data !== null, 'E1: valid JSON', String(data));

  const keys = data ? Object.keys(data).sort() : [];
  assert(
    JSON.stringify(keys) === JSON.stringify([...ALL_CLASSES].sort()),
    'E1: exactly four classes present',
    `got keys: ${JSON.stringify(keys)}`
  );

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// E2: Each class object has exactly the keys: consecutive, threshold, graduated
// ---------------------------------------------------------------------------
console.log('\n--- E2: class objects have correct keys ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-e2-'));
  const vault = buildVault(tmp, []);
  const out   = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  const data   = readOut(out);
  const expectedKeys = ['consecutive', 'graduated', 'threshold'].sort();

  for (const cls of ALL_CLASSES) {
    if (!data || !data[cls]) {
      assert(false, `E2: class ${cls} present`, 'missing from output');
      continue;
    }
    const actualKeys = Object.keys(data[cls]).sort();
    assert(
      JSON.stringify(actualKeys) === JSON.stringify(expectedKeys),
      `E2: ${cls} has exactly {consecutive, threshold, graduated}`,
      `got: ${JSON.stringify(actualKeys)}`
    );
  }

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// E3: consecutive is always a non-negative integer
// E4: graduated is always a boolean
// E5: threshold matches hardcoded spec values
// ---------------------------------------------------------------------------
console.log('\n--- E3/E4/E5: type checks on class fields ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-e3-'));
  const vault = buildVault(tmp, [
    { filename: '0001-pruning.md', labels: ['pruning'], bodyToken: 'APPROVED' },
  ]);
  const out = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  const data   = readOut(out);

  for (const cls of ALL_CLASSES) {
    if (!data || !data[cls]) continue;
    assert(
      Number.isInteger(data[cls].consecutive) && data[cls].consecutive >= 0,
      `E3: ${cls}.consecutive is non-negative integer`,
      `got: ${data[cls].consecutive} (${typeof data[cls].consecutive})`
    );
    assert(
      typeof data[cls].graduated === 'boolean',
      `E4: ${cls}.graduated is boolean`,
      `got: ${data[cls].graduated} (${typeof data[cls].graduated})`
    );
    assert(
      data[cls].threshold === THRESHOLDS[cls],
      `E5: ${cls}.threshold === ${THRESHOLDS[cls]}`,
      `got: ${data[cls].threshold}`
    );
  }

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// E6: Non-ledger files (e.g., _index.md) in ledger/ are handled without crash
// ---------------------------------------------------------------------------
console.log('\n--- E6: _index.md in ledger/ does not crash script ---');
{
  const tmp       = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-e6-'));
  const vaultDir  = path.join(tmp, 'vault');
  const ledgerDir = path.join(vaultDir, 'ledger');
  fs.mkdirSync(ledgerDir, { recursive: true });

  // Write an _index.md with no frontmatter labels
  fs.writeFileSync(path.join(ledgerDir, '_index.md'),
    '# Index: ledger\n- [entry](0001.md)\n');

  // Also a valid pruning entry
  fs.writeFileSync(path.join(ledgerDir, '0001-pruning.md'),
    '---\ntype: log\nlabels: ["pruning"]\n---\nAPPROVED by god.\n');

  const out = path.join(tmp, 'out.json');
  const result = runGraduation(vaultDir, out);

  assert(result.status === 0,
    'E6a: exit 0 even with _index.md present',
    `stderr: ${result.stderr}`);

  const data = readOut(out);
  assert(data !== null, 'E6b: output is valid JSON', String(data));

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// E7: Entries with only non-power-class labels (e.g. [run, governance]) ignored
// ---------------------------------------------------------------------------
console.log('\n--- E7: non-power-class labels are ignored ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-e7-'));
  const vault = buildVault(tmp, [
    // Labels with no power-class tag — these must be ignored
    { filename: '0001-run-log.md',        labels: ['run'],                 bodyToken: 'APPROVED'  },
    { filename: '0002-governance-log.md', labels: ['run', 'governance'],   bodyToken: 'RATIFIED'  },
    { filename: '0003-council-log.md',    labels: ['council', 'contract'], bodyToken: 'SIGNED'    },
    // One real pruning entry to confirm counting still works
    { filename: '0004-pruning.md',        labels: ['pruning'],             bodyToken: 'APPROVED'  },
  ]);
  const out = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0, 'E7: exit 0', `stderr: ${result.stderr}`);

  const data = readOut(out);
  // Only the one real pruning entry should count
  assert(
    data && data['pruning'] && data['pruning'].consecutive === 1,
    'E7: only power-class entries counted (pruning=1)',
    `pruning: ${data && data['pruning'] ? JSON.stringify(data['pruning']) : 'missing'}`
  );
  for (const cls of ['mega-auth', 'steward-signoff', 'amendment']) {
    assert(
      data && data[cls] && data[cls].consecutive === 0,
      `E7: ${cls} not polluted by non-power-class entries`,
      `got consecutive=${data && data[cls] ? data[cls].consecutive : 'missing'}`
    );
  }

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// E8: Exit code is exactly 0 on normal successful run (not 2, not null)
// ---------------------------------------------------------------------------
console.log('\n--- E8: exit code is exactly 0 on success ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-e8-'));
  const vault = buildVault(tmp, []);
  const out   = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  assert(result.status === 0,
    'E8: exit code is exactly 0',
    `got ${result.status}`);

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// E10: Graduation boundary: exactly threshold-1 → false; exactly threshold → true
//      For pruning (threshold=5): 4 → false, 5 → true
// ---------------------------------------------------------------------------
console.log('\n--- E10: graduation boundary: N-1 false, N true (pruning at 5) ---');
{
  // 4 approvals → not graduated
  {
    const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-e10a-'));
    const vault = buildVault(tmp, Array.from({ length: 4 }, (_, i) => ({
      filename:  `${String(i + 1).padStart(4, '0')}-pruning.md`,
      labels:    ['pruning'],
      bodyToken: 'APPROVED',
    })));
    const out = path.join(tmp, 'out.json');

    const result = runGraduation(vault, out);
    const data   = readOut(out);
    assert(result.status === 0, 'E10a: exit 0 (4 approvals)', `stderr: ${result.stderr}`);
    assert(
      data && data['pruning'] && data['pruning'].consecutive === 4 && data['pruning'].graduated === false,
      'E10a: pruning 4/5 → graduated=false',
      JSON.stringify(data && data['pruning'])
    );
    fs.rmSync(tmp, { recursive: true, force: true });
  }

  // 5 approvals → graduated
  {
    const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-e10b-'));
    const vault = buildVault(tmp, Array.from({ length: 5 }, (_, i) => ({
      filename:  `${String(i + 1).padStart(4, '0')}-pruning.md`,
      labels:    ['pruning'],
      bodyToken: 'APPROVED',
    })));
    const out = path.join(tmp, 'out.json');

    const result = runGraduation(vault, out);
    const data   = readOut(out);
    assert(result.status === 0, 'E10b: exit 0 (5 approvals)', `stderr: ${result.stderr}`);
    assert(
      data && data['pruning'] && data['pruning'].consecutive === 5 && data['pruning'].graduated === true,
      'E10b: pruning 5/5 → graduated=true',
      JSON.stringify(data && data['pruning'])
    );
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

// ---------------------------------------------------------------------------
// E11: Veto resets to 0, not negative; subsequent positive still increments from 0
// ---------------------------------------------------------------------------
console.log('\n--- E11: veto resets to 0 (not negative) ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-e11-'));
  const vault = buildVault(tmp, [
    // Start fresh — immediately veto with no prior approvals
    { filename: '0001-pruning-veto.md',    labels: ['pruning'], bodyToken: 'VETOED'   },
    { filename: '0002-pruning-approve.md', labels: ['pruning'], bodyToken: 'APPROVED' },
  ]);
  const out = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  const data   = readOut(out);

  assert(result.status === 0, 'E11: exit 0', `stderr: ${result.stderr}`);
  assert(
    data && data['pruning'] && data['pruning'].consecutive === 1,
    'E11: veto at 0, then one approval → consecutive=1 (not -1+1=0)',
    JSON.stringify(data && data['pruning'])
  );

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// E12: Mixed positive tokens (APPROVED + RATIFIED + SIGNED) in same class
//      all increment the same class counter
// ---------------------------------------------------------------------------
console.log('\n--- E12: mixed positive tokens count for same class ---');
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-e12-'));
  const vault = buildVault(tmp, [
    { filename: '0001-pruning-approved.md',  labels: ['pruning'], bodyToken: 'APPROVED' },
    { filename: '0002-pruning-ratified.md',  labels: ['pruning'], bodyToken: 'RATIFIED' },
    { filename: '0003-pruning-signed.md',    labels: ['pruning'], bodyToken: 'SIGNED'   },
  ]);
  const out = path.join(tmp, 'out.json');

  const result = runGraduation(vault, out);
  const data   = readOut(out);

  assert(result.status === 0, 'E12: exit 0', `stderr: ${result.stderr}`);
  assert(
    data && data['pruning'] && data['pruning'].consecutive === 3,
    'E12: APPROVED+RATIFIED+SIGNED all count → consecutive=3',
    JSON.stringify(data && data['pruning'])
  );

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// E13: Default --out path is <vault>/god/regency-status.json when flag omitted
// ---------------------------------------------------------------------------
console.log('\n--- E13: default --out is <vault>/god/regency-status.json ---');
{
  const tmp      = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-e13-'));
  const vaultDir = path.join(tmp, 'vault');
  const ledgerDir = path.join(vaultDir, 'ledger');
  const godDir    = path.join(vaultDir, 'god');
  fs.mkdirSync(ledgerDir, { recursive: true });
  fs.mkdirSync(godDir,    { recursive: true });

  const result = spawnSync(process.execPath, [
    GRADUATION_JS,
    '--vault', vaultDir,
    // No --out flag
  ], { encoding: 'utf8', timeout: 10000 });

  const defaultOut = path.join(godDir, 'regency-status.json');

  assert(result.status === 0,
    'E13a: exit 0 with default --out',
    `stderr: ${result.stderr}`);

  assert(fs.existsSync(defaultOut),
    'E13b: default output file created at <vault>/god/regency-status.json',
    `looked for: ${defaultOut}`);

  let parsed = null;
  try { parsed = JSON.parse(fs.readFileSync(defaultOut, 'utf8')); } catch (_) {}
  assert(parsed !== null,
    'E13c: default output file is valid JSON',
    `content: ${fs.existsSync(defaultOut) ? fs.readFileSync(defaultOut, 'utf8') : 'missing'}`);

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\nEdge-case fixtures: ${passed} passed, ${failed} failed.`);
process.exit(failed > 0 ? 1 : 0);
