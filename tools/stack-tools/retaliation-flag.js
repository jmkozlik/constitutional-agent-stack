#!/usr/bin/env node
/**
 * retaliation-flag.js — anti-collusion backstop
 *
 * Scans the last --window governance ledger entries for evidence that --target
 * filed a motion/mutiny AGAINST a member of --voters (the pruning majority).
 * Pure ledger arithmetic; no writable config accepted for filer/target mapping.
 *
 * Exit codes:
 *   0  — RETALIATION-CLEAR (no conflict found)
 *   1  — error (bad args, I/O failure, parse error)
 *   3  — CONFLICT detected (flag file written to --out)
 *
 * Invocation:
 *   node retaliation-flag.js --target <agent-id> --voters <a,b,c>
 *                             [--vault PATH] [--window N] [--out PATH]
 */

'use strict';

const fs   = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// CLI parsing — accept only the documented flags; no config file accepted
// ---------------------------------------------------------------------------
function parseArgs(argv) {
  const args = argv.slice(2);
  const result = {
    target:  null,
    voters:  null,
    vault:   null,
    window:  20,
    out:     null,
  };

  for (let i = 0; i < args.length; i++) {
    const flag = args[i];
    const next = args[i + 1];

    switch (flag) {
      case '--target':
        if (!next || next.startsWith('--')) die('--target requires a value');
        result.target = next;
        i++;
        break;
      case '--voters':
        if (!next || next.startsWith('--')) die('--voters requires a value');
        result.voters = next;
        i++;
        break;
      case '--vault':
        if (!next || next.startsWith('--')) die('--vault requires a value');
        result.vault = next;
        i++;
        break;
      case '--window':
        if (!next || next.startsWith('--')) die('--window requires a value');
        const w = parseInt(next, 10);
        if (isNaN(w) || w < 1) die('--window must be a positive integer');
        result.window = w;
        i++;
        break;
      case '--out':
        if (!next || next.startsWith('--')) die('--out requires a value');
        result.out = next;
        i++;
        break;
      default:
        die(`Unknown flag: ${flag}`);
    }
  }

  if (!result.target) die('--target is required');
  if (!result.voters) die('--voters is required');

  // Resolve vault: explicit flag, else VAULT env, else default vault location
  if (!result.vault) {
    result.vault = process.env.VAULT || (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault'));
  }

  if (!result.out) {
    result.out = path.join(result.vault, 'god', 'beacons', 'retaliation-flags');
  }

  return result;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function die(msg) {
  process.stderr.write(`retaliation-flag: error: ${msg}\n`);
  process.exit(1);
}

/**
 * Whole-token, case-insensitive equality check.
 * Ensures "obs-1" does NOT match "obs-10", "obs-11", etc.
 * We normalise both sides to lowercase and compare exactly.
 */
function tokenEq(a, b) {
  return a.toLowerCase().trim() === b.toLowerCase().trim();
}

/**
 * Parse YAML-style frontmatter from a markdown file.
 * Returns an object of key → value strings (values trimmed).
 * Only the region between the first and second `---` line is parsed.
 */
function parseFrontmatter(text) {
  const fm = {};
  const lines = text.split('\n');
  let inFrontmatter = false;
  let started = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!started && trimmed === '---') {
      inFrontmatter = true;
      started = true;
      continue;
    }
    if (started && inFrontmatter && trimmed === '---') {
      break; // end of frontmatter
    }
    if (!inFrontmatter) break;

    // Parse "key: value" lines
    const m = line.match(/^([a-zA-Z0-9_-]+)\s*:\s*(.*)$/);
    if (m) {
      fm[m[1].toLowerCase()] = m[2].trim();
    }
  }
  return fm;
}

/**
 * Extract the `labels:` array from frontmatter text.
 * Handles both inline form `labels: [a, b, c]` and the key-value form.
 * Returns an array of lowercase label strings.
 */
