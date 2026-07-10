#!/usr/bin/env node
/**
 * gate_t1-graduation_write-guard.js
 *
 * Asserts the WRITE-GUARD requirements of graduation.js.
 *
 * From the contract:
 *   "Writes ONLY a regular file at <out>. lstat the parent dir; if <out> or its
 *    parent is a symlink, do NOT follow it — abort. Abort if parent is a non-dir."
 *
 * Covered behaviors:
 *   WG-1. <out> itself is a symlink (to a regular file) → abort, non-zero exit
 *   WG-2. Parent directory of <out> is a symlink (to a real dir) → abort, non-zero exit
 *   WG-3. Parent directory of <out> is a regular file (non-dir) → abort, non-zero exit
 *   WG-4. Normal parent dir, <out> does not yet exist → succeeds, file written, exit 0
 *   WG-5. Normal parent dir, <out> already exists as a regular file → overwrites, exit 0
 *   WG-6. Verifies the script does NOT follow a symlink and write to the real target
 *         (WG-1 enforces this; additionally assert the real target is unmodified)
 *
 * Run: node gate_t1-graduation_write-guard.js <path-to-graduation.js>
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
  console.error('Usage: node gate_t1-graduation_write-guard.js <path-to-graduation.js>');
  process.exit(2);
}
if (!fs.existsSync(GRADUATION_JS)) {
  console.error(`graduation.js not found at: ${GRADUATION_JS}`);
  process.exit(2);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function buildMinimalVault(tmpBase) {
  const vaultDir  = path.join(tmpBase, 'vault');
  const ledgerDir = path.join(vaultDir, 'ledger');
  fs.mkdirSync(ledgerDir, { recursive: true });
  // Empty ledger is sufficient — write-guard tests don't depend on ledger content
  return vaultDir;
}

function runGraduation(vaultPath, outPath) {
  return spawnSync(process.execPath, [
    GRADUATION_JS,
    '--vault', vaultPath,
    '--out',   outPath,
  ], { encoding: 'utf8', timeout: 10000 });
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
// WG-1: <out> is a symlink (pointing to a regular file) → must abort
// ---------------------------------------------------------------------------
console.log('\n--- WG-1: <out> is a symlink to a regular file ---');
{
  const tmp       = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-wg1-'));
  const vault     = buildMinimalVault(tmp);
  const realFile  = path.join(tmp, 'real-target.json');
  const symlinkOut = path.join(tmp, 'symlink-out.json');

  // Create the real target file and a symlink pointing to it
  fs.writeFileSync(realFile, '{"original": true}\n');
  fs.symlinkSync(realFile, symlinkOut);
  const originalContent = fs.readFileSync(realFile, 'utf8');

  const result = runGraduation(vault, symlinkOut);

  assert(result.status !== 0,
    'WG-1a: exit non-zero when <out> is a symlink',
    `got exit ${result.status}\nstderr: ${result.stderr}`);

  // The real target must NOT have been overwritten
  let currentContent;
  try { currentContent = fs.readFileSync(realFile, 'utf8'); } catch (_) { currentContent = null; }
  assert(currentContent === originalContent,
    'WG-1b: real target file not modified through symlink',
    `original: "${originalContent.trim()}", current: "${String(currentContent).trim()}"`);

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// WG-2: Parent directory of <out> is a symlink (to a real dir) → must abort
// ---------------------------------------------------------------------------
console.log('\n--- WG-2: parent dir of <out> is a symlink ---');
{
  const tmp       = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-wg2-'));
  const vault     = buildMinimalVault(tmp);
  const realDir   = path.join(tmp, 'real-dir');
  const symlinkDir = path.join(tmp, 'link-dir');

  fs.mkdirSync(realDir, { recursive: true });
  fs.symlinkSync(realDir, symlinkDir);

  // <out> lives inside the symlinked parent
  const outPath = path.join(symlinkDir, 'status.json');

  const result = runGraduation(vault, outPath);

  assert(result.status !== 0,
    'WG-2a: exit non-zero when parent dir is a symlink',
    `got exit ${result.status}\nstderr: ${result.stderr}`);

  // Nothing should have been written inside the real dir
  const filesInReal = fs.readdirSync(realDir);
  assert(filesInReal.length === 0,
    'WG-2b: no file written inside real dir via symlinked parent',
    `found: ${JSON.stringify(filesInReal)}`);

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// WG-3: Parent directory of <out> is a regular file (non-dir) → must abort
// ---------------------------------------------------------------------------
console.log('\n--- WG-3: parent of <out> is a regular file (non-dir) ---');
{
  const tmp      = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-wg3-'));
  const vault    = buildMinimalVault(tmp);
  const fakeDir  = path.join(tmp, 'not-a-dir');

  // Create a regular file where the "parent" would be
  fs.writeFileSync(fakeDir, 'i am a file, not a directory\n');

  // <out> path whose parent "not-a-dir" is actually a file
  const outPath = path.join(fakeDir, 'status.json');

  const result = runGraduation(vault, outPath);

  assert(result.status !== 0,
    'WG-3: exit non-zero when parent of <out> is a regular file',
    `got exit ${result.status}\nstderr: ${result.stderr}`);

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// WG-4: Normal parent dir, <out> does not yet exist → creates file, exit 0
// ---------------------------------------------------------------------------
console.log('\n--- WG-4: normal parent dir, <out> new file ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-wg4-'));
  const vault = buildMinimalVault(tmp);
  const outDir = path.join(tmp, 'output-dir');
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, 'regency-status.json');

  // Confirm file does not yet exist
  assert(!fs.existsSync(outPath), 'WG-4-pre: <out> does not exist before run');

  const result = runGraduation(vault, outPath);

  assert(result.status === 0,
    'WG-4a: exit 0 with normal parent dir',
    `got exit ${result.status}\nstderr: ${result.stderr}`);

  assert(fs.existsSync(outPath),
    'WG-4b: output file created',
    `path: ${outPath}`);

  // Verify it's a regular file (not a symlink, not a dir)
  const stat = fs.lstatSync(outPath);
  assert(stat.isFile() && !stat.isSymbolicLink(),
    'WG-4c: output is a regular file (not symlink)',
    `isFile=${stat.isFile()} isSymlink=${stat.isSymbolicLink()}`);

  // Verify content is valid JSON
  let parsed = null;
  try { parsed = JSON.parse(fs.readFileSync(outPath, 'utf8')); } catch (_) {}
  assert(parsed !== null && typeof parsed === 'object',
    'WG-4d: output file contains valid JSON object',
    `content: ${fs.existsSync(outPath) ? fs.readFileSync(outPath, 'utf8') : 'missing'}`);

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// WG-5: Normal parent dir, <out> already exists as a regular file → overwrites, exit 0
// ---------------------------------------------------------------------------
console.log('\n--- WG-5: <out> already exists as regular file → overwritten ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-wg5-'));
  const vault = buildMinimalVault(tmp);
  const outDir = path.join(tmp, 'out');
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, 'regency-status.json');

  // Pre-create the output file with stale content
  fs.writeFileSync(outPath, '{"stale": true}\n');

  const result = runGraduation(vault, outPath);

  assert(result.status === 0,
    'WG-5a: exit 0 when overwriting existing output file',
    `got exit ${result.status}\nstderr: ${result.stderr}`);

  let parsed = null;
  try { parsed = JSON.parse(fs.readFileSync(outPath, 'utf8')); } catch (_) {}
  assert(parsed !== null && typeof parsed === 'object',
    'WG-5b: overwritten file is valid JSON',
    `content: ${fs.existsSync(outPath) ? fs.readFileSync(outPath, 'utf8') : 'missing'}`);

  // The stale sentinel key should be gone
  assert(parsed && parsed['stale'] === undefined,
    'WG-5c: stale content replaced (not stale key)',
    `parsed: ${JSON.stringify(parsed)}`);

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// WG-6: Writes ONLY the <out> file — no additional side-effect files
//        (belt-and-suspenders: confirm nothing else was written to vault)
// ---------------------------------------------------------------------------
console.log('\n--- WG-6: writes only the <out> file, no vault mutations ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'grad-wg6-'));
  const vault = buildMinimalVault(tmp);
  const outPath = path.join(tmp, 'status.json');

  // Snapshot ledger before run
  const ledgerDir     = path.join(vault, 'ledger');
  const ledgerBefore  = fs.readdirSync(ledgerDir).sort();

  const result = runGraduation(vault, outPath);

  assert(result.status === 0, 'WG-6a: exit 0', `stderr: ${result.stderr}`);

  const ledgerAfter = fs.readdirSync(ledgerDir).sort();
  assert(
    JSON.stringify(ledgerBefore) === JSON.stringify(ledgerAfter),
    'WG-6b: ledger directory unchanged after run',
    `before: ${JSON.stringify(ledgerBefore)}, after: ${JSON.stringify(ledgerAfter)}`
  );

  fs.rmSync(tmp, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\nWrite-guard fixtures: ${passed} passed, ${failed} failed.`);
process.exit(failed > 0 ? 1 : 0);
