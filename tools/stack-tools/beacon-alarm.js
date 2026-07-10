#!/usr/bin/env node
// beacon-alarm.js — regression doorbell for the vault health beacon.
// God-space machinery: thresholds hardcoded, no agent-writable input can
// raise a threshold or silence a metric.
//
// Invocation: node beacon-alarm.js [--vault PATH] [--out PATH]
// Default vault: $VAULT_ROOT
// Default out:   <vault>/god/beacons
//
// Exit codes:
//   0  — BEACON-NOMINAL (all healthy, or insufficient data window)
//   4  — regression detected; alarm file written to <out>/alarm-<UTCstamp>.md
//   1  — internal error (write-guard failure, etc.)

'use strict';

const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// GOD-SPACE THRESHOLDS — hardcoded, non-suppressible
// ---------------------------------------------------------------------------
const THRESHOLDS = {
  FIRST_PASS_FLOOR:      0.6,   // alarm if first-pass-verification-rate DROPS below this
  REWORK_CEILING:        2.0,   // alarm if rework-rate RISES above this (retries per run)
  CONTRACT_VIOLATIONS:   0,     // alarm if ANY contract violations > 0
  PROMOTION_CHURN:       0,     // alarm if ANY promotion churn > 0
  GOV_HEAT_CEILING:      6,     // alarm if governance-heat per run EXCEEDS this
};

// Minimum number of distinct runs required to compute a rolling window.
// With fewer than this, we cannot distinguish regression from normal variance.
const MIN_WINDOW_RUNS = 2;

// Rolling window size: last N runs by ledger order.
const WINDOW_SIZE = 5;

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
// WRITE-GUARD — adversarial vector hardening (same semantics as beacon.js)
// ---------------------------------------------------------------------------

/**
 * Validates the output directory:
 *   - Must exist and be a real directory (not a symlink, not a file).
 *   - If it does not exist, create it (after confirming parent is safe).
 * Returns the resolved real path of the directory.
 * Throws on any adversarial condition.
 */
function validateOutDir(outPath) {
  const resolved = path.resolve(outPath);

  let stat;
  try {
    stat = fs.lstatSync(resolved); // lstat: does NOT follow symlinks
  } catch (e) {
    if (e.code === 'ENOENT') {
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
 * Filename: alarm-<UTCstamp>.md
 * If it collides with an existing file, appends -01, -02, … counter.
 * No path traversal possible — filename is script-generated.
 */
function pickAlarmFile(outDir, ts) {
  const base = `alarm-${ts}.md`;
  const candidate = path.join(outDir, base);

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
      const alt = path.join(outDir, `alarm-${ts}-${suffix}.md`);
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
        throw e2;
      }
    }
    throw new Error(`WRITE-GUARD: could not find a free filename after 99 tries`);
  } catch (e) {
    if (e.code === 'ENOENT') return candidate;
    throw e;
  }
}

// ---------------------------------------------------------------------------
// Ledger parsing (re-implemented per contract: must not import beacon.js)
// ---------------------------------------------------------------------------

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

/**
 * Returns array of ledger entry objects from <vault>/ledger/*.md,
 * sorted ascending by filename (which is the canonical ledger sequence).
 * Each entry: { file, seq, frontmatter, body, raw }
 */
function parseLedger(vault) {
  const ledgerDir = path.join(vault, 'ledger');
  let files;
  try {
    files = fs.readdirSync(ledgerDir)
      .filter(f => f.endsWith('.md') && f !== '_index.md')
      .sort(); // lexicographic = sequence order (zero-padded filenames)
  } catch (e) {
    if (e.code === 'ENOENT') return [];
    throw e;
  }

  return files.map((f, idx) => {
    const filePath = path.join(ledgerDir, f);
    const text = fs.readFileSync(filePath, 'utf8');
    const fm = parseFrontmatter(text);
    const body = stripFrontmatter(text);
    // Extract leading sequence number from filename (e.g. "0023-..." → 23)
    const seqMatch = f.match(/^(\d+)-/);
    const seq = seqMatch ? parseInt(seqMatch[1], 10) : idx;
    return { file: f, seq, frontmatter: fm, body, raw: text };
  });
}

