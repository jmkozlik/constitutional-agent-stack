#!/usr/bin/env node
/**
 * gate_t2-leak-linter_behaviors.js
 * Gate fixtures for leak-linter.js — t2-leak-linter, run r003-stack-tools.
 *
 * Derived exclusively from the contract interface spec (t2-leak-linter.md).
 * Barred from reading any implementation worktree.
 *
 * Behavior classes under test:
 *   A. Shadow-dimension name hit  → exit 2, flag file written citing term+line
 *   B. Threshold/weight pattern hit → exit 2, flag file written citing term+line
 *   C. Combined hit (worked example from contract) → exit 2, flag file written
 *   D. Clean artifact              → exit 0, stdout contains "LEAK-LINT CLEAN"
 *   E. Write-guard: flags-dir is a symlink → abort (non-zero, NOT 2)
 *   F. Write-guard: flags-dir exists as a non-directory file → abort (non-zero, NOT 2)
 *   G. Crash/exit-1 must NOT be mistaken for flagged (exit code == 2 strictly)
 *
 * Invocation: node gate_t2-leak-linter_behaviors.js [path-to-leak-linter.js]
 * Default linter path: ./leak-linter.js
 *
 * Exit codes:
 *   0 — all assertions passed
 *   1 — one or more assertions failed
 */

'use strict';

const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const LINTER = path.resolve(process.argv[2] || path.join(__dirname, 'leak-linter.js'));
const PASS = '✓';
const FAIL = '✗';

let passed = 0;
let failed = 0;
const failures = [];

function assert(label, condition, detail) {
  if (condition) {
    console.log(`  ${PASS}  ${label}`);
    passed++;
  } else {
    console.error(`  ${FAIL}  ${label}${detail ? ' — ' + detail : ''}`);
    failed++;
    failures.push({ label, detail });
  }
}

function makeTmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'gate-leak-linter-'));
}

function writeArtifact(dir, filename, content) {
  const p = path.join(dir, filename);
  fs.writeFileSync(p, content, 'utf8');
  return p;
}

function runLinter(artifactPath, flagsDir) {
  const args = [LINTER, artifactPath];
  if (flagsDir !== undefined) {
    args.push('--flags-dir', flagsDir);
  }
  const result = spawnSync(process.execPath, args, { encoding: 'utf8', timeout: 10000 });
  return result;
}

function findFlagFiles(flagsDir) {
  if (!fs.existsSync(flagsDir)) return [];
  return fs.readdirSync(flagsDir).filter(f => f.endsWith('.flag.md'));
}

function readFlagFile(flagsDir) {
  const files = findFlagFiles(flagsDir);
  if (files.length === 0) return null;
  return fs.readFileSync(path.join(flagsDir, files[0]), 'utf8');
}

function cleanup(dir) {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch (_) {}
}

