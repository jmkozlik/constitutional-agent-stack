#!/usr/bin/env node
// God-space machinery: vault/ledger/ is append-only for ALL agents.
// Hook protocol: PreToolUse, JSON on stdin; exit 2 + stderr = block.
const fs = require('fs');
const path = require('path');
const LEDGER = (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault')) + '/ledger/';

// Never hang a blocking hook: if stdin stalls, fail-open after 3s.
const timer = setTimeout(() => process.exit(0), 3000);

let raw = '';
process.stdin.on('data', (d) => (raw += d));
process.stdin.on('end', () => {
  clearTimeout(timer);
  let input;
  try { input = JSON.parse(raw); } catch { process.exit(0); }
  const tool = input.tool_name || '';
  const fp = (input.tool_input && input.tool_input.file_path) || '';
  if (!fp) process.exit(0);

  // Canonicalize: resolve relative paths and ../, then realpath the deepest
  // EXISTING ancestor — closes symlink tricks and case tricks on
  // case-insensitive APFS (LEDGER/ vs ledger/).
  let canon;
  try {
    const abs = path.resolve(input.cwd || require('os').homedir(), fp);
    let dir = path.dirname(abs);
    while (!fs.existsSync(dir)) dir = path.dirname(dir);
    canon = path.join(fs.realpathSync(dir), abs.slice(dir.length));
  } catch { canon = path.resolve(fp); }

  if (!canon.toLowerCase().startsWith(LEDGER.toLowerCase())) process.exit(0);
  // The gardener mechanically regenerates the index; it is NOT a ledger entry.
  if (canon.toLowerCase() === (LEDGER + '_index.md').toLowerCase()) process.exit(0);

  if (tool === 'Edit' || tool === 'NotebookEdit') {
    console.error('LEDGER GUARD: the ledger is append-only — editing an existing entry is constitutionally barred. Create a NEW entry file instead.');
    process.exit(2);
  }
  if (tool === 'Write' && fs.existsSync(canon)) {
    console.error('LEDGER GUARD: that ledger entry already exists and the ledger is append-only. Create a new entry file with a new id.');
    process.exit(2);
  }
  process.exit(0);
});
