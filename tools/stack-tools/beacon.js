#!/usr/bin/env node
// beacon.js — deterministic vault health-arithmetic
// God-space machinery: no agent-influenceable inputs, formulas hardcoded.
// Invocation: node beacon.js [--vault PATH] [--out PATH]
// Default vault: $VAULT_ROOT
// Default out:   <vault>/god/beacons

'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const args = argv.slice(2);
  let vault = (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault'));
  let out = null;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--vault' && args[i + 1]) {
      vault = args[++i];
    } else if (args[i] === '--out' && args[i + 1]) {
      out = args[++i];
    }
  }
  if (!out) out = path.join(vault, 'god', 'beacons');
  return { vault, out };
}

// ---------------------------------------------------------------------------
// WRITE-GUARD — adversarial vector hardening
// ---------------------------------------------------------------------------

/**
 * Validates the output directory:
 *   - Must exist and be a real directory (not a symlink, not a file).
 *   - If it does not exist, create it (after confirming parent is safe).
 * Returns the resolved real path of the directory.
 * Throws on any adversarial condition.
 */
function validateOutDir(outPath) {
  // Resolve any .. so path.join later can't escape via a component
  const resolved = path.resolve(outPath);

  // Check if it exists
  let stat;
  try {
    stat = fs.lstatSync(resolved); // lstat: does NOT follow symlinks
  } catch (e) {
    if (e.code === 'ENOENT') {
      // Try to create it; but first confirm parent is safe
      const parent = path.dirname(resolved);
      validateOutDir(parent); // recurse up to validate parent
      fs.mkdirSync(resolved, { recursive: false });
      return resolved;
    }
    throw new Error(`WRITE-GUARD: cannot stat out path "${resolved}": ${e.message}`);
  }

  if (stat.isSymbolicLink()) {
    throw new Error(
      `WRITE-GUARD: out path "${resolved}" is a symlink — refusing to write through it`
    );
  }
  if (!stat.isDirectory()) {
    throw new Error(
      `WRITE-GUARD: out path "${resolved}" exists but is not a directory`
    );
  }

  return resolved;
}

/**
 * Picks a collision-safe output file path under outDir.
 * Filename: beacon-<UTCstamp>.md
 * If it collides with an existing file, appends -01, -02, … counter.
 * No path traversal possible — filename is script-generated.
 */
function pickOutFile(outDir, ts) {
  const base = `beacon-${ts}.md`;
  const candidate = path.join(outDir, base);

  // Verify the candidate itself is not a symlink (adversarial pre-planted file)
  try {
    const st = fs.lstatSync(candidate);
    if (st.isSymbolicLink()) {
      throw new Error(
        `WRITE-GUARD: target file "${candidate}" is a symlink — refusing to write`
      );
    }
    // File already exists — find a counter suffix
    for (let n = 1; n <= 99; n++) {
      const suffix = String(n).padStart(2, '0');
      const alt = path.join(outDir, `beacon-${ts}-${suffix}.md`);
      try {
        const st2 = fs.lstatSync(alt);
        if (st2.isSymbolicLink()) {
          throw new Error(
            `WRITE-GUARD: target file "${alt}" is a symlink — refusing to write`
          );
        }
        // exists and not symlink → try next counter
      } catch (e2) {
        if (e2.code === 'ENOENT') return alt;
        throw e2; // re-throw WRITE-GUARD errors
      }
    }
    throw new Error(`WRITE-GUARD: could not find a free filename after 99 tries`);
  } catch (e) {
    if (e.code === 'ENOENT') return candidate; // base name is free
    throw e;
  }
}

// ---------------------------------------------------------------------------
// Ledger parsing
// ---------------------------------------------------------------------------

/**
 * Returns array of ledger entry objects parsed from <vault>/ledger/*.md.
 * Each object has: { file, frontmatter: {type, labels, runId, status}, body }
 * We parse only the YAML frontmatter block (lines between the first two ---).
 */
function parseLedger(vault) {
  const ledgerDir = path.join(vault, 'ledger');
  let files;
  try {
    files = fs.readdirSync(ledgerDir).filter(f => f.endsWith('.md') && f !== '_index.md');
  } catch (e) {
    if (e.code === 'ENOENT') return [];
    throw e;
  }

  return files.map(f => {
    const filePath = path.join(ledgerDir, f);
    const text = fs.readFileSync(filePath, 'utf8');
    const fm = parseFrontmatter(text);
    const body = stripFrontmatter(text);
    return { file: f, frontmatter: fm, body, raw: text };
  });
}

/**
 * Parse a minimal YAML frontmatter block.
 * Extracts: type, labels (array), run-id, status.
 */
