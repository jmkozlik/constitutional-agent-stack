#!/usr/bin/env node
/**
 * gate_t1-beacon_write-guard.js
 * Asserts:
 *   WG-1: beacon.js refuses to write when --out is a symlink pointing to a real dir
 *   WG-2: beacon.js refuses to write when --out is a regular file (not a directory)
 *   WG-3: beacon.js succeeds (exit 0) when --out is a normal directory
 *
 * Contract ref: "WRITE-GUARD" section — symlink: if <out> is a symlink, do NOT
 * follow it; non-file entry: if out path exists and is not a directory, abort.
 */
'use strict';
const fs   = require('fs');
const path = require('path');
const {execFileSync, spawnSync} = require('child_process');
const os   = require('os');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function makeSyntheticVault(base) {
  // Minimal vault: one ledger start+complete so beacon.js has something to read
  const ledger  = path.join(base, 'ledger');
  const telem   = path.join(base, '.telemetry');
  const canary  = path.join(base, 'god', 'canary');
  const archive = path.join(base, 'executors', 'archive', 'rX');

  fs.mkdirSync(ledger, {recursive: true});
  fs.mkdirSync(telem,  {recursive: true});
  fs.mkdirSync(canary, {recursive: true});
  fs.mkdirSync(archive, {recursive: true});

  // ledger: start + complete at 10:00 and 10:08
  fs.writeFileSync(path.join(ledger, '0001-rX-start.md'),
    '---\ntype: log\nlabels: [run]\nrun-id: rX\n---\n2026-01-01T10:00:00Z · rX START\n');
  fs.writeFileSync(path.join(ledger, '0002-rX-complete.md'),
    '---\ntype: log\nlabels: [run]\nrun-id: rX\n---\n2026-01-01T10:08:00Z · rX COMPLETE\n');

  // verify-report: NOT-REFUTED
  fs.writeFileSync(path.join(archive, 'verify-report-t1.md'),
    '# Verify Report\nVerdict: NOT-REFUTED\n');

  // telemetry: one row AFTER a canary boot
  const bootTs  = '2026-01-01T09:00:00.000Z';
  const telemTs = '2026-01-01T09:01:00.000Z';
  fs.writeFileSync(path.join(canary, 'boot-log.jsonl'),
    JSON.stringify({ts: bootTs, event: 'sessionstart'}) + '\n');
  fs.writeFileSync(path.join(telem, 'raw-2026-01-01.jsonl'),
    JSON.stringify({ts: telemTs, tool: 'Write', file: '/tmp/x', session: 'test'}) + '\n');

  return base;
}

function runBeacon(vaultPath, outPath) {
  const beacon = path.join(__dirname, 'beacon.js');
  const args   = ['--vault', vaultPath, '--out', outPath];
  return spawnSync(process.execPath, [beacon, ...args], {encoding: 'utf8', timeout: 10000});
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
// WG-1: symlink out dir → must refuse
// ---------------------------------------------------------------------------
console.log('\n--- WG-1: symlink out dir ---');
{
  const tmp    = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-wg1-'));
  const vault  = makeSyntheticVault(path.join(tmp, 'vault'));
  const real   = path.join(tmp, 'real-out');
  const lnk    = path.join(tmp, 'link-out');
  fs.mkdirSync(real, {recursive: true});
  fs.symlinkSync(real, lnk);

  const result = runBeacon(vault, lnk);
  // Must exit non-zero AND not write any files into the real target
  const filesWritten = fs.readdirSync(real).filter(f => f.startsWith('beacon-'));
  assert(result.status !== 0,
    'WG-1a: exit code non-zero when --out is a symlink',
    `got exit ${result.status}`);
  assert(filesWritten.length === 0,
    'WG-1b: no beacon file written through symlink',
    `found ${filesWritten.length} file(s)`);

  // cleanup
  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// WG-2: out path is a regular file (not a directory) → must refuse
// ---------------------------------------------------------------------------
console.log('\n--- WG-2: out path is a regular file ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-wg2-'));
  const vault = makeSyntheticVault(path.join(tmp, 'vault'));
  const file  = path.join(tmp, 'not-a-dir.txt');
  fs.writeFileSync(file, 'i am a file\n');

  const result = runBeacon(vault, file);
  assert(result.status !== 0,
    'WG-2: exit code non-zero when --out is a regular file',
    `got exit ${result.status}\nstderr: ${result.stderr}`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// WG-3: out path is a normal (non-symlink) directory → must succeed (exit 0)
// ---------------------------------------------------------------------------
console.log('\n--- WG-3: normal directory succeeds ---');
{
  const tmp   = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-wg3-'));
  const vault = makeSyntheticVault(path.join(tmp, 'vault'));
  const out   = path.join(tmp, 'out');
  fs.mkdirSync(out, {recursive: true});

  const result = runBeacon(vault, out);
  assert(result.status === 0,
    'WG-3a: exit 0 when --out is a normal directory',
    `got exit ${result.status}\nstderr: ${result.stderr}`);

  const files = fs.readdirSync(out).filter(f => f.startsWith('beacon-'));
  assert(files.length >= 1,
    'WG-3b: beacon file written into out directory',
    `found ${files.length} file(s)`);

  fs.rmSync(tmp, {recursive: true, force: true});
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\nWrite-guard fixtures: ${passed} passed, ${failed} failed.`);
process.exit(failed > 0 ? 1 : 0);
