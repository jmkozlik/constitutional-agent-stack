/**
 * gate_t3-compiler_hash.js
 * ACCEPTANCE GATE: faithful compile → exit 0 + all 11 staged defs SHA-256-match
 * the recorded hashes in DEF-HASHES.txt.
 *
 * This fixture is INDEPENDENT of the implementation. It:
 *   1. Builds a synthetic tree (vault + agents-dir + templates) from real files.
 *   2. Invokes compile.js via the interface spec CLI.
 *   3. Asserts exit 0.
 *   4. Asserts every staged file's SHA-256 matches the prerecorded hash in
 *      DEF-HASHES.txt — the canonical check the panel demanded.
 *
 * Run: node gate_t3-compiler_hash.js <path-to-compile.js>
 */

'use strict';

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const os = require('os');

// ---------------------------------------------------------------------------
// Configuration — all paths are absolute, no hardcoded cwd assumptions.
// ---------------------------------------------------------------------------
const COMPILE_JS = process.argv[2];
if (!COMPILE_JS) {
  console.error('Usage: node gate_t3-compiler_hash.js <path-to-compile.js>');
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
function sha256File(filePath) {
  const buf = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function parseHashesFile(p) {
  // Format: "<hex>  <name>.md" (two spaces, as shasum -a 256 output)
  const lines = fs.readFileSync(p, 'utf8').trim().split('\n');
  const map = {};
  for (const line of lines) {
    const m = line.match(/^([0-9a-f]{64})\s+(.+\.md)$/);
    if (!m) throw new Error(`Unexpected line in hashes file: ${line}`);
    map[m[2]] = m[1];
  }
  return map;
}

// Build body template: read live def, replace law block with marker.
// Returns the template string.
function buildBodyTemplate(defPath) {
  const content = fs.readFileSync(defPath, 'utf8');
  const lines = content.split('\n');
  const openIdx = lines.indexOf('<agent-stack-law>');
  const closeIdx = lines.indexOf('</agent-stack-law>');
  if (openIdx === -1 && closeIdx === -1) {
    // Utility def — no law block; template is full file verbatim.
    return content;
  }
  if (openIdx === -1 || closeIdx === -1) {
    throw new Error(`Malformed law block in ${defPath}: open=${openIdx} close=${closeIdx}`);
  }
  // Replace the inclusive range [openIdx .. closeIdx] with the marker.
  const before = lines.slice(0, openIdx);
  const after   = lines.slice(closeIdx + 1);
  return [...before, '@@AGENT-STACK-LAW@@', ...after].join('\n');
}

// ---------------------------------------------------------------------------
// Test setup: create a temporary synthetic tree
// ---------------------------------------------------------------------------
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'gate-t3-hash-'));

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

// Copy real core.md into synthetic vault
fs.copyFileSync(
  path.join(VAULT_ROOT, '_system', 'core.md'),
  path.join(systemDir, 'core.md')
);

// Copy real charters
for (const charter of ['executor.md', 'observer.md', 'council.md', 'monarch.md']) {
  const src = path.join(VAULT_ROOT, '_system', 'charters', charter);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, path.join(chartersDir, charter));
  }
}

// Copy all 11 live defs into synthetic agents dir AND build templates
const allDefs = fs.readdirSync(LIVE_AGENTS_DIR).filter(f => f.endsWith('.md'));
if (allDefs.length !== 11) {
  console.error(`Expected 11 live defs, found ${allDefs.length}. Aborting.`);
  process.exit(2);
}

const manifest = {};

// Charter mapping: derived from the contract's interface spec example.
// executor = has law block AND is an executor-type agent; we use the logic:
// if the def contains <agent-stack-law> → needs a charter.
// The exact charter is determined by reading the agent's role from the def text.
// For the ACCEPTANCE gate we use the same mapping the implementer will use,
// which must be reproducible from the spec. The contract says manifest maps
// def name → one of executor | observer | council | none.
// We determine this from the live def content (the charter block it currently embeds).
function detectCharter(defPath) {
  const content = fs.readFileSync(defPath, 'utf8');
  if (!content.includes('<agent-stack-law>')) return 'none';
  // The charter used is the one whose content appears verbatim in the law block.
  // Read each charter file and check if it appears in the content.
  const charterNames = ['executor', 'observer', 'council', 'monarch'];
  for (const name of charterNames) {
    const charterPath = path.join(VAULT_ROOT, '_system', 'charters', `${name}.md`);
    if (!fs.existsSync(charterPath)) continue;
    const charterContent = fs.readFileSync(charterPath, 'utf8');
    // Strip trailing newline for matching (the charter file may have one).
    if (content.includes(charterContent.trimEnd())) return name;
  }
  throw new Error(`Cannot detect charter for ${defPath}`);
}

for (const defFile of allDefs) {
  const livePath = path.join(LIVE_AGENTS_DIR, defFile);
  fs.copyFileSync(livePath, path.join(agentsDir, defFile));

  // Build and write body template
  const template = buildBodyTemplate(livePath);
  const defName = defFile.replace(/\.md$/, '');
  fs.writeFileSync(path.join(templatesDir, `${defName}.body.md`), template);

  // Determine charter
  manifest[defName] = detectCharter(livePath);
}

fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));

// ---------------------------------------------------------------------------
// Invoke compile.js
// ---------------------------------------------------------------------------
const result = spawnSync('node', [
  COMPILE_JS,
  '--vault',       vaultDir,
  '--agents-dir',  agentsDir,
  '--staging-dir', stagingDir,
  '--templates',   templatesDir,
  '--manifest',    manifestPath,
], { encoding: 'utf8' });

// ---------------------------------------------------------------------------
// Assertions
// ---------------------------------------------------------------------------
let pass = true;
const failures = [];

function assert(condition, msg) {
  if (!condition) {
    pass = false;
    failures.push(`FAIL: ${msg}`);
  }
}

// Assertion 1: exit 0
assert(result.status === 0,
  `compile.js exited ${result.status} (expected 0)\nSTDOUT: ${result.stdout}\nSTDERR: ${result.stderr}`);

// Assertion 2: all 11 staged files exist
const recordedHashes = parseHashesFile(HASHES_FILE);
const expectedDefs   = Object.keys(recordedHashes); // e.g. ["stack-implementer.md", ...]

assert(expectedDefs.length === 11,
  `DEF-HASHES.txt has ${expectedDefs.length} entries, expected 11`);

for (const defFile of expectedDefs) {
  const stagedPath = path.join(stagingDir, defFile);
  assert(fs.existsSync(stagedPath), `Staged file missing: ${stagedPath}`);

  if (fs.existsSync(stagedPath)) {
    const actual   = sha256File(stagedPath);
    const expected = recordedHashes[defFile];
    assert(actual === expected,
      `Hash mismatch for ${defFile}:\n  got      ${actual}\n  expected ${expected}`);
  }
}

// Assertion 3: _gate-fail.txt must NOT exist on success
const gateFailPath = path.join(stagingDir, '_gate-fail.txt');
assert(!fs.existsSync(gateFailPath),
  `_gate-fail.txt unexpectedly present in staging on supposed-success run`);

// ---------------------------------------------------------------------------
// Cleanup and report
// ---------------------------------------------------------------------------
fs.rmSync(tmpDir, { recursive: true, force: true });

if (pass) {
  console.log('[PASS] gate_t3-compiler_hash: exit 0 + all 11 SHA-256 hashes match DEF-HASHES.txt');
  process.exit(0);
} else {
  console.error('[FAIL] gate_t3-compiler_hash');
  for (const f of failures) console.error(f);
  process.exit(1);
}