// ---------------------------------------------------------------------------
// Suite A: shadow-dimension term hit — "unanimity"
// ---------------------------------------------------------------------------
console.log('\nSuite A: shadow-dimension term hit (unanimity)');
{
  const tmp = makeTmpDir();
  const flagsDir = path.join(tmp, 'flags');
  fs.mkdirSync(flagsDir);
  const artifact = writeArtifact(tmp, 'artifact-a.md', [
    'This artifact discusses coordination.',
    'We require unanimity among reviewers.',
    'No numeric thresholds here.',
  ].join('\n'));

  const result = runLinter(artifact, flagsDir);

  assert(
    'A1: exit code is exactly 2 on shadow-term hit',
    result.status === 2,
    `got ${result.status}`
  );

  const flagFiles = findFlagFiles(flagsDir);
  assert(
    'A2: exactly one flag file written',
    flagFiles.length === 1,
    `found ${flagFiles.length} flag files: ${flagFiles.join(', ')}`
  );

  const flagContent = readFlagFile(flagsDir);
  assert(
    'A3: flag file contains the matched term "unanimity"',
    flagContent !== null && /unanimity/i.test(flagContent),
    `flag content: ${flagContent}`
  );

  assert(
    'A4: flag file contains a line number',
    flagContent !== null && /line\s*[:#]?\s*\d+/i.test(flagContent),
    `flag content: ${flagContent}`
  );

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite B: threshold pattern hit — "score > 0.8"
// ---------------------------------------------------------------------------
console.log('\nSuite B: threshold/weight pattern hit (score > 0.8)');
{
  const tmp = makeTmpDir();
  const flagsDir = path.join(tmp, 'flags');
  fs.mkdirSync(flagsDir);
  const artifact = writeArtifact(tmp, 'artifact-b.md', [
    'Evaluation notes.',
    'Promote if score > 0.8 is achieved.',
    'Otherwise hold.',
  ].join('\n'));

  const result = runLinter(artifact, flagsDir);

  assert(
    'B1: exit code is exactly 2 on threshold-pattern hit',
    result.status === 2,
    `got ${result.status}`
  );

  const flagFiles = findFlagFiles(flagsDir);
  assert(
    'B2: flag file written for threshold pattern',
    flagFiles.length >= 1,
    `found ${flagFiles.length} flag files`
  );

  const flagContent = readFlagFile(flagsDir);
  assert(
    'B3: flag file mentions the line number of the hit',
    flagContent !== null && /line\s*[:#]?\s*\d+/i.test(flagContent),
    `flag content: ${flagContent}`
  );

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite C: combined hit — worked example from contract
//   "promote if unanimity > 0.8"
//   Expects: term "unanimity" cited AND threshold pattern cited, exit 2
// ---------------------------------------------------------------------------
console.log('\nSuite C: combined hit — worked example (unanimity > 0.8)');
{
  const tmp = makeTmpDir();
  const flagsDir = path.join(tmp, 'flags');
  fs.mkdirSync(flagsDir);
  const artifact = writeArtifact(tmp, 'artifact-c.md', [
    'Summary of run r001.',
    'promote if unanimity > 0.8',
    'All other conditions nominal.',
  ].join('\n'));

  const result = runLinter(artifact, flagsDir);

  assert(
    'C1: exit code is exactly 2',
    result.status === 2,
    `got ${result.status}`
  );

  const flagFiles = findFlagFiles(flagsDir);
  assert(
    'C2: at least one flag file written',
    flagFiles.length >= 1,
    `found ${flagFiles.length}`
  );

  const flagContent = readFlagFile(flagsDir);
  assert(
    'C3: flag content cites "unanimity"',
    flagContent !== null && /unanimity/i.test(flagContent),
    `flag content: ${flagContent}`
  );

  assert(
    'C4: flag content cites threshold/score pattern hit',
    flagContent !== null && /(score|threshold|0\.8|>)/i.test(flagContent),
    `flag content: ${flagContent}`
  );

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite D: clean artifact
// ---------------------------------------------------------------------------
console.log('\nSuite D: clean artifact (no leak terms)');
{
  const tmp = makeTmpDir();
  const flagsDir = path.join(tmp, 'flags');
  fs.mkdirSync(flagsDir);
  const artifact = writeArtifact(tmp, 'artifact-d.md', [
    'This skill summarizes recent runs.',
    'It does not mention any forbidden terms.',
    'All content is operational and safe to promote.',
    'Discussion covers scheduling, retries, and heartbeat intervals.',
  ].join('\n'));

  const result = runLinter(artifact, flagsDir);

  assert(
    'D1: exit code is 0 for clean artifact',
    result.status === 0,
    `got ${result.status}`
  );

  const combined = (result.stdout || '') + (result.stderr || '');
  assert(
    'D2: stdout contains "LEAK-LINT CLEAN"',
    /LEAK-LINT CLEAN/i.test(combined),
    `stdout: ${result.stdout} | stderr: ${result.stderr}`
  );

  const flagFiles = findFlagFiles(flagsDir);
  assert(
    'D3: no flag files written for clean artifact',
    flagFiles.length === 0,
    `found ${flagFiles.length} flag files: ${flagFiles.join(', ')}`
  );

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite E: write-guard — flags-dir is a symlink (must refuse to write)
// ---------------------------------------------------------------------------
console.log('\nSuite E: write-guard — flags-dir is a symlink');
{
  const tmp = makeTmpDir();
  const realDir = path.join(tmp, 'real-target');
  fs.mkdirSync(realDir);
  const symlinkPath = path.join(tmp, 'symlink-flags');
  fs.symlinkSync(realDir, symlinkPath);

  const artifact = writeArtifact(tmp, 'artifact-e.md', [
    'promote if unanimity > 0.8',
  ].join('\n'));

  const result = runLinter(artifact, symlinkPath);

  assert(
    'E1: linter aborts (non-zero exit) when flags-dir is a symlink',
    result.status !== 0,
    `got exit code ${result.status}`
  );

  assert(
    'E2: linter does NOT exit 2 (symlink-abort must not be mistaken for a flag hit)',
    result.status !== 2,
    `got exit code ${result.status} — should be non-zero and non-2`
  );

  // No flag file should have been written to the symlink target either
  const flagsInReal = fs.readdirSync(realDir).filter(f => f.endsWith('.flag.md'));
  assert(
    'E3: no flag files written through the symlink to the real target',
    flagsInReal.length === 0,
    `found files in symlink target: ${flagsInReal.join(', ')}`
  );

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite F: write-guard — flags-dir path exists as a regular file (non-dir)
// ---------------------------------------------------------------------------
console.log('\nSuite F: write-guard — flags-dir is a regular file (not a directory)');
{
  const tmp = makeTmpDir();
  const notADir = path.join(tmp, 'not-a-dir');
  fs.writeFileSync(notADir, 'i am a file, not a directory\n', 'utf8');

  const artifact = writeArtifact(tmp, 'artifact-f.md', [
    'governance-heat reading elevated.',
  ].join('\n'));

  const result = runLinter(artifact, notADir);

  assert(
    'F1: linter aborts (non-zero exit) when flags-dir is a regular file',
    result.status !== 0,
    `got exit code ${result.status}`
  );

  assert(
    'F2: exit code is not 2 (non-dir abort must not be mistaken for a flag hit)',
    result.status !== 2,
    `got exit code ${result.status} — should be non-zero and non-2`
  );

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite G: crash-not-flagged contract — a nonexistent artifact must NOT
//          produce exit 2 (no such file → crash/error, not "flagged")
// ---------------------------------------------------------------------------
console.log('\nSuite G: crash/error must NOT exit with code 2');
{
  const tmp = makeTmpDir();
  const flagsDir = path.join(tmp, 'flags');
  fs.mkdirSync(flagsDir);
  const nonExistentArtifact = path.join(tmp, 'does-not-exist.md');

  const result = runLinter(nonExistentArtifact, flagsDir);

  assert(
    'G1: exit code is not 2 when artifact does not exist (crash != flagged)',
    result.status !== 2,
    `got exit code ${result.status} — a missing-file error must not look like a flag hit`
  );

  const flagFiles = findFlagFiles(flagsDir);
  assert(
    'G2: no flag file written when artifact does not exist',
    flagFiles.length === 0,
    `found ${flagFiles.length} flag files`
  );

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite H: additional shadow-dimension terms from spec
//   governance-heat, rehydration-dip, tokens-per-task
// ---------------------------------------------------------------------------
console.log('\nSuite H: additional shadow-dimension terms (governance-heat, rehydration-dip, tokens-per-task)');

const additionalTerms = [
  { term: 'governance-heat', line: 'The governance-heat reading was elevated today.' },
  { term: 'rehydration-dip', line: 'A rehydration-dip was observed in task output.' },
  { term: 'tokens-per-task', line: 'Tracking tokens-per-task across all runs.' },
];

for (const { term, line } of additionalTerms) {
  const tmp = makeTmpDir();
  const flagsDir = path.join(tmp, 'flags');
  fs.mkdirSync(flagsDir);
  const artifact = writeArtifact(tmp, `artifact-${term}.md`, [
    'Preamble line.',
    line,
    'Postamble line.',
  ].join('\n'));

  const result = runLinter(artifact, flagsDir);

  assert(
    `H-${term}: exit 2 on shadow term "${term}"`,
    result.status === 2,
    `got ${result.status}`
  );

  const flagContent = readFlagFile(flagsDir);
  assert(
    `H-${term}: flag content cites term "${term}"`,
    flagContent !== null && new RegExp(term, 'i').test(flagContent),
    `flag content: ${flagContent}`
  );

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite I: flag file basename derived from artifact basename (naming contract)
// ---------------------------------------------------------------------------
console.log('\nSuite I: flag file basename contains artifact basename');
{
  const tmp = makeTmpDir();
  const flagsDir = path.join(tmp, 'flags');
  fs.mkdirSync(flagsDir);
  const artifact = writeArtifact(tmp, 'my-special-skill.md', [
    'weight: 0.7',
  ].join('\n'));

  const result = runLinter(artifact, flagsDir);

  assert(
    'I1: exit 2 on weight pattern',
    result.status === 2,
    `got ${result.status}`
  );

  const flagFiles = findFlagFiles(flagsDir);
  assert(
    'I2: flag file name includes artifact basename "my-special-skill"',
    flagFiles.some(f => f.includes('my-special-skill')),
    `flag files: ${flagFiles.join(', ')}`
  );

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Suite J: case-insensitivity — "UNANIMITY" upper-case must be caught
// ---------------------------------------------------------------------------
console.log('\nSuite J: case-insensitive matching for shadow terms');
{
  const tmp = makeTmpDir();
  const flagsDir = path.join(tmp, 'flags');
  fs.mkdirSync(flagsDir);
  const artifact = writeArtifact(tmp, 'artifact-j.md', [
    'No forbidden terms in standard case.',
    'But UNANIMITY is in upper case here.',
  ].join('\n'));

  const result = runLinter(artifact, flagsDir);

  assert(
    'J1: exit 2 for upper-case shadow term (case-insensitive)',
    result.status === 2,
    `got ${result.status}`
  );

  cleanup(tmp);
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\n${'='.repeat(60)}`);
console.log(`Results: ${passed} passed, ${failed} failed`);
if (failures.length > 0) {
  console.error('\nFailed assertions:');
  for (const f of failures) {
    console.error(`  ${FAIL}  ${f.label}${f.detail ? ': ' + f.detail : ''}`);
  }
}
console.log('='.repeat(60));
process.exit(failed > 0 ? 1 : 0);