function parseFrontmatter(text) {
  const lines = text.split('\n');
  if (lines[0].trim() !== '---') return {};
  const endIdx = lines.indexOf('---', 1);
  if (endIdx === -1) return {};
  const fmLines = lines.slice(1, endIdx);
  const result = {};
  for (const line of fmLines) {
    const m = line.match(/^([\w-]+):\s*(.+)$/);
    if (!m) continue;
    const key = m[1];
    const val = m[2].trim();
    if (key === 'labels') {
      // Parse [a, b, c] array
      result.labels = val.replace(/^\[|\]$/g, '')
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);
    } else if (key === 'run-id') {
      result.runId = val;
    } else {
      result[key] = val;
    }
  }
  return result;
}

function stripFrontmatter(text) {
  const lines = text.split('\n');
  if (lines[0].trim() !== '---') return text;
  const endIdx = lines.indexOf('---', 1);
  if (endIdx === -1) return text;
  return lines.slice(endIdx + 1).join('\n').trim();
}

// ---------------------------------------------------------------------------
// Telemetry parsing
// ---------------------------------------------------------------------------

/**
 * Returns array of { ts: Date, ...rest } from all *.jsonl in <vault>/.telemetry/
 * Sorted ascending by ts.
 */
function parseTelemetry(vault) {
  const telDir = path.join(vault, '.telemetry');
  let files;
  try {
    files = fs.readdirSync(telDir).filter(f => f.endsWith('.jsonl'));
  } catch (e) {
    if (e.code === 'ENOENT') return [];
    throw e;
  }

  const rows = [];
  for (const f of files) {
    const text = fs.readFileSync(path.join(telDir, f), 'utf8');
    for (const line of text.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const obj = JSON.parse(trimmed);
        if (obj.ts) {
          obj._date = new Date(obj.ts);
          rows.push(obj);
        }
      } catch (_) { /* skip malformed */ }
    }
  }

  rows.sort((a, b) => a._date - b._date);
  return rows;
}

// ---------------------------------------------------------------------------
// Canary parsing
// ---------------------------------------------------------------------------

/**
 * Returns { boots: Date[], lastBoot: Date|null } from <vault>/god/canary/
 * boot-log.jsonl lines contain {"ts": "..."} entries.
 * last-boot.json contains {"last_boot": "..."}.
 */
function parseCanary(vault) {
  const canaryDir = path.join(vault, 'god', 'canary');
  const bootLogPath = path.join(canaryDir, 'boot-log.jsonl');
  const lastBootPath = path.join(canaryDir, 'last-boot.json');

  const boots = [];
  try {
    const text = fs.readFileSync(bootLogPath, 'utf8');
    for (const line of text.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const obj = JSON.parse(trimmed);
        if (obj.ts) boots.push(new Date(obj.ts));
      } catch (_) { /* skip malformed line */ }
    }
    boots.sort((a, b) => a - b);
  } catch (e) {
    // Treat absent (ENOENT) AND unreadable boot-log the same: no boot data.
    // A god-space hook must never crash on bad input.
  }

  let lastBoot = null;
  try {
    const obj = JSON.parse(fs.readFileSync(lastBootPath, 'utf8'));
    if (obj.last_boot) lastBoot = new Date(obj.last_boot);
  } catch (e) {
    // Treat absent (ENOENT) AND malformed (SyntaxError, etc.) the same:
    // no last-boot data → lastBoot stays null → liveness=UNKNOWN downstream.
    // A god-space hook must never crash on bad input.
  }

  // Use last-boot.json as authoritative "last boot" if available,
  // regardless of whether it appears in the log (could be more recent)
  const allBoots = [...boots];
  if (lastBoot && (allBoots.length === 0 || lastBoot > allBoots[allBoots.length - 1])) {
    allBoots.push(lastBoot);
    allBoots.sort((a, b) => a - b);
  }

  return { boots: allBoots, lastBoot: allBoots.length > 0 ? allBoots[allBoots.length - 1] : null };
}

// ---------------------------------------------------------------------------
// Verify-report scanning
// ---------------------------------------------------------------------------

/**
 * Scans <vault>/executors/archive/<run-id>/verify-report-<task>.md files.
 * Returns array of { runId, task, verdict: 'NOT-REFUTED'|'REFUTED'|'UNKNOWN' }
 */
