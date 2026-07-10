#!/usr/bin/env node
// PostToolUse telemetry capture — silent, fast, fail-open.
// Raw feed for Phase 2 scorecards/beacon. Agents do not read this.
const fs = require('fs');
const timer = setTimeout(() => process.exit(0), 3000); // never hang a hook
let raw = '';
process.stdin.on('data', (d) => (raw += d));
process.stdin.on('end', () => {
  clearTimeout(timer);
  try {
    const i = JSON.parse(raw);
    const rec = {
      ts: new Date().toISOString(),
      tool: i.tool_name || '',
      file: (i.tool_input && i.tool_input.file_path) || undefined,
      session: i.session_id || '',
    };
    const dir = (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault')) + '/.telemetry';
    fs.mkdirSync(dir, { recursive: true });
    fs.appendFileSync(
      dir + '/raw-' + rec.ts.slice(0, 10) + '.jsonl',
      JSON.stringify(rec) + '\n'
    );
  } catch (e) { /* fail-open: telemetry must never break a session */ }
  process.exit(0);
});
