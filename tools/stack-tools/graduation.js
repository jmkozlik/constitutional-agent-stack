#!/usr/bin/env node
'use strict';

// graduation.js — deterministic ledger reader for regency graduation status
// God-space: reads ledger, counts consecutive unvetoed MONARCH decisions per
// power class, reports which classes have hit their hardcoded threshold.

const fs = require('fs');
const path = require('path');

// --- Hardcoded thresholds (god-space, do NOT read from vault) ---
const THRESHOLDS = {
  'mega-auth':       10,
  'steward-signoff': 10,
  'pruning':          5,
  'amendment':       20,
};

const POWER_CLASSES = Object.keys(THRESHOLDS);

// Decision tokens
const POSITIVE_TOKENS = /\b(RATIFIED|SIGNED|APPROVED)\b/;
const VETO_TOKENS     = /\b(VETOED|REVERSED)\b/;

// --- CLI argument parsing ---
function parseArgs(argv) {
  const args = argv.slice(2);
  let vault = (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault'));
  let out    = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--vault' && args[i + 1]) {
      vault = args[++i];
    } else if (args[i] === '--out' && args[i + 1]) {
      out = args[++i];
    }
  }

  if (!out) {
    out = path.join(vault, 'god', 'regency-status.json');
  }

  return { vault, out };
}

// --- Frontmatter label extraction ---
// Returns array of label strings from YAML frontmatter, or [] if none.
function extractLabels(content) {
  // Match frontmatter block between --- delimiters
  const fmMatch = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!fmMatch) return [];

  const fm = fmMatch[1];

  // Match labels: [a, b, c]  OR  multi-line block form
  const inlineMatch = fm.match(/^labels\s*:\s*\[([^\]]*)\]/m);
  if (inlineMatch) {
    return inlineMatch[1]
      .split(',')
      .map(s => s.trim().replace(/^['"]|['"]$/g, ''))
      .filter(Boolean);
  }

  // Multi-line block:
  //   labels:
  //     - foo
  //     - bar
  // Walk frontmatter line-by-line. Find the `labels:` key (value empty on that
  // line), then collect subsequent indented `- item` lines until the next
  // non-indented (new-key) line OR end-of-frontmatter. Does NOT rely on a
  // following key existing (the previous `\Z` regex anchor was invalid in JS
  // and silently dropped labels-as-last-key blocks).
  const lines = fm.split(/\r?\n/);
  const labels = [];
  let inLabelsBlock = false;
  for (const line of lines) {
    if (!inLabelsBlock) {
      // Look for the labels: key with an empty inline value (block form).
      if (/^labels\s*:\s*$/.test(line)) {
        inLabelsBlock = true;
      }
      continue;
    }
    // Inside the block: indented list items continue it.
    const itemMatch = line.match(/^\s+-\s+(.+)$/);
    if (itemMatch) {
      labels.push(itemMatch[1].trim().replace(/^['"]|['"]$/g, ''));
      continue;
    }
    // A blank line is tolerated within the block; anything else (a new
    // non-indented key) ends it.
    if (/^\s*$/.test(line)) continue;
    break;
  }
  if (labels.length > 0) return labels;

  return [];
}

// --- Determine which power class (if any) an entry belongs to ---
// Returns the single matching power-class string, or null.
function entryPowerClass(labels) {
  const matches = POWER_CLASSES.filter(cls => labels.includes(cls));
  if (matches.length === 1) return matches[0];
  return null; // zero or ambiguous (>1) — not a MONARCH DECISION per spec
}

// --- Determine decision type from body ---
// Returns 'positive', 'veto', or null.
function decisionType(body) {
  const hasPositive = POSITIVE_TOKENS.test(body);
  const hasVeto     = VETO_TOKENS.test(body);

  if (hasVeto)     return 'veto';     // veto wins if both present
  if (hasPositive) return 'positive';
  return null;
}

// --- Read and sort ledger entries ---
function readLedger(ledgerDir) {
  let files;
  try {
    files = fs.readdirSync(ledgerDir);
  } catch (e) {
    // Ledger directory missing → treat as empty ledger
    return [];
  }

  // Keep only .md files, sort ascending by filename
  return files
    .filter(f => f.endsWith('.md'))
    .sort()
    .map(f => {
      const fullPath = path.join(ledgerDir, f);
      try {
        return { file: f, content: fs.readFileSync(fullPath, 'utf8') };
      } catch (_) {
        return null;
      }
    })
    .filter(Boolean);
}

// --- Core counting logic ---
function computeStatus(entries) {
  // Initialize counters
  const counters = {};
  for (const cls of POWER_CLASSES) {
    counters[cls] = 0;
  }

  for (const { content } of entries) {
    const labels = extractLabels(content);
    const cls    = entryPowerClass(labels);
    if (!cls) continue; // not a MONARCH DECISION

    // Body is everything after frontmatter
    const bodyStart = content.indexOf('---', 3); // skip opening ---
    const body = bodyStart >= 0 ? content.slice(bodyStart + 3) : content;

    const dtype = decisionType(body);
    if (!dtype) continue; // no decision token in body

    if (dtype === 'positive') {
      counters[cls] += 1;
    } else {
      // veto or reversal → reset
      counters[cls] = 0;
    }
  }

  // Build output
  const result = {};
  for (const cls of POWER_CLASSES) {
    const consecutive = counters[cls];
    const threshold   = THRESHOLDS[cls];
    result[cls] = {
      consecutive,
      threshold,
      graduated: consecutive >= threshold,
    };
  }
  return result;
}

// --- Write-guard: safe write to out file ---
function safeWrite(outPath, data) {
  const parentDir = path.dirname(outPath);

  // lstat the parent directory — abort on symlink or non-directory
  let parentStat;
  try {
    parentStat = fs.lstatSync(parentDir);
  } catch (e) {
    // Parent doesn't exist — create it only if it's a straightforward path
    // (no traversal check needed; out is script/flag-controlled per spec)
    fs.mkdirSync(parentDir, { recursive: true });
    parentStat = fs.lstatSync(parentDir);
  }

  if (parentStat.isSymbolicLink()) {
    console.error(`ABORT: parent directory ${parentDir} is a symlink — write refused.`);
    process.exit(1);
  }

  if (!parentStat.isDirectory()) {
    console.error(`ABORT: parent path ${parentDir} is not a directory — write refused.`);
    process.exit(1);
  }

  // lstat the out file itself if it exists — abort if it's a symlink
  try {
    const outStat = fs.lstatSync(outPath);
    if (outStat.isSymbolicLink()) {
      console.error(`ABORT: out path ${outPath} is a symlink — write refused.`);
      process.exit(1);
    }
  } catch (_) {
    // File doesn't exist yet — that's fine
  }

  fs.writeFileSync(outPath, JSON.stringify(data, null, 2) + '\n', 'utf8');
}

// --- Main ---
function main() {
  const { vault, out } = parseArgs(process.argv);
  const ledgerDir = path.join(vault, 'ledger');

  const entries = readLedger(ledgerDir);
  const status  = computeStatus(entries);

  safeWrite(out, status);

  // One-line summary to stdout
  const graduated = Object.entries(status)
    .filter(([, v]) => v.graduated)
    .map(([k]) => k);

  const summary = graduated.length > 0
    ? `GRADUATED: ${graduated.join(', ')}`
    : 'No classes graduated yet';

  const details = POWER_CLASSES
    .map(cls => `${cls}=${status[cls].consecutive}/${status[cls].threshold}`)
    .join(' ');

  console.log(`graduation.js: ${summary} | ${details}`);
  process.exit(0);
}

main();