function parseVerifyReports(vault) {
  const archiveDir = path.join(vault, 'executors', 'archive');
  let runDirs;
  try {
    runDirs = fs.readdirSync(archiveDir).filter(d => {
      try {
        return fs.lstatSync(path.join(archiveDir, d)).isDirectory();
      } catch (_) { return false; }
    });
  } catch (e) {
    if (e.code === 'ENOENT') return [];
    throw e;
  }

  const reports = [];
  for (const runId of runDirs) {
    const runDir = path.join(archiveDir, runId);
    let files;
    try {
      files = fs.readdirSync(runDir).filter(f => f.startsWith('verify-report-') && f.endsWith('.md'));
    } catch (_) { continue; }

    for (const f of files) {
      // extract task from filename: verify-report-<task>.md
      const taskMatch = f.match(/^verify-report-(.+)\.md$/);
      const task = taskMatch ? taskMatch[1] : f;
      const text = fs.readFileSync(path.join(runDir, f), 'utf8');
      let verdict = 'UNKNOWN';
      // Look for the literal tokens: check frontmatter verdict field first, then body
      const fm = parseFrontmatter(text);
      if (fm.verdict === 'NOT-REFUTED') verdict = 'NOT-REFUTED';
      else if (fm.verdict === 'REFUTED') verdict = 'REFUTED';
      else if (text.includes('NOT-REFUTED')) verdict = 'NOT-REFUTED';
      else if (text.includes('REFUTED')) verdict = 'REFUTED';

      // Determine attempt number from filename (e.g. verify-report-t3-index-attempt1 → attempt 1)
      const attemptMatch = task.match(/attempt(\d+)$/);
      const attempt = attemptMatch ? parseInt(attemptMatch[1], 10) : 1;
      // Remove attempt suffix from task name for grouping
      const baseTask = task.replace(/-attempt\d+$/, '');

      reports.push({ runId, file: f, task: baseTask, fullTask: task, attempt, verdict });
    }
  }
  return reports;
}

// ---------------------------------------------------------------------------
// Git log parsing
// ---------------------------------------------------------------------------

/**
 * Returns git log entries from the vault repo.
 * Uses execFileSync with array args to avoid shell injection.
 */
function parseGitLog(vault) {
  let output;
  try {
    output = execFileSync('git', [
      '-C', vault,
      'log',
      '--pretty=format:%H%x1f%s%x1f%ai',
      '--no-merges'
    ], { encoding: 'utf8', timeout: 10000 });
  } catch (e) {
    return [];
  }

  return output.trim().split('\n').filter(Boolean).map(line => {
    const parts = line.split('\x1f');
    return {
      hash: parts[0] || '',
      subject: parts[1] || '',
      date: parts[2] ? new Date(parts[2]) : null
    };
  });
}

// ---------------------------------------------------------------------------
// Metric computation
// ---------------------------------------------------------------------------

/**
 * Parse the leading timestamp from a ledger body line.
 * Accepts a full ISO instant (with time, e.g. 2026-01-01T10:00:00Z) or a
 * date-only string (2026-06-05). Returns a Date, or null if none found.
 * The full ISO form is preferred because it preserves sub-day resolution.
 */
function parseLeadingTimestamp(body) {
  if (!body) return null;
  // Full ISO instant: YYYY-MM-DDThh:mm(:ss)?(.sss)?(Z|±hh:mm)?
  const isoMatch = body.match(
    /^\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)/
  );
  if (isoMatch) {
    const d = new Date(isoMatch[1]);
    if (!isNaN(d.getTime())) return d;
  }
  // Date only: YYYY-MM-DD
  const dateMatch = body.match(/^\s*(\d{4}-\d{2}-\d{2})/);
  if (dateMatch) {
    const d = new Date(dateMatch[1]);
    if (!isNaN(d.getTime())) return d;
  }
  return null;
}

/**
 * Extracts run start/complete timestamps from ledger.
 * Returns Map<runId, { start: Date|null, complete: Date|null }>
 */
function extractRunTimestamps(entries) {
  const runs = new Map();

  for (const entry of entries) {
    const { frontmatter, body } = entry;
    if (!frontmatter.runId) continue;
    const runId = frontmatter.runId;

    if (!runs.has(runId)) runs.set(runId, { start: null, complete: null });
    const rec = runs.get(runId);

    // Detect start/complete timestamp from the body's leading timestamp token.
    // Ledger bodies lead with a timestamp, e.g.
    //   "2026-06-05 · r001-killtest START ..."           (date only)
    //   "2026-01-01T10:00:00Z · rX START"                (full ISO instant)
    // Prefer the full ISO instant (with time) so start→complete deltas have
    // sub-day resolution (contract worked example: 10:00→10:08 = 8m).
    const date = parseLeadingTimestamp(body);

    if (body.includes(' START ') || body.match(/\bSTART\b/)) {
      if (!rec.start) rec.start = date;
    }
    if (body.includes(' COMPLETE') || body.match(/\bCOMPLETE\b/)) {
      if (!rec.complete) rec.complete = date;
    }
  }

  return runs;
}

/**
 * Groups ledger entries by run-id, extracts labels.
 */
function groupByRun(entries) {
  const byRun = new Map();
  for (const entry of entries) {
    const runId = entry.frontmatter.runId || '_global';
    if (!byRun.has(runId)) byRun.set(runId, []);
    byRun.get(runId).push(entry);
  }
  return byRun;
}

