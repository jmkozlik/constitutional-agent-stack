#!/usr/bin/env node
// God-space: no executor spawns without an existing contract + active run.
// PreToolUse on Agent|Task. exit 2 + stderr = block. Fail-open on errors.
const fs = require('fs');
const STATE = (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault')) + '/council/state.md';
const EXEC_TYPES = /^stack-(implementer|test-engineer|integrator)$/;
const timer = setTimeout(() => process.exit(0), 3000);
let raw = '';
process.stdin.on('data', (d) => (raw += d));
process.stdin.on('end', () => {
  clearTimeout(timer);
  let input;
  try { input = JSON.parse(raw); } catch { process.exit(0); }
  const ti = input.tool_input || {};
  const prompt = ti.prompt || '';
  // Anchored to the actual marker LINE format — a prompt merely DISCUSSING
  // the marker (reviews, docs) must not be classified as an executor spawn.
  const isExecutor = EXEC_TYPES.test(ti.subagent_type || '') || /^EXECUTOR-SPAWN run-id:\s*\S+/m.test(prompt);
  if (!isExecutor) process.exit(0);

  let state = '';
  try { state = fs.readFileSync(STATE, 'utf8'); } catch {
    console.error('SPAWN GUARD: council/state.md unreadable — no executor spawns without run state.');
    process.exit(2);
  }
  const block = (state.match(/<!-- RUN-STATE([\s\S]*?)-->/) || [])[1] || '';
  const lane = (block.match(/^lane:\s*(\S+)/m) || [])[1] || 'none';
  const runId = (block.match(/^run-id:\s*(\S+)/m) || [])[1] || 'none';
  if (lane === 'none' || lane === 'quick' || runId === 'none') {
    console.error(`SPAWN GUARD: no active standard/mega run (lane=${lane}, run-id=${runId}). Executors spawn only inside a run — update RUN-STATE first (see _system/run-protocol.md).`);
    process.exit(2);
  }
  const m = prompt.match(/^CONTRACT:\s*(\S+)/m);
  if (!m) {
    console.error('SPAWN GUARD: executor spawn without a "CONTRACT: <path>" line in the prompt. No contract, no spawn.');
    process.exit(2);
  }
  if (!fs.existsSync(m[1])) {
    console.error(`SPAWN GUARD: contract file does not exist: ${m[1]}. No contract, no spawn.`);
    process.exit(2);
  }
  process.exit(0);
});