/**
 * Extracts ordered run-ids from ledger by their FIRST appearance.
 * Returns array of runIds in ascending ledger-sequence order.
 */
function extractOrderedRunIds(entries) {
  const seen = new Set();
  const ordered = [];
  for (const entry of entries) {
    const runId = entry.frontmatter.runId;
    if (runId && runId !== '_global' && !seen.has(runId)) {
      seen.add(runId);
      ordered.push(runId);
    }
  }
  return ordered;
}

// ---------------------------------------------------------------------------
// Verify-report scanning (re-implemented per contract: must not import beacon.js)
// ---------------------------------------------------------------------------

/**
 * Scans <vault>/executors/archive/<run-id>/verify-report-<task>.md files.
 * Returns array of { runId, task, attempt, verdict }
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
      files = fs.readdirSync(runDir)
        .filter(f => f.startsWith('verify-report-') && f.endsWith('.md'));
    } catch (_) { continue; }

    for (const f of files) {
      const taskMatch = f.match(/^verify-report-(.+)\.md$/);
      const task = taskMatch ? taskMatch[1] : f;
      const text = fs.readFileSync(path.join(runDir, f), 'utf8');
      let verdict = 'UNKNOWN';
      const fm = parseFrontmatter(text);
      if (fm.verdict === 'NOT-REFUTED') verdict = 'NOT-REFUTED';
      else if (fm.verdict === 'REFUTED') verdict = 'REFUTED';
      else if (text.includes('NOT-REFUTED')) verdict = 'NOT-REFUTED';
      else if (text.includes('REFUTED')) verdict = 'REFUTED';

      const attemptMatch = task.match(/attempt(\d+)$/);
      const attempt = attemptMatch ? parseInt(attemptMatch[1], 10) : 1;
      const baseTask = task.replace(/-attempt\d+$/, '');

      reports.push({ runId, file: f, task: baseTask, fullTask: task, attempt, verdict });
    }
  }
  return reports;
}

// ---------------------------------------------------------------------------
// Metric computation over a rolling window of run-ids
// ---------------------------------------------------------------------------

/**
 * Compute first-pass-verification-rate AGGREGATED over the rolling window.
 *
 * Granularity is the RUN: a run "passes first-pass" iff every task it ran was
 * NOT-REFUTED on attempt 1 (zero first-attempt REFUTED verdicts). The window
 * rate is then:
 *
 *     rate = (runs that passed first-pass) / (runs that had any verify report)
 *
 * This is the contract's window metric — a sustained drop in first-pass quality
 * across the last N runs. (Worked example: 5 runs, 2 clean → 0.4 < floor 0.6;
 * boundary 3 clean of 5 → 0.6, exactly at floor, NOT a regression.)
 *
 * Returns {
 *   rate: number|null,        // aggregate window rate, null if no run had reports
 *   passRuns: number,         // count of clean runs
 *   totalRuns: number,        // count of runs with >=1 verify report
 *   perRun: Map<runId,{pass,total}>,  // per-run task breakdown (driver attribution)
 *   failingRuns: string[]     // runs that contributed >=1 REFUTED attempt-1 task
 * }
 */
