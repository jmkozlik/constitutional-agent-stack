/**
 * gate_t3-compiler_perturbation.js
 * RED-TEAM GATE: proves the hash gate actually catches corruption.
 *
 * If a single byte of core.md or a body template differs from what was used to
 * produce the recorded hashes, compile.js MUST exit NONZERO and MUST write
 * <staging-dir>/_gate-fail.txt naming the differing defs.
 *
 * This fixture runs THREE perturbation scenarios:
 *   A. core.md mutated by one appended byte       → all law-embedding defs fail
 *   B. one body template mutated by one byte       → that def fails
 *   C. both mutations simultaneously               → all law-embedding defs fail
 *
 * Each scenario asserts: exit status != 0 AND _gate-fail.txt exists in staging.
 *
 * Run: node gate_t3-compiler_perturbation.js <path-to-compile.js>
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
  console.error('Usage: node gate_t3-compiler_perturbation.js <path-to-compile.js>');
  process.exit(2);
}
if (!fs.existsSync(COMPILE_JS)) {
  console.error(`compile.js not found at: ${COMPILE_JS}`);
  process.exit(2);
}

const VAULT_ROOT      = (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault'));
const LIVE_AGENTS_DIR = (process.env.CLAUDE_AGENTS_DIR || require('path').join(require('os').homedir(), '.claude', 'agents'));
const HASHES_FILE     = (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault')) + '/executors/contracts/r003-stack-tools/DEF-HASHES.txt';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function buildBodyTemplate(defPath) {
  const content = fs.readFileSync(defPath, 'utf8');
  const lines   = content.split('\n');
  const openIdx  = lines.indexOf('<agent-stack-law>');
  const closeIdx = lines.indexOf('</agent-stack-law>');
  if (openIdx === -1 && closeIdx === -1) return content; // utility
  if (openIdx === -1 || closeIdx === -1)
    throw new Error(`Malformed law block in ${defPath}`);
  const before = lines.slice(0, openIdx);
  const after   = lines.slice(closeIdx + 1);
  return [...before, '@@AGENT-STACK-LAW@@', ...after].join('\n');
}

function detectCharter(defPath) {
  const content = fs.readFileSync(defPath, 'utf8');
  if (!content.includes('<agent-stack-law>')) return 'none';
  const charterNames = ['executor', 'observer', 'council', 'monarch'];
  for (const name of charterNames) {
    const charterPath = path.join(VAULT_ROOT, '_system', 'charters', `${name}.md`);
    if (!fs.existsSync(charterPath)) continue;
    const charterContent = fs.readFileSync(charterPath, 'utf8');
    if (content.includes(charterContent.trimEnd())) return name;
  }
  throw new Error(`Cannot detect charter for ${defPath}`);
}

// Build a fresh synthetic tree in a new tmpdir; apply optional mutations.
// mutations: { coreMdExtra: string, templateMutations: { [defName]: string } }
function buildTree(mutations = {}) {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'gate-t3-pert-'));

  const vaultDir    = path.join(tmpDir, 'vault');
  const systemDir   = path.join(vaultDir, '_system');
  const chartersDir = path.join(systemDir, 'charters');
  const agentsDir   = path.join(tmpDir, 'agents');
  const templatesDir = path.join(tmpDir, 'templates');
  const stagingDir   = path.join(tmpDir, 'staging');
  const manifestPath = path.join(tmpDir, 'manifest.json');

  for (const d of [vaultDir, systemDir, chartersDir, agentsDir, templatesDir, stagingDir]) {
    fs.mkdirSync(d, { recursive: true });
  }

  // core.md — optionally perturbed
  let coreContent = fs.readFileSync(path.join(VAULT_ROOT, '_system', 'core.md'), 'utf8');
  if (mutations.coreMdExtra) coreContent += mutations.coreMdExtra;
  fs.writeFileSync(path.join(systemDir, 'core.md'), coreContent);

  // Charters — always faithful
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
    let template = buildBodyTemplate(livePath);

    // Apply per-def template mutation if present
    if (mutations.templateMutations && mutations.templateMutations[defName]) {
      template += mutations.templateMutations[defName];
    }
    fs.writeFileSync(path.join(templatesDir, `${defName}.body.md`), template);

    manifest[defName] = detectCharter(livePath);
  }

  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));

  return { tmpDir, vaultDir, agentsDir, templatesDir, stagingDir, manifestPath };
}

function runCompile({ vaultDir, agentsDir, templatesDir, stagingDir, manifestPath }) {
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

// Which defs have a law block (should fail on core.md perturbation)
const lawEmbeddingDefs = fs.readdirSync(LIVE_AGENTS_DIR)
  .filter(f => f.endsWith('.md'))
  .filter(f => {
    const content = fs.readFileSync(path.join(LIVE_AGENTS_DIR, f), 'utf8');
    return content.includes('<agent-stack-law>');
  })
  .map(f => f.replace(/\.md$/, ''));

// ---------------------------------------------------------------------------
// SCENARIO A: core.md perturbed by one byte (appended 'X')
// ---------------------------------------------------------------------------
{
  const tree = buildTree({ coreMdExtra: 'X' });
  const result = runCompile(tree);

  assert(result.status !== 0,
    `Scenario A (core.md +1 byte): expected exit nonzero, got ${result.status}\n` +
    `STDOUT: ${result.stdout}\nSTDERR: ${result.stderr}`);

  const gateFailPath = path.join(tree.stagingDir, '_gate-fail.txt');
  assert(fs.existsSync(gateFailPath),
    `Scenario A (core.md +1 byte): expected _gate-fail.txt in staging, not found`);

  if (fs.existsSync(gateFailPath)) {
    const gateFailContent = fs.readFileSync(gateFailPath, 'utf8');
    // At least one law-embedding def must be named in the fail file
    const namedAFailing = lawEmbeddingDefs.some(d => gateFailContent.includes(d));
    assert(namedAFailing,
      `Scenario A: _gate-fail.txt does not name any law-embedding def.\nContent: ${gateFailContent}`);
  }

  fs.rmSync(tree.tmpDir, { recursive: true, force: true });
  console.log('[SCENARIO A] core.md+1byte: compile exits nonzero + _gate-fail.txt written');
}

// ---------------------------------------------------------------------------
// SCENARIO B: one body template mutated (pick stack-implementer)
// ---------------------------------------------------------------------------
{
  const targetDef = 'stack-implementer';
  const tree = buildTree({ templateMutations: { [targetDef]: 'X' } });
  const result = runCompile(tree);

  assert(result.status !== 0,
    `Scenario B (template +1 byte): expected exit nonzero, got ${result.status}\n` +
    `STDOUT: ${result.stdout}\nSTDERR: ${result.stderr}`);

  const gateFailPath = path.join(tree.stagingDir, '_gate-fail.txt');
  assert(fs.existsSync(gateFailPath),
    `Scenario B (template +1 byte): expected _gate-fail.txt in staging, not found`);

  if (fs.existsSync(gateFailPath)) {
    const gateFailContent = fs.readFileSync(gateFailPath, 'utf8');
    assert(gateFailContent.includes(targetDef),
      `Scenario B: _gate-fail.txt does not name ${targetDef}.\nContent: ${gateFailContent}`);
  }

  fs.rmSync(tree.tmpDir, { recursive: true, force: true });
  console.log('[SCENARIO B] template+1byte (stack-implementer): compile exits nonzero + _gate-fail.txt names the def');
}

// ---------------------------------------------------------------------------
// SCENARIO C: both core.md and a utility template mutated
// Utility def (stack-context-builder) template mutation: still fails because
// even the utility hash will differ. core.md mutation: all law-embedding fail.
// ---------------------------------------------------------------------------
{
  const targetDef = 'stack-context-builder'; // utility
  const tree = buildTree({
    coreMdExtra: 'Y',
    templateMutations: { [targetDef]: 'Y' },
  });
  const result = runCompile(tree);

  assert(result.status !== 0,
    `Scenario C (both): expected exit nonzero, got ${result.status}\n` +
    `STDOUT: ${result.stdout}\nSTDERR: ${result.stderr}`);

  const gateFailPath = path.join(tree.stagingDir, '_gate-fail.txt');
  assert(fs.existsSync(gateFailPath),
    `Scenario C (both): expected _gate-fail.txt in staging, not found`);

  fs.rmSync(tree.tmpDir, { recursive: true, force: true });
  console.log('[SCENARIO C] core.md+template both mutated: compile exits nonzero + _gate-fail.txt written');
}

// ---------------------------------------------------------------------------
// Final report
// ---------------------------------------------------------------------------
if (pass) {
  console.log('[PASS] gate_t3-compiler_perturbation: all 3 perturbation scenarios caught');
  process.exit(0);
} else {
  console.error('[FAIL] gate_t3-compiler_perturbation');
  for (const f of failures) console.error(f);
  process.exit(1);
}