/**
 * Metric: first-pass-verification-rate per run.
 * Fraction of tasks where attempt 1 verdict was NOT-REFUTED.
 */
function computeFirstPassRate(verifyReports) {
  // Group by runId+baseTask, find attempt-1 verdict
  const byRunTask = new Map();
  for (const r of verifyReports) {
    const key = `${r.runId}::${r.task}`;
    if (!byRunTask.has(key)) byRunTask.set(key, []);
    byRunTask.get(key).push(r);
  }

  const byRun = new Map();
  for (const [key, reports] of byRunTask) {
    const runId = reports[0].runId;
    if (!byRun.has(runId)) byRun.set(runId, { pass: 0, total: 0 });
    const rec = byRun.get(runId);
    rec.total++;
    // Find attempt 1 (or the report with no attempt suffix)
    const attempt1 = reports.find(r => r.attempt === 1) || reports[0];
    if (attempt1.verdict === 'NOT-REFUTED') rec.pass++;
  }

  const result = {};
  for (const [runId, { pass, total }] of byRun) {
    result[runId] = total > 0 ? pass / total : null;
  }
  return result;
}

/**
 * Metric: rework-rate — retry-ladder ledger entries per run.
 * A retry-ladder entry is any ledger entry that is itself a rung on the retry
 * ladder. We recognise it by:
 *   - label `retry-ladder` or `retry` on the entry, OR
 *   - body token `RETRY` (e.g. "· rW RETRY 1"), OR
 *   - body token "attempt 2"+ (a later attempt is a rework), OR
 *   - an aggregate body field "retries: N" (a completion-line summary).
 * Each retry-ladder entry counts as 1; a "retries: N" summary contributes N.
 */
function computeReworkRate(entries) {
  const byRun = new Map();

  for (const entry of entries) {
    const runId = entry.frontmatter.runId;
    if (!runId) continue;
    if (!byRun.has(runId)) byRun.set(runId, 0);

    const labels = entry.frontmatter.labels || [];
    const body = entry.body || '';

    // Aggregate "retries: N" summary line contributes N directly.
    const retryCountMatch = body.match(/retries:\s*(\d+)/);
    if (retryCountMatch) {
      byRun.set(runId, byRun.get(runId) + parseInt(retryCountMatch[1], 10));
      continue;
    }

    // A single retry-ladder rung counts as 1.
    const isRetryRung =
      labels.includes('retry-ladder') ||
      labels.includes('retry') ||
      /\bRETRY\b/.test(body) ||
      body.includes('attempt 2') ||
      body.includes('attempt-2') ||
      /attempt\s+[2-9]\b/i.test(body);

    if (isRetryRung) {
      byRun.set(runId, byRun.get(runId) + 1);
    }
  }

  return Object.fromEntries(byRun);
}

/**
 * Metric: revert-frequency — git revert commits per run.
 * Maps revert commits to runs by checking which run-id appears in the commit subject.
 */
function computeRevertFrequency(gitLog, runIds) {
  const byRun = {};
  for (const runId of runIds) byRun[runId] = 0;
  byRun['_unattributed'] = 0;

  for (const commit of gitLog) {
    if (!commit.subject.toLowerCase().startsWith('revert')) continue;
    // Try to attribute to a run
    let attributed = false;
    for (const runId of runIds) {
      if (commit.subject.includes(runId)) {
        byRun[runId] = (byRun[runId] || 0) + 1;
        attributed = true;
        break;
      }
    }
    if (!attributed) {
      byRun['_unattributed']++;
    }
  }

  return byRun;
}

/**
 * Metric: time-to-merge — ledger start→complete delta per run.
 * Returns { runId: '<N>m' | '<N>h' | '<N>d' | 'incomplete' }.
 * NOTE: when timestamps are date-only (no time component), delta is in whole days.
 */
function computeTimeToMerge(runTimestamps) {
  const result = {};
  for (const [runId, { start, complete }] of runTimestamps) {
    if (!start || !complete) {
      result[runId] = 'incomplete';
      continue;
    }
    const deltaMs = complete - start;
    if (deltaMs < 0) {
      result[runId] = 'incomplete';
      continue;
    }
    const deltaMin = Math.round(deltaMs / 60000);
    if (deltaMin < 60) {
      result[runId] = `${deltaMin}m`;
    } else if (deltaMin < 1440) {
      result[runId] = `${Math.round(deltaMin / 60)}h`;
    } else {
      result[runId] = `${Math.round(deltaMin / 1440)}d`;
    }
  }
  return result;
}

/**
 * Metric: tokens-per-task proxy — telemetry event count per run-id.
 * We assign telemetry rows to runs by matching run timestamps:
 * if a row's ts falls within [runStart, runComplete], it belongs to that run.
 * Rows not matching any run go to '_unattributed'.
 */
