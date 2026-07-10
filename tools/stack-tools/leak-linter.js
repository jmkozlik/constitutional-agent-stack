'use strict';
// leak-linter.js — scans a proposed/ artifact for grading-machinery language
// that must never leak to lower layers.
// Forbidden-term list is GOD-SPACE: defined here, never read from vault.
// Exit code: EXACTLY 2 on any hit, 0 on clean.

const fs = require('fs');
const path = require('path');

// ============================================================
// GOD-SPACE: forbidden term definitions — edit only with monarch approval
// ============================================================
const FORBIDDEN_TERMS = [
  // Shadow-dimension names (literal string match, case-insensitive)
  { type: 'shadow-dimension', pattern: /\bunanimity\b/i, label: 'unanimity' },
  { type: 'shadow-dimension', pattern: /\bgovernance-heat\b/i, label: 'governance-heat' },
  { type: 'shadow-dimension', pattern: /\brehydration-dip\b/i, label: 'rehydration-dip' },
  { type: 'shadow-dimension', pattern: /\btokens-per-task\b/i, label: 'tokens-per-task' },

  // Threshold / weight patterns — scoring context
  { type: 'threshold-pattern', pattern: /(score|dimension|rating)\s*[<>]=?\s*\d/i, label: 'score/dimension/rating comparison to number' },
  { type: 'threshold-pattern', pattern: /\bweight\s*[:=]/i, label: 'weight assignment' },
  { type: 'threshold-pattern', pattern: /\bcomposite\s*(formula|score)\b/i, label: 'composite formula/score' },
  { type: 'threshold-pattern', pattern: /\bthreshold\b\s*[:=]\s*\d/i, label: 'threshold assignment to number' },
  // Decimal/probability comparison — catches "X > 0.N" patterns common in grading (0-1 scale)
  { type: 'threshold-pattern', pattern: /\b[\w][\w-]+\s*[<>]=?\s*0\.\d+/i, label: 'decimal comparison (possible grading threshold, 0-1 scale)' },
];
// ============================================================
// END GOD-SPACE
// ============================================================

const DEFAULT_FLAGS_DIR = (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault')) + '/god/beacons/leak-flags';

function parseArgs(argv) {
  const args = argv.slice(2);
  let artifactPath = null;
  let flagsDir = DEFAULT_FLAGS_DIR;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--flags-dir') {
      if (i + 1 >= args.length) {
        console.error('leak-linter: --flags-dir requires a path argument');
        process.exit(1);
      }
      flagsDir = args[++i];
    } else if (!args[i].startsWith('--')) {
      artifactPath = args[i];
    } else {
      console.error(`leak-linter: unknown flag: ${args[i]}`);
      process.exit(1);
    }
  }

  if (!artifactPath) {
    console.error('Usage: node leak-linter.js <artifact-path> [--flags-dir PATH]');
    process.exit(1);
  }

  return { artifactPath, flagsDir };
}

function validateFlagsDir(flagsDir) {
  // Write-guard: never follow a symlink, never write outside flags-dir
  let stat;
  try {
    stat = fs.lstatSync(flagsDir);
  } catch (e) {
    if (e.code === 'ENOENT') {
      // Attempt to create — but first ensure parent is safe
      // Check resolved parent does not traverse outside
      const resolved = path.resolve(flagsDir);
      const parent = path.dirname(resolved);
      // Verify parent itself is not a symlink
      try {
        const parentStat = fs.lstatSync(parent);
        if (parentStat.isSymbolicLink()) {
          console.error(`leak-linter: flags-dir parent is a symlink — aborting (write-guard)`);
          process.exit(1);
        }
        if (!parentStat.isDirectory()) {
          console.error(`leak-linter: flags-dir parent is not a directory — aborting`);
          process.exit(1);
        }
      } catch (pe) {
        console.error(`leak-linter: cannot stat flags-dir parent: ${pe.message}`);
        process.exit(1);
      }
      fs.mkdirSync(flagsDir, { recursive: false });
      return;
    }
    console.error(`leak-linter: cannot stat flags-dir: ${e.message}`);
    process.exit(1);
  }

  if (stat.isSymbolicLink()) {
    console.error(`leak-linter: flags-dir is a symlink — aborting (write-guard)`);
    process.exit(1);
  }
  if (!stat.isDirectory()) {
    console.error(`leak-linter: flags-dir exists but is not a directory — aborting (write-guard)`);
    process.exit(1);
  }

  // Traversal guard: ensure flags-dir path does not contain '..' after normalization
  const resolved = path.resolve(flagsDir);
  if (resolved !== path.normalize(resolved)) {
    console.error(`leak-linter: flags-dir path traversal detected — aborting (write-guard)`);
    process.exit(1);
  }
}

