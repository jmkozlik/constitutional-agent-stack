/**
 * gate_t3-compiler_symlink.js
 * PER-FILE SYMLINK GATE: before opening any output path <staging-dir>/<def>.md
 * for write, compile.js must fs.lstatSync that path; if it is a symlink, ABORT.
 *
 * This is a critical adversarial guard: a leftover symlink in staging pointing
 * at a live def would otherwise silently clobber the live agent definition.
 *
 * Scenarios:
 *   S1. One output path in staging is a symlink to an UNRELATED temp file.
 *       compile.js must abort before writing any output.
 *   S2. One output path in staging is a symlink pointing at a LIVE agent def.
 *       compile.js must abort WITHOUT clobbering the live def.
 *   S3. Multiple output paths are symlinks. All cause abort.
 *   S4. Symlink exists on a UTILITY def (no law block) — guard applies equally.
 *
 * Run: node gate_t3-compiler_symlink.js <path-to-compile.js>
 */

'use strict';

const { spawnSync } = require('child_process');
const fs   = require('fs');
const path = require('path');
const os   = require('os');
const crypto = require('crypto');

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------
const COMPILE_JS = process.argv[2];
if (!COMPILE_JS) {
  console.error('Usage: node gate_t3-compiler_symlink.js <path-to-compile.js>');
  process.exit(2);
}
if (!fs.existsSync(COMPILE_JS)) {
  console.error(`compile.js not found at: ${COMPILE_JS}`);
  process.exit(2);
}

const VAULT_ROOT      = (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault'));
const LIVE_AGENTS_DIR = (process.env.CLAUDE_AGENTS_DIR || require('path').join(require('os').homedir(), '.claude', 'agents'));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function sha256File(filePath) {
  const buf = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function buildFullTree() {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'gate-t3-sym-'));

  const vaultDir    = path.join(tmpDir, 'vault');
  const systemDir   = path.join(vaultDir, '_system');
  const chartersDir = path.join(systemDir, 'charters');
  const agentsDir   = path.join(tmpDir, 'agents');
  const templatesDir = path.join(tmpDir, 'templates');
  const manifestPath = path.join(tmpDir, 'manifest.json');

  for (const d of [vaultDir, systemDir, chartersDir, agentsDir, templatesDir]) {
    fs.mkdirSync(d, { recursive: true });
  }

  fs.copyFileSync(
    path.join(VAULT_ROOT, '_system', 'core.md'),
    path.join(systemDir, 'core.md')
  );

  for (const charter of ['executor.md', 'observer.md', 'council.md', 'monarch.md']) {
    const src = path.join(VAULT_ROOT, '_system', 'charters', charter);
    if (fs.existsSync(src)) fs.copyFileSync(src, path.join(chartersDir, charter));
  }

  const allDefs = fs.readdirSync(LIVE_AGENTS_DIR).filter(f => f.endsWith('.md'));
  const manifest = {};

  for (const defFile of allDefs) {
    const livePath = path.join(LIVE_AGENTS_DIR, defFile);
    fs.copyFileSync(livePath, path.join(agentsDir, defFile));

    const defName = defFile.replace(/\.md$/, '');
    const content = fs.readFileSync(livePath, 'utf8');
    const lines   = content.split('\n');
    const openIdx  = lines.indexOf('<agent-stack-law>');
    const closeIdx = lines.indexOf('</agent-stack-law>');

    let template;
    if (openIdx === -1 && closeIdx === -1) {
      template = content;
      manifest[defName] = 'none';
    } else {
      const before = lines.slice(0, openIdx);
      const after   = lines.slice(closeIdx + 1);
      template = [...before, '@@AGENT-STACK-LAW@@', ...after].join('\n');

      const charterNames = ['executor', 'observer', 'council', 'monarch'];
      let detected = 'executor';
      for (const name of charterNames) {
        const cp = path.join(VAULT_ROOT, '_system', 'charters', `${name}.md`);
        if (!fs.existsSync(cp)) continue;
        if (content.includes(fs.readFileSync(cp, 'utf8').trimEnd())) {
          detected = name;
          break;
        }
      }
      manifest[defName] = detected;
    }
    fs.writeFileSync(path.join(templatesDir, `${defName}.body.md`), template);
  }

  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));

  return { tmpDir, vaultDir, agentsDir, templatesDir, manifestPath };
}

