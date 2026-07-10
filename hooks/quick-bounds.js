#!/usr/bin/env node
// God-space: quick-lane commits are mechanically bounded.
// PreToolUse on Bash. Judgment proposes, arithmetic disposes. Fail-open.
const fs = require('fs');
const { execSync } = require('child_process');
const STATE = (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault')) + '/council/state.md';
const DEP_FILES = /(^|\/)(package\.json|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|requirements\.txt|pyproject\.toml|Cargo\.toml|go\.mod|Gemfile)$/;
const timer = setTimeout(() => process.exit(0), 3000);
let raw = '';
process.stdin.on('data', (d) => (raw += d));
process.stdin.on('end', () => {
  clearTimeout(timer);
  try {
    const input = JSON.parse(raw);
    const cmd = (input.tool_input && input.tool_input.command) || '';
    // \bgit\b ... \bcommit\b catches `git -C <path> commit`, env-prefixed forms, etc.
    if (!/\bgit\b[^\n|;&]*\bcommit\b/.test(cmd)) process.exit(0);
    const state = fs.readFileSync(STATE, 'utf8');
    const block = (state.match(/<!-- RUN-STATE([\s\S]*?)-->/) || [])[1] || '';
    if (((block.match(/^lane:\s*(\S+)/m) || [])[1] || 'none') !== 'quick') process.exit(0);
    // TIMING: this hook sees PRE-command staged state. Staging inside the same
    // command (git add && git commit, commit -a/-am/--all) would evade the
    // numstat bound entirely — so in quick lane, stage-and-commit one-shots
    // are blocked outright. Stage first, then commit.
    if (/\bgit\b[^\n]*\badd\b/.test(cmd) || /\bcommit\b[^\n]*\s(-a\b|-am\b|--all\b)/.test(cmd)) {
      console.error('QUICK-LANE BOUNDS: stage-and-commit in one command evades the staged-diff bound. In quick lane: `git add` first (separate command), then commit — the bound is checked against what is actually staged. If the change is too big to bother, that is your answer: promote to standard.');
      process.exit(2);
    }
    const cwd = input.cwd || process.cwd();
    const numstat = execSync('git diff --cached --numstat', { cwd, timeout: 2000 }).toString().trim();
    if (!numstat) process.exit(0);
    const rows = numstat.split('\n').map((l) => l.split('\t'));
    const files = rows.length;
    const lines = rows.reduce((a, r) => a + (parseInt(r[0]) || 0) + (parseInt(r[1]) || 0), 0);
    const dep = rows.find((r) => DEP_FILES.test(r[2] || ''));
    if (files > 2 || lines > 150 || dep) {
      console.error(`QUICK-LANE BOUNDS: staged change exceeds quick lane (files=${files}/2, lines=${lines}/150${dep ? ', dependency manifest touched: ' + dep[2] : ''}). MANDATORY PROMOTION: set lane to standard in council/state.md, decompose properly, then proceed (see _system/run-protocol.md). Partial work becomes context, not waste.`);
      process.exit(2);
    }
    process.exit(0);
  } catch (e) { process.exit(0); }
});