function extractLabels(fm) {
  const raw = fm['labels'] || '';
  if (!raw) return [];
  // Strip brackets and split by comma
  return raw
    .replace(/^\[/, '')
    .replace(/\]$/, '')
    .split(',')
    .map(s => s.trim().toLowerCase())
    .filter(Boolean);
}

/**
 * Extract filed-by and against from a ledger entry.
 *
 * Priority order (spec):
 *   1. Frontmatter `filed-by:` and `against:` keys
 *   2. Body lines `· filer: <value>` and `· against: <value>`
 *
 * Returns { filedBy: string|null, against: string|null }
 */
function extractFilingInfo(text, fm) {
  // 1. Frontmatter
  let filedBy = fm['filed-by'] || null;
  let against = fm['against'] || null;

  if (filedBy && against) return { filedBy, against };

  // 2. Body fallback — look for `· filer: <value>` and `· against: <value>`
  //    The bullet character may be · (U+00B7) or a plain ASCII period/dash.
  //    Per spec the exact form is `· filer:` / `· against:`.
  const bodyLines = text.split('\n');
  for (const line of bodyLines) {
    if (!filedBy) {
      const mFiler = line.match(/[·•*-]\s*filer\s*:\s*(.+)/i);
      if (mFiler) filedBy = mFiler[1].trim();
    }
    if (!against) {
      const mAgainst = line.match(/[·•*-]\s*against\s*:\s*(.+)/i);
      if (mAgainst) against = mAgainst[1].trim();
    }
    if (filedBy && against) break;
  }

  return { filedBy, against };
}