function runCompile({ vaultDir, agentsDir, stagingDir, templatesDir, manifestPath }) {
  return spawnSync('node', [
    COMPILE_JS,
    '--vault',       vaultDir,
    '--agents-dir',  agentsDir,
    '--staging-dir', stagingDir,
    '--templates',   templatesDir,
    '--manifest',    manifestPath,
  ], { encoding: 'utf8' });
}

// ---------------------------------------------------------------------------
// Test runner
// ---------------------------------------------------------------------------
let pass = true;
const failures = [];

function assert(condition, msg) {
  if (!condition) {
    pass = false;
    failures.push(`FAIL: ${msg}`);
  }
}

// ---------------------------------------------------------------------------
// SCENARIO S1: one output path in staging is a symlink to an unrelated file
// ---------------------------------------------------------------------------
{
  const base = buildFullTree();
  const stagingDir = path.join(base.tmpDir, 'staging');
  fs.mkdirSync(stagingDir);

  // Create an innocent target file
  const targetFile = path.join(base.tmpDir, 'innocent-target.txt');
  fs.writeFileSync(targetFile, 'original content');
  const originalContent = fs.readFileSync(targetFile, 'utf8');

  // Place a symlink at the output path for stack-implementer.md
  const symlinkPath = path.join(stagingDir, 'stack-implementer.md');
  fs.symlinkSync(targetFile, symlinkPath);

  const result = runCompile({
    vaultDir:     base.vaultDir,
    agentsDir:    base.agentsDir,
    stagingDir,
    templatesDir: base.templatesDir,
    manifestPath: base.manifestPath,
  });

  assert(result.status !== 0,
    `S1 (symlink to unrelated file): expected exit nonzero, got ${result.status}\n` +
    `STDOUT: ${result.stdout}\nSTDERR: ${result.stderr}`);

  // Target file must not have been overwritten
  const afterContent = fs.readFileSync(targetFile, 'utf8');
  assert(afterContent === originalContent,
    `S1: target file was overwritten through symlink — content changed`);

  fs.rmSync(base.tmpDir, { recursive: true, force: true });
  console.log('[SCENARIO S1] symlink-to-unrelated: compile exits nonzero, target file untouched');
}

// ---------------------------------------------------------------------------
// SCENARIO S2: symlink points to a LIVE agent def
// The critical scenario: a leftover symlink → live def would clobber it.
// ---------------------------------------------------------------------------
{
  const base = buildFullTree();
  const stagingDir = path.join(base.tmpDir, 'staging');
  fs.mkdirSync(stagingDir);

  // Record the hash of the live def BEFORE the test
  const liveDefPath = path.join(LIVE_AGENTS_DIR, 'stack-implementer.md');
  const hashBefore  = sha256File(liveDefPath);

  // Place a symlink at the staging output path pointing at the live def
  const symlinkPath = path.join(stagingDir, 'stack-implementer.md');
  fs.symlinkSync(liveDefPath, symlinkPath);

  const result = runCompile({
    vaultDir:     base.vaultDir,
    agentsDir:    base.agentsDir,
    stagingDir,
    templatesDir: base.templatesDir,
    manifestPath: base.manifestPath,
  });

  assert(result.status !== 0,
    `S2 (symlink→live def): expected exit nonzero, got ${result.status}\n` +
    `STDOUT: ${result.stdout}\nSTDERR: ${result.stderr}`);

  // CRITICAL: live def must be unmodified
  const hashAfter = sha256File(liveDefPath);
  assert(hashAfter === hashBefore,
    `S2: LIVE DEF WAS CLOBBERED through symlink! Hash changed:\n` +
    `  before: ${hashBefore}\n  after:  ${hashAfter}`);

  fs.rmSync(base.tmpDir, { recursive: true, force: true });
  console.log('[SCENARIO S2] symlink→live-def: compile exits nonzero, live def unmodified');
}