function scanArtifact(artifactPath) {
  let content;
  try {
    content = fs.readFileSync(artifactPath, 'utf8');
  } catch (e) {
    console.error(`leak-linter: cannot read artifact: ${e.message}`);
    process.exit(1);
  }

  const lines = content.split('\n');
  const hits = [];

  for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
    const line = lines[lineIdx];
    const lineNo = lineIdx + 1;
    for (const term of FORBIDDEN_TERMS) {
      const match = term.pattern.exec(line);
      if (match) {
        hits.push({
          type: term.type,
          label: term.label,
          lineNo,
          snippet: line.trim(),
          matchText: match[0],
        });
      }
    }
  }

  return hits;
}

function resolveFlagFilePath(flagsDir, basename) {
  // Collision guard: if base name exists, append -NN counter suffix
  const base = `${basename}.flag.md`;
  const candidate = path.join(flagsDir, base);

  // Security: verify the resolved path is strictly under flagsDir
  function assertUnderFlagsDir(p) {
    const resolvedFlagsDir = path.resolve(flagsDir);
    const resolvedP = path.resolve(p);
    if (!resolvedP.startsWith(resolvedFlagsDir + path.sep) &&
        resolvedP !== resolvedFlagsDir) {
      console.error(`leak-linter: resolved flag path escapes flags-dir — aborting (write-guard)`);
      process.exit(1);
    }
  }

  assertUnderFlagsDir(candidate);

  if (!fs.existsSync(candidate)) {
    return candidate;
  }

  for (let i = 2; i <= 999; i++) {
    const numbered = path.join(flagsDir, `${basename}-${String(i).padStart(2, '0')}.flag.md`);
    assertUnderFlagsDir(numbered);
    if (!fs.existsSync(numbered)) {
      return numbered;
    }
  }

  console.error('leak-linter: could not find a free flag file name after 999 attempts');
  process.exit(1);
}

function writeFlagFile(flagsDir, artifactPath, hits) {
  const artifactBasename = path.basename(artifactPath);
  const utcStamp = new Date().toISOString().replace(/[:.]/g, '-');
  const flagBasename = `${artifactBasename}-${utcStamp}`;
  const flagFilePath = resolveFlagFilePath(flagsDir, flagBasename);

  // Build flag content
  const lines = [
    '---',
    'type: leak-flag',
    `artifact: ${artifactPath}`,
    `flagged-at: ${new Date().toISOString()}`,
    '---',
    `# Leak-Linter Flag: ${artifactBasename}`,
    '',
    `**Artifact:** \`${artifactPath}\``,
    `**Hits:** ${hits.length}`,
    '',
    '## Hits',
    '',
  ];

  for (const hit of hits) {
    lines.push(`### Line ${hit.lineNo} — ${hit.type}: ${hit.label}`);
    lines.push(`- **Match:** \`${hit.matchText}\``);
    lines.push(`- **Snippet:** \`${hit.snippet}\``);
    lines.push('');
  }

  // Write-guard: verify the file does not already exist as a symlink or non-regular file
  try {
    const existingStat = fs.lstatSync(flagFilePath);
    if (existingStat.isSymbolicLink() || !existingStat.isFile()) {
      console.error(`leak-linter: flag file path is a symlink or non-regular file — aborting (write-guard)`);
      process.exit(1);
    }
  } catch (e) {
    // ENOENT is fine — file does not exist yet
    if (e.code !== 'ENOENT') {
      console.error(`leak-linter: cannot stat flag file path: ${e.message}`);
      process.exit(1);
    }
  }

  try {
    fs.writeFileSync(flagFilePath, lines.join('\n'), { flag: 'wx' }); // wx = fail if exists
  } catch (e) {
    console.error(`leak-linter: cannot write flag file: ${e.message}`);
    process.exit(1);
  }

  return flagFilePath;
}

// ============================================================
// Main
// ============================================================
(function main() {
  const { artifactPath, flagsDir } = parseArgs(process.argv);

  // Validate artifact is a regular file (read-only access)
  let artifactStat;
  try {
    artifactStat = fs.lstatSync(artifactPath);
  } catch (e) {
    console.error(`leak-linter: cannot stat artifact: ${e.message}`);
    process.exit(1);
  }
  if (artifactStat.isSymbolicLink()) {
    // Follow through for reading is fine but we note the real path
    // We do NOT restrict reading symlinks — only WRITING is guarded
  }
  if (!artifactStat.isFile() && !artifactStat.isSymbolicLink()) {
    console.error(`leak-linter: artifact path is not a file`);
    process.exit(1);
  }

  const hits = scanArtifact(artifactPath);

  if (hits.length === 0) {
    console.log(`LEAK-LINT CLEAN: ${artifactPath}`);
    process.exit(0);
  }

  // Hits found — validate/create flags dir and write flag
  validateFlagsDir(flagsDir);
  const flagFilePath = writeFlagFile(flagsDir, artifactPath, hits);

  console.error(`LEAK-LINT FLAGGED: ${artifactPath} — ${hits.length} hit(s)`);
  console.error(`Flag written: ${flagFilePath}`);

  process.exit(2);
})();