// ---------------------------------------------------------------------------
// Write-guard: safe flag file creation under <out>
// ---------------------------------------------------------------------------
function writeFlagFile(outDir, target, conflicts) {
  // lstat the parent — do NOT follow symlinks
  let stat;
  try {
    stat = fs.lstatSync(outDir);
  } catch (e) {
    if (e.code === 'ENOENT') {
      // Create directory (recursive), then re-lstat
      fs.mkdirSync(outDir, { recursive: true });
      stat = fs.lstatSync(outDir);
    } else {
      die(`Cannot lstat output directory "${outDir}": ${e.message}`);
    }
  }

  if (!stat.isDirectory()) {
    die(`Output path "${outDir}" exists but is not a directory (symlink or file) — aborting write`);
  }

  // Verify parent is a real directory (not a symlink to a directory)
  if (stat.isSymbolicLink()) {
    die(`Output path "${outDir}" is a symlink — aborting write (write-guard)`);
  }

  const stamp = new Date().toISOString().replace(/[:.]/g, '-').replace('T', 'T').slice(0, 23) + 'Z';
  const baseName = `${target}-${stamp}.flag.md`;

  // Collision avoidance: if file exists, append -NN suffix
  let filePath = path.join(outDir, baseName);
  if (fs.existsSync(filePath)) {
    let n = 1;
    while (fs.existsSync(filePath)) {
      filePath = path.join(outDir, baseName.replace('.flag.md', `-${String(n).padStart(2, '0')}.flag.md`));
      n++;
      if (n > 99) die('Too many collision suffixes — cannot write flag file');
    }
  }

  // Verify the final resolved path is still inside outDir (path traversal guard)
  const resolvedOut  = path.resolve(outDir);
  const resolvedFile = path.resolve(filePath);
  if (!resolvedFile.startsWith(resolvedOut + path.sep) && resolvedFile !== resolvedOut) {
    die(`Path traversal detected: resolved file "${resolvedFile}" escapes output dir "${resolvedOut}"`);
  }

  const lines = [
    '---',
    'type: retaliation-flag',
    `labels: [governance, case]`,
    `target: ${target}`,
    `status: conflict`,
    '---',
    `# Retaliation Flag — ${target}`,
    '',
    `Detected at: ${new Date().toISOString()}`,
    '',
    '## Conflicting filings',
    '',
  ];

  for (const c of conflicts) {
    lines.push(`### ${c.filename}`);
    lines.push(`- filed-by: ${c.filedBy}`);
    lines.push(`- against: ${c.against}`);
    lines.push(`- matched voter: ${c.matchedVoter}`);
    lines.push('');
  }

  fs.writeFileSync(filePath, lines.join('\n'), { encoding: 'utf8', flag: 'wx' });
  return filePath;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
function main() {
  const opts = parseArgs(process.argv);

  const targetId  = opts.target.toLowerCase().trim();
  const voterList = opts.voters
    .split(',')
    .map(v => v.toLowerCase().trim())
    .filter(Boolean);

  if (voterList.length === 0) die('--voters must contain at least one voter id');

  const ledgerDir = path.join(opts.vault, 'ledger');

  // Validate ledger directory exists and is a real directory (not symlink)
  let ledgerStat;
  try {
    ledgerStat = fs.lstatSync(ledgerDir);
  } catch (e) {
    die(`Cannot access ledger directory "${ledgerDir}": ${e.message}`);
  }
  if (!ledgerStat.isDirectory()) {
    die(`Ledger path "${ledgerDir}" is not a directory`);
  }

  // Read all .md ledger entries (excluding the section _index.md).
  // The rolling --window is defined over the LEDGER ENTRIES themselves
  // (sorted by filename), NOT over the governance subset. We take the newest
  // --window entries FIRST, then filter that window for motion/mutiny labels.
  // This is the security-load-bearing bound: an old filing that has scrolled
  // out of the newest-N ledger entries must NOT escalate, otherwise every
  // ancient filing floods god forever and the backstop becomes ignorable.
  let allFiles;
  try {
    allFiles = fs.readdirSync(ledgerDir)
      .filter(f => f.endsWith('.md') && f !== '_index.md')
      .sort(); // lexicographic = chronological for N-padded names
  } catch (e) {
    die(`Cannot read ledger directory: ${e.message}`);
  }

  // Take the newest --window ledger entries (sorted ascending, take the tail).
  const windowFiles = allFiles.slice(-opts.window);

  // Within the window, filter for motion/mutiny entries (parse frontmatter).
  const windowEntries = [];
  for (const filename of windowFiles) {
    const filepath = path.join(ledgerDir, filename);

    // Lstat each file — skip symlinks (read-guard)
    let fstat;
    try {
      fstat = fs.lstatSync(filepath);
    } catch (e) {
      continue; // skip unreadable
    }
    if (!fstat.isFile()) continue; // skip symlinks and dirs

    let text;
    try {
      text = fs.readFileSync(filepath, 'utf8');
    } catch (e) {
      continue; // skip unreadable files
    }

    const fm = parseFrontmatter(text);
    const labels = extractLabels(fm);

    if (labels.includes('motion') || labels.includes('mutiny')) {
      windowEntries.push({ filename, filepath, text, fm });
    }
  }

  // Scan for conflicts
  const conflicts = [];

  for (const entry of windowEntries) {
    const { filedBy, against } = extractFilingInfo(entry.text, entry.fm);

    if (!filedBy || !against) continue; // incomplete filing info — skip

    // CONFLICT iff filed-by == target AND against matches any voter
    if (!tokenEq(filedBy, targetId)) continue;

    // Check each voter for a whole-token match against the `against` field
    for (const voter of voterList) {
      if (tokenEq(against, voter)) {
        conflicts.push({
          filename: entry.filename,
          filedBy,
          against,
          matchedVoter: voter,
        });
        break; // one voter match per entry is enough
      }
    }
  }

  if (conflicts.length === 0) {
    process.stdout.write('RETALIATION-CLEAR\n');
    process.exit(0);
  }

  // CONFLICT — write flag file and exit 3
  let flagPath;
  try {
    flagPath = writeFlagFile(opts.out, opts.target, conflicts);
  } catch (e) {
    die(`Failed to write flag file: ${e.message}`);
  }

  process.stderr.write(`RETALIATION-CONFLICT: flag written to ${flagPath}\n`);
  process.exit(3);
}

main();
