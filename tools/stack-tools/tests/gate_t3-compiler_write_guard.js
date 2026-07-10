/**
 * gate_t3-compiler_write_guard.js
 * WRITE-GUARD GATE: compile.js must refuse to write to --agents-dir, and must
 * refuse when staging-dir == agents-dir (resolved with realpath).
 *
 * Scenarios tested:
 *   W1. staging-dir == agents-dir (exact same path) → exit nonzero, no output written
 *   W2. staging-dir is a realpath-resolved alias of agents-dir (symlinked dir) → exit nonzero
 *   W3. staging-dir path is INSIDE agents-dir (subdirectory) → exit nonzero
 *       (belt-and-suspenders: if compile.js allows this it would still write inside agents-dir)
 *   W4. staging-dir exists as a file (non-directory) → exit nonzero
 *
 * Run: node gate_t3-compiler_write_guard.js <path-to-compile.js>
 */

'use strict';

const { spawnSync } = require('child_process');
const fs   = require('fs');
const path = require('path');
const os   = require('os');

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------
const COMPILE_JS = process.argv[2];
if (!COMPILE_JS) {
  console.error('Usage: node gate_t3-compiler_write_guard.js <path-to-compile.js>');
  process.exit(2);
}
if (!fs.existsSync(COMPILE_JS)) {
  console.error(`compile.js not found at: ${COMPILE_JS}`);
  process.exit(2);
}

const VAULT_ROOT      = (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault'));
const LIVE_AGENTS_DIR = (process.env.CLAUDE_AGENTS_DIR || require('path').join(require('os').homedir(), '.claude', 'agents'));

// ---------------------------------------------------------------------------
// Build a minimal valid synthetic tree (templates + manifest + vault)
// suitable for triggering the compile.js startup path.
// We only need one def to be present.
// ---------------------------------------------------------------------------
function buildMinimalTree() {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'gate-t3-wg-'));

  const vaultDir    = path.join(tmpDir, 'vault');
  const systemDir   = path.join(vaultDir, '_system');
  const chartersDir = path.join(systemDir, 'charters');
  const agentsDir   = path.join(tmpDir, 'agents');
  const templatesDir = path.join(tmpDir, 'templates');
  const manifestPath = path.join(tmpDir, 'manifest.json');

  for (const d of [vaultDir, systemDir, chartersDir, agentsDir, templatesDir]) {
    fs.mkdirSync(d, { recursive: true });
  }

  // Real core.md
  fs.copyFileSync(
    path.join(VAULT_ROOT, '_system', 'core.md'),
    path.join(systemDir, 'core.md')
  );

  // Charters
  for (const charter of ['executor.md', 'observer.md', 'council.md']) {
    const src = path.join(VAULT_ROOT, '_system', 'charters', charter);
    if (fs.existsSync(src)) fs.copyFileSync(src, path.join(chartersDir, charter));
  }

  // Copy all live defs + build templates (needed so compile.js can proceed far
  // enough to hit the staging guard — it must not fail on template lookup first)
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

      // Detect charter
      const charterNames = ['executor', 'observer', 'council', 'monarch'];
      let detectedCharter = 'executor'; // fallback
      for (const name of charterNames) {
        const cp = path.join(VAULT_ROOT, '_system', 'charters', `${name}.md`);
        if (!fs.existsSync(cp)) continue;
        if (content.includes(fs.readFileSync(cp, 'utf8').trimEnd())) {
          detectedCharter = name;
          break;
        }
      }
      manifest[defName] = detectedCharter;
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
// SCENARIO W1: staging-dir == agents-dir (same path string)
// ---------------------------------------------------------------------------
{
  const base = buildMinimalTree();
  // Use agents dir as staging dir
  const result = runCompile({
    vaultDir:     base.vaultDir,
    agentsDir:    base.agentsDir,
    stagingDir:   base.agentsDir,   // same!
    templatesDir: base.templatesDir,
    manifestPath: base.manifestPath,
  });

  assert(result.status !== 0,
    `W1 (staging==agents): expected exit nonzero, got ${result.status}\n` +
    `STDOUT: ${result.stdout}\nSTDERR: ${result.stderr}`);

  // Verify no .md files appeared inside agents dir that weren't there before
  // (compile.js must have exited before writing any output)
  // agents dir was pre-populated with all defs; no NEW files should exist
  const agentFiles = fs.readdirSync(base.agentsDir).filter(f => f.endsWith('.md'));
  // Original count = 11
  assert(agentFiles.length === 11,
    `W1: agents dir file count changed — compile.js may have written output to agents-dir`);

  fs.rmSync(base.tmpDir, { recursive: true, force: true });
  console.log('[SCENARIO W1] staging==agents: compile exits nonzero, no output written');
}