function computeTokensProxy(telemetry, runTimestamps) {
  const byRun = {};
  for (const [runId] of runTimestamps) byRun[runId] = 0;
  byRun['_unattributed'] = 0;

  for (const row of telemetry) {
    const ts = row._date;
    let attributed = false;
    for (const [runId, { start, complete }] of runTimestamps) {
      if (start && complete && ts >= start && ts <= complete) {
        byRun[runId] = (byRun[runId] || 0) + 1;
        attributed = true;
        break;
      }
    }
    if (!attributed) byRun['_unattributed']++;
  }

  return byRun;
}

/**
 * Metric: promotion-churn — count of entries that indicate a promotion was
 * subsequently reverted. Looks for 'promoted-then-reverted' pattern in ledger.
 * More concretely: count ledger entries where labels include both 'promotion'
 * and 'revert', or body contains "reverted" near a promotion context.
 */
function computePromotionChurn(entries) {
  const byRun = {};
  for (const entry of entries) {
    const runId = entry.frontmatter.runId || '_global';
    const labels = entry.frontmatter.labels || [];
    const body = entry.body || '';

    const isChurn = (labels.includes('promotion') && labels.includes('revert')) ||
      body.match(/promot\w+.*revert|revert.*promot/i);

    if (isChurn) {
      byRun[runId] = (byRun[runId] || 0) + 1;
    }
  }
  return byRun;
}

/**
 * SHADOW metric: governance-heat — motion + mutiny ledger entries per run.
 */
function computeGovernanceHeat(entries) {
  const byRun = {};
  for (const entry of entries) {
    const runId = entry.frontmatter.runId || '_global';
    const type = entry.frontmatter.type || '';
    const labels = entry.frontmatter.labels || [];

    const isHeat = type === 'motion' ||
      labels.includes('motion') ||
      labels.includes('mutiny') ||
      entry.body.match(/\bMUTINY\b/);

    if (isHeat) {
      byRun[runId] = (byRun[runId] || 0) + 1;
    }
  }
  return byRun;
}

/**
 * SHADOW metric: unanimity-rate — from panel ledger entries, fraction where all
 * pre-convene verdicts agreed.
 * Panel entries body: "· pre-convene: role PASS/N · role PASS/N · role PASS/N"
 * Unanimous = all roles had the same primary verdict (e.g., all PASS or all RE-DISCUSS).
 */
function computeUnanimityRate(entries) {
  const byRun = {};

  for (const entry of entries) {
    const runId = entry.frontmatter.runId || '_global';
    const labels = entry.frontmatter.labels || [];
    const body = entry.body || '';

    // Panel entries have label 'council' or body contains 'pre-convene'
    const isPanel = labels.includes('council') || body.includes('pre-convene:');
    if (!isPanel) continue;

    // Extract pre-convene verdicts: "PASS" or "RE-DISCUSS"
    const preConveneMatch = body.match(/pre-convene:\s*(.+?)(?:·\s*convene|\n|$)/);
    if (!preConveneMatch) continue;
    const preConveneText = preConveneMatch[1];
    const verdicts = [...preConveneText.matchAll(/\b(PASS|RE-DISCUSS)\b/g)].map(m => m[1]);
    if (verdicts.length === 0) continue;

    const unanimous = verdicts.every(v => v === verdicts[0]) ? 1 : 0;
    if (!byRun[runId]) byRun[runId] = { unanimous: 0, total: 0 };
    byRun[runId].unanimous += unanimous;
    byRun[runId].total++;
  }

  const result = {};
  for (const [runId, { unanimous, total }] of Object.entries(byRun)) {
    result[runId] = total > 0 ? unanimous / total : null;
  }
  return result;
}

/**
 * Metric: telemetry-liveness
 * - If no canary data at all: liveness=UNKNOWN
 * - If canary has a boot ts and NO telemetry rows appear after that boot: RECORDER-DEAD alarm
 * - If telemetry rows exist after the latest canary boot: liveness=OK
 */
function computeTelemetryLiveness(canary, telemetry) {
  const { lastBoot } = canary;

  if (!lastBoot) {
    // No canary data at all — absence of canary is not proof of dead recorder
    return { status: 'UNKNOWN', detail: 'no canary boot data found' };
  }

  // Filter telemetry rows that occurred AFTER the latest canary boot
  const rowsAfterBoot = telemetry.filter(row => row._date > lastBoot);

  if (rowsAfterBoot.length === 0) {
    // Canary boot exists but NO telemetry rows after it
    return {
      status: 'RECORDER-DEAD',
      detail: `canary last boot ${lastBoot.toISOString()} has no telemetry rows after it`,
      alarm: true
    };
  }

  const latestTs = rowsAfterBoot[rowsAfterBoot.length - 1]._date;
  return {
    status: 'OK',
    detail: `${rowsAfterBoot.length} rows after last boot ${lastBoot.toISOString()}; latest ${latestTs.toISOString()}`
  };
}