// ---------------------------------------------------------------------------
// SCENARIO S3: multiple symlinks in staging (two defs)
// compile.js must abort even if the FIRST file has no symlink
// (the abort must happen before ANY write, or at the first symlink encountered)
// ---------------------------------------------------------------------------
{
  const base = buildFullTree();
  const stagingDir = path.join(base.tmpDir, 'staging');
  fs.mkdirSync(stagingDir);

  const target1 = path.join(base.tmpDir, 'dummy1.txt');
  const target2 = path.join(base.tmpDir, 'dummy2.txt');
  fs.writeFileSync(target1, 'dummy1');
  fs.writeFileSync(target2, 'dummy2');

  fs.symlinkSync(target1, path.join(stagingDir, 'stack-implementer.md'));
  fs.symlinkSync(target2, path.join(stagingDir, 'stack-behavior-analyst.md'));

  const result = runCompile({
    vaultDir:     base.vaultDir,
    agentsDir:    base.agentsDir,
    stagingDir,
    templatesDir: base.templatesDir,
    manifestPath: base.manifestPath,
  });

  assert(result.status !== 0,
    `S3 (multiple symlinks): expected exit nonzero, got ${result.status}\n` +
    `STDOUT: ${result.stdout}\nSTDERR: ${result.stderr}`);

  // Both dummy targets must still have original content
  assert(fs.readFileSync(target1, 'utf8') === 'dummy1',
    `S3: target1 was overwritten through symlink`);
  assert(fs.readFileSync(target2, 'utf8') === 'dummy2',
    `S3: target2 was overwritten through symlink`);

  fs.rmSync(base.tmpDir, { recursive: true, force: true });
  console.log('[SCENARIO S3] multiple symlinks: compile exits nonzero, no targets overwritten');
}

// ---------------------------------------------------------------------------
// SCENARIO S4: symlink on a UTILITY def (no law block)
// Per spec: per-file lstat applies to ALL output paths, not just law-embedding ones.
// ---------------------------------------------------------------------------
{
  const base = buildFullTree();
  const stagingDir = path.join(base.tmpDir, 'staging');
  fs.mkdirSync(stagingDir);

  const targetFile = path.join(base.tmpDir, 'utility-target.txt');
  fs.writeFileSync(targetFile, 'utility content');

  // stack-context-builder is a utility (no law block, manifest 'none')
  fs.symlinkSync(targetFile, path.join(stagingDir, 'stack-context-builder.md'));

  const result = runCompile({
    vaultDir:     base.vaultDir,
    agentsDir:    base.agentsDir,
    stagingDir,
    templatesDir: base.templatesDir,
    manifestPath: base.manifestPath,
  });

  assert(result.status !== 0,
    `S4 (utility symlink): expected exit nonzero, got ${result.status}\n` +
    `STDOUT: ${result.stdout}\nSTDERR: ${result.stderr}`);

  const afterContent = fs.readFileSync(targetFile, 'utf8');
  assert(afterContent === 'utility content',
    `S4: utility target file was overwritten through symlink`);

  fs.rmSync(base.tmpDir, { recursive: true, force: true });
  console.log('[SCENARIO S4] utility-def symlink: compile exits nonzero, target untouched');
}

// ---------------------------------------------------------------------------
// Final report
// ---------------------------------------------------------------------------
if (pass) {
  console.log('[PASS] gate_t3-compiler_symlink: all 4 per-file symlink scenarios aborted correctly');
  process.exit(0);
} else {
  console.error('[FAIL] gate_t3-compiler_symlink');
  for (const f of failures) console.error(f);
  process.exit(1);
}