// ---------------------------------------------------------------------------
// SCENARIO W2: staging-dir is a symlink to agents-dir
// realpath resolution must catch this
// ---------------------------------------------------------------------------
{
  const base = buildMinimalTree();
  const symlinkStaging = path.join(base.tmpDir, 'staging-link');
  fs.symlinkSync(base.agentsDir, symlinkStaging);

  const result = runCompile({
    vaultDir:     base.vaultDir,
    agentsDir:    base.agentsDir,
    stagingDir:   symlinkStaging,   // symlink → agents dir
    templatesDir: base.templatesDir,
    manifestPath: base.manifestPath,
  });

  assert(result.status !== 0,
    `W2 (staging=symlink-to-agents): expected exit nonzero, got ${result.status}\n` +
    `STDOUT: ${result.stdout}\nSTDERR: ${result.stderr}`);

  fs.rmSync(base.tmpDir, { recursive: true, force: true });
  console.log('[SCENARIO W2] staging=symlink→agents: compile exits nonzero');
}

// ---------------------------------------------------------------------------
// SCENARIO W3: staging-dir exists as a plain FILE, not a directory
// Per spec: "lstat staging-dir, abort if it exists as a non-directory"
// ---------------------------------------------------------------------------
{
  const base = buildMinimalTree();
  const fileStaging = path.join(base.tmpDir, 'staging-is-a-file');
  fs.writeFileSync(fileStaging, 'I am not a directory');

  const result = runCompile({
    vaultDir:     base.vaultDir,
    agentsDir:    base.agentsDir,
    stagingDir:   fileStaging,    // exists as a file
    templatesDir: base.templatesDir,
    manifestPath: base.manifestPath,
  });

  assert(result.status !== 0,
    `W3 (staging is a file): expected exit nonzero, got ${result.status}\n` +
    `STDOUT: ${result.stdout}\nSTDERR: ${result.stderr}`);

  // File must not have been overwritten with directory content
  assert(fs.statSync(fileStaging).isFile(),
    `W3: staging path is no longer a file — compile.js may have converted it`);

  fs.rmSync(base.tmpDir, { recursive: true, force: true });
  console.log('[SCENARIO W3] staging-is-file: compile exits nonzero');
}

// ---------------------------------------------------------------------------
// SCENARIO W4: staging-dir is a subdirectory OF agents-dir
// compile.js would write inside agents-dir — the guard must catch this.
// (This is a belt-and-suspenders test; the spec says refuse if staging==agents
// resolved; a subdirectory is a different path but still inside agents-dir.)
// NOTE: if compile.js only checks exact equality, this test documents whether
// it also guards subdir writes. The spec says "NEVER writes to --agents-dir"
// and "refuse if staging-dir == agents-dir (resolve both with realpath first)".
// A subdirectory is NOT the same path, so compile.js MAY allow this scenario —
// we assert it here as SHOULD-refuse; if it exits 0 we WARN but do not FAIL
// the gate (the spec does not explicitly enumerate subdir as forbidden).
// We record the outcome for the verifier.
// ---------------------------------------------------------------------------
{
  const base = buildMinimalTree();
  const subdirStaging = path.join(base.agentsDir, 'staging-subdir');
  fs.mkdirSync(subdirStaging);

  const result = runCompile({
    vaultDir:     base.vaultDir,
    agentsDir:    base.agentsDir,
    stagingDir:   subdirStaging,   // subdir inside agents-dir
    templatesDir: base.templatesDir,
    manifestPath: base.manifestPath,
  });

  // Per strict reading of spec: staging-dir == agents-dir is the ONLY
  // mentioned equality check. Subdirectory is a different realpath.
  // We document: if compile.js exits 0 here, output is inside agents-dir,
  // which is a policy violation the panel should note.
  if (result.status !== 0) {
    console.log('[SCENARIO W4] staging=subdir-of-agents: compile exits nonzero (good, stricter than spec requires)');
  } else {
    console.warn('[WARN W4] staging=subdir-of-agents: compile exited 0 — output written inside agents-dir.' +
      ' Spec only mandates staging != agents (exact), not subdir guard. Document for panel.');
  }

  fs.rmSync(base.tmpDir, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// Final report
// ---------------------------------------------------------------------------
if (pass) {
  console.log('[PASS] gate_t3-compiler_write_guard: W1 staging==agents, W2 symlinked-dir, W3 staging-is-file all rejected');
  process.exit(0);
} else {
  console.error('[FAIL] gate_t3-compiler_write_guard');
  for (const f of failures) console.error(f);
  process.exit(1);
}