// ---------------------------------------------------------------------------
// Report generation
// ---------------------------------------------------------------------------

/**
 * Formats a UTC timestamp for use as a filename-safe string.
 * e.g. 2026-06-05T14:30:00Z → 20260605T143000Z
 */
function formatUTCStamp(date) {
  return date.toISOString()
    .replace(/[-:]/g, '')
    .replace(/\.\d+Z$/, 'Z');
}

/**
 * Format a rate (0..1) as a clean decimal per the contract worked example
 * (e.g. 1.0, 0.5, 0.75). null → 'n/a'.
 */
function formatRate(rate) {
  if (rate === null || rate === undefined) return 'n/a';
  // Keep a trailing .0 for whole numbers (contract: first-pass-verification-rate=1.0)
  if (Number.isInteger(rate)) return rate.toFixed(1);
  // Trim trailing zeros otherwise (0.50 -> 0.5)
  return String(parseFloat(rate.toFixed(4)));
}

/**
 * Generate the localized markdown report.
 *
 * TOKEN FORMAT CONTRACT (worked example, load-bearing for the blind gate):
 *   - `<metric>=<value>` for aggregate values
 *   - `<metric> <run-id>=<value>` for per-run localized values
 *   - first-pass-verification-rate is a DECIMAL (1.0, 0.75), never a percentage
 *   - time-to-merge <run-id>=<N>m
 *   - rework-rate=<N>, tokens-per-task proxy=<N>
 *   - The literal token `RECORDER-DEAD` appears in this report ONLY on a real
 *     liveness alarm. UNKNOWN ("no data") must stay grep-distinguishable from
 *     RECORDER-DEAD — so no legend/explanation may contain that token.
 */