function computeFirstPass(verifyReports, windowRunIds) {
  const windowSet = new Set(windowRunIds);

  // Group by runId+baseTask so multiple attempts of one task collapse to one task.
  const byRunTask = new Map();
  for (const r of verifyReports) {
    if (!windowSet.has(r.runId)) continue;
    const key = `${r.runId}::${r.task}`;
    if (!byRunTask.has(key)) byRunTask.set(key, []);
    byRunTask.get(key).push(r);
  }

  // Per-run task tallies: { pass, total } where pass = tasks NOT-REFUTED@1.
  const perRun = new Map();
  for (const runId of windowRunIds) perRun.set(runId, { pass: 0, total: 0 });

  for (const [, reports] of byRunTask) {
    const runId = reports[0].runId;
    const rec = perRun.get(runId);
    if (!rec) continue;
    rec.total++;
    const attempt1 = reports.find(r => r.attempt === 1) || reports[0];
    if (attempt1.verdict === 'NOT-REFUTED') {
      rec.pass++;
    }
  }

  // Aggregate at the RUN level.
  let passRuns = 0;
  let totalRuns = 0;
  const failingRuns = [];
  for (const runId of windowRunIds) {
    const rec = perRun.get(runId);
    if (!rec || rec.total === 0) continue; // run had no verify reports — excluded
    totalRuns++;
    if (rec.pass === rec.total) {
      passRuns++; // clean run: every task NOT-REFUTED on attempt 1
    } else {
      failingRuns.push(runId); // contributed >=1 REFUTED first-pass verdict
    }
  }

  return {
    rate: totalRuns > 0 ? passRuns / totalRuns : null,
    passRuns,
    totalRuns,
    perRun,
    failingRuns
  };
}

/**
 * Compute rework-rate per run-id (retry-ladder ledger entries per run).
 * Returns Map<runId, count>
 */
function computeReworkRateByRun(entries, windowRunIds) {
  const windowSet = new Set(windowRunIds);
  const byRun = new Map();
  for (const runId of windowRunIds) byRun.set(runId, 0);

  for (const entry of entries) {
    const runId = entry.frontmatter.runId;
    if (!runId || !windowSet.has(runId)) continue;

    const labels = entry.frontmatter.labels || [];
    const body = entry.body || '';

    const retryCountMatch = body.match(/retries:\s*(\d+)/);
    if (retryCountMatch) {
      byRun.set(runId, byRun.get(runId) + parseInt(retryCountMatch[1], 10));
      continue;
    }

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

  return byRun;
}

/**
 * Compute contract-violation count per run-id.
 * Looks for ledger entries with label 'contract-violation' or body token
 * 'CONTRACT VIOLATION' / 'contract-violation'.
 * Returns Map<runId, count>
 */
function computeContractViolationsByRun(entries, windowRunIds) {
  const windowSet = new Set(windowRunIds);
  const byRun = new Map();
  for (const runId of windowRunIds) byRun.set(runId, 0);

  for (const entry of entries) {
    const runId = entry.frontmatter.runId;
    if (!runId || !windowSet.has(runId)) continue;

    const labels = entry.frontmatter.labels || [];
    const body = entry.body || '';
    const type = entry.frontmatter.type || '';

    const isViolation =
      labels.includes('contract-violation') ||
      labels.includes('violation') ||
      type === 'contract-violation' ||
      /contract.violation/i.test(body) ||
      /CONTRACT.VIOLATION/i.test(body);

    if (isViolation) {
      byRun.set(runId, byRun.get(runId) + 1);
    }
  }

  return byRun;
}

/**
 * Compute promotion-churn per run-id.
 * Churn = a promotion that was subsequently reverted. The ledger records this
 * either as:
 *   (a) a SINGLE entry tagged with both 'promotion'/'promoted' and
 *       'revert'/'reverted' (or whose body says "promoted ... reverted"), OR
 *   (b) a PAIR of entries within the same run: one promotion entry
 *       (label 'promoted'/'promotion', or body "promoted") and one revert
 *       entry (label 'reverted'/'revert', or body "reverted").
 * For a run, churn = single-entry hits + min(promoteCount, revertCount) for the
 * separate-entry pattern. This catches the separated promoted/reverted pair the
 * fixtures emit while never double-counting a combined entry.
 * Returns Map<runId, count>
 */
function computePromotionChurnByRun(entries, windowRunIds) {
  const windowSet = new Set(windowRunIds);
  const byRun = new Map();
  for (const runId of windowRunIds) byRun.set(runId, 0);

  // Per-run tallies of separate promotion / revert events.
  const promoteCount = new Map();
  const revertCount = new Map();
  for (const runId of windowRunIds) {
    promoteCount.set(runId, 0);
    revertCount.set(runId, 0);
  }

  for (const entry of entries) {
    const runId = entry.frontmatter.runId;
    if (!runId || !windowSet.has(runId)) continue;

    const labels = entry.frontmatter.labels || [];
    const body = entry.body || '';

    const isPromote =
      labels.includes('promotion') ||
      labels.includes('promoted') ||
      /\bpromot\w*/i.test(body);
    const isRevert =
      labels.includes('revert') ||
      labels.includes('reverted') ||
      /\brevert\w*/i.test(body);

    // (a) Combined entry — a single entry that is BOTH a promotion and a revert.
    if (isPromote && isRevert) {
      byRun.set(runId, byRun.get(runId) + 1);
      continue;
    }

    // (b) Separate entries — tally for later pairing.
    if (isPromote) promoteCount.set(runId, promoteCount.get(runId) + 1);
    if (isRevert) revertCount.set(runId, revertCount.get(runId) + 1);
  }

  // Pair up separate promotion/revert events per run.
  for (const runId of windowRunIds) {
    const pairs = Math.min(promoteCount.get(runId), revertCount.get(runId));
    if (pairs > 0) {
      byRun.set(runId, byRun.get(runId) + pairs);
    }
  }

  return byRun;
}

/**
 * Compute governance-heat per run-id (motion + mutiny ledger entries).
 * Returns Map<runId, count>
 */
function computeGovHeatByRun(entries, windowRunIds) {
  const windowSet = new Set(windowRunIds);
  const byRun = new Map();
  for (const runId of windowRunIds) byRun.set(runId, 0);

  for (const entry of entries) {
    const runId = entry.frontmatter.runId;
    if (!runId || !windowSet.has(runId)) continue;

    const type = entry.frontmatter.type || '';
    const labels = entry.frontmatter.labels || [];
    const body = entry.body || '';

    const isHeat =
      type === 'motion' ||
      labels.includes('motion') ||
      labels.includes('mutiny') ||
      /\bMUTINY\b/.test(body);

    if (isHeat) {
      byRun.set(runId, byRun.get(runId) + 1);
    }
  }

  return byRun;
}

// ---------------------------------------------------------------------------
// Regression analysis
// ---------------------------------------------------------------------------

/**
 * Find the "driver" run: the run most responsible for a regression.
 * For rate metrics (lower-is-worse): run with the lowest rate.
 * For count metrics (higher-is-worse): run with the highest count.
 */
function findDriverRunLowest(byRunMap) {
  let driverRun = null;
  let worstVal = Infinity;
  for (const [runId, val] of byRunMap) {
    if (val !== null && val < worstVal) {
      worstVal = val;
      driverRun = runId;
    }
  }
  return { driverRun, worstVal };
}

function findDriverRunHighest(byRunMap) {
  let driverRun = null;
  let worstVal = -Infinity;
  for (const [runId, val] of byRunMap) {
    if (val !== null && val > worstVal) {
      worstVal = val;
      driverRun = runId;
    }
  }
  return { driverRun, worstVal };
}

/**
 * Analyze metrics for regressions over the window.
 * Returns array of regression objects: { metric, value, threshold, driverRun, direction, detail }
 *
 * Threshold semantics are STRICT:
 *   - floor metrics alarm only when value <  floor   (exactly-at-floor is healthy)
 *   - ceiling metrics alarm only when value >  ceiling (exactly-at-ceiling is healthy)
 */
function analyzeRegressions(metrics) {
  const regressions = [];

  // 1. first-pass-verification-rate — AGGREGATE window rate.
  //    Alarm only when the window rate DROPS strictly below the floor.
  {
    const fp = metrics.firstPass;
    if (fp && fp.rate !== null && fp.rate < THRESHOLDS.FIRST_PASS_FLOOR) {
      // Driver: a run that contributed a REFUTED first-pass verdict. Prefer the
      // run with the lowest per-run pass rate; fall back to the first failing run.
      let driverRun = fp.failingRuns.length > 0 ? fp.failingRuns[0] : null;
      let worstRunRate = Infinity;
      for (const runId of fp.failingRuns) {
        const rec = fp.perRun.get(runId);
        const r = rec && rec.total > 0 ? rec.pass / rec.total : 0;
        if (r < worstRunRate) {
          worstRunRate = r;
          driverRun = runId;
        }
      }
      regressions.push({
        metric: 'first-pass-verification-rate',
        value: fp.rate,
        threshold: THRESHOLDS.FIRST_PASS_FLOOR,
        driverRun,
        direction: 'below-floor',
        // Contract worked example token: states the OBSERVED value, the
        // threshold crossed, and the driver run.
        detail: `first-pass-verification-rate=${formatRate(fp.rate)} < ${formatRate(THRESHOLDS.FIRST_PASS_FLOOR)}, driver: ${driverRun}`,
        observed: fp.rate,
        allFailing: fp.failingRuns.map(runId => {
          const rec = fp.perRun.get(runId);
          return { runId, rate: rec && rec.total > 0 ? rec.pass / rec.total : null };
        })
      });
    }
  }

  // 2. rework-rate — alarm if ANY run in window exceeds ceiling
  const rrFailing = [];
  for (const [runId, count] of metrics.reworkByRun) {
    if (count > THRESHOLDS.REWORK_CEILING) {
      rrFailing.push({ runId, count });
    }
  }
  if (rrFailing.length > 0) {
    rrFailing.sort((a, b) => b.count - a.count);
    const driver = rrFailing[0];
    regressions.push({
      metric: 'rework-rate',
      value: driver.count,
      threshold: THRESHOLDS.REWORK_CEILING,
      driverRun: driver.runId,
      direction: 'above-ceiling',
      detail: `rework-rate=${driver.count} > ${THRESHOLDS.REWORK_CEILING}, driver: ${driver.runId}`,
      allFailing: rrFailing
    });
  }

  // 3. contract-violations — alarm if count > 0 in ANY run in window
  const cvFailing = [];
  for (const [runId, count] of metrics.violationsByRun) {
    if (count > THRESHOLDS.CONTRACT_VIOLATIONS) {
      cvFailing.push({ runId, count });
    }
  }
  if (cvFailing.length > 0) {
    cvFailing.sort((a, b) => b.count - a.count);
    const driver = cvFailing[0];
    regressions.push({
      metric: 'contract-violations',
      value: driver.count,
      threshold: THRESHOLDS.CONTRACT_VIOLATIONS,
      driverRun: driver.runId,
      direction: 'above-ceiling',
      detail: `contract-violations=${driver.count} > ${THRESHOLDS.CONTRACT_VIOLATIONS}, driver: ${driver.runId}`,
      allFailing: cvFailing
    });
  }

  // 4. promotion-churn — alarm if count > 0 in ANY run in window
  const pcFailing = [];
  for (const [runId, count] of metrics.churnByRun) {
    if (count > THRESHOLDS.PROMOTION_CHURN) {
      pcFailing.push({ runId, count });
    }
  }
  if (pcFailing.length > 0) {
    pcFailing.sort((a, b) => b.count - a.count);
    const driver = pcFailing[0];
    regressions.push({
      metric: 'promotion-churn',
      value: driver.count,
      threshold: THRESHOLDS.PROMOTION_CHURN,
      driverRun: driver.runId,
      direction: 'above-ceiling',
      detail: `promotion-churn=${driver.count} > ${THRESHOLDS.PROMOTION_CHURN}, driver: ${driver.runId}`,
      allFailing: pcFailing
    });
  }

  // 5. governance-heat — alarm if ANY run in window exceeds ceiling
  const ghFailing = [];
  for (const [runId, count] of metrics.govHeatByRun) {
    if (count > THRESHOLDS.GOV_HEAT_CEILING) {
      ghFailing.push({ runId, count });
    }
  }
  if (ghFailing.length > 0) {
    ghFailing.sort((a, b) => b.count - a.count);
    const driver = ghFailing[0];
    regressions.push({
      metric: 'governance-heat',
      value: driver.count,
      threshold: THRESHOLDS.GOV_HEAT_CEILING,
      driverRun: driver.runId,
      direction: 'above-ceiling',
      detail: `governance-heat=${driver.count} > ${THRESHOLDS.GOV_HEAT_CEILING}, driver: ${driver.runId}`,
      allFailing: ghFailing
    });
  }

  return regressions;
}

// ---------------------------------------------------------------------------
// Report formatting
// ---------------------------------------------------------------------------

/**
 * Formats a rate (0..1) as a decimal string (e.g. 0.40, 0.60).
 */
function formatRate(val) {
  if (val === null || val === undefined) return 'n/a';
  if (Number.isInteger(val)) return val.toFixed(1);
  return String(parseFloat(val.toFixed(4)));
}

/**
 * Formats a UTC timestamp for filename use.
 * e.g. 2026-06-05T14:30:00Z → 20260605T143000Z
 */
function formatUTCStamp(date) {
  return date.toISOString()
    .replace(/[-:]/g, '')
    .replace(/\.\d+Z$/, 'Z');
}

/**
 * Generate a localized alarm markdown file.
 * Names the metric, threshold crossed, and specific run-id/agent-type that
 * drove it. Not a raw dump.
 */
function generateAlarmReport(regressions, windowRunIds, ts) {
  const lines = [
    `---`,
    `type: beacon-alarm`,
    `generated: ${ts.toISOString()}`,
    `regression-count: ${regressions.length}`,
    `---`,
    ``,
    `# BEACON ALARM — ${ts.toISOString()}`,
    ``,
    `Regression detected in rolling window of last ${WINDOW_SIZE} runs.`,
    `Window runs (most recent first): ${[...windowRunIds].reverse().join(', ')}`,
    ``
  ];

  lines.push(`## Regressions (${regressions.length})`);
  lines.push('');

  for (const reg of regressions) {
    lines.push(`### ${reg.metric}`);
    lines.push('');
    lines.push(`- **Metric**: ${reg.metric}`);
    lines.push(`- **Observed value**: ${reg.metric}=${formatRate(reg.value)}`);
    lines.push(`- **Threshold**: ${reg.direction === 'below-floor' ? 'floor' : 'ceiling'} ${formatRate(reg.threshold)}`);
    lines.push(`- **Driver run**: ${reg.driverRun}`);
    lines.push(`- **Summary**: ${reg.detail}`);

    if (reg.allFailing && reg.allFailing.length > 1) {
      lines.push(`- **All failing runs in window**:`);
      for (const f of reg.allFailing) {
        lines.push(`  - ${f.runId}: ${formatRate(f.rate !== undefined ? f.rate : f.count)}`);
      }
    }
    lines.push('');
  }

  lines.push(`## Thresholds (god-space, hardcoded)`);
  lines.push('');
  lines.push(`| Metric | Direction | Threshold |`);
  lines.push(`|--------|-----------|-----------|`);
  lines.push(`| first-pass-verification-rate | floor | ${THRESHOLDS.FIRST_PASS_FLOOR} |`);
  lines.push(`| rework-rate | ceiling | ${THRESHOLDS.REWORK_CEILING} |`);
  lines.push(`| contract-violations | ceiling | ${THRESHOLDS.CONTRACT_VIOLATIONS} |`);
  lines.push(`| promotion-churn | ceiling | ${THRESHOLDS.PROMOTION_CHURN} |`);
  lines.push(`| governance-heat | ceiling | ${THRESHOLDS.GOV_HEAT_CEILING}/run |`);
  lines.push('');

  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  const { vault, out } = parseArgs(process.argv);

  // Validate write-guard first — fail fast before expensive reads.
  // We do this upfront even though we may not write (healthy case) because
  // the out dir must be safe before we commit to any path.
  let safeOut;
  try {
    safeOut = validateOutDir(out);
  } catch (e) {
    process.stderr.write(`beacon-alarm.js: ${e.message}\n`);
    process.exit(1);
  }

  // Read ledger (read-only)
  const ledgerEntries = parseLedger(vault);

  // Extract ordered run-ids from ledger
  const allOrderedRunIds = extractOrderedRunIds(ledgerEntries);

  // Read verify reports (read-only)
  const verifyReports = parseVerifyReports(vault);

  // --- Insufficient data check ---
  // We require at least MIN_WINDOW_RUNS distinct runs in the ledger.
  if (allOrderedRunIds.length < MIN_WINDOW_RUNS) {
    process.stdout.write(
      `BEACON-NOMINAL (note: insufficient data — only ${allOrderedRunIds.length} run(s) in ledger, need ≥ ${MIN_WINDOW_RUNS})\n`
    );
    process.exit(0);
  }

  // Select the rolling window: last WINDOW_SIZE runs (most recent by ledger order)
  const windowRunIds = allOrderedRunIds.slice(-WINDOW_SIZE);

  // Compute metrics over the window
  const firstPass       = computeFirstPass(verifyReports, windowRunIds);
  const reworkByRun     = computeReworkRateByRun(ledgerEntries, windowRunIds);
  const violationsByRun = computeContractViolationsByRun(ledgerEntries, windowRunIds);
  const churnByRun      = computePromotionChurnByRun(ledgerEntries, windowRunIds);
  const govHeatByRun    = computeGovHeatByRun(ledgerEntries, windowRunIds);

  const metrics = {
    firstPass,
    reworkByRun,
    violationsByRun,
    churnByRun,
    govHeatByRun
  };

  // Analyze for regressions
  const regressions = analyzeRegressions(metrics);

  const ts = new Date();
  const stamp = formatUTCStamp(ts);

  if (regressions.length === 0) {
    // All healthy
    process.stdout.write(`BEACON-NOMINAL\n`);
    process.exit(0);
  }

  // Regression(s) detected — write localized alarm file
  let alarmFile;
  try {
    alarmFile = pickAlarmFile(safeOut, stamp);
  } catch (e) {
    process.stderr.write(`beacon-alarm.js: ${e.message}\n`);
    process.exit(1);
  }

  const report = generateAlarmReport(regressions, windowRunIds, ts);

  try {
    fs.writeFileSync(alarmFile, report, { encoding: 'utf8', flag: 'wx' });
  } catch (e) {
    if (e.code === 'EEXIST') {
      // Race: try once more with a 1ms offset
      process.stderr.write(`beacon-alarm.js: collision on write (race), retrying once\n`);
      const stamp2 = formatUTCStamp(new Date(ts.getTime() + 1));
      const alarmFile2 = path.join(safeOut, `alarm-${stamp2}.md`);
      fs.writeFileSync(alarmFile2, report, { encoding: 'utf8', flag: 'wx' });
      alarmFile = alarmFile2;
    } else {
      process.stderr.write(`beacon-alarm.js: write failed: ${e.message}\n`);
      process.exit(1);
    }
  }

  // One-line summary to stdout naming the first (primary) regression
  const primary = regressions[0];
  process.stdout.write(
    `BEACON-ALARM: ${regressions.length} regression(s) — ${primary.detail} | alarm: ${alarmFile}\n`
  );

  process.exit(4);
}

// Export for testing (when required as a module rather than run directly)
if (require.main === module) {
  main();
} else {
  module.exports = {
    THRESHOLDS,
    MIN_WINDOW_RUNS,
    WINDOW_SIZE,
    parseArgs,
    validateOutDir,
    pickAlarmFile,
    parseFrontmatter,
    parseLedger,
    extractOrderedRunIds,
    parseVerifyReports,
    computeFirstPass,
    computeReworkRateByRun,
    computeContractViolationsByRun,
    computePromotionChurnByRun,
    computeGovHeatByRun,
    analyzeRegressions,
    generateAlarmReport,
    formatRate,
    formatUTCStamp
  };
}