function generateReport(metrics, ts, vault) {
  const lines = [
    `---`,
    `type: beacon`,
    `generated: ${ts.toISOString()}`,
    `vault: ${vault}`,
    `---`,
    ``,
    `# Vault Health Beacon — ${ts.toISOString()}`,
    ``,
    `## Summary`,
    ``
  ];

  const alarms = [];
  if (metrics.telemetryLiveness.alarm) {
    // Real alarm — the RECORDER-DEAD token is allowed here.
    alarms.push(`ALARM: telemetry-liveness=${metrics.telemetryLiveness.status}`);
  }

  if (alarms.length > 0) {
    lines.push(`> ALARMS: ${alarms.join('; ')}`);
    lines.push(``);
  }

  // -------------------------------------------------------------------------
  // first-pass-verification-rate (NAMED) — DECIMAL, not percentage
  // -------------------------------------------------------------------------
  lines.push(`## first-pass-verification-rate`);
  lines.push(`<!-- NAMED metric: fraction of tasks NOT-REFUTED on attempt 1 -->`);
  const fpvr = metrics.firstPassRate;
  if (Object.keys(fpvr).length === 0) {
    lines.push(`_no verify-reports found_`);
  } else {
    // Localized per run: `first-pass-verification-rate <run-id>=<decimal>`
    for (const [runId, rate] of Object.entries(fpvr)) {
      lines.push(`- first-pass-verification-rate ${runId}=${formatRate(rate)}`);
    }
    // Aggregate token (worked example: `first-pass-verification-rate=1.0`)
    const rates = Object.values(fpvr).filter(r => r !== null);
    if (rates.length > 0) {
      const agg = rates.reduce((a, b) => a + b, 0) / rates.length;
      lines.push(`- first-pass-verification-rate=${formatRate(agg)}`);
    }
  }
  lines.push(``);

  // -------------------------------------------------------------------------
  // rework-rate (NAMED) — `rework-rate=<N>`
  // -------------------------------------------------------------------------
  lines.push(`## rework-rate`);
  lines.push(`<!-- NAMED metric: retry-ladder ledger entries per run -->`);
  const rr = metrics.reworkRate;
  const rrRuns = Object.keys(rr).filter(r => r !== '_unattributed');
  let reworkTotal = 0;
  for (const runId of rrRuns) {
    if (rr[runId] > 0) {
      lines.push(`- rework-rate ${runId}=${rr[runId]}`);
      reworkTotal += rr[runId];
    }
  }
  lines.push(`- rework-rate=${reworkTotal}`);
  lines.push(``);

  // -------------------------------------------------------------------------
  // revert-frequency (NAMED) — `revert-frequency=<N>`
  // -------------------------------------------------------------------------
  lines.push(`## revert-frequency`);
  lines.push(`<!-- NAMED metric: git revert commits per run -->`);
  const rf = metrics.revertFreq;
  let revertTotal = 0;
  for (const [runId, count] of Object.entries(rf)) {
    if (runId === '_unattributed') continue;
    if (count > 0) {
      lines.push(`- revert-frequency ${runId}=${count}`);
      revertTotal += count;
    }
  }
  if ((rf['_unattributed'] || 0) > 0) {
    lines.push(`- revert-frequency _unattributed=${rf['_unattributed']}`);
    revertTotal += rf['_unattributed'];
  }
  lines.push(`- revert-frequency=${revertTotal}`);
  lines.push(``);

  // -------------------------------------------------------------------------
  // time-to-merge (NAMED) — `time-to-merge <run-id>=<N>m`
  // -------------------------------------------------------------------------
  lines.push(`## time-to-merge`);
  lines.push(`<!-- NAMED metric: ledger start→complete timestamp delta per run -->`);
  const ttm = metrics.timeToMerge;
  if (Object.keys(ttm).length === 0) {
    lines.push(`_no run timestamps found_`);
  } else {
    for (const [runId, delta] of Object.entries(ttm)) {
      lines.push(`- time-to-merge ${runId}=${delta}`);
    }
  }
  lines.push(``);

  // -------------------------------------------------------------------------
  // tokens-per-task (NAMED proxy) — `tokens-per-task proxy=<N>`
  // -------------------------------------------------------------------------
  lines.push(`## tokens-per-task proxy`);
  lines.push(`<!-- NAMED metric proxy: telemetry event count per run-id -->`);
  const tpt = metrics.tokensProxy;
  let tptTotal = 0;
  for (const [runId, count] of Object.entries(tpt)) {
    if (runId === '_unattributed') continue;
    if (count > 0) {
      lines.push(`- tokens-per-task proxy ${runId}=${count}`);
      tptTotal += count;
    }
  }
  if ((tpt['_unattributed'] || 0) > 0) {
    lines.push(`- tokens-per-task proxy _unattributed=${tpt['_unattributed']}`);
    tptTotal += tpt['_unattributed'];
  }
  lines.push(`- tokens-per-task proxy=${tptTotal}`);
  lines.push(``);

  // -------------------------------------------------------------------------
  // promotion-churn (NAMED) — `promotion-churn=<N>`
  // -------------------------------------------------------------------------
  lines.push(`## promotion-churn`);
  lines.push(`<!-- NAMED metric: promoted-then-reverted count -->`);
  const pc = metrics.promotionChurn;
  let churnTotal = 0;
  for (const [runId, count] of Object.entries(pc)) {
    if (count > 0) {
      lines.push(`- promotion-churn ${runId}=${count}`);
      churnTotal += count;
    }
  }
  lines.push(`- promotion-churn=${churnTotal}`);
  lines.push(``);

  // -------------------------------------------------------------------------
  // governance-heat (SHADOW) — `governance-heat=<N>`
  // -------------------------------------------------------------------------
  lines.push(`## governance-heat`);
  lines.push(`<!-- SHADOW metric: motion+mutiny ledger entries per run -->`);
  const gh = metrics.govHeat;
  let heatTotal = 0;
  for (const [runId, count] of Object.entries(gh)) {
    if (count > 0) {
      lines.push(`- governance-heat ${runId}=${count}`);
      heatTotal += count;
    }
  }
  lines.push(`- governance-heat=${heatTotal}`);
  lines.push(``);

  // -------------------------------------------------------------------------
  // unanimity-rate (SHADOW) — DECIMAL
  // -------------------------------------------------------------------------
  lines.push(`## unanimity-rate`);
  lines.push(`<!-- SHADOW metric: fraction of panels where all pre-convene verdicts agreed -->`);
  const ur = metrics.unanimityRate;
  if (Object.keys(ur).length === 0) {
    lines.push(`_no panel entries found_`);
  } else {
    for (const [runId, rate] of Object.entries(ur)) {
      lines.push(`- unanimity-rate ${runId}=${formatRate(rate)}`);
    }
    const urRates = Object.values(ur).filter(r => r !== null);
    if (urRates.length > 0) {
      const agg = urRates.reduce((a, b) => a + b, 0) / urRates.length;
      lines.push(`- unanimity-rate=${formatRate(agg)}`);
    }
  }
  lines.push(``);

  // -------------------------------------------------------------------------
  // telemetry-liveness — `telemetry-liveness=OK|UNKNOWN|RECORDER-DEAD`
  // The RECORDER-DEAD token must appear ONLY when status === 'RECORDER-DEAD'.
  // No legend may name the other states, or grep-distinguishability breaks.
  // -------------------------------------------------------------------------
  lines.push(`## telemetry-liveness`);
  const tl = metrics.telemetryLiveness;
  lines.push(`- telemetry-liveness=${tl.status}`);
  lines.push(`- detail: ${tl.detail}`);
  lines.push(``);

  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  const { vault, out } = parseArgs(process.argv);

  // Validate write-guard first — fail fast before expensive reads
  let safeOut;
  try {
    safeOut = validateOutDir(out);
  } catch (e) {
    process.stderr.write(`beacon.js: ${e.message}\n`);
    process.exit(1);
  }

  // Read all data sources (read-only)
  const ledgerEntries = parseLedger(vault);
  const telemetry = parseTelemetry(vault);
  const canary = parseCanary(vault);
  const verifyReports = parseVerifyReports(vault);
  const gitLog = parseGitLog(vault);

  // Extract run IDs from ledger
  const runTimestamps = extractRunTimestamps(ledgerEntries);
  const runIds = [...runTimestamps.keys()];

  // Compute all metrics
  const metrics = {
    firstPassRate: computeFirstPassRate(verifyReports),
    reworkRate: computeReworkRate(ledgerEntries),
    revertFreq: computeRevertFrequency(gitLog, runIds),
    timeToMerge: computeTimeToMerge(runTimestamps),
    tokensProxy: computeTokensProxy(telemetry, runTimestamps),
    promotionChurn: computePromotionChurn(ledgerEntries),
    govHeat: computeGovernanceHeat(ledgerEntries),
    unanimityRate: computeUnanimityRate(ledgerEntries),
    telemetryLiveness: computeTelemetryLiveness(canary, telemetry)
  };

  // Determine timestamp for output filename
  let ts;
  try {
    ts = new Date();
    if (isNaN(ts.getTime())) throw new Error('invalid date');
  } catch (_) {
    // Fallback: use latest canary ts or epoch counter
    if (canary.lastBoot) {
      ts = canary.lastBoot;
    } else {
      ts = new Date(0);
    }
  }

  // Pick collision-safe output file
  const stamp = formatUTCStamp(ts);
  let outFile;
  try {
    outFile = pickOutFile(safeOut, stamp);
  } catch (e) {
    process.stderr.write(`beacon.js: ${e.message}\n`);
    process.exit(1);
  }

  // Generate report
  const report = generateReport(metrics, ts, vault);

  // Write report (the ONLY write operation)
  try {
    fs.writeFileSync(outFile, report, { encoding: 'utf8', flag: 'wx' });
    // 'wx' = exclusive create — fails if file appeared between our lstat check and now
  } catch (e) {
    if (e.code === 'EEXIST') {
      // Race: try once more with a new counter
      process.stderr.write(`beacon.js: collision on write (race), retrying once\n`);
      const stamp2 = formatUTCStamp(new Date(ts.getTime() + 1));
      const outFile2 = path.join(safeOut, `beacon-${stamp2}.md`);
      // WRITE-GUARD: lstat the retry path before writing — same guard as primary path.
      // A pre-planted symlink at the retry name must not be written through.
      try {
        const st2 = fs.lstatSync(outFile2);
        if (st2.isSymbolicLink()) {
          throw new Error(
            `WRITE-GUARD: retry target file "${outFile2}" is a symlink — refusing to write`
          );
        }
      } catch (lstatErr) {
        if (lstatErr.code !== 'ENOENT') throw lstatErr;
        // ENOENT: path is free, safe to create
      }
      fs.writeFileSync(outFile2, report, { encoding: 'utf8', flag: 'wx' });
      outFile = outFile2;
    } else {
      process.stderr.write(`beacon.js: write failed: ${e.message}\n`);
      process.exit(1);
    }
  }

  // One-line summary to stdout
  const liveness = metrics.telemetryLiveness.status;
  const runCount = runIds.length;
  const verifyCount = Object.values(metrics.firstPassRate).filter(r => r !== null).length;
  const govCount = Object.values(metrics.govHeat).reduce((a, b) => a + b, 0);
  const summary = `beacon: ${runCount} runs | first-pass-rate per-run above | gov-heat ${govCount} | liveness=${liveness} | report: ${outFile}`;
  process.stdout.write(summary + '\n');

  process.exit(0);
}

// Export for testing (when required as a module rather than run directly)
if (require.main === module) {
  main();
} else {
  module.exports = {
    parseArgs,
    validateOutDir,
    pickOutFile,
    parseFrontmatter,
    parseLedger,
    parseTelemetry,
    parseCanary,
    parseVerifyReports,
    parseGitLog,
    parseLeadingTimestamp,
    extractRunTimestamps,
    computeFirstPassRate,
    computeReworkRate,
    computeRevertFrequency,
    computeTimeToMerge,
    computeTokensProxy,
    computePromotionChurn,
    computeGovernanceHeat,
    computeUnanimityRate,
    computeTelemetryLiveness,
    formatUTCStamp,
    formatRate,
    generateReport
  };
}
